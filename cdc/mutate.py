"""
Module 700 — labelled fault injection.

Five operators rewrite a copied tree so ground truth is known by construction.
The source tree is never modified. NOMINAL is the adversary: the name and
docstring survive, the body does not.
"""

from __future__ import annotations

import ast
import builtins
import math
import os
import shutil
from dataclasses import dataclass
from typing import List, Optional, Sequence, Set, Union

from .model import Claim, CodeElement, sub_tokens

OPERATORS = ("DELETE", "RENAME", "WEAKEN", "STUB", "NOMINAL")

_WEAKEN = {
    "sha256": "md5",
    "sha512": "sha1",
    "AESGCM": "_xor_cipher",
    "pbkdf2_hmac": "md5",
    "secrets": "random",
}

_Func = Union[ast.FunctionDef, ast.AsyncFunctionDef]
_BUILTIN_NAMES = set(dir(builtins))


@dataclass(frozen=True)
class Mutation:
    operator: str
    target_uid: str
    target_name: str
    path: str
    claim_cid: str


def mutate_source(source: str, target_name: str, operator: str) -> str:
    tree = ast.parse(source)
    if operator == "DELETE":
        _delete_function(tree, target_name)
    elif operator == "RENAME":
        for func in _matching_functions(tree, target_name):
            func.name = f"_mutated_{func.name}"
    elif operator == "WEAKEN":
        for func in _matching_functions(tree, target_name):
            _weaken_function(func)
    elif operator == "STUB":
        for func in _matching_functions(tree, target_name):
            func.body = [ast.Raise(
                exc=ast.Name(id="NotImplementedError", ctx=ast.Load()),
                cause=None,
            )]
    elif operator == "NOMINAL":
        for func in _matching_functions(tree, target_name):
            _nominal_function(func)
        _drop_unused_imports(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def apply_mutations(
    src_root: str,
    dst_root: str,
    claims: Sequence[Claim],
    elements: Sequence[CodeElement],
    rng,
    rate: float = 0.3,
) -> list[Mutation]:
    shutil.copytree(src_root, dst_root, dirs_exist_ok=True)
    eligible = [
        el for el in elements
        if el.kind in {"function", "method"} and not el.is_stub
    ]
    pool = list(eligible)
    rng.shuffle(pool)
    chosen = pool[: math.floor(rate * len(pool))]
    records: list[Mutation] = []
    for el in chosen:
        operator = rng.choice(OPERATORS)
        path = _join(dst_root, el.path)
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        mutated = mutate_source(source, el.name, operator)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(mutated)
        records.append(Mutation(
            operator=operator,
            target_uid=el.uid,
            target_name=el.name,
            path=el.path,
            claim_cid=_claim_cid(claims, el),
        ))
    return records


def rename_identifiers(source: str, fraction: float, rng) -> str:
    if fraction == 0:
        ast.parse(source)
        return source
    tree = ast.parse(source)
    defined: List[str] = []
    seen: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name not in _BUILTIN_NAMES and node.name not in seen:
                defined.append(node.name)
                seen.add(node.name)
    if not defined:
        return ast.unparse(tree)
    shuffled = list(defined)
    rng.shuffle(shuffled)
    selected = shuffled[: math.ceil(fraction * len(defined))]
    mapping = {old: f"_r{i}_{old}" for i, old in enumerate(selected)}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in mapping:
                node.name = mapping[node.name]
        elif isinstance(node, ast.Name) and node.id in mapping:
            node.id = mapping[node.id]
        elif isinstance(node, ast.Attribute) and node.attr in mapping:
            node.attr = mapping[node.attr]
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _matching_functions(tree: ast.AST, target_name: str) -> List[_Func]:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == target_name
    ]


def _delete_function(tree: ast.AST, target_name: str) -> None:
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        node.body = [
            stmt for stmt in body
            if not (
                isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))
                and stmt.name == target_name
            )
        ]


def _weaken_function(func: _Func) -> None:
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id in _WEAKEN:
            node.id = _WEAKEN[node.id]
        elif isinstance(node, ast.Attribute) and node.attr in _WEAKEN:
            node.attr = _WEAKEN[node.attr]


def _nominal_function(func: _Func) -> None:
    kept: List[ast.stmt] = []
    if func.body and _is_docstring(func.body[0]):
        kept.append(func.body[0])
    kept.append(ast.Return(value=ast.Constant(value=None)))
    func.body = kept


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _drop_unused_imports(tree: ast.AST) -> None:
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    body: List[ast.stmt] = []
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            kept = [a for a in stmt.names if _bound_name(a) in used]
            if kept:
                stmt.names = kept
                body.append(stmt)
        elif isinstance(stmt, ast.ImportFrom):
            if any(a.name == "*" for a in stmt.names):
                body.append(stmt)
                continue
            kept = [a for a in stmt.names if _bound_name(a) in used]
            if kept:
                stmt.names = kept
                body.append(stmt)
        else:
            body.append(stmt)
    tree.body = body


def _bound_name(alias: ast.alias) -> str:
    if alias.asname:
        return alias.asname
    return alias.name.split(".")[0]


def _claim_cid(claims: Sequence[Claim], el: CodeElement) -> str:
    if not claims:
        return ""
    tokens = set(sub_tokens(el.name))
    best: Optional[Claim] = None
    best_n = 0
    for claim in claims:
        n = len(set(claim.terms) & tokens)
        if n > best_n:
            best_n = n
            best = claim
    if best is None:
        return claims[0].cid
    return best.cid


def _join(root: str, rel: str) -> str:
    parts = rel.replace("\\", "/").split("/")
    return os.path.join(root, *parts)

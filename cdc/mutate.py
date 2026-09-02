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


def mutate_source(
    source: str,
    target_name: str,
    operator: str,
    lineno: Optional[int] = None,
) -> str:
    tree = ast.parse(source)
    _apply_operator(tree, target_name, operator, lineno)
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
    trees: dict[str, ast.AST] = {}
    for el in chosen:
        operator = rng.choice(OPERATORS)
        path = _join(dst_root, el.path)
        if path not in trees:
            with open(path, encoding="utf-8") as fh:
                trees[path] = ast.parse(fh.read())
        _apply_operator(trees[path], el.name, operator, el.lineno)
        records.append(Mutation(
            operator=operator,
            target_uid=el.uid,
            target_name=el.name,
            path=el.path,
            claim_cid=_claim_cid(claims, el),
        ))
    for path, tree in trees.items():
        ast.fix_missing_locations(tree)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(ast.unparse(tree))
    return records


def rename_identifiers(source: str, fraction: float, rng) -> str:
    """
    Replace a fraction of the defined function and class names with opaque ones.

    The replacement is a bare ``f{i}``, not a decoration of the original. A
    decorated name such as ``_r0_digest_token`` still sub-tokenises to
    ``digest`` and ``token``, so the original identifier survives intact and no
    lexical signal is removed -- the ablation would measure nothing. The
    replacement must therefore share no sub-token with the name it replaces.

    Only identifiers are ablated: file paths and docstrings are untouched, so
    the NAME channel can still fire on the path and the DOC channel is
    unaffected.
    """
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
    mapping = _opaque_mapping(selected, _identifiers(tree))
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


def _identifiers(tree: ast.AST) -> Set[str]:
    """Every name already bound or referenced in the module."""
    out: Set[str] = set(_BUILTIN_NAMES)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, ast.arg):
            out.add(node.arg)
        elif isinstance(node, ast.alias):
            out.add(_bound_name(node))
    return out


def _opaque_mapping(selected: Sequence[str], taken: Set[str]) -> dict:
    """Map each selected name to a fresh ``f{i}`` that collides with nothing."""
    mapping: dict = {}
    i = 0
    for old in selected:
        while f"f{i}" in taken:
            i += 1
        mapping[old] = f"f{i}"
        taken.add(f"f{i}")
        i += 1
    return mapping


def _apply_operator(
    tree: ast.AST,
    target_name: str,
    operator: str,
    lineno: Optional[int] = None,
) -> None:
    if operator == "DELETE":
        _delete_function(tree, target_name, lineno)
    elif operator == "RENAME":
        for func in _matching_functions(tree, target_name, lineno):
            func.name = f"_mutated_{func.name}"
    elif operator == "WEAKEN":
        for func in _matching_functions(tree, target_name, lineno):
            _weaken_function(func)
    elif operator == "STUB":
        for func in _matching_functions(tree, target_name, lineno):
            func.body = [ast.Raise(
                exc=ast.Name(id="NotImplementedError", ctx=ast.Load()),
                cause=None,
            )]
    elif operator == "NOMINAL":
        for func in _matching_functions(tree, target_name, lineno):
            _nominal_function(func)
        _drop_unused_imports(tree)


def _is_target_func(node: ast.AST, target_name: str, lineno: Optional[int]) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    if node.name != target_name:
        return False
    return lineno is None or node.lineno == lineno


def _matching_functions(
    tree: ast.AST, target_name: str, lineno: Optional[int] = None,
) -> List[_Func]:
    return [
        node for node in ast.walk(tree)
        if _is_target_func(node, target_name, lineno)
    ]


def _delete_function(
    tree: ast.AST, target_name: str, lineno: Optional[int] = None,
) -> None:
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        node.body = [
            stmt for stmt in body
            if not _is_target_func(stmt, target_name, lineno)
        ]
        if (
            isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.body
        ):
            node.body = [ast.Pass()]


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

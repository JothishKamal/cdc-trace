"""
Module 200 — code extraction.

Builds a CodeElement inventory from a Python tree: functions, classes, methods,
routes and schema tables, with the imports each element can see, the names it
calls, a normalised vocabulary of the operations it actually performs, whether
its body is a stub, and whether it is reachable from an entry point.

The operation vocabulary is what makes the BODY channel substantive rather than
nominal: a function named `aes_gcm_encrypt_token` whose body raises
NotImplementedError has the name but not the operation.
"""

from __future__ import annotations

import ast
import os
from dataclasses import replace
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

from .model import CodeElement

STRONG_OPS: Dict[str, str] = {
    "AESGCM": "op:aead", "encrypt": "op:aead", "decrypt": "op:aead",
    "sha256": "op:hash", "sha512": "op:hash", "blake2b": "op:hash",
    "md5": "op:hash_weak", "sha1": "op:hash_weak",
    "pbkdf2_hmac": "op:kdf", "scrypt": "op:kdf",
    "hmac": "op:mac", "new": "op:mac",
    "token_bytes": "op:random", "urandom": "op:random",
    "compile": "op:regex", "match": "op:regex",
    "execute": "op:sql", "executemany": "op:sql", "commit": "op:sql",
    "dumps": "op:serialise", "loads": "op:serialise",
}

_STUB_MARKERS = ("NotImplementedError",)

_Func = Union[ast.FunctionDef, ast.AsyncFunctionDef]


def extract_source(source: str, path: str) -> List[CodeElement]:
    tree = ast.parse(source)
    imports = _module_imports(tree)
    is_test = _is_test_path(path)
    mod = _module_id(path)
    elements: List[CodeElement] = []
    for node in tree.body:
        elements.extend(_schema_tables(node, path, mod, imports))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            elements.append(_class_element(node, path, mod, imports))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cls = _enclosing_class(node, tree)
            nested = _enclosing_function(node, tree)
            elements.append(_function_element(
                node, path, mod, imports, is_test, cls, nested,
            ))
            elements.extend(_route_elements(node, path, mod, imports))
    return elements


def extract_codebase(root: str) -> List[CodeElement]:
    elements: List[CodeElement] = []
    extra_entries: Set[str] = set()
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, root).replace("\\", "/")
            with open(full, encoding="utf-8") as fh:
                source = fh.read()
            elements.extend(extract_source(source, rel))
            extra_entries |= _main_guard_names(source)
    return _apply_reachability(elements, extra_entries)


def _module_id(path: str) -> str:
    p = path.replace("\\", "/").replace("/", ".")
    if p.endswith(".py"):
        p = p[:-3]
    if p.endswith(".__init__"):
        p = p[:-9]
    return p


def _is_test_path(path: str) -> bool:
    norm = path.replace("\\", "/")
    base = os.path.basename(norm)
    return "/tests/" in f"/{norm}" or (
        base.startswith("test_") and base.endswith(".py")
    )


def _module_imports(tree: ast.Module) -> frozenset:
    names: Set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return frozenset(names)


def _parent_map(tree: ast.AST) -> Dict[ast.AST, ast.AST]:
    return {
        child: node
        for node in ast.walk(tree)
        for child in ast.iter_child_nodes(node)
    }


def _enclosing_class(node: ast.AST, tree: ast.AST) -> Optional[str]:
    parents = _parent_map(tree)
    cur: Optional[ast.AST] = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, ast.ClassDef):
            return cur.name
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None
    return None


def _enclosing_function(node: ast.AST, tree: ast.AST) -> bool:
    parents = _parent_map(tree)
    cur: Optional[ast.AST] = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return True
        if isinstance(cur, ast.ClassDef):
            return False
    return False


def _schema_tables(
    node: ast.AST, path: str, mod: str, imports: frozenset,
) -> List[CodeElement]:
    if not isinstance(node, ast.Assign):
        return []
    if not any(isinstance(t, ast.Name) and t.id == "SCHEMA" for t in node.targets):
        return []
    if not isinstance(node.value, ast.Dict):
        return []
    out: List[CodeElement] = []
    for key in node.value.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            out.append(CodeElement(
                uid=f"{mod}:{key.value}",
                kind="table",
                name=key.value,
                path=path,
                lineno=node.lineno,
                doc="",
                imports=imports,
                calls=frozenset(),
                body_ops=frozenset(),
                is_stub=False,
                reachable=False,
            ))
    return out


def _class_element(
    node: ast.ClassDef, path: str, mod: str, imports: frozenset,
) -> CodeElement:
    return CodeElement(
        uid=f"{mod}:{node.name}",
        kind="class",
        name=node.name,
        path=path,
        lineno=node.lineno,
        doc=ast.get_docstring(node) or "",
        imports=imports,
        calls=frozenset(),
        body_ops=frozenset(),
        is_stub=False,
        reachable=False,
    )


def _function_element(
    node: _Func,
    path: str,
    mod: str,
    imports: frozenset,
    is_test: bool,
    cls: Optional[str],
    nested: bool,
) -> CodeElement:
    if cls and not nested:
        kind = "test" if is_test else "method"
        uid = f"{mod}:{cls}.{node.name}"
    else:
        kind = "test" if is_test else "function"
        uid = f"{mod}:{node.name}"
    stub = _is_stub(node)
    calls, ops = _calls_and_ops(node)
    if stub:
        ops = frozenset()
    return CodeElement(
        uid=uid,
        kind=kind,
        name=node.name,
        path=path,
        lineno=node.lineno,
        doc=ast.get_docstring(node) or "",
        imports=imports,
        calls=frozenset(calls),
        body_ops=frozenset(ops),
        is_stub=stub,
        reachable=False,
    )


def _route_elements(
    node: _Func, path: str, mod: str, imports: frozenset,
) -> List[CodeElement]:
    out: List[CodeElement] = []
    for route_path in _route_paths(node):
        out.append(CodeElement(
            uid=f"{mod}:route:{route_path}",
            kind="route",
            name=route_path,
            path=path,
            lineno=node.lineno,
            doc=ast.get_docstring(node) or "",
            imports=imports,
            calls=frozenset({node.name}),
            body_ops=frozenset(),
            is_stub=False,
            reachable=False,
        ))
    return out


def _route_paths(node: _Func) -> List[str]:
    paths: List[str] = []
    for dec in node.decorator_list:
        if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
            continue
        if dec.func.attr not in {"route", "get", "post"} or not dec.args:
            continue
        arg0 = dec.args[0]
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            paths.append(arg0.value)
    return paths


def _is_stub(node: _Func) -> bool:
    body = list(node.body)
    if body and _is_docstring(body[0]):
        body = body[1:]
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and _is_ellipsis(stmt.value):
        return True
    if isinstance(stmt, ast.Raise) and _raises_stub(stmt):
        return True
    if isinstance(stmt, ast.Return) and _is_none_constant(stmt.value):
        return True
    return False


def _is_docstring(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _is_ellipsis(value: ast.expr) -> bool:
    return isinstance(value, ast.Constant) and value.value is Ellipsis


def _is_none_constant(value: Optional[ast.expr]) -> bool:
    return isinstance(value, ast.Constant) and value.value is None


def _raises_stub(stmt: ast.Raise) -> bool:
    exc = stmt.exc
    if exc is None:
        return False
    name = None
    if isinstance(exc, ast.Name):
        name = exc.id
    elif isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
        name = exc.func.id
    return name in _STUB_MARKERS


def _calls_and_ops(node: _Func) -> Tuple[Set[str], Set[str]]:
    calls: Set[str] = set()
    ops: Set[str] = set()
    for child in _walk_skip_nested(node.body):
        if isinstance(child, ast.Call):
            name = _call_name(child.func)
            if name:
                calls.add(name)
                if name in STRONG_OPS:
                    ops.add(STRONG_OPS[name])
        elif isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
            ops.add("op:loop")
        elif isinstance(child, ast.If):
            ops.add("op:branch")
        elif isinstance(child, (ast.Try, ast.Raise)):
            ops.add("op:error")
    return calls, ops


def _walk_skip_nested(stmts: Iterable[ast.AST]) -> Iterable[ast.AST]:
    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield stmt
        for child in ast.iter_child_nodes(stmt):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            yield child
            yield from _walk_skip_nested_node(child)


def _walk_skip_nested_node(node: ast.AST) -> Iterable[ast.AST]:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield child
        yield from _walk_skip_nested_node(child)


def _call_name(func: ast.AST) -> Optional[str]:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _main_guard_names(source: str) -> Set[str]:
    tree = ast.parse(source)
    names: Set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.If) and _is_main_guard(node.test):
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    name = _call_name(child.func)
                    if name:
                        names.add(name)
                elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                    if child.id not in {"__name__", "__main__"}:
                        names.add(child.id)
    return names


def _is_main_guard(test: ast.expr) -> bool:
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    left, right = test.left, test.comparators[0]
    return (
        (_is_name(left, "__name__") and _is_str(right, "__main__"))
        or (_is_str(left, "__main__") and _is_name(right, "__name__"))
    )


def _is_name(node: ast.AST, ident: str) -> bool:
    return isinstance(node, ast.Name) and node.id == ident


def _is_str(node: ast.AST, value: str) -> bool:
    return isinstance(node, ast.Constant) and node.value == value


def _apply_reachability(
    elements: List[CodeElement], extra_entries: Set[str],
) -> List[CodeElement]:
    by_name: Dict[str, List[CodeElement]] = {}
    for el in elements:
        by_name.setdefault(el.name, []).append(el)
    uid_map = {el.uid: el for el in elements}
    reachable: Set[str] = set()
    queue: List[str] = []
    for el in elements:
        if el.name == "main" or el.kind == "route" or el.name in extra_entries:
            if el.uid not in reachable:
                reachable.add(el.uid)
                queue.append(el.uid)
    while queue:
        uid = queue.pop(0)
        el = uid_map[uid]
        for call in el.calls:
            for callee in by_name.get(call, []):
                if callee.uid not in reachable:
                    reachable.add(callee.uid)
                    queue.append(callee.uid)
    return [
        replace(el, reachable=True) if el.uid in reachable else el
        for el in elements
    ]

"""
Module 100 — the data model.

Three frozen record types cross every module boundary, plus the one text
normalisation everything agrees on.  Provenance is a SET of source tags, not a
single tag; that is what makes disjointness a real relation rather than a
count of distinct channels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import FrozenSet

# Structural words that appear in identifiers but carry no claim content.
STOPLIST = frozenset({
    "get", "set", "the", "and", "for", "handler", "util", "utils", "helper",
    "main", "run", "data", "value", "object", "obj", "impl", "base", "core",
    "py", "self", "cls", "init", "new", "str", "int", "list", "dict",
})

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def sub_tokens(text: str) -> list[str]:
    """
    Normalise an identifier, path or sentence into content sub-tokens.

    Splits on non-alphanumerics and on camelCase boundaries, lowercases, then
    drops single characters and structural words.  Order is preserved and
    duplicates are kept, so callers may count as well as compare.
    """
    out: list[str] = []
    for part in re.split(r"[^A-Za-z0-9]+", text):
        if not part:
            continue
        for piece in _CAMEL.split(part):
            piece = piece.lower()
            if len(piece) > 1 and piece not in STOPLIST:
                out.append(piece)
    return out


@dataclass(frozen=True)
class CodeElement:
    uid: str                    # "pkg.mod:Class.method"
    kind: str                   # function|class|method|route|table|config|test
    name: str
    path: str
    lineno: int
    doc: str
    imports: FrozenSet[str]
    calls: FrozenSet[str]
    body_ops: FrozenSet[str]    # normalised operation vocabulary from the AST
    is_stub: bool
    reachable: bool             # from a declared entry point


@dataclass(frozen=True)
class Claim:
    cid: str
    component: str
    text: str
    kind: str                   # architecture|algorithm|requirement|interface|data
    terms: FrozenSet[str]
    implied_libs: FrozenSet[str]
    section: str


@dataclass(frozen=True)
class Evidence:
    claim: str
    element: str
    channel: str                # NAME|DOC|IMPORT|CALL|SCHEMA|TEST|BODY
    provenance: FrozenSet[str]  # {"ch:NAME", "tok:aes", "file:crypto/aes.py"}
    strength: float             # [0,1]; governs emission only, never disjointness

"""
Module 400 — evidence generation.

The only module that constructs provenance. Seven channels emit one Evidence
per (claim, element, channel) that fires; strength gates emission only.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Set

from .model import Claim, CodeElement, Evidence, sub_tokens

CLAIM_OPS = {
    "encrypts": "op:aead",
    "encrypt": "op:aead", "aes": "op:aead", "gcm": "op:aead", "hashes": "op:hash",
    "hash": "op:hash", "sha256": "op:hash", "signs": "op:mac", "hmac": "op:mac",
    "stores": "op:sql", "queries": "op:sql", "table": "op:sql", "database": "op:sql",
    "parses": "op:regex", "validates": "op:branch", "generates": "op:random",
}

_FIXED = 0.8


def gather(
    claim: Claim,
    elements: Sequence[CodeElement],
    min_strength: float = 0.15,
) -> list[Evidence]:
    out: List[Evidence] = []
    for el in elements:
        out.extend(_for_element(claim, el, elements, min_strength))
    return out


def _for_element(
    claim: Claim,
    el: CodeElement,
    elements: Sequence[CodeElement],
    min_strength: float,
) -> List[Evidence]:
    ev: List[Evidence] = []
    for piece in (
        _name(claim, el),
        _doc(claim, el),
        _import(claim, el),
        _call(claim, el, elements),
        _schema(claim, el),
        _test(claim, el, elements),
        _body(claim, el),
    ):
        if piece is not None and piece.strength >= min_strength:
            ev.append(piece)
    return ev


def _jaccard(a: Set[str], b: Set[str]) -> Optional[float]:
    union = a | b
    if not union:
        return None
    return len(a & b) / len(union)


def _evidence(
    claim: Claim,
    el: CodeElement,
    channel: str,
    provenance: Set[str],
    strength: float,
) -> Evidence:
    return Evidence(
        claim=claim.cid,
        element=el.uid,
        channel=channel,
        provenance=frozenset(provenance),
        strength=strength,
    )


def _name(claim: Claim, el: CodeElement) -> Optional[Evidence]:
    a = set(claim.terms)
    b = set(sub_tokens(el.name + " " + el.path))
    shared = a & b
    strength = _jaccard(a, b)
    if not shared or strength is None:
        return None
    return _evidence(
        claim, el, "NAME",
        {"ch:NAME"} | {f"tok:{t}" for t in shared} | {f"file:{el.path}"},
        strength,
    )


def _doc(claim: Claim, el: CodeElement) -> Optional[Evidence]:
    a = set(claim.terms)
    b = set(sub_tokens(el.doc))
    shared = a & b
    strength = _jaccard(a, b)
    if not shared or strength is None:
        return None
    return _evidence(
        claim, el, "DOC",
        {"ch:DOC"} | {f"tok:{t}" for t in shared} | {f"file:{el.path}"},
        strength,
    )


def _import(claim: Claim, el: CodeElement) -> Optional[Evidence]:
    shared = claim.implied_libs & el.imports
    if not shared:
        return None
    return _evidence(
        claim, el, "IMPORT",
        {"ch:IMPORT"} | {f"lib:{l}" for l in shared} | {f"file:{el.path}"},
        _FIXED,
    )


def _call(
    claim: Claim, el: CodeElement, elements: Sequence[CodeElement],
) -> Optional[Evidence]:
    if not el.reachable:
        return None
    for other in elements:
        if other.uid == el.uid:
            continue
        if el.name in other.calls:
            return _evidence(
                claim, el, "CALL",
                {"ch:CALL", f"file:{other.path}", f"sym:{other.uid}"},
                _FIXED,
            )
    return None


def _schema(claim: Claim, el: CodeElement) -> Optional[Evidence]:
    if el.kind not in {"table", "route"}:
        return None
    a = set(claim.terms)
    b = set(sub_tokens(el.name))
    shared = a & b
    strength = _jaccard(a, b)
    if not shared or strength is None:
        return None
    return _evidence(
        claim, el, "SCHEMA",
        {"ch:SCHEMA"} | {f"tok:{t}" for t in shared} | {f"file:{el.path}"},
        strength,
    )


def _test(
    claim: Claim, el: CodeElement, elements: Sequence[CodeElement],
) -> Optional[Evidence]:
    for other in elements:
        if other.kind == "test" and el.name in other.calls:
            return _evidence(
                claim, el, "TEST",
                {"ch:TEST", f"file:{other.path}", f"sym:{other.uid}"},
                _FIXED,
            )
    return None


def _body(claim: Claim, el: CodeElement) -> Optional[Evidence]:
    if el.is_stub:
        return None
    implied = {CLAIM_OPS[t] for t in claim.terms if t in CLAIM_OPS}
    shared = el.body_ops & implied
    if not shared:
        return None
    return _evidence(
        claim, el, "BODY",
        {"ch:BODY"} | set(shared) | {f"file:{el.path}"},
        _FIXED,
    )

"""
Comparison policies: seven matchers, one signature.

True means the claim is judged implemented. Thresholds and k_min are
swept by the experiment harness; hybrid is the Review 1 proposal
preserved verbatim as a baseline.
"""

from __future__ import annotations

from typing import Callable, Sequence

from .corroborate import corroboration, counterfactual_worst
from .model import Claim, CodeElement, Evidence, sub_tokens


def _jaccard(claim: Claim, el: CodeElement) -> float:
    a = set(claim.terms)
    b = set(sub_tokens(el.name + " " + el.doc + " " + el.path))
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _cosine(claim: Claim, el: CodeElement, embedder) -> float:
    if embedder is None:
        return 0.0
    return embedder.similarity(claim.text, el.name + " " + el.doc)


def lexical(
    claim: Claim,
    elements: Sequence[CodeElement],
    evidence: Sequence[Evidence],
    *,
    embedder=None,
    threshold: float = 0.5,
    k_min: int = 2,
) -> bool:
    best = 0.0
    for el in elements:
        j = _jaccard(claim, el)
        if j > best:
            best = j
    return best >= threshold


def embedding(
    claim: Claim,
    elements: Sequence[CodeElement],
    evidence: Sequence[Evidence],
    *,
    embedder=None,
    threshold: float = 0.5,
    k_min: int = 2,
) -> bool:
    if embedder is None:
        return False
    best = 0.0
    for el in elements:
        s = embedder.similarity(claim.text, el.name + " " + el.doc)
        if s > best:
            best = s
    return best >= threshold


def hybrid(
    claim: Claim,
    elements: Sequence[CodeElement],
    evidence: Sequence[Evidence],
    *,
    embedder=None,
    threshold: float = 0.5,
    k_min: int = 2,
) -> bool:
    best = 0.0
    for el in elements:
        score = 0.5 * _jaccard(claim, el) + 0.5 * _cosine(claim, el, embedder)
        if score > best:
            best = score
    return best >= threshold


def evidence_count(
    claim: Claim,
    elements: Sequence[CodeElement],
    evidence: Sequence[Evidence],
    *,
    embedder=None,
    threshold: float = 0.5,
    k_min: int = 2,
) -> bool:
    return len(evidence) >= k_min


def channel_count(
    claim: Claim,
    elements: Sequence[CodeElement],
    evidence: Sequence[Evidence],
    *,
    embedder=None,
    threshold: float = 0.5,
    k_min: int = 2,
) -> bool:
    return len({e.channel for e in evidence}) >= k_min


def cdc(
    claim: Claim,
    elements: Sequence[CodeElement],
    evidence: Sequence[Evidence],
    *,
    embedder=None,
    threshold: float = 0.5,
    k_min: int = 2,
) -> bool:
    return corroboration(evidence) >= k_min


def cdc_counterfactual(
    claim: Claim,
    elements: Sequence[CodeElement],
    evidence: Sequence[Evidence],
    *,
    embedder=None,
    threshold: float = 0.5,
    k_min: int = 2,
) -> bool:
    return counterfactual_worst(evidence)[0] >= k_min


POLICIES: dict[str, Callable] = {
    "lexical": lexical,
    "embedding": embedding,
    "hybrid": hybrid,
    "evidence_count": evidence_count,
    "channel_count": channel_count,
    "cdc": cdc,
    "cdc_counterfactual": cdc_counterfactual,
}

POLICY_LABELS: dict[str, str] = {
    "lexical": "Lexical overlap",
    "embedding": "TF-IDF cosine",
    "hybrid": "Structural + semantic (Review 1)",
    "evidence_count": "Evidence count",
    "channel_count": "Channel count",
    "cdc": "Corroboration C",
    "cdc_counterfactual": "Corroboration + counterfactual",
}

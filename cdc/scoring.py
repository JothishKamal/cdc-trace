"""
Module 600 — scoring.

Three-level verdicts from corroboration and counterfactual ablation, then
per-claim results aggregated to component and document gap scores.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from .corroborate import corroboration, counterfactual_worst
from .evidence import gather
from .model import Claim, CodeElement

_CAP = 24


def verdict(evidence, k_min: int = 2) -> str:
    c = corroboration(evidence)
    if c < k_min:
        return "UNSUPPORTED"
    worst, _ = counterfactual_worst(evidence)
    return "SUPPORTED" if worst >= k_min else "WEAK"


@dataclass(frozen=True)
class ClaimResult:
    cid: str
    component: str
    verdict: str
    c: int
    worst_c: int
    worst_source: str
    n_evidence: int
    capped: bool


@dataclass(frozen=True)
class GapReport:
    results: list[ClaimResult]
    by_component: dict[str, float]
    gap_score: float


def score_document(
    claims: Sequence[Claim],
    elements: Sequence[CodeElement],
    k_min: int = 2,
) -> GapReport:
    results: list[ClaimResult] = []
    for claim in claims:
        evidence = gather(claim, elements)
        c = corroboration(evidence)
        worst_c, worst_source = counterfactual_worst(evidence)
        results.append(ClaimResult(
            cid=claim.cid,
            component=claim.component,
            verdict=verdict(evidence, k_min),
            c=c,
            worst_c=worst_c,
            worst_source=worst_source,
            n_evidence=len(evidence),
            capped=len(evidence) > _CAP,
        ))
    n = len(results)
    gap_score = (
        sum(1 for r in results if r.verdict != "SUPPORTED") / n if n else 0.0
    )
    grouped: dict[str, list[ClaimResult]] = defaultdict(list)
    for r in results:
        grouped[r.component].append(r)
    by_component = {
        comp: sum(1 for r in rs if r.verdict != "SUPPORTED") / len(rs)
        for comp, rs in grouped.items()
    }
    return GapReport(
        results=results, by_component=by_component, gap_score=gap_score,
    )

"""
Module 500 — the corroboration engine.

Three operations, and they are the substance of the method:

  510  dependency classification
         Two pieces of evidence are dependent when their provenance sets
         intersect, i.e. when one signal can move both of them.

  520  corroboration quantity  C(claim)
         The size of the largest set of evidence whose provenance sets are
         PAIRWISE DISJOINT.  This is a maximum independent set in the conflict
         graph whose edges are shared provenance.  It is the number of
         genuinely separate reasons to believe a claim, not the number of
         agreeing matches.

  530  counterfactual source ablation
         For every provenance source present, delete all evidence touching it
         and recompute C.  A verdict must survive the loss of any one source.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

from .model import Evidence


# --------------------------------------------------------------------- 510
def dependency_components(evidence: Sequence[Evidence]) -> List[List[int]]:
    """
    Partition evidence indices by the transitive closure of 'shares a
    provenance source'.  Reported in the evidence bundle for explanation; the
    verdict itself uses the stricter pairwise-disjoint measure below, because
    transitive closure over-merges (a shares X with b, b shares Y with c, yet
    a and c are disjoint).
    """
    n = len(evidence)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        for j in range(i + 1, n):
            if evidence[i].provenance & evidence[j].provenance:
                union(i, j)

    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values()]


# --------------------------------------------------------------------- 520
def _conflict_masks(evidence: Sequence[Evidence]) -> List[int]:
    n = len(evidence)
    masks = [0] * n
    for i in range(n):
        for j in range(n):
            if i != j and (evidence[i].provenance & evidence[j].provenance):
                masks[i] |= 1 << j
    return masks


def _max_independent_set(masks: List[int], n: int) -> Tuple[int, int]:
    """
    Exact maximum independent set by branch and bound (n is small: <= 24).
    Returns (size, bitmask of one optimal set).
    """
    if n == 0:
        return 0, 0
    best, best_set = 0, 0

    def expand(candidates: int, chosen: int, size: int) -> None:
        nonlocal best, best_set
        if candidates == 0:
            if size > best:
                best, best_set = size, chosen
            return
        if size + bin(candidates).count("1") <= best:
            return
        # Pivot on the highest-degree vertex inside the candidate set.
        pivot, pivot_deg = -1, -1
        c = candidates
        while c:
            v = (c & -c).bit_length() - 1
            c &= c - 1
            deg = bin(masks[v] & candidates).count("1")
            if deg > pivot_deg:
                pivot, pivot_deg = v, deg
        # Branch: take the pivot, or drop it.
        expand(candidates & ~masks[pivot] & ~(1 << pivot),
               chosen | (1 << pivot), size + 1)
        expand(candidates & ~(1 << pivot), chosen, size)

    expand((1 << n) - 1, 0, 0)
    return best, best_set


def witness_set(evidence: Sequence[Evidence], cap: int = 24) -> List[int]:
    """
    Indices of one maximum pairwise provenance-disjoint evidence set.  This
    exact set is what the gap report carries, so a reader can audit which
    independent reasons the verdict rested on.
    """
    idx = list(range(len(evidence)))
    if len(idx) > cap:                      # bounded work; the cap is recorded
        idx = idx[:cap]
    sub = [evidence[i] for i in idx]
    masks = _conflict_masks(sub)
    _, bits = _max_independent_set(masks, len(sub))
    return [idx[k] for k in range(len(sub)) if bits >> k & 1]


def corroboration(evidence: Sequence[Evidence], cap: int = 24) -> int:
    """C(claim): the number of mutually independent reasons to believe it."""
    return len(witness_set(evidence, cap))


# --------------------------------------------------------------------- 530
def sources(evidence: Iterable[Evidence]) -> List[str]:
    out: set[str] = set()
    for e in evidence:
        out |= set(e.provenance)
    return sorted(out)


def ablate(evidence: Sequence[Evidence], source: str) -> List[Evidence]:
    """Every piece of evidence that does not touch `source`."""
    return [e for e in evidence if source not in e.provenance]


def counterfactual_worst(evidence: Sequence[Evidence],
                         cap: int = 24) -> Tuple[int, str]:
    """
    Return (worst C after losing any one source, the source responsible).

    A claim supported only because one identifier appears in several places is
    caught here: removing that one token collapses its corroboration.
    """
    srcs = sources(evidence)
    if not srcs:
        return 0, ""
    worst, worst_src = 10 ** 6, srcs[0]
    for s in srcs:
        c = corroboration(ablate(evidence, s), cap)
        if c < worst:
            worst, worst_src = c, s
    return worst, worst_src

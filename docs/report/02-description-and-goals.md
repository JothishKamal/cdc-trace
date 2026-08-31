# Description and Goals

## Literature Review

Traceability is the ability to describe and follow the life of a requirement in both a forwards and backwards direction [6]. Gotel and Finkelstein framed the *requirements traceability problem* as a pre-requirements-specification problem of who contributed what, and why [6]. Subsequent surveys treat software traceability as a first-class concern spanning recovery, maintenance, and use [7], [10].

Automated recovery of candidate links has a long IR lineage. Hayes, Dekhtyar, and Sundaram studied candidate-link generation methods and established the precision/recall trade-off that still organises evaluation [8]. De Lucia, Fasano, Oliveto, and Tortora applied IR inside artefact-management systems [9]. Antoniol et al. recovered links between code and documentation with probabilistic IR [11]. Those methods answer *which artefacts are similar*, not *whether a claim is independently implemented*.

Recent work applies neural and LLM techniques to the same recovery task. Keim, Corallo, Fuchß, Hey, Telge, and Koziolek recover trace links between software documentation and code [1]. Fuchß et al. propose LiSSA, a retrieval-augmented generation approach toward generic TLR [2]. Alturayeif, Hassine, and Ahmad survey machine-learning approaches for automated software traceability [3]. Baumgärtner (2026) and Cao (2025) continue the LLM-for-traceability / TLR line as publicly described [4], [5]. Across this line, the operating assumption remains that a recovered link is evidence of implementation. The stub that shares an identifier with the claim is a recovered link. It is not an implementation.

The Review 1 proposal in this project was a hybrid of structural overlap and semantic similarity. That matcher is retained verbatim as the `hybrid` baseline. The present method does not replace TLR; it asks a stricter question of the evidence TLR-style matchers already emit.

## Research Gap

TLR, embeddings, and LLMs can agree that a claim is implemented for one shared reason — typically an identifier or a docstring that restates it. Counting distinct channels does not close the gap: `NAME` and `DOC` often share tokens and files, so channel-count treats dependent signals as independent witnesses. Connected components over-merge: two pieces of evidence may share a token with a third while remaining disjoint from each other.

No prior TLR method in the reviewed literature counts only mutually independent, provenance-disjoint evidence, or requires a verdict to survive ablation of any single source. That is the gap this project addresses.

## Objectives

1. Extract claims from Markdown and LaTeX and extract a Python code inventory (AST, call graph, routes, schema, tests) without network access at run time.
2. Emit seven provenance-tagged evidence channels and compute `C(claim)` as a maximum independent set over set-valued provenance.
3. Apply counterfactual source ablation and produce `SUPPORTED` / `WEAK` / `UNSUPPORTED` verdicts with document-level gap scores.
4. Compare CDC policies against lexical, embedding, hybrid (Review 1), evidence-count, and channel-count baselines on a labelled mutation corpus (E0–E6), reporting Wilson 95% intervals.
5. Align the work with **SDG 4** (Quality Education) — making claim–code gaps inspectable in student theses — and **SDG 9** (Industry, Innovation and Infrastructure) — a deterministic, offline method for implementation-evidence audit.
6. Prepare a planned peer-reviewed / Scopus-indexed conference paper on channel-disjoint corroboration for traceability-gap detection.

## Problem Statement

Given a claims document and a Python code archive, decide for each claim whether independent implementation evidence exists, and localise claims that are supported only by correlated signals (names, restated docstrings) or not at all. Do this deterministically, offline, and with labels that are known by construction under mutation.

## Project Plan

| Phase | Work | Status |
|---|---|---|
| Foundation | Data model (100), corroboration engine (500) | Done |
| Extraction | Code AST (200), claims Markdown/LaTeX (300) | Done |
| Evidence | Seven channels (400), scoring and policies (600) | Done |
| Evaluation | Mutation operators (700), corpus, E0–E6, figures (800) | Done |
| This review | README, draft report, slides, demo script | This deliverable |
| Final Review | Live LLM backend, corpus scale-up, cross-language, oral probe | Deferred |

Seed `20260902`, `k_min = 2`. Experiments write `results/results.json`; `python experiments/report.py` prints the tables cited in this draft.

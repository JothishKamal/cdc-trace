# Technical Specification

## Functional Requirements

| ID | Requirement |
|---|---|
| FR-1 | Extract `CodeElement` inventory from a Python tree: functions, classes, methods, routes, schema, imports, call graph, reachability, stub detection. |
| FR-2 | Extract `Claim` lists from Markdown and LaTeX behind one interface; equivalent input must agree. |
| FR-3 | Emit evidence on seven channels (`NAME`, `DOC`, `IMPORT`, `CALL`, `SCHEMA`, `TEST`, `BODY`) with set-valued provenance (`ch:`, `tok:`, `file:`, `lib:`, `sym:`, `op:`). |
| FR-4 | Compute `C(claim)` as the size of a maximum pairwise-disjoint evidence set (exact branch-and-bound, cap 24). |
| FR-5 | Ablate each provenance source and recompute `C`; report worst-case `C` and the responsible source. |
| FR-6 | Verdicts: `SUPPORTED` if `C ≥ k_min` and worst ablated `C ≥ k_min`; `WEAK` if only the first holds; `UNSUPPORTED` otherwise. Default `k_min = 2`. |
| FR-7 | Aggregate claim verdicts to component and document gap scores. |
| FR-8 | Compare policies behind one signature: `lexical`, `embedding`, `hybrid`, `evidence_count`, `channel_count`, `cdc`, `cdc_counterfactual`. |
| FR-9 | Inject labelled mutations (`DELETE`, `RENAME`, `WEAKEN`, `STUB`, `NOMINAL`) on a copy of the corpus; never modify the pristine tree. |
| FR-10 | Run E0–E6 from a single seed, write `results/results.json`, print Wilson-interval tables, write `assets/fig1.png`–`fig6.png`. |

Non-goals (not requirements): plagiarism detection, grading, code-quality judgement, proofs of correctness, live network calls.

## Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | Python 3.11+. Standard library plus `numpy>=1.24` and `matplotlib>=3.7` only. |
| NFR-2 | No network access in `cdc/`, `experiments/`, `figures/`, or `tests/`. The demo runs offline. |
| NFR-3 | Deterministic: global `SEED = 20260902` for every random draw. |
| NFR-4 | Frozen dataclasses. Disjointness is plain set intersection, never strength-weighted. |
| NFR-5 | Tests runnable as `python tests/test_….py` and pytest-compatible; no required test framework. |
| NFR-6 | Evidence per claim capped at 24; the cap is recorded when it binds. |
| NFR-7 | Wilson 95% intervals on reported rates so sample size is visible. |

## Feasibility

**Technical.** Python `ast` is sufficient for the inventory. Maximum independent set on at most 24 vertices is exact and cheap. TF-IDF cosine needs only numpy. Mutation labels are by construction, so precision and recall are well-defined on the gap class.

**Operational.** The demo needs no GPU, no API key, and no network. `python experiments/report.py` reprints tables from committed `results/results.json`.

**Schedule.** In-scope modules 100–800 are implemented. The four Final Review items are deferred by design, which keeps this review inside a 60–75% completion band that can be checked against the tree.

**Risks (stated, not buried).** Ground truth is mutation-injected and encodes our assumptions. Channel independence is an assumption. `BODY` analysis is shallow. The default embedder is a lexical-semantic proxy. The corpus is small. Python only.

## Hardware and Software Specification

**Hardware (minimum).** A laptop or desktop able to run CPython 3.11; no discrete GPU required. Disk enough for the repository, `results/results.json`, and six PNG figures.

**Software.**

| Item | Specification |
|---|---|
| Language | Python 3.11+ |
| Runtime libraries | numpy ≥ 1.24, matplotlib ≥ 3.7 (`requirements.txt`) |
| Code analysis | Python standard-library `ast` |
| Embedder (baselines) | TF-IDF over identifier sub-tokens, cosine similarity |
| OS | Any OS that runs CPython 3.11 (developed and demoed on Windows) |
| Network | Not used at run time |

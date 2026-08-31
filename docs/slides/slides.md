# Review 2 slides

Thirteen sections. Title of the project is fixed.

## title

**Traceability-Gap Detection Between Student Code and Thesis Claims**

Channel-disjoint corroboration: a claim is implemented only when mutually independent, provenance-disjoint evidence survives the loss of any single source.

## guide approval

- Project title (fixed at Review 1): *Traceability-Gap Detection Between Student Code and Thesis Claims*
- Method name: channel-disjoint corroboration (CDC)
- Review 1 proposal retained as the `hybrid` baseline (structural overlap + semantic similarity)
- This review: working pipeline, mutation corpus, E0–E6, figures, draft report, demo
- Guide sign-off requested on: in-scope modules 100–800 complete; four items deferred to Final Review (listed on Conclusion)

## Aim

Decide, for each claim in a thesis-style document, whether the Python code supplies **independent** implementation evidence — not merely a similar identifier — and localise claims that fail that test.

## Abstract

Traceability-link recovery treats resemblance as implementation. A stub named `aes_gcm_encrypt_token` fools lexical matching, embeddings, and an LLM for one shared reason: the identifier. This project tags evidence with set-valued provenance across seven channels, counts only a maximum pairwise-disjoint set `C(claim)`, and requires the count to survive ablating any single source. Evaluation is mutation-injected (labels by construction). Numbers below are copied from `python experiments/report.py`. `cdc_counterfactual` does **not** have the lowest false-implemented rate; E0 best-F1 on a rare gap class lands high lexical/hybrid/embedding thresholds, so those policies rarely predict implemented.

## Literature Review

- Gotel & Finkelstein: the requirements traceability problem [6]
- Hayes / De Lucia / Antoniol: IR candidate-link recovery [8], [9], [11]
- Cleland-Huang et al.; Spanoudakis & Zisman: surveys and roadmap [7], [10]
- Keim 2024: documentation–code trace links [1]
- Fuchß 2025: LiSSA — RAG for generic TLR [2]
- Alturayeif 2025: ML for automated traceability, SLR [3]
- Baumgärtner 2026, Cao 2025: LLM-for-traceability / TLR as publicly described [4], [5]

Shared limit: a recovered link is not independent implementation evidence.

## Research Gap

Matchers can agree because they share one signal. Channel-count still treats `NAME` and `DOC` as independent when they share tokens and files. Connected components over-merge disjoint witnesses. Missing: count only provenance-disjoint evidence, and require the verdict to survive deleting any one source.

## Objectives

1. Extract claims (Markdown/LaTeX) and Python code; emit seven provenance-tagged channels.
2. Compute `C(claim)` (maximum independent set) and counterfactual ablation; verdict `SUPPORTED` / `WEAK` / `UNSUPPORTED`.
3. Compare CDC to lexical, embedding, hybrid (Review 1), evidence-count, and channel-count on labelled mutations (E0–E6, Wilson intervals).
4. **SDG 4** Quality Education — inspectable claim–code gaps in student theses.
5. **SDG 9** Industry, Innovation and Infrastructure — deterministic, offline implementation-evidence audit.
6. Outcome: a planned peer-reviewed / Scopus-indexed conference paper on channel-disjoint corroboration.

## Framework/Architecture

```
claims document --[300]-->          +--> [400] evidence (7 channels)
code archive    --[200]-->          |
                                    v
                            [500] C(claim) + ablation
                                    v
                            [600] verdicts + policies
                                    ^
                            [700] mutations --> [800] E0–E6
```

`C` = size of the largest pairwise-disjoint evidence set. Strength is emission-only.

## Functional Requirements

- FR-1/2 Extract code (AST, graph, stubs) and claims (md/tex).
- FR-3 Seven channels, set-valued provenance.
- FR-4 Exact `C(claim)`, cap 24.
- FR-5 Counterfactual source ablation.
- FR-6 Three-level verdicts, `k_min = 2`.
- FR-7 Gap scores (claim → component → document).
- FR-8 Seven policies, one signature.
- FR-9 Five mutation operators on a copy.
- FR-10 E0–E6, Wilson tables, fig1–fig6.
- Offline; no grading, plagiarism, or live LLM.

## Modules

| ID | File | Role |
|---|---|---|
| 100 | `cdc/model.py` | `Claim`, `CodeElement`, `Evidence`; sub-tokens |
| 200 | `cdc/codebase.py` | AST inventory, call graph, routes, schema |
| 300 | `cdc/claims.py` | Markdown and LaTeX claim extraction |
| 400 | `cdc/evidence.py` | Seven channels, provenance |
| 500 | `cdc/corroborate.py` | Dependency graph, exact `C`, ablation |
| 600 | `cdc/scoring.py`, `cdc/policies.py` | Verdicts, gap scores, policies |
| 700 | `cdc/mutate.py` | `DELETE` `RENAME` `WEAKEN` `STUB` `NOMINAL` |
| 800 | `experiments/`, `figures/` | E0–E6, `results.json`, plots |

## Experiments and Results

Copied from `python experiments/report.py` (`seed=20260902`, `k_min=2`; thresholds `channel_count` 4, `embedding` 0.6, `evidence_count` 4, `hybrid` 0.5, `lexical` 0.4).

```
=== E1 main comparison (held-out, gap class) ===
policy                    prec % (95% CI)     rec % (95% CI)     F1     FIR % (95% CI)
cdc                    100.00 ( 51.0-100.0)  23.53 (  9.6- 47.3)  38.10  76.47 ( 52.7- 90.4)
cdc_counterfactual      40.00 ( 16.8- 68.7)  23.53 (  9.6- 47.3)  29.63  76.47 ( 52.7- 90.4)
channel_count           50.00 ( 23.7- 76.3)  29.41 ( 13.3- 53.1)  37.04  70.59 ( 46.9- 86.7)
embedding               21.54 ( 13.3- 33.0)  82.35 ( 59.0- 93.8)  34.15  17.65 (  6.2- 41.0)
evidence_count          80.00 ( 37.6- 96.4)  23.53 (  9.6- 47.3)  36.36  76.47 ( 52.7- 90.4)
hybrid                  21.13 ( 13.2- 32.0)  88.24 ( 65.7- 96.7)  34.09  11.76 (  3.3- 34.3)
lexical                 20.51 ( 13.0- 30.8)  94.12 ( 73.0- 99.0)  33.68   5.88 (  1.0- 27.0)
```

`cdc_counterfactual` does not have the lowest FIR. Lowest E1 FIR is `lexical` 5.88% (1.0-27.0), then `hybrid` 11.76% (3.3-34.3), then `embedding` 17.65% (6.2-41.0). `cdc` and `cdc_counterfactual` are both 76.47% (52.7-90.4). Identifier-ablation curves: `assets/fig4.png`.

## Conclusion

**Done (checkable):** modules 100–800, corpus, E0–E6, figures, tests, README, these slides.

**Deferred — planned Final Review work:** live LLM backend; corpus scale-up; cross-language extraction; oral-probe generation. None of those four is implemented in this tree.

**Completion: 60–75%.** In-scope Review 2 work is present; the four Final Review items are absent. That split is explicit and checkable.

**Limitations:** mutation-injected ground truth; channel independence assumed; shallow `BODY`; TF-IDF proxy embedder; small corpus (Wilson intervals); Python only.

## References

[1] Keim et al., ICSE 2024, doi: 10.1145/3597503.3639130.
[2] Fuchß et al., LiSSA, ICSE 2025, doi: 10.1109/ICSE55347.2025.00186.
[3] Alturayeif et al., JSS 230, 2025, doi: 10.1016/j.jss.2025.112536.
[4] Baumgärtner, LLM-for-traceability / TLR, 2026 (as publicly described).
[5] Cao, LLM-for-traceability / TLR, 2025 (as publicly described).
[6] Gotel and Finkelstein, ICRE 1994, doi: 10.1109/ICRE.1994.292398.
[7] Cleland-Huang et al., FOSE/ICSE 2014, doi: 10.1145/2593882.2593891.
[8] Hayes, Dekhtyar, and Sundaram, IEEE TSE 32(1), 2006, doi: 10.1109/TSE.2006.3.
[9] De Lucia et al., ACM TOSEM 16(4), 2007, doi: 10.1145/1276933.1276934.
[10] Spanoudakis and Zisman, *Handbook of SEKE*, vol. 3, 2005.

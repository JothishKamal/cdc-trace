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

Traceability-link recovery treats resemblance as implementation. A stub named `aes_gcm_encrypt_token` fools lexical matching, embeddings, and an LLM for one shared reason: the identifier. This project tags evidence with set-valued provenance across seven channels, counts only a maximum pairwise-disjoint set `C(claim)`, and requires the count to survive ablating any single source. Evaluation is mutation-injected (labels by construction) at (claim, element) granularity. Numbers below are copied from `python experiments/report.py`. Headline: on the `NOMINAL` mutation — name and docstring kept, body gutted — `lexical`, `embedding` and `hybrid` separate pristine from gutted by **exactly 0.0 points** — guaranteed by construction, since those policies read only name, docstring and path and `NOMINAL` leaves all three unchanged — while `cdc` separates by **100.0**. Our first evaluation was mis-specified and reported the opposite; it has been corrected and the mis-specification is disclosed below.

## Literature Review

- Gotel & Finkelstein: the requirements traceability problem [6]
- Hayes / De Lucia / Antoniol: IR candidate-link recovery [8], [9], [11]
- Cleland-Huang et al.; Spanoudakis & Zisman: surveys and roadmap [7], [10]
- Keim 2024: documentation–code trace links [1]
- Fuchß 2025: LiSSA — RAG for generic TLR [2]
- Alturayeif 2025: ML for automated traceability, SLR [3]
- Hey, Keim, and Corallo 2024: requirements classification for TLR [4]
- Marcus and Maletic 2003: documentation–code links via LSI [5]

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

Copied from `python experiments/report.py` (`seed=20260902`, `k_min=2`; thresholds `channel_count` 3, `embedding` 0.1, `evidence_count` 3, `hybrid` 0.1, `lexical` 0.1). Evaluation is at (claim, element) granularity: one pair per claim that had evidence on that element before mutation.

**Primary comparison — pristine versus gutted.** A policy that accepts nothing scores a low false-implemented rate without any skill, so a false-implemented rate on its own is not evidence. Only the gap between *accepts the pristine element* and *accepts the same element after mutation* is skill. That gap is why separation, not FIR, is the reported number.

```
[NOMINAL]  n = 49 mutated pairs
------------------------------------------------------------------------------------------------
policy                  accepts pristine % (95% CI)    accepts gutted % (95% CI)  sep. pp
lexical                         75.51 ( 61.9- 85.4)          75.51 ( 61.9- 85.4)      0.0
embedding                       79.59 ( 66.4- 88.5)          79.59 ( 66.4- 88.5)      0.0
hybrid                          77.55 ( 64.1- 87.0)          77.55 ( 64.1- 87.0)      0.0
evidence_count                  91.84 ( 80.8- 96.8)          14.29 (  7.1- 26.7)     77.6
channel_count                   91.84 ( 80.8- 96.8)          14.29 (  7.1- 26.7)     77.6
cdc                            100.00 ( 92.7-100.0)           0.00 (  0.0-  7.3)    100.0
cdc_counterfactual              79.59 ( 66.4- 88.5)           0.00 (  0.0-  7.3)     79.6
```

`lexical`, `embedding` and `hybrid` separate `NOMINAL` by **exactly 0.0 pp** — the identical number in both columns. They accept a gutted function at precisely the rate they accept a working one, so they carry no information about whether the body exists. `cdc` separates it by **100.0**. This is not an artefact of threshold choice, and the reason is stronger than a sweep: it is guaranteed **by construction**. `lexical`, `embedding` and `hybrid` read only `el.name`, `el.doc` and `el.path` (`cdc/policies.py`) and never read the `k_min` they accept; `NOMINAL` leaves those three fields byte-for-byte unchanged, so each computes the identical score on both sides and separates exactly 0.0 at every threshold and every `k_min`.

Separation (pp) across all five operators, n = 49 / 40 / 19 / 29 / 32 mutated pairs:

| policy | NOMINAL | STUB | WEAKEN | RENAME | DELETE † |
|---|---:|---:|---:|---:|---:|
| `lexical` | 0.0 | 20.0 | 0.0 | 0.0 | 81.2 |
| `embedding` | 0.0 | 35.0 | 0.0 | 0.0 | 93.8 |
| `hybrid` | 0.0 | 30.0 | 0.0 | 3.4 | 90.6 |
| `evidence_count` | 77.6 | 75.0 | 5.3 | 86.2 | 100.0 |
| `channel_count` | 77.6 | 75.0 | 5.3 | 86.2 | 100.0 |
| `cdc` | 100.0 | 77.5 | 0.0 | 100.0 | 100.0 |
| `cdc_counterfactual` | 79.6 | 72.5 | 15.8 | 100.0 | 100.0 |

† `DELETE` removes the element from the tree entirely, so its gutted column is 0.0 for all seven policies by construction and its pairs are free true positives — a sanity check, not evidence. Its n here (32, over all pairs) is a different population from the 13 DELETE pairs in the E1 test split below.

**Secondary — E1 pair-level.**

```
=== E1 pair-level comparison (gap class) ===
n = 431 (claim, element) pairs; 68 carry a gap-inducing mutation
policy                    prec % (95% CI)     rec % (95% CI)     F1     FIR % (95% CI)
lexical                 33.03 ( 24.9- 42.3)  52.94 ( 41.2- 64.3)  40.68  47.06 ( 35.7- 58.8)
embedding               38.37 ( 28.8- 48.9)  48.53 ( 37.1- 60.2)  42.86  51.47 ( 39.8- 62.9)
hybrid                  38.46 ( 29.1- 48.7)  51.47 ( 39.8- 62.9)  44.03  48.53 ( 37.1- 60.2)
evidence_count          25.68 ( 20.4- 31.8)  83.82 ( 73.3- 90.7)  39.31  16.18 (  9.3- 26.7)
channel_count           25.68 ( 20.4- 31.8)  83.82 ( 73.3- 90.7)  39.31  16.18 (  9.3- 26.7)
cdc                     28.70 ( 23.2- 35.0)  94.12 ( 85.8- 97.7)  43.99   5.88 (  2.3- 14.2)
cdc_counterfactual      26.32 ( 21.2- 32.1)  95.59 ( 87.8- 98.5)  41.27   4.41 (  1.5- 12.2)

The 60/40 split is not group-aware: the same (project, cid, uid) pair can
appear on both sides of it across mutation rounds, so E1 is optimistic and
is not a held-out result. The primary artifact is the E2b separation table
below, which is not split-based.
```

`cdc` and `cdc_counterfactual` hold the two highest recalls and the two lowest false-implemented rates, which is the ordering the method predicts and the opposite of what our first evaluation reported. (The caveat printed with that table says the separation table is "below" it, which is where `report.py` prints it; on this slide it is above.) E1 is **not** a held-out result: the 60/40 split is not group-aware, so E1 is optimistic by an unmeasured amount. The primary artifact is the separation table above, which is not split-based.

**E3 identifier ablation (`assets/fig4.png`).** Renaming a growing fraction of function
and class names to opaque tokens, then re-running the same `NOMINAL` separation:

| policy | 0.00 | 0.25 | 0.50 | 0.75 | 1.00 |
|---|---:|---:|---:|---:|---:|
| `lexical` / `embedding` / `hybrid` | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `evidence_count` / `channel_count` | 80.6 | 55.0 | 35.1 | 25.5 | 7.7 |
| `cdc` | 95.5 | 66.0 | 54.6 | 33.0 | 15.4 |
| `cdc_counterfactual` | 89.6 | 47.0 | 30.9 | 0.0 | 0.0 |

Separation in pp; n = 67, 100, 97, 94, 65 mutated pairs. This one does **not** flatter the
method: `cdc` separation falls monotonically as identifiers are destroyed, because `NAME`
is one of the seven channels and wholesale renaming genuinely removes evidence the method
uses. What it does not do is make corroboration wrong — `cdc`'s accepts-gutted column is
0.00% at every ablation level, so the method goes silent rather than accepting a gutted
body, and at full ablation it still separates by 15.4 pp where every lexical baseline
separates by 0.0.

**Disclosed costs.**

- The original claim-level evaluation was mis-specified: it marked a claim as a gap whenever its single lexical best-match element was mutated, but 141 of 161 such claims are still implemented by other elements. It understated every evidence-based policy. Corrected here; the old table is retained in the README as a captioned diagnostic.
- `WEAKEN` is the weak operator for the method: `cdc` separates it by 0.0 pp (n = 19) and `cdc_counterfactual` beats `cdc` there at 15.8 pp. `mutate.py` maps `sha256` to `md5` and `codebase.py` maps `md5` to `op:hash_weak` instead of dropping the operation, so `BODY` still fires after the algorithm is weakened — a limit of the operation vocabulary, not a bug.
- Corroboration degrades under wholesale identifier renaming: `cdc` separation on `NOMINAL` falls from 95.5 pp to 15.4 pp between 0.00 and 1.00 ablation (E3 above). `NAME` is one of the seven channels, so removing every identifier removes evidence the method uses. The loss is entirely in accepts-pristine; accepts-gutted stays at 0.00%.
- The counterfactual costs acceptance of legitimate code: `cdc_counterfactual` accepts 79.59% of pristine `NOMINAL` pairs against `cdc`'s 100.00%, because `ledger schema:connect_memory` is called but has no test calling it, so ablating `ch:CALL` collapses it. `cdc_counterfactual` is the stricter policy and the wrong default on thinly tested codebases; `cdc` is the better default.

## Conclusion

**Finding.** At (claim, element) granularity on the `NOMINAL` mutation — name and docstring kept, body gutted — `lexical`, `embedding` and `hybrid` separate pristine from gutted by **exactly 0.0 pp**: they accept a gutted function at precisely the rate they accept a working one, so they carry no information about whether the body exists. That 0.0 is guaranteed by construction, not found by a grid search: those three policies read only name, docstring and path (they take a `k_min` and never read it) and `NOMINAL` leaves all three byte-for-byte unchanged, so they compute the identical score on both sides at every threshold and every `k_min`. Channel-disjoint corroboration separates the same mutation by **100.0 pp**, and on E1 `cdc` and `cdc_counterfactual` hold the two highest recalls (94.12% and 95.59%) together with the two lowest false-implemented rates (5.88% and 4.41%), against `lexical`'s 47.06%.

**Correction we made to our own evaluation.** The first evaluation was mis-specified. It labelled at claim level, marking a claim as a gap whenever its single lexical best-match element was mutated, while 141 of 161 such claims remain genuinely implemented by other elements. Those labels understated every evidence-based policy and made the published table contradict the method's own claim. The corrected evaluation labels at (claim, element) granularity; the mis-specified table is retained in the README as a captioned diagnostic rather than deleted.

**Limitations, stated up front:**

- `WEAKEN` is the method's weak operator: `cdc` separates it by 0.0 pp (n = 19), and `cdc_counterfactual` beats `cdc` there at 15.8 pp. Cause: `sha256` maps to `md5`, which the operation vocabulary keeps as `op:hash_weak` rather than dropping, so `BODY` still fires.
- `cdc_counterfactual` costs acceptance of legitimate code: 79.59% of pristine `NOMINAL` pairs against `cdc`'s 100.00%, driven by one called-but-untested element. It is the stricter policy and the wrong default on thinly tested codebases; `cdc` is the better default.
- Identifier ablation costs the method real ground: `cdc` separation on `NOMINAL` falls from 95.5 pp at 0.00 ablation to 15.4 pp at 1.00. It goes silent rather than wrong — accepts-gutted stays at 0.00% throughout — but a fully obfuscated codebase is one this method has much less to say about.
- E1 is not held out: the 60/40 split is not group-aware, so it is optimistic by an unmeasured amount. The separation table is the primary artifact and is not split-based.
- `DELETE` is degenerate: its gutted column is 0.0 for all seven policies by construction and its pairs are free true positives.
- `CALL` and `TEST` emit only when the callee is not a stub and another channel already fired, so `NOMINAL` can demote a claim; this is current `gather` behaviour, not the original spec table.
- Also: mutation-injected ground truth; channel independence assumed; shallow `BODY`; TF-IDF proxy embedder; small corpus (Wilson intervals throughout); Python only.

**Deferred — planned Final Review work:** live LLM backend; corpus scale-up; cross-language extraction; oral-probe generation. None of those four is implemented in this tree.

**Done (checkable):** modules 100–800, corpus, E0–E6, figures, tests, README, these slides. **Completion: 60–75%.** In-scope work is present; the four deferred items are absent. That split is explicit and checkable.

## References

[1] Keim et al., ICSE 2024, doi: 10.1145/3597503.3639130.
[2] Fuchß et al., LiSSA, ICSE 2025, doi: 10.1109/ICSE55347.2025.00186.
[3] Alturayeif et al., JSS 230, 2025, doi: 10.1016/j.jss.2025.112536.
[4] T. Hey, J. Keim, and S. Corallo, RE 2024, doi: 10.1109/RE59067.2024.00024.
[5] A. Marcus and J. I. Maletic, ICSE 2003, doi: 10.1109/ICSE.2003.1201194.
[6] Gotel and Finkelstein, ICRE 1994, doi: 10.1109/ICRE.1994.292398.
[7] Cleland-Huang et al., FOSE/ICSE 2014, doi: 10.1145/2593882.2593891.
[8] Hayes, Dekhtyar, and Sundaram, IEEE TSE 32(1), 2006, doi: 10.1109/TSE.2006.3.
[9] De Lucia et al., ACM TOSEM 16(4), 2007, doi: 10.1145/1276933.1276934.
[10] Spanoudakis and Zisman, *Handbook of SEKE*, vol. 3, 2005.

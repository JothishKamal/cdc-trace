# Introduction

**Project title:** Traceability-Gap Detection Between Student Code and Thesis Claims

## Background

A claims document — a thesis, a design document, an architecture README — asserts that a system does certain things. The source code either does them or it does not. Deciding which, by hand, is slow and subjective, and it does not scale.

Automated traceability-link recovery (TLR) already exists and is mature [1]–[10]. Information-retrieval matchers, embedding similarity, and large language models all recover candidate links between documentation and code. The failure they do not address is this: **a claim is not implemented merely because some code resembles it.**

Consider a document claiming *"AES-GCM encrypts the session token"* against:

```python
def aes_gcm_encrypt_token(token):
    """Encrypts the session token with AES-GCM."""
    raise NotImplementedError
```

Lexical matching says implemented. Embedding similarity says implemented. An LLM shown that signature says implemented. All three agree — and all three agree for one reason, which is the identifier string. Rename the function to `f7` and every one of them collapses at the same instant. Their agreement was never three independent judgements; it was one signal counted three times.

This is the traceability analogue of counting correlated votes as independent witnesses. Weighting the matchers does not fix it, because a weighting rescales all of them together and cannot change the ordering when the correlated signal is the dominant one.

## Motivation

Review and audit settings need a different question from TLR. The useful output is not “this sentence is similar to this function.” It is whether a claim is supported by **mutually independent** implementation evidence, and whether that support **survives the loss of any single source** (a name, a docstring, a shared token, a file).

Channel-disjoint corroboration (CDC) gathers evidence through seven provenance-tagged channels (`NAME`, `DOC`, `IMPORT`, `CALL`, `SCHEMA`, `TEST`, `BODY`) and counts only evidence whose provenance sets are pairwise disjoint. `C(claim)` is the size of that largest independent set. A counterfactual check deletes every source in turn; a verdict must survive the loss of any single source. A claim propped up entirely by naming does not survive. `CALL` and `TEST` emit only when the callee is not a stub and another channel already fired, so `NOMINAL` can demote a claim; this gate is current behaviour, not the original spec table.

The default embedder used by the lexical-semantic baselines is TF-IDF over identifier sub-tokens (numpy only). It is a lexical-semantic proxy, not a neural embedding. That fact is stated in the README and is not hidden.

## What the evaluation shows

Evaluation is at (claim, element) granularity on a mutation-injected corpus, and the headline metric is *separation*: how much more often a policy accepts the pristine element than the same element after mutation. A policy that accepts nothing scores a low false-implemented rate with no skill at all, so only that gap is evidence. On the `NOMINAL` operator — name, docstring and path kept byte-for-byte, body gutted — `lexical`, `embedding` and `hybrid` separate by **exactly 0.0 percentage points**: they accept a gutted function at precisely the rate they accept a working one. That 0.0 is guaranteed by construction rather than established by a grid search: those three policies read only `el.name`, `el.doc` and `el.path` and never read the `k_min` they accept, and `NOMINAL` leaves all three byte-for-byte unchanged, so each computes the identical score on both sides at every threshold and every `k_min`. Channel-disjoint corroboration separates the same mutation by **100.0 points**. Full tables are in the README, printed verbatim by `python experiments/report.py`.

Three things about that result are stated here rather than left for a reader to find. First, our own first evaluation was **mis-specified**: it labelled at claim level, marking a claim as a gap whenever its single lexical best-match element was mutated, while 141 of 161 such claims remain genuinely implemented by other elements. Those labels understated every evidence-based policy and made the published table contradict this method's own claim. The evaluation has been corrected, and the mis-specified table is retained in the README as a captioned diagnostic rather than deleted. Second, the E1 pair-level table is **not** a held-out result: its 60/40 split is not group-aware, so the same `(project, cid, uid)` pair can appear on both sides across mutation rounds and E1 is optimistic by an unmeasured amount; the separation table is the primary artifact and is not split-based. Third, `WEAKEN` is the method's weak operator — `cdc` separates it by 0.0 pp (n = 19) and `cdc_counterfactual` beats `cdc` there at 15.8 pp — because weakening maps `sha256` to `md5` and the operation vocabulary keeps `md5` as `op:hash_weak` instead of dropping the operation, so `BODY` still fires. `DELETE` is degenerate for the opposite reason: no element survives it, so its gutted column is 0.0 for every policy by construction and its pairs are free true positives.

Counterfactual ablation carries its own cost, stated with the same emphasis: `cdc_counterfactual` accepts 79.59% of pristine `NOMINAL` pairs against `cdc`'s 100.00%, because one corpus element is called but has no test calling it, so ablating `ch:CALL` collapses its count. `cdc_counterfactual` is the stricter policy and the wrong default on a thinly tested codebase; `cdc` is the better default.

## Scope

**In scope for this review**

- Python AST extraction: functions, classes, methods, routes, schema elements, imports, call graph, test references.
- Claim extraction from Markdown and LaTeX documents behind one interface.
- All seven evidence channels, with set-valued provenance.
- The corroboration engine: dependency classification, exact `C(claim)`, counterfactual ablation.
- Labelled mutation corpus with five operators (`DELETE`, `RENAME`, `WEAKEN`, `STUB`, `NOMINAL`).
- Comparison policies, including the Review 1 hybrid matcher as a baseline.
- Experiments E0–E6, figures, dependency-free tests, README.
- Draft report sections, slide content, demo script.

**Deferred as planned Final Review work**

- Live LLM claim-extraction backend.
- Corpus scale-up beyond the vendored set.
- Cross-language extraction beyond Python.
- Oral-probe question generation for high-gap components.

**Explicit non-goals.** Plagiarism or authorship detection; grading; judging code quality; proving code correct. The system localises which claims lack independent implementation evidence, and nothing more.

The four deferred items are not implemented in this tree. Modules 100–800, E0–E6, figures, tests, and these draft deliverables are. That split is the checkable basis for a 60–75% completion claim at this review.

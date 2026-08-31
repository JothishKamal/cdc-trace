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

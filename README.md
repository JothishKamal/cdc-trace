# Traceability-Gap Detection Between Student Code and Thesis Claims

A claims document asserts that a system does certain things. The source code
either does them or it does not. Automated traceability-link recovery already
exists; the failure it does not address is that **a claim is not implemented
merely because some code resembles it.**

Consider a document claiming *"AES-GCM encrypts the session token"* against:

```python
def aes_gcm_encrypt_token(token):
    """Encrypts the session token with AES-GCM."""
    raise NotImplementedError
```

Lexical matching says implemented. Embedding similarity says implemented. An
LLM shown that signature says implemented. All three agree — and all three
agree for one reason, which is the identifier string. Rename the function to
`f7` and every one of them collapses at the same instant.

This package gathers evidence for each claim through seven provenance-tagged
channels (`NAME`, `DOC`, `IMPORT`, `CALL`, `SCHEMA`, `TEST`, `BODY`), then
counts only mutually independent evidence. `C(claim)` is the size of the
largest set of evidence whose provenance sets are pairwise disjoint. A
counterfactual check deletes every source in turn; a verdict must survive the
loss of any single source.

The default embedder is TF-IDF over identifier sub-tokens (numpy only). It is
a lexical-semantic proxy, not a neural embedding.

## What is implemented

| File | Role |
|---|---|
| `cdc/model.py` | `Claim`, `CodeElement`, `Evidence`; sub-token normalisation |
| `cdc/codebase.py` | AST inventory, call graph, reachability, routes, schema, stub detection |
| `cdc/claims.py` | claim extraction; Markdown and LaTeX frontends |
| `cdc/evidence.py` | seven channels, set-valued provenance |
| `cdc/corroborate.py` | dependency graph, exact `C(claim)`, counterfactual ablation |
| `cdc/scoring.py` | `SUPPORTED` / `WEAK` / `UNSUPPORTED` verdicts and gap scores |
| `cdc/policies.py` | `lexical`, `embedding`, `hybrid`, `evidence_count`, `channel_count`, `cdc`, `cdc_counterfactual` |
| `cdc/embed.py` | TF-IDF cosine over identifier sub-tokens |
| `cdc/mutate.py` | labelled fault injection: `DELETE`, `RENAME`, `WEAKEN`, `STUB`, `NOMINAL` |

Experiments E0–E6 live in `experiments/`. Figures are written to `assets/`.
Ground truth is mutation-injected on a vendored Python corpus.

## Running it

```
python tests/test_corroborate.py
python experiments/run_all.py
python experiments/report.py
python figures/make_figures.py
```

Every file under `tests/` is runnable the same way (`python tests/test_….py`).
`run_all.py` writes `results/results.json`. `report.py` prints the tables
below. `make_figures.py` writes `assets/fig1.png` … `assets/fig6.png`.
`python experiments/run_all.py --quick` is a one-round smoke run.

Dependencies: `pip install -r requirements.txt` (numpy, matplotlib).

## Headline results

Copied from `python experiments/report.py`:

```
seed=20260902  k_min=2
baseline_thresholds: {"channel_count": 4, "embedding": 0.6, "evidence_count": 4, "hybrid": 0.5, "lexical": 0.4}

=== E1 main comparison (held-out, gap class) ===
policy                    prec % (95% CI)     rec % (95% CI)     F1     FIR % (95% CI)
cdc                    100.00 ( 51.0-100.0)  23.53 (  9.6- 47.3)  38.10  76.47 ( 52.7- 90.4)
cdc_counterfactual      40.00 ( 16.8- 68.7)  23.53 (  9.6- 47.3)  29.63  76.47 ( 52.7- 90.4)
channel_count           50.00 ( 23.7- 76.3)  29.41 ( 13.3- 53.1)  37.04  70.59 ( 46.9- 86.7)
embedding               21.54 ( 13.3- 33.0)  82.35 ( 59.0- 93.8)  34.15  17.65 (  6.2- 41.0)
evidence_count          80.00 ( 37.6- 96.4)  23.53 (  9.6- 47.3)  36.36  76.47 ( 52.7- 90.4)
hybrid                  21.13 ( 13.2- 32.0)  88.24 ( 65.7- 96.7)  34.09  11.76 (  3.3- 34.3)
lexical                 20.51 ( 13.0- 30.8)  94.12 ( 73.0- 99.0)  33.68   5.88 (  1.0- 27.0)

=== E2 NOMINAL false-implemented rate ===
policy                     FIR % (95% CI)
cdc                     75.00 ( 46.8- 91.1)
cdc_counterfactual      75.00 ( 46.8- 91.1)
channel_count           66.67 ( 39.1- 86.2)
embedding                8.33 (  1.5- 35.4)
evidence_count          75.00 ( 46.8- 91.1)
hybrid                   8.33 (  1.5- 35.4)
lexical                  8.33 (  1.5- 35.4)

=== E4 cdc vs cdc_counterfactual ===
policy                     F1     FIR % (95% CI)
cdc                     36.36  77.78 ( 63.7- 87.5)
cdc_counterfactual      31.58  73.33 ( 59.0- 84.0)
```

`cdc_counterfactual` does not have the lowest false-implemented rate. On E1,
lowest FIR is `lexical` at 5.88% (1.0-27.0), then `hybrid` at 11.76% (3.3-34.3),
then `embedding` at 17.65% (6.2-41.0). `cdc` and `cdc_counterfactual` are both
76.47% (52.7-90.4).

E0 sets each free-threshold baseline to its own best F1 on a rare gap class.
That lands high thresholds (`lexical` 0.4, `hybrid` 0.5, `embedding` 0.6), so
those policies rarely predict implemented: low FIR, high recall, precision
near 20% (`lexical` 20.51, `hybrid` 21.13, `embedding` 21.54). CDC still finds
`C ≥ 2` after a single-function `NOMINAL` because other files remain.

On E2 NOMINAL, `lexical` / `hybrid` / `embedding` FIR is 8.33% (1.5-35.4);
`cdc` and `cdc_counterfactual` are 75.00% (46.8-91.1). On E4, ablation is
slightly better than plain C (`cdc_counterfactual` FIR 73.33% vs `cdc` 77.78%)
but is not the lowest policy.

## Honest limitations

- Ground truth is mutation-injected. The mutation operators encode our own assumptions
  about how implementations diverge from claims, and real divergence may not look like this.
- Channel independence is an assumption, not a proof. `DOC` and `NAME` are strongly
  correlated in practice, and provenance tagging only partly captures that.
- `BODY` analysis is shallow: a normalised operation vocabulary from the AST, not semantic
  understanding. It detects stubs reliably and weakened algorithms only sometimes.
- The default embedder is a lexical-semantic proxy, so the `embedding` and `hybrid`
  baselines are somewhat weaker than a neural implementation would be. Reported as such.
- Corpus scale is small. Wilson intervals are reported throughout, so a reader can see
  which differences the sample size actually resolves.
- `CALL` and `TEST` emit only when the callee is not a stub and another channel already fired, so a `NOMINAL` mutation can demote a claim. This is current `gather` behaviour, not the original spec table.
- Python only.

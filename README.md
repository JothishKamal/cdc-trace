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

Every number in this section is copied from `python experiments/report.py`
(`seed=20260902`, `k_min=2`, thresholds
`{"channel_count": 3, "embedding": 0.1, "evidence_count": 3, "hybrid": 0.1, "lexical": 0.1}`).
Evaluation is at (claim, element) granularity: one pair per claim that had evidence on
that element before mutation.

### Primary comparison — pristine versus gutted

A policy that refuses everything scores a flattering false-implemented rate while
separating nothing. Only the gap between *accepts the pristine element* and *accepts the
same element after mutation* is skill, so separation is the headline metric.

`NOMINAL` is the adversarial operator: name, docstring and path are kept byte-for-byte
and the body is gutted.

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

`lexical`, `embedding` and `hybrid` separate `NOMINAL` by **exactly 0.0 points** — not
close to zero, the identical number in both columns. They accept a gutted function at
precisely the rate they accept a working one, so they carry no information about whether
the body exists. `cdc` separates it by **100.0**: it accepts every pristine pair and none
of the gutted ones.

That 0.0 is threshold-invariant. Separation for those three policies is 0.0 at every
point of the sweep grid (seven thresholds, 0.1 to 0.7, crossed with every swept `k_min`),
so it is not an artefact of the threshold E0 happened to select. It cannot be otherwise:
name, docstring and path are the only inputs those three policies read, and `NOMINAL`
leaves all three unchanged.

Separation in percentage points, all five operators:

| policy | NOMINAL | STUB | WEAKEN | RENAME | DELETE † |
|---|---:|---:|---:|---:|---:|
| `lexical` | 0.0 | 20.0 | 0.0 | 0.0 | 81.2 |
| `embedding` | 0.0 | 35.0 | 0.0 | 0.0 | 93.8 |
| `hybrid` | 0.0 | 30.0 | 0.0 | 3.4 | 90.6 |
| `evidence_count` | 77.6 | 75.0 | 5.3 | 86.2 | 100.0 |
| `channel_count` | 77.6 | 75.0 | 5.3 | 86.2 | 100.0 |
| `cdc` | 100.0 | 77.5 | 0.0 | 100.0 | 100.0 |
| `cdc_counterfactual` | 79.6 | 72.5 | 15.8 | 100.0 | 100.0 |

n = 49 (NOMINAL), 40 (STUB), 19 (WEAKEN), 29 (RENAME), 32 (DELETE) mutated pairs.

† `DELETE` removes the element from the tree entirely, so its gutted column is 0.0
for all seven policies by construction and its pairs are free true positives. Read that
column as a sanity check, not as evidence. Note also that this DELETE n (32, counted over
all pairs) is a different population from the DELETE count in the E1 table below (13,
counted over the 431-pair test split); the two are not the same quantity.

`WEAKEN` is the method's weak operator and the one place a baseline beats corroboration:
`cdc` separates it by 0.0 pp (n = 19) while `cdc_counterfactual` reaches 15.8 pp. The
cause is the operation vocabulary, not a defect in the harness — see limitations below.

### E1 pair-level comparison

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

(The caveat printed with that table refers to the separation table as being "below" it,
which is where `report.py` prints it; in this README it is the section above.)

The corrected evaluation reverses what the original one reported. `cdc` and
`cdc_counterfactual` now hold the two highest recalls and the two lowest
false-implemented rates, which is the ordering the method predicts. Lowest FIR is
`cdc_counterfactual` at 4.41% (1.5-12.2), then `cdc` at 5.88% (2.3-14.2), then
`evidence_count` and `channel_count` at 16.18% (9.3-26.7). The three name-based baselines are far behind:
`lexical` 47.06% (35.7-58.8), `hybrid` 48.53% (37.1-60.2), `embedding` 51.47%
(39.8-62.9). Precision is low for every policy because the base rate of gaps at pair
granularity is small, so F1 is not the number to read here — separation is.

`report.py` also prints the same table with the 13 `DELETE` pairs removed, as a
sensitivity check. The ordering holds: `cdc` recall 92.73%, FIR 7.27%; `lexical` recall
41.82%, FIR 58.18%.

### E4 — `cdc` versus `cdc_counterfactual`

```
=== E4 cdc versus cdc_counterfactual ===
cdc_counterfactual keeps the corroboration count but drops the
channel-disjointness requirement.
------------------------------------------------------------------------------------------------
policy                    prec % (95% CI)     rec % (95% CI)     F1     FIR % (95% CI)
cdc                     28.78 ( 25.2- 32.7)  93.49 ( 88.7- 96.3)  44.01   6.51 (  3.7- 11.3)
cdc_counterfactual      26.66 ( 23.3- 30.3)  95.27 ( 90.9- 97.6)  41.66   4.73 (  2.4-  9.1)
```

`cdc_counterfactual` buys its slightly lower false-implemented rate by rejecting
legitimate code: it accepts 79.59% of pristine `NOMINAL` pairs against `cdc`'s 100.00%.
The cause is a single corpus element — `ledger schema:connect_memory` is called but no
test calls it, so ablating `ch:CALL` collapses it. `cdc_counterfactual` is therefore the
stricter policy and the wrong default on a thinly tested codebase. `cdc` is the better
default; `cdc_counterfactual` is the right choice only where a false *implemented*
verdict costs more than a false gap.

### Diagnostic — the original, mis-specified claim-level table

This is the evaluation this project published first. It is retained, not deleted: having
diagnosed our own metric is a more defensible position than only ever showing the
corrected number.

```
=== E1 secondary: claim-level labelling (diagnostic only) ===
thresholds: {"channel_count": 4, "embedding": 0.6, "evidence_count": 4, "hybrid": 0.5, "lexical": 0.4}
------------------------------------------------------------------------------------------------
Claim-level labelling marks a claim as a gap when its single lexical best-match
element was mutated. Measured on this corpus, 141 of 161 such claims remain
genuinely implemented by other elements, so this table understates every
evidence-based policy and is retained only as a diagnostic.
policy                    prec % (95% CI)     rec % (95% CI)     F1     FIR % (95% CI)
lexical                 20.51 ( 13.0- 30.8)  94.12 ( 73.0- 99.0)  33.68   5.88 (  1.0- 27.0)
embedding               21.54 ( 13.3- 33.0)  82.35 ( 59.0- 93.8)  34.15  17.65 (  6.2- 41.0)
hybrid                  21.13 ( 13.2- 32.0)  88.24 ( 65.7- 96.7)  34.09  11.76 (  3.3- 34.3)
evidence_count          80.00 ( 37.6- 96.4)  23.53 (  9.6- 47.3)  36.36  76.47 ( 52.7- 90.4)
channel_count           50.00 ( 23.7- 76.3)  29.41 ( 13.3- 53.1)  37.04  70.59 ( 46.9- 86.7)
cdc                    100.00 ( 51.0-100.0)  23.53 (  9.6- 47.3)  38.10  76.47 ( 52.7- 90.4)
cdc_counterfactual      40.00 ( 16.8- 68.7)  23.53 (  9.6- 47.3)  29.63  76.47 ( 52.7- 90.4)
```

Claim-level labelling marked a claim as a gap whenever its single lexical best-match
element was mutated. On this corpus, 141 of 161 such claims remain genuinely implemented
by other elements, so the labels were wrong and the table understates every
evidence-based policy — which is why it appeared to show `cdc` at a 76.47%
false-implemented rate against `lexical`'s 5.88%. That evaluation was mis-specified; it
has been corrected, and the (claim, element) tables above supersede it.

## Honest limitations

- The original evaluation was mis-specified and we corrected it. Claim-level labelling
  called a claim a gap whenever its single lexical best-match element was mutated, but
  141 of 161 such claims remain genuinely implemented by other elements. That labelling
  understated every evidence-based policy and made the published result contradict the
  method's own claim. The corrected evaluation labels at (claim, element) granularity;
  the old table is kept above as a captioned diagnostic.
- `WEAKEN` is the method's weak operator: `cdc` separates it by 0.0 pp (n = 19) and
  `cdc_counterfactual` beats `cdc` there at 15.8 pp. `cdc/mutate.py` weakens an algorithm
  by mapping `sha256` to `md5`, and `cdc/codebase.py` maps `md5` to `op:hash_weak` rather
  than dropping the operation, so `BODY` still fires after the algorithm has been
  weakened. That is a limitation of the operation vocabulary, not a bug.
- The counterfactual costs acceptance of legitimate code. `cdc_counterfactual` accepts
  79.59% of pristine `NOMINAL` pairs against `cdc`'s 100.00%, because `ledger
  schema:connect_memory` is called but has no test calling it, so ablating `ch:CALL`
  collapses it. `cdc_counterfactual` is the stricter policy and the wrong default on
  thinly tested codebases; `cdc` is the better default.
- E1 is not a held-out result. The 60/40 split is not group-aware — the same
  `(project, cid, uid)` pair can appear on both sides of it across mutation rounds — so
  E1 is optimistic by an unmeasured amount. The primary artifact is the E2b separation
  table, which is not split-based.
- `DELETE` is degenerate. Its gutted column is 0.0 for all seven policies by construction
  and its pairs are free true positives, so it discriminates nothing between policies.
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

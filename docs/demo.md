# Demo script

Offline. From the repository root. Dependencies: `pip install -r requirements.txt` (numpy, matplotlib). No network.

## Commands in order

### 1. Corroboration semantics

```
python tests/test_corroborate.py
```

Expected:

```
ok: test_ablation_removes_every_evidence_touching_a_source
ok: test_counterfactual_demotes_a_name_dependent_claim
ok: test_counterfactual_survives_when_support_is_genuinely_broad
ok: test_empty_evidence_is_zero_corroboration
ok: test_provenance_sharing_is_not_transitive
ok: test_sources_are_sorted_and_deduplicated
ok: test_three_name_derived_evidences_are_one_witness
ok: test_witness_set_is_exactly_maximum_and_pairwise_disjoint
8 tests passed
```

Point at while it runs: three name-derived matches count as **one** witness; provenance sharing is **not** transitive (`C = 2` inside one connected component).

### 2. Worked NOMINAL example (live)

```
python tests/test_integration.py
```

Expected:

```
ok: test_nominal_mutation_flips_a_claim_to_unsupported
1 tests passed
```

Walk-through (what the test does):

1. Load `corpus/sessionstore` code and `doc.md`.
2. Take the first claim the pristine tree marks `SUPPORTED`.
3. Find the name-best element (in the current corpus this is aimed at `seal_blob`).
4. Copy the tree. Apply `NOMINAL`: **keep the name and docstring, gut the body** (`pass` / `NotImplementedError`).
5. Re-extract and re-score. Verdict is no longer `SUPPORTED`.

That is the adversary the method exists to catch: lexical, embedding, and an LLM shown the signature still see an implemented claim; the identifier never moved.

Optional one-liner to show the operator itself:

```
python -c "from cdc.mutate import mutate_source; print(mutate_source('def seal_blob(x):\n    \"\"\"returns ciphertext\"\"\"\n    return gcm(x)\n', 'seal_blob', 'NOMINAL'))"
```

The name and docstring remain; the body does not.

### 3. Headline tables (do not re-invent numbers)

`results/results.json` is already written by the full harness. Print it:

```
python experiments/report.py
```

The primary comparison is **separation**: how much more often a policy accepts the pristine element than the same element after the mutation. Say this before the table goes up: *a policy that accepts nothing scores a low false-implemented rate without any skill, so a false-implemented rate on its own is not evidence — only the gap between the two columns is.*

Expected, on `NOMINAL` — name and docstring kept, body gutted (`seed=20260902`, `k_min=2`; thresholds `channel_count` 3, `embedding` 0.1, `evidence_count` 3, `hybrid` 0.1, `lexical` 0.1):

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

Say out loud: **on `NOMINAL`, `lexical`, `embedding` and `hybrid` separate by exactly 0.0 points, and `cdc` separates by 100.0.** Not close to zero — the identical number in both columns. They accept a gutted function at precisely the rate they accept a working one, so they carry no information about whether the body exists. If asked whether that is a threshold artefact: no, and the reason is stronger than a sweep — it is true **by construction**, so no grid search is needed to establish it. `lexical`, `embedding` and `hybrid` read only `el.name`, `el.doc` and `el.path` (`cdc/policies.py`), and they accept a `k_min` argument that they never read. `NOMINAL` rewrites the body and leaves those three fields byte-for-byte identical, so each of those policies computes the same number before and after the mutation. Equal columns, separation exactly 0.0, at every threshold and every `k_min`.

Separation in percentage points across all five operators (n = 49 / 40 / 19 / 29 / 32 mutated pairs):

| policy | NOMINAL | STUB | WEAKEN | RENAME | DELETE † |
|---|---:|---:|---:|---:|---:|
| `lexical` | 0.0 | 20.0 | 0.0 | 0.0 | 81.2 |
| `embedding` | 0.0 | 35.0 | 0.0 | 0.0 | 93.8 |
| `hybrid` | 0.0 | 30.0 | 0.0 | 3.4 | 90.6 |
| `evidence_count` | 77.6 | 75.0 | 5.3 | 86.2 | 100.0 |
| `channel_count` | 77.6 | 75.0 | 5.3 | 86.2 | 100.0 |
| `cdc` | 100.0 | 77.5 | 0.0 | 100.0 | 100.0 |
| `cdc_counterfactual` | 79.6 | 72.5 | 15.8 | 100.0 | 100.0 |

† Volunteer this before anyone asks: `DELETE` removes the element from the tree entirely, so its gutted column is 0.0 for all seven policies **by construction** and its pairs are free true positives. It is a sanity check, not a discriminator. Its n here (32, over all pairs) is a different population from the 13 `DELETE` pairs inside the E1 test split below; do not present them as the same quantity.

Volunteer the weak operator too: **`WEAKEN` is where the method is weakest.** `cdc` separates it by 0.0 pp (n = 19) and `cdc_counterfactual` beats `cdc` there at 15.8 pp. `cdc/mutate.py` weakens an algorithm by mapping `sha256` to `md5`, and `cdc/codebase.py` maps `md5` to `op:hash_weak` rather than dropping the operation, so `BODY` still fires after the algorithm has been weakened. That is a limit of the operation vocabulary, not a bug, and it is not hidden.

Then the pair-level table:

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

(The caveat printed inside that block calls the separation table "below", which is where `report.py` prints it; in this script it is above.)

`cdc` and `cdc_counterfactual` hold the two highest recalls (94.12% and 95.59%) and the two lowest false-implemented rates (5.88% and 4.41%), against `lexical` 47.06%, `hybrid` 48.53% and `embedding` 51.47%. Say plainly that **E1 is not a held-out result**: the 60/40 split is not group-aware, so the same `(project, cid, uid)` pair can appear on both sides of it across mutation rounds and E1 is optimistic by an unmeasured amount. The separation table above is the primary artifact and is not split-based.

And the ablation comparison:

```
=== E4 cdc versus cdc_counterfactual ===
cdc_counterfactual keeps the corroboration count but drops the
channel-disjointness requirement.
------------------------------------------------------------------------------------------------
policy                    prec % (95% CI)     rec % (95% CI)     F1     FIR % (95% CI)
cdc                     28.78 ( 25.2- 32.7)  93.49 ( 88.7- 96.3)  44.01   6.51 (  3.7- 11.3)
cdc_counterfactual      26.66 ( 23.3- 30.3)  95.27 ( 90.9- 97.6)  41.66   4.73 (  2.4-  9.1)
```

`cdc_counterfactual` buys its slightly lower false-implemented rate by rejecting legitimate code: it accepts 79.59% of pristine `NOMINAL` pairs against `cdc`'s 100.00%. One corpus element causes it — `ledger schema:connect_memory` is called from `db.py` but no test calls it, so ablating `ch:CALL` collapses its count. `cdc_counterfactual` is therefore the stricter policy and the wrong default on a thinly tested codebase; **`cdc` is the better default.**

To regenerate results (slow; not required live):

```
python experiments/run_all.py --quick
python experiments/run_all.py
```

### 4. The correction we made to our own evaluation

Present this; do not wait to be caught by it. It is the strongest thing on the slide deck after the 0.0.

**What was wrong.** The first evaluation labelled at **claim level**: a claim was marked a gap whenever its single lexical best-match element was mutated. That is wrong whenever a claim is implemented by more than one element — mutate the best-match function and the claim is still implemented by the others, but the label says "gap" and every policy that looks at real evidence is scored as having missed it.

**How it was found.** The published table said `cdc` had a 76.47% false-implemented rate against `lexical`'s 5.88% — the method losing, on its own headline table, to the baseline it was built to beat. Rather than ship that, we measured the labels themselves: **141 of 161** such claims remain genuinely implemented by other elements. The labels were wrong, not the method.

**What changed.** Evaluation is now at **(claim, element) granularity** — one pair per claim that had evidence on that element before the mutation — and the primary comparison is separation rather than a false-implemented rate. **The engine did not change.** `cdc/` was not touched: the same corroboration code produces both tables. Only the labelling and the reporting changed.

**What we kept.** The mis-specified table is still printed by `report.py` and still in the README, captioned as a diagnostic. It was not deleted. Show it if asked:

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

### 5. Figures

```
python figures/make_figures.py
```

Writes `assets/fig1.png` … `assets/fig6.png`. On the panel, open **`assets/fig3.png`** (the
primary separation bars) first, then **`assets/fig4.png`** (identifier ablation).

Present `fig4` with its caveat, and present the caveat before the curve, not after. It
plots the same separation measure as `fig3` against the fraction of function and class
names renamed to opaque tokens:

```
Separation in percentage points against ablation fraction:
policy                      0.0     0.25      0.5     0.75      1.0
lexical                     0.0      0.0      0.0      0.0      0.0
embedding                   0.0      0.0      0.0      0.0      0.0
hybrid                      0.0      0.0      0.0      0.0      0.0
evidence_count             80.6     55.0     35.1     25.5      7.7
channel_count              80.6     55.0     35.1     25.5      7.7
cdc                        95.5     66.0     54.6     33.0     15.4
cdc_counterfactual         89.6     47.0     30.9      0.0      0.0
```

Say out loud: **this one does not flatter us.** `cdc` separation falls from 95.5 pp to
15.4 pp as identifiers are destroyed. `NAME` is one of the seven evidence channels, so
renaming every identifier removes evidence the method genuinely uses, and the curve shows
exactly that. Then say what it does *not* show: `cdc`'s accepts-gutted column is 0.00% at
every ablation level, so the method never starts accepting a gutted body — it stops
recognising working code and goes quiet. Lost recall, not a false `SUPPORTED`. And the
baselines gain nothing from the comparison: `lexical`, `embedding` and `hybrid` sit at
0.0 pp at *every* level including 0.00, because `NOMINAL` never changes what they read.
At full ablation `cdc` still separates by 15.4 pp where all three of them separate by
nothing.

If asked why `cdc_counterfactual` hits 0.0 at 0.75 and 1.00: it accepts nothing at all
there (0.00% pristine, 0.00% gutted). It is the stricter policy, and on obfuscated code
it refuses everything, which is why `cdc` is the default.

An earlier version of this figure showed `lexical`, `hybrid` and `embedding` flat at
F1 = 1.000 while `cdc` fell away — the inverse of the claim. Two defects caused it, both
fixed: the metric hard-coded `fp = 0` and `precision = 1.0`, so it could not penalise a
policy that accepts everything; and the rename emitted `_r{i}_{old}`, which still
sub-tokenises to the original identifier, so nothing was actually being ablated. If the
panel saw the old figure, say this before they ask.

## Panel Q&A

### Why should we trust the corrected numbers if the first ones were wrong?

Three reasons, and none of them is "trust us". First, **the engine never changed**: `cdc/` was not touched between the two evaluations, so the same corroboration code produced both tables. What was wrong was the labelling — claim-level best-match labelling, which marks a claim as a gap even when other elements still implement it — and we measured exactly how wrong: 141 of 161 such claims remain genuinely implemented. Second, the headline result is not a tuned number, and it is not defended by a sweep either — it holds **by construction**: `lexical`, `embedding` and `hybrid` read only `el.name`, `el.doc` and `el.path` (they take a `k_min` argument and never read it), and `NOMINAL` leaves all three byte-for-byte unchanged, so each computes the same score before and after the mutation and its separation is exactly 0.0 at every threshold and every `k_min`. That is a stronger statement than "we searched a grid and never saw it move". Third, it is **reproducible**: the harness is seeded and offline, repeated `python experiments/run_all.py` runs write a byte-identical `results/results.json`, and every number in the README, the slides and this script is copied from `python experiments/report.py` rather than retyped. The old table is still printed, captioned as a diagnostic, so both are on the record.

### Does the method depend on identifiers after all?

Partly, and E3 measures how much. Rename every function and class to an opaque token and
`cdc` separation on `NOMINAL` falls from 95.5 pp to 15.4 pp. `NAME` is one of the seven
evidence channels, so that is a real cost, not an artefact — wholesale renaming removes
evidence the method uses. Two things bound it. First, the method degrades by going
silent, not by becoming wrong: `cdc` accepts 0.00% of gutted elements at every ablation
level, so obfuscation costs recall, never a false `SUPPORTED`. Second, it degrades from a
position the baselines never occupy: `lexical`, `embedding` and `hybrid` separate 0.0 pp
at *every* ablation level including zero, so at full ablation a 15.4 pp separation is
still the only separation on the table. The honest summary is that corroboration needs
more than a name but is weakened when names are destroyed, and file paths and docstrings
carry the residue.

### Where is the method weakest?

`WEAKEN`. `cdc` separates it by 0.0 pp (n = 19) and `cdc_counterfactual` beats `cdc` there at 15.8 pp — a baseline-style ablation policy outperforming plain corroboration on one operator. The cause is known: `cdc/mutate.py` weakens an algorithm by mapping `sha256` to `md5`, and `cdc/codebase.py` maps `md5` to `op:hash_weak` rather than dropping the operation, so `BODY` still fires after the algorithm has been weakened. It is a limit of the operation vocabulary, not a bug, and it is disclosed in the README, on the Conclusion slide and in the report.

### If the counterfactual is stricter, why is it not the default?

Because strictness is not free. `cdc_counterfactual` accepts only 79.59% of pristine `NOMINAL` pairs against `cdc`'s 100.00% — it rejects legitimately implemented code. One corpus element shows the mechanism: `ledger schema:connect_memory` is called from `db.py` but no test calls it, so ablating `ch:CALL` leaves only same-file channels, which all conflict, and the count collapses. On a thinly tested codebase that behaviour is common, so `cdc` is the better default; `cdc_counterfactual` is the right choice only where a false *implemented* verdict costs more than a false gap.

### Is the E1 table a held-out result?

No, and we do not present it as one. The 60/40 split is not group-aware: the same `(project, cid, uid)` pair can appear on both sides of it across mutation rounds, so E1 is optimistic by an unmeasured amount. `report.py` prints that caveat with the table. The primary artifact is the separation table, which is not split-based. A group-aware split on `(project, cid, uid)` is the fix and is not implemented here. Related: the `DELETE` operator is degenerate — it removes the element from the tree, so its gutted column is 0.0 for all seven policies by construction and its pairs are free true positives. `report.py` also prints E1 with those 13 pairs removed as a sensitivity check, and the ordering holds (`cdc` recall 92.73%, FIR 7.27%; `lexical` recall 41.82%, FIR 58.18%).

### Why not just use an LLM?

The stub `aes_gcm_encrypt_token` / `NotImplementedError` is the answer. An LLM shown that signature agrees with lexical matching and embedding similarity, and all three agree because of the identifier. Rename it to `f7` and they collapse together. The method exists to refuse correlated agreement. Live LLM claim extraction is deferred Final Review work; the demo is offline by design. The default embedder is TF-IDF over sub-tokens, not a neural model.

### Why is a maximum independent set needed rather than counting channels?

Because provenance is a **set**, not a channel tag. `NAME` and `DOC` routinely share `tok:` and `file:` sources — the docstring restates the identifier. Channel-count treats them as two witnesses; they are one. If each evidence item had a single channel tag, “channel-disjoint” would collapse into counting distinct channels and the independent set would be decoration. Connected components are also wrong: `e1` may share a token with `e2` and `e2` a file with `e3` while `e1` and `e3` remain disjoint, so `C = 2` inside one component. That is `test_provenance_sharing_is_not_transitive`.

### How do you know the mutations are realistic?

We do not claim they are a sample of real student divergence. Ground truth is mutation-injected and labelled by construction so precision and recall are exact. The operators (`DELETE`, `RENAME`, `WEAKEN`, `STUB`, `NOMINAL`) encode **our** assumptions about how implementations peel away from claims. Real divergence may not look like this. That limitation is in the README and on the Conclusion slide. `NOMINAL` is the synthetic adversary the method is built to catch, not a field study.

### What happens on code you did not author?

The pipeline does not know authorship. It parses Python with `ast`, extracts claims from Markdown or LaTeX, and reports `C`, ablation, and a verdict. There is no plagiarism detector and no grader. The labelled corpus is authored so mutations have known targets; that is evaluation, not a requirement at inference. On other people’s Python the same commands run; there is no mutation label, so you get verdicts, not precision/recall. Cross-language extraction and corpus scale-up are deferred Final Review work. Python only.

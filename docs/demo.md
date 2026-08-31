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

Expected (copied from a real run; `seed=20260902`, `k_min=2`):

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

Say out loud: **`cdc_counterfactual` does not have the lowest FIR.** On E1 the lowest FIR is `lexical` at 5.88% (1.0-27.0). E0 set each free-threshold baseline to its own best F1 on a rare gap class, which lands high thresholds, so those policies rarely predict implemented.

To regenerate results (slow; not required live):

```
python experiments/run_all.py --quick
python experiments/run_all.py
```

### 4. Figures

```
python figures/make_figures.py
```

Writes `assets/fig1.png` … `assets/fig6.png`. On the panel, open **`assets/fig4.png`** (identifier-ablation curves).

## Panel Q&A

### Why not just use an LLM?

The stub `aes_gcm_encrypt_token` / `NotImplementedError` is the answer. An LLM shown that signature agrees with lexical matching and embedding similarity, and all three agree because of the identifier. Rename it to `f7` and they collapse together. The method exists to refuse correlated agreement. Live LLM claim extraction is deferred Final Review work; the demo is offline by design. The default embedder is TF-IDF over sub-tokens, not a neural model.

### Why is a maximum independent set needed rather than counting channels?

Because provenance is a **set**, not a channel tag. `NAME` and `DOC` routinely share `tok:` and `file:` sources — the docstring restates the identifier. Channel-count treats them as two witnesses; they are one. If each evidence item had a single channel tag, “channel-disjoint” would collapse into counting distinct channels and the independent set would be decoration. Connected components are also wrong: `e1` may share a token with `e2` and `e2` a file with `e3` while `e1` and `e3` remain disjoint, so `C = 2` inside one component. That is `test_provenance_sharing_is_not_transitive`.

### How do you know the mutations are realistic?

We do not claim they are a sample of real student divergence. Ground truth is mutation-injected and labelled by construction so precision and recall are exact. The operators (`DELETE`, `RENAME`, `WEAKEN`, `STUB`, `NOMINAL`) encode **our** assumptions about how implementations peel away from claims. Real divergence may not look like this. That limitation is in the README and on the Conclusion slide. `NOMINAL` is the synthetic adversary the method is built to catch, not a field study.

### What happens on code you did not author?

The pipeline does not know authorship. It parses Python with `ast`, extracts claims from Markdown or LaTeX, and reports `C`, ablation, and a verdict. There is no plagiarism detector and no grader. The labelled corpus is authored so mutations have known targets; that is evaluation, not a requirement at inference. On other people’s Python the same commands run; there is no mutation label, so you get verdicts, not precision/recall. Cross-language extraction and corpus scale-up are deferred Final Review work. Python only.

# Evaluation Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Correct the ground-truth labelling defect that makes the reported experiments measure corpus token ambiguity instead of detector quality, and regenerate every downstream artifact from the corrected results.

**Architecture:** No change to `cdc/`. The defect is confined to `experiments/run_all.py`, where a claim is labelled implemented-or-not by whether a lexical `best_match` element was mutated. Evaluation moves to (claim, element) pair granularity, where the mutation actually occurred. The old claim-level analysis is retained as a clearly-captioned secondary result rather than deleted.

**Spec:** `docs/superpowers/specs/2026-08-31-cdc-trace-design.md`

## Global Constraints

- Python 3.11+. numpy and matplotlib only. **No network access.**
- Seed stays `SEED = 20260902`; `k_min = 2`. Re-running `run_all.py` must reproduce `results/results.json` byte-for-byte.
- **`cdc/` must not be modified.** The engine is verified correct; this plan corrects evaluation only.
- Every number appearing in README, slides or report docs must be copied from actual `experiments/report.py` output. Never write a number the code did not produce.
- Conventional Commits, no `Co-Authored-By` trailer. Scopes: `experiments`, `figures`, `readme`, `report`, `slides`.
- Never mention any submission portal or programme name.
- Do not delete the claim-level results. Diagnosing our own metric is a strength; hiding the weaker framing is the thing a reviewer will probe.

## Diagnostic evidence this plan is built on

Measured against the current tree, all six corpus projects:

- The gutted element is correctly demoted to `C < 2` in **161 of 161** cases. Stub detection is **36/36**. The engine has no failures.
- In **141 of 161** cases (87.6%) the *claim* nonetheless stays supported, because other elements in the codebase genuinely satisfy it. The claim-level label calls that a missed gap. It is not one.
- At (claim, element) granularity on `NOMINAL`, with the existing thresholds:

```
policy                  accepts pristine  accepts gutted   separation
  lexical                          2.5%            2.5%         0.0
  embedding                        4.3%            4.3%         0.0
  hybrid                           3.7%            3.7%         0.0
  evidence_count                  92.5%           37.9%        54.7
  channel_count                   92.5%           37.9%        54.7
  cdc                             92.5%            0.0%        92.5
  cdc_counterfactual              92.5%            0.0%        92.5
```

These are the numbers Task 1 must reproduce (small drift is acceptable if the
sampling differs; the ordering and the 0.0 separations must hold).

---

### Task 1: Correct the evaluation granularity

**Files:**
- Modify: `experiments/run_all.py`
- Test: `tests/test_evaluation.py` (create)

**Interfaces:**
- Produces `results/results.json` with keys: `seed`, `k_min`, `baseline_thresholds`,
  `e0_threshold_sweep`, `e1_main`, `e1_claim_level_secondary`, `e2_by_operator`,
  `e2b_separation`, `e3_identifier_ablation`, `e4_counterfactual`, `e5_calibration`,
  `e6_scaling`.

**Three defects to correct in `run_all.py`:**

1. `best_match` initialises `best_n = -1`, so an element sharing **zero** tokens with the
   claim still wins. Change it to require at least one shared token and return `None`
   otherwise. A claim with no match must be excluded from pair-level evaluation, not
   assigned an arbitrary target.
2. `mutate_items` labels `truly_implemented = op is None` at claim level. Replace the
   primary evaluation with pair-level items: one item per (claim, mutated element) where
   the claim had evidence on that element before mutation. `truly_implemented` is then
   `False` for that pair exactly when that element was mutated by a gap-inducing operator.
3. Policies must be applied to the single target element, not the whole codebase:
   evidence filtered to `e.element == target.uid`, and `elements` passed as `[target]`.

**Retain, do not delete:** the existing claim-level computation, written to
`e1_claim_level_secondary` with an added `"caveat"` string reading exactly:

```
Claim-level labelling marks a claim as a gap when its single lexical best-match
element was mutated. Measured on this corpus, 141 of 161 such claims remain
genuinely implemented by other elements, so this table understates every
evidence-based policy and is retained only as a diagnostic.
```

**New `e2b_separation`:** for each operator in `DELETE, RENAME, WEAKEN, STUB, NOMINAL`
and each policy, record `accepts_pristine`, `accepts_gutted`, `separation`
(= `accepts_pristine - accepts_gutted`, in percentage points), and `n`. This is the
primary comparison artifact, because it exposes a policy that scores well by refusing
to accept anything.

- [ ] **Step 1: Write the failing test**

Create `tests/test_evaluation.py` asserting the properties that must hold, reading
`results/results.json`:

```python
"""Evaluation-harness invariants."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def results():
    with open(os.path.join(ROOT, "results", "results.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_best_match_requires_a_shared_token():
    from experiments.run_all import best_match
    from cdc.model import Claim, CodeElement
    claim = Claim(cid="c", component="x", text="t", kind="requirement",
                  terms=frozenset({"alpha"}), implied_libs=frozenset(), section="1")
    el = CodeElement(uid="m:f", kind="function", name="zzz", path="m.py", lineno=1,
                     doc="", imports=frozenset(), calls=frozenset(),
                     body_ops=frozenset(), is_stub=False, reachable=True)
    assert best_match(claim, [el]) is None


def test_separation_table_is_present_for_every_operator():
    sep = results()["e2b_separation"]
    assert set(sep) == {"DELETE", "RENAME", "WEAKEN", "STUB", "NOMINAL"}
    for op, policies in sep.items():
        for name, row in policies.items():
            assert {"accepts_pristine", "accepts_gutted", "separation", "n"} <= set(row)


def test_name_based_policies_cannot_separate_nominal():
    """NOMINAL preserves name and docstring byte-for-byte, so lexical cannot see it."""
    nominal = results()["e2b_separation"]["NOMINAL"]
    for name in ("lexical", "hybrid", "embedding"):
        assert abs(nominal[name]["separation"]) < 1.0, name


def test_corroboration_separates_nominal():
    nominal = results()["e2b_separation"]["NOMINAL"]
    for name in ("cdc", "cdc_counterfactual"):
        assert nominal[name]["separation"] > 80.0, name
        assert nominal[name]["accepts_gutted"] < 1.0, name


def test_claim_level_secondary_is_retained_with_its_caveat():
    sec = results()["e1_claim_level_secondary"]
    assert "caveat" in sec and "understates" in sec["caveat"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `python tests/test_evaluation.py`
Expected: FAIL — `e2b_separation` missing.

- [ ] **Step 3: Implement the three corrections plus `e2b_separation`**

- [ ] **Step 4: Regenerate and verify determinism**

```bash
python experiments/run_all.py
python experiments/run_all.py   # second run
git diff --stat results/results.json   # must be empty after the second run
python tests/test_evaluation.py
for t in tests/test_*.py; do python "$t"; done
```
Expected: all suites pass; the second run leaves `results.json` unchanged.

- [ ] **Step 5: Commit**

```bash
git add experiments/run_all.py tests/test_evaluation.py results/results.json
git commit -m "fix(experiments): evaluate at claim-element granularity

Claim-level labelling marked a claim as a gap whenever its lexical
best-match element was mutated, but 141 of 161 such claims remain
implemented by other elements. Evaluation moves to the pair where the
mutation occurred; the claim-level table is retained as a diagnostic.
Adds the pristine-versus-gutted separation table."
```

---

### Task 2: Reporting and figures

**Files:**
- Modify: `experiments/report.py`, `figures/make_figures.py`

`report.py` prints, in order: the corrected E1 pair-level table; the **E2b separation
table** as the primary comparison; the per-operator breakdown; E4; E5 calibration; and
last, the claim-level secondary table **with its caveat printed immediately above it**.
Keep Wilson intervals throughout.

`make_figures.py`: fig3 becomes the separation bar chart (accepts-pristine against
accepts-gutted per policy, `NOMINAL`); the remaining figures regenerate from the new
keys. Any figure whose underlying key changed must be regenerated, not left stale.

- [ ] **Step 1:** Update both scripts.
- [ ] **Step 2:** Run `python experiments/report.py` and `python figures/make_figures.py`; confirm all six PNGs are rewritten and every table prints without a KeyError.
- [ ] **Step 3:** Commit `fix(experiments): report separation table as the primary comparison` and `fix(figures): regenerate figures from corrected results`.

---

### Task 3: README, slides and report documents

**Files:**
- Modify: `README.md`, `docs/slides/slides.md`, `docs/report/01-introduction.md`,
  `docs/report/04-design.md`

Same-shape editing work across four documents; do it as one unit.

Every number replaced with corrected `report.py` output. Specifically:

- **README** — replace the headline block with the corrected tables. Rewrite the
  paragraph beginning "`cdc_counterfactual` does not have the lowest false-implemented
  rate" to state what the corrected evaluation shows. **Keep** the honest-limitations
  section, and add one bullet recording that the original claim-level evaluation
  understated the method and why.
- **Slides — Experiments and Results:** lead with the separation table. Add one line
  explaining that a policy accepting nothing scores a low false-implemented rate without
  skill, which is why separation is reported.
- **Slides — Conclusion:** currently discusses only completion percentage. It must state
  the actual finding: name-based matching cannot separate `NOMINAL` at any threshold
  (separation ≈ 0), corroboration separates it fully, and the first evaluation was
  mis-specified and was corrected. Keep the deferred-work list.
- **`docs/report/01-introduction.md`** and **`04-design.md`** — update any claim about
  results to match, keeping the existing `CALL`/`TEST` disclosure.

- [ ] **Step 1:** Make the edits.
- [ ] **Step 2:** Verify every number against `python experiments/report.py` output.
- [ ] **Step 3:** Commit `docs(readme): report corrected evaluation` and `docs(slides): state the corrected finding in results and conclusion`.

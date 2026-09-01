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

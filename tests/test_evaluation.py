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
    """
    Corroboration must reject the gutted element and separate NOMINAL widely.

    The 75.0 floor is not a tuned figure: it is a bound chosen to sit well
    clear of the name-based policies, which separate NOMINAL by 0.0 points
    because the operator preserves name, docstring and path byte-for-byte.
    The margin assertion below is the substantive claim; the floor only keeps
    a policy from clearing that margin while barely separating anything.
    """
    nominal = results()["e2b_separation"]["NOMINAL"]
    name_based = ("lexical", "hybrid", "embedding")
    for name in ("cdc", "cdc_counterfactual"):
        assert nominal[name]["accepts_gutted"] < 1.0, name
        assert nominal[name]["separation"] > 75.0, name
        for other in name_based:
            margin = nominal[name]["separation"] - nominal[other]["separation"]
            assert margin > 50.0, f"{name} vs {other}: {margin}"


def test_claim_level_secondary_is_retained_with_its_caveat():
    sec = results()["e1_claim_level_secondary"]
    assert "caveat" in sec and "understates" in sec["caveat"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")

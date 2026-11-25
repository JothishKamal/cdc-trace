"""Held-out calibration, test adequacy and the README annotation sheets (review R02)."""
import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from annotation.annotate import merge, score, sheets


def _load(name):
    with open(os.path.join(ROOT, "results", name), encoding="utf-8") as fh:
        return json.load(fh)


def test_held_out_calibration_covers_every_library_pair():
    cal = _load("calibration_ext.json")
    rows = cal["held_out_libraries"].values()
    assert sum(r["n"] for r in rows) == cal["n_pairs"] == 3822
    for r in rows:
        assert 0 <= r["n_implemented"] <= r["n"]
        assert abs(r["fraction_truly_implemented"] - r["n_implemented"] / r["n"]) < 1e-6


def test_held_out_share_rises_from_zero_to_two():
    cal = _load("calibration_ext.json")["held_out_libraries"]
    f = [cal[str(c)]["fraction_truly_implemented"] for c in range(3)]
    assert f[0] < f[1] < f[2]


def test_coverage_lists_all_fifteen_projects():
    cov = _load("coverage.json")
    assert len(cov["authored"]) == 6 and len(cov["libraries"]) == 9
    for group in cov.values():
        for r in group.values():
            assert 0 <= r["covered_statements"] <= r["statements"]
            assert 0 <= r["covered_branches"] <= r["branches"]
            assert r["tests_run"] > 0


def test_readme_sheets_hide_extractor_and_merge_back():
    doc = os.path.join(ROOT, "corpus_ext", "deprecation", "doc.md")
    with tempfile.TemporaryDirectory() as tmp:
        prefix = os.path.join(tmp, "r")
        master, n, k = sheets(prefix, [doc])
        assert n > 0 and 0 < k <= n
        for who in ("A", "B"):
            with open(f"{prefix}_sheet_{who}.csv", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            assert "extracted" not in rows[0] and len(rows) == n
            for r in rows:
                r["is_claim"], r["completed"] = "1", "1"
            with open(f"{prefix}_sheet_{who}.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
        merge(prefix)
        out = score(master)
        assert out["labelled"] == n and out["precision"] == 1.0 and out["tp"] == k
        assert out["agreement"]["gold_raw_agreement"] == 1.0


def test_readme_annotation_is_complete_and_verdicts_cover_every_claim():
    with open(os.path.join(ROOT, "annotation", "readmes", "readme_sentences.csv"), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1032
    for r in rows:
        for c in ("is_claim_a", "completed_a", "is_claim_b", "completed_b"):
            assert r[c] in ("0", "1"), (r["sid"], c)
        assert not (r["is_claim_a"] == "0" and r["completed_a"] == "1")
    ver = _load("readme_verdicts.json")
    assert ver["unmatched"] == {"SUPPORTED": 0, "WEAK": 0, "UNSUPPORTED": 0}
    total = sum(sum(v.values()) for v in ver.values())
    assert total == sum(r["extracted"] == "1" for r in rows) == 145


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")

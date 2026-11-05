"""Invariants of the independent corpus, the LLM baseline tooling and the annotation kit."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from cdc.model import CodeElement
from experiments.external import public_entries
from experiments.llm_score import score


def _el(name, calls=frozenset()):
    return CodeElement(uid=f"m:{name}", kind="function", name=name, path="m.py", lineno=1,
                       doc="", imports=frozenset(), calls=calls, body_ops=frozenset(),
                       is_stub=False, reachable=False)


def test_corpus_ext_has_nine_licensed_pinned_projects():
    with open(os.path.join(ROOT, "corpus_ext", "manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    assert len(man["projects"]) == 9
    for p in man["projects"]:
        assert "==" in p["pypi"]
        assert os.path.exists(os.path.join(ROOT, "corpus_ext", p["name"], "LICENSE")), p["name"]
        assert os.path.isdir(os.path.join(ROOT, p["code_dir"]))


def test_public_entries_reach_callees_of_public_functions():
    els = public_entries([_el("api", frozenset({"_helper"})), _el("_helper"), _el("_unused")])
    reach = {e.name: e.reachable for e in els}
    assert reach == {"api": True, "_helper": True, "_unused": False}


def test_llm_score_counts_missing_and_deleted_as_rejections():
    pairs = [
        {"corpus": "a", "family": "original", "project": "p", "cid": "c1", "uid": "u",
         "round": 0, "operator": "NOMINAL", "pre": "k1", "mut": "k2"},
        {"corpus": "a", "family": "original", "project": "p", "cid": "c2", "uid": "v",
         "round": 0, "operator": "DELETE", "pre": "k1", "mut": None},
        {"corpus": "a", "family": "original", "project": "p", "cid": "c3", "uid": "w",
         "round": 0, "operator": None, "pre": "k1", "mut": "k3"},
    ]
    answers = [{"id": "k1", "answer": "YES"}, {"id": "k2", "answer": "NO"}]
    res = score(pairs, answers)
    assert res["by_set"]["a"]["original"]["NOMINAL"]["separation"] == 100.0
    assert res["by_set"]["a"]["original"]["DELETE"]["separation"] == 100.0
    m = res["confusion"]["a"]["association"]
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (2, 1, 0, 0)


def test_provisional_labels_cover_every_sentence():
    import csv
    path = os.path.join(ROOT, "annotation", "sentences_provisional.csv")
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 123
    assert all(r["is_claim_a"] in ("0", "1") and r["completed_a"] in ("0", "1") for r in rows)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")

"""
X8: tool verdicts on README claims split by the annotators' labels (review item D5).

Joins each extracted README claim with its annotated sentence and counts SUPPORTED, WEAK
and UNSUPPORTED separately for sentences both annotators call completed claims and for
sentences both reject. Writes results/readme_verdicts.json.
"""
from __future__ import annotations

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from experiments import external as X  # noqa: E402
from experiments.revision import write_manifest  # noqa: E402
from cdc.scoring import score_document  # noqa: E402


def _b(v):
    return str(v).strip() == "1"


def run():
    with open(os.path.join(ROOT, "annotation", "readmes", "readme_sentences.csv"), encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["extracted"] == "1"]
    gold = {}
    for r in rows:
        a = _b(r["is_claim_a"]) and _b(r["completed_a"])
        b = _b(r["is_claim_b"]) and _b(r["completed_b"])
        name = r["doc"].split("/")[1]
        gold[(name, " ".join(r["sentence"].split()))] = "claim" if a and b else ("not_claim" if not a and not b else "split")
    X.set_mode("default")
    pristine, _ = X.load_ext("default")
    out = {k: {"SUPPORTED": 0, "WEAK": 0, "UNSUPPORTED": 0} for k in ("claim", "not_claim", "split", "unmatched")}
    for name, (_code, claims, els) in pristine:
        rep = score_document(claims, els)
        for c, res in zip(claims, rep.results):
            g = gold.get((name, " ".join(c.text.split())), "unmatched")
            out[g][res.verdict] += 1
    with open(os.path.join(ROOT, "results", "readme_verdicts.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, sort_keys=True, indent=2)
        fh.write("\n")
    write_manifest()
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

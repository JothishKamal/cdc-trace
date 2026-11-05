"""
Provisional automated labels for annotation/sentences.csv (review items M1, M2).

These labels were written by an LLM (Claude Opus 5.5), not by a person. They are a
placeholder until two human annotators outside the team fill sentences.csv, and
must not be reported as human annotation.

Rule used: is_claim = 1 when the sentence states a checkable property of the code
(behaviour, structure, data or library use); motivation, rationale and advice to
callers are 0. completed = 0 when the claim is phrased as a requirement ("should",
"must", "only ... if"). component is given only when the heading is wrong.

  python annotation/provisional_labels.py   writes annotation/sentences_provisional.csv
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# (document stem, sid) -> (is_claim, completed[, component]); every other sentence is (1, 1).
EXCEPTIONS = {
    ("geocoder", 0): (1, 0),
    ("imageproc", 8): (0, 0),
    ("ledger", 8): (1, 0),
    ("ledger", 16): (1, 1, "Sql storage"),
    ("sessionstore", 7): (0, 0),
    ("sessionstore", 8): (1, 0),
    ("sessionstore", 12): (0, 0),
    ("taskqueue", 0): (1, 0),
}


def main():
    src = os.path.join(HERE, "sentences.csv")
    dst = os.path.join(HERE, "sentences_provisional.csv")
    with open(src, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        stem = r["doc"].split("/")[1]
        lab = EXCEPTIONS.get((stem, int(r["sid"])), (1, 1))
        r["is_claim_a"], r["completed_a"] = str(lab[0]), str(lab[1])
        r["component_a"] = lab[2] if len(lab) > 2 else ""
    with open(dst, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", os.path.relpath(dst, os.path.dirname(HERE)))


if __name__ == "__main__":
    main()

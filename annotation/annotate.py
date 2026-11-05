"""
Claim-annotation kit (review items M1, M2, D5).

  python annotation/annotate.py template [DOC ...]   writes annotation/sentences.csv
  python annotation/annotate.py score   FILE.csv     prints extraction quality

`template` lists every sentence of each design document (Markdown by default;
pass paths to annotate other documents, including real student reports). Two
annotators fill three columns each, independently:

  is_claim      1 if the sentence asserts something the code does or contains
  completed     1 if it describes completed work (0 for plans or requirements)
  component     the component the sentence is about (free text; blank = same as heading)

`score` compares the annotation with the rule-based extractor and reports
precision, recall and F1 of claim extraction (gold = is_claim and completed),
the accuracy of heading-based component association, and, when the file has a
second annotator (columns ending in _b), Cohen's kappa on is_claim.
"""
from __future__ import annotations

import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from cdc.claims import _SENTENCE, _is_assertive, _latex_pairs, _markdown_pairs

COLS = ["doc", "sid", "heading", "sentence", "extracted",
        "is_claim_a", "completed_a", "component_a",
        "is_claim_b", "completed_b", "component_b"]


def sentences(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    pairs = _latex_pairs(text) if path.endswith(".tex") else _markdown_pairs(text)
    out = []
    for heading, paragraph in pairs:
        for s in _SENTENCE.split(paragraph):
            s = s.strip()
            if s:
                out.append((heading, s, int(_is_assertive(s))))
    return out


def template(docs, dst):
    with open(dst, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        for doc in docs:
            rel = os.path.relpath(doc, ROOT).replace(os.sep, "/")
            for i, (h, s, ext) in enumerate(sentences(doc)):
                w.writerow([rel, i, h, s, ext, "", "", "", "", "", ""])
    return dst


def _b(v):
    return str(v).strip() in ("1", "y", "yes", "true", "True")


def kappa(a, b):
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def score(path, who="a"):
    with open(path, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r[f"is_claim_{who}"].strip() != ""]
    if not rows:
        return {"labelled": 0}
    tp = fp = fn = tn = 0
    comp_ok = comp_n = 0
    for r in rows:
        gold = _b(r[f"is_claim_{who}"]) and _b(r[f"completed_{who}"])
        pred = _b(r["extracted"])
        tp += gold and pred
        fp += pred and not gold
        fn += gold and not pred
        tn += not gold and not pred
        if gold and pred:
            comp_n += 1
            want = r[f"component_{who}"].strip() or r["heading"].strip()
            comp_ok += want.lower() == r["heading"].strip().lower()
    p = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    out = {"labelled": len(rows), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
           "precision": round(p, 4), "recall": round(rc, 4),
           "f1": round(2 * p * rc / (p + rc), 4) if p + rc else 0.0,
           "component_accuracy": round(comp_ok / comp_n, 4) if comp_n else None}
    both = [r for r in rows if r.get("is_claim_b", "").strip() != ""]
    if both:
        out["kappa_is_claim"] = round(kappa(
            [_b(r["is_claim_a"]) for r in both], [_b(r["is_claim_b"]) for r in both]), 4)
        out["double_labelled"] = len(both)
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "template":
        docs = sys.argv[2:] or sorted(glob.glob(os.path.join(ROOT, "corpus", "*", "doc.md")))
        dst = os.path.join(ROOT, "annotation", "sentences.csv")
        template(docs, dst)
        print("wrote", os.path.relpath(dst, ROOT))
    elif len(sys.argv) == 3 and sys.argv[1] == "score":
        import json
        print(json.dumps(score(sys.argv[2]), indent=2))
    else:
        print(__doc__)

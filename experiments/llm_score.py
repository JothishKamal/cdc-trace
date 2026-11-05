"""
L2: score the code-reading LLM baseline from llm/answers.jsonl. No network.

A pair is accepted on a side when the model answered YES for that side's prompt;
a deleted element, a missing answer or an unparsed answer counts as a rejection
(and is counted). Writes results/llm.json with separation per corpus, family and
operator, with 95% cluster-bootstrap intervals, and confusion matrices on the
original-operator pairs under both labellings. No threshold is tuned.
"""
from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from experiments.revision import BOOT, confusion
from experiments.run_all import SEED, r6


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def accepted(ans, key):
    return key is not None and ans.get(key) == "YES"


def sep_with_ci(rows, ans, seed):
    clusters = {}
    for r in rows:
        clusters.setdefault((r["project"], r["cid"]), []).append(
            (int(accepted(ans, r["pre"])), int(accepted(ans, r["mut"]))))
    n = len(rows)
    a_p = sum(a for v in clusters.values() for a, _ in v)
    a_m = sum(b for v in clusters.values() for _, b in v)
    keys = sorted(clusters)
    rng = random.Random(seed)
    stats = []
    for _ in range(BOOT):
        sp = sm = k = 0
        for _i in keys:
            for a, b in clusters[keys[rng.randrange(len(keys))]]:
                sp += a
                sm += b
                k += 1
        stats.append(100.0 * (sp - sm) / k if k else 0.0)
    stats.sort()
    return {"n": n, "n_clusters": len(keys),
            "accepts_pristine": r6(100.0 * a_p / n if n else 0),
            "accepts_mutated": r6(100.0 * a_m / n if n else 0),
            "separation": r6(100.0 * (a_p - a_m) / n if n else 0),
            "cluster_ci95": [r6(stats[int(0.025 * BOOT)]), r6(stats[int(0.975 * BOOT) - 1])]}


def is_gap(r, labelling):
    if r["operator"] is None:
        return False
    return not (labelling == "behavioural" and r["operator"] == "RENAME")


def score(pairs, answers):
    ans = {a["id"]: a["answer"] for a in answers}
    needed = {k for r in pairs for k in (r["pre"], r["mut"]) if k}
    out = {"prompts_needed": len(needed), "prompts_answered": len(needed & set(ans)),
           "unparsed": sum(1 for k in needed if ans.get(k) == "UNPARSED"),
           "by_set": {}, "confusion": {}}
    groups = {}
    for r in pairs:
        if r["operator"] is None:
            continue
        groups.setdefault((r["corpus"], r["family"], r["operator"]), []).append(r)
    for (corpus, family, op), rows in sorted(groups.items()):
        out["by_set"].setdefault(corpus, {}).setdefault(family, {})[op] = sep_with_ci(
            rows, ans, SEED + len(op) + len(family))
    for corpus in sorted({r["corpus"] for r in pairs}):
        rows = [r for r in pairs if r["corpus"] == corpus and r["family"] == "original"]
        out["confusion"][corpus] = {
            lab: confusion([(is_gap(r, lab), accepted(ans, r["mut"])) for r in rows])
            for lab in ("association", "behavioural")}
    return out


def main():
    pairs = load(os.path.join(ROOT, "llm", "pairs.jsonl"))
    answers = load(os.path.join(ROOT, "llm", "answers.jsonl"))
    info_path = os.path.join(ROOT, "llm", "run_info.json")
    res = score(pairs, answers)
    if os.path.exists(info_path):
        with open(info_path, encoding="utf-8") as fh:
            res["run_info"] = json.load(fh)
    with open(os.path.join(ROOT, "results", "llm.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, sort_keys=True, indent=2)
        fh.write("\n")
    print(f"{res['prompts_answered']}/{res['prompts_needed']} prompts answered, "
          f"{res['unparsed']} unparsed")


if __name__ == "__main__":
    main()

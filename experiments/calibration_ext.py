"""
X6: calibration of the corroboration count C on held-out projects (review R02, 12.5).

Repeats E5 of run_all.py, unchanged, on the nine independently written libraries in
corpus_ext/: for every claim-element pair in three mutation rounds, the share of pairs
whose element was left intact, by C. The authored-corpus bins are copied alongside for
comparison. Deterministic; no network. Writes results/calibration_ext.json.
"""
from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from experiments import external as X
from experiments.revision import ROUNDS, write_manifest
from experiments.run_all import RATE, SEED, build_items, e5_calibration


def run():
    X.set_mode("default")
    pristine, man = X.load_ext("default")
    items = []
    for pi, (name, (code_dir, claims, elements)) in enumerate(pristine):
        for ri in range(ROUNDS):
            rng = random.Random(SEED + 17 * (pi + 1) + 1009 * (ri + 1))
            pairs, _claims = build_items(code_dir, claims, elements, rng, RATE, name, ri)
            items.extend(pairs)
    held_out = e5_calibration(items)
    with open(os.path.join(ROOT, "results", "results.json"), encoding="utf-8") as fh:
        authored = json.load(fh)["e5_calibration"]
    out = {"n_pairs": len(items), "held_out_libraries": held_out, "authored": authored}
    with open(os.path.join(ROOT, "results", "calibration_ext.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, sort_keys=True, indent=2)
        fh.write("\n")
    write_manifest()
    return out


if __name__ == "__main__":
    r = run()
    print("pairs", r["n_pairs"])
    for c, rec in r["held_out_libraries"].items():
        a = r["authored"].get(c)
        print(f"C={c}: libraries {rec['n_implemented']}/{rec['n']} = {rec['fraction_truly_implemented']:.3f}"
              + (f" | authored {a['n_implemented']}/{a['n']} = {a['fraction_truly_implemented']:.3f}" if a else ""))

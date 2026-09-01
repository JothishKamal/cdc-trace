"""Print the corrected E1-E6 tables with Wilson 95% intervals."""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PREFERRED = (
    "lexical",
    "embedding",
    "hybrid",
    "evidence_count",
    "channel_count",
    "cdc",
    "cdc_counterfactual",
)
OPERATOR_ORDER = ("NOMINAL", "STUB", "WEAKEN", "RENAME", "DELETE")

E1_DISCLOSURE = (
    "The 60/40 split is not group-aware: the same (project, cid, uid) pair can\n"
    "appear on both sides of it across mutation rounds, so E1 is optimistic and\n"
    "is not a held-out result. The primary artifact is the E2b separation table\n"
    "below, which is not split-based."
)

DELETE_CAPTION = (
    "DELETE removes the element from the tree entirely, so its gutted column is\n"
    "0.0 for all seven policies by construction and its pairs are free true\n"
    "positives. Read the DELETE row as a sanity check, not as evidence."
)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h) * 100, min(1.0, c + h) * 100)


def load_results():
    path = os.path.join(ROOT, "results", "results.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def ordered_policies(keys):
    out = [name for name in PREFERRED if name in keys]
    out += [name for name in sorted(keys) if name not in out]
    return out


def ordered_operators(keys):
    out = [op for op in OPERATOR_ORDER if op in keys]
    out += [op for op in sorted(keys) if op not in out]
    return out


def pct_ci(rate, k, n):
    lo, hi = wilson(k, n)
    return f"{100 * rate:6.2f} ({lo:5.1f}-{hi:5.1f})"


def rule(width=96):
    print("-" * width)


def heading(text):
    print()
    print(f"=== {text} ===")


def line(policy, m):
    p = pct_ci(m["precision"], m["tp"], m["tp"] + m["fp"])
    r = pct_ci(m["recall"], m["tp"], m["tp"] + m["fn"])
    fir = pct_ci(m["false_implemented_rate"], m["n_false_implemented"], m["n_mutated"])
    return f"{policy:<22} {p:>18} {r:>18} {100 * m['f1']:6.2f} {fir:>18}"


def gap_table(block):
    print(f"{'policy':<22} {'prec % (95% CI)':>18} {'rec % (95% CI)':>18}"
          f" {'F1':>6} {'FIR % (95% CI)':>18}")
    for policy in ordered_policies(block):
        print(line(policy, block[policy]))


def print_e1(res):
    main = res["e1_main"]
    heading("E1 pair-level comparison (gap class)")
    any_row = main[next(iter(main))]
    print(f"n = {any_row['n']} (claim, element) pairs;"
          f" {any_row['n_mutated']} carry a gap-inducing mutation")
    gap_table(main)
    print()
    print(E1_DISCLOSURE)

    excl = res.get("e1_main_excluding_delete")
    if not excl:
        return
    excl_row = excl[next(iter(excl))]
    n_delete = any_row["n"] - excl_row["n"]
    print()
    print(f"--- E1 sensitivity: the same table with the {n_delete} DELETE pairs"
          f" removed ---")
    print(DELETE_CAPTION)
    print(f"n = {excl_row['n']} pairs; {excl_row['n_mutated']} mutated")
    gap_table(excl)


def print_e2b(res):
    sep = res["e2b_separation"]
    heading("E2b pristine-versus-gutted separation (PRIMARY COMPARISON)")
    print("Acceptance of the pristine element against acceptance of the same")
    print("element after mutation, per operator. A policy that refuses")
    print("everything scores a flattering false-implemented rate while")
    print("separating nothing; only the gap between the two columns is skill.")
    for op in ordered_operators(sep):
        block = sep[op]
        any_row = block[next(iter(block))]
        print()
        print(f"[{op}]  n = {any_row['n']} mutated pairs")
        if op == "DELETE":
            print(DELETE_CAPTION)
        rule()
        print(f"{'policy':<22} {'accepts pristine % (95% CI)':>28}"
              f" {'accepts gutted % (95% CI)':>28} {'sep. pp':>8}")
        for policy in ordered_policies(block):
            row = block[policy]
            n = row["n"]
            p = pct_ci(row["accepts_pristine"] / 100.0, row["n_accepts_pristine"], n)
            g = pct_ci(row["accepts_gutted"] / 100.0, row["n_accepts_gutted"], n)
            print(f"{policy:<22} {p:>28} {g:>28} {row['separation']:8.1f}")


def print_e2(res):
    e2 = res["e2_by_operator"]
    heading("E2 per-operator breakdown (gap class)")
    for op in ordered_operators(e2):
        block = e2[op]
        any_row = block[next(iter(block))]
        print()
        print(f"[{op}]  n = {any_row['n']} pairs;"
              f" {any_row['n_mutated']} mutated")
        if op == "DELETE":
            print(DELETE_CAPTION)
        rule()
        gap_table(block)


def print_e4(res):
    heading("E4 cdc versus cdc_counterfactual")
    print("cdc_counterfactual keeps the corroboration count but drops the")
    print("channel-disjointness requirement.")
    rule()
    gap_table(res["e4_counterfactual"])


def print_e5(res):
    e5 = res["e5_calibration"]
    heading("E5 calibration of C")
    print(f"{'C':>3} {'n':>6} {'implemented':>12}"
          f" {'fraction truly implemented % (95% CI)':>40}")
    for key in sorted(e5, key=lambda k: int(e5[k]["c"])):
        row = e5[key]
        cell = pct_ci(row["fraction_truly_implemented"],
                      row["n_implemented"], row["n"])
        print(f"{row['c']:>3} {row['n']:>6} {row['n_implemented']:>12} {cell:>40}")


def print_e1_secondary(res):
    sec = res["e1_claim_level_secondary"]
    heading("E1 secondary: claim-level labelling (diagnostic only)")
    print("thresholds:", json.dumps(sec.get("thresholds", {}), sort_keys=True))
    rule()
    print(sec["caveat"])
    gap_table(sec["policies"])


def main():
    res = load_results()
    print(f"seed={res['seed']}  k_min={res['k_min']}")
    print("baseline_thresholds:", json.dumps(res["baseline_thresholds"], sort_keys=True))
    print_e1(res)
    print_e2b(res)
    print_e2(res)
    print_e4(res)
    print_e5(res)
    print_e1_secondary(res)


if __name__ == "__main__":
    main()

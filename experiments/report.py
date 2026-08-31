"""Print E0–E6 tables with Wilson 95% intervals."""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def pct_ci(rate, k, n):
    lo, hi = wilson(k, n)
    return f"{100 * rate:6.2f} ({lo:5.1f}-{hi:5.1f})"


def line(policy, m):
    p = pct_ci(m["precision"], m["tp"], m["tp"] + m["fp"])
    r = pct_ci(m["recall"], m["tp"], m["tp"] + m["fn"])
    fir = pct_ci(m["false_implemented_rate"], m["n_false_implemented"], m["n_mutated"])
    return f"{policy:<22} {p:>18} {r:>18} {100 * m['f1']:6.2f} {fir:>18}"


def main():
    res = load_results()
    print(f"seed={res['seed']}  k_min={res['k_min']}")
    print("baseline_thresholds:", json.dumps(res["baseline_thresholds"], sort_keys=True))
    print()
    print("=== E1 main comparison (held-out, gap class) ===")
    print(f"{'policy':<22} {'prec % (95% CI)':>18} {'rec % (95% CI)':>18} {'F1':>6} {'FIR % (95% CI)':>18}")
    for policy, m in sorted(res["e1_main"].items()):
        print(line(policy, m))
    print()
    print("=== E2 NOMINAL false-implemented rate ===")
    nominal = res["e2_by_operator"]["NOMINAL"]
    print(f"{'policy':<22} {'FIR % (95% CI)':>18}")
    for policy, m in sorted(nominal.items()):
        fir = pct_ci(m["false_implemented_rate"], m["n_false_implemented"], m["n_mutated"])
        print(f"{policy:<22} {fir:>18}")
    print()
    print("=== E4 cdc vs cdc_counterfactual ===")
    print(f"{'policy':<22} {'F1':>6} {'FIR % (95% CI)':>18}")
    for policy in ("cdc", "cdc_counterfactual"):
        m = res["e4_counterfactual"][policy]
        fir = pct_ci(m["false_implemented_rate"], m["n_false_implemented"], m["n_mutated"])
        print(f"{policy:<22} {100 * m['f1']:6.2f} {fir:>18}")


if __name__ == "__main__":
    main()

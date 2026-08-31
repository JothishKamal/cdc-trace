"""Render fig1–fig6 from results/results.json. No network."""
from __future__ import annotations

import json
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
DPI = 150
PREFERRED = (
    "lexical",
    "embedding",
    "hybrid",
    "evidence_count",
    "channel_count",
    "cdc",
    "cdc_counterfactual",
)


def load_results():
    path = os.path.join(ROOT, "results", "results.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(fig, path):
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def ordered_policies(keys):
    seen = []
    for name in PREFERRED:
        if name in keys:
            seen.append(name)
    for name in sorted(keys):
        if name not in seen and name != "mode":
            seen.append(name)
    return seen


def _box(ax, x, y, w, h, text, fc="#e8eef4", ec="#2c3e50", fs=9, fw="normal"):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=fc, edgecolor=ec, linewidth=1.2, zorder=2,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, fontweight=fw, zorder=3)
    return p


def _arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=12,
        color="#2c3e50", lw=1.4, zorder=1,
    ))


def fig1_pipeline(path):
    fig, ax = plt.subplots(figsize=(10.5, 8.2), layout="constrained")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Channel-disjoint corroboration pipeline", fontsize=13, pad=8)

    _box(ax, 0.4, 8.35, 4.0, 1.15,
         "Claims document\nMarkdown / LaTeX", fc="#d6eaf8")
    _box(ax, 5.6, 8.35, 4.0, 1.15,
         "Code archive\nPython repository", fc="#d5f5e3")
    _arrow(ax, 2.4, 8.35, 2.4, 7.55)
    _arrow(ax, 7.6, 8.35, 7.6, 7.55)

    _box(ax, 0.4, 6.35, 4.0, 1.15,
         "Extract claims\nterms, implied libraries", fc="#d6eaf8")
    _box(ax, 5.6, 6.35, 4.0, 1.15,
         "Extract code\nAST, calls, stubs, tests", fc="#d5f5e3")
    _arrow(ax, 2.4, 6.35, 4.6, 5.55)
    _arrow(ax, 7.6, 6.35, 5.4, 5.55)

    _box(ax, 2.0, 4.35, 6.0, 1.15,
         "Evidence gathering\nNAME  DOC  IMPORT  CALL  SCHEMA  TEST  BODY",
         fc="#fdebd0")
    _arrow(ax, 5.0, 4.35, 5.0, 3.55)

    _box(ax, 2.0, 2.35, 6.0, 1.15,
         "Corroboration\nconflict graph  ·  C = max independent set  ·  ablation",
         fc="#f5b7b1")
    _arrow(ax, 5.0, 2.35, 5.0, 1.55)

    _box(ax, 2.0, 0.35, 6.0, 1.15,
         "Scoring\nSUPPORTED / WEAK / UNSUPPORTED  →  gap score",
         fc="#d7bde2")
    save(fig, path)


def fig2_dependent_example(path):
    fig, ax = plt.subplots(figsize=(11.2, 7.6), layout="constrained")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.4)
    ax.axis("off")
    ax.set_title(
        "Worked example: NAME and DOC share token and file (AES-GCM stub)",
        fontsize=12, pad=8,
    )

    _box(ax, 0.35, 7.15, 11.3, 0.9,
         'Claim:  "AES-GCM encrypts the session token"',
         fc="#d6eaf8", fs=11, fw="bold")

    _box(ax, 0.35, 4.55, 5.4, 2.35,
         "Stub (NOMINAL)\n\n"
         "def aes_gcm_encrypt_token(token):\n"
         '    """Encrypts the session token with AES-GCM."""\n'
         "    raise NotImplementedError",
         fc="#f4f6f7", fs=8.5)

    _box(ax, 6.15, 5.85, 5.5, 0.95,
         "e1  NAME   aes_gcm_encrypt_token\n"
         "{ch:NAME, tok:aes_gcm, file:crypto/aes.py}",
         fc="#fad7a0", fs=8)
    _box(ax, 6.15, 4.55, 5.5, 0.95,
         "e2  DOC    docstring restates the name\n"
         "{ch:DOC, tok:aes_gcm, file:crypto/aes.py}",
         fc="#fad7a0", fs=8)

    ax.annotate(
        "", xy=(8.9, 5.85), xytext=(8.9, 5.50),
        arrowprops=dict(arrowstyle="-", color="#922b21", lw=2),
    )
    ax.text(9.05, 5.68, "share tok + file", fontsize=8, color="#922b21", va="center")

    _box(ax, 6.15, 3.15, 5.5, 0.95,
         "e3  IMPORT  (optional, independent)\n"
         "{ch:IMPORT, lib:cryptography, file:session.py}",
         fc="#d5f5e3", fs=8)

    _box(ax, 0.35, 1.55, 5.4, 2.55,
         "Naive count treats each match as a vote:\n"
         "  NAME + DOC  =  2  (or 3 with IMPORT)\n\n"
         "Corroboration counts only disjoint provenance:\n"
         "  NAME and DOC are one witness\n"
         "  C = 1, not 2\n"
         "  with independent IMPORT, C = 2, not 3",
         fc="#f5eef8", fs=8.5)

    _box(ax, 6.15, 1.55, 5.5, 1.25,
         "Stub has no BODY channel.\n"
         "Lexical / embedding / hybrid all fire\n"
         "from the identifier string alone.",
         fc="#f5b7b1", fs=8.5)

    ax.text(8.9, 0.85, "C(claim) = size of a maximum pairwise-disjoint evidence set",
            ha="center", fontsize=9)
    save(fig, path)


def fig3_policy_comparison(res, path):
    e1 = res.get("e1_main", {})
    fig, ax = plt.subplots(figsize=(10.5, 5.6), layout="constrained")
    ax.set_xlabel("Policy")
    ax.set_ylabel("Score")
    ax.set_title("E1 policy comparison (held-out, gap class)")
    ax.set_ylim(0.0, 1.05)

    if not isinstance(e1, dict) or not e1:
        save(fig, path)
        return

    policies = ordered_policies(e1.keys())
    f1s, firs = [], []
    lo_err, hi_err = [], []
    have_ci = True
    for p in policies:
        m = e1.get(p) or {}
        f1s.append(float(m.get("f1", 0.0)))
        fir = float(m.get("false_implemented_rate", 0.0))
        firs.append(fir)
        k, n = m.get("n_false_implemented"), m.get("n_mutated")
        if isinstance(k, (int, float)) and isinstance(n, (int, float)):
            lo, hi = wilson(int(k), int(n))
            lo_err.append(max(0.0, fir - lo))
            hi_err.append(max(0.0, hi - fir))
        else:
            have_ci = False

    x = list(range(len(policies)))
    w = 0.38
    xl = [i - w / 2 for i in x]
    xr = [i + w / 2 for i in x]
    ax.bar(xl, f1s, w, label="F1")
    if have_ci and lo_err and hi_err:
        ax.bar(xr, firs, w, label="False-implemented rate",
               yerr=[lo_err, hi_err], capsize=3, error_kw={"linewidth": 1.0})
    else:
        ax.bar(xr, firs, w, label="False-implemented rate")
    ax.set_xticks(x)
    ax.set_xticklabels(policies, rotation=25, ha="right")
    ax.legend()
    save(fig, path)


def fig4_ablation(res, path):
    e3 = res.get("e3_identifier_ablation", {})
    fig, ax = plt.subplots(figsize=(9.5, 5.6), layout="constrained")
    ax.set_xlabel("Identifier-ablation fraction")
    ax.set_ylabel("F1")
    ax.set_title("E3 identifier ablation")
    ax.set_ylim(0.0, 1.05)
    ax.set_xlim(-0.05, 1.05)

    if not isinstance(e3, dict):
        save(fig, path)
        return

    frac_keys = []
    for key in e3:
        try:
            frac_keys.append((float(key), key))
        except (TypeError, ValueError):
            continue
    frac_keys.sort()

    policy_names = set()
    for _, key in frac_keys:
        block = e3.get(key) or {}
        if isinstance(block, dict):
            policy_names.update(k for k, v in block.items() if isinstance(v, dict))
    policies = ordered_policies(policy_names)

    for policy in policies:
        xs, ys = [], []
        for frac, key in frac_keys:
            block = e3.get(key) or {}
            rec = block.get(policy) if isinstance(block, dict) else None
            if isinstance(rec, dict) and "f1" in rec:
                xs.append(frac)
                ys.append(float(rec["f1"]))
        if xs:
            ax.plot(xs, ys, marker="o", label=policy)

    if policies:
        ax.legend(loc="best", fontsize=8)
    save(fig, path)


def fig5_calibration(res, path):
    e5 = res.get("e5_calibration", {})
    fig, ax = plt.subplots(figsize=(8.4, 5.4), layout="constrained")
    ax.set_xlabel("C (corroboration)")
    ax.set_ylabel("Fraction truly implemented")
    ax.set_title("E5 calibration of C")
    ax.set_ylim(0.0, 1.15)

    rows = []
    if isinstance(e5, dict):
        for key, val in e5.items():
            if not isinstance(val, dict):
                continue
            try:
                c = int(val.get("c", key))
            except (TypeError, ValueError):
                continue
            frac = val.get("fraction_truly_implemented")
            if frac is None:
                continue
            rows.append((c, float(frac), val.get("n"), val.get("n_implemented")))
    rows.sort()

    if rows:
        cs = [r[0] for r in rows]
        fracs = [r[1] for r in rows]
        ax.bar(cs, fracs, width=0.6)
        ax.set_xticks(cs)
        for c, frac, n, n_impl in rows:
            label = f"{frac:.2f}"
            extra = []
            if isinstance(n, (int, float)):
                extra.append(f"n={int(n)}")
            if isinstance(n_impl, (int, float)):
                extra.append(f"{int(n_impl)} impl.")
            if extra:
                label = f"{label}\n" + "\n".join(extra)
            ax.text(c, min(frac + 0.04, 1.08), label, ha="center", va="bottom", fontsize=8)
    save(fig, path)


def fig6_operator_heatmap(res, path):
    e2 = res.get("e2_by_operator", {})
    fig, ax = plt.subplots(figsize=(9.2, 5.8), layout="constrained")
    ax.set_title("E2 per-operator recall")
    ax.set_xlabel("Operator")
    ax.set_ylabel("Policy")

    if not isinstance(e2, dict) or not e2:
        save(fig, path)
        return

    op_pref = ("DELETE", "NOMINAL", "RENAME", "STUB", "WEAKEN")
    operators = [o for o in op_pref if o in e2]
    operators += [o for o in sorted(e2) if o not in operators]

    policy_names = set()
    for op in operators:
        block = e2.get(op) or {}
        if isinstance(block, dict):
            policy_names.update(k for k, v in block.items() if isinstance(v, dict))
    policies = ordered_policies(policy_names)

    data = []
    for pol in policies:
        row = []
        for op in operators:
            rec = (e2.get(op) or {}).get(pol) or {}
            if isinstance(rec, dict) and "recall" in rec:
                row.append(float(rec["recall"]))
            else:
                row.append(float("nan"))
        data.append(row)

    im = ax.imshow(data, cmap="viridis", vmin=0.0, vmax=1.0, aspect="auto")
    fig.colorbar(im, ax=ax, label="Recall")
    ax.set_xticks(range(len(operators)), labels=operators)
    ax.set_yticks(range(len(policies)), labels=policies)
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            if val != val:
                continue
            color = "white" if val < 0.45 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=8)
    save(fig, path)


def main():
    res = load_results()
    os.makedirs(ASSETS, exist_ok=True)
    fig1_pipeline(os.path.join(ASSETS, "fig1.png"))
    fig2_dependent_example(os.path.join(ASSETS, "fig2.png"))
    fig3_policy_comparison(res, os.path.join(ASSETS, "fig3.png"))
    fig4_ablation(res, os.path.join(ASSETS, "fig4.png"))
    fig5_calibration(res, os.path.join(ASSETS, "fig5.png"))
    fig6_operator_heatmap(res, os.path.join(ASSETS, "fig6.png"))


if __name__ == "__main__":
    main()

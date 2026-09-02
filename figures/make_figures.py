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
MARKERS = ("o", "s", "^", "D", "v", "P", "X")
DASHES = ("-", "--", "-.", ":", (0, (3, 1, 1, 1)), (0, (5, 2)), (0, (1, 1)))


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


def fig3_separation(res, path, operator="NOMINAL"):
    """Accepts-pristine against accepts-gutted per policy, one operator."""
    sep = res.get("e2b_separation", {})
    block = sep.get(operator, {}) if isinstance(sep, dict) else {}
    fig, ax = plt.subplots(figsize=(10.5, 5.8), layout="constrained")
    ax.set_xlabel("Policy")
    ax.set_ylabel("Acceptance rate")
    ax.set_title(
        f"E2b pristine-versus-gutted separation ({operator})"
    )
    ax.set_ylim(0.0, 1.35)

    if not isinstance(block, dict) or not block:
        save(fig, path)
        return

    policies = ordered_policies(block.keys())
    n = 0
    pris, gut, seps = [], [], []
    pris_err = [[], []]
    gut_err = [[], []]
    for name in policies:
        row = block.get(name) or {}
        n = int(row.get("n") or 0)
        p = float(row.get("accepts_pristine", 0.0)) / 100.0
        g = float(row.get("accepts_gutted", 0.0)) / 100.0
        pris.append(p)
        gut.append(g)
        seps.append(float(row.get("separation", 0.0)))
        for val, key, err in (
            (p, "n_accepts_pristine", pris_err),
            (g, "n_accepts_gutted", gut_err),
        ):
            k = row.get(key)
            if isinstance(k, (int, float)) and n:
                lo, hi = wilson(int(k), n)
                err[0].append(max(0.0, val - lo))
                err[1].append(max(0.0, hi - val))
            else:
                err[0].append(0.0)
                err[1].append(0.0)

    x = list(range(len(policies)))
    w = 0.38
    xl = [i - w / 2 for i in x]
    xr = [i + w / 2 for i in x]
    ax.bar(xl, pris, w, label="Accepts pristine element",
           color="#2e86c1", edgecolor="white", linewidth=0.8,
           yerr=pris_err, capsize=3, error_kw={"linewidth": 1.0})
    ax.bar(xr, gut, w, label="Accepts gutted element",
           color="#c0392b", edgecolor="white", linewidth=0.8,
           yerr=gut_err, capsize=3, error_kw={"linewidth": 1.0})
    for i, s in enumerate(seps):
        ax.text(i, 1.05, f"sep {s:.1f} pp", ha="center", va="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(policies, rotation=25, ha="right")
    ax.legend(loc="upper center", ncol=2, fontsize=8, framealpha=1.0)
    ax.text(
        0.0, -0.30,
        f"n = {n} mutated (claim, element) pairs. Bars carry Wilson 95%"
        " intervals.\nOnly the gap between the two bars is skill: a policy"
        " that refuses everything\nseparates nothing while scoring a"
        " flattering false-implemented rate.",
        transform=ax.transAxes, fontsize=8, va="top",
    )
    save(fig, path)


def fig4_ablation(res, path):
    """Pristine-versus-gutted separation against identifier-ablation fraction."""
    e3 = res.get("e3_identifier_ablation", {})
    fig, ax = plt.subplots(figsize=(9.5, 6.4), layout="constrained")
    ax.set_xlabel("Identifier-ablation fraction")
    ax.set_ylabel("Separation (percentage points)")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-4.0, 104.0)

    if not isinstance(e3, dict):
        save(fig, path)
        return

    operator = e3.get("headline_operator", "NOMINAL")
    ax.set_title(
        f"E3 identifier ablation: separation on {operator}"
    )

    frac_keys = []
    for key in e3:
        try:
            frac_keys.append((float(key), key))
        except (TypeError, ValueError):
            continue
    frac_keys.sort()

    policy_names = set()
    for _, key in frac_keys:
        block = (e3.get(key) or {}).get(operator) or {}
        if isinstance(block, dict):
            policy_names.update(k for k, v in block.items() if isinstance(v, dict))
    policies = ordered_policies(policy_names)

    ns = []
    for policy in policies:
        xs, ys = [], []
        for frac, key in frac_keys:
            block = (e3.get(key) or {}).get(operator) or {}
            rec = block.get(policy) if isinstance(block, dict) else None
            if isinstance(rec, dict) and "separation" in rec:
                xs.append(frac)
                ys.append(float(rec["separation"]))
                if rec.get("n"):
                    ns.append((frac, int(rec["n"])))
        if xs:
            # lexical, embedding and hybrid all sit flat on 0.0 for the whole
            # sweep. Distinct dash patterns and markers keep a hidden line
            # visible under the one drawn on top of it.
            i = policies.index(policy)
            ax.plot(
                xs, ys,
                marker=MARKERS[i % len(MARKERS)],
                linestyle=DASHES[i % len(DASHES)],
                markersize=6 - 0.4 * i, linewidth=1.6,
                label=policy,
            )

    if policies:
        ax.legend(loc="upper right", fontsize=8)

    counts = ", ".join(f"{f:g}: n={n}" for f, n in sorted(dict(ns).items()))
    ax.text(
        0.0, -0.13,
        "Separation is accepts-pristine minus accepts-gutted, in percentage"
        " points, on the\n"
        f"{operator} operator -- the same measure as fig3. Mutated pairs per"
        f" fraction: {counts}.\n"
        "lexical, embedding and hybrid lie flat on 0.0 at every fraction:"
        " NOMINAL leaves name,\n"
        "docstring and path unchanged and those are the only fields they read,"
        " so they cannot\n"
        "separate at any ablation level. cdc separation falls as identifiers"
        " are destroyed --\n"
        "NAME is one of the seven evidence channels, so this is a real cost of"
        " the method.",
        transform=ax.transAxes, fontsize=8, va="top",
    )
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
        err = [[], []]
        for _c, frac, n, n_impl in rows:
            if isinstance(n, (int, float)) and isinstance(n_impl, (int, float)):
                lo, hi = wilson(int(n_impl), int(n))
                err[0].append(max(0.0, frac - lo))
                err[1].append(max(0.0, hi - frac))
            else:
                err[0].append(0.0)
                err[1].append(0.0)
        ax.bar(cs, fracs, width=0.6, yerr=err, capsize=4,
               error_kw={"linewidth": 1.0})
        ax.set_xticks(cs)
        for i, (c, frac, n, n_impl) in enumerate(rows):
            label = f"{frac:.2f}"
            extra = []
            if isinstance(n, (int, float)):
                extra.append(f"n={int(n)}")
            if isinstance(n_impl, (int, float)):
                extra.append(f"{int(n_impl)} impl.")
            if extra:
                label = f"{label}\n" + "\n".join(extra)
            top = min(frac + err[1][i] + 0.02, 1.15)
            ax.text(c, top, label, ha="center", va="bottom", fontsize=8)
        ax.set_ylim(0.0, 1.32)
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
    if "DELETE" in operators:
        ax.text(
            0.0, -0.12,
            "DELETE removes the element from the tree entirely, so every"
            " policy scores 1.00 there by construction:\nthose pairs are free"
            " true positives, not evidence of detection.",
            transform=ax.transAxes, fontsize=8, va="top",
        )
    save(fig, path)


def main():
    res = load_results()
    os.makedirs(ASSETS, exist_ok=True)
    fig1_pipeline(os.path.join(ASSETS, "fig1.png"))
    fig2_dependent_example(os.path.join(ASSETS, "fig2.png"))
    fig3_separation(res, os.path.join(ASSETS, "fig3.png"))
    fig4_ablation(res, os.path.join(ASSETS, "fig4.png"))
    fig5_calibration(res, os.path.join(ASSETS, "fig5.png"))
    fig6_operator_heatmap(res, os.path.join(ASSETS, "fig6.png"))


if __name__ == "__main__":
    main()

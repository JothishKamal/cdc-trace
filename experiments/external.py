"""
X1-X5: the protocol of revision.py on an independently written corpus (corpus_ext/):
nine small PyPI libraries chosen by a fixed rule, with claims extracted by the
same rule from each README. Deterministic; no network. Writes results/external.json.

Settings are carried over from the authored corpus unchanged (thresholds tuned
there, k_min = 2, emission threshold 0.15). Two variants are reported:
  thr0    emission threshold 0 (no item is filtered by strength)
  public  public functions (no leading underscore) also count as entry points,
          since a library has no main
  X1  pristine claim-level verdicts and pair statistics
  X2  separation per operator (cluster-bootstrap intervals)
  X3  leave-one-project-out confusion matrices, thresholds tuned on corpus_ext
  X4  thresholds transferred from the authored corpus
  X5  whole-project claim support (any-element and pooled)
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from cdc import codebase as cb
from cdc import evidence as ev_mod
from cdc.claims import extract_claims
from cdc.corroborate import corroboration
from cdc.mutate import OPERATORS
from cdc.policies import POLICIES
from cdc.scoring import score_document
from experiments import revision as R
from experiments.run_all import COUNT_POLICIES, SCORE_POLICIES, build_embedder, r6

_ORIG_EXTRACT = cb.extract_codebase


def public_entries(elements):
    names = {e.name for e in elements
             if e.kind in {"function", "method", "class"} and not e.name.startswith("_")}
    reset = [dataclasses.replace(e, reachable=False) for e in elements]
    return cb._apply_reachability(reset, names)


def load_ext(mode):
    with open(os.path.join(ROOT, "corpus_ext", "manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    out = []
    for p in man["projects"]:
        code = os.path.join(ROOT, p["code_dir"])
        els = _ORIG_EXTRACT(code)
        if mode == "public":
            els = public_entries(els)
        with open(os.path.join(ROOT, p["doc_md"]), encoding="utf-8") as fh:
            claims = extract_claims(fh.read(), "md")
        out.append((p["name"], (code, claims, els)))
    return out, man


def set_mode(mode):
    R._EV_CACHE.clear()
    if mode == "public":
        R.extract_codebase = lambda root: public_entries(_ORIG_EXTRACT(root))
    else:
        R.extract_codebase = _ORIG_EXTRACT
    thr = 0.0 if mode == "thr0" else 0.15
    R.DEFAULT["min_strength"] = thr
    for v in R.VARIANTS.values():
        v.pop("min_strength", None)


def pristine_stats(pristine, thr):
    out = {}
    for name, (code, claims, els) in pristine:
        rep = score_document(claims, els)
        verdicts = [r.verdict for r in rep.results]
        pairs = c2 = claims_any = 0
        for c in claims:
            by = {}
            for e in ev_mod.gather(c, els, min_strength=thr):
                by.setdefault(e.element, []).append(e)
            pairs += len(by)
            k = sum(corroboration(v) >= 2 for v in by.values())
            c2 += k
            claims_any += k > 0
        out[name] = {
            "functions": sum(1 for el in els if el.kind in {"function", "method"}),
            "elements": len(els), "tests": sum(e.kind == "test" for e in els),
            "claims": len(claims), "pairs": pairs, "pairs_C2": c2,
            "claims_any_element_C2": claims_any,
            "supported": verdicts.count("SUPPORTED"), "weak": verdicts.count("WEAK"),
            "unsupported": verdicts.count("UNSUPPORTED"),
        }
    return out


def run_mode(mode, authored_th):
    set_mode(mode)
    pristine, man = load_ext(mode)
    embedder = build_embedder(pristine)
    pairs = R.build_pairs(R.build_scenarios(pristine, "original"))

    deciders = {n: R.baseline_decider(n, embedder) for n in POLICIES if n not in R.VARIANTS}
    deciders.update({n: R.variant_decider(n) for n in ("cdc", "cdc_counterfactual", "no_stub_gate")})
    deciders.update({n: R.body_aware_decider(n, embedder)
                     for n in ("stub_check", "lexical_plus_stub", "op_check")})
    tunable = [n for n in POLICIES if n in SCORE_POLICIES + COUNT_POLICIES]

    lopo_assoc, chosen = R.lopo(pairs, deciders, tunable, embedder, "association")
    lopo_behav, _ = R.lopo(pairs, deciders, tunable, embedder, "behavioural")
    transfer = R.confusion  # alias for readability
    transferred = {
        name: transfer([(R.is_gap(p, "association"), dec(p, "mut", authored_th)) for p in pairs])
        for name, dec in deciders.items()
    }
    out = {
        "n_pairs": len(pairs),
        "n_mutated": sum(1 for p in pairs if p["operator"] is not None),
        "x1_pristine": pristine_stats(pristine, R.DEFAULT["min_strength"]),
        "x2_separation": R.sep_block(pairs, deciders, authored_th, OPERATORS, with_ci=True),
        "x3_lopo_association": lopo_assoc,
        "x3_lopo_behavioural": lopo_behav,
        "x3_lopo_thresholds": chosen,
        "x4_transferred_thresholds": transferred,
    }
    if mode == "default":
        out["x5_project_level"] = R.project_level(pristine, authored_th, embedder)
    return out


def run():
    with open(os.path.join(ROOT, "results", "revision.json"), encoding="utf-8") as fh:
        authored_th = json.load(fh)["thresholds_pooled"]
    _, man = load_ext("default")
    results = {"corpus": man, "authored_thresholds": authored_th}
    for mode in ("default", "thr0", "public"):
        results[mode] = run_mode(mode, authored_th)
    set_mode("default")
    with open(os.path.join(ROOT, "results", "external.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, sort_keys=True, indent=2)
        fh.write("\n")
    with open(os.path.join(ROOT, "results", "manifest.sha256.json"), "w", encoding="utf-8") as fh:
        json.dump(R.manifest(), fh, sort_keys=True, indent=2)
        fh.write("\n")
    return results


if __name__ == "__main__":
    run()

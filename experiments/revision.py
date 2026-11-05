"""
R1-R9: experiments added in response to the Team03_R01 review. Deterministic; no network.

The E0-E6 harness in run_all.py is left untouched. This script reuses its corpus
loading, best-match and mutated-uid rules, and writes results/revision.json.

  R1  ablation of the stub gate, channels, provenance tags and decision rule
  R2  body-aware baselines (stub check, lexical + stub check, operation check)
  R3  leave-one-project-out evaluation with full confusion matrices
  R4  semantic mutations that keep the body non-empty
  R5  sensitivity to k_min, the emission threshold and tag granularity
  R6  whole-project claim support with an explicit aggregation rule
  R7  claim-aware operation check (negative evidence) for WEAKEN
  R8  cap hits, warning burden on pristine projects, RENAME label semantics
  R9  manifest of hashes for code, corpus and results
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from cdc import evidence as ev_mod
from cdc.codebase import extract_codebase
from cdc.corroborate import corroboration, counterfactual_worst
from cdc.evidence import CLAIM_OPS
from cdc.mutate import OPERATORS, _apply_operator, _join, _matching_functions
from cdc.policies import POLICIES
from cdc.scoring import score_document
from experiments.run_all import (
    COUNT_POLICIES, K_SWEEP, RATE, SCORE_POLICIES, SEED, THRESHOLDS,
    build_embedder, load_manifest, load_project, mutated_uid, r6,
)

ROUNDS = 3
BOOT = 2000
CAP = 24
SEMANTIC = ("NEGATE_COND", "DROP_GUARD", "CONST_RETURN")
CHANNELS = ("NAME", "DOC", "IMPORT", "SCHEMA", "BODY", "CALL", "TEST")
TAG_CLASSES = ("tok:", "file:", "sym:", "lib:", "op:")
# A claim that names a strong primitive is contradicted by its weak counterpart.
WEAK_OF = {"op:hash": "op:hash_weak"}

DEFAULT = {
    "stub_gate": True, "require_other": True, "channels": CHANNELS,
    "drop_tags": (), "min_strength": 0.15, "rule": "C", "k": 2, "claim_ops": False,
}

# R1/R5 variants: one change from DEFAULT each.
VARIANTS = {
    "cdc": {},
    "cdc_counterfactual": {"rule": "Cmin"},
    "no_stub_gate": {"stub_gate": False},
    "no_gate_at_all": {"stub_gate": False, "require_other": False},
    "no_disjointness": {"rule": "count"},
    "no_name_doc": {"channels": ("IMPORT", "SCHEMA", "BODY", "CALL", "TEST")},
    "no_body": {"channels": ("NAME", "DOC", "IMPORT", "SCHEMA", "CALL", "TEST")},
    "no_call_test": {"channels": ("NAME", "DOC", "IMPORT", "SCHEMA", "BODY")},
    "tags_no_file": {"drop_tags": ("file:",)},
    "tags_no_tok": {"drop_tags": ("tok:",)},
    "tags_channel_only": {"drop_tags": TAG_CLASSES},
    "claim_ops": {"claim_ops": True},
}


def cfg_of(name):
    cfg = dict(DEFAULT)
    cfg.update(VARIANTS.get(name, {}))
    return cfg


# ----------------------------------------------------------------- evidence
def gather_v(claim, elements, cfg):
    """cdc.evidence.gather with every rule exposed as a switch."""
    out = []
    keep = set(cfg["channels"])
    for el in elements:
        ev = []
        for piece in (
            ev_mod._name(claim, el), ev_mod._doc(claim, el),
            ev_mod._import(claim, el), ev_mod._schema(claim, el),
            ev_mod._body(claim, el),
        ):
            if piece is not None and piece.strength >= cfg["min_strength"]:
                ev.append(piece)
        gated = (bool(ev) or not cfg["require_other"]) and (
            not el.is_stub or not cfg["stub_gate"]
        )
        if gated:
            for piece in (
                ev_mod._call(claim, el, elements), ev_mod._test(claim, el, elements),
            ):
                if piece is not None and piece.strength >= cfg["min_strength"]:
                    ev.append(piece)
        for e in ev:
            if e.channel not in keep:
                continue
            if cfg["drop_tags"]:
                prov = frozenset(
                    t for t in e.provenance if not t.startswith(cfg["drop_tags"])
                )
                e = ev_mod.Evidence(e.claim, e.element, e.channel, prov, e.strength)
            out.append(e)
    return out


def claim_ops_ok(claim, el):
    """Negative evidence: the claim names an operation the body does not perform."""
    implied = {CLAIM_OPS[t] for t in claim.terms if t in CLAIM_OPS}
    if not implied or el is None:
        return True
    if any(WEAK_OF.get(op) in el.body_ops and op not in el.body_ops for op in implied):
        return False
    return bool(implied & el.body_ops)


def decide(cfg, claim, el, evidence):
    if el is None:
        return False
    rule, k = cfg["rule"], cfg["k"]
    if rule == "C":
        ok = corroboration(evidence) >= k
    elif rule == "Cmin":
        ok = counterfactual_worst(evidence)[0] >= k
    elif rule == "count":
        ok = len(evidence) >= k
    else:
        raise ValueError(rule)
    if ok and cfg["claim_ops"]:
        ok = claim_ops_ok(claim, el)
    return ok


# --------------------------------------------------------- semantic faults
def _negate_cond(func):
    for node in ast.walk(func):
        if isinstance(node, ast.If):
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            return True
    return False


def _drop_guard(func):
    """Remove every `if ...: raise` guard (omitted validation)."""
    changed = False
    for node in ast.walk(func):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        kept = [
            s for s in body
            if not (isinstance(s, ast.If) and any(isinstance(n, ast.Raise) for n in ast.walk(s)))
        ]
        if len(kept) != len(body):
            node.body = kept or [ast.Pass()]
            changed = True
    return changed


def _const_return(func):
    """Keep the computation but return None from every `return <value>`."""
    changed = False
    for node in ast.walk(func):
        if isinstance(node, ast.Return) and node.value is not None and not (
            isinstance(node.value, ast.Constant) and node.value.value is None
        ):
            node.value = ast.Constant(value=None)
            changed = True
    return changed


_SEM = {"NEGATE_COND": _negate_cond, "DROP_GUARD": _drop_guard, "CONST_RETURN": _const_return}


def semantic_applicable(func, op):
    probe = ast.parse(ast.unparse(func)).body[0]
    return _SEM[op](probe)


def apply_ops(src_root, dst_root, plan):
    """Copy the tree and apply [(element, operator)] in one pass per file."""
    shutil.copytree(src_root, dst_root, dirs_exist_ok=True)
    trees = {}
    for el, op in plan:
        path = _join(dst_root, el.path)
        if path not in trees:
            with open(path, encoding="utf-8") as fh:
                trees[path] = ast.parse(fh.read())
        if op in _SEM:
            for func in _matching_functions(trees[path], el.name, el.lineno):
                _SEM[op](func)
        else:
            _apply_operator(trees[path], el.name, op, el.lineno)
    for path, tree in trees.items():
        ast.fix_missing_locations(tree)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(ast.unparse(tree))


def semantic_plan(code_dir, elements, rng):
    """Same 30% sampling as apply_mutations, restricted to applicable operators."""
    eligible = [e for e in elements if e.kind in {"function", "method"} and not e.is_stub]
    pool = list(eligible)
    rng.shuffle(pool)
    plan = []
    trees = {}
    for el in pool[: math.floor(RATE * len(pool))]:
        path = _join(code_dir, el.path)
        if path not in trees:
            with open(path, encoding="utf-8") as fh:
                trees[path] = ast.parse(fh.read())
        funcs = _matching_functions(trees[path], el.name, el.lineno)
        ops = [op for op in SEMANTIC if funcs and semantic_applicable(funcs[0], op)]
        if ops:
            plan.append((el, rng.choice(ops)))
    return plan


# ---------------------------------------------------------------- scenarios
def build_scenarios(pristine, family):
    """One scenario per (project, round): pristine and mutated element lists."""
    out = []
    for pi, (name, (code_dir, claims, elements)) in enumerate(pristine):
        ordered = sorted(elements, key=lambda e: e.uid)
        for ri in range(ROUNDS):
            if family == "original":
                # The same seeds as run_all.run, so the pairs match the paper's E1/E2.
                from cdc.mutate import apply_mutations
                rng = random.Random(SEED + 17 * (pi + 1) + 1009 * (ri + 1))
                with tempfile.TemporaryDirectory() as tmp:
                    dst = os.path.join(tmp, "code")
                    recs = apply_mutations(code_dir, dst, claims, ordered, rng, rate=RATE)
                    mut = extract_codebase(dst)
                targeted = {m.target_uid: m.operator for m in recs}
            else:
                rng = random.Random(SEED + 70001 + 17 * (pi + 1) + 1009 * (ri + 1))
                plan = semantic_plan(code_dir, ordered, rng)
                with tempfile.TemporaryDirectory() as tmp:
                    dst = os.path.join(tmp, "code")
                    apply_ops(code_dir, dst, plan)
                    mut = extract_codebase(dst)
                targeted = {el.uid: op for el, op in plan}
            out.append({
                "project": name, "round": ri, "claims": claims,
                "pre": ordered, "mut": sorted(mut, key=lambda e: e.uid),
                "targeted": targeted,
            })
    return out


_EV_CACHE = {}


def pair_evidence(sc, side, claim, cfg):
    key = (id(sc), side, claim.cid, cfg["stub_gate"], cfg["require_other"],
           cfg["channels"], cfg["drop_tags"], cfg["min_strength"])
    if key not in _EV_CACHE:
        by = {}
        for e in gather_v(claim, sc[side], cfg):
            by.setdefault(e.element, []).append(e)
        _EV_CACHE[key] = by
    return _EV_CACHE[key]


def build_pairs(scenarios):
    """Pairs fixed by the default configuration, as in run_all.build_items."""
    pairs = []
    for sc in scenarios:
        pre_el = {e.uid: e for e in sc["pre"]}
        mut_el = {e.uid: e for e in sc["mut"]}
        for claim in sc["claims"]:
            pre = pair_evidence(sc, "pre", claim, DEFAULT)
            for uid in sorted(pre):
                el = pre_el[uid]
                op = sc["targeted"].get(uid)
                muid = mutated_uid(el, op) if op in OPERATORS else uid
                pairs.append({
                    "sc": sc, "project": sc["project"], "round": sc["round"],
                    "cid": claim.cid, "claim": claim, "uid": uid, "muid": muid,
                    "operator": op, "pre_el": el,
                    "mut_el": mut_el.get(muid) if muid is not None else None,
                })
    return pairs


# ------------------------------------------------------------------ deciders
def variant_decider(name):
    cfg = cfg_of(name)

    def run(p, side, _th):
        el = p["pre_el"] if side == "pre" else p["mut_el"]
        if el is None:
            return False
        uid = p["uid"] if side == "pre" else p["muid"]
        ev = pair_evidence(p["sc"], side, p["claim"], cfg).get(uid, [])
        return decide(cfg, p["claim"], el, ev)
    return run


def baseline_decider(name, embedder):
    def run(p, side, th):
        el = p["pre_el"] if side == "pre" else p["mut_el"]
        if el is None:
            return False
        uid = p["uid"] if side == "pre" else p["muid"]
        ev = pair_evidence(p["sc"], side, p["claim"], DEFAULT).get(uid, [])
        kw = {"embedder": embedder, "threshold": 0.5, "k_min": 2}
        if name in SCORE_POLICIES:
            kw["threshold"] = float(th[name])
        elif name in COUNT_POLICIES:
            kw["k_min"] = int(th[name])
        return POLICIES[name](p["claim"], [el], ev, **kw)
    return run


def body_aware_decider(name, embedder):
    lex = baseline_decider("lexical", embedder)

    def run(p, side, th):
        el = p["pre_el"] if side == "pre" else p["mut_el"]
        if el is None or el.is_stub:
            return False
        if name == "stub_check":
            return True
        if name == "lexical_plus_stub":
            return lex(p, side, th)
        if name == "op_check":
            return claim_ops_ok(p["claim"], el)
        raise ValueError(name)
    return run


# ------------------------------------------------------------------- metrics
def confusion(rows):
    """rows: (is_gap, accepted). Positive class = gap (rejected)."""
    tp = sum(1 for g, a in rows if g and not a)
    fn = sum(1 for g, a in rows if g and a)
    fp = sum(1 for g, a in rows if not g and not a)
    tn = sum(1 for g, a in rows if not g and a)
    div = lambda a, b: a / b if b else 0.0
    prec, rec, spec = div(tp, tp + fp), div(tp, tp + fn), div(tn, tn + fp)
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": r6(prec), "recall": r6(rec), "specificity": r6(spec),
        "balanced_accuracy": r6((rec + spec) / 2),
        "f1": r6(div(2 * prec * rec, prec + rec)),
        "false_supported_rate": r6(div(fn, tp + fn)),
        "false_rejected_rate": r6(div(fp, fp + tn)),
    }


def is_gap(p, labelling):
    op = p["operator"]
    if op is None:
        return False
    if labelling == "behavioural" and op == "RENAME":
        return False
    return True


def tune(decider, name, train, embedder):
    """E0 rule on the training projects only: best F1 on the gap class."""
    grid = THRESHOLDS if name in SCORE_POLICIES else K_SWEEP
    best = None
    for v in grid:
        th = {name: v}
        m = confusion([(is_gap(p, "association"), decider(p, "mut", th)) for p in train])
        if best is None or m["f1"] > best[1]:
            best = (v, m["f1"])
    return best[0]


def separation(pairs, decider, th):
    n = len(pairs)
    a_p = sum(1 for p in pairs if decider(p, "pre", th))
    a_m = sum(1 for p in pairs if decider(p, "mut", th))
    return a_p, a_m, n


def cluster_ci(pairs, decider, th, seed):
    """95% bootstrap interval for separation, resampling (project, claim) clusters."""
    clusters = {}
    for p in pairs:
        clusters.setdefault((p["project"], p["cid"]), []).append(
            (1 if decider(p, "pre", th) else 0, 1 if decider(p, "mut", th) else 0)
        )
    keys = sorted(clusters)
    if not keys:
        return [0.0, 0.0]
    rng = random.Random(seed)
    stats = []
    for _ in range(BOOT):
        s_p = s_m = n = 0
        for _k in keys:
            for a, b in clusters[keys[rng.randrange(len(keys))]]:
                s_p += a
                s_m += b
                n += 1
        stats.append(100.0 * (s_p - s_m) / n if n else 0.0)
    stats.sort()
    return [r6(stats[int(0.025 * BOOT)]), r6(stats[int(0.975 * BOOT) - 1])]


def sep_block(pairs, deciders, th, ops, with_ci=False):
    out = {}
    for op in ops:
        sel = [p for p in pairs if p["operator"] == op]
        out[op] = {}
        for name, dec in deciders.items():
            a_p, a_m, n = separation(sel, dec, th)
            row = {
                "n": n, "accepts_pristine": r6(100.0 * a_p / n if n else 0),
                "accepts_mutated": r6(100.0 * a_m / n if n else 0),
                "separation": r6(100.0 * (a_p - a_m) / n if n else 0),
            }
            if with_ci:
                row["cluster_ci95"] = cluster_ci(sel, dec, th, SEED + len(name) + len(op))
            row["n_clusters"] = len({(p["project"], p["cid"]) for p in sel})
            out[op][name] = row
    return out


# ------------------------------------------------------------------ R3 LOPO
def lopo(pairs, deciders, tunable, embedder, labelling):
    projects = sorted({p["project"] for p in pairs})
    rows = {name: [] for name in deciders}
    chosen = {name: {} for name in tunable}
    for held in projects:
        train = [p for p in pairs if p["project"] != held]
        test = [p for p in pairs if p["project"] == held]
        th = {}
        for name in tunable:
            th[name] = tune(deciders[name], name, train, embedder)
            chosen[name][held] = th[name]
        th["lexical"] = th.get("lexical", 0.1)
        for name, dec in deciders.items():
            for p in test:
                rows[name].append((is_gap(p, labelling), dec(p, "mut", th)))
    out = {name: confusion(r) for name, r in rows.items()}
    return out, chosen


# --------------------------------------------------------- R6 whole project
def project_level(pristine, th, embedder):
    """
    Claim support over the whole program. A claim is supported when at least one
    element x has C(c, x) >= 2 ("any-element"); the alternative pools every item
    for the claim into one conflict graph ("pooled", C(c, P) >= 2).

    Three conditions per claim, with labels fixed by construction:
      pristine    nothing mutated                         -> implemented
      one_gutted  NOMINAL on one of >= 2 supporting elements -> implemented
      all_gutted  NOMINAL on every supporting element      -> not implemented
    """
    out = {"rule": "any-element: exists x with C(c,x) >= 2; pooled: C(c,P) >= 2",
           "conditions": {}}
    cond_rows = {c: {"cdc_any": [], "cdc_pooled": [], "lexical_any": []}
                 for c in ("pristine", "one_gutted", "all_gutted")}
    n_multi = 0
    for pi, (name, (code_dir, claims, elements)) in enumerate(pristine):
        ordered = sorted(elements, key=lambda e: e.uid)
        rng = random.Random(SEED + 50001 + pi)
        for claim in claims:
            ev = ev_mod.gather(claim, ordered)
            by = {}
            for e in ev:
                by.setdefault(e.element, []).append(e)
            el_of = {e.uid: e for e in ordered}
            support = sorted(
                u for u, items in by.items()
                if corroboration(items) >= 2
                and el_of[u].kind in {"function", "method"} and not el_of[u].is_stub
            )
            if not support:
                continue
            conds = {"pristine": [], "all_gutted": support}
            if len(support) >= 2:
                conds["one_gutted"] = [rng.choice(support)]
                n_multi += 1
            for cond, victims in conds.items():
                with tempfile.TemporaryDirectory() as tmp:
                    dst = os.path.join(tmp, "code")
                    apply_ops(code_dir, dst, [(el_of[u], "NOMINAL") for u in victims])
                    mut = sorted(extract_codebase(dst), key=lambda e: e.uid)
                mev = ev_mod.gather(claim, mut)
                mby = {}
                for e in mev:
                    mby.setdefault(e.element, []).append(e)
                any_ok = any(corroboration(v) >= 2 for v in mby.values())
                pooled_ok = corroboration(mev) >= 2
                lex_ok = POLICIES["lexical"](
                    claim, mut, [], embedder=embedder, threshold=float(th["lexical"]),
                )
                cond_rows[cond]["cdc_any"].append(any_ok)
                cond_rows[cond]["cdc_pooled"].append(pooled_ok)
                cond_rows[cond]["lexical_any"].append(lex_ok)
    for cond, rows in cond_rows.items():
        out["conditions"][cond] = {
            k: {"n": len(v), "accepts": sum(v),
                "accepts_pct": r6(100.0 * sum(v) / len(v) if v else 0)}
            for k, v in rows.items()
        }
    out["claims_with_two_or_more_supporting_elements"] = n_multi
    return out


# -------------------------------------------------------------- R8 sundries
def cap_hits(pristine):
    pair_hits = claim_hits = n_pairs = n_claims = 0
    largest = 0
    for _name, (_dir, claims, elements) in pristine:
        for claim in claims:
            ev = ev_mod.gather(claim, elements)
            n_claims += 1
            largest = max(largest, len(ev))
            claim_hits += len(ev) > CAP
            by = {}
            for e in ev:
                by.setdefault(e.element, []).append(e)
            for items in by.values():
                n_pairs += 1
                pair_hits += len(items) > CAP
    return {"pairs": n_pairs, "pair_cap_hits": pair_hits, "claims": n_claims,
            "pooled_claim_cap_hits": claim_hits, "largest_pooled_evidence": largest}


def warning_burden(pristine):
    out = {}
    for name, (_dir, claims, elements) in pristine:
        rep = score_document(claims, elements)
        verdicts = [r.verdict for r in rep.results]
        out[name] = {
            "claims": len(verdicts),
            "supported": verdicts.count("SUPPORTED"),
            "weak": verdicts.count("WEAK"),
            "unsupported": verdicts.count("UNSUPPORTED"),
        }
    return out


def weaken_effective(pairs, pristine):
    """How many WEAKEN targets in the pooled rounds actually changed any code."""
    from cdc.mutate import mutate_source
    dirs = {n: d for n, (d, _c, _e) in pristine}
    seen = {}
    for p in pairs:
        if p["operator"] != "WEAKEN":
            continue
        el = p["pre_el"]
        with open(_join(dirs[p["project"]], el.path), encoding="utf-8") as fh:
            src = fh.read()
        changed = ast.unparse(ast.parse(src)) != mutate_source(src, el.name, "WEAKEN", el.lineno)
        seen[(p["project"], p["round"], el.uid)] = changed
    n_pairs = sum(1 for p in pairs if p["operator"] == "WEAKEN")
    eff = sum(1 for p in pairs if p["operator"] == "WEAKEN"
              and seen[(p["project"], p["round"], p["pre_el"].uid)])
    return {"targets": len(seen), "targets_changed": sum(seen.values()),
            "pairs": n_pairs, "pairs_on_changed_targets": eff}


def targeted_weaken(pristine):
    """
    R7: WEAKEN applied one function at a time, only where it changes the code.
    Each such function becomes one scenario with a single mutated element.
    """
    from cdc.mutate import mutate_source
    scenarios = []
    for name, (code_dir, claims, elements) in pristine:
        ordered = sorted(elements, key=lambda e: e.uid)
        for el in ordered:
            if el.kind not in {"function", "method"} or el.is_stub:
                continue
            with open(_join(code_dir, el.path), encoding="utf-8") as fh:
                src = fh.read()
            if ast.unparse(ast.parse(src)) == mutate_source(src, el.name, "WEAKEN", el.lineno):
                continue
            with tempfile.TemporaryDirectory() as tmp:
                dst = os.path.join(tmp, "code")
                apply_ops(code_dir, dst, [(el, "WEAKEN")])
                mut = sorted(extract_codebase(dst), key=lambda e: e.uid)
            scenarios.append({"project": name, "round": 0, "claims": claims,
                              "pre": ordered, "mut": mut, "targeted": {el.uid: "WEAKEN"},
                              "target": el.uid})
    pairs = [p for p in build_pairs(scenarios)
             if p["uid"] == p["sc"]["target"]]
    return pairs, [sc["target"] for sc in scenarios]


def body_on_weaken(pairs):
    """How often BODY fires before and after WEAKEN, to explain the WEAKEN result."""
    sel = [p for p in pairs if p["operator"] == "WEAKEN"]
    before = after = 0
    for p in sel:
        pre = pair_evidence(p["sc"], "pre", p["claim"], DEFAULT).get(p["uid"], [])
        post = pair_evidence(p["sc"], "mut", p["claim"], DEFAULT).get(p["muid"], [])
        before += any(e.channel == "BODY" for e in pre)
        after += any(e.channel == "BODY" for e in post)
    return {"n": len(sel), "body_fires_pristine": before, "body_fires_mutated": after}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def manifest():
    out = {}
    for sub in ("cdc", "experiments", "corpus", "corpus_ext", "annotation", "results"):
        for dirpath, dirnames, files in os.walk(os.path.join(ROOT, sub)):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for fn in sorted(files):
                if fn.endswith((".py", ".md", ".tex", ".json", ".csv")) and fn != "manifest.sha256.json":
                    p = os.path.join(dirpath, fn)
                    out[os.path.relpath(p, ROOT).replace(os.sep, "/")] = sha(p)
    return out


# ----------------------------------------------------------------------- run
def run():
    pristine = [(e["name"], load_project(e)) for e in load_manifest()["projects"]]
    embedder = build_embedder(pristine)
    orig = build_pairs(build_scenarios(pristine, "original"))
    sem = build_pairs(build_scenarios(pristine, "semantic"))

    deciders = {n: baseline_decider(n, embedder) for n in POLICIES if n not in VARIANTS}
    deciders.update({n: variant_decider(n) for n in VARIANTS})
    deciders.update({n: body_aware_decider(n, embedder)
                     for n in ("stub_check", "lexical_plus_stub", "op_check")})
    tunable = [n for n in POLICIES if n in SCORE_POLICIES + COUNT_POLICIES]

    lopo_assoc, chosen = lopo(orig, deciders, tunable, embedder, "association")
    lopo_behav, _ = lopo(orig, deciders, tunable, embedder, "behavioural")
    # Separation tables use thresholds tuned on all projects pooled (as E0);
    # text policies cannot separate NOMINAL at any threshold, so the choice
    # only matters for the other operators.
    th = {n: tune(deciders[n], n, orig, embedder) for n in tunable}

    sens = {"k_min": {}, "min_strength": {}}
    nominal = [p for p in orig if p["operator"] == "NOMINAL"]
    for rule, label in (("C", "cdc"), ("Cmin", "cdc_counterfactual")):
        for k in (1, 2, 3, 4):
            VARIANTS[f"_{label}_k{k}"] = {"rule": rule, "k": k}
            dec = variant_decider(f"_{label}_k{k}")
            a_p, a_m, n = separation(nominal, dec, th)
            sens["k_min"][f"{label}_k{k}"] = {
                "nominal_separation": r6(100.0 * (a_p - a_m) / n),
                "nominal_accepts_pristine": r6(100.0 * a_p / n),
                **{k2: v for k2, v in confusion(
                    [(is_gap(p, "association"), dec(p, "mut", th)) for p in orig]
                ).items() if k2 in ("false_supported_rate", "false_rejected_rate")},
            }
    for s in (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50):
        VARIANTS[f"_ms{s}"] = {"min_strength": s}
        dec = variant_decider(f"_ms{s}")
        a_p, a_m, n = separation(nominal, dec, th)
        sens["min_strength"][str(s)] = {
            "nominal_separation": r6(100.0 * (a_p - a_m) / n),
            "nominal_accepts_pristine": r6(100.0 * a_p / n),
            **{k2: v for k2, v in confusion(
                [(is_gap(p, "association"), dec(p, "mut", th)) for p in orig]
            ).items() if k2 in ("false_supported_rate", "false_rejected_rate")},
        }

    weak_pairs, weak_targets = targeted_weaken(pristine)
    main_names = list(deciders)
    results = {
        "seed": SEED, "rounds": ROUNDS, "bootstrap_reps": BOOT,
        "n_pairs_original": len(orig), "n_pairs_semantic": len(sem),
        "thresholds_pooled": th,
        "lopo_thresholds": chosen,
        "r1_r2_separation_original": sep_block(
            orig, deciders, th, OPERATORS, with_ci=True),
        "r3_lopo_association_labels": lopo_assoc,
        "r3_lopo_behavioural_labels": lopo_behav,
        "r4_separation_semantic": sep_block(sem, deciders, th, SEMANTIC, with_ci=True),
        "r4_operator_counts": {op: sum(1 for p in sem if p["operator"] == op) for op in SEMANTIC},
        "r5_sensitivity": sens,
        "r6_project_level": project_level(pristine, th, embedder),
        "r8_cap_hits": cap_hits(pristine),
        "r8_warning_burden_pristine": warning_burden(pristine),
        "r8_body_on_weaken": body_on_weaken(orig),
        "r8_weaken_effective": weaken_effective(orig, pristine),
        "r7_targeted_weaken": {
            "targets": weak_targets,
            "separation": sep_block(weak_pairs, deciders, th, ("WEAKEN",)),
            # Only claims about the weakened primitive are falsified by WEAKEN.
            "separation_crypto_claims": sep_block(
                [p for p in weak_pairs
                 if {CLAIM_OPS[t] for t in p["claim"].terms if t in CLAIM_OPS}
                 & {"op:hash", "op:aead", "op:mac", "op:random", "op:kdf"}],
                deciders, th, ("WEAKEN",)),
        },
        "policies": main_names,
    }
    out_dir = os.path.join(ROOT, "results")
    with open(os.path.join(out_dir, "revision.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, sort_keys=True, indent=2)
        fh.write("\n")
    with open(os.path.join(out_dir, "manifest.sha256.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest(), fh, sort_keys=True, indent=2)
        fh.write("\n")
    return results


if __name__ == "__main__":
    run()

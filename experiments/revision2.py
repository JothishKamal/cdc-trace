"""
R10-R15: second round of experiments for the Team03_R01 review. Deterministic; no network.

revision.py is left untouched, so every number it writes stays byte-identical.
This script reuses its corpus, pairs and deciders, and writes results/revision2.json.

  R10  NAME and DOC removed separately (not only together)
  R11  hiding file paths and docstrings on the NOMINAL pairs
  R12  a strength-weighted corroboration count against the binary count
  R13  warning burden per project (pair level and claim level, pristine code)
  R14  three more behavioural faults: WRONG_PARAM, DROP_BRANCH, BAD_EXCEPT
  R15  a wider stub detector, tested on its own and inside cdc
  R16  why the E3 0% point is 95.5 pp and not 100.0 pp
"""
from __future__ import annotations

import ast
import dataclasses
import itertools
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
from cdc.codebase import _is_stub, extract_codebase
from cdc.corroborate import corroboration
from cdc.mutate import _join, _matching_functions
from experiments import revision as R
from experiments.run_all import (
    RATE, SEED, build_embedder, load_manifest, load_project, r6,
)

NEW_OPS = ("WRONG_PARAM", "DROP_BRANCH", "BAD_EXCEPT")
STUB_FORMS_ORIG = ("pass", "ellipsis", "return_none", "raise_nie")
STUB_FORMS_NEW = ("return_const", "return_empty", "return_param", "delegate")
HELPER = "_pending"


# ------------------------------------------------------------ R14 operators
def _int_args(func):
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            for a in list(node.args) + [k.value for k in node.keywords]:
                if (isinstance(a, ast.Constant) and type(a.value) is int
                        and a.value not in (0, 1)):
                    yield a


def _wrong_param(func):
    """Every integer literal argument of a call (key size, nonce length,
    iteration count, retry limit) is replaced by 1."""
    changed = False
    for a in _int_args(func):
        a.value = 1
        changed = True
    return changed


def _raises(node):
    return any(isinstance(n, ast.Raise) for n in ast.walk(node))


def _drop_branch(func):
    """Remove the first `if` that is not a raise-guard: one case is not handled."""
    for node in ast.walk(func):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for i, s in enumerate(body):
            if isinstance(s, ast.If) and not _raises(s):
                rest = body[:i] + body[i + 1:]
                node.body = rest or [ast.Pass()]
                return True
    return False


def _bad_except(func):
    """Every `except` handler swallows the error."""
    changed = False
    for node in ast.walk(func):
        if isinstance(node, ast.ExceptHandler):
            node.body = [ast.Pass()]
            changed = True
    return changed


R._SEM.update({"WRONG_PARAM": _wrong_param, "DROP_BRANCH": _drop_branch,
               "BAD_EXCEPT": _bad_except})


# ---------------------------------------------------------- R15 stub forms
def _doc_prefix(func):
    b = func.body
    if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) \
            and isinstance(b[0].value.value, str):
        return [b[0]]
    return []


def _params(func):
    names = [a.arg for a in func.args.posonlyargs + func.args.args]
    return [n for n in names if n not in ("self", "cls")]


def _has_value_return(func):
    return any(isinstance(n, ast.Return) and n.value is not None
               and not (isinstance(n.value, ast.Constant) and n.value.value is None)
               for n in ast.walk(func))


def make_stub(func, form):
    """Replace the body by one stub form, keeping name and docstring."""
    keep = _doc_prefix(func)
    if form == "pass":
        stmt = ast.Pass()
    elif form == "ellipsis":
        stmt = ast.Expr(ast.Constant(Ellipsis))
    elif form == "return_none":
        stmt = ast.Return(ast.Constant(None))
    elif form == "raise_nie":
        stmt = ast.Raise(ast.Name("NotImplementedError", ast.Load()), None)
    elif form == "return_const":
        stmt = ast.Return(ast.Constant(0))
    elif form == "return_empty":
        stmt = ast.Return(ast.Dict([], []))
    elif form == "return_param":
        stmt = ast.Return(ast.Name(_params(func)[0], ast.Load()))
    elif form == "delegate":
        stmt = ast.Return(ast.Call(ast.Name(HELPER, ast.Load()), [], []))
    else:
        raise ValueError(form)
    func.body = keep + [stmt]


def stub_applicable(func, form):
    if form in ("return_const", "return_empty"):
        return _has_value_return(func)
    if form == "return_param":
        return _has_value_return(func) and bool(_params(func))
    return True


def _is_stub_ext(func, stub_names):
    """
    Wider incompleteness detector. Besides the four original forms it flags a body
    that is one statement returning a constant, an empty literal or an unchanged
    parameter, or that only calls or returns a call to a function that is a stub.
    """
    if _is_stub(func):
        return True
    body = list(func.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if len(body) != 1:
        return False
    s = body[0]
    val = s.value if isinstance(s, (ast.Return, ast.Expr)) else None
    if val is None:
        return False
    if isinstance(s, ast.Return):
        if isinstance(val, ast.Constant):
            return True
        if isinstance(val, (ast.List, ast.Tuple, ast.Set)) and not val.elts:
            return True
        if isinstance(val, ast.Dict) and not val.keys:
            return True
        if isinstance(val, ast.Name) and val.id in _params(func):
            return True
    if isinstance(val, ast.Call):
        f = val.func
        callee = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
        if callee in stub_names:
            return True
    return False


def ext_stub_uids(code_dir, elements):
    """uids of function elements the wider detector flags."""
    trees = {}
    funcs = {}
    for el in elements:
        if el.kind not in {"function", "method", "test"}:
            continue
        path = _join(code_dir, el.path)
        if path not in trees:
            with open(path, encoding="utf-8") as fh:
                trees[path] = ast.parse(fh.read())
        m = _matching_functions(trees[path], el.name, el.lineno)
        if m:
            funcs[el.uid] = m[0]
    stub_names = {el.name for el in elements if el.is_stub}
    return {u for u, f in funcs.items() if _is_stub_ext(f, stub_names)}


def apply_stub_forms(src_root, dst_root, plan):
    """plan: [(element, form)]; adds the stub helper to a file that delegates."""
    shutil.copytree(src_root, dst_root, dirs_exist_ok=True)
    trees, need_helper = {}, set()
    for el, form in plan:
        path = _join(dst_root, el.path)
        if path not in trees:
            with open(path, encoding="utf-8") as fh:
                trees[path] = ast.parse(fh.read())
        for func in _matching_functions(trees[path], el.name, el.lineno):
            make_stub(func, form)
        if form == "delegate":
            need_helper.add(path)
    for path in need_helper:
        helper = ast.parse(f"def {HELPER}():\n    raise NotImplementedError\n").body[0]
        trees[path].body.append(helper)
    for path, tree in trees.items():
        ast.fix_missing_locations(tree)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(ast.unparse(tree))


# ----------------------------------------------------------- shared helpers
_KEEP = []  # R.pair_evidence caches by id(scenario); keep every copy alive


def remap(sc, f):
    """A copy of scenario sc whose pre and mut element lists are passed through f."""
    new = dict(sc)
    _KEEP.append(new)
    new["pre"] = [f(e, "pre") for e in sc["pre"]]
    new["mut"] = [f(e, "mut") for e in sc["mut"]]
    return new


def remap_pairs(pairs, f):
    """Same pairs (fixed on unmodified code), evaluated on transformed elements."""
    cache = {}
    out = []
    for p in pairs:
        key = id(p["sc"])
        if key not in cache:
            cache[key] = remap(p["sc"], f)
        nsc = cache[key]
        pre = {e.uid: e for e in nsc["pre"]}
        mut = {e.uid: e for e in nsc["mut"]}
        q = dict(p)
        q["sc"] = nsc
        q["pre_el"] = pre.get(p["uid"])
        q["mut_el"] = mut.get(p["muid"]) if p["muid"] is not None else None
        out.append(q)
    return out


def sep_row(pairs, dec, th=None):
    th = th or {}
    a_p, a_m, n = R.separation(pairs, dec, th)
    return {"n": n, "accepts_pristine": r6(100.0 * a_p / n if n else 0),
            "accepts_mutated": r6(100.0 * a_m / n if n else 0),
            "separation": r6(100.0 * (a_p - a_m) / n if n else 0)}


def lopo_fixed(pairs, dec, labelling="association"):
    rows = [(R.is_gap(p, labelling), dec(p, "mut", {})) for p in pairs]
    return R.confusion(rows)


def by_op(pairs, op):
    return [p for p in pairs if p["operator"] == op]


# ------------------------------------------------------------ R12 weighting
def weighted_C(items):
    """Largest total strength of a pairwise provenance-disjoint subset."""
    best = 0.0
    n = len(items)
    for r in range(1, n + 1):
        for comb in itertools.combinations(items, r):
            ok = all(not (a.provenance & b.provenance)
                     for a, b in itertools.combinations(comb, 2))
            if ok:
                best = max(best, sum(e.strength for e in comb))
    return best


W_GRID = (0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.4)


def weighted_decider(p, side, th):
    el = p["pre_el"] if side == "pre" else p["mut_el"]
    if el is None:
        return False
    uid = p["uid"] if side == "pre" else p["muid"]
    ev = R.pair_evidence(p["sc"], side, p["claim"], R.DEFAULT).get(uid, [])
    return weighted_C(ev) >= th["weighted"]


def weighted_lopo(pairs):
    projects = sorted({p["project"] for p in pairs})
    rows, chosen = [], {}
    for held in projects:
        train = [p for p in pairs if p["project"] != held]
        best = None
        for w in W_GRID:
            m = R.confusion([(R.is_gap(p, "association"), weighted_decider(p, "mut", {"weighted": w}))
                             for p in train])
            if best is None or m["f1"] > best[1]:
                best = (w, m["f1"])
        chosen[held] = best[0]
        rows += [(R.is_gap(p, "association"), weighted_decider(p, "mut", {"weighted": best[0]}))
                 for p in pairs if p["project"] == held]
    return R.confusion(rows), chosen


# ------------------------------------------------------------ pair builders
def r14_pairs_of(pristine):
    """R14 pairs: each new fault applied to every function it changes, one at a time."""
    r14_pairs = []
    applicable = {op: 0 for op in NEW_OPS}
    for name, (code_dir, claims, elements) in pristine:
        ordered = sorted(elements, key=lambda e: e.uid)
        for el in ordered:
            if el.kind not in {"function", "method"} or el.is_stub:
                continue
            with open(_join(code_dir, el.path), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            funcs = _matching_functions(tree, el.name, el.lineno)
            if not funcs:
                continue
            for op in NEW_OPS:
                if not R.semantic_applicable(funcs[0], op):
                    continue
                applicable[op] += 1
                with tempfile.TemporaryDirectory() as tmp:
                    dst = os.path.join(tmp, "code")
                    R.apply_ops(code_dir, dst, [(el, op)])
                    mut = sorted(extract_codebase(dst), key=lambda e: e.uid)
                sc = {"project": name, "round": 0, "claims": claims, "pre": ordered,
                      "mut": mut, "targeted": {el.uid: op}, "target": el.uid}
                r14_pairs += [p for p in R.build_pairs([sc]) if p["uid"] == el.uid]
    return r14_pairs, applicable


def r15_pairs_of(pristine):
    """R15b pairs: one placeholder form per sampled function, 30% per round."""
    ext_cache = {}
    r15_pairs = []
    for pi, (name, (code_dir, claims, elements)) in enumerate(pristine):
        ordered = sorted(elements, key=lambda e: e.uid)
        for ri in range(R.ROUNDS):
            rng = random.Random(SEED + 80001 + 17 * (pi + 1) + 1009 * (ri + 1))
            pool = [e for e in ordered if e.kind in {"function", "method"} and not e.is_stub]
            rng.shuffle(pool)
            plan = []
            for el in pool[: math.floor(RATE * len(pool))]:
                with open(_join(code_dir, el.path), encoding="utf-8") as fh:
                    func = _matching_functions(ast.parse(fh.read()), el.name, el.lineno)[0]
                forms = [f for f in STUB_FORMS_NEW if stub_applicable(func, f)]
                plan.append((el, rng.choice(forms)))
            with tempfile.TemporaryDirectory() as tmp:
                dst = os.path.join(tmp, "code")
                apply_stub_forms(code_dir, dst, plan)
                mut = sorted(extract_codebase(dst), key=lambda e: e.uid)
                mut_ext = ext_stub_uids(dst, mut)
            sc = {"project": name, "round": ri, "claims": claims, "pre": ordered,
                  "mut": mut, "targeted": {el.uid: f.upper() for el, f in plan}}
            ext_cache[id(sc)] = (ext_stub_uids(code_dir, ordered), mut_ext)
            r15_pairs += R.build_pairs([sc])

    return r15_pairs, ext_cache


# ----------------------------------------------------------------------- run
def run():
    pristine = [(e["name"], load_project(e)) for e in load_manifest()["projects"]]
    embedder = build_embedder(pristine)
    orig = R.build_pairs(R.build_scenarios(pristine, "original"))
    out = {"seed": SEED}

    base = {n: R.baseline_decider(n, embedder) for n in ("lexical",)}
    th_lex = {"lexical": 0.1}
    cdc = R.variant_decider("cdc")
    cdc_cf = R.variant_decider("cdc_counterfactual")
    stub = R.body_aware_decider("stub_check", embedder)

    # R10: NAME and DOC separately.
    R.VARIANTS["no_name"] = {"channels": tuple(c for c in R.CHANNELS if c != "NAME")}
    R.VARIANTS["no_doc"] = {"channels": tuple(c for c in R.CHANNELS if c != "DOC")}
    r10 = {}
    for v in ("cdc", "no_name", "no_doc", "no_name_doc"):
        dec = R.variant_decider(v)
        r10[v] = {op: sep_row(by_op(orig, op), dec) for op in ("NOMINAL", "STUB", "RENAME")}
        r10[v]["balanced_accuracy"] = lopo_fixed(orig, dec)["balanced_accuracy"]
        r10[v]["pristine_accepts_all_pairs"] = r6(100.0 * sum(
            dec(p, "pre", {}) for p in orig) / len(orig))
    out["r10_name_doc_separately"] = r10

    # R11: hide file paths and docstrings, element-level, on the NOMINAL pairs.
    nominal = by_op(orig, "NOMINAL")
    file_ids = {}

    def opaque(path):
        if path not in file_ids:
            file_ids[path] = len(file_ids) + 1
        stem = f"m{file_ids[path]}x.py"
        return ("tests/" + stem) if "/tests/" in "/" + path or \
            os.path.basename(path).startswith("test_") else stem

    conds = {
        "full": lambda e, s: e,
        "no_paths": lambda e, s: dataclasses.replace(e, path=opaque(e.path)),
        "no_docstrings": lambda e, s: dataclasses.replace(e, doc=""),
        "no_paths_no_docstrings": lambda e, s: dataclasses.replace(e, path=opaque(e.path), doc=""),
    }
    r11 = {}
    for cname, f in conds.items():
        sel = remap_pairs(nominal, f)
        r11[cname] = {
            "cdc": sep_row(sel, cdc), "cdc_counterfactual": sep_row(sel, cdc_cf),
            "lexical": sep_row(sel, base["lexical"], th_lex),
            "stub_check": sep_row(sel, stub),
        }
    out["r11_hidden_paths_docstrings_nominal"] = r11

    # R12: weighted count.
    r12 = {"grid": list(W_GRID), "nominal": {}, "stub": {}}
    for w in W_GRID:
        th = {"weighted": w}
        r12["nominal"][str(w)] = sep_row(nominal, weighted_decider, th)
        r12["stub"][str(w)] = sep_row(by_op(orig, "STUB"), weighted_decider, th)
    lo, chosen = weighted_lopo(orig)
    r12["lopo_association"] = lo
    r12["lopo_thresholds"] = chosen
    r12["cdc_lopo_association"] = lopo_fixed(orig, cdc)
    out["r12_weighted_count"] = r12

    # R13: warning burden per project on pristine code.
    r13 = {}
    for name, (code_dir, claims, elements) in pristine:
        seen = {}
        for p in orig:
            if p["project"] == name and p["round"] == 0:
                seen[(p["cid"], p["uid"])] = p
        prs = list(seen.values())
        rej_cdc = sum(1 for p in prs if not cdc(p, "pre", {}))
        rej_stub = sum(1 for p in prs if not stub(p, "pre", {}))
        by = {}
        flagged = 0
        for claim in claims:
            ev = ev_mod.gather(claim, elements)
            by = {}
            for e in ev:
                by.setdefault(e.element, []).append(e)
            if not any(corroboration(v) >= 2 for v in by.values()):
                flagged += 1
        r13[name] = {"pairs": len(prs), "pairs_rejected_cdc": rej_cdc,
                     "pairs_rejected_stub_check": rej_stub,
                     "claims": len(claims), "claims_flagged_any_element": flagged}
    out["r13_warning_burden_per_project"] = r13

    # R14: three more behavioural faults, applied to every function where they
    # change the code (one function per scenario, so n is not limited by sampling).
    r14_pairs, applicable = r14_pairs_of(pristine)
    deciders = {"lexical": base["lexical"], "cdc": cdc, "cdc_counterfactual": cdc_cf,
                "stub_check": stub,
                "op_check": R.body_aware_decider("op_check", embedder)}
    out["r14_more_faults"] = {
        "functions_changed": applicable,
        "separation": {op: {n: sep_row(by_op(r14_pairs, op), d, th_lex)
                            for n, d in deciders.items()} for op in NEW_OPS},
    }

    # R15a: stub detection on its own. Every non-stub function is turned into each
    # stub form in turn; detection rate per form, original vs wider detector.
    det = {f: {"n": 0, "orig": 0, "ext": 0} for f in STUB_FORMS_ORIG + STUB_FORMS_NEW}
    fp = {"functions": 0, "orig": 0, "ext": 0, "ext_flagged": []}
    for name, (code_dir, claims, elements) in pristine:
        uids_ext = ext_stub_uids(code_dir, elements)
        for el in elements:
            if el.kind in {"function", "method"} and not el.is_stub:
                fp["functions"] += 1
                if el.uid in uids_ext:
                    fp["ext"] += 1
                    fp["ext_flagged"].append(f"{name}:{el.uid}")
        for el in sorted(elements, key=lambda e: e.uid):
            if el.kind not in {"function", "method"} or el.is_stub:
                continue
            with open(_join(code_dir, el.path), encoding="utf-8") as fh:
                func = _matching_functions(ast.parse(fh.read()), el.name, el.lineno)[0]
            for form in det:
                if not stub_applicable(func, form):
                    continue
                with tempfile.TemporaryDirectory() as tmp:
                    dst = os.path.join(tmp, "code")
                    apply_stub_forms(code_dir, dst, [(el, form)])
                    mut = extract_codebase(dst)
                    m = [e for e in mut if e.uid == el.uid]
                    if not m:
                        continue
                    det[form]["n"] += 1
                    det[form]["orig"] += m[0].is_stub
                    det[form]["ext"] += el.uid in ext_stub_uids(dst, mut)
    for f, d in det.items():
        d["orig_rate"] = r6(100.0 * d["orig"] / d["n"] if d["n"] else 0)
        d["ext_rate"] = r6(100.0 * d["ext"] / d["n"] if d["n"] else 0)
    out["r15a_stub_detection"] = {"by_form": det, "pristine_false_positives": fp}

    # R15b: the new stub forms as mutations, cdc with the original vs wider detector.
    r15_pairs, ext_cache = r15_pairs_of(pristine)

    def to_ext(pairs):
        groups = {}
        for p in pairs:
            groups.setdefault(id(p["sc"]), []).append(p)
        out_p = []
        for key, grp in groups.items():
            pre_x, mut_x = ext_cache[key]
            f = lambda e, s, px=pre_x, mx=mut_x: dataclasses.replace(
                e, is_stub=e.is_stub or e.uid in (px if s == "pre" else mx))
            out_p += remap_pairs(grp, f)
        return out_p

    r15_ext = to_ext(r15_pairs)
    # Cost on unmodified code: the wider detector applied to pristine elements of
    # each project (the same in every round).
    proj_ext = {n: ext_stub_uids(d, e) for n, (d, _c, e) in pristine}
    orig_ext = []
    for name in proj_ext:
        flag = proj_ext[name]
        orig_ext += remap_pairs(
            [p for p in orig if p["project"] == name],
            lambda e, s, fl=flag: e if s == "mut" else dataclasses.replace(
                e, is_stub=e.is_stub or e.uid in fl))
    r15b = {}
    for form in STUB_FORMS_NEW:
        op = form.upper()
        r15b[op] = {
            "cdc": sep_row(by_op(r15_pairs, op), cdc),
            "cdc_wider_stub": sep_row(by_op(r15_ext, op), cdc),
            "stub_check": sep_row(by_op(r15_pairs, op), stub),
            "stub_check_wider": sep_row(by_op(r15_ext, op), stub),
            "lexical": sep_row(by_op(r15_pairs, op), base["lexical"], th_lex),
        }
    r15b["pristine_accepts_all_original_pairs"] = {
        "cdc": r6(100.0 * sum(cdc(p, "pre", {}) for p in orig) / len(orig)),
        "cdc_wider_stub": r6(100.0 * sum(cdc(p, "pre", {}) for p in orig_ext) / len(orig_ext)),
    }
    out["r15b_new_stub_mutations"] = r15b

    # R16: E3 draws its own NOMINAL sample. List the 0%-level pristine pairs cdc rejects.
    from experiments.run_all import e3_ablation  # noqa: F401  (documented, not rerun)
    out["r16_note"] = ("E3 uses seeds SEED+90001+... and E3_ROUNDS*rounds rounds, so its "
                       "0% NOMINAL sample (67 pairs) differs from the 49 pairs of R1.")

    with open(os.path.join(ROOT, "results", "revision2.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, sort_keys=True, indent=2)
        fh.write("\n")
    with open(os.path.join(ROOT, "results", "manifest.sha256.json"), "w", encoding="utf-8") as fh:
        json.dump(R.manifest(), fh, sort_keys=True, indent=2)
        fh.write("\n")
    return out


if __name__ == "__main__":
    run()

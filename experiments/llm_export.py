"""
L1: export claim-element prompts for a code-reading LLM baseline.

Writes llm/prompts.jsonl (one unique prompt per claim and function source) and
llm/pairs.jsonl (every evaluated pair, with the prompt id for its pristine and its
mutated side). The prompts are run on a local model by llm/llm_run.py, and the
answers scored by experiments/llm_score.py. Deterministic; no network.

Pair sets: the authored corpus (original operators, semantic faults, targeted
WEAKEN, R14 faults, R15 placeholders) and the independent corpus (original operators).
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from cdc import codebase as cb
from experiments import external as X
from experiments import revision as R
from experiments import revision2 as R2
from experiments.run_all import load_manifest

MAX_LINES = 150
SRC = {}  # id(CodeElement) -> source text
_KEEP = []

PROMPT = """You are reviewing a student software project. A sentence from the project report \
makes a claim about the code. Below is one code element from the project.

Claim: {claim}

Code element `{name}` from `{path}`:
```python
{source}
```

Does this code element actually implement what the claim states? Judge the code itself, \
not its name or docstring. Answer with exactly one word: YES or NO."""


def _source_of(src_text, tree, el):
    if el.kind in {"function", "method", "test", "class"}:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and node.name == el.name and node.lineno == el.lineno:
                seg = ast.get_source_segment(src_text, node, padded=True) or ""
                break
        else:
            seg = ""
    else:
        lines = src_text.splitlines()
        seg = "\n".join(lines[max(el.lineno - 1, 0): el.lineno + 14])
    lines = seg.splitlines()
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES] + [f"# ... {len(lines) - MAX_LINES} more lines omitted"]
    return "\n".join(lines)


def capturing(extract):
    def run(root):
        els = extract(root)
        cache = {}
        for el in els:
            path = os.path.join(root, *el.path.split("/"))
            if path not in cache:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                cache[path] = (text, ast.parse(text))
            text, tree = cache[path]
            SRC[id(el)] = _source_of(text, tree, el)
        _KEEP.append(els)
        return els
    return run


def install(extract):
    wrapped = capturing(extract)
    R.extract_codebase = wrapped
    R2.extract_codebase = wrapped
    return wrapped


def authored_pristine(wrapped):
    out = []
    for e in load_manifest()["projects"]:
        from cdc.claims import extract_claims
        code = os.path.join(ROOT, e["code_dir"])
        with open(os.path.join(ROOT, e["doc_md"]), encoding="utf-8") as fh:
            claims = extract_claims(fh.read(), "md")
        out.append((e["name"], (code, claims, wrapped(code))))
    return out


def pid(claim_text, el):
    h = hashlib.sha1()
    h.update(claim_text.encode())
    h.update(b"\0")
    h.update(el.name.encode())
    h.update(b"\0")
    h.update(el.path.encode())
    h.update(b"\0")
    h.update(SRC[id(el)].encode())
    return h.hexdigest()[:16]


def main():
    out_dir = os.path.join(ROOT, "llm")
    os.makedirs(out_dir, exist_ok=True)
    prompts, rows = {}, []

    def add(pairs, corpus, family):
        for p in pairs:
            rec = {"corpus": corpus, "family": family, "project": p["project"],
                   "round": p["round"], "cid": p["cid"], "uid": p["uid"],
                   "operator": p["operator"], "pre": None, "mut": None}
            for side, el in (("pre", p["pre_el"]), ("mut", p["mut_el"])):
                if el is None:
                    continue
                k = pid(p["claim"].text, el)
                if k not in prompts:
                    prompts[k] = PROMPT.format(claim=p["claim"].text, name=el.name,
                                               path=el.path, source=SRC[id(el)])
                rec[side] = k
            rows.append(rec)

    wrapped = install(cb.extract_codebase)
    pristine = authored_pristine(wrapped)
    add(R.build_pairs(R.build_scenarios(pristine, "original")), "authored", "original")
    add(R.build_pairs(R.build_scenarios(pristine, "semantic")), "authored", "semantic")
    add(R.targeted_weaken(pristine)[0], "authored", "weaken")
    add(R2.r14_pairs_of(pristine)[0], "authored", "r14")
    add(R2.r15_pairs_of(pristine)[0], "authored", "placeholder")

    X.set_mode("default")
    wrapped = install(X._ORIG_EXTRACT)
    ext, _man = X.load_ext("default")
    ext = [(n, (c, cl, wrapped(c))) for n, (c, cl, _e) in ext]
    add(R.build_pairs(R.build_scenarios(ext, "original")), "external", "original")

    with open(os.path.join(out_dir, "prompts.jsonl"), "w", encoding="utf-8") as fh:
        for k in sorted(prompts):
            fh.write(json.dumps({"id": k, "prompt": prompts[k]}) + "\n")
    with open(os.path.join(out_dir, "pairs.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    print(len(prompts), "prompts,", len(rows), "pairs")


if __name__ == "__main__":
    main()

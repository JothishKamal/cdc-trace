"""
X7: test adequacy of both corpora (review items D4 and R02 section 9).

For each project, copies the code to a temporary folder, runs its tests under coverage.py
with branch coverage, and records line and branch coverage of the non-test code, the
number of tests passed and failed, and assert statements per test function.
Needs pytest and coverage. Writes results/coverage.json.
"""
from __future__ import annotations

import ast
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from experiments.revision import write_manifest  # noqa: E402


def projects():
    out = []
    for man, corpus in (("corpus/manifest.json", "authored"), ("corpus_ext/manifest.json", "libraries")):
        with open(os.path.join(ROOT, man), encoding="utf-8") as fh:
            for p in json.load(fh)["projects"]:
                out.append((corpus, p["name"], os.path.join(ROOT, p["code_dir"])))
    return out


def is_test(path):
    parts = path.replace(os.sep, "/").split("/")
    return "tests" in parts or os.path.basename(path).startswith("test_")


def asserts_per_test(code):
    n_tests = n_asserts = 0
    for f in glob.glob(os.path.join(code, "**", "*.py"), recursive=True):
        rel = os.path.relpath(f, code)
        if not is_test(rel):
            continue
        tree = ast.parse(open(f, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                n_tests += 1
                n_asserts += sum(isinstance(x, ast.Assert) or (
                    isinstance(x, ast.Call) and (
                        (isinstance(x.func, ast.Attribute) and x.func.attr.startswith("assert"))
                        or (isinstance(x.func, ast.Name) and x.func.id.startswith("assert"))
                        or (isinstance(x.func, ast.Attribute) and x.func.attr in ("raises", "warns"))))
                    for x in ast.walk(node))
    return n_tests, n_asserts


def run_one(code):
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "code")
        shutil.copytree(code, work, ignore=shutil.ignore_patterns("__pycache__"))
        src = [os.path.relpath(f, work) for f in glob.glob(os.path.join(work, "**", "*.py"), recursive=True)
               if not is_test(os.path.relpath(f, work))]
        rc = open(os.path.join(work, ".coveragerc"), "w")
        rc.write("[run]\nbranch = True\nsource = .\nomit =\n    tests/*\n    */tests/*\n    test_*.py\n    */test_*.py\n")
        rc.close()
        # deprecation's tests import unittest2, an old backport of unittest that no longer
        # imports on current Python; a one-line stand-in is put on the path instead.
        shims = os.path.join(tmp, "shims")
        os.makedirs(shims)
        with open(os.path.join(shims, "unittest2.py"), "w") as fh:
            fh.write("from unittest import *  # noqa: F401,F403\n")
        env = dict(os.environ, PYTHONPATH=work + os.pathsep + shims, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run(
            [sys.executable, "-m", "coverage", "run", "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "--junitxml", os.path.join(tmp, "junit.xml"), "."],
            cwd=work, env=env, capture_output=True, text=True, timeout=1800)
        subprocess.run([sys.executable, "-m", "coverage", "json", "-o", os.path.join(tmp, "cov.json")],
                       cwd=work, env=env, capture_output=True, text=True)
        with open(os.path.join(tmp, "cov.json"), encoding="utf-8") as fh:
            cov = json.load(fh)["totals"]
        import xml.etree.ElementTree as ET
        suites = ET.parse(os.path.join(tmp, "junit.xml")).getroot()
        s = suites if suites.tag == "testsuite" else suites.find("testsuite")
        tests, fail, err, skip = (int(s.get(k, 0)) for k in ("tests", "failures", "errors", "skipped"))
        return {
            "source_files": len(src),
            "statements": cov["num_statements"], "covered_statements": cov["covered_lines"],
            "line_coverage": round(100.0 * cov["covered_lines"] / cov["num_statements"], 1),
            "branches": cov["num_branches"], "covered_branches": cov["covered_branches"],
            "branch_coverage": round(100.0 * cov["covered_branches"] / cov["num_branches"], 1)
            if cov["num_branches"] else None,
            "tests_run": tests, "tests_failed": fail + err, "tests_skipped": skip,
            # the summary line without its wall-clock time, so reruns give identical files
            "pytest_tail": re.sub(r" in [0-9.]+s.*$", "", proc.stdout.strip().splitlines()[-1].strip("= "))
            if proc.stdout.strip() else "",
        }


def main():
    out = {}
    for corpus, name, code in projects():
        r = run_one(code)
        r["test_functions"], r["asserts"] = asserts_per_test(code)
        out.setdefault(corpus, {})[name] = r
        print(f"{corpus:9s} {name:12s} line {r['line_coverage']:5.1f}%  branch {r['branch_coverage']}%  "
              f"tests {r['tests_run']} failed {r['tests_failed']} skipped {r['tests_skipped']}  "
              f"asserts/test {r['asserts'] / max(r['test_functions'], 1):.2f}")
    with open(os.path.join(ROOT, "results", "coverage.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, sort_keys=True, indent=2)
        fh.write("\n")
    write_manifest()


if __name__ == "__main__":
    main()

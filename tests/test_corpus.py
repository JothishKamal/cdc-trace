"""Corpus integrity checks."""
import ast
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from cdc.claims import extract_claims
from cdc.codebase import extract_codebase


def manifest():
    with open(os.path.join(ROOT, "corpus", "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_manifest_lists_six_projects():
    assert len(manifest()["projects"]) == 6


def test_every_project_parses_and_yields_elements():
    for p in manifest()["projects"]:
        els = extract_codebase(os.path.join(ROOT, p["code_dir"]))
        assert len(els) >= 8, p["name"]


def test_every_document_yields_enough_claims():
    for p in manifest()["projects"]:
        with open(os.path.join(ROOT, p["doc_md"]), encoding="utf-8") as fh:
            claims = extract_claims(fh.read(), "md")
        assert len(claims) >= 12, f"{p['name']} yielded only {len(claims)} claims"


def test_markdown_and_latex_documents_agree_per_project():
    for p in manifest()["projects"]:
        with open(os.path.join(ROOT, p["doc_md"]), encoding="utf-8") as fh:
            md = [(c.component, c.text) for c in extract_claims(fh.read(), "md")]
        with open(os.path.join(ROOT, p["doc_tex"]), encoding="utf-8") as fh:
            tex = [(c.component, c.text) for c in extract_claims(fh.read(), "tex")]
        assert md == tex, p["name"]


def test_most_claims_are_supported_on_unmutated_code():
    """A corpus where the pristine code fails its own document is a broken corpus."""
    from cdc.scoring import score_document
    for p in manifest()["projects"]:
        els = extract_codebase(os.path.join(ROOT, p["code_dir"]))
        with open(os.path.join(ROOT, p["doc_md"]), encoding="utf-8") as fh:
            claims = extract_claims(fh.read(), "md")
        report = score_document(claims, els)
        assert report.gap_score <= 0.25, f"{p['name']} gap {report.gap_score:.2f}"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")

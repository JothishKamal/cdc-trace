"""End-to-end integration: the NOMINAL adversary on real corpus code."""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from cdc.claims import extract_claims
from cdc.codebase import extract_codebase
from cdc.evidence import gather
from cdc.mutate import mutate_source
from cdc.scoring import verdict


def test_nominal_mutation_flips_a_claim_to_unsupported():
    src = os.path.join(ROOT, "corpus", "sessionstore")
    elements = extract_codebase(os.path.join(src, "code"))
    with open(os.path.join(src, "doc.md"), encoding="utf-8") as fh:
        claims = extract_claims(fh.read(), "md")

    # Find a claim that the pristine code supports.
    target = None
    for c in claims:
        if verdict(gather(c, elements)) == "SUPPORTED":
            target = c
            break
    assert target is not None, "corpus supports no claim; corpus is broken"

    # Gut the element it depends on, keeping name and docstring.
    best = max(elements, key=lambda e: len(target.terms & set(e.name.lower().split("_"))))
    with tempfile.TemporaryDirectory() as d:
        dst = os.path.join(d, "code")
        shutil.copytree(os.path.join(src, "code"), dst)
        path = os.path.join(dst, os.path.basename(best.path))
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(mutate_source(source, best.name, "NOMINAL"))
        mutated = extract_codebase(dst)

    assert verdict(gather(target, mutated)) != "SUPPORTED"


if __name__ == "__main__":
    test_nominal_mutation_flips_a_claim_to_unsupported()
    print("ok: test_nominal_mutation_flips_a_claim_to_unsupported")
    print("1 tests passed")

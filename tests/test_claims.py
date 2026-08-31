"""Unit tests for claim extraction from Markdown and LaTeX."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.claims import extract_claims

MD = """# Design

## Cryptography

AES-GCM encrypts the session token. This section is introductory.

The system stores sessions in a dedicated table.

## Routing

The API exposes a /health endpoint.
"""

TEX = r"""\section{Cryptography}
AES-GCM encrypts the session token. This section is introductory.

The system stores sessions in a dedicated table.

\section{Routing}
The API exposes a /health endpoint.
"""


def test_extracts_only_assertive_sentences():
    claims = extract_claims(MD, "md")
    texts = [c.text for c in claims]
    assert any("AES-GCM encrypts" in t for t in texts)
    assert not any("introductory" in t for t in texts)


def test_component_is_the_nearest_heading():
    claims = {c.text: c for c in extract_claims(MD, "md")}
    crypto = next(c for t, c in claims.items() if "AES-GCM" in t)
    routing = next(c for t, c in claims.items() if "/health" in t)
    assert crypto.component == "Cryptography"
    assert routing.component == "Routing"


def test_terms_and_implied_libraries_are_derived():
    claim = next(c for c in extract_claims(MD, "md") if "AES-GCM" in c.text)
    assert {"aes", "gcm", "session", "token"} <= claim.terms
    assert "cryptography" in claim.implied_libs


def test_kind_is_assigned_by_keyword():
    claims = {c.text: c.kind for c in extract_claims(MD, "md")}
    assert next(k for t, k in claims.items() if "AES-GCM" in t) == "algorithm"
    assert next(k for t, k in claims.items() if "/health" in t) == "interface"
    assert next(k for t, k in claims.items() if "table" in t) == "data"


def test_markdown_and_latex_frontends_agree():
    md = [(c.component, c.text) for c in extract_claims(MD, "md")]
    tex = [(c.component, c.text) for c in extract_claims(TEX, "tex")]
    assert md == tex


def test_claim_ids_are_stable_and_unique():
    a = [c.cid for c in extract_claims(MD, "md")]
    b = [c.cid for c in extract_claims(MD, "md")]
    assert a == b and len(set(a)) == len(a)


def test_assertive_verbs_match_whole_tokens_only():
    claims = extract_claims("## Users\n\nThe user profile is optional.\n", "md")
    assert claims == []


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")

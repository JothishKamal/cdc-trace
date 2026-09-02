"""Unit tests for the policy family."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.embed import TfidfEmbedder
from cdc.model import Claim, CodeElement, Evidence
from cdc.policies import POLICIES, POLICY_LABELS

CLAIM = Claim(cid="c1", component="Crypto",
              text="AES-GCM encrypts the session token.", kind="algorithm",
              terms=frozenset({"aes", "gcm", "encrypts", "session", "token"}),
              implied_libs=frozenset({"cryptography"}), section="1")

NOMINAL_ELEMENT = CodeElement(
    uid="m:f", kind="function", name="aes_gcm_encrypt_token",
    path="crypto/aes.py", lineno=1,
    doc="Encrypts the session token with AES-GCM.",
    imports=frozenset(), calls=frozenset(), body_ops=frozenset(),
    is_stub=True, reachable=False)

NOMINAL_EVIDENCE = [
    Evidence("c1", "m:f", "NAME",
             frozenset({"ch:NAME", "tok:aes", "tok:gcm", "file:crypto/aes.py"}), 0.9),
    Evidence("c1", "m:f", "DOC",
             frozenset({"ch:DOC", "tok:aes", "tok:gcm", "file:crypto/aes.py"}), 0.9),
]


def test_every_policy_has_a_label():
    assert set(POLICIES) == set(POLICY_LABELS)
    assert len(POLICIES) == 7


def test_all_policies_share_one_signature():
    emb = TfidfEmbedder([CLAIM.text, NOMINAL_ELEMENT.name])
    for name, fn in POLICIES.items():
        out = fn(CLAIM, [NOMINAL_ELEMENT], NOMINAL_EVIDENCE,
                 embedder=emb, threshold=0.3, k_min=2)
        assert isinstance(out, bool), name


def test_nominal_mutation_fools_the_baselines_and_not_cdc():
    """The headline claim, pinned as a test."""
    emb = TfidfEmbedder([CLAIM.text, NOMINAL_ELEMENT.name, NOMINAL_ELEMENT.doc])
    kw = dict(embedder=emb, threshold=0.3, k_min=2)
    assert POLICIES["lexical"](CLAIM, [NOMINAL_ELEMENT], NOMINAL_EVIDENCE, **kw)
    assert POLICIES["hybrid"](CLAIM, [NOMINAL_ELEMENT], NOMINAL_EVIDENCE, **kw)
    assert POLICIES["evidence_count"](CLAIM, [NOMINAL_ELEMENT], NOMINAL_EVIDENCE, **kw)
    assert POLICIES["channel_count"](CLAIM, [NOMINAL_ELEMENT], NOMINAL_EVIDENCE, **kw)
    assert not POLICIES["cdc"](CLAIM, [NOMINAL_ELEMENT], NOMINAL_EVIDENCE, **kw)
    assert not POLICIES["cdc_counterfactual"](CLAIM, [NOMINAL_ELEMENT],
                                              NOMINAL_EVIDENCE, **kw)


def test_tfidf_similarity_is_symmetric_and_bounded():
    emb = TfidfEmbedder(["aes gcm encrypt token", "parse json config"])
    s = emb.similarity("aes gcm encrypt token", "parse json config")
    assert 0.0 <= s <= 1.0
    assert abs(s - emb.similarity("parse json config", "aes gcm encrypt token")) < 1e-9
    assert emb.similarity("aes gcm", "aes gcm") > 0.99


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")

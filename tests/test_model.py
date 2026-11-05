"""Unit tests for the data model and token normalisation."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.model import Claim, CodeElement, Evidence, sub_tokens


def test_sub_tokens_splits_snake_and_camel_case():
    assert sub_tokens("aes_gcm_encrypt_token") == ["aes", "gcm", "encrypt", "token"]
    assert sub_tokens("AesGcmEncryptToken") == ["aes", "gcm", "encrypt", "token"]
    assert sub_tokens("crypto/aes_gcm.py") == ["crypto", "aes", "gcm"]  # "py" is stoplisted


def test_sub_tokens_drops_stoplist_and_single_characters():
    assert sub_tokens("get_user_handler") == ["user"]
    assert sub_tokens("a_b_session") == ["session"]


def test_sub_tokens_handles_acronym_boundaries():
    assert sub_tokens("HTTPSConnection") == ["https", "connection"]


def test_evidence_is_frozen_and_hashable():
    e = Evidence(claim="c1", element="m:f", channel="NAME",
                 provenance=frozenset({"ch:NAME", "tok:aes"}), strength=0.9)
    assert hash(e) is not None
    try:
        e.strength = 0.1
        raise AssertionError("Evidence must be immutable")
    except AttributeError:
        pass


def test_dataclasses_construct_with_expected_fields():
    el = CodeElement(uid="m:f", kind="function", name="f", path="m.py", lineno=1,
                     doc="", imports=frozenset(), calls=frozenset(),
                     body_ops=frozenset(), is_stub=False, reachable=True)
    assert el.uid == "m:f" and not el.is_stub
    cl = Claim(cid="c1", component="Crypto", text="AES-GCM encrypts the token.",
               kind="algorithm", terms=frozenset({"aes", "gcm"}),
               implied_libs=frozenset({"cryptography"}), section="3.1")
    assert cl.component == "Crypto"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")

"""Unit tests for evidence channels and provenance construction."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.corroborate import corroboration
from cdc.evidence import gather
from cdc.model import Claim, CodeElement

CLAIM = Claim(cid="c1", component="Crypto",
              text="AES-GCM encrypts the session token.", kind="algorithm",
              terms=frozenset({"aes", "gcm", "encrypts", "session", "token"}),
              implied_libs=frozenset({"cryptography"}), section="1")


def el(uid, name, path, doc="", imports=(), calls=(), body_ops=(),
       kind="function", is_stub=False, reachable=True):
    return CodeElement(uid=uid, kind=kind, name=name, path=path, lineno=1,
                       doc=doc, imports=frozenset(imports),
                       calls=frozenset(calls), body_ops=frozenset(body_ops),
                       is_stub=is_stub, reachable=reachable)


def channels(ev):
    return {e.channel for e in ev}


def test_name_channel_carries_shared_tokens_and_file():
    ev = gather(CLAIM, [el("m:f", "aes_gcm_encrypt_token", "crypto/aes.py")])
    name = next(e for e in ev if e.channel == "NAME")
    assert "ch:NAME" in name.provenance
    assert "tok:aes" in name.provenance and "tok:gcm" in name.provenance
    assert "file:crypto/aes.py" in name.provenance


def test_docstring_restating_the_name_is_dependent_not_corroborating():
    """The central case: name plus its own docstring is ONE reason, not two."""
    ev = gather(CLAIM, [el("m:f", "aes_gcm_encrypt_token", "crypto/aes.py",
                           doc="Encrypts the session token with AES-GCM.")])
    assert {"NAME", "DOC"} <= channels(ev)
    assert corroboration(ev) == 1


def test_import_in_another_file_is_independent_of_the_name():
    ev = gather(CLAIM, [
        el("m:f", "aes_gcm_encrypt_token", "crypto/aes.py"),
        el("s:g", "open_session", "session.py", imports=["cryptography"]),
    ])
    assert corroboration(ev) >= 2


def test_call_channel_uses_the_caller_file_not_the_callee():
    ev = gather(CLAIM, [
        el("m:f", "aes_gcm_encrypt_token", "crypto/aes.py"),
        el("a:h", "handle_login", "web/app.py", calls=["aes_gcm_encrypt_token"]),
    ])
    call = next(e for e in ev if e.channel == "CALL")
    assert "file:web/app.py" in call.provenance
    assert "file:crypto/aes.py" not in call.provenance
    assert "sym:a:h" in call.provenance


def test_body_channel_requires_a_real_operation():
    live = gather(CLAIM, [el("m:f", "aes_gcm_encrypt_token", "crypto/aes.py",
                             body_ops=["op:aead"])])
    assert "BODY" in channels(live)
    stub = gather(CLAIM, [el("m:f", "aes_gcm_encrypt_token", "crypto/aes.py",
                             body_ops=[], is_stub=True)])
    assert "BODY" not in channels(stub)


def test_nominal_stub_collapses_corroboration_to_one():
    """Name and docstring intact, body gutted: every baseline is fooled."""
    ev = gather(CLAIM, [el("m:f", "aes_gcm_encrypt_token", "crypto/aes.py",
                           doc="Encrypts the session token with AES-GCM.",
                           body_ops=[], is_stub=True, reachable=False)])
    assert {"NAME", "DOC"} <= channels(ev)
    assert corroboration(ev) == 1


def test_test_channel_uses_the_test_file():
    ev = gather(CLAIM, [
        el("m:f", "aes_gcm_encrypt_token", "crypto/aes.py"),
        el("t:t", "test_encrypt", "tests/test_crypto.py", kind="test",
           calls=["aes_gcm_encrypt_token"]),
    ])
    t = next(e for e in ev if e.channel == "TEST")
    assert "file:tests/test_crypto.py" in t.provenance


def test_weak_matches_are_not_emitted():
    ev = gather(CLAIM, [el("z:z", "unrelated_widget_factory", "ui/widget.py")])
    assert ev == []


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")

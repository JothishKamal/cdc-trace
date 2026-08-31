"""Unit tests for AST-level code extraction."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cdc.codebase import extract_codebase, extract_source

SAMPLE = '''
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SCHEMA = {"sessions": ["id", "token"], "users": ["id", "email"]}


def aes_gcm_encrypt_token(token, key):
    """Encrypts the session token with AES-GCM."""
    box = AESGCM(key)
    return box.encrypt(b"n", token, None)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def unimplemented_rotation():
    """Rotates the signing key daily."""
    raise NotImplementedError


def main():
    aes_gcm_encrypt_token(b"t", b"k" * 32)
'''


def by_name(elements):
    return {e.name: e for e in elements}


def test_extracts_functions_with_docstrings_and_lines():
    els = by_name(extract_source(SAMPLE, "crypto/aes.py"))
    assert "aes_gcm_encrypt_token" in els
    e = els["aes_gcm_encrypt_token"]
    assert e.kind == "function"
    assert "AES-GCM" in e.doc
    assert e.path == "crypto/aes.py"
    assert e.lineno > 0


def test_records_imports_and_calls():
    els = by_name(extract_source(SAMPLE, "crypto/aes.py"))
    assert "cryptography" in els["aes_gcm_encrypt_token"].imports
    assert "hashlib" in els["digest"].imports
    assert "AESGCM" in els["aes_gcm_encrypt_token"].calls


def test_detects_stub_bodies():
    els = by_name(extract_source(SAMPLE, "crypto/aes.py"))
    assert els["unimplemented_rotation"].is_stub
    assert not els["aes_gcm_encrypt_token"].is_stub


def test_body_ops_capture_the_operations_actually_performed():
    els = by_name(extract_source(SAMPLE, "crypto/aes.py"))
    assert "op:aead" in els["aes_gcm_encrypt_token"].body_ops
    assert "op:hash" in els["digest"].body_ops
    assert els["unimplemented_rotation"].body_ops == frozenset()


def test_schema_elements_are_extracted():
    els = extract_source(SAMPLE, "crypto/aes.py")
    tables = {e.name for e in els if e.kind == "table"}
    assert tables == {"sessions", "users"}


def test_reachability_is_transitive_from_entry_points():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "app.py"), "w", encoding="utf-8") as fh:
            fh.write(SAMPLE)
        els = by_name(extract_codebase(d))
    assert els["aes_gcm_encrypt_token"].reachable      # called by main
    assert not els["digest"].reachable                 # never called


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"{len(fns)} tests passed")

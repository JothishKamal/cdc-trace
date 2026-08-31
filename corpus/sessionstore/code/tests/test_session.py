from crypto import (
    aes_gcm_decrypt_token,
    aes_gcm_encrypt_token,
    hash_session_token,
    rotate_session_key,
)
from persist import query_session, store_session


def test_aes_gcm_encrypt_token():
    key = rotate_session_key()
    blob = aes_gcm_encrypt_token(key, b"tok")
    assert isinstance(blob, bytes)


def test_aes_gcm_decrypt_token():
    key = rotate_session_key()
    blob = aes_gcm_encrypt_token(key, b"tok")
    aes_gcm_decrypt_token(key, blob)


def test_hash_session_token():
    digest = hash_session_token(b"tok")
    assert isinstance(digest, str)


def test_store_session():
    store_session("s1", "u1", "a" * 64, 1)


def test_query_session():
    store_session("s2", "u2", "b" * 64, 2)
    query_session("s2")


def test_rotate_session_key():
    key = rotate_session_key()
    assert isinstance(key, bytes)

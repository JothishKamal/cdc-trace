from crypto import (
    aes_gcm_decrypt_token,
    aes_gcm_encrypt_token,
    hash_session_token,
    rotate_session_key,
)
from persist import query_session, store_session


def main():
    """Run an encrypt, hash, store, and query round trip."""
    key = rotate_session_key()
    token = b"session-token-example"
    blob = aes_gcm_encrypt_token(key, token)
    plain = aes_gcm_decrypt_token(key, blob)
    digest = hash_session_token(plain)
    store_session("s1", "u1", digest, 0)
    row = query_session("s1")
    return {"plain": plain, "row": row, "key": key}


if __name__ == "__main__":
    main()

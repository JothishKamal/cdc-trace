from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import hashlib
import secrets


NONCE_SIZE = 12
KEY_SIZE = 32


def aes_gcm_encrypt_token(key, token):
    if not isinstance(key, (bytes, bytearray)):
        raise TypeError("key must be bytes")
    if len(key) != KEY_SIZE:
        raise ValueError("key must be 32 bytes")
    if not isinstance(token, (bytes, bytearray)):
        raise TypeError("token must be bytes")
    nonce = secrets.token_bytes(NONCE_SIZE)
    aesgcm = AESGCM(bytes(key))
    ciphertext = aesgcm.encrypt(nonce, bytes(token), None)
    return nonce + ciphertext


def aes_gcm_decrypt_token(key, blob):
    if not isinstance(key, (bytes, bytearray)):
        raise TypeError("key must be bytes")
    if len(key) != KEY_SIZE:
        raise ValueError("key must be 32 bytes")
    if not isinstance(blob, (bytes, bytearray)):
        raise TypeError("blob must be bytes")
    raw = bytes(blob)
    if len(raw) < NONCE_SIZE + 16:
        raise ValueError("ciphertext too short")
    nonce = raw[:NONCE_SIZE]
    ciphertext = raw[NONCE_SIZE:]
    aesgcm = AESGCM(bytes(key))
    return aesgcm.decrypt(nonce, ciphertext, None)


def hash_session_token(token):
    if not isinstance(token, (bytes, bytearray)):
        raise TypeError("token must be bytes")
    digest = hashlib.sha256(bytes(token))
    return digest.hexdigest()


def rotate_session_key(old_key=None):
    new_key = secrets.token_bytes(KEY_SIZE)
    if old_key is not None and old_key == new_key:
        return secrets.token_bytes(KEY_SIZE)
    return new_key

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import hashlib
import secrets


NONCE_SIZE = 12
KEY_SIZE = 32


def aes_gcm_encrypt_token(key, token):
    """Encrypt a session token with AES GCM.

    The function uses cryptography AESGCM so the returned blob carries a
    nonce followed by authenticated ciphertext.
    """
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
    """Return the plaintext token from an AES GCM blob.

    The first twelve bytes are the nonce; the remainder is ciphertext
    that AESGCM decrypts under the same key.
    """
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
    """Hash a session token with sha256 via hashlib.

    The digest is a lowercase hex string so persist can store it without
    keeping the recoverable token.
    """
    if not isinstance(token, (bytes, bytearray)):
        raise TypeError("token must be bytes")
    digest = hashlib.sha256(bytes(token))
    return digest.hexdigest()


def rotate_session_key(old_key=None):
    """Generate a random session key and rotate away from old_key.

    Fresh material comes from secrets.token_bytes so the new key is not
    derived from the previous one.
    """
    new_key = secrets.token_bytes(KEY_SIZE)
    if old_key is not None and bytes(old_key) == new_key:
        new_key = secrets.token_bytes(KEY_SIZE)
    return new_key

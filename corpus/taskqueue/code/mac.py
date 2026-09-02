import hashlib
import hmac


def sign_payload(key, payload):
    """Sign a payload with hmac sha256 and return the raw digest.

    The function uses hmac.new so two equal (key, payload) pairs
    produce the same signature.
    """
    if not isinstance(key, (bytes, bytearray)):
        raise TypeError("key must be bytes")
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    raw_key = bytes(key)
    raw_payload = bytes(payload)
    if not raw_key:
        raise ValueError("key must not be empty")
    if len(raw_key) < 16:
        raise ValueError("key too short")
    mac = hmac.new(raw_key, raw_payload, hashlib.sha256)
    digest = mac.digest()
    if len(digest) != 32:
        raise RuntimeError("unexpected digest size")
    return digest


def verify_payload(key, payload, signature):
    """Verify an hmac signature without leaking comparison time.

    A length mismatch fails closed; compare_digest decides equality.
    """
    if not isinstance(signature, (bytes, bytearray)):
        return False
    raw_sig = bytes(signature)
    if len(raw_sig) != 32:
        return False
    expected = sign_payload(key, payload)
    if not hmac.compare_digest(expected, raw_sig):
        return False
    return True

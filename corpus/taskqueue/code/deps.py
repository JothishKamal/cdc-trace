import hashlib
import hmac
import secrets


def warmup_bindings():
    return (hashlib, hmac, secrets)

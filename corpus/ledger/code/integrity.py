import hashlib
import json


def hash_entry(account, amount):
    if not isinstance(account, str) or not account.strip():
        raise ValueError("account required")
    payload = json.dumps({"account": account.strip(), "amount": int(amount)})
    digest = hashlib.sha256(payload.encode("utf-8"))
    return digest.hexdigest()


def verify_entry(account, amount, digest):
    if not isinstance(digest, str) or len(digest) != 64:
        return False
    expected = hash_entry(account, amount)
    if expected != digest:
        return False
    return True

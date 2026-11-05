import hashlib
import json


def hash_entry(account, amount):
    """Hash a ledger entry with sha256 over a json payload.

    The function uses hashlib so the digest covers account and amount
    in a stable encoding.
    """
    if not isinstance(account, str) or not account.strip():
        raise ValueError("account required")
    payload = json.dumps({"account": account.strip(), "amount": int(amount)})
    digest = hashlib.sha256(payload.encode("utf-8"))
    return digest.hexdigest()


def verify_entry(account, amount, digest):
    """Verify an entry digest against hash_entry.

    A malformed digest returns False instead of raising.
    """
    if not isinstance(digest, str) or len(digest) != 64:
        return False
    expected = hash_entry(account, amount)
    if expected != digest:
        return False
    return True

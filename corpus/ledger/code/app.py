from db import insert_entry, query_entry, store_account
from integrity import hash_entry, verify_entry


def main():
    """Hash an entry, insert it, query it, and verify the digest."""
    store_account("a1", "cash", 0)
    digest = hash_entry("a1", 50)
    entry_id = insert_entry("a1", 50, digest)
    row = query_entry(entry_id)
    ok = verify_entry("a1", 50, digest)
    return {"row": row, "ok": ok}


if __name__ == "__main__":
    main()

from schema import SCHEMA, connect_memory


_CONN = None


def _db():
    global _CONN
    if _CONN is None:
        _CONN = connect_memory()
    return _CONN


def insert_entry(account, amount, digest):
    """Store a ledger entry in the database.

    The insert writes account, amount, and an integrity digest into the
    entries table.
    """
    if not isinstance(account, str) or not account.strip():
        raise ValueError("account required")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("digest must be a sha256 hex string")
    conn = _db()
    cursor = conn.execute(
        "INSERT INTO entries (account, amount, digest) VALUES (?, ?, ?)",
        (account.strip(), int(amount), digest),
    )
    conn.commit()
    return cursor.lastrowid


def query_entry(entry_id):
    """Query the entries table and return one row mapping."""
    conn = _db()
    cursor = conn.execute(
        "SELECT id, account, amount, digest FROM entries WHERE id = ?",
        (entry_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columns = SCHEMA["entries"]
    return {
        columns[0]: row[0],
        columns[1]: row[1],
        columns[2]: row[2],
        columns[3]: row[3],
    }


def store_account(account_id, name, balance):
    """Store an account row in the database using sql upsert."""
    if not isinstance(account_id, str) or not account_id.strip():
        raise ValueError("account id required")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name required")
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO accounts (id, name, balance) VALUES (?, ?, ?)",
        (account_id.strip(), name.strip(), int(balance)),
    )
    conn.commit()
    return account_id.strip()

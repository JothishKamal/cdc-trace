import sqlite3


_CREATE_ENTRIES = (
    "CREATE TABLE IF NOT EXISTS entries ("
    "id INTEGER PRIMARY KEY, "
    "account TEXT NOT NULL, "
    "amount INTEGER NOT NULL, "
    "digest TEXT NOT NULL"
    ")"
)
_CREATE_ACCOUNTS = (
    "CREATE TABLE IF NOT EXISTS accounts ("
    "id TEXT PRIMARY KEY, "
    "name TEXT NOT NULL, "
    "balance INTEGER NOT NULL"
    ")"
)


_CONN = None


def _connect():
    conn = sqlite3.connect(":memory:")
    conn.execute(_CREATE_ACCOUNTS)
    conn.execute(_CREATE_ENTRIES)
    conn.commit()
    return conn


def _db():
    global _CONN
    if _CONN is None:
        _CONN = _connect()
    return _CONN


def insert_entry(account, amount, digest):
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
    conn = _db()
    cursor = conn.execute(
        "SELECT id, account, amount, digest FROM entries WHERE id = ?",
        (entry_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "account": row[1],
        "amount": row[2],
        "digest": row[3],
    }


def store_account(account_id, name, balance):
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

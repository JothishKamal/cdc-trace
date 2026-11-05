import sqlite3


SCHEMA = {
    "accounts": ["id", "name", "balance"],
    "entries": ["id", "account", "amount", "digest"],
    "balances": ["account", "total"],
}

_CREATE_ACCOUNTS = (
    "CREATE TABLE IF NOT EXISTS accounts ("
    "id TEXT PRIMARY KEY, "
    "name TEXT NOT NULL, "
    "balance INTEGER NOT NULL"
    ")"
)
_CREATE_ENTRIES = (
    "CREATE TABLE IF NOT EXISTS entries ("
    "id INTEGER PRIMARY KEY, "
    "account TEXT NOT NULL, "
    "amount INTEGER NOT NULL, "
    "digest TEXT NOT NULL"
    ")"
)
_CREATE_BALANCES = (
    "CREATE TABLE IF NOT EXISTS balances ("
    "account TEXT PRIMARY KEY, "
    "total INTEGER NOT NULL"
    ")"
)


def create_tables(conn):
    """Create the accounts, entries, and balances tables in SCHEMA."""
    conn.execute(_CREATE_ACCOUNTS)
    conn.execute(_CREATE_ENTRIES)
    conn.execute(_CREATE_BALANCES)
    conn.commit()
    return list(SCHEMA.keys())


def connect_memory():
    """Open an in-memory sqlite3 database and install SCHEMA tables."""
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    return conn

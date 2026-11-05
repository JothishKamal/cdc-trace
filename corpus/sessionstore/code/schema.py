import sqlite3


SCHEMA = {
    "sessions": ["id", "user_id", "token_hash", "expires"],
    "users": ["id", "name", "password_hash"],
}

_CREATE_SESSIONS = (
    "CREATE TABLE IF NOT EXISTS sessions ("
    "id TEXT PRIMARY KEY, "
    "user_id TEXT NOT NULL, "
    "token_hash TEXT NOT NULL, "
    "expires INTEGER NOT NULL"
    ")"
)
_CREATE_USERS = (
    "CREATE TABLE IF NOT EXISTS users ("
    "id TEXT PRIMARY KEY, "
    "name TEXT NOT NULL, "
    "password_hash TEXT NOT NULL"
    ")"
)


def create_tables(conn):
    """Create the sessions and users tables described by SCHEMA."""
    conn.execute(_CREATE_SESSIONS)
    conn.execute(_CREATE_USERS)
    conn.commit()
    return list(SCHEMA.keys())


def connect_memory():
    """Open an in-memory sqlite3 database and install SCHEMA tables."""
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    return conn

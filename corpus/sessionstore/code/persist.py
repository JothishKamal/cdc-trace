import sqlite3


_CREATE = (
    "CREATE TABLE IF NOT EXISTS sessions ("
    "id TEXT PRIMARY KEY, "
    "user_id TEXT NOT NULL, "
    "token_hash TEXT NOT NULL, "
    "expires INTEGER NOT NULL"
    ")"
)


def _connect():
    conn = sqlite3.connect(":memory:")
    conn.execute(_CREATE)
    conn.commit()
    return conn


_CONN = None


def _db():
    global _CONN
    if _CONN is None:
        _CONN = _connect()
    return _CONN


def store_session(session_id, user_id, token_hash, expires):
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO sessions (id, user_id, token_hash, expires) "
        "VALUES (?, ?, ?, ?)",
        (session_id, user_id, token_hash, int(expires)),
    )
    conn.commit()
    return session_id


def query_session(session_id):
    conn = _db()
    cursor = conn.execute(
        "SELECT id, user_id, token_hash, expires FROM sessions WHERE id = ?",
        (session_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "user_id": row[1],
        "token_hash": row[2],
        "expires": row[3],
    }

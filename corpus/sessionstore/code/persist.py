from schema import connect_memory, SCHEMA


_CONN = None


def _db():
    global _CONN
    if _CONN is None:
        _CONN = connect_memory()
    return _CONN


def store_session(session_id, user_id, token_hash, expires):
    """Store a session row in the database.

    The insert writes id, user_id, token_hash, and expires into the
    sessions table defined by SCHEMA.
    """
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("session_id required")
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id required")
    if not isinstance(token_hash, str) or len(token_hash) != 64:
        raise ValueError("token_hash must be a sha256 hex digest")
    conn = _db()
    conn.execute(
        "INSERT OR REPLACE INTO sessions (id, user_id, token_hash, expires) "
        "VALUES (?, ?, ?, ?)",
        (session_id.strip(), user_id.strip(), token_hash, int(expires)),
    )
    conn.commit()
    return session_id.strip()


def query_session(session_id):
    """Query the sessions table and return one row mapping.

    Columns follow SCHEMA: id, user_id, token_hash, and expires.
    """
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("session_id required")
    conn = _db()
    cursor = conn.execute(
        "SELECT id, user_id, token_hash, expires FROM sessions WHERE id = ?",
        (session_id.strip(),),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    columns = SCHEMA["sessions"]
    return {
        columns[0]: row[0],
        columns[1]: row[1],
        columns[2]: row[2],
        columns[3]: row[3],
    }

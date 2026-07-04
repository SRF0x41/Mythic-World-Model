import sqlite3
import uuid
from datetime import datetime

from database import get_connection, init_db as _init_db


def init_db():
    _init_db(["sources"])


def add_source(url, source_type, *, origin=None, author=None,
               published_at=None, credibility_score=None, summary=None,
               raw_text=None):
    """Insert a new source. Returns the source id."""
    conn = get_connection()
    now = datetime.now().isoformat()
    src_id = str(uuid.uuid4())
    published_at = published_at or now
    conn.execute(
        """INSERT INTO sources
           (id, url, origin, author, published_at, source_type,
            credibility_score, summary, raw_text, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (src_id, url, origin, author, published_at, source_type,
         credibility_score, summary, raw_text, now),
    )
    conn.commit()
    conn.close()
    return src_id


def get_source(source_id):
    """Return a single source dict or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sources WHERE id = ?", (source_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_sources(*, source_type=None, limit=100, offset=0):
    """List sources, optionally filtered by type."""
    conn = get_connection()
    query = "SELECT * FROM sources"
    params = []
    if source_type:
        query += " WHERE source_type = ?"
        params.append(source_type)
    query += " ORDER BY ingested_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_sources(query_text):
    """Full-text search across summary, raw_text, author, origin."""
    conn = get_connection()
    pattern = f"%{query_text}%"
    rows = conn.execute(
        """SELECT * FROM sources
           WHERE summary LIKE ? OR raw_text LIKE ? OR author LIKE ? OR origin LIKE ?
           ORDER BY ingested_at DESC LIMIT 100""",
        (pattern, pattern, pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

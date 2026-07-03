import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "sources.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            url TEXT,
            origin TEXT,
            author TEXT,
            published_at TEXT,
            source_type TEXT NOT NULL,
            credibility_score REAL CHECK(credibility_score BETWEEN 0.0 AND 1.0),
            summary TEXT,
            raw_text TEXT,
            ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(url, ingested_at)
        );

        CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
        CREATE INDEX IF NOT EXISTS idx_sources_published ON sources(published_at);
        CREATE INDEX IF NOT EXISTS idx_sources_ingested ON sources(ingested_at);
    """)
    conn.commit()
    conn.close()


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

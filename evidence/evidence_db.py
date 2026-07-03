import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "evidence.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS evidence (
            id TEXT PRIMARY KEY,
            claim TEXT NOT NULL,
            quotation TEXT,
            source_id TEXT NOT NULL,
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS evidence_relations (
            id TEXT PRIMARY KEY,
            evidence_a_id TEXT NOT NULL REFERENCES evidence(id),
            evidence_b_id TEXT NOT NULL REFERENCES evidence(id),
            relation_type TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(evidence_a_id, evidence_b_id)
        );

        CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source_id);
        CREATE INDEX IF NOT EXISTS idx_evidence_created ON evidence(created_at);
    """)
    conn.commit()
    conn.close()


def add_evidence(claim, source_id, *, quotation=None, confidence_score=None):
    """Insert a new evidence object. Returns its id."""
    conn = get_connection()
    ev_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO evidence (id, claim, quotation, source_id, confidence_score, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (ev_id, claim, quotation, source_id, confidence_score, now),
    )
    conn.commit()
    conn.close()
    return ev_id


def get_evidence(evidence_id):
    """Return a single evidence dict or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM evidence WHERE id = ?", (evidence_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_evidence(*, source_id=None, limit=100, offset=0):
    """List evidence, optionally filtered by source."""
    conn = get_connection()
    query = "SELECT * FROM evidence"
    params = []
    if source_id:
        query += " WHERE source_id = ?"
        params.append(source_id)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def relate_evidence(evidence_a_id, evidence_b_id, relation_type):
    """Store a relationship between two pieces of evidence."""
    conn = get_connection()
    rel_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    try:
        conn.execute(
            """INSERT INTO evidence_relations (id, evidence_a_id, evidence_b_id, relation_type, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (rel_id, evidence_a_id, evidence_b_id, relation_type, now),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # relation already exists
    conn.close()
    return rel_id


def get_related(evidence_id):
    """Return evidence objects related to the given evidence id."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT e.*, er.relation_type
           FROM evidence e
           JOIN evidence_relations er
             ON e.id = er.evidence_a_id OR e.id = er.evidence_b_id
           WHERE er.evidence_a_id = ? OR er.evidence_b_id = ?
           AND e.id != ?""",
        (evidence_id, evidence_id, evidence_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_evidence(query_text):
    """Search evidence by claim text."""
    conn = get_connection()
    pattern = f"%{query_text}%"
    rows = conn.execute(
        "SELECT * FROM evidence WHERE claim LIKE ? ORDER BY created_at DESC LIMIT 100",
        (pattern,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

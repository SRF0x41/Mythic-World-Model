import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "signals.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signals (
            id TEXT PRIMARY KEY,
            claim TEXT NOT NULL,
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            frequency INTEGER DEFAULT 0,
            time_distribution TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS signal_evidence (
            signal_id TEXT NOT NULL REFERENCES signals(id),
            evidence_id TEXT NOT NULL,
            PRIMARY KEY(signal_id, evidence_id)
        );

        CREATE INDEX IF NOT EXISTS idx_signals_confidence ON signals(confidence_score);
        CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
    """)
    conn.commit()
    conn.close()


def add_signal(claim, *, confidence_score=None, evidence_ids=None):
    """Create a new signal. Returns the signal id."""
    conn = get_connection()
    sig_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO signals (id, claim, confidence_score, frequency, created_at, updated_at)
           VALUES (?, ?, ?, 0, ?, ?)""",
        (sig_id, claim, confidence_score, now, now),
    )
    if evidence_ids:
        for ev_id in evidence_ids:
            conn.execute(
                "INSERT INTO signal_evidence (signal_id, evidence_id) VALUES (?, ?)",
                (sig_id, ev_id),
            )
        conn.execute(
            "UPDATE signals SET frequency = ? WHERE id = ?",
            (len(evidence_ids), sig_id),
        )
    conn.commit()
    conn.close()
    return sig_id


def add_evidence_to_signal(signal_id, evidence_id):
    """Link additional evidence to an existing signal."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO signal_evidence (signal_id, evidence_id) VALUES (?, ?)",
            (signal_id, evidence_id),
        )
    except sqlite3.IntegrityError:
        pass  # already linked
    conn.execute(
        """UPDATE signals
           SET frequency = (SELECT COUNT(*) FROM signal_evidence WHERE signal_id = ?),
               updated_at = datetime('now')
           WHERE id = ?""",
        (signal_id, signal_id),
    )
    conn.commit()
    conn.close()


def get_signal(signal_id):
    """Return a single signal dict or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM signals WHERE id = ?", (signal_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_signal_with_evidence(signal_id):
    """Return signal dict plus linked evidence ids."""
    conn = get_connection()
    sig = conn.execute("SELECT * FROM signals WHERE id = ?", (signal_id,)).fetchone()
    ev_ids = [r["evidence_id"] for r in conn.execute(
        "SELECT evidence_id FROM signal_evidence WHERE signal_id = ?", (signal_id,)
    ).fetchall()]
    conn.close()
    if not sig:
        return None
    result = dict(sig)
    result["evidence_ids"] = ev_ids
    return result


def list_signals(*, limit=100, offset=0, min_frequency=None):
    """List signals, optionally filtered by minimum frequency."""
    conn = get_connection()
    query = "SELECT * FROM signals"
    params = []
    if min_frequency is not None:
        query += " WHERE frequency >= ?"
        params.append(min_frequency)
    query += " ORDER BY confidence_score DESC, frequency DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_signals(query_text):
    """Search signals by claim text."""
    conn = get_connection()
    pattern = f"%{query_text}%"
    rows = conn.execute(
        "SELECT * FROM signals WHERE claim LIKE ? ORDER BY confidence_score DESC LIMIT 100",
        (pattern,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

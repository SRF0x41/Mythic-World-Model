import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "world_models.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS world_models (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            narrative_synthesis TEXT,
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS wm_models (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            model_id       TEXT NOT NULL,
            PRIMARY KEY(world_model_id, model_id)
        );

        CREATE TABLE IF NOT EXISTS wm_hypotheses (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            hypothesis_id  TEXT NOT NULL,
            PRIMARY KEY(world_model_id, hypothesis_id)
        );

        CREATE TABLE IF NOT EXISTS wm_concepts (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            concept_id     TEXT NOT NULL,
            PRIMARY KEY(world_model_id, concept_id)
        );

        CREATE TABLE IF NOT EXISTS wm_signals (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            signal_id      TEXT NOT NULL,
            PRIMARY KEY(world_model_id, signal_id)
        );

        CREATE TABLE IF NOT EXISTS wm_evidence (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            evidence_id    TEXT NOT NULL,
            PRIMARY KEY(world_model_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS wm_sources (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            source_id      TEXT NOT NULL,
            PRIMARY KEY(world_model_id, source_id)
        );

        CREATE INDEX IF NOT EXISTS idx_wm_confidence ON world_models(confidence_score);
    """)
    conn.commit()
    conn.close()


def add_world_model(name, *, description=None, narrative_synthesis=None,
                    confidence_score=None, model_ids=None,
                    hypothesis_ids=None, concept_ids=None,
                    signal_ids=None, evidence_ids=None, source_ids=None):
    """Create a new world model. Returns the world model id."""
    conn = get_connection()
    wm_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO world_models
           (id, name, description, narrative_synthesis, confidence_score, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (wm_id, name, description, narrative_synthesis,
         confidence_score, now, now),
    )
    if model_ids:
        for m_id in model_ids:
            conn.execute(
                "INSERT INTO wm_models (world_model_id, model_id) VALUES (?, ?)",
                (wm_id, m_id),
            )
    if hypothesis_ids:
        for h_id in hypothesis_ids:
            conn.execute(
                "INSERT INTO wm_hypotheses (world_model_id, hypothesis_id) VALUES (?, ?)",
                (wm_id, h_id),
            )
    if concept_ids:
        for c_id in concept_ids:
            conn.execute(
                "INSERT INTO wm_concepts (world_model_id, concept_id) VALUES (?, ?)",
                (wm_id, c_id),
            )
    if signal_ids:
        for s_id in signal_ids:
            conn.execute(
                "INSERT INTO wm_signals (world_model_id, signal_id) VALUES (?, ?)",
                (wm_id, s_id),
            )
    if evidence_ids:
        for e_id in evidence_ids:
            conn.execute(
                "INSERT INTO wm_evidence (world_model_id, evidence_id) VALUES (?, ?)",
                (wm_id, e_id),
            )
    if source_ids:
        for src_id in source_ids:
            conn.execute(
                "INSERT INTO wm_sources (world_model_id, source_id) VALUES (?, ?)",
                (wm_id, src_id),
            )
    conn.commit()
    conn.close()
    return wm_id


def get_world_model(wm_id):
    """Return a single world model dict or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM world_models WHERE id = ?", (wm_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_world_model_full(wm_id):
    """Return world model with all linked objects."""
    conn = get_connection()
    wm = conn.execute("SELECT * FROM world_models WHERE id = ?", (wm_id,)).fetchone()
    if not wm:
        conn.close()
        return None

    result = dict(wm)
    result["model_ids"] = [r["model_id"] for r in conn.execute(
        "SELECT model_id FROM wm_models WHERE world_model_id = ?", (wm_id,)
    ).fetchall()]
    result["hypothesis_ids"] = [r["hypothesis_id"] for r in conn.execute(
        "SELECT hypothesis_id FROM wm_hypotheses WHERE world_model_id = ?", (wm_id,)
    ).fetchall()]
    result["concept_ids"] = [r["concept_id"] for r in conn.execute(
        "SELECT concept_id FROM wm_concepts WHERE world_model_id = ?", (wm_id,)
    ).fetchall()]
    result["signal_ids"] = [r["signal_id"] for r in conn.execute(
        "SELECT signal_id FROM wm_signals WHERE world_model_id = ?", (wm_id,)
    ).fetchall()]
    result["evidence_ids"] = [r["evidence_id"] for r in conn.execute(
        "SELECT evidence_id FROM wm_evidence WHERE world_model_id = ?", (wm_id,)
    ).fetchall()]
    result["source_ids"] = [r["source_id"] for r in conn.execute(
        "SELECT source_id FROM wm_sources WHERE world_model_id = ?", (wm_id,)
    ).fetchall()]
    conn.close()
    return result


def list_world_models(*, limit=100, offset=0):
    """List world models ordered by confidence."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM world_models ORDER BY confidence_score DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_world_models(query_text):
    """Search world models by name, description, or narrative."""
    conn = get_connection()
    pattern = f"%{query_text}%"
    rows = conn.execute(
        """SELECT * FROM world_models
           WHERE name LIKE ? OR description LIKE ? OR narrative_synthesis LIKE ?
           ORDER BY confidence_score DESC LIMIT 100""",
        (pattern, pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

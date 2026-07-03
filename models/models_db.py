import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "models.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS models (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS model_hypotheses (
            model_id     TEXT NOT NULL REFERENCES models(id),
            hypothesis_id TEXT NOT NULL,
            PRIMARY KEY(model_id, hypothesis_id)
        );

        CREATE TABLE IF NOT EXISTS model_concepts (
            model_id    TEXT NOT NULL REFERENCES models(id),
            concept_id  TEXT NOT NULL,
            PRIMARY KEY(model_id, concept_id)
        );

        CREATE TABLE IF NOT EXISTS model_signals (
            model_id  TEXT NOT NULL REFERENCES models(id),
            signal_id TEXT NOT NULL,
            PRIMARY KEY(model_id, signal_id)
        );

        CREATE TABLE IF NOT EXISTS model_evidence (
            model_id    TEXT NOT NULL REFERENCES models(id),
            evidence_id TEXT NOT NULL,
            PRIMARY KEY(model_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS competing_models (
            model_a_id TEXT NOT NULL REFERENCES models(id),
            model_b_id TEXT NOT NULL REFERENCES models(id),
            PRIMARY KEY(model_a_id, model_b_id)
        );

        CREATE INDEX IF NOT EXISTS idx_models_confidence ON models(confidence_score);
    """)
    conn.commit()
    conn.close()


def add_model(name, *, description=None, confidence_score=None,
              hypothesis_ids=None, concept_ids=None,
              signal_ids=None, evidence_ids=None):
    """Create a new model. Returns the model id."""
    conn = get_connection()
    model_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO models (id, name, description, confidence_score, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (model_id, name, description, confidence_score, now, now),
    )
    if hypothesis_ids:
        for h_id in hypothesis_ids:
            conn.execute(
                "INSERT INTO model_hypotheses (model_id, hypothesis_id) VALUES (?, ?)",
                (model_id, h_id),
            )
    if concept_ids:
        for c_id in concept_ids:
            conn.execute(
                "INSERT INTO model_concepts (model_id, concept_id) VALUES (?, ?)",
                (model_id, c_id),
            )
    if signal_ids:
        for s_id in signal_ids:
            conn.execute(
                "INSERT INTO model_signals (model_id, signal_id) VALUES (?, ?)",
                (model_id, s_id),
            )
    if evidence_ids:
        for e_id in evidence_ids:
            conn.execute(
                "INSERT INTO model_evidence (model_id, evidence_id) VALUES (?, ?)",
                (model_id, e_id),
            )
    conn.commit()
    conn.close()
    return model_id


def get_model(model_id):
    """Return a single model dict or None."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_model_full(model_id):
    """Return model with all linked hypotheses, concepts, signals, evidence."""
    conn = get_connection()
    model = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    if not model:
        conn.close()
        return None

    result = dict(model)
    result["hypothesis_ids"] = [r["hypothesis_id"] for r in conn.execute(
        "SELECT hypothesis_id FROM model_hypotheses WHERE model_id = ?", (model_id,)
    ).fetchall()]
    result["concept_ids"] = [r["concept_id"] for r in conn.execute(
        "SELECT concept_id FROM model_concepts WHERE model_id = ?", (model_id,)
    ).fetchall()]
    result["signal_ids"] = [r["signal_id"] for r in conn.execute(
        "SELECT signal_id FROM model_signals WHERE model_id = ?", (model_id,)
    ).fetchall()]
    result["evidence_ids"] = [r["evidence_id"] for r in conn.execute(
        "SELECT evidence_id FROM model_evidence WHERE model_id = ?", (model_id,)
    ).fetchall()]
    result["competitors"] = [r["model_b_id"] for r in conn.execute(
        "SELECT model_b_id FROM competing_models WHERE model_a_id = ?", (model_id,)
    ).fetchall()]
    conn.close()
    return result


def set_competing_models(model_a_id, model_b_id):
    """Mark two models as competing explanations."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO competing_models (model_a_id, model_b_id) VALUES (?, ?)",
            (model_a_id, model_b_id),
        )
        conn.execute(
            "INSERT INTO competing_models (model_a_id, model_b_id) VALUES (?, ?)",
            (model_b_id, model_a_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def list_models(*, limit=100, offset=0):
    """List models ordered by confidence."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM models ORDER BY confidence_score DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_models(query_text):
    """Search models by name or description."""
    conn = get_connection()
    pattern = f"%{query_text}%"
    rows = conn.execute(
        "SELECT * FROM models WHERE name LIKE ? OR description LIKE ? ORDER BY confidence_score DESC LIMIT 100",
        (pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

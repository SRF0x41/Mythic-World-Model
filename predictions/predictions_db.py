import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "predictions.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS predictions (
            id TEXT PRIMARY KEY,
            statement TEXT NOT NULL,
            model_id TEXT NOT NULL,
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            expected_timeframe TEXT,
            validation_status TEXT DEFAULT 'pending'
                CHECK(validation_status IN ('pending', 'validated', 'invalidated', 'expired')),
            validated_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions(model_id);
        CREATE INDEX IF NOT EXISTS idx_predictions_status ON predictions(validation_status);
        CREATE INDEX IF NOT EXISTS idx_predictions_confidence ON predictions(confidence_score);
    """)
    conn.commit()
    conn.close()


def add_prediction(statement, model_id, *, confidence_score=None,
                   expected_timeframe=None):
    """Create a new prediction. Returns the prediction id."""
    conn = get_connection()
    pred_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO predictions
           (id, statement, model_id, confidence_score, expected_timeframe,
            validation_status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (pred_id, statement, model_id, confidence_score,
         expected_timeframe, now, now),
    )
    conn.commit()
    conn.close()
    return pred_id


def update_validation(prediction_id, status, *, validated_at=None):
    """Update the validation status of a prediction."""
    conn = get_connection()
    now = validated_at or datetime.now().isoformat()
    conn.execute(
        """UPDATE predictions
           SET validation_status = ?, validated_at = ?, updated_at = ?
           WHERE id = ?""",
        (status, now, now, prediction_id),
    )
    conn.commit()
    conn.close()


def get_prediction(prediction_id):
    """Return a single prediction dict or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM predictions WHERE id = ?", (prediction_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_predictions(*, model_id=None, validation_status=None,
                     limit=100, offset=0):
    """List predictions, optionally filtered."""
    conn = get_connection()
    query = "SELECT * FROM predictions WHERE 1=1"
    params = []
    if model_id:
        query += " AND model_id = ?"
        params.append(model_id)
    if validation_status:
        query += " AND validation_status = ?"
        params.append(validation_status)
    query += " ORDER BY confidence_score DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_predictions(query_text):
    """Search predictions by statement text."""
    conn = get_connection()
    pattern = f"%{query_text}%"
    rows = conn.execute(
        "SELECT * FROM predictions WHERE statement LIKE ? ORDER BY confidence_score DESC LIMIT 100",
        (pattern,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

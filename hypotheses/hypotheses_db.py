import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "hypotheses.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hypotheses (
            id TEXT PRIMARY KEY,
            claim TEXT NOT NULL,
            source_concept_id TEXT NOT NULL REFERENCES concepts_ref(id),
            target_concept_id TEXT NOT NULL REFERENCES concepts_ref(id),
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Mirror table so hypotheses can reference concepts without cross-DB FK
        CREATE TABLE IF NOT EXISTS concepts_ref (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS hypothesis_signals (
            hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
            signal_id TEXT NOT NULL,
            PRIMARY KEY(hypothesis_id, signal_id)
        );

        CREATE TABLE IF NOT EXISTS hypothesis_evidence (
            hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
            evidence_id TEXT NOT NULL,
            PRIMARY KEY(hypothesis_id, evidence_id)
        );

        CREATE TABLE IF NOT EXISTS competing_hypotheses (
            hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
            competitor_id TEXT NOT NULL REFERENCES hypotheses(id),
            PRIMARY KEY(hypothesis_id, competitor_id)
        );

        CREATE INDEX IF NOT EXISTS idx_hypotheses_source ON hypotheses(source_concept_id);
        CREATE INDEX IF NOT EXISTS idx_hypotheses_target ON hypotheses(target_concept_id);
        CREATE INDEX IF NOT EXISTS idx_hypotheses_confidence ON hypotheses(confidence_score);
    """)
    conn.commit()
    conn.close()


def sync_concepts(concept_ids, names):
    """Upsert concept references so hypotheses can point to them."""
    conn = get_connection()
    for cid, name in zip(concept_ids, names):
        conn.execute(
            "INSERT OR IGNORE INTO concepts_ref (id, name) VALUES (?, ?)",
            (cid, name),
        )
    conn.commit()
    conn.close()


def add_hypothesis(claim, source_concept_id, target_concept_id,
                   *, source_concept_name=None, target_concept_name=None,
                   confidence_score=None, signal_ids=None, evidence_ids=None):
    """Create a new hypothesis. Returns the hypothesis id."""
    conn = get_connection()
    hyp_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    # ensure concepts exist in ref table
    if source_concept_name:
        conn.execute(
            "INSERT OR IGNORE INTO concepts_ref (id, name) VALUES (?, ?)",
            (source_concept_id, source_concept_name),
        )
    if target_concept_name:
        conn.execute(
            "INSERT OR IGNORE INTO concepts_ref (id, name) VALUES (?, ?)",
            (target_concept_id, target_concept_name),
        )

    conn.execute(
        """INSERT INTO hypotheses
           (id, claim, source_concept_id, target_concept_id, confidence_score, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (hyp_id, claim, source_concept_id, target_concept_id,
         confidence_score, now, now),
    )
    if signal_ids:
        for sig_id in signal_ids:
            conn.execute(
                "INSERT INTO hypothesis_signals (hypothesis_id, signal_id) VALUES (?, ?)",
                (hyp_id, sig_id),
            )
    if evidence_ids:
        for ev_id in evidence_ids:
            conn.execute(
                "INSERT INTO hypothesis_evidence (hypothesis_id, evidence_id) VALUES (?, ?)",
                (hyp_id, ev_id),
            )
    conn.commit()
    conn.close()
    return hyp_id


def get_hypothesis(hypothesis_id):
    """Return a single hypothesis dict or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM hypotheses WHERE id = ?", (hypothesis_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_hypothesis_full(hypothesis_id):
    """Return hypothesis with all supporting data."""
    conn = get_connection()
    hyp = conn.execute("SELECT * FROM hypotheses WHERE id = ?", (hypothesis_id,)).fetchone()
    if not hyp:
        conn.close()
        return None

    result = dict(hyp)
    result["signal_ids"] = [r["signal_id"] for r in conn.execute(
        "SELECT signal_id FROM hypothesis_signals WHERE hypothesis_id = ?",
        (hypothesis_id,),
    ).fetchall()]
    result["evidence_ids"] = [r["evidence_id"] for r in conn.execute(
        "SELECT evidence_id FROM hypothesis_evidence WHERE hypothesis_id = ?",
        (hypothesis_id,),
    ).fetchall()]
    result["competitors"] = [dict(r) for r in conn.execute(
        "SELECT h.* FROM competing_hypotheses ch "
        "JOIN hypotheses h ON h.id = ch.competitor_id "
        "WHERE ch.hypothesis_id = ?",
        (hypothesis_id,),
    ).fetchall()]
    conn.close()
    return result


def set_competing(hypothesis_id, competitor_id):
    """Mark two hypotheses as competing explanations."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO competing_hypotheses (hypothesis_id, competitor_id) VALUES (?, ?)",
            (hypothesis_id, competitor_id),
        )
        # bidirectional
        conn.execute(
            "INSERT INTO competing_hypotheses (hypothesis_id, competitor_id) VALUES (?, ?)",
            (competitor_id, hypothesis_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def list_hypotheses(*, source_concept_id=None, target_concept_id=None,
                    limit=100, offset=0):
    """List hypotheses, optionally filtered by concept involvement."""
    conn = get_connection()
    query = "SELECT * FROM hypotheses WHERE 1=1"
    params = []
    if source_concept_id:
        query += " AND source_concept_id = ?"
        params.append(source_concept_id)
    if target_concept_id:
        query += " AND target_concept_id = ?"
        params.append(target_concept_id)
    query += " ORDER BY confidence_score DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_hypotheses(query_text):
    """Search hypotheses by claim text."""
    conn = get_connection()
    pattern = f"%{query_text}%"
    rows = conn.execute(
        "SELECT * FROM hypotheses WHERE claim LIKE ? ORDER BY confidence_score DESC LIMIT 100",
        (pattern,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

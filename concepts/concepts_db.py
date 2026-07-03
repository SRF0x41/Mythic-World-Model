import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "concepts.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Hierarchical: parent/child concept relationships
        CREATE TABLE IF NOT EXISTS concept_hierarchy (
            parent_id TEXT NOT NULL REFERENCES concepts(id),
            child_id  TEXT NOT NULL REFERENCES concepts(id),
            PRIMARY KEY(parent_id, child_id)
        );

        -- Semantic: influences, opposes, related_to, contributes_to, etc.
        CREATE TABLE IF NOT EXISTS concept_relations (
            source_id   TEXT NOT NULL REFERENCES concepts(id),
            target_id   TEXT NOT NULL REFERENCES concepts(id),
            relation_type TEXT NOT NULL,
            PRIMARY KEY(source_id, target_id, relation_type)
        );

        -- Link concepts to signals that informed them
        CREATE TABLE IF NOT EXISTS concept_signals (
            concept_id TEXT NOT NULL REFERENCES concepts(id),
            signal_id  TEXT NOT NULL,
            PRIMARY KEY(concept_id, signal_id)
        );

        -- Link concepts to evidence
        CREATE TABLE IF NOT EXISTS concept_evidence (
            concept_id TEXT NOT NULL REFERENCES concepts(id),
            evidence_id TEXT NOT NULL,
            PRIMARY KEY(concept_id, evidence_id)
        );

        CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name);
    """)
    conn.commit()
    conn.close()


def add_concept(name, *, description=None, confidence_score=None,
                signal_ids=None, evidence_ids=None):
    """Create a new concept. Returns the concept id."""
    conn = get_connection()
    concept_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO concepts (id, name, description, confidence_score, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (concept_id, name, description, confidence_score, now, now),
    )
    if signal_ids:
        for sig_id in signal_ids:
            conn.execute(
                "INSERT INTO concept_signals (concept_id, signal_id) VALUES (?, ?)",
                (concept_id, sig_id),
            )
    if evidence_ids:
        for ev_id in evidence_ids:
            conn.execute(
                "INSERT INTO concept_evidence (concept_id, evidence_id) VALUES (?, ?)",
                (concept_id, ev_id),
            )
    conn.commit()
    conn.close()
    return concept_id


def get_concept(concept_id):
    """Return a single concept dict or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM concepts WHERE id = ?", (concept_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_concept_by_name(name):
    """Look up a concept by its unique name."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM concepts WHERE name = ?", (name,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_concept_full(concept_id):
    """Return concept with all relationships, signals, and evidence."""
    conn = get_connection()
    concept = conn.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,)).fetchone()
    if not concept:
        conn.close()
        return None

    result = dict(concept)

    # hierarchy
    parents = [dict(r) for r in conn.execute(
        "SELECT c.* FROM concepts c JOIN concept_hierarchy ch ON c.id = ch.parent_id WHERE ch.child_id = ?",
        (concept_id,),
    ).fetchall()]
    children = [dict(r) for r in conn.execute(
        "SELECT c.* FROM concepts c JOIN concept_hierarchy ch ON c.id = ch.child_id WHERE ch.parent_id = ?",
        (concept_id,),
    ).fetchall()]
    result["parents"] = parents
    result["children"] = children

    # semantic relations
    result["relations"] = [dict(r) for r in conn.execute(
        "SELECT cr.*, c.name as target_name FROM concept_relations cr "
        "JOIN concepts c ON c.id = cr.target_id WHERE cr.source_id = ?",
        (concept_id,),
    ).fetchall()]
    result["incoming_relations"] = [dict(r) for r in conn.execute(
        "SELECT cr.*, c.name as source_name FROM concept_relations cr "
        "JOIN concepts c ON c.id = cr.source_id WHERE cr.target_id = ?",
        (concept_id,),
    ).fetchall()]

    # signals and evidence
    result["signal_ids"] = [r["signal_id"] for r in conn.execute(
        "SELECT signal_id FROM concept_signals WHERE concept_id = ?", (concept_id,)
    ).fetchall()]
    result["evidence_ids"] = [r["evidence_id"] for r in conn.execute(
        "SELECT evidence_id FROM concept_evidence WHERE concept_id = ?", (concept_id,)
    ).fetchall()]

    conn.close()
    return result


def set_parent_child(parent_id, child_id):
    """Make one concept a parent of another."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO concept_hierarchy (parent_id, child_id) VALUES (?, ?)",
            (parent_id, child_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.execute(
        "UPDATE concepts SET updated_at = datetime('now') WHERE id IN (?, ?)",
        (parent_id, child_id),
    )
    conn.commit()
    conn.close()


def add_relation(source_id, target_id, relation_type):
    """Add a semantic relationship between two concepts."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO concept_relations (source_id, target_id, relation_type) VALUES (?, ?, ?)",
            (source_id, target_id, relation_type),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.execute(
        "UPDATE concepts SET updated_at = datetime('now') WHERE id IN (?, ?)",
        (source_id, target_id),
    )
    conn.commit()
    conn.close()


def list_concepts(*, limit=100, offset=0):
    """List concepts."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM concepts ORDER BY name LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_concepts(query_text):
    """Search concepts by name or description."""
    conn = get_connection()
    pattern = f"%{query_text}%"
    rows = conn.execute(
        "SELECT * FROM concepts WHERE name LIKE ? OR description LIKE ? ORDER BY name LIMIT 100",
        (pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

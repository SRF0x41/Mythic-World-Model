"""
Unified database for the Mythic World Model.

All 8 layers + ontology live in a single SQLite file.
Each layer's tables keep their original names; no prefixing needed
since all table names are already unique across layers.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "mythic_world_model.db"


def get_connection():
    """Get a connection to the unified database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# --------------------------------------------------------------------------- #
# Schema definitions per layer — each returns the SQL DDL string
# --------------------------------------------------------------------------- #

def _sources_schema():
    return """
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
    """


def _evidence_schema():
    return """
        CREATE TABLE IF NOT EXISTS evidence (
            id TEXT PRIMARY KEY,
            claim TEXT NOT NULL,
            quotation TEXT,
            source_id TEXT NOT NULL REFERENCES sources(id),
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
    """


def _signals_schema():
    return """
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
            evidence_id TEXT NOT NULL REFERENCES evidence(id),
            PRIMARY KEY(signal_id, evidence_id)
        );
        CREATE INDEX IF NOT EXISTS idx_signals_confidence ON signals(confidence_score);
        CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
    """


def _concepts_schema():
    return """
        CREATE TABLE IF NOT EXISTS concepts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS concept_hierarchy (
            parent_id TEXT NOT NULL REFERENCES concepts(id),
            child_id  TEXT NOT NULL REFERENCES concepts(id),
            PRIMARY KEY(parent_id, child_id)
        );
        CREATE TABLE IF NOT EXISTS concept_relations (
            source_id   TEXT NOT NULL REFERENCES concepts(id),
            target_id   TEXT NOT NULL REFERENCES concepts(id),
            relation_type TEXT NOT NULL,
            PRIMARY KEY(source_id, target_id, relation_type)
        );
        CREATE TABLE IF NOT EXISTS concept_signals (
            concept_id TEXT NOT NULL REFERENCES concepts(id),
            signal_id  TEXT NOT NULL REFERENCES signals(id),
            PRIMARY KEY(concept_id, signal_id)
        );
        CREATE TABLE IF NOT EXISTS concept_evidence (
            concept_id TEXT NOT NULL REFERENCES concepts(id),
            evidence_id TEXT NOT NULL REFERENCES evidence(id),
            PRIMARY KEY(concept_id, evidence_id)
        );
        CREATE INDEX IF NOT EXISTS idx_concepts_name ON concepts(name);
    """


def _hypotheses_schema():
    return """
        CREATE TABLE IF NOT EXISTS hypotheses (
            id TEXT PRIMARY KEY,
            claim TEXT NOT NULL,
            source_concept_id TEXT NOT NULL REFERENCES concepts(id),
            target_concept_id TEXT NOT NULL REFERENCES concepts(id),
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS hypothesis_signals (
            hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
            signal_id TEXT NOT NULL REFERENCES signals(id),
            PRIMARY KEY(hypothesis_id, signal_id)
        );
        CREATE TABLE IF NOT EXISTS hypothesis_evidence (
            hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
            evidence_id TEXT NOT NULL REFERENCES evidence(id),
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
    """


def _models_schema():
    return """
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
            hypothesis_id TEXT NOT NULL REFERENCES hypotheses(id),
            PRIMARY KEY(model_id, hypothesis_id)
        );
        CREATE TABLE IF NOT EXISTS model_concepts (
            model_id    TEXT NOT NULL REFERENCES models(id),
            concept_id  TEXT NOT NULL REFERENCES concepts(id),
            PRIMARY KEY(model_id, concept_id)
        );
        CREATE TABLE IF NOT EXISTS model_signals (
            model_id  TEXT NOT NULL REFERENCES models(id),
            signal_id TEXT NOT NULL REFERENCES signals(id),
            PRIMARY KEY(model_id, signal_id)
        );
        CREATE TABLE IF NOT EXISTS model_evidence (
            model_id    TEXT NOT NULL REFERENCES models(id),
            evidence_id TEXT NOT NULL REFERENCES evidence(id),
            PRIMARY KEY(model_id, evidence_id)
        );
        CREATE TABLE IF NOT EXISTS competing_models (
            model_a_id TEXT NOT NULL REFERENCES models(id),
            model_b_id TEXT NOT NULL REFERENCES models(id),
            PRIMARY KEY(model_a_id, model_b_id)
        );
        CREATE INDEX IF NOT EXISTS idx_models_confidence ON models(confidence_score);
    """


def _predictions_schema():
    return """
        CREATE TABLE IF NOT EXISTS predictions (
            id TEXT PRIMARY KEY,
            statement TEXT NOT NULL,
            model_id TEXT NOT NULL REFERENCES models(id),
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
    """


def _world_models_schema():
    return """
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
            model_id       TEXT NOT NULL REFERENCES models(id),
            PRIMARY KEY(world_model_id, model_id)
        );
        CREATE TABLE IF NOT EXISTS wm_hypotheses (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            hypothesis_id  TEXT NOT NULL REFERENCES hypotheses(id),
            PRIMARY KEY(world_model_id, hypothesis_id)
        );
        CREATE TABLE IF NOT EXISTS wm_concepts (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            concept_id     TEXT NOT NULL REFERENCES concepts(id),
            PRIMARY KEY(world_model_id, concept_id)
        );
        CREATE TABLE IF NOT EXISTS wm_signals (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            signal_id      TEXT NOT NULL REFERENCES signals(id),
            PRIMARY KEY(world_model_id, signal_id)
        );
        CREATE TABLE IF NOT EXISTS wm_evidence (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            evidence_id    TEXT NOT NULL REFERENCES evidence(id),
            PRIMARY KEY(world_model_id, evidence_id)
        );
        CREATE TABLE IF NOT EXISTS wm_sources (
            world_model_id TEXT NOT NULL REFERENCES world_models(id),
            source_id      TEXT NOT NULL REFERENCES sources(id),
            PRIMARY KEY(world_model_id, source_id)
        );
        CREATE INDEX IF NOT EXISTS idx_wm_confidence ON world_models(confidence_score);
    """


def _ontology_schema():
    return """
        CREATE TABLE IF NOT EXISTS ontology_nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            node_type TEXT NOT NULL DEFAULT 'concept'
                CHECK(node_type IN ('concept', 'signal', 'hypothesis', 'model', 'world_model')),
            confidence_score REAL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS ontology_edges (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES ontology_nodes(id),
            target_id TEXT NOT NULL REFERENCES ontology_nodes(id),
            edge_type TEXT NOT NULL,
            strength REAL CHECK(strength BETWEEN 0.0 AND 1.0),
            description TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source_id, target_id, edge_type)
        );
        CREATE TABLE IF NOT EXISTS ontology_provenance (
            id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL REFERENCES ontology_nodes(id),
            supports_id TEXT NOT NULL,
            supports_type TEXT NOT NULL
                CHECK(supports_type IN ('evidence', 'signal', 'source', 'hypothesis', 'model', 'world_model')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(node_id, supports_id, supports_type)
        );
        CREATE TABLE IF NOT EXISTS ontology_observations (
            id TEXT PRIMARY KEY,
            target_id TEXT NOT NULL REFERENCES ontology_nodes(id),
            observation_type TEXT NOT NULL
                CHECK(observation_type IN ('note', 'insight', 'definition_update', 'correction')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ontology_edges_source ON ontology_edges(source_id);
        CREATE INDEX IF NOT EXISTS idx_ontology_edges_target ON ontology_edges(target_id);
        CREATE INDEX IF NOT EXISTS idx_ontology_edges_type ON ontology_edges(edge_type);
        CREATE INDEX IF NOT EXISTS idx_ontology_nodes_type ON ontology_nodes(node_type);
        CREATE INDEX IF NOT EXISTS idx_ontology_provenance_node ON ontology_provenance(node_id);
        CREATE INDEX IF NOT EXISTS idx_ontology_provenance_supports ON ontology_provenance(supports_id);
        CREATE INDEX IF NOT EXISTS idx_ontology_observations_target ON ontology_observations(target_id);
    """


# Map of layer names to their schema functions
_LAYER_SCHEMAS = {
    "sources": _sources_schema,
    "evidence": _evidence_schema,
    "signals": _signals_schema,
    "concepts": _concepts_schema,
    "hypotheses": _hypotheses_schema,
    "models": _models_schema,
    "predictions": _predictions_schema,
    "world_models": _world_models_schema,
    "ontology": _ontology_schema,
}


def init_db(layers=None):
    """
    Initialize the database schema.

    Args:
        layers: Optional list of layer names to initialize.
                If None, initializes all layers.
    Returns:
        List of initialized layer names.
    """
    if layers is None:
        layers = list(_LAYER_SCHEMAS.keys())

    conn = get_connection()
    initialized = []
    for layer_name in layers:
        if layer_name in _LAYER_SCHEMAS:
            conn.executescript(_LAYER_SCHEMAS[layer_name]())
            initialized.append(layer_name)
    conn.commit()
    conn.close()
    return initialized

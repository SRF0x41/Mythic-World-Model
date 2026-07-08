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
    """
    Layer 1 — Sources.

    Immutable records of raw information. Everything begins here.
    A Source is never modified or deleted—only appended.

    Columns:
        id                  Unique UUID for this source record.
        url                 Original URL or link to the source material.
        origin              Publication, platform, or venue where the source appeared.
        author              Named author or contributor of the source.
        published_at        Date/time the source was originally published (ISO 8601).
        source_type         Category of source (article, paper, podcast, transcript, etc.).
        credibility_score   Float 0.0–1.0 indicating source reliability as evidence.
        summary             AI-generated concise summary of the source content.
        raw_text            Full raw text of the ingested source, preserved verbatim.
        ingested_at         Timestamp when this source was first ingested into the system.
        content_hash        SHA-256 hash of raw_text (first 16 hex chars) for deduplication.
    """
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
            content_hash TEXT,
            UNIQUE(url, ingested_at),
            UNIQUE(content_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
        CREATE INDEX IF NOT EXISTS idx_sources_published ON sources(published_at);
        CREATE INDEX IF NOT EXISTS idx_sources_ingested ON sources(ingested_at);
        CREATE INDEX IF NOT EXISTS idx_sources_hash ON sources(content_hash);
    """
    
def init_sources_schema():
    """
    Initialize only the Sources layer schema.

    Returns:
        bool: True if initialization completed successfully.
    """
    conn = get_connection()
    try:
        conn.executescript(_sources_schema())
        conn.commit()
        return True
    finally:
        conn.close()


def _evidence_schema():
    """
    Layer 2 — Evidence.

    Sources are decomposed into individual claims. One source may produce
    many independent pieces of evidence. Evidence is the atomic unit of reasoning.

    Columns (evidence):
        id                  Unique UUID for this evidence record.
        claim               A single extractable claim supported by the source.
        quotation           Direct quote or extracted passage that backs the claim.
        source_id           Reference back to the Source this evidence was drawn from.
        confidence_score    Float 0.0–1.0 indicating how well the quotation supports the claim.
        created_at          Timestamp when this evidence record was created.

    Columns (evidence_relations):
        id                  Unique UUID for this relation.
        evidence_a_id       First evidence object in the relationship.
        evidence_b_id       Second evidence object in the relationship.
        relation_type       Nature of the link (supports, contradicts, relates_to).
        created_at          Timestamp when this relation was created.
    """
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
    """
    Layer 3 — Signals.

    Evidence accumulates into Signals — recurring observations across many
    independent sources. Signals identify patterns but intentionally avoid explaining them.

    Columns (signals):
        id                  Unique UUID for this signal.
        claim               The observed pattern or recurring phenomenon.
        confidence_score    Float 0.0–1.0 indicating strength of the signal.
        frequency           Count of independent sources that exhibit this pattern.
        time_distribution   ISO date range or distribution showing when the signal appears.
        created_at          Timestamp when this signal was first created.
        updated_at          Timestamp of the last modification to this signal.

    Columns (signal_evidence):
        signal_id           Reference to the Signal this evidence supports.
        evidence_id         Reference to the Evidence supporting this signal.
    """
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
    """
    Layer 4 — Concepts.

    Stable ontological objects that change slowly over time. Concepts form
    the vocabulary from which hypotheses and models are constructed.

    Columns (concepts):
        id                  Unique UUID for this concept.
        name                Human-readable name (e.g., "Trust", "Religion", "Community").
        description         Definition of what this concept represents in the ontology.
        confidence_score    Float 0.0–1.0 indicating how well-established the concept is.
        created_at          Timestamp when this concept was first created.
        updated_at          Timestamp of the last modification to this concept.

    Columns (concept_hierarchy):
        parent_id           Parent concept in the hierarchy (e.g., "Identity").
        child_id            Child concept (e.g., "Shared Identity" under "Identity").

    Columns (concept_relations):
        source_id           Source concept in the relationship.
        target_id           Target concept in the relationship.
        relation_type       Nature of the link (influences, opposes, related_to).

    Columns (concept_signals):
        concept_id          Concept this signal is associated with.
        signal_id           Signal that supports or illustrates this concept.

    Columns (concept_evidence):
        concept_id          Concept this evidence relates to.
        evidence_id         Evidence that directly supports this concept.
    """
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
    """
    Layer 5 — Hypotheses.

    Introduce causal reasoning by connecting Concepts through directional
    relationships. Multiple competing hypotheses may coexist until accumulating
    evidence increases confidence in one over another.

    Columns (hypotheses):
        id                  Unique UUID for this hypothesis.
        claim               Causal statement (e.g., "Declining Religion increases Search for Secular Rituals").
        source_concept_id   The originating concept in the causal relationship.
        target_concept_id   The concept being influenced or affected.
        confidence_score    Float 0.0–1.0 indicating how well-supported the hypothesis is.
        created_at          Timestamp when this hypothesis was first created.
        updated_at          Timestamp of the last modification.

    Columns (hypothesis_signals):
        hypothesis_id       Hypothesis this signal supports.
        signal_id           Signal that provides backing for this hypothesis.

    Columns (hypothesis_evidence):
        hypothesis_id       Hypothesis this evidence directly supports.
        evidence_id         Evidence object that backs this hypothesis.

    Columns (competing_hypotheses):
        hypothesis_id       The primary hypothesis.
        competitor_id       Another hypothesis that offers a competing explanation.
    """
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
    """
    Layer 6 — Models.

    Networks of interconnected Hypotheses that explain systems rather than
    isolated relationships. Models compete based on explanatory power, not popularity.

    Columns (models):
        id                  Unique UUID for this model.
        name                Human-readable name of the model.
        description         Explanation of what system or phenomenon the model describes.
        confidence_score    Float 0.0–1.0 based on accumulated supporting evidence.
        created_at          Timestamp when this model was first created.
        updated_at          Timestamp of the last modification.

    Columns (model_hypotheses):
        model_id            Model that contains this hypothesis.
        hypothesis_id       Hypothesis included in this model's network.

    Columns (model_concepts):
        model_id            Model that involves this concept.
        concept_id          Concept referenced by this model.

    Columns (model_signals):
        model_id            Model this signal supports.
        signal_id           Signal that backs this model.

    Columns (model_evidence):
        model_id            Model this evidence supports.
        evidence_id         Evidence that directly backs this model.

    Columns (competing_models):
        model_a_id          First competing model.
        model_b_id          Second competing model offering an alternative explanation.
    """
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
    """
    Layer 7 — Predictions.

    Falsifiable expectations generated from Models. Predictions provide a
    mechanism for continuously evaluating model quality over time.

    Columns (predictions):
        id                  Unique UUID for this prediction.
        statement           The prediction statement (e.g., "AI companionship will become socially normalized").
        model_id            The parent Model from which this prediction was derived.
        confidence_score    Float 0.0–1.0 indicating how confident the model is in this prediction.
        expected_timeframe  ISO date range by which the prediction should materialize.
        validation_status   One of: pending, validated, invalidated, expired.
        validated_at        Timestamp when the prediction was last validated/invalidated (ISO 8601).
        created_at          Timestamp when this prediction was first created.
        updated_at          Timestamp of the last modification.
    """
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
    """
    Layer 8 — World Models.

    Highest level of abstraction. Synthesizes the strongest Models into a
    coherent explanation of the current historical moment. Never considered
    complete — evolves as new information enters the system.

    Columns (world_models):
        id                  Unique UUID for this world model.
        name                Human-readable name of the world model.
        description         High-level overview of the era or historical moment it explains.
        narrative_synthesis  Coherent narrative that ties all supporting models together.
        confidence_score    Float 0.0–1.0 based on cumulative evidence across all layers.
        created_at          Timestamp when this world model was first created.
        updated_at          Timestamp of the last modification.

    Columns (wm_models):
        world_model_id      World Model this model belongs to.
        model_id            Supporting Model included in this world model.

    Columns (wm_hypotheses):
        world_model_id      World Model this hypothesis supports.
        hypothesis_id       Hypothesis included in this world model's reasoning chain.

    Columns (wm_concepts):
        world_model_id      World Model this concept is part of.
        concept_id          Concept referenced by this world model.

    Columns (wm_signals):
        world_model_id      World Model this signal supports.
        signal_id           Signal backing this world model.

    Columns (wm_evidence):
        world_model_id      World Model this evidence supports.
        evidence_id         Evidence directly backing this world model.

    Columns (wm_sources):
        world_model_id      World Model this source contributes to.
        source_id           Original Source in the provenance chain of this world model.
    """
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
    """
    Ontology — Graph Store.

    Central cross-layer graph that mirrors the concept network and provides
    BFS pathfinding, subgraph extraction, cross-layer provenance tracing,
    and graph statistics. Transforms the database from an archive into a
    knowledge graph capable of supporting genuine world modeling.

    Columns (ontology_nodes):
        id                  Unique UUID for this node.
        name                Human-readable name of the concept/entity.
        description         Definition of what this node represents in the graph.
        node_type           Category: concept, signal, hypothesis, model, or world_model.
        confidence_score    Float 0.0–1.0 indicating how well-established this node is.
        created_at          Timestamp when this node was first created.
        updated_at          Timestamp of the last modification.

    Columns (ontology_edges):
        id                  Unique UUID for this edge.
        source_id           Originating node in the relationship.
        target_id           Destination node in the relationship.
        edge_type           Nature of the link (influences, opposes, related_to, contributes_to).
        strength            Float 0.0–1.0 indicating the weight of this relationship.
        description         Human-readable explanation of why this edge exists.
        created_at          Timestamp when this edge was created.

    Columns (ontology_provenance):
        id                  Unique UUID for this provenance record.
        node_id             The ontology node being traced.
        supports_id         The ID of the supporting object in its original layer.
        supports_type       Layer type of the supporting object (evidence, signal, source, etc.).

    Columns (ontology_observations):
        id                  Unique UUID for this observation.
        target_id           The ontology node this observation annotates.
        observation_type    Category: note, insight, definition_update, correction.
        content             The observation text, preserved as an immutable record.
        created_at          Timestamp when this observation was made.
    """
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

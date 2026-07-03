# Layer 4 — Concepts

Signals are distilled into **Concepts**. Concepts are stable ontological objects that change slowly over time.

### Purpose

Represent the enduring structures beneath observations. Concepts form the ontology graph—the vocabulary from which hypotheses and models are constructed. They are reusable across thousands of different analyses.

### Examples

Trust, Religion, Community, Identity, Institutions, Technology, Ritual, Individualism, Economic Security

### Question Answered

> What enduring things are we observing?

### Schema

**`concepts`** — `id`, `name` (unique), `description`, `confidence_score`, `created_at`, `updated_at`.

**`concept_hierarchy`** — parent/child relationships (is-a, subcategory-of).

**`concept_relations`** — semantic relationships (influences, opposes, related_to, contributes_to).

**`concept_signals`** / **`concept_evidence`** — join tables linking concepts back to supporting signals and evidence.

### API

- `init_db()` — create tables
- `add_concept(name, description, signal_ids, evidence_ids)` — create a concept
- `get_concept(id)` / `get_concept_by_name(name)` / `get_concept_full(id)` — look up with all relationships
- `set_parent_child(parent, child)` — add a hierarchical relationship
- `add_relation(source, target, type)` — add a semantic relationship
- `list_concepts()` / `search_concepts(query)` — browse and search

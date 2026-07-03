# Layer 5 — Hypotheses

Hypotheses introduce **causal reasoning**. They connect concepts together through directional relationships.

### Purpose

Explain how and why concepts influence one another. Multiple hypotheses may coexist simultaneously—including competing explanations—until accumulating evidence increases confidence in one over another.

### Examples

- Declining Religion increases Search for Secular Rituals
- Institutional Distrust reduces Civic Participation
- Social Media increases Identity Performance
- Economic Insecurity amplifies Political Polarization

### Question Answered

> How do these concepts influence one another?

### Schema

**`hypotheses`** — `id`, `claim`, `source_concept_id`, `target_concept_id`, `confidence_score`, `created_at`, `updated_at`.

**`concepts_ref`** — local mirror of concept ids/names so hypotheses can reference concepts without cross-database foreign keys.

**`hypothesis_signals`** / **`hypothesis_evidence`** — join tables linking hypotheses to supporting signals and evidence.

**`competing_hypotheses`** — pairs of hypotheses that offer alternative explanations for the same phenomenon.

### API

- `init_db()` — create tables
- `add_hypothesis(claim, source_concept_id, target_concept_id, ...)` — create a hypothesis
- `get_hypothesis(id)` / `get_hypothesis_full(id)` — look up with all supporting data
- `set_competing(a, b)` — mark two hypotheses as competing
- `list_hypotheses(source_concept_id, target_concept_id)` — browse, filtered by concept involvement
- `search_hypotheses(query)` — search by claim text

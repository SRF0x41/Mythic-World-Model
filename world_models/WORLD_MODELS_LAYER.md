# Layer 8 — World Models

World Models represent the **highest level of abstraction**. A World Model synthesizes the strongest models into a coherent explanation of the current historical moment.

### Purpose

Answer the big questions:

- What kind of era are we living through?
- Why are these cultural shifts occurring?
- Which underlying forces appear to be driving them?
- How do seemingly unrelated events connect?

A World Model is never complete. As new information enters the system, every layer may evolve, producing a continuously improving understanding.

### Question Answered

> What is the coherent story that ties everything together?

### Schema

**`world_models`** — `id`, `name`, `description`, `narrative_synthesis`, `confidence_score`, `created_at`, `updated_at`.

**`wm_models`** / **`wm_hypotheses`** / **`wm_concepts`** / **`wm_signals`** / **`wm_evidence`** / **`wm_sources`** — join tables linking the world model to every layer beneath it, ensuring full provenance from narrative back to original source.

### API

- `init_db()` — create tables
- `add_world_model(name, model_ids, hypothesis_ids, ...)` — create a world model
- `get_world_model(id)` / `get_world_model_full(id)` — look up with all linked objects
- `list_world_models()` — browse all world models
- `search_world_models(query)` — search by name, description, or narrative

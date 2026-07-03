# Layer 6 — Models

Models are **networks of interconnected hypotheses**. Rather than explaining isolated relationships, models explain systems.

### Purpose

Group hypotheses into coherent explanations of complex phenomena. Models compete based on explanatory power, not popularity. Confidence increases as additional evidence supports the same network of relationships.

### Example

```
Economic Insecurity  →  Institutional Distrust  →  Loss of Shared Identity
                                                        ↓
                                          Search for Meaning  →  Rise of Alternative Communities
```

### Question Answered

> What system best explains the observed patterns?

### Schema

**`models`** — `id`, `name`, `description`, `confidence_score`, `created_at`, `updated_at`.

**`model_hypotheses`** / **`model_concepts`** / **`model_signals`** / **`model_evidence`** — join tables linking a model to everything it depends on.

**`competing_models`** — pairs of models that offer alternative explanations for the same phenomenon.

### API

- `init_db()` — create tables
- `add_model(name, hypothesis_ids, concept_ids, ...)` — create a model
- `get_model(id)` / `get_model_full(id)` — look up with all linked objects
- `set_competing_models(a, b)` — mark two models as competing
- `list_models()` / `search_models(query)` — browse and search

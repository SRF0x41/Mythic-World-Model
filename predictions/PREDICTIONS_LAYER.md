# Layer 7 — Predictions

Predictions extend models into the future. They are **falsifiable expectations** generated from a model.

### Purpose

Provide a mechanism for continuously evaluating model quality. If a model is correct, its predictions should materialize. Tracking validation over time reveals which models hold up and which don't.

### Examples

- Interest in secular rituals will continue increasing
- AI companionship will become socially normalized
- Civic organizations will continue declining
- Identity-based communities will become increasingly important

### Question Answered

> If this model is correct, what should happen next?

### Schema

**`predictions`** — `id`, `statement`, `model_id`, `confidence_score`, `expected_timeframe`, `validation_status` (`pending` / `validated` / `invalidated` / `expired`), `validated_at`, `created_at`, `updated_at`.

### API

- `init_db()` — create tables
- `add_prediction(statement, model_id, ...)` — create a prediction
- `update_validation(id, status)` — mark a prediction validated, invalidated, or expired
- `get_prediction(id)` — look up a single prediction
- `list_predictions(model_id, validation_status)` — browse, filtered by model or status
- `search_predictions(query)` — search by statement text

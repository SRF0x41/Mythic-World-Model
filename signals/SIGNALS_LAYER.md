# Layer 3 — Signals

Evidence accumulates into **Signals**. Signals answer one question: *what keeps showing up?*

### Purpose

Identify recurring observations across many independent sources. A signal is a pattern, not an explanation. It says something is happening, not why.

### Examples

- Rising institutional distrust
- Declining religious participation
- AI anxiety
- Increasing loneliness
- Political fragmentation

### Question Answered

> What patterns consistently emerge?

### Schema

**`signals`** — `id`, `claim`, `confidence_score`, `frequency`, `time_distribution`, `created_at`, `updated_at`.

**`signal_evidence`** — join table linking signals to the evidence that supports them. Frequency auto-updates when evidence is added.

### API

- `init_db()` — create tables
- `add_signal(claim, evidence_ids, ...)` — create a signal, returns its id
- `add_evidence_to_signal(signal_id, evidence_id)` — link additional evidence, updates frequency
- `get_signal(id)` / `get_signal_with_evidence(id)` — look up a signal
- `list_signals(min_frequency, ...)` — browse signals
- `search_signals(query)` — search by claim text

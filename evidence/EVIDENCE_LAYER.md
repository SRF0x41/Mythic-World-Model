# Layer 2 — Evidence

Sources are transformed into **Evidence**. Each piece of evidence is a single extractable claim supported by a source.

### Purpose

Break sources down into atomic, reusable units of reasoning. One article may produce many independent pieces of evidence, each linkable to signals, concepts, and hypotheses above it.

### Question Answered

> What does this source actually support?

### Schema

**`evidence`** — `id`, `claim`, `quotation`, `source_id`, `confidence_score`, `created_at`.

**`evidence_relations`** — relationships between evidence objects (e.g., one piece of evidence supports or contradicts another).

### API

- `init_db()` — create tables
- `add_evidence(claim, source_id, ...)` — insert evidence, returns its id
- `get_evidence(id)` — look up a single evidence object
- `list_evidence(source_id, ...)` — browse evidence, optionally by source
- `relate_evidence(a, b, type)` — store a relationship between two evidence objects
- `get_related(id)` — find all evidence linked to a given piece
- `search_evidence(query)` — search by claim text

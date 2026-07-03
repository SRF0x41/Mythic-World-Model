# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Overview

The Mythic World Model is a knowledge graph system built in pure Python + SQLite. It transforms raw information through 8 layers of increasing abstraction, persisting every intermediate object so all reasoning remains inspectable and reusable.

```
Source → Evidence → Signal → Concept → Hypothesis → Model → Prediction → World Model
```

## Architecture

Each layer is a **standalone Python package** with its own SQLite database:

| Directory | Layer | Database |
|-----------|-------|----------|
| `sources/` | 1 — Sources | `sources.db` |
| `evidence/` | 2 — Evidence | `evidence.db` |
| `signals/` | 3 — Signals | `signals.db` |
| `concepts/` | 4 — Concepts | `concepts.db` |
| `hypotheses/` | 5 — Hypotheses | `hypotheses.db` |
| `models/` | 6 — Models | `models.db` |
| `predictions/` | 7 — Predictions | `predictions.db` |
| `world_models/` | 8 — World Models | `world_models.db` |
| `ontology/` | Graph Store | `ontology.db` |

Each package has the same structure:
- `db.py` — schema (`init_db()`) + all CRUD functions
- `__init__.py` — public API re-exports
- `*_LAYER.md` — layer documentation (purpose, schema, API)

The `ontology/` package is the central graph store. It mirrors the concept network and provides BFS pathfinding, subgraph extraction, cross-layer provenance tracing, and graph statistics.

`lm_client/` is an OpenAI-compatible API client (LM Studio) for local LLM inference. Used for AI-generated summaries, evidence extraction, and reasoning.

### Key design rules

- **Zero external dependencies** for the core — only Python stdlib (`sqlite3`, `uuid`, `json`)
- **`requests`** is the only external dependency, used by `lm_client/`
- Each layer stores foreign IDs as plain TEXT strings (no cross-DB foreign key constraints)
- Objects are never modified or deleted — only appended
- All IDs are UUIDs, all timestamps are ISO format
- `init_db()` is idempotent — safe to call before any operation

## Development

- Python 3.11+ required
- No build step — import packages directly
- Databases are created lazily on first `init_db()` call
- `.gitignore` excludes `*.db` files; databases are not committed
- No test suite, linter, or formatter configured yet

## Working on a layer

1. Read the `*_LAYER.md` file for purpose and schema
2. Add/modify functions in `db.py`
3. Export new functions in `__init__.py`
4. Test by importing the package directly in Python

Example:
```python
from sources import init_db, add_source
init_db()
add_source("https://example.com", "article")
```

## Constitution

`mythic_world_model_constitution.md` contains the full system specification including philosophy, ontology design, conceptual workflow, and guiding principles. Reference it when making architectural decisions.

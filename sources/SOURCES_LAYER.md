# Layer 1 — Sources

Everything begins here. A **Source** is an immutable record of raw information.

### Purpose

Capture and persist every piece of input the system consumes. Sources are never modified or deleted—only appended.

### What It Stores

- News articles, academic papers, Reddit discussions, government publications, books, interviews, podcasts, surveys, transcripts
- Unique ID, URL/origin, author, publication date, source type, credibility score, AI-generated summary, raw text

### Question Answered

> What information do we possess?

### Schema

**`sources`** — one row per ingested source. Columns: `id`, `url`, `origin`, `author`, `published_at`, `source_type`, `credibility_score`, `summary`, `raw_text`, `ingested_at`.

### API

- `init_db()` — create tables if they don't exist
- `add_source(url, source_type, ...)` — insert a new source, returns its id
- `get_source(id)` — look up a single source
- `list_sources(source_type, limit, offset)` — browse sources
- `search_sources(query)` — full-text search across summary, raw text, author, origin

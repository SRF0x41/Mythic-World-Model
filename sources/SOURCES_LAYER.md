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

**`sources`** — one row per ingested source. Columns: `id`, `url`, `origin`, `author`, `published_at`, `source_type`, `credibility_score`, `summary`, `raw_text`, `ingested_at`, `content_hash`.

### API

- `init_db()` — create tables if they don't exist
- `add_source(url, source_type, ...)` — insert a new source, returns its id
- `get_source(id)` — look up a single source
- `list_sources(source_type, limit, offset)` — browse sources
- `search_sources(query)` — full-text search across summary, raw text, author, origin

### Source extraction pipeline

`source_extraction.py` provides LLM-assisted utilities for parsing raw text and populating the sources table from the Mind the Wires search results database.

**Verification** — before any extraction work is done, each source is verified:

- `verify_source(source_text)` → `SOURCE` or `NOISE` — classifies whether the text is a genuine information source or noise (verification/CAPTCHA windows, ads, paywalls, login pages, error pages, bot detection). Noise is skipped immediately, avoiding unnecessary LLM calls.

**Extraction functions** — run on verified sources:

- `extract_metadata(source_text)` → `(title, date, author)` — combined extraction (preferred over the three separate calls below)
- `extract_title(source_text)` → title string (standalone)
- `extract_article_date(source_text)` → ISO 8601 date string (standalone)
- `extract_authorship(source_text)` → author name(s) (standalone)
- `generate_credibility_score(source_text)` → float 0.0–1.0
- `generate_source_summary(source_text)` → 3-5 sentence summary

**Pipeline functions**

- `populate_db_from_mtw(log=True)` — iterates all rows from the MTW database, verifies and extracts each source, and inserts it into the sources table. Returns `(processed_count, elapsed_seconds)`.
- `clear_sources()` — deletes all rows from the sources table (testing utility).
- `log_run(time_unit="minute")` — runs the pipeline and writes a timing log to `sources/`.

Each extraction function loads a prompt template from `sources/prompts/`, appends the source text, and sends it to the local LLM via streaming. Prompt templates:

| Prompt | Purpose |
|--------|---------|
| `VERIFY_SOURCE_PROMPT.md` | Classify as `SOURCE` or `NOISE` |
| `EXTRACT_METADATA_PROMPT.md` | Extract title, date, and author in one call |
| `EXTRACT_TITLE_PROMPT.md` | Extract the article title |
| `EXTRACT_DATE_PROMPT.md` | Extract the publication date |
| `EXTRACT_AUTHORSHIP_PROMPT.md` | Extract author name(s) |
| `CREDIBILITY_SCORE_PROMPT.md` | Score credibility 0.0–1.0 |
| `SOURCE_SUMMARY_PROMPT.md` | Generate a factual summary |

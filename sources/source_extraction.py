
"""
Source extraction utilities.

Uses the local LLM to parse structured metadata (title, date, etc.)
from raw source text. Each function loads a prompt template, appends
the source text, and sends it to the LLM via streaming.

IMPORTANT: The source of sources is still Mind the Wires db for now until I develop a source program
"""

from pathlib import Path
from datetime import datetime
import sqlite3
import uuid
import time
import hashlib

# --- Paths ---
SCRIPT_DIR = Path(__file__).parent
PROMPTS_DIR = SCRIPT_DIR / "prompts"

# --- Third-party / custom imports ---

from lm_client.lm_studio_client import LmStudioClient
from lm_client.prompt_builder import PromptBuilder
from database.db import get_connection, init_sources_schema

# --- Database connection ---

# External database containing raw Mind the Wires search results
mtw_db_path = Path("/home/user1/Desktop/Dev/Global-Information-Trend-Assessment/database/search_results.db")
mtw_connection = sqlite3.connect(mtw_db_path)

# Mythic database
mythic_db_conn = get_connection()

# --- Shared LLM client ---

lm_client = LmStudioClient()

# --- LLM-assisted extraction functions ---


def extract_title(source_text):
    """Extract the title from raw source text.

    Sends the source through the EXTRACT_TITLE_PROMPT template.
    Returns the LLM response containing the title string.
    """
    prompt = PromptBuilder()
    prompt.add_from_file(PROMPTS_DIR / 'EXTRACT_TITLE_PROMPT.md')
    prompt.add_text(source_text)

    return lm_client.send_streaming(prompt.get_prompt())


def extract_article_date(source_text):
    """Extract the publication date from raw source text.

    Sends the source through the EXTRACT_DATE_PROMPT template.
    Returns the LLM response containing the date string (ISO 8601).
    """
    prompt = PromptBuilder()
    prompt.add_from_file(PROMPTS_DIR / 'EXTRACT_DATE_PROMPT.md')
    prompt.add_text(source_text)

    return lm_client.send_streaming(prompt.get_prompt())

def generate_credibility_score(source_text):
    """Generate a credibility score (0.0–1.0) for a source based on its content.

    Sends the source through the CREDIBILITY_SCORE_PROMPT template.
    Returns the LLM response containing a single float between 0.0 and 1.0.
    """
    prompt = PromptBuilder()
    prompt.add_from_file(PROMPTS_DIR / 'CREDIBILITY_SCORE_PROMPT.md')
    prompt.add_text(source_text)

    return lm_client.send_streaming(prompt.get_prompt())

def generate_source_summary(source_text):
    """Generate a concise factual summary of the source text.

    Sends the source through the SOURCE_SUMMARY_PROMPT template.
    Returns the LLM response containing a 3-5 sentence summary.
    """
    prompt = PromptBuilder()
    prompt.add_from_file(PROMPTS_DIR / 'SOURCE_SUMMARY_PROMPT.md')
    prompt.add_text(source_text)

    return lm_client.send_streaming(prompt.get_prompt())

def extract_authorship(source_text):
    """Extract the author or authorship information from raw source text.

    Sends the source through the EXTRACT_AUTHORSHIP_PROMPT template.
    Returns the LLM response containing the author name(s) string.
    """
    prompt = PromptBuilder()
    prompt.add_from_file(PROMPTS_DIR / 'EXTRACT_AUTHORSHIP_PROMPT.md')
    prompt.add_text(source_text)

    return lm_client.send_streaming(prompt.get_prompt())


def _source_hash(raw_text: str) -> str:
    """Compute a short SHA-256 hash of raw text for deduplication.

    Returns the first 16 hex characters — sufficient for collision
    avoidance while keeping the DB column small.
    """
    return hashlib.sha256(raw_text.encode()).hexdigest()[:16]


def extract_metadata(source_text) -> tuple[str, str, str]:
    """Extract title, date, and author in a single LLM call.

    Returns a tuple of (title, date, author).
    Each field falls back to 'UNKNOWN' if not found.
    """
    prompt = PromptBuilder()
    prompt.add_from_file(PROMPTS_DIR / 'EXTRACT_METADATA_PROMPT.md')
    prompt.add_text(source_text)

    response = lm_client.send_streaming(prompt.get_prompt())

    title = 'UNKNOWN'
    date = 'UNKNOWN'
    author = 'UNKNOWN'

    for line in response.split('\n'):
        line = line.strip()
        if line.upper().startswith('TITLE:'):
            title = line[len('TITLE:'):].strip() or 'UNKNOWN'
        elif line.upper().startswith('DATE:'):
            date = line[len('DATE:'):].strip() or 'UNKNOWN'
        elif line.upper().startswith('AUTHOR:'):
            author = line[len('AUTHOR:'):].strip() or 'UNKNOWN'

    return title, date, author


def verify_source(source_text):
    """Verify that the text is an actual information source and not noise.

    Sends the source through the VERIFY_SOURCE_PROMPT template.
    Returns the LLM response containing either 'SOURCE' or 'NOISE'.
    """
    prompt = PromptBuilder()
    prompt.add_from_file(PROMPTS_DIR / 'VERIFY_SOURCE_PROMPT.md')
    prompt.add_text(source_text)

    return lm_client.send_streaming(prompt.get_prompt())



def populate_db_from_mtw(log=True):
    """
    Populate the sources table from the Mind the Wires search_results database.

    MTW schema (search_results):
        id, url, title, content, search_query, timestamp, word_count, source_domain, date_posted

    Sources schema:
        id (UUID), url, origin, author, published_at, source_type,
        credibility_score, summary, raw_text, ingested_at, content_hash

    Returns a tuple of (processed_count, elapsed_seconds).
    """
    start = time.time()
    processed = 0

    # Ensure the sources table exists
    init_sources_schema()

    # Set row_factory on MTW connection so rows are dict-like
    mtw_connection.row_factory = sqlite3.Row

    cursor = mtw_connection.cursor()
    cursor.execute(
        "SELECT id, url, title, content, source_domain, date_posted, "
        "timestamp FROM search_results"
    )

    for row in cursor:
        processed += 1
        if log:
            print(f"\n--- Processing: {row['url']} ---")

        # --- raw source ---
        raw_source = row['content']

        # --- dedup: skip if already processed (before any LLM calls) ---
        content_hash = _source_hash(raw_source)
        if mythic_db_conn.execute("SELECT 1 FROM sources WHERE content_hash = ?", (content_hash,)).fetchone():
            if log:
                print(f"  Skipped (duplicate content): {row['url']}")
            continue
        if mythic_db_conn.execute("SELECT 1 FROM sources WHERE url = ?", (row['url'],)).fetchone():
            if log:
                print(f"  Skipped (duplicate url): {row['url']}")
            continue

        # --- verification: skip noise before any other LLM calls ---
        verification = verify_source(raw_source)
        if 'NOISE' in verification.upper():
            if log:
                print(f"  Skipped: classified as noise ({verification})")
            continue

        # --- solid data (mapped from MTW) ---
        source_id = str(uuid.uuid4())
        url = row['url']
        origin = row['source_domain']
        published_at = row['date_posted']
        ingested_at = row['timestamp']

        # --- LLM assisted data parsing ---
        title, source_date, author = extract_metadata(raw_source)
        credibility_raw = generate_credibility_score(raw_source)
        source_summary = generate_source_summary(raw_source)

        # Parse credibility score — LLM returns a string, schema requires float
        try:
            credibility_score = float(credibility_raw)
        except (TypeError, ValueError):
            if log:
                print(f"  WARNING: could not parse credibility score, defaulting to 0.5")
            credibility_score = 0.5

        # Clamp to [0.0, 1.0] to satisfy CHECK constraint
        credibility_score = max(0.0, min(1.0, credibility_score))

        # Insert into the sources table
        try:
            mythic_db_conn.execute(
                "INSERT INTO sources "
                "(id, url, origin, author, published_at, source_type, "
                " credibility_score, summary, raw_text, ingested_at, content_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    source_id,
                    url,
                    origin,
                    author,
                    published_at or source_date,
                    "article",  # source_type — all MTW sources are articles
                    credibility_score,
                    source_summary,
                    raw_source,
                    ingested_at,
                    content_hash,
                ),
            )
            mythic_db_conn.commit()
            if log:
                print(f"  Inserted source {source_id}")
                print(f"    url: {url}")
                print(f"    origin: {origin}")
                print(f"    author: {author}")
                print(f"    published_at: {published_at or source_date}")
                print(f"    source_type: article")
                print(f"    credibility_score: {credibility_score}")
                print(f"    summary: {source_summary}")
                print(f"    ingested_at: {ingested_at}")
        except sqlite3.IntegrityError as e:
            if log:
                print(f"  Skipped (duplicate url/ingested_at): {e}")

    elapsed = time.time() - start
    if log:
        print(f"\npopulate_db_from_mtw completed in {elapsed:.1f}s")

    return processed, elapsed


def clear_sources():
    """Delete all rows from the sources table.

    Testing utility — wipes the table so populate_db_from_mtw can be
    re-run without duplicates.
    """
    mythic_db_conn.execute("DELETE FROM sources")
    mythic_db_conn.commit()
    print("Cleared all rows from sources.")


def log_run(time_unit="minute"):
    """Run populate_db_from_mtw and write a timing note to sources/.

    Writes a .txt file with the timestamp, rows processed, total elapsed
    time, and estimated time per row.

    Parameters:
        time_unit: "minute", "hour", or "all" — determines how many rows
                   to process based on the time available. Defaults to "minute".
    """
    start = time.time()

    processed, elapsed = populate_db_from_mtw(log=False)
    elapsed_total = time.time() - start
    per_row = elapsed_total / processed if processed > 0 else 0

    note_path = SCRIPT_DIR / f"run_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    note_path.write_text(
        f"Run: {datetime.now().isoformat()}\n"
        f"Time unit: {time_unit}\n"
        f"Rows processed: {processed}\n"
        f"Total elapsed: {elapsed_total:.1f}s\n"
        f"Avg time per row: {per_row:.2f}s\n"
    )
    print(f"Run log written to {note_path}")
        
        
        
    


def main():
    ''' REMEMBER TO DELETE CLEAR SOURCES EVENTUALLY ''' 
    clear_sources()
    populate_db_from_mtw()


if __name__ == "__main__":
    main()

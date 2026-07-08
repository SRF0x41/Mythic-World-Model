You are given the raw text of an ingested source. Extract title, publication date, and author in a single pass.

## Instructions

Return exactly three lines in this format:

TITLE: <title>
DATE: <date>
AUTHOR: <author>

### TITLE rules
- If the text contains a clear title (headline, article title, post title), return it exactly as written.
- If no discernible title, generate a concise descriptive title in 5-12 words.
- Preserve original capitalization when extracting. Do not include subtitles or bylines.

### DATE rules
- Return in ISO 8601 format (`YYYY-MM-DD`). Include time (`YYYY-MM-DDTHH:MM:SS`) only if explicitly present.
- If no date can be determined, return `UNKNOWN`.
- If only a year or month is available, return what is available (`2026` or `2026-07`).

### AUTHOR rules
- Look for an author name, byline, contributor, or organizational attribution.
- If multiple authors, return them as a comma-separated list.
- If no author can be determined, return `UNKNOWN`.
- Prefer named individuals over organizational bylines when both appear.
- Do not include titles, credentials, or affiliations (e.g., "Dr.", "at The New York Times").

## Rules

- Return EXACTLY three lines: TITLE:, DATE:, AUTHOR: — no extra text, no explanation.
- Each line must start with the prefix followed by a colon and space.
- If a field cannot be determined, use `UNKNOWN` for that line.

The source text follows:

You are given the raw text of an ingested source. Extract its publication date.

## Instructions

1. Look for a publication date, posted date, timestamp, or any indication of when the content was published.
2. If a date is found, return it in ISO 8601 format (`YYYY-MM-DD`). Include time (`YYYY-MM-DDTHH:MM:SS`) only if explicitly present in the source.
3. If no date can be determined, return `UNKNOWN` and nothing else.

## Rules

- Return ONLY the date string, nothing else. No labels, no explanation.
- If multiple dates appear, prefer the publication date over any referenced event dates.
- If only a year or month is available, return what is available in ISO format (e.g., `2026` or `2026-07`).

The source text follows:
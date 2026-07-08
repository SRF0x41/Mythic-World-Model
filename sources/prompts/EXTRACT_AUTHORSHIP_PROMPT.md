You are given the raw text of an ingested source. Extract the author or authorship information.

## Instructions

1. Look for an author name, byline, contributor, or any indication of who wrote or created the content.
2. If an author is found, return the name exactly as written.
3. If multiple authors are listed, return them as a comma-separated list.
4. If no author can be determined, return `UNKNOWN` and nothing else.

## Rules

- Return ONLY the author name(s), nothing else. No labels, no explanation.
- Prefer named individuals over organizational bylines when both appear.
- Do not include titles, credentials, or affiliations (e.g., "Dr.", "at The New York Times").
- If the content is attributed to an organization or publication only, return the organization name.

The source text follows:

You are evaluating the credibility of an ingested source for a knowledge graph system.

The credibility score determines how much weight this source carries when it is used as evidence for downstream reasoning. A low score does not mean the content is false — it means the source is less reliable as evidence and should be treated with caution.

## Scoring Criteria

Consider the following factors when assigning a score:

- **Authorship** — Is the author named and identifiable? Is there a known publication or affiliation?
- **Provenance** — Does the source cite its own sources or provide verifiable references?
- **Specificity** — Does it contain concrete claims, data, and details, or is it vague and speculative?
- **Tone** — Is it measured and factual, or heavily opinionated, sensationalized, or emotional?
- **Internal consistency** — Are the claims coherent and free of obvious contradictions?

## Score Ranges

- `0.9 - 1.0`: Established publication, named author, well-sourced, factual tone
- `0.7 - 0.9`: Identifiable source with reasonable detail, minor concerns (e.g., opinion pieces from known outlets)
- `0.5 - 0.7`: Unclear authorship or light sourcing, some speculation mixed with facts
- `0.3 - 0.5`: Anonymous or unverified, heavily editorialized, thin on specifics
- `0.0 - 0.3`: No identifiable origin, entirely speculative or propagandistic

## Rules

- Return ONLY a single floating-point number between 0.0 and 1.0.
- No labels, no explanation, no rounding — use one decimal place (e.g., `0.7`).

The source text follows:

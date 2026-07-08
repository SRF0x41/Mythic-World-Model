# Mythic World Model

A living knowledge graph for modeling the contemporary zeitgeist.

---

## What Is This?

We live in an era of overwhelming information. Every day, thousands of articles, papers, discussions, and reports are published about the world we live in. Most of this information is consumed once and forgotten — even by the systems designed to analyze it.

The Mythic World Model takes a different approach. Instead of asking a question, getting an answer, and moving on, it builds a **permanent record of understanding** that grows richer with every new piece of information.

Think of it as a library of knowledge that never forgets. Every observation, every pattern, every explanation, and every connection is stored permanently. New information doesn't replace what came before — it adds to it, reshaping and refining the picture over time.

The goal is not to produce isolated answers, but to accumulate a coherent understanding of how culture changes, why those changes occur, and what they may imply for the future.

---

## Philosophy

Most AI systems today are conversational. You ask a question, the system gives an answer, and the reasoning that produced that answer disappears. The system has no memory of its own thought process. If you ask the same question tomorrow, it reasons from scratch.

This project is built on the belief that **reasoning itself is data worth preserving**.

When the system reads an article, it doesn't just produce a summary. It extracts specific claims from that article. It notices which claims appear across many independent sources. It groups those recurring patterns into stable concepts. It builds hypotheses about how those concepts influence each other. It constructs models that explain systems of change. And it makes predictions that can be tested against future events.

Every single one of these steps is stored as a permanent, inspectable object in a database. If the system concludes that institutional distrust is rising, you can trace that conclusion back through the model, through the hypotheses, through the concepts, through the signals, through the individual pieces of evidence, and ultimately to the original articles and sources that started it all.

This matters for several reasons:

- **Transparency.** Every conclusion carries its full chain of evidence. You can see exactly why the system believes what it believes, down to the original source.
- **Continuity.** Understanding accumulates. The system doesn't start over each time — it builds on what it already knows.
- **Competition.** Multiple explanations can coexist. The system holds competing hypotheses and models side by side, letting accumulating evidence determine which holds up better over time.
- **Falsifiability.** Models generate predictions. As new information arrives, those predictions are validated or invalidated, revealing which models are actually useful and which aren't.

The system is not designed to produce opinions. It is designed to construct **testable, evidence-backed explanations** of the world we live in.

Nothing exists without provenance. Every object in the system can be traced back to the sources that informed it.

---

## Architecture

Built on a minimal, fully local-first stack:

- **Python** — reasoning and orchestration layer (zero external dependencies for the core)
- **SQLite** — persistent knowledge substrate

No distributed systems, no external databases, no heavyweight infrastructure. Every transformation is explicit. Every object is inspectable. Every relationship is queryable.

### Database Layout

All layers and the ontology share a single SQLite database (`database/mythic_world_model.db`). Each layer's tables keep their original names — there is no prefixing needed since all table names are already unique across layers. This simplifies cross-layer queries and provenance tracing.

For the detailed schema, see [mtw_schema.md](./mtw_schema.md). The full system specification is in [mythic_world_model_constitution.md](./mythic_world_model_constitution.md).

---

## Layers

The system transforms raw information into increasingly abstract layers of understanding. Each layer is a standalone module with its own SQLite database.

| Layer | Directory | Question Answered |
|-------|-----------|-------------------|
| **0 — Verification** | (pre-sources) | Is this text actually a source or noise? |
| **1 — Sources** | [`sources/`](./sources/SOURCES_LAYER.md) | What information do we possess? |
| **2 — Evidence** | [`evidence/`](./evidence/EVIDENCE_LAYER.md) | What does this source actually support? |
| **3 — Signals** | [`signals/`](./signals/SIGNALS_LAYER.md) | What patterns consistently emerge? |
| **4 — Concepts** | [`concepts/`](./concepts/CONCEPTS_LAYER.md) | What enduring things are we observing? |
| **5 — Hypotheses** | [`hypotheses/`](./hypotheses/HYPOTHESES_LAYER.md) | How do these concepts influence one another? |
| **6 — Models** | [`models/`](./models/MODELS_LAYER.md) | What system best explains the observed patterns? |
| **7 — Predictions** | [`predictions/`](./predictions/PREDICTIONS_LAYER.md) | If this model is correct, what should happen next? |
| **8 — World Models** | [`world_models/`](./world_models/WORLD_MODELS_LAYER.md) | What coherent story ties everything together? |

Each layer maintains explicit references to the objects that produced it and the objects it supports, ensuring full provenance from every conclusion back to the original source. All tables live in a single shared database.

```
Source → Evidence → Signal → Concept → Hypothesis → Model → Prediction → World Model
```

Before any source enters Layer 1, the **verification** step classifies raw text as `SOURCE` or `NOISE`. Verification rejects ads, paywalls, login pages, error pages, and bot detection challenges before any extraction LLM calls are made, saving time and keeping the graph clean.

---

## Guiding Principle

The long-term vision is to build a living cognitive map of the modern world — a continuously evolving knowledge graph capable of explaining how culture changes, why those changes occur, and what they may imply for the future.

Nothing is discarded. Every observation remains available as evidence for future analysis.

---

## Usage

Install dependencies and initialize the database:

```bash
pip install -r requirements.txt
```

Each layer exposes a database module with an `init_db()` function and CRUD operations:

```python
from database import init_db
init_db()

from sources import add_source
source_id = add_source("https://example.com/article", "article", author="Jane Doe")
```

See each layer's `*_LAYER.md` documentation for its full API.

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP client for fetching sources and LM API calls |
| `tiktoken` | Token counting for LLM input windows |
| `certifi` / `charset-normalizer` / `idna` / `regex` / `urllib3` | Transitive dependencies |

## Dev Notes

- Perhaps credibility scores should be brief paragraphs instead of hard rankings
 CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            url TEXT,
            origin TEXT,
            author TEXT,
            published_at TEXT,
            source_type TEXT NOT NULL,
            credibility_score REAL CHECK(credibility_score BETWEEN 0.0 AND 1.0),
            summary TEXT,
            raw_text TEXT,
            ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(url, ingested_at)
        );
        CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
        CREATE INDEX IF NOT EXISTS idx_sources_published ON sources(published_at);
        CREATE INDEX IF NOT EXISTS idx_sources_ingested ON sources(ingested_at);
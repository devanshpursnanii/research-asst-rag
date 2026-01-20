-- PaperStack Metrics Schema
-- SQLite database for tracking PaperChat performance metrics

-- Session tracking
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    session_start_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Request-level metrics for each chat query
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    query TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    total_chunk_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    llm_latency_ms REAL NOT NULL,
    total_latency_ms REAL NOT NULL,
    operation_type TEXT NOT NULL DEFAULT 'chat_message',
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Individual chunk metrics for each request
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    paper_title TEXT NOT NULL,
    content_preview TEXT NOT NULL,
    chunk_token_count INTEGER NOT NULL,
    FOREIGN KEY (request_id) REFERENCES requests(request_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_requests_session ON requests(session_id);
CREATE INDEX IF NOT EXISTS idx_requests_created ON requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_request ON chunks(request_id);

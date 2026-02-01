# Database Layer - Technical Documentation

## Overview
Abstraction layer supporting both SQLite (local) and PostgreSQL (Supabase cloud) with unified interface for metrics and session persistence.

## Architecture

```
backend/db/
├── __init__.py
├── connection.py        # Database connection factory
├── repository.py        # Pure DB I/O operations
├── schema.sql          # SQLite schema
└── schema_postgres.sql # PostgreSQL schema
```

## Design Principles

1. **Database Agnostic**: Single codebase for SQLite and PostgreSQL
2. **No Business Logic**: Pure I/O operations, no FastAPI/AI dependencies
3. **Connection Management**: Automatic cleanup, proper resource handling
4. **Type Safety**: Pydantic models for validation in parent modules

## Connection Layer (connection.py)

### Configuration

**Environment Variables**:
```bash
DATABASE_TYPE=sqlite|postgres  # Required

# SQLite Config
SQLITE_DB_PATH=logs.db

# PostgreSQL Config (Supabase)
SUPABASE_HOST=db.xxxxx.supabase.co
SUPABASE_PORT=5432
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=your_password
```

### Functions

#### get_connection()

**Purpose**: Return appropriate connection based on DATABASE_TYPE

**Returns**:
- `sqlite3.Connection` (DATABASE_TYPE=sqlite)
- `psycopg2.connection` (DATABASE_TYPE=postgres)

**Raises**:
- `ValueError`: Invalid DATABASE_TYPE
- `ConnectionError`: Database connection fails

#### _get_sqlite_connection()

**Configuration**:
```python
conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
conn.execute("PRAGMA foreign_keys = ON")
conn.row_factory = sqlite3.Row
```

**Features**:
- Foreign key enforcement enabled
- Dict-like row access via Row factory
- Thread-safe connections

**File Location**: Resolved relative to project root

#### _get_postgres_connection()

**Configuration**:
```python
conn = psycopg2.connect(
    host=SUPABASE_HOST,
    port=SUPABASE_PORT,
    database=SUPABASE_DATABASE,
    user=SUPABASE_USER,
    password=SUPABASE_PASSWORD,
    cursor_factory=RealDictCursor
)
```

**Features**:
- RealDictCursor for dict-like row access (matches SQLite Row)
- Compatible with Supabase session pooler
- Connection pooling at server level

**Error Handling**:
- Validates credentials exist before connecting
- Wraps connection errors with context

## Repository Layer (repository.py)

### Query Building

#### _build_query(query: str) -> str

**Purpose**: Convert SQLite placeholders to PostgreSQL format

**Behavior**:
- SQLite: `?` placeholders (unchanged)
- PostgreSQL: Replaces `?` with `%s`

**Example**:
```python
# Input
"INSERT INTO table (col1, col2) VALUES (?, ?)"

# SQLite output (unchanged)
"INSERT INTO table (col1, col2) VALUES (?, ?)"

# PostgreSQL output
"INSERT INTO table (col1, col2) VALUES (%s, %s)"
```

**Usage**: All raw SQL queries use `?`, then get converted

### CRUD Operations

#### create_session(session_id, session_start_ts)

**Purpose**: Insert new session record

**SQL**:
```sql
-- SQLite
INSERT OR IGNORE INTO sessions (session_id, session_start_ts) 
VALUES (?, ?)

-- PostgreSQL
INSERT INTO sessions (session_id, session_start_ts) 
VALUES (%s, %s) 
ON CONFLICT (session_id) DO NOTHING
```

**Behavior**: Idempotent - safe to call multiple times

#### insert_request(request_data: Dict)

**Purpose**: Insert metrics for single request

**Required Fields**:
- `request_id`: Unique identifier (UUID)
- `session_id`: Parent session
- `query`: User query text
- `prompt_tokens`: Input token count
- `total_chunk_tokens`: Retrieved context tokens
- `completion_tokens`: Output token count
- `llm_latency_ms`: LLM inference time
- `total_latency_ms`: Total request time
- `operation_type`: "chat_message" | "brain_search"
- `status`: "success" | "error"
- `error_message`: Optional error details

**SQL**:
```sql
INSERT INTO requests (
    request_id, session_id, query, 
    prompt_tokens, total_chunk_tokens, completion_tokens,
    llm_latency_ms, total_latency_ms, 
    operation_type, status, error_message
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

#### insert_chunks(request_id, chunks: List[Dict])

**Purpose**: Batch insert chunk metrics

**Required Fields per Chunk**:
- `chunk_index`: Position in retrieval order
- `paper_title`: Source paper
- `content_preview`: First 200 chars
- `chunk_token_count`: Token count

**SQL**:
```sql
INSERT INTO chunks (
    request_id, chunk_index, paper_title, 
    content_preview, chunk_token_count
) VALUES (?, ?, ?, ?, ?)
```

**Performance**: Uses `executemany()` for batch insert

#### get_requests_by_session(session_id) -> List[Dict]

**Purpose**: Retrieve all requests for session

**Returns**: List of request dicts with `total_tokens` calculated

**Calculation**:
```python
total_tokens = prompt_tokens + total_chunk_tokens + completion_tokens
```

**SQL**:
```sql
SELECT *, 
       (prompt_tokens + total_chunk_tokens + completion_tokens) as total_tokens
FROM requests 
WHERE session_id = ?
ORDER BY created_at DESC
```

#### get_chunks_by_request(request_id) -> List[Dict]

**Purpose**: Retrieve all chunks for request

**Returns**: List of chunk dicts

**SQL**:
```sql
SELECT * FROM chunks 
WHERE request_id = ? 
ORDER BY chunk_index
```

#### get_session_metrics(session_id) -> Dict

**Purpose**: Aggregate all metrics for session

**Returns**:
```python
{
    'session_id': str,
    'total_requests': int,
    'total_tokens': int,
    'avg_llm_latency': float,
    'avg_total_latency': float,
    'requests': [
        {
            'request_id': str,
            'query': str,
            'prompt_tokens': int,
            'total_chunk_tokens': int,
            'completion_tokens': int,
            'total_tokens': int,
            'llm_latency_ms': float,
            'total_latency_ms': float,
            'operation_type': str,
            'status': str,
            'created_at': datetime,
            'chunks': [...]
        },
        ...
    ]
}
```

**Aggregation Logic**:
- Total requests: COUNT(*)
- Total tokens: SUM(prompt_tokens + total_chunk_tokens + completion_tokens)
- Avg LLM latency: AVG(llm_latency_ms)
- Avg total latency: AVG(total_latency_ms)

**Joins**: requests ← chunks (for each request)

#### session_exists(session_id) -> bool

**Purpose**: Quick existence check

**SQL**:
```sql
SELECT 1 FROM sessions WHERE session_id = ? LIMIT 1
```

**Returns**: True if found, False otherwise

#### delete_session(session_id)

**Purpose**: Delete session and cascade to requests/chunks

**Behavior**:
- SQLite: Foreign keys CASCADE DELETE (if enabled)
- PostgreSQL: Database-level CASCADE DELETE

**SQL**:
```sql
DELETE FROM sessions WHERE session_id = ?
```

**Effect**: Removes session + all requests + all chunks

### Connection Management

**Pattern** (used in all functions):
```python
def some_operation():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        # ... process results
    finally:
        conn.close()  # Always close
```

**Benefits**:
- No connection leaks
- Automatic cleanup on exceptions
- Transaction safety (commit before close)

## Schema Design

### Tables

#### sessions
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    session_start_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Track active/historical sessions

**Relationships**: Parent to requests

#### requests
```sql
CREATE TABLE requests (
    request_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    query TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    total_chunk_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    llm_latency_ms REAL NOT NULL,
    total_latency_ms REAL NOT NULL,
    operation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        ON DELETE CASCADE
);
```

**Purpose**: Store per-request metrics

**Relationships**: 
- Parent: sessions (session_id)
- Child: chunks (request_id)

#### chunks
```sql
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- SQLite
    -- OR --
    id SERIAL PRIMARY KEY,  -- PostgreSQL
    
    request_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    paper_title TEXT NOT NULL,
    content_preview TEXT NOT NULL,
    chunk_token_count INTEGER NOT NULL,
    
    FOREIGN KEY (request_id) REFERENCES requests(request_id)
        ON DELETE CASCADE
);
```

**Purpose**: Store retrieved chunks for each request

**Relationships**: Parent is requests (request_id)

### Indexes

**PostgreSQL**:
```sql
CREATE INDEX idx_requests_session_id ON requests(session_id);
CREATE INDEX idx_chunks_request_id ON chunks(request_id);
```

**Purpose**: Speed up JOIN and WHERE queries

**SQLite**: Auto-indexes on foreign keys and primary keys

### CASCADE DELETE Flow

```
DELETE FROM sessions WHERE session_id = 'abc'
  ↓
DELETE FROM requests WHERE session_id = 'abc'
  ↓
DELETE FROM chunks WHERE request_id IN (...)
```

**Result**: Single delete removes all related data

## Database Differences

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Placeholder | `?` | `%s` |
| Upsert | `INSERT OR IGNORE` | `ON CONFLICT DO NOTHING` |
| Row Access | `sqlite3.Row` | `RealDictCursor` |
| Auto-increment | `AUTOINCREMENT` | `SERIAL` |
| Connection | File-based | TCP/IP |
| Concurrency | File locking | MVCC |
| Deployment | Single file | Cloud database |

**Abstraction**: repository.py handles all differences transparently

## Data Flow

### Write Path
```
Backend API
  ↓
collect_request_metrics() [AI module]
  ↓
repository.insert_request(data)
  ↓
_build_query() [convert placeholders]
  ↓
get_connection() [DB-specific conn]
  ↓
cursor.execute() + commit()
  ↓
close connection
```

### Read Path
```
Backend API
  ↓
repository.get_session_metrics(session_id)
  ↓
get_connection()
  ↓
Execute aggregate query
  ↓
Fetch all requests + JOIN chunks
  ↓
Return structured dict
  ↓
Close connection
```

## Error Handling

### Connection Errors

**SQLite**:
- Missing DB file → Auto-created on startup
- Permission errors → Propagate to caller
- Locked database → Retry or fail

**PostgreSQL**:
- Missing credentials → `ConnectionError` with message
- Network issues → psycopg2 exception propagates
- Authentication failure → Connection error

### Query Errors

**Handled by Caller**: Repository doesn't catch query errors
**Foreign Key Violations**: Prevented by proper insert order
**Duplicate Keys**: Handled by upsert logic (OR IGNORE / ON CONFLICT)

## Performance Considerations

### SQLite
- **Bottleneck**: Write locking (single writer)
- **Optimization**: Batch inserts (executemany)
- **Best For**: Single-instance deployments

### PostgreSQL
- **Bottleneck**: Network latency
- **Optimization**: Connection pooling, batch inserts
- **Best For**: Multi-instance, cloud deployments

### Query Optimization
- **Indexes**: On foreign keys and frequently queried columns
- **Batch Inserts**: executemany for chunks
- **Aggregation**: Database-level SUM/AVG (not Python)

## Testing

### SQLite Testing
```bash
# Database auto-created on first run
python -c "from backend.db.repository import *; create_session('test')"
```

### PostgreSQL Testing
```bash
# 1. Set env vars in .env
DATABASE_TYPE=postgres
SUPABASE_HOST=...
SUPABASE_PASSWORD=...

# 2. Run schema in Supabase SQL editor
# Copy contents of schema_postgres.sql

# 3. Test connection
python -c "from backend.db.connection import get_connection; get_connection()"
```

## Migration Path

### SQLite → PostgreSQL

1. Export data:
```python
import sqlite3
import json

conn = sqlite3.connect('logs.db')
conn.row_factory = sqlite3.Row

sessions = [dict(row) for row in conn.execute("SELECT * FROM sessions")]
requests = [dict(row) for row in conn.execute("SELECT * FROM requests")]
chunks = [dict(row) for row in conn.execute("SELECT * FROM chunks")]

with open('export.json', 'w') as f:
    json.dump({'sessions': sessions, 'requests': requests, 'chunks': chunks}, f)
```

2. Update .env:
```bash
DATABASE_TYPE=postgres
SUPABASE_HOST=...
```

3. Import data:
```python
import json
from backend.db.repository import *

with open('export.json') as f:
    data = json.load(f)

for s in data['sessions']:
    create_session(s['session_id'], s['session_start_ts'])

for r in data['requests']:
    insert_request(r)

for req_id, chunk_list in group_chunks_by_request(data['chunks']):
    insert_chunks(req_id, chunk_list)
```

## Deployment

### SQLite (Development)
1. Set `DATABASE_TYPE=sqlite` in .env
2. Run backend - DB auto-created
3. Single server instance only

### PostgreSQL (Production)
1. Create Supabase project
2. Run schema_postgres.sql in SQL editor
3. Set credentials in .env
4. Set `DATABASE_TYPE=postgres`
5. Start backend
6. Supports multiple instances

### Backups

**SQLite**: Copy logs.db file
**PostgreSQL**: Use Supabase dashboard or pg_dump

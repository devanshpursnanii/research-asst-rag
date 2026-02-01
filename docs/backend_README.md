# Backend - Technical Documentation

## Overview
FastAPI backend providing RESTful API for Paper Brain AI system. Manages authentication, session state, database operations, and AI module integration.

## Architecture

```
backend/
├── main.py           # FastAPI app, endpoints, middleware
├── models.py         # Pydantic request/response models
├── session.py        # In-memory session management
└── db/
    ├── connection.py # Database connection abstraction
    ├── repository.py # Pure DB I/O operations
    ├── schema.sql    # SQLite schema
    └── schema_postgres.sql  # PostgreSQL schema
```

## Core Components

### 1. FastAPI Application (main.py)

#### Startup & Initialization

**Database Bootstrap** (bootstrap_database):
- Detects `DATABASE_TYPE` from env (sqlite/postgres)
- **SQLite**: Auto-creates DB file if missing, executes schema.sql
- **PostgreSQL**: Verifies connection, checks table existence
- Logs initialization status

**Startup Event**:
```python
@app.on_event("startup")
async def startup_event():
    bootstrap_database()
    cleanup_old_sessions()  # Remove sessions >24h old
```

#### Authentication System

**Token-Based Access**:
- Single access token from `ACCESS_TOKEN` env var (default: "welcometopaperstack1")
- Bearer token authentication on all routes except auth validation

**Auth Middleware Flow**:
1. **OPTIONS requests**: Pass through (CORS preflight)
2. **Public paths**: `/auth/validate`, `/`, `/docs`, `/openapi.json`, `/redoc`
3. **All other routes**: Require `Authorization: Bearer <token>` header
4. **Invalid/missing token**: 401 Unauthorized

**Validation**:
```python
def verify_token(token: str) -> bool:
    return token == ACCESS_TOKEN
```

#### CORS Configuration

**Allowed Origins**:
```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.0.104:3000",  # Local network
    "http://192.168.0.106:3000",
    "http://192.168.0.107:3000"
]
```

**Headers**: Allow all
**Methods**: GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH
**Credentials**: Enabled

#### API Endpoints

**1. POST /auth/validate**
- **Purpose**: Validate access token
- **Request**: `{"token": "string"}`
- **Response**: `{"valid": bool, "message": "string"}`
- **No auth required**

**2. POST /session/create**
- **Purpose**: Create new session with unique ID
- **Request**: `{"initial_query": "string"}`
- **Response**: `{"session_id": "uuid", "created_at": "ISO8601"}`
- **Creates**: SessionLogger, QuotaTracker, in-memory session

**3. POST /brain/search**
- **Purpose**: Search papers with Paper Brain
- **Request**: `{"session_id": "uuid", "query": "string", "search_mode": "topic|title"}`
- **Response**: `{"thinking_steps": [...], "papers": [...], "searches_remaining": int}`
- **Quota check**: can_use_brain()
- **Increment**: brain_searches counter
- **Error handling**: QuotaExhaustedError → 429 with cooldown

**4. POST /brain/load**
- **Purpose**: Load selected papers' PDFs
- **Request**: `{"session_id": "uuid", "paper_ids": ["arxiv_id1", ...]}`
- **Response**: `{"thinking_steps": [...], "loaded_papers": [...], "status": "success"}`
- **Side effect**: Stores Documents in session.loaded_documents

**5. POST /chat/message**
- **Purpose**: Send message to RAG chat
- **Request**: `{"session_id": "uuid", "message": "string"}`
- **Response**: `{"thinking_steps": [...], "answer": "string", "citations": [...], "messages_remaining": int}`
- **Quota check**: can_use_chat()
- **Metrics**: Collects and persists to DB
- **Increment**: chat_messages counter

**6. GET /session/{session_id}/info**
- **Purpose**: Get session info and logs
- **Response**: `{"session_info": {...}, "logs_summary": {...}}`
- **Returns**: Session metadata, quota status, loaded papers

**7. GET /metrics/{session_id}**
- **Purpose**: Get all metrics for session
- **Response**: `{"session_id": "uuid", "total_requests": int, "total_tokens": int, "requests": [...]}`
- **Source**: Database (repository.get_session_metrics)

#### Error Handling

**Error Types**:
- `quota_exhausted`: Rate limit hit (429)
- `not_found`: Session not found (404)
- `validation`: Invalid request data (422)
- `unauthorized`: Missing/invalid token (401)
- `internal`: Server error (500)

**ErrorResponse Model**:
```python
{
    "error": "Human-readable message",
    "error_type": "quota_exhausted",
    "cooldown_minutes": 15,
    "message": "Additional context"
}
```

### 2. Data Models (models.py)

#### Request Models

**CreateSessionRequest**:
- `initial_query`: str (first user query)

**BrainSearchRequest**:
- `session_id`: UUID
- `query`: str (research query)
- `search_mode`: "topic" | "title" (default: "topic")

**BrainLoadRequest**:
- `session_id`: UUID
- `paper_ids`: List[str] (arXiv IDs)

**ChatMessageRequest**:
- `session_id`: UUID
- `message`: str (user question)

#### Response Models

**ThinkingStep**: Agent processing status
- `step`: str (e.g., "rewriting", "searching")
- `status`: "in_progress" | "complete" | "error"
- `result`: Optional[str]

**Paper**: arXiv paper metadata
- `title`, `authors`, `abstract`, `arxiv_id`, `url`, `score`

**Citation**: Extracted from response
- `paper`: str (title)
- `page`: int

**QuotaStatus**: Session limits
- `brain`: {allowed: bool, remaining: int, limit: int}
- `chat`: {allowed: bool, remaining: int, limit: int}
- `api_exhausted`: bool

**MetricsRequest**: Single request metrics
- `request_id`, `query`, `prompt_tokens`, `total_chunk_tokens`
- `completion_tokens`, `total_tokens`, `llm_latency_ms`
- `total_latency_ms`, `operation_type`, `status`, `created_at`
- `chunks`: List[{chunk_index, paper_title, content_preview, chunk_token_count}]

### 3. Session Management (session.py)

**Session Dataclass**:
```python
@dataclass
class Session:
    session_id: str              # UUID
    logger: SessionLogger        # AI module logger
    quota: QuotaTracker          # Usage limits
    
    # Paper Brain
    loaded_documents: List[Document]
    loaded_paper_titles: List[str]
    brain_history: List[dict]
    
    # Paper Chat
    chat_history: List[dict]
    
    # Metadata
    created_at: datetime
    last_activity: datetime
    initial_query: str
```

**Global Store**:
```python
sessions: Dict[str, Session] = {}
```

**Functions**:

- `create_session(initial_query)`: Creates session, stores in memory
- `get_session(session_id)`: Retrieves session, updates last_activity
- `cleanup_old_sessions(max_age_hours=24)`: Removes stale sessions, saves logs
- `delete_session(session_id)`: Manual deletion, saves logs

**Session Lifecycle**:
1. Created via `/session/create`
2. Lives in memory during active use
3. Updated on every API call (last_activity)
4. Auto-cleanup after 24h of inactivity
5. Logs saved before deletion

### 4. Database Layer

#### Connection (db/connection.py)

**Dual Database Support**:

**Environment Variables**:
```bash
DATABASE_TYPE=sqlite|postgres

# SQLite
SQLITE_DB_PATH=logs.db

# PostgreSQL (Supabase)
SUPABASE_HOST=db.xxxxx.supabase.co
SUPABASE_PORT=5432
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=...
```

**get_connection()** returns:
- `sqlite3.Connection` (DATABASE_TYPE=sqlite)
- `psycopg2.connection` (DATABASE_TYPE=postgres)

**SQLite Configuration**:
- Foreign keys enabled
- Row factory for dict-like access
- Thread-safe (check_same_thread=False)

**PostgreSQL Configuration**:
- RealDictCursor for dict-like rows
- Connection pooling (via Supabase)
- Session pooler for serverless compatibility

#### Repository (db/repository.py)

**Pure DB I/O - No FastAPI/AI imports**

**Query Building**:
```python
def _build_query(query: str) -> str:
    """Replace ? with %s for PostgreSQL"""
    if DATABASE_TYPE == "postgres":
        return query.replace("?", "%s")
    return query
```

**Functions**:

1. **create_session(session_id, session_start_ts)**
   - Inserts into `sessions` table
   - SQLite: `INSERT OR IGNORE`
   - PostgreSQL: `INSERT ... ON CONFLICT DO NOTHING`

2. **insert_request(request_data)**
   - Inserts into `requests` table
   - Fields: request_id, session_id, query, tokens, latencies, status

3. **insert_chunks(request_id, chunks)**
   - Batch insert into `chunks` table
   - Per-chunk: chunk_index, paper_title, content_preview, token_count

4. **get_requests_by_session(session_id)**
   - Returns all requests for session
   - Includes calculated total_tokens

5. **get_chunks_by_request(request_id)**
   - Returns all chunks for request
   - Used in metrics display

6. **get_session_metrics(session_id)**
   - Aggregates: total_requests, total_tokens, avg latencies
   - Joins requests + chunks
   - Returns full metrics view

7. **session_exists(session_id)**
   - Quick existence check
   - Used for validation

8. **delete_session(session_id)**
   - CASCADE deletes requests and chunks
   - SQLite: Manual deletion via foreign keys
   - PostgreSQL: Database-level cascade

**Error Handling**:
- All functions properly close connections
- Transactions committed before close
- Exceptions propagate to caller

### 5. Database Schema

#### Tables

**sessions**:
```sql
session_id TEXT PRIMARY KEY
session_start_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

**requests**:
```sql
request_id TEXT PRIMARY KEY
session_id TEXT (FK → sessions)
query TEXT
prompt_tokens INTEGER
total_chunk_tokens INTEGER
completion_tokens INTEGER
llm_latency_ms REAL
total_latency_ms REAL
operation_type TEXT ('chat_message', 'brain_search', etc.)
status TEXT ('success', 'error')
error_message TEXT
created_at TIMESTAMP
```

**chunks**:
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
request_id TEXT (FK → requests)
chunk_index INTEGER
paper_title TEXT
content_preview TEXT
chunk_token_count INTEGER
```

**Relationships**:
- sessions → requests (1:N, CASCADE DELETE)
- requests → chunks (1:N, CASCADE DELETE)

**Indexes** (PostgreSQL):
```sql
CREATE INDEX idx_requests_session_id ON requests(session_id);
CREATE INDEX idx_chunks_request_id ON chunks(request_id);
```

## Data Flow

### Session Creation Flow
```
POST /session/create
  → create_session(query)
  → SessionLogger init
  → QuotaTracker init
  → Store in sessions dict
  → repository.create_session()
  → Return session_id + timestamp
```

### Paper Search Flow
```
POST /brain/search
  → get_session(session_id)
  → quota.can_use_brain()
  → web_brain_search() [AI module]
  → quota.increment_brain()
  → Return papers + thinking_steps
```

### RAG Chat Flow
```
POST /chat/message
  → get_session(session_id)
  → quota.can_use_chat()
  → web_chat_query() [AI module]
  → collect_request_metrics()
  → repository.insert_request()
  → repository.insert_chunks()
  → quota.increment_chat()
  → Return answer + citations
```

### Metrics Retrieval Flow
```
GET /metrics/{session_id}
  → repository.get_session_metrics()
  → Aggregate from requests + chunks
  → Calculate totals and averages
  → Return MetricsResponse
```

## Environment Configuration

**Required**:
```bash
GOOGLE_API_KEY1=...
GOOGLE_API_KEY2=...
ACCESS_TOKEN=...
```

**Database (choose one)**:
```bash
# SQLite (local)
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=logs.db

# PostgreSQL (Supabase)
DATABASE_TYPE=postgres
SUPABASE_HOST=...
SUPABASE_PASSWORD=...
```

## Deployment Considerations

### SQLite Mode (Development)
- Single file database
- Auto-created on startup
- No external dependencies
- Not suitable for multi-instance deployments

### PostgreSQL Mode (Production)
- Supabase cloud database
- Connection pooling via session pooler
- Supports multiple backend instances
- Requires manual schema execution

### Session Storage
- **In-memory**: Fast but not persistent across restarts
- **Cleanup**: Auto-removes after 24h
- **Logs**: Saved to disk before deletion

### CORS
- **Development**: localhost + local IPs
- **Production**: Add deployment domain to allow_origins

### Authentication
- **Demo**: Single shared token
- **Production**: Consider JWT, API keys, or OAuth

## Performance

### Optimizations
1. **In-memory sessions**: O(1) lookup
2. **Connection pooling**: Reused DB connections (PostgreSQL)
3. **Batch inserts**: insert_chunks uses executemany
4. **Lazy cleanup**: cleanup_old_sessions on startup only

### Bottlenecks
- AI module calls (LLM latency)
- arXiv PDF fetching
- Database writes (metrics)

## Testing

**Start server**:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**With startup script**:
```bash
./start.sh  # Starts backend + frontend
```

**Database initialization**:
- SQLite: Automatic
- PostgreSQL: Run schema_postgres.sql in Supabase

## API Documentation

**Interactive docs**: http://localhost:8000/docs
**OpenAPI spec**: http://localhost:8000/openapi.json

# PaperStack - System Architecture

## System Overview

PaperStack is a full-stack AI-powered research paper discovery and multi-paper RAG (Retrieval-Augmented Generation) chat system. It combines intelligent arXiv search with citation-backed question answering across multiple academic papers.

## High-Level Architecture

```
┌─────────────────┐
│   Frontend      │  Next.js 16 + React 19 + Tailwind
│   (Port 3000)   │  • Token-based auth
└────────┬────────┘  • Real-time metrics
         │           • Message persistence
         │ REST API
         │
┌────────▼────────┐
│   Backend       │  FastAPI + Python
│   (Port 8000)   │  • Session management
└────────┬────────┘  • Auth middleware
         │           • Metrics collection
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│  AI   │ │Database │  SQLite/PostgreSQL
│Module │ │ Layer   │  • Sessions
└───┬───┘ └─────────┘  • Requests
    │                  • Chunks
    │
┌───▼────────────┐
│External APIs   │  • Google Gemini 2.5 Flash Lite
│                │  • arXiv API
└────────────────┘  • ChromaDB (local)
```

## Component Communication

### 1. Frontend → Backend (REST API)

**Protocol**: HTTP/REST with JWT-style Bearer tokens
**Base URL**: http://localhost:8000 (dev), configurable via env

**Endpoints**:
- `POST /auth/validate` - Token validation
- `POST /session/create` - Initialize session
- `POST /brain/search` - Search papers
- `POST /brain/load` - Load PDFs
- `POST /chat/message` - RAG chat
- `GET /session/{id}/info` - Session details
- `GET /metrics/{id}` - Metrics dashboard

**Flow**:
```
User Action (Frontend)
  ↓
SessionContext function
  ↓
api.ts client (adds Authorization header)
  ↓
FastAPI endpoint
  ↓
AI module function
  ↓
Response to frontend
```

### 2. Backend → AI Module (Function Calls)

**Integration**: Direct Python imports

**Bridge Layer** (`ai/web_interface.py`):
- `web_brain_search()` - Paper discovery
- `web_brain_load_papers()` - PDF loading
- `web_chat_query()` - RAG chat

**Session Retrieval**:
```python
session = get_session(session_id)
# Access: session.loaded_documents, session.quota, session.logger
```

### 3. AI Module → External APIs

**Google Gemini**:
- **Model**: gemini-2.5-flash-lite
- **Keys**: GOOGLE_API_KEY1 (primary), GOOGLE_API_KEY2 (fallback)
- **Usage**: LLM completions, embeddings (text-embedding-004)

**arXiv API**:
- **Endpoint**: http://export.arxiv.org/api/query
- **Format**: Atom XML feed
- **Usage**: Metadata + PDF download

**ChromaDB**:
- **Storage**: Local persistent directory (`./chroma_db`)
- **Usage**: Paper ranking during discovery

### 4. Backend → Database (Repository Pattern)

**Layer Separation**:
```
backend/main.py (API handlers)
  ↓
ai/metrics_collector.py (collect data)
  ↓
backend/db/repository.py (pure I/O)
  ↓
backend/db/connection.py (DB abstraction)
  ↓
SQLite or PostgreSQL
```

**No Circular Dependencies**: AI module doesn't import backend, repository doesn't import FastAPI/AI

## Data Flow

### Complete User Journey

#### 1. Authentication
```
Browser loads page
  ↓
AuthGuard checks localStorage/sessionStorage
  ↓
If token exists: Validate with backend
  ↓
POST /auth/validate {token}
  ↓
Backend: verify_token(token)
  ↓
Response: {valid: true}
  ↓
Frontend: Show app
```

#### 2. Paper Discovery
```
User enters research query
  ↓
searchPapers() → POST /brain/search
  ↓
Backend: get_session(), check quota
  ↓
AI: semantic_rewrite(query) [Gemini LLM]
  ↓
AI: search_papers() [arXiv API, 15 papers]
  ↓
AI: rank_with_chroma() [ChromaDB, top 10]
  ↓
Response: {papers: [...], thinking_steps: [...]}
  ↓
Frontend: Display in BrainSidebar
```

#### 3. Paper Loading
```
User selects papers + clicks Load
  ↓
loadPapers(paperIds) → POST /brain/load
  ↓
Backend: get_session()
  ↓
AI: ingest_arxiv_paper() for each ID
  ↓
  └→ Fetch PDF from arXiv
  └→ Parse with pypdf (in-memory)
  └→ Create Document per page
  ↓
AI: Store in session.loaded_documents
  ↓
Response: {loaded_papers: [...], status: 'success'}
  ↓
Frontend: Update loadedPapers state
```

#### 4. RAG Chat
```
User sends question
  ↓
sendMessage(message) → POST /chat/message
  ↓
Backend: get_session(), check quota
  ↓
AI: multi_paper_rag_with_documents()
  ↓
AI Pipeline:
  1. Router classifies query (QA/Summarize/Compare/Explain)
  2. Enhance query (2 variations)
  3. Hybrid retrieval (Vector + BM25)
  4. LLM reranking
  5. Paper-aware MMR (diversity)
  6. Token compression (18K limit)
  7. LLM generation with citations
  ↓
Metrics: collect_request_metrics()
  ↓
Database: repository.insert_request() + insert_chunks()
  ↓
Response: {answer: "...", citations: [...]}
  ↓
Frontend: Display + persist + refresh metrics
```

## Storage Architecture

### In-Memory (backend/session.py)
```python
sessions: Dict[str, Session] = {}

Session:
  - session_id: UUID
  - loaded_documents: List[Document]  # Papers loaded for RAG
  - chat_history: List[dict]          # Not persisted
  - brain_history: List[dict]         # Agent interactions
  - quota: QuotaTracker               # Usage limits
  - logger: SessionLogger             # AI operations log
```

**Lifetime**: Created on session/create, cleanup after 24h

### LocalStorage (Frontend)
```javascript
paperstack_token: string              // Auth token
paperstack_messages_{sessionId}: JSON // Chat history per session
```

**Lifetime**: Persistent until manual clear (token removed on browser close)

### SessionStorage (Frontend)
```javascript
paperstack_validated: 'true'  // Auth flag
```

**Lifetime**: Cleared on tab/browser close

### Database (SQLite/PostgreSQL)
```
sessions         (session_id, session_start_ts)
  └─ requests    (request_id, query, tokens, latencies)
      └─ chunks  (chunk_index, paper_title, content, tokens)
```

**Lifetime**: Persistent, manual deletion via API

### File System
```
logs/                     # Session logs (JSON)
chroma_db/               # Vector DB storage
logs.db                  # SQLite database (if DATABASE_TYPE=sqlite)
```

## State Management Layers

### Layer 1: Browser State (Frontend)
- **AuthGuard**: Authentication status
- **SessionContext**: Global app state (session, messages, papers, metrics)
- **Component State**: Local UI state (loading, errors, selections)

### Layer 2: In-Memory State (Backend)
- **sessions dict**: Active session data
- **quota trackers**: Usage limits per session
- **loaded documents**: Papers ready for RAG

### Layer 3: Persistent State (Database)
- **sessions table**: Historical sessions
- **requests table**: All RAG operations
- **chunks table**: Retrieved content per request

### Layer 4: AI State
- **ChromaDB**: Paper embeddings during discovery
- **LlamaIndex**: Document indexes, retrievers
- **SessionLogger**: Detailed operation logs

## Security Architecture

### Authentication
- **Method**: Bearer token (single shared token for demo)
- **Storage**: localStorage (frontend), env var (backend)
- **Validation**: Per-request middleware
- **Bypass**: OPTIONS (CORS), public paths

### CORS
- **Development**: localhost + local network IPs
- **Production**: Must add deployment domains
- **Preflight**: OPTIONS requests bypass auth

### API Keys
- **Gemini API**: Dual key system with fallback
- **Supabase**: PostgreSQL credentials (if using)
- **Storage**: .env file (git-ignored)

### Input Validation
- **Frontend**: TypeScript type checking
- **Backend**: Pydantic models
- **Database**: Parameterized queries (SQL injection prevention)

## Deployment Architecture

### Development (Local)
```
Terminal 1: ./start.sh
  ├─ Backend (uvicorn, port 8000)
  └─ Frontend (next dev, port 3000)

Database: SQLite (logs.db)
AI: Local inference calls
```

### Production (Recommended)

**Frontend**:
- Platform: Vercel, Netlify, or custom
- Build: `npm run build` + `npm start`
- Env: NEXT_PUBLIC_API_URL

**Backend**:
- Platform: Railway, Render, or custom
- Server: Gunicorn + Uvicorn workers
- Database: PostgreSQL (Supabase)
- Env: All keys, Supabase credentials

**Database**:
- Supabase PostgreSQL
- Session pooler for serverless
- Run schema_postgres.sql manually

## Performance Characteristics

### Latency Breakdown

**Paper Search** (8-12s total):
- Semantic rewrite: 1-2s (LLM)
- arXiv API: 2-3s (network)
- ChromaDB ranking: 1-2s (local)
- Agent overhead: 2-4s

**Paper Loading** (5-10s per paper):
- PDF fetch: 2-4s (network)
- PDF parse: 1-2s (pypdf)
- Document creation: 1-2s

**RAG Chat** (10-20s total):
- Query enhancement: 1-2s (LLM)
- Hybrid retrieval: 2-4s (vector+BM25)
- LLM reranking: 2-3s (LLM)
- Generation: 4-8s (LLM with context)
- Metrics persist: <1s

### Bottlenecks
1. **LLM API calls**: Gemini Flash Lite (network latency)
2. **arXiv PDF downloads**: External network
3. **Database writes**: Minimal impact (async possible)

### Optimizations
- **In-memory PDFs**: No disk I/O
- **Hybrid retrieval**: Better recall than vector-only
- **MMR diversity**: Single pass, O(n²) but n small
- **Token compression**: Automatic, only when needed
- **Connection pooling**: PostgreSQL only

## Scalability Considerations

### Current Limitations
- **In-memory sessions**: Lost on restart, not shared across instances
- **Single-threaded**: Python GIL limits (use uvicorn workers)
- **Rate limits**: Gemini API quotas

### Scaling Path
1. **Horizontal Backend**: 
   - Move sessions to Redis/database
   - Use Supabase PostgreSQL
   - Add load balancer

2. **API Optimization**:
   - Cache semantic rewrites
   - Batch arXiv requests
   - Async LLM calls

3. **Database**:
   - PostgreSQL connection pooling
   - Read replicas for metrics
   - Archive old sessions

## Error Handling Strategy

### Frontend
- **Network**: Retry with exponential backoff
- **401**: Clear token, reload (re-auth)
- **429**: Display cooldown message
- **500**: Show error, log to console

### Backend
- **QuotaExhaustedError**: Return 429 with cooldown
- **Session Not Found**: Return 404
- **Validation Error**: Return 422 with details
- **Internal**: Return 500, log traceback

### AI Module
- **API Quota**: Fallback to secondary key
- **arXiv Error**: Return empty results, log
- **PDF Parse Error**: Skip page, continue

## Monitoring & Observability

### Built-in Metrics
- **Per-request**: Tokens, latencies, chunks
- **Per-session**: Total tokens, request count
- **Database**: Persistent storage

### Logs
- **AI Operations**: SessionLogger → JSON files
- **API Requests**: FastAPI console output
- **Errors**: Python traceback to stderr

### Future Enhancements
- Prometheus metrics endpoint
- Structured logging (JSON)
- APM integration (Sentry, DataDog)

## Configuration Management

### Environment Variables (.env)

```bash
# AI
GOOGLE_API_KEY1=primary_chat_key
GOOGLE_API_KEY2=brain_search_key

# Auth
ACCESS_TOKEN=welcometopaperstack1

# Database
DATABASE_TYPE=sqlite|postgres
SQLITE_DB_PATH=logs.db
SUPABASE_HOST=db.xxx.supabase.co
SUPABASE_PASSWORD=...

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Runtime Configuration

**AI Settings** (ai/retrieval.py):
```python
Settings.chunk_size = 768
Settings.chunk_overlap = 128
```

**Quota Limits** (ai/quota_manager.py):
```python
MAX_BRAIN_SEARCHES = 3
MAX_CHAT_MESSAGES = 5
USER_COOLDOWN_MINUTES = 15
```

**CORS Origins** (backend/main.py):
```python
allow_origins = [localhost, local_network_ips, ...]
```

## Testing Strategy

### Development Testing
```bash
# Full stack
./start.sh

# Backend only
cd backend && uvicorn main:app --reload

# Frontend only
cd frontend && npm run dev

# Standalone AI
python main.py
```

### Integration Testing
1. Start servers (`./start.sh`)
2. Open http://localhost:3000
3. Enter token: "welcometopaperstack1"
4. Search papers → Load → Chat

### Database Testing
```bash
# SQLite
python -c "from backend.db.repository import *"

# PostgreSQL
DATABASE_TYPE=postgres python test_supabase.py
```

## Troubleshooting Guide

### Common Issues

**1. 401 on page load**
- Cause: Pre-auth API calls
- Fix: Session creation removed from page mount

**2. CORS errors**
- Cause: OPTIONS blocked by auth
- Fix: Middleware skips OPTIONS first

**3. Messages disappear**
- Cause: No localStorage persistence
- Fix: Auto-save on state change

**4. Session not found**
- Cause: Backend restart (in-memory loss)
- Fix: Frontend auto-creates new session

**5. Quota exhausted**
- Cause: Gemini API limits
- Fix: Fallback key, or wait for cooldown

## Development Workflow

### Setup
```bash
1. Clone repo
2. Copy .env.example → .env
3. Add API keys
4. Install: pip install -r requirements.txt
5. Install: cd frontend && npm install
6. Run: ./start.sh
```

### Making Changes

**Frontend**: Auto-reload (Turbopack)
**Backend**: Auto-reload (--reload flag)
**AI Module**: Restart backend to pick up changes

### Adding Features

**New Endpoint**:
1. Add to backend/models.py (Pydantic models)
2. Implement in backend/main.py (@app.post decorator)
3. Add to frontend/lib/api.ts (API client)
4. Call from SessionContext or component

**New AI Feature**:
1. Implement in ai/ module
2. Export in ai/__init__.py
3. Bridge in ai/web_interface.py
4. Call from backend endpoint

## Documentation Index

- **AI Module**: [ai/README.md](ai/README.md)
- **Backend API**: [backend/README.md](backend/README.md)
- **Database Layer**: [backend/db/README.md](backend/db/README.md)
- **Frontend**: [frontend/README.md](frontend/README.md)
- **Auth System**: [AUTH_GUIDE.md](AUTH_GUIDE.md)
- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Supabase Setup**: [SUPABASE_SETUP.md](SUPABASE_SETUP.md)

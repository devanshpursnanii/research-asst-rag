# AI Module - Technical Documentation

## Overview
The AI module implements a dual-system architecture for research paper discovery and multi-paper RAG (Retrieval-Augmented Generation) chat. It combines agent-based search with intelligent retrieval routing.

## Architecture

### Core Components

```
ai/
├── brain.py              # Agent-based paper discovery system
├── rag.py                # Multi-paper RAG with task routing
├── retrieval.py          # Hybrid retrieval & query enhancement
├── fetcher.py            # arXiv paper ingestion
├── api_config.py         # Dual API key management with fallback
├── logger.py             # Session logging for RAG operations
├── quota_manager.py      # Usage limits and cooldown tracking
├── metrics_collector.py  # Token counting and metrics
├── token_counter.py      # tiktoken-based token counting
└── web_interface.py      # FastAPI integration layer
```

## System 1: Paper Brain (Discovery)

**Purpose**: Find and rank relevant research papers from arXiv

### Flow

1. **Semantic Rewrite** (brain.py:semantic_rewrite)
   - Input: Raw user query
   - Process: LLM optimizes query for arXiv search (Gemini 2.5 Flash Lite)
   - Output: Keyword-focused search string
   - Special case: Detects paper titles and searches verbatim

2. **arXiv Search** (brain.py:search_papers)
   - Query arXiv API with semantic query
   - Fetch 15 papers with metadata (title, authors, abstract, arXiv ID)
   - Extract paper details from Atom XML feed

3. **ChromaDB Ranking** (brain.py:rank_with_chroma)
   - Initialize ChromaDB with Google embedding function (text-embedding-004)
   - Index all 15 paper abstracts
   - Rerank by semantic similarity to original query
   - Return top 10 papers

4. **Agent Loop** (brain.py:paper_brain_interface)
   - User interacts with ReActAgent (max 3 messages for cost control)
   - Tools available:
     - `search_more_papers()`: Refine and search again
     - `load_selected_papers()`: Load PDFs for RAG (1-10 indices)
   - State management via global BrainState class

5. **Paper Loading** (fetcher.py:ingest_arxiv_paper)
   - Fetch PDF from arXiv by ID
   - Parse with pypdf (in-memory, no disk writes)
   - Create LlamaIndex Document per page with metadata
   - Return list of Documents ready for indexing

### Key Configurations

- **LLM**: Gemini 2.5 Flash Lite (GOOGLE_API_KEY2)
- **Embeddings**: text-embedding-004 (768 dims)
- **Message Limit**: 3 per session (quota_manager.py)
- **Search Limit**: 3 per session
- **Top Papers**: 10 displayed, 15 searched

## System 2: Multi-Paper RAG (Chat)

**Purpose**: Answer questions across multiple loaded papers with intelligent retrieval

### Architecture Layers

#### 1. Retrieval Layer (retrieval.py)

**Hybrid Retrieval**:
- Vector search (semantic similarity)
- BM25 search (keyword matching)
- Reciprocal rank fusion (QueryFusionRetriever)
- Task type awareness:
  - `RETRIEVAL_DOCUMENT` for indexing
  - `RETRIEVAL_QUERY` for searching

**Query Enhancement** (enhance_query_for_rag):
- Generate 2 query variations with LLM
- Expand abbreviations, add technical synonyms
- Each variation retrieves independently
- Deduplicate by node ID

**LLM Reranking** (llm_rerank_chunks):
- Rerank top 20 chunks by relevance
- LLM scores and orders chunks
- Return top N most relevant

#### 2. Task Routing (rag.py)

**Router Query Engine** classifies queries into 4 task types:

1. **Question Answering** (QA)
   - Queries: "What is...", "How does...", "Why..."
   - Retrieval: top_k=10, top_n=5, λ=0.8 (high relevance)
   - Focus: Precise answers to specific questions

2. **Summarization**
   - Queries: "Summarize...", "Give overview..."
   - Retrieval: top_k=15, top_n=6, λ=0.6 (balanced)
   - Focus: Comprehensive coverage

3. **Comparison**
   - Queries: "Compare...", "Difference between...", "Contrast..."
   - Retrieval: top_k=20, top_n=8, λ=0.5 (high diversity)
   - Focus: Multiple papers, diverse perspectives

4. **Explanation**
   - Queries: "Explain...", "How does X work..."
   - Retrieval: top_k=12, top_n=6, λ=0.7 (moderate relevance)
   - Focus: In-depth understanding

**Parameters**:
- `top_k`: Initial retrieval count
- `top_n`: Final chunks after MMR
- `λ`: Relevance vs diversity (0-1, higher=more relevance)

#### 3. Paper-Aware MMR (rag.py:apply_mmr_diversity)

**Maximal Marginal Relevance** ensures diverse paper coverage:

```
MMR Score = λ × relevance - (1-λ) × max_similarity

Similarity Calculation:
- Same paper (same arxiv_id): similarity = 1.0
- Different paper: similarity = 0.3
```

**Algorithm**:
1. Select highest relevance chunk first
2. For each remaining chunk:
   - Calculate MMR score balancing relevance and paper diversity
   - Penalize chunks from already-selected papers
3. Iteratively select until top_n reached

**Result**: Diverse set of chunks from multiple papers

#### 4. Token Compression (rag.py:compress_if_needed)

- **Limit**: 18,000 tokens max context
- **Estimation**: 1 token ≈ 4 characters
- **Compression**: Truncate each chunk proportionally if exceeded
- **Trigger**: Automatic when total exceeds limit

### Response Generation

**Citation Format**:
- Inline citations: [Paper Title, Page X]
- Flowing paragraphs (no bullet points)
- Multi-paper synthesis

**Prompt Template** (retrieval.py:get_citation_prompt):
```
Context information from research papers:
---------------------
{context_str}
---------------------
Using the context above, answer the query...
Answer in clear, flowing paragraphs with citations inline.
Format citations as [Paper Title, Page X]...
```

## API Configuration & Fallback

### Dual API Key System (api_config.py)

**Architecture**:
- `GOOGLE_API_KEY1`: Primary (Paper Chat RAG)
- `GOOGLE_API_KEY2`: Secondary (Paper Brain search)
- **Fallback**: KEY2 → KEY1 → QuotaExhaustedError

**Functions**:
- `get_brain_llm()`: Returns LLM with KEY2
- `get_chat_llm()`: Returns LLM with KEY1
- `try_with_fallback()`: Automatic fallback on quota exhaustion

**Error Detection**:
- Catches "resource", "quota", "exhausted", "429" in error messages
- Retries with fallback key
- Raises `QuotaExhaustedError` if both exhausted

## Session Logging (logger.py)

**Purpose**: Track all LLM calls, embeddings, and retrieved chunks

### SessionLogger Class

**Initialization**:
```python
logger = SessionLogger(
    query_title="User's query",
    mode="paper_brain"  # or "multi_paper_rag"
)
```

**Logged Data**:
1. **RAG Chunks**: Retrieved content with scores, sources, metadata
2. **Embedding Calls**: Input text, token count, model, latency
3. **LLM Calls**: Prompts, completions, tokens, latency

**Output**: JSON file in `logs/session_YYYYMMDD_HHMMSS_XXXX.json`

**Structure**:
```json
{
  "session_id": "session_...",
  "title": "User query",
  "mode": "multi_paper_rag",
  "timestamp_start": "ISO8601",
  "timestamp_end": "ISO8601",
  "rag_chunks": [...],
  "api_calls_embeddings": [...],
  "api_calls_llm": [...]
}
```

## Quota Management (quota_manager.py)

### QuotaTracker

**Limits**:
- Brain searches: 3 per session
- Chat messages: 5 per session
- User cooldown: 15 minutes
- API cooldown: 30 minutes

**Methods**:
- `can_use_brain()`: Returns (allowed, minutes_left)
- `can_use_chat()`: Returns (allowed, minutes_left)
- `increment_brain()`: +1 brain search
- `increment_chat()`: +1 chat message
- `mark_api_exhausted()`: Start 30min cooldown

**Cooldown Reset**: Automatic when time expires

## Metrics Collection (metrics_collector.py)

**Purpose**: Collect metrics WITHOUT persisting (repository's job)

### Functions

1. **collect_chunk_metrics(nodes)**:
   - Input: Retrieved NodeWithScore list
   - Output: (chunk_metrics_list, total_chunk_tokens)
   - Per-chunk data: index, paper_title, preview, token_count

2. **collect_request_metrics(...)**:
   - Aggregates all request metrics
   - Returns dict ready for DB insertion
   - Includes: prompt_tokens, chunk_tokens, completion_tokens, latencies

## Token Counting (token_counter.py)

**Encoder**: tiktoken cl100k_base (GPT-4 tokenizer)

**Functions**:
- `count_tokens(text)`: Single text → token count
- `count_tokens_batch(texts)`: List of texts → list of counts

**Global Encoder**: Lazy-loaded singleton for performance

## Integration Points

### With Backend (web_interface.py)

Functions that bridge AI and FastAPI:
- `web_brain_search()`: Paper Brain search endpoint
- `web_brain_load_papers()`: Load papers endpoint
- `web_chat_query()`: RAG chat endpoint

Each function:
1. Takes session ID and user input
2. Retrieves session from memory
3. Calls AI module functions
4. Returns structured response for API

### With Database

- Metrics collected but not persisted by AI module
- Backend repository layer handles DB writes
- Clean separation: AI focuses on inference, backend on storage

## Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY1=primary_api_key    # Paper Chat
GOOGLE_API_KEY2=secondary_api_key  # Paper Brain

# Optional
CHROMA_DB_PATH=./chroma_db         # ChromaDB storage
```

### Settings (retrieval.py)

```python
Settings.llm = GoogleGenAI(...)
Settings.embed_model = GoogleGenAIEmbedding(...)
Settings.chunk_size = 768
Settings.chunk_overlap = 128
```

## Data Flow

### Paper Discovery Flow
```
User Query 
  → semantic_rewrite() [LLM]
  → search_papers() [arXiv API]
  → rank_with_chroma() [ChromaDB]
  → ReActAgent loop [LLM + Tools]
  → load_selected_papers() [arXiv PDF]
  → Documents ready for RAG
```

### RAG Chat Flow
```
User Question
  → enhance_query_for_rag() [2 variations, LLM]
  → create_hybrid_retriever() [Vector + BM25]
  → retrieve() [Multiple queries, deduplicate]
  → llm_rerank_chunks() [LLM scoring]
  → apply_mmr_diversity() [Paper-aware selection]
  → compress_if_needed() [Token limit]
  → query_engine.query() [LLM with context]
  → Response with citations
```

## Performance Optimizations

1. **In-Memory PDF Processing**: No disk I/O (fetcher.py)
2. **Query Variations**: 2 queries instead of 1 for better recall
3. **Hybrid Search**: Vector + BM25 fusion
4. **LLM Reranking**: Precision boost on top candidates
5. **MMR Diversity**: Prevents single-paper domination
6. **Token Compression**: Automatic context management
7. **API Fallback**: Seamless key switching on quota
8. **Lazy Encoder**: Single tiktoken instance

## Error Handling

- **QuotaExhaustedError**: Both API keys exhausted
- **ConnectionError**: arXiv API or PDF fetch fails
- **ValidationError**: Invalid paper IDs or queries
- **TimeoutError**: Slow API responses

## Testing

Run standalone:
```bash
python main.py
```

Integrated with backend:
```bash
./start.sh  # Starts FastAPI + Next.js
```

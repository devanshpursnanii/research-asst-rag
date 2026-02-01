PaperBrain Pipeline (arXiv Search)
User Query → Results

Query Rewriting (only in topic mode)

LLM (Gemini 2.5 Flash) rewrites query with technical terms, removes filler words
Title mode: skips rewriting, uses original query verbatim
arXiv API Search

Title mode: ti:"query" search with capitalization variants
Topic mode: all:semantic_query search
Fetches 15 results max
Semantic Ranking (ChromaDB)

Embed abstracts with text-embedding-004 (RETRIEVAL_DOCUMENT)
Query against user's original query (preserves intent)
Distance-based scoring (1 - distance)
Results

Top 10 papers with normalized relevance scores (0-1)

---------------------------------------------------

PaperChat Pipeline (RAG on Loaded Papers)
User Query → Answer

Multi-Query Generation

LLM generates 2 semantic variations of user query
Hybrid Retrieval (per variation)

Vector search: ChromaDB with text-embedding-004 (RETRIEVAL_QUERY task type)
BM25: Keyword-based retrieval
RRF (Reciprocal Rank Fusion): Combines both scores
LLM Reranking

Top 20 chunks sent to LLM for relevance scoring
Returns reordered top N chunks
MMR Diversification

λ=0.85 (relevance) vs 0.15 (diversity)
Paper-aware: penalizes same-paper chunks for cross-paper coverage
Outputs 4-8 chunks (task-dependent)
Task Routing (LLMSingleSelector)

Routes to: QA (5 chunks), Summarize (8 chunks), Compare (8 chunks), or Explain (6 chunks)
Each has custom top_k, top_n, λ, max_tokens, and prompts
Answer Generation

Gemini 2.5 Flash generates response with inline citations
Format: [Paper Title, Page X]
Techniques Used: Multi-query expansion, Dense retrieval (embeddings), BM25, RRF, LLM reranking, MMR, Router pattern

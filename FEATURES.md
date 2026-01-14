## Features

### Intelligent Paper Discovery
- **Dual Search Modes**: Title-exact or topic-semantic search
- **LLM Query Optimization**: Gemini 2.5 Flash Lite query expansion for better discovery
- **Semantic Ranking**: ChromaDB vector search with relevance scoring
- **Quota Management**: 3 searches per session with 15-min cooldown

### Citation-Grounded Chat
- **Multi-Query Retrieval**: 2 semantic variations with hybrid vector + BM25 search
- **LLM Reranking**: Top 20 chunks reranked for relevance
- **MMR Diversification**: λ=0.85 balance between relevance and cross-paper diversity
- **Task-Aware Routing**: QA, Explain, Summarize, or Compare with specialized prompts
- **Automatic Citations**: Every response includes source paper and page numbers
- **Quota Management**: 5 messages per session with 15-min cooldown

### Production Architecture
- **FastAPI Backend**: Async endpoints with proper error handling
- **Next.js Frontend**: Server-side rendering with React 19
- **Session Persistence**: In-memory sessions 
- **Auto-Recovery**: 404 session recovery with seamless recreation
- **Comprehensive Logging**: LLM calls and RAG chunks tracked per session

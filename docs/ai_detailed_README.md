# Paper Brain AI System

Intelligent arXiv paper discovery and multi-paper RAG system with agent-based interaction.

## Project Structure

```
project_physics/
├── ai/                     # Main AI package
│   |── __init__.py         # Package exports
|   |── README.md           # This file
│   |── brain.py            # Agent-based paper discovery
│   |── rag.py              # Multi-paper RAG with intelligent routing
│   |── retrieval.py        # Hybrid retrieval & configuration
│   |__ fetcher.py          # arXiv paper ingestion
├── main.py                 # Main entry point
├── requirements.txt        # Dependencies
├── .env                    # API keys


## Quick Start

```bash
# Run the system
python3 main.py
```

## AI Package Components

### `brain.py` - Paper Discovery
- Agent-based arXiv search with semantic query rewriting
- ChromaDB-powered abstract ranking
- 3-message limit for cost optimization
- LLM-based query routing (QUIT/SWITCH/AGENT)

### `rag.py` - Multi-Paper RAG
- Intelligent task routing (QA/Summarize/Compare/Explain)
- Paper-aware MMR for cross-paper diversity
- Token compression
- Cross-paper citations

### `retrieval.py` - Shared Utilities
- Hybrid retrieval (Vector + BM25)
- Global LLM/embedding configuration
- Custom citation prompts

### `fetcher.py` - arXiv Integration
- Title-based paper search
- In-memory PDF processing
- Document metadata extraction

## 🔧 Usage

### As a Package

```python
from ai import (
    paper_brain_interface,
    multi_paper_rag_with_documents,
    configure_settings,
    ingest_arxiv_paper
)

# Run paper discovery
documents = asyncio.run(paper_brain_interface())

# Query loaded papers
response = multi_paper_rag_with_documents(documents, "Your question")
```

### Standalone

```bash
python3 main.py
```

## Future Expansion

The consolidated `ai/` package structure allows for easy expansion:

```
future_structure/
├── backend/
│   └── api/
│       └── app.py          # FastAPI/Flask wrapper for ai package
├── frontend/
│   └── ui/
│       └── app.tsx         # React/Next.js frontend
└── ai/                      # Core logic (unchanged)
    ├── brain.py
    ├── rag.py
    ├── retrieval.py
    └── fetcher.py
```

## API Call Optimization

- **Discovery Phase**: ~10K tokens per session
- **RAG Setup**: ~500-1500 tokens/page (one-time)
- **RAG Queries**: ~3.5K-8.5K tokens per query

Total session estimate: ~65K tokens (3 papers, 5 questions)

## Environment Variables

```.env
GOOGLE_API_KEY=your_gemini_api_key_here
```


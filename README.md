# Physics Paper Search Engine

Advanced semantic search system for physics research papers with LLM-powered query expansion and multi-stage retrieval.

## Features

- **LLM Query Expansion**: Physics-aware query expansion using Gemini 2.5 Flash
- **Dense Retrieval**: Fast vector search using ChromaDB and sentence-transformers
- **Cross-Encoder Re-Ranking**: Improved relevance with cross-encoder models
- **MMR Diversification**: Maximal Marginal Relevance for diverse results
- **Persistent Database**: Vector database persists across runs

## Pipeline Flow

```
Query 
  → LLM Query Expansion (Gemini 2.5 Flash)
  → Dense Retrieval (ChromaDB)
  → Cross-Encoder Re-Ranking
  → MMR Diversification
  → Top-K Papers (default k=5)
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up Google API Key:
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

Or create a `.env` file (see `.env.example`)

3. Run the search:
```bash
python3 index/db.py
```

## Usage

The database will be automatically created on first run and persisted in `./chroma_db`. Subsequent runs will load the existing database.

Edit the query in `index/db.py` to search for different topics.

## Dataset

Place your `papers.csv` in the `data/` directory with columns:
- title
- abstract
- categories
- created
- id
- doi


                    USER QUERY
                        ↓
        "Compare attention in Transformer vs BERT"
                        ↓
                ┌───────────────┐
                │  ROUTER (LLM) │
                │  Reads query  │
                │  & tool descs │
                └───────┬───────┘
                        ↓
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
   [QA Engine]   [Compare Engine]  [Summarize]  [Explain]
                        ↓ SELECTED
                        ↓
            ┌───────────────────────┐
            │ TaskSpecificRetriever │
            │ (top_k=20, top_n=8)  │
            └───────────┬───────────┘
                        ↓
            ┌───────────────────────┐
            │  Hybrid Retrieval     │
            │  Vector + BM25        │
            └───────────┬───────────┘
                        ↓
                  20 chunks
                        ↓
            ┌───────────────────────┐
            │  MMR Diversity        │
            │  Paper-aware selection│
            └───────────┬───────────┘
                        ↓
                  8 chunks (4 from each paper)
                        ↓
            ┌───────────────────────┐
            │  Compression Check    │
            │  Fit in token budget  │
            └───────────┬───────────┘
                        ↓
                  8 chunks ready
                        ↓
            ┌───────────────────────┐
            │  Query Engine         │
            │  Build prompt + LLM   │
            └───────────┬───────────┘
                        ↓
                FINAL RESPONSE
          "Both papers use self-attention
           mechanisms, but with key 
           differences... [Transformer, Page 3]
           ... [BERT, Page 5]"
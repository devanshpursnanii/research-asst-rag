# PaperStack

<div align="center">

**AI-Powered Research Assistant with Citation-Grounded Responses**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.1+-black.svg)](https://nextjs.org/)

[Features](#features) • [Architecture](#architecture) • [Installation](#installation) • [Usage](#usage) • [API](#api-documentation) • [Contributing](#contributing)

</div>

---

## Overview

PaperStack is a production-grade RAG (Retrieval-Augmented Generation) system for academic research. It combines intelligent paper discovery with citation-grounded question answering, ensuring every response is traceable to exact sources.

### Key Components

- **PaperBrain** — Semantic paper discovery and ranking from arXiv
- **PaperChat** — Citation-enforced Q&A over selected research papers
- **Session Management** — Persistent sessions with quota limits and activity tracking

---

## Architecture

### Technical Stack

**Backend**
- FastAPI + LlamaIndex
- Google Gemini 2.5 Flash (generation)
- text-embedding-004 (embeddings)
- ChromaDB (vector store)
- BM25 (keyword search)

**Frontend**
- Next.js 16 + React 19
- TypeScript + Tailwind CSS
- Lucide Icons

### RAG Pipeline

```
User Query
  ↓
Multi-Query Generation (2 variations)
  ↓
Hybrid Retrieval (Vector + BM25)
  ↓
Reciprocal Rank Fusion
  ↓
LLM Reranking (Top 20)
  ↓
MMR Diversification (λ=0.85)
  ↓
Response Generation + Citations
```

### Paper Search Pipeline

```
User Query
  ↓
[Title Mode] Original Query + Caps Variants → arXiv ti: search
[Topic Mode] LLM Query Expansion → arXiv all: search
  ↓
Semantic Ranking (ChromaDB)
  ↓
Score Normalization (0-100)
  ↓
Top 10 Papers
```

---

## Installation

### Prerequisites

- **Python 3.10+** (tested with 3.10)
- **Node.js 18+** (tested with 18.x)
- **npm** or **yarn**
- **Google API Key** ([Get one here](https://aistudio.google.com/app/apikey))

### 1. Clone Repository

```bash
git clone https://github.com/devanshpursnanii/research-asst-rag.git
cd research-asst-rag
```

### 2. Backend Setup

#### Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or with virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Configure API Keys

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:

```bash
GOOGLE_API_KEY=your_actual_api_key_here
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

---

## Usage

### Option 1: Quick Start (Recommended)

Use the provided startup script to run both servers:

```bash
chmod +x start.sh
./start.sh
```

This will:
- ✓ Start FastAPI backend on `http://localhost:8000`
- ✓ Start Next.js frontend on `http://localhost:3000`
- ✓ Auto-reload on file changes

**Access the app**: Open [http://localhost:3000](http://localhost:3000)

Press `Ctrl+C` to stop both servers.

### Option 2: Run Individually

#### Terminal 1 - Backend

```bash
# From project root
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2 - Frontend

```bash
cd frontend
npm run dev
```

### Option 3: Production Build

#### Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm run build
npm start
```

---

## Usage Guide

### 1. Search Papers
- Choose **Title Search** for exact paper titles (e.g., "Attention Is All You Need")
- Choose **Topic Search** for broader discovery (e.g., "transformer architectures")
- PaperBrain semantically ranks results and displays top 10 papers
- **Quota**: 3 searches per session

### 2. Load Papers
- Select papers using checkboxes
- Click **"Load Selected Papers"** to download and process PDFs
- Papers are parsed and indexed for retrieval

### 3. Chat with Papers
- Ask questions in PaperChat (e.g., "What is the attention mechanism?")
- Receive answers with **automatic citations** [Paper Title, Page X]
- Click citations to see exact source text
- **Quota**: 5 messages per session

### 4. Monitor Activity
- View loaded papers in **Session Activity** sidebar
- Track quota usage (searches remaining, messages remaining)
- Check cooldown timers when quotas exhausted

---

## API Documentation

Once running, access interactive API docs:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/session/create` | Create new session |
| `POST` | `/brain/search` | Search arXiv papers |
| `POST` | `/brain/load` | Load papers for RAG |
| `POST` | `/chat/message` | Query loaded papers |
| `GET` | `/session/{id}/info` | Get session info & logs |

---

## Project Structure

```
research-project/
├── backend/
│   ├── main.py              # FastAPI app & endpoints
│   ├── models.py            # Pydantic models
│   └── session.py           # Session management
├── frontend/
│   ├── app/                 # Next.js pages
│   ├── components/          # React components
│   ├── contexts/            # React contexts
│   └── lib/                 # API client
├── ai/
│   ├── web_interface.py     # Main RAG logic
│   ├── rag.py               # Multi-paper RAG engine
│   ├── query_engine.py      # Task-aware query routing
│   ├── quota_manager.py     # Quota & cooldown logic
│   └── logger.py            # Session logging
├── requirements.txt         # Python dependencies
├── start.sh                 # Startup script
└── .env.example            # Environment template
```

---

## Configuration

### Quota Limits

Edit `ai/quota_manager.py`:

```python
MAX_BRAIN_SEARCHES = 3      # Searches per session
MAX_CHAT_MESSAGES = 5       # Chat messages per session
USER_COOLDOWN_MINUTES = 15  # Cooldown after exhaustion
```

### RAG Parameters

Edit `ai/rag.py`:

```python
top_k_retrieve = 20         # Chunks to retrieve
top_k_rerank = 10           # Chunks after reranking
similarity_threshold = 0.1  # Minimum relevance score
```

### Session Retention

Edit `backend/main.py`:

```python
max_age_hours = 48          # Auto-cleanup old sessions
```

---

## Troubleshooting

### Backend Issues

**"ModuleNotFoundError"**
```bash
pip install -r requirements.txt --force-reinstall
```

**"GOOGLE_API_KEY not found"**
- Ensure `.env` file exists in root directory
- Check key is properly formatted (no quotes, no spaces)

**Port 8000 already in use**
```bash
# Find process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Frontend Issues

**"Module not found"**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Port 3000 already in use**
```bash
# Find process on port 3000
lsof -ti:3000 | xargs kill -9
```

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details

---

## Acknowledgments

- **arXiv**: Research papers sourced from [arXiv.org](https://arxiv.org)
- **Google AI**: Powered by Gemini 2.5 Flash and text-embedding-004
- **LlamaIndex**: RAG framework
- **ChromaDB**: Vector database

---

## Developer

**Devansh Pursnani**  
Computer Science Engineering Student  
Applied AI • Language Models • Retrieval Systems

[![GitHub](https://img.shields.io/badge/GitHub-devanshpursnanii-181717?logo=github)](https://github.com/devanshpursnanii)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin)](https://www.linkedin.com/in/devansh-pursnani-946853231/)
[![Email](https://img.shields.io/badge/Email-devansh.pursnani23%40spit.ac.in-EA4335?logo=gmail)](mailto:devansh.pursnani23@spit.ac.in)

---


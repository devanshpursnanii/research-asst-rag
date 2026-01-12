"""
AI Package: Unified paper discovery and RAG system

Components:
- brain: Agent-based arXiv paper discovery
- rag: Multi-paper RAG with intelligent routing
- retrieval: Hybrid retrieval and configuration
- fetcher: arXiv paper ingestion
"""

from .brain import paper_brain_interface
from .rag import multi_paper_rag_with_documents
from .retrieval import configure_settings, create_hybrid_retriever
from .fetcher import ingest_arxiv_paper

__all__ = [
    'paper_brain_interface',
    'multi_paper_rag_with_documents',
    'configure_settings',
    'create_hybrid_retriever',
    'ingest_arxiv_paper'
]

"""
Web-Friendly Interface for Paper Brain AI

Wraps CLI functions with JSON responses for FastAPI integration.
Returns structured data instead of printing to console.
"""

from typing import List, Dict, Any, Optional
import asyncio
import time
import requests
import feedparser
import chromadb
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
from llama_index.core import Document
from llama_index.core import VectorStoreIndex
import os
from .api_config import get_brain_llm, get_chat_llm, QuotaExhaustedError
from .fetcher import ingest_arxiv_paper
from .rag import multi_paper_rag_with_documents, multi_paper_rag_with_documents_with_metrics
from .logger import SessionLogger


async def web_brain_search(query: str, search_mode: str = "topic", logger: Optional[SessionLogger] = None) -> Dict[str, Any]:
    """
    Search arXiv papers with semantic rewriting and ranking.
    
    Args:
        query: User's research query
        search_mode: 'title' for title-only search, 'topic' for general search
        logger: Optional session logger
        
    Returns:
        {
            "thinking_steps": [
                {"step": "rewriting", "status": "complete", "result": "optimized query"},
                {"step": "searching", "status": "complete", "result": "15 papers found"},
                {"step": "ranking", "status": "complete", "result": "10 papers ranked"}
            ],
            "papers": [
                {
                    "title": "...",
                    "authors": "...",
                    "abstract": "...",
                    "arxiv_id": "...",
                    "url": "...",
                    "score": 0.95
                }
            ],
            "error": None
        }
    """
    thinking_steps = []
    
    try:
        # Step 1: Semantic rewrite (ONLY for topic mode)
        semantic_query = query.strip()
        
        if search_mode == "topic":
            thinking_steps.append({"step": "rewriting", "status": "in_progress", "result": None})
            
            llm = get_brain_llm(temperature=0.1)
            prompt = f"""You are a research paper search optimizer. Rewrite the user's query into an optimal arXiv search string.

CONSTRAINTS:
- Use technical terms and keywords
- use clean punctutation marks 
- Remove filler words (e.g., "papers about", "research on")
- Focus on core concepts
- Keep domain-specific terminology

USER QUERY: "{query}"

OUTPUT (search string only, no explanation):"""
            
            start_time = time.time()
            response = await llm.acomplete(prompt)
            latency_ms = (time.time() - start_time) * 1000
            
            semantic_query = str(response).strip().strip('"')
            
            # Log LLM call
            if logger:
                logger.log_llm_call(
                    call_type="semantic_rewrite",
                    input_text=query,
                    output_text=semantic_query,
                    prompt_preview=prompt,
                    latency_ms=latency_ms,
                    temperature=0.1
                )
            
            thinking_steps[-1] = {"step": "rewriting", "status": "complete", "result": semantic_query}
        else:
            # Title mode: Use original query for better matching
            thinking_steps.append({"step": "preparing", "status": "complete", "result": f"Using exact title search: {query}"})
        
        # Step 2: Search arXiv with mode-based query
        thinking_steps.append({"step": "searching", "status": "in_progress", "result": None})
        
        base_url = 'http://export.arxiv.org/api/query'
        
        if search_mode == "title":
            # Title search: Use ORIGINAL query with normalization
            # Try multiple variations for better results
            search_queries = [
                f'ti:"{query}"',  # Exact as entered
                f'ti:"{query.title()}"',  # Title Case
            ]
            
            feed = None
            for search_q in search_queries:
                params = {
                    'search_query': search_q,
                    'start': 0,
                    'max_results': 15,
                    'sortBy': 'relevance',
                    'sortOrder': 'descending'
                }
                
                response = requests.get(base_url, params=params, timeout=15)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                
                if feed.entries:
                    break  # Found results, stop trying
            
            # Fallback to topic search if title search found nothing
            if not feed or not feed.entries:
                thinking_steps[-1] = {"step": "searching", "status": "in_progress", "result": "No exact title match, trying broader search..."}
                params = {
                    'search_query': f'all:{query}',
                    'start': 0,
                    'max_results': 15,
                    'sortBy': 'relevance',
                    'sortOrder': 'descending'
                }
                response = requests.get(base_url, params=params, timeout=15)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
        else:
            # Topic mode: Use semantic rewritten query
            params = {
                'search_query': f'all:{semantic_query}',
                'start': 0,
                'max_results': 15,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        
        if not feed.entries:
            return {
                "thinking_steps": thinking_steps,
                "papers": [],
                "error": "No papers found. Try a different query."
            }
        
        # Extract paper data
        papers = []
        for entry in feed.entries:
            arxiv_id = entry.id.split('/abs/')[-1]
            papers.append({
                'title': entry.title.replace('\n', ' ').strip(),
                'abstract': entry.summary.replace('\n', ' ').strip(),
                'authors': ', '.join([a.name for a in entry.authors[:3]]),
                'arxiv_id': arxiv_id,
                'url': entry.link
            })
        
        thinking_steps[-1] = {"step": "searching", "status": "complete", "result": f"{len(papers)} papers found"}
        
        # Step 3: Rank by relevance using ChromaDB
        thinking_steps.append({"step": "ranking", "status": "in_progress", "result": None})
        
        client = chromadb.Client()
        google_ef = GoogleGenerativeAiEmbeddingFunction(
            api_key=os.getenv("GOOGLE_API_KEY2"),
            model_name="models/text-embedding-004"
        )
        
        collection_name = f"papers_{int(time.time() * 1000000)}"
        collection = client.create_collection(
            name=collection_name,
            embedding_function=google_ef
        )
        
        # Add abstracts to collection
        for i, paper in enumerate(papers):
            collection.add(
                documents=[paper['abstract']],
                metadatas=[{'index': i}],
                ids=[f"paper_{i}"]
            )
        
        # Query for top 10 matches using ORIGINAL query (not rewritten)
        # This preserves user intent and improves score alignment
        results = collection.query(
            query_texts=[query],  # Use original query, not semantic_query
            n_results=min(10, len(papers))
        )
        
        # Build ranked list
        ranked = []
        for i, doc_id in enumerate(results['ids'][0]):
            idx = results['metadatas'][0][i]['index']
            paper = papers[idx].copy()
            paper['score'] = round(1.0 - results['distances'][0][i], 3)
            ranked.append(paper)
        
        thinking_steps[-1] = {"step": "ranking", "status": "complete", "result": f"{len(ranked)} papers ranked"}
        
        return {
            "thinking_steps": thinking_steps,
            "papers": ranked,
            "error": None
        }
        
    except QuotaExhaustedError as e:
        return {
            "thinking_steps": thinking_steps,
            "papers": [],
            "error": f"quota_exhausted: {e.message}"
        }
    except Exception as e:
        return {
            "thinking_steps": thinking_steps,
            "papers": [],
            "error": f"error: {str(e)}"
        }


async def web_brain_load_papers(paper_ids: List[str], logger: Optional[SessionLogger] = None) -> Dict[str, Any]:
    """
    Load selected papers from arXiv and prepare for RAG.
    
    Args:
        paper_ids: List of arXiv IDs to load
        logger: Optional session logger
        
    Returns:
        {
            "thinking_steps": [
                {"step": "loading", "status": "complete", "result": "3 papers loaded"}
            ],
            "documents": [Document objects],
            "loaded_papers": ["paper_title1", "paper_title2", ...],
            "error": None
        }
    """
    thinking_steps = []
    documents = []
    loaded_papers = []
    
    try:
        thinking_steps.append({"step": "loading", "status": "in_progress", "result": None})
        
        for arxiv_id in paper_ids:
            try:
                # Run in thread pool to avoid blocking event loop
                docs = await asyncio.to_thread(ingest_arxiv_paper, arxiv_id)
                documents.extend(docs)
                # Get paper title from first document's metadata
                if docs and hasattr(docs[0], 'metadata'):
                    loaded_papers.append(docs[0].metadata.get('title', arxiv_id))
                else:
                    loaded_papers.append(arxiv_id)
            except Exception as e:
                print(f"⚠️  Failed to load {arxiv_id}: {e}")
        
        thinking_steps[-1] = {"step": "loading", "status": "complete", "result": f"{len(documents)} documents loaded from {len(loaded_papers)} papers"}
        
        return {
            "thinking_steps": thinking_steps,
            "documents": documents,
            "loaded_papers": loaded_papers,
            "error": None if documents else "Failed to load any papers"
        }
        
    except Exception as e:
        return {
            "thinking_steps": thinking_steps,
            "documents": [],
            "loaded_papers": [],
            "error": f"error: {str(e)}"
        }


async def web_chat_query(query: str, documents: List[Document], logger: Optional[SessionLogger] = None) -> Dict[str, Any]:
    """
    Query loaded papers using RAG with intelligent routing.
    
    Args:
        query: User's question
        documents: Loaded paper documents
        logger: Optional session logger
        
    Returns:
        {
            "thinking_steps": [...],
            "answer": "...",
            "citations": [...],
            "metrics": {
                "query": str,
                "prompt_tokens": int,
                "total_chunk_tokens": int,
                "completion_tokens": int,
                "llm_latency_ms": float,
                "total_latency_ms": float,
                "chunks": [...]
            },
            "error": None
        }
    """
    thinking_steps = []
    
    try:
        if not documents:
            return {
                "thinking_steps": [],
                "answer": "",
                "citations": [],
                "metrics": None,
                "error": "No papers loaded. Please load papers first."
            }
        
        # Indicate routing
        thinking_steps.append({"step": "routing", "status": "in_progress", "result": None})
        
        # Call RAG function in thread pool to avoid event loop conflicts
        start_time = time.time()
        rag_result = await asyncio.to_thread(multi_paper_rag_with_documents_with_metrics, documents, query, logger)
        total_latency_ms = (time.time() - start_time) * 1000
        
        thinking_steps[-1] = {"step": "routing", "status": "complete", "result": "query routed"}
        thinking_steps.append({"step": "generating", "status": "complete", "result": "answer generated"})
        
        # Extract citations from response - handle multiple formats
        import re
        response_text = str(rag_result['response'])
        
        # Try standard format: [Paper Title, Page X]
        citations_raw = re.findall(r'\[([^,\]]+),\s*Page\s+(\d+)\]', response_text, re.IGNORECASE)
        
        # Also try without "Page" prefix: [Paper Title, 5]
        if not citations_raw:
            citations_raw = re.findall(r'\[([^,\]]+),\s*(\d+)\]', response_text)
        
        citations = [{"paper": paper.strip(), "page": int(page)} for paper, page in citations_raw]
        unique_citations = list({f"{c['paper']}-{c['page']}": c for c in citations}.values())
        
        # Build metrics dict
        from .metrics_collector import collect_request_metrics
        metrics = collect_request_metrics(
            query=query,
            answer=str(rag_result['response']),
            chunks=rag_result['chunks'],
            total_chunk_tokens=rag_result['total_chunk_tokens'],
            llm_latency_ms=rag_result['llm_latency_ms'],
            total_latency_ms=total_latency_ms
        )
        
        return {
            "thinking_steps": thinking_steps,
            "answer": str(rag_result['response']),
            "citations": unique_citations,
            "metrics": metrics,
            "error": None
        }
        
    except QuotaExhaustedError as e:
        return {
            "thinking_steps": thinking_steps,
            "answer": "",
            "citations": [],
            "metrics": None,
            "error": f"quota_exhausted: {e.message}"
        }
    except Exception as e:
        return {
            "thinking_steps": thinking_steps,
            "answer": "",
            "citations": [],
            "metrics": None,
            "error": f"error: {str(e)}"
        }

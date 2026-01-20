"""
Metrics collection for RAG operations.
This module collects metrics WITHOUT persisting them - that's the repository's job.
"""

from typing import Dict, List, Any
from llama_index.core.schema import NodeWithScore
from .token_counter import count_tokens, count_tokens_batch
import uuid


def generate_request_id() -> str:
    """Generate unique request ID."""
    return str(uuid.uuid4())


def collect_chunk_metrics(nodes: List[NodeWithScore]) -> tuple[List[Dict[str, Any]], int]:
    """
    Collect metrics for retrieved chunks.
    
    Args:
        nodes: Retrieved nodes with scores
        
    Returns:
        Tuple of (chunk_metrics_list, total_chunk_tokens)
    """
    chunks = []
    total_tokens = 0
    
    for idx, node in enumerate(nodes):
        # Extract paper title from metadata
        paper_title = node.metadata.get('title', 'Unknown Paper')
        
        # Get content preview (first 200 chars)
        content_preview = node.text[:200] + "..." if len(node.text) > 200 else node.text
        
        # Count tokens
        chunk_tokens = count_tokens(node.text)
        total_tokens += chunk_tokens
        
        chunks.append({
            'chunk_index': idx,
            'paper_title': paper_title,
            'content_preview': content_preview,
            'chunk_token_count': chunk_tokens
        })
    
    return chunks, total_tokens


def collect_request_metrics(
    query: str,
    answer: str,
    chunks: List[Dict[str, Any]],
    total_chunk_tokens: int,
    llm_latency_ms: float,
    total_latency_ms: float
) -> Dict[str, Any]:
    """
    Collect all metrics for a chat request.
    
    Args:
        query: User query
        answer: LLM response
        chunks: Chunk metrics from collect_chunk_metrics()
        total_chunk_tokens: Total tokens from all chunks
        llm_latency_ms: LLM inference latency
        total_latency_ms: Total request latency
        
    Returns:
        Dict with all metrics ready for DB insertion
    """
    # Count tokens
    prompt_tokens = count_tokens(query)
    completion_tokens = count_tokens(answer)
    
    return {
        'query': query,
        'prompt_tokens': prompt_tokens,
        'total_chunk_tokens': total_chunk_tokens,
        'completion_tokens': completion_tokens,
        'llm_latency_ms': llm_latency_ms,
        'total_latency_ms': total_latency_ms,
        'chunks': chunks
    }

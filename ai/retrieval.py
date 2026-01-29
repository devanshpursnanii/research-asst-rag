"""Hybrid Retrieval & RAG Configuration: Shared utilities for retrieval."""

from typing import List, Optional
from llama_index.core import VectorStoreIndex, Settings, PromptTemplate, Document
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.retrievers import BM25Retriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.schema import NodeWithScore
from dotenv import load_dotenv
import time
from .api_config import get_chat_llm, get_embedding_model

load_dotenv()


def configure_settings(llm=None):
    """Configure global LLM and embedding settings."""
    if llm is None:
        llm = get_chat_llm(temperature=0.1)
    
    embedding_config = get_embedding_model()
    embed_model = GeminiEmbedding(
        model_name=embedding_config["model_name"],
        api_key=embedding_config["api_key"],
        task_type="RETRIEVAL_DOCUMENT"  # For indexing documents
    )
    
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.chunk_size = 768
    Settings.chunk_overlap = 128
    
    return llm, embed_model


def create_hybrid_retriever(index, top_k=5):
    """Create hybrid retriever combining vector and BM25 search."""
    vector_retriever = index.as_retriever(similarity_top_k=top_k)
    
    bm25_retriever = BM25Retriever.from_defaults(
        docstore=index.docstore,
        similarity_top_k=top_k
    )
    
    hybrid_retriever = QueryFusionRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        similarity_top_k=top_k,
        num_queries=1,
        mode="reciprocal_rerank",
        use_async=False
    )
    
    return hybrid_retriever


async def enhance_query_for_rag(query: str) -> List[str]:
    """Generate 2 query variations for better retrieval coverage."""
    llm = get_chat_llm(temperature=0.3)
    
    prompt = f"""Generate 2 variations of this research query for semantic search. Expand abbreviations, add technical synonyms, and rephrase for clarity.

Original: "{query}"

Output exactly 2 variations (one per line, no numbering):"""

    start_time = time.time()
    response = await llm.acomplete(prompt)
    
    # Parse variations
    variations = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
    
    # Ensure exactly 2 variations
    if len(variations) < 2:
        # Fallback: return original + one variation
        return [query, variations[0] if variations else query]
    
    return variations[:2]


async def llm_rerank_chunks(query: str, nodes: List[NodeWithScore], top_n: int = 10) -> List[NodeWithScore]:
    """Use LLM to rerank retrieved chunks for better precision."""
    if len(nodes) <= top_n:
        return nodes
    
    llm = get_chat_llm(temperature=0.0)
    
    # Format chunks for reranking
    chunks_text = "\n\n".join([
        f"[{i+1}] {node.metadata.get('title', 'Unknown')} (Page {node.metadata.get('page_label', '?')}):\n{node.text[:300]}..."
        for i, node in enumerate(nodes[:20])  # Rerank top 20
    ])
    
    prompt = f"""Rank these research paper chunks by relevance to the query. Output ONLY the top {top_n} chunk numbers in order (comma-separated, e.g., "3,7,1,15,9").

Query: "{query}"

Chunks:
{chunks_text}

Top {top_n} most relevant (numbers only):"""

    response = await llm.acomplete(prompt)
    
    try:
        # Parse ranked indices
        ranked_indices = [int(x.strip()) - 1 for x in response.text.strip().split(',') if x.strip().isdigit()]
        
        # Reorder nodes
        reranked = [nodes[i] for i in ranked_indices if 0 <= i < len(nodes)]
        
        # Add remaining nodes if needed
        remaining = [n for i, n in enumerate(nodes) if i not in ranked_indices]
        reranked.extend(remaining)
        
        return reranked[:top_n]
    except:
        # Fallback: return original order
        return nodes[:top_n]


def get_citation_prompt():
    """Get prompt template with multi-paper citation format."""
    return PromptTemplate(
        "Context information from research papers:\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Using the context above, answer the query below.\n"
        "Answer in clear, flowing paragraphs with citations inline. "
        "Format citations as [Paper Title, Page X] using the paper's title and page number. "
        "Avoid lists or bullet points.\n\n"
        "Query: {query_str}\n"
        "Answer: "
    )


def create_query_engine(retriever, citation_prompt=None, response_mode="compact"):
    """Create query engine with custom prompt and retriever."""
    if citation_prompt is None:
        citation_prompt = get_citation_prompt()
    
    return RetrieverQueryEngine.from_args(
        retriever=retriever,
        text_qa_template=citation_prompt,
        response_mode=response_mode
    )

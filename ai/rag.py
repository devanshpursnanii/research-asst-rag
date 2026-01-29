"""
Multi-Paper RAG with Intelligent Task Routing

Architecture:
1. Load multiple papers from arXiv → Unified index
2. Router classifies query into: QA | Summarize | Compare | Explain
3. Task-specific retrieval with custom parameters
4. Paper-aware MMR ensures diversity across papers
5. Token compression for optimal context
"""

from typing import List, Optional, Dict, Any
import numpy as np
import time
import asyncio
from llama_index.core import VectorStoreIndex, Document, PromptTemplate
from llama_index.core.schema import NodeWithScore
from llama_index.core.query_engine import RetrieverQueryEngine, RouterQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.selectors import LLMSingleSelector
from llama_index.embeddings.gemini import GeminiEmbedding
from dotenv import load_dotenv
import re
from .retrieval import configure_settings, create_hybrid_retriever, enhance_query_for_rag, llm_rerank_chunks
from .logger import SessionLogger
from .api_config import get_chat_llm, get_embedding_model

load_dotenv()


def apply_mmr_diversity(nodes: List[NodeWithScore], top_n: int = 4, lambda_param: float = 0.7) -> List[NodeWithScore]:
    """
    Apply Maximal Marginal Relevance to diversify retrieved nodes.
    
    Args:
        nodes: Retrieved nodes with scores
        top_n: Number of final diverse nodes to select
        lambda_param: Relevance vs diversity tradeoff (higher = more relevance)
        
    Returns:
        Diversified subset of nodes
    """
    if len(nodes) <= top_n:
        return nodes
    
    # Extract relevance scores
    scores = np.array([node.score for node in nodes])
    
    # Normalize scores
    if scores.max() > scores.min():
        scores = (scores - scores.min()) / (scores.max() - scores.min())
    
    selected = []
    selected_indices = []
    remaining_indices = list(range(len(nodes)))
    
    # Select first (highest relevance)
    first_idx = remaining_indices.pop(0)
    selected.append(nodes[first_idx])
    selected_indices.append(first_idx)
    
    # Iteratively select remaining
    while len(selected) < top_n and remaining_indices:
        mmr_scores = []
        
        for idx in remaining_indices:
            relevance = scores[idx]
            
            # Diversity: avoid same paper
            max_similarity = 0
            for sel_idx in selected_indices:
                # Same paper = high similarity, different paper = low similarity
                same_paper = (nodes[idx].metadata.get('arxiv_id') == 
                            nodes[sel_idx].metadata.get('arxiv_id'))
                similarity = 1.0 if same_paper else 0.3
                max_similarity = max(max_similarity, similarity)
            
            # MMR score
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
            mmr_scores.append((idx, mmr_score))
        
        # Select highest MMR
        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        remaining_indices.remove(best_idx)
        selected.append(nodes[best_idx])
        selected_indices.append(best_idx)
    
    return selected


def compress_if_needed(nodes: List[NodeWithScore], max_tokens: int = 18000) -> List[NodeWithScore]:
    """Compress nodes if total content exceeds token limit."""
    total_chars = sum(len(node.text) for node in nodes)
    estimated_tokens = total_chars // 4
    
    if estimated_tokens <= max_tokens:
        return nodes
    
    print(f"⚠️  Compressing: {estimated_tokens} tokens → ~{max_tokens} tokens")
    compression_ratio = max_tokens / estimated_tokens
    
    compressed_nodes = []
    for node in nodes:
        new_length = int(len(node.text) * compression_ratio)
        compressed_text = node.text[:new_length] + "..."
        compressed_node = NodeWithScore(node=node.node, score=node.score)
        compressed_node.node.text = compressed_text
        compressed_nodes.append(compressed_node)
    
    return compressed_nodes


class TaskSpecificRetriever:
    """Custom retriever with task-specific parameters and paper-aware MMR."""
    def __init__(self, index: VectorStoreIndex, top_k: int, top_n: int, 
                 lambda_param: float, max_tokens: int, logger: Optional[SessionLogger] = None):
        self.index = index
        self.top_k = top_k
        self.top_n = top_n
        self.lambda_param = lambda_param
        self.max_tokens = max_tokens
        self.logger = logger
    
    def retrieve(self, query: str) -> List[NodeWithScore]:
        """Retrieve with query enhancement, proper embedding task type, and LLM reranking."""
        # Generate 2 query variations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        query_variations = loop.run_until_complete(enhance_query_for_rag(query))
        loop.close()
        
        # Create query-specific embedding model
        embedding_config = get_embedding_model()
        query_embed_model = GeminiEmbedding(
            model_name=embedding_config["model_name"],
            api_key=embedding_config["api_key"],
            task_type="RETRIEVAL_QUERY"  # For query embeddings
        )
        
        # Retrieve with each query variation
        all_nodes = []
        seen_node_ids = set()
        
        for q_var in query_variations:
            # Embed query with RETRIEVAL_QUERY task type
            hybrid_retriever = create_hybrid_retriever(self.index, top_k=self.top_k)
            retrieved = hybrid_retriever.retrieve(q_var)
            
            # Deduplicate
            for node in retrieved:
                node_id = node.node.node_id
                if node_id not in seen_node_ids:
                    all_nodes.append(node)
                    seen_node_ids.add(node_id)
        
        # LLM reranking (adds 1 LLM call per query)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        reranked_nodes = loop.run_until_complete(
            llm_rerank_chunks(query, all_nodes, top_n=min(self.top_k * 2, len(all_nodes)))
        )
        loop.close()
        
        # Paper-aware MMR on reranked results
        diverse_nodes = apply_mmr_diversity(reranked_nodes, top_n=self.top_n, 
                                           lambda_param=self.lambda_param)
        
        # Compress if needed
        compressed_nodes = compress_if_needed(diverse_nodes, max_tokens=self.max_tokens)
        
        # Log RAG chunks
        if self.logger:
            for node in compressed_nodes:
                title = node.metadata.get('title', 'Unknown Paper')
                page = node.metadata.get('page_label', '?')
                self.logger.log_rag_chunk(
                    text=node.node.text,
                    score=node.score,
                    source=f"{title} (Page {page})",
                    metadata=node.metadata,
                    retrieval_method="enhanced_query_reranked_mmr"
                )
        
        # Format nodes with citation metadata
        for node in compressed_nodes:
            title = node.metadata.get('title', 'Unknown Paper')
            page = node.metadata.get('page_label', '?')
            node.node.text = f"[{title}, Page {page}]\n{node.node.text}"
        
        return compressed_nodes


def create_task_engine(index: VectorStoreIndex, top_k: int, top_n: int, 
                       lambda_param: float, max_tokens: int, prompt: PromptTemplate,
                       logger: Optional[SessionLogger] = None) -> RetrieverQueryEngine:
    """Create task-specific query engine with custom retrieval parameters."""
    retriever = TaskSpecificRetriever(index, top_k, top_n, lambda_param, max_tokens, logger)
    
    return RetrieverQueryEngine.from_args(
        retriever=retriever,
        text_qa_template=prompt,
        response_mode="compact"
    )


def get_task_prompts():
    """Get task-specific prompt templates with structured output formats."""
    base_context = (
        "Context information from research papers:\n"
        "------\n"
        "{context_str}\n"
        "------\n"
    )
    
    return {
        "qa": PromptTemplate(
            base_context +
            "Answer in 2-3 sentences. Be direct and factual. "
            "Cite as [Paper Title, Page X].\n\n"
            "Question: {query_str}\n"
            "Answer: "
        ),
        "summarize": PromptTemplate(
            base_context +
            "Provide a structured summary using bullet points:\n"
            "• Main contributions\n"
            "• Key methods\n"
            "• Important findings\n"
            "Cite as [Paper Title, Page X].\n\n"
            "Topic: {query_str}\n"
            "Summary: "
        ),
        "compare": PromptTemplate(
            base_context +
            "Structure your comparison as:\n"
            "**Similarities:**\n- Point 1\n- Point 2\n\n"
            "**Differences:**\n- Paper A: ... [Citation]\n- Paper B: ... [Citation]\n\n"
            "Cite as [Paper Title, Page X].\n\n"
            "Comparison: {query_str}\n"
            "Answer: "
        ),
        "explain": PromptTemplate(
            base_context +
            "Explain in clear steps:\n"
            "1. Core concept: ...\n"
            "2. How it works: ...\n"
            "3. Key insight: ...\n"
            "Cite as [Paper Title, Page X].\n\n"
            "Explain: {query_str}\n"
            "Explanation: "
        )
    }


def create_qa_engine(index: VectorStoreIndex, prompts: dict, logger: Optional[SessionLogger] = None) -> RetrieverQueryEngine:
    """QA engine: precise, focused answers."""
    return create_task_engine(
        index=index,
        top_k=15,
        top_n=5,
        lambda_param=0.85,
        max_tokens=10000,
        prompt=prompts["qa"],
        logger=logger
    )


def create_summarize_engine(index: VectorStoreIndex, prompts: dict, logger: Optional[SessionLogger] = None) -> RetrieverQueryEngine:
    """Summarization engine: broad, comprehensive coverage."""
    return create_task_engine(
        index=index,
        top_k=15,
        top_n=8,
        lambda_param=0.8,
        max_tokens=25000,
        prompt=prompts["summarize"],
        logger=logger
    )


def create_compare_engine(index: VectorStoreIndex, prompts: dict, logger: Optional[SessionLogger] = None) -> RetrieverQueryEngine:
    """Comparison engine: multi-paper analysis."""
    return create_task_engine(
        index=index,
        top_k=20,
        top_n=8,
        lambda_param=0.7,
        max_tokens=20000,
        prompt=prompts["compare"],
        logger=logger
    )


def create_explain_engine(index: VectorStoreIndex, prompts: dict, logger: Optional[SessionLogger] = None) -> RetrieverQueryEngine:
    """Explanation engine: conceptual deep-dive."""
    return create_task_engine(
        index=index,
        top_k=18,
        top_n=6,
        lambda_param=0.8,
        max_tokens=18000,
        prompt=prompts["explain"],
        logger=logger
    )


def analyze_citations(response_text: str) -> dict:
    """Analyze citation coverage in response."""
    citations = re.findall(r'\[([^,]+), Page (\d+)\]', response_text)
    
    if not citations:
        return {
            'total_citations': 0,
            'unique_papers': 0,
            'unique_pages': 0,
            'papers': []
        }
    
    unique_papers = list(set([c[0] for c in citations]))
    unique_pages = len(set(citations))
    
    return {
        'total_citations': len(citations),
        'unique_papers': len(unique_papers),
        'unique_pages': unique_pages,
        'papers': unique_papers
    }


def create_router_engine(index: VectorStoreIndex, logger: Optional[SessionLogger] = None) -> RouterQueryEngine:
    """Create router that selects appropriate task-specific engine."""
    prompts = get_task_prompts()
    
    # Create task-specific engines
    qa_engine = create_qa_engine(index, prompts, logger)
    summarize_engine = create_summarize_engine(index, prompts, logger)
    compare_engine = create_compare_engine(index, prompts, logger)
    explain_engine = create_explain_engine(index, prompts, logger)
    
    # Wrap in QueryEngineTool with descriptions
    tools = [
        QueryEngineTool.from_defaults(
            query_engine=qa_engine,
            name="qa",
            description=(
                "Use for direct questions requiring precise, factual answers. "
                "Examples: 'What is the learning rate?', 'Which optimizer was used?', "
                "'What datasets were evaluated?'"
            )
        ),
        QueryEngineTool.from_defaults(
            query_engine=summarize_engine,
            name="summarize",
            description=(
                "Use for requests to summarize or provide overview of papers, methods, or findings. "
                "Examples: 'Summarize the main contributions', 'Give an overview of the approach', "
                "'What are the key findings?'"
            )
        ),
        QueryEngineTool.from_defaults(
            query_engine=compare_engine,
            name="compare",
            description=(
                "Use for comparing concepts, methods, or approaches across multiple papers. "
                "Examples: 'Compare X and Y', 'What are the differences between...', "
                "'How do these papers approach...'"
            )
        ),
        QueryEngineTool.from_defaults(
            query_engine=explain_engine,
            name="explain",
            description=(
                "Use for requests to explain concepts, mechanisms, or how something works. "
                "Examples: 'Explain how X works', 'How does Y mechanism function?', "
                "'Walk me through the process of...'"
            )
        )
    ]
    
    # Create router with lighter LLM for selection (saves quota)
    router_llm = get_chat_llm(temperature=0.1)
    return RouterQueryEngine(
        selector=LLMSingleSelector.from_defaults(llm=router_llm),
        query_engine_tools=tools,
        verbose=True
    )


def multi_paper_rag_with_documents(documents: List[Document], query: str, logger: Optional[SessionLogger] = None):
    """
    Multi-paper RAG with pre-loaded documents (from Paper Brain).
    
    Args:
        documents: Already loaded Document objects
        query: User query (router will classify task type)
        logger: Optional session logger
    
    Returns:
        LLM response with cross-paper citations
    """
    print(f"{'='*80}")
    print(f"MULTI-PAPER RAG WITH INTELLIGENT ROUTING")
    print(f"{'='*80}\n")
    
    # Configure settings
    configure_settings()
    
    # Build unified index from documents
    print("Building unified index...")
    index = VectorStoreIndex.from_documents(documents)
    print("✓ Index created\n")
    
    # Create router
    print("Creating intelligent router...\n")
    router = create_router_engine(index, logger)
    
    # Query with automatic routing and timing
    print(f"Query: {query}\n")
    print("Routing to appropriate engine...\n")
    
    start_time = time.time()
    response = router.query(query)
    latency_ms = (time.time() - start_time) * 1000
    
    # Log router query and final answer generation
    if logger:
        logger.log_llm_call(
            call_type="query_routing_and_answer",
            input_text=query,
            output_text=str(response),
            latency_ms=latency_ms,
            temperature=0.7
        )
    
    # Analyze citations
    citation_stats = analyze_citations(str(response))
    print(f"\n{'─'*80}")
    print(f"CITATION METRICS")
    print(f"{'─'*80}")
    print(f"📊 Papers cited: {citation_stats['unique_papers']} papers")
    print(f"📄 Unique pages: {citation_stats['unique_pages']} pages")
    print(f"🔗 Total citations: {citation_stats['total_citations']}")
    if citation_stats['papers']:
        print(f"📚 Papers: {', '.join(citation_stats['papers'][:3])}..." if len(citation_stats['papers']) > 3 else f"📚 Papers: {', '.join(citation_stats['papers'])}")
    
    return response


def multi_paper_rag_with_documents_with_metrics(documents: List[Document], query: str, logger: Optional[SessionLogger] = None) -> Dict[str, Any]:
    """
    Multi-paper RAG that returns both response and metrics for DB logging.
    
    Args:
        documents: Already loaded Document objects
        query: User query
        logger: Optional session logger
    
    Returns:
        Dict with:
            - response: LLM response
            - chunks: List of chunk metrics
            - total_chunk_tokens: Total tokens in all chunks
            - llm_latency_ms: LLM inference latency
    """
    from .metrics_collector import collect_chunk_metrics
    
    # Configure settings
    configure_settings()
    
    # Build unified index from documents
    index = VectorStoreIndex.from_documents(documents)
    
    # Create router with modified retriever that tracks chunks
    router = create_router_engine_with_metrics(index, logger)
    
    # Query with timing
    llm_start = time.time()
    response = router.query(query)
    llm_latency_ms = (time.time() - llm_start) * 1000
    
    # Get retrieved chunks from response source nodes
    retrieved_nodes = response.source_nodes if hasattr(response, 'source_nodes') else []
    chunks, total_chunk_tokens = collect_chunk_metrics(retrieved_nodes)
    
    return {
        'response': response,
        'chunks': chunks,
        'total_chunk_tokens': total_chunk_tokens,
        'llm_latency_ms': llm_latency_ms
    }


def create_router_engine_with_metrics(index: VectorStoreIndex, logger: Optional[SessionLogger] = None) -> RouterQueryEngine:
    """Create router that preserves source nodes for metrics."""
    prompts = get_task_prompts()
    
    # Create task-specific engines (same as before)
    qa_engine = create_qa_engine(index, prompts, logger)
    summarize_engine = create_summarize_engine(index, prompts, logger)
    compare_engine = create_compare_engine(index, prompts, logger)
    explain_engine = create_explain_engine(index, prompts, logger)
    
    # Wrap in QueryEngineTool with descriptions
    tools = [
        QueryEngineTool.from_defaults(
            query_engine=qa_engine,
            name="qa",
            description=(
                "Use for direct questions requiring precise, factual answers. "
                "Examples: 'What is the learning rate?', 'Which optimizer was used?', "
                "'What datasets were evaluated?'"
            )
        ),
        QueryEngineTool.from_defaults(
            query_engine=summarize_engine,
            name="summarize",
            description=(
                "Use for requests to summarize or provide overview of papers, methods, or findings. "
                "Examples: 'Summarize the main contributions', 'Give an overview of the approach', "
                "'What are the key findings?'"
            )
        ),
        QueryEngineTool.from_defaults(
            query_engine=compare_engine,
            name="compare",
            description=(
                "Use for comparing concepts, methods, or approaches across multiple papers. "
                "Examples: 'Compare X and Y', 'What are the differences between...', "
                "'How do these papers approach...'"
            )
        ),
        QueryEngineTool.from_defaults(
            query_engine=explain_engine,
            name="explain",
            description=(
                "Use for requests to explain concepts, mechanisms, or how something works. "
                "Examples: 'Explain how X works', 'How does Y mechanism function?', "
                "'Walk me through the process of...'"
            )
        )
    ]
    
    # Create router
    router_llm = get_chat_llm(temperature=0.1)
    return RouterQueryEngine(
        selector=LLMSingleSelector.from_defaults(llm=router_llm),
        query_engine_tools=tools,
        verbose=True
    )

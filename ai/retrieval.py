"""Hybrid Retrieval & RAG Configuration: Shared utilities for retrieval."""

from typing import List
from llama_index.core import VectorStoreIndex, Settings, PromptTemplate, Document
from llama_index.llms.google_genai import GoogleGenAI 
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.query_engine import RetrieverQueryEngine
from dotenv import load_dotenv

load_dotenv()


def configure_settings():
    """Configure global LLM and embedding settings."""
    llm = GoogleGenAI(model="models/gemini-2.5-flash-lite", temperature=0.1)
    embed_model = GoogleGenAIEmbedding(model_name="models/text-embedding-004")
    
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.chunk_size = 512
    
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

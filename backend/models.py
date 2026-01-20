"""
Pydantic Models for API Request/Response Validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ==================
# REQUEST MODELS
# ==================

class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    initial_query: str = Field(..., description="User's initial research query")


class BrainSearchRequest(BaseModel):
    """Request to search papers with Paper Brain."""
    session_id: str = Field(..., description="Session UUID")
    query: str = Field(..., description="Research query to search")
    search_mode: str = Field(default="topic", description="Search mode: 'title' or 'topic'")
    search_mode: str = Field(default="topic", description="Search mode: 'title' or 'topic'")


class BrainLoadRequest(BaseModel):
    """Request to load selected papers."""
    session_id: str = Field(..., description="Session UUID")
    paper_ids: List[str] = Field(..., description="List of arXiv IDs to load")


class ChatMessageRequest(BaseModel):
    """Request to send a message in Paper Chat."""
    session_id: str = Field(..., description="Session UUID")
    message: str = Field(..., description="User's question")


# ==================
# RESPONSE MODELS
# ==================

class ThinkingStep(BaseModel):
    """Thinking step in agent processing."""
    step: str = Field(..., description="Step name (e.g., 'rewriting', 'searching')")
    status: str = Field(..., description="Status: 'in_progress', 'complete', 'error'")
    result: Optional[str] = Field(None, description="Result or description of step")


class Paper(BaseModel):
    """Paper metadata from arXiv."""
    title: str
    authors: str
    abstract: str
    arxiv_id: str
    url: str
    score: float = Field(..., description="Relevance score (0-1)")


class Citation(BaseModel):
    """Citation extracted from response."""
    paper: str = Field(..., description="Paper title")
    page: int = Field(..., description="Page number")


class QuotaStatus(BaseModel):
    """Quota status for a session."""
    brain: Dict[str, Any] = Field(..., description="Brain quota info")
    chat: Dict[str, Any] = Field(..., description="Chat quota info")
    api_exhausted: bool = Field(..., description="Whether API is exhausted")


class SessionInfo(BaseModel):
    """Session information."""
    session_id: str
    created_at: str
    last_activity: str
    initial_query: str
    loaded_papers: List[str]
    quota_status: QuotaStatus
    brain_searches_used: int
    chat_messages_used: int


# ==================
# ENDPOINT RESPONSES
# ==================

class CreateSessionResponse(BaseModel):
    """Response from creating a session."""
    session_id: str
    created_at: str
    message: str = "Session created successfully"


class BrainSearchResponse(BaseModel):
    """Response from Paper Brain search."""
    thinking_steps: List[ThinkingStep]
    papers: List[Paper]
    searches_remaining: int
    error: Optional[str] = None


class BrainLoadResponse(BaseModel):
    """Response from loading papers."""
    thinking_steps: List[ThinkingStep]
    loaded_papers: List[str]
    status: str
    error: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Response from Paper Chat message."""
    thinking_steps: List[ThinkingStep]
    answer: str
    citations: List[Citation]
    messages_remaining: int
    error: Optional[str] = None


class SessionInfoResponse(BaseModel):
    """Response with session info and logs."""
    session_info: SessionInfo
    logs_summary: Dict[str, Any]
    error: Optional[str] = None


class MetricsRequest(BaseModel):
    """Single request in metrics view."""
    request_id: str
    query: str
    prompt_tokens: int
    total_chunk_tokens: int
    completion_tokens: int
    total_tokens: int
    llm_latency_ms: float
    total_latency_ms: float
    operation_type: str
    status: str
    created_at: str
    chunks: List[Dict[str, Any]]


class MetricsResponse(BaseModel):
    """Response with session metrics from SQLite database."""
    session_id: str
    total_requests: int
    total_tokens: int
    avg_llm_latency: float
    avg_total_latency: float
    requests: List[MetricsRequest]
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    error_type: str = Field(..., description="Type: 'quota_exhausted', 'not_found', 'validation', 'internal'")
    cooldown_minutes: Optional[int] = None
    message: str

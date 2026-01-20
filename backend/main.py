"""
FastAPI Backend for Paper Brain AI

5 Endpoints:
1. POST /session/create - Create new session
2. POST /brain/search - Search papers with Paper Brain
3. POST /brain/load - Load selected papers
4. POST /chat/message - Send message to Paper Chat
5. GET /session/{session_id}/info - Get session info and logs
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sys
import os
from datetime import datetime
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import (
    CreateSessionRequest, CreateSessionResponse,
    BrainSearchRequest, BrainSearchResponse,
    BrainLoadRequest, BrainLoadResponse,
    ChatMessageRequest, ChatMessageResponse,
    SessionInfoResponse, ErrorResponse,
    ThinkingStep, Paper, Citation, QuotaStatus, SessionInfo,
    MetricsResponse, MetricsRequest
)
from backend.session import (
    create_session, get_session, cleanup_old_sessions,
    get_session_count
)
from ai.web_interface import web_brain_search, web_brain_load_papers, web_chat_query
from ai.api_config import QuotaExhaustedError


# ==================
# DB INITIALIZATION
# ==================

def bootstrap_database():
    """Initialize database if it doesn't exist."""
    from backend.db.connection import DB_PATH, get_connection
    from pathlib import Path
    
    if not DB_PATH.exists():
        print("📊 Database not found. Creating logs.db...")
        
        # Read schema
        schema_path = Path(__file__).parent / "db" / "schema.sql"
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Create database and execute schema
        conn = get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
            print("✅ Database initialized successfully")
        finally:
            conn.close()
    else:
        print("✅ Database already exists at", DB_PATH)


# ==================
# FASTAPI APP SETUP
# ==================

app = FastAPI(
    title="Paper Brain AI API",
    description="Research paper discovery and RAG chat API",
    version="1.0.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Run startup tasks."""
    bootstrap_database()

# CORS Configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://192.168.0.106:3000",
        "http://192.168.0.107:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# ==================
# ENDPOINTS
# ==================

async def log_chat_metrics_async(session_id: str, metrics: dict):
    """
    Asynchronously log chat metrics to database.
    This runs after the response is sent to the user.
    """
    try:
        from backend.db import repository
        from ai.metrics_collector import generate_request_id
        
        # Generate request ID
        request_id = generate_request_id()
        
        # Build request data
        request_data = {
            'request_id': request_id,
            'session_id': session_id,
            'query': metrics['query'],
            'prompt_tokens': metrics['prompt_tokens'],
            'total_chunk_tokens': metrics['total_chunk_tokens'],
            'completion_tokens': metrics['completion_tokens'],
            'llm_latency_ms': metrics['llm_latency_ms'],
            'total_latency_ms': metrics['total_latency_ms'],
            'operation_type': 'chat_message',
            'status': 'success'
        }
        
        # Insert request
        await asyncio.to_thread(repository.insert_request, request_data)
        
        # Insert chunks
        await asyncio.to_thread(repository.insert_chunks, request_id, metrics['chunks'])
        
        print(f"✓ Metrics logged for request {request_id[:8]}...")
    except Exception as e:
        # Log error but don't raise (logging failure shouldn't break the app)
        print(f"⚠️  Failed to log metrics: {e}")


@app.post("/session/create", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_new_session(request: CreateSessionRequest):
    """
    Create a new session for Paper Brain.
    
    - **initial_query**: User's research query for session title
    
    Returns session_id and creation timestamp.
    """
    try:
        session = create_session(initial_query=request.initial_query)
        
        # Log session creation to database
        from backend.db import repository
        repository.create_session(session.session_id, session.created_at)
        
        return CreateSessionResponse(
            session_id=session.session_id,
            created_at=session.created_at.isoformat(),
            message="Session created successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@app.post("/brain/search", response_model=BrainSearchResponse)
async def brain_search(request: BrainSearchRequest):
    """
    Search arXiv papers with Paper Brain.
    
    - **session_id**: Active session UUID
    - **query**: Research query to search
    
    Returns thinking steps, ranked papers, and remaining searches.
    """
    # Get session
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check quota
    can_use, cooldown_mins = session.quota.can_use_brain()
    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exhausted",
                "cooldown_minutes": cooldown_mins,
                "message": f"Paper Brain quota exhausted. Try again in {cooldown_mins} minutes."
            }
        )
    
    # Perform search
    try:
        result = await web_brain_search(request.query, search_mode=request.search_mode, logger=session.logger)
        
        # Check for errors
        if result.get("error"):
            if "quota_exhausted" in result["error"]:
                # Mark API as exhausted
                session.quota.mark_api_exhausted()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "api_quota_exhausted",
                        "cooldown_minutes": 30,
                        "message": "API quota exhausted. Try again in 30 minutes."
                    }
                )
            else:
                return BrainSearchResponse(
                    thinking_steps=[ThinkingStep(**step) for step in result["thinking_steps"]],
                    papers=[],
                    searches_remaining=session.quota.get_remaining_brain_searches(),
                    error=result["error"]
                )
        
        # Increment quota
        session.quota.increment_brain()
        
        # Add to history
        session.brain_history.append({
            "query": request.query,
            "papers_found": len(result["papers"]),
            "timestamp": datetime.now().isoformat()
        })
        
        return BrainSearchResponse(
            thinking_steps=[ThinkingStep(**step) for step in result["thinking_steps"]],
            papers=[Paper(**paper) for paper in result["papers"]],
            searches_remaining=session.quota.get_remaining_brain_searches(),
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return BrainSearchResponse(
            thinking_steps=[],
            papers=[],
            searches_remaining=session.quota.get_remaining_brain_searches(),
            error=f"Internal error: {str(e)}"
        )


@app.post("/brain/load", response_model=BrainLoadResponse)
async def brain_load(request: BrainLoadRequest):
    """
    Load selected papers for RAG.
    
    - **session_id**: Active session UUID
    - **paper_ids**: List of arXiv IDs to load
    
    Returns loading status and paper titles.
    """
    # Get session
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Load papers
    try:
        # Add initial status
        thinking_steps = [
            {"step_number": 1, "description": f"Downloading {len(request.paper_ids)} papers from arXiv..."},
            {"step_number": 2, "description": "Extracting text and building index..."},
        ]
        
        result = await web_brain_load_papers(request.paper_ids, logger=session.logger)
        
        if result.get("error"):
            return BrainLoadResponse(
                thinking_steps=[ThinkingStep(**step) for step in result["thinking_steps"]],
                loaded_papers=[],
                status="failed",
                error=result["error"]
            )
        
        # Store documents in session
        session.loaded_documents = result["documents"]
        session.loaded_paper_titles = result["loaded_papers"]
        session.logger.mode = "multi_paper_rag"  # Switch to RAG mode
        
        return BrainLoadResponse(
            thinking_steps=[ThinkingStep(**step) for step in result["thinking_steps"]],
            loaded_papers=result["loaded_papers"],
            status="success",
            error=None
        )
        
    except Exception as e:
        return BrainLoadResponse(
            thinking_steps=[],
            loaded_papers=[],
            status="failed",
            error=f"Internal error: {str(e)}"
        )


@app.post("/chat/message", response_model=ChatMessageResponse)
async def chat_message(request: ChatMessageRequest):
    """
    Send a message to Paper Chat.
    
    - **session_id**: Active session UUID
    - **message**: User's question about loaded papers
    
    Returns answer with citations and remaining messages.
    """
    # Get session
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if papers loaded
    if not session.loaded_documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No papers loaded. Please load papers first using /brain/load"
        )
    
    # Check quota
    can_use, cooldown_mins = session.quota.can_use_chat()
    if not can_use:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exhausted",
                "cooldown_minutes": cooldown_mins,
                "message": f"Paper Chat quota exhausted. Try again in {cooldown_mins} minutes."
            }
        )
    
    # Query RAG
    try:
        result = await web_chat_query(
            request.message,
            session.loaded_documents,
            logger=session.logger
        )
        
        # Check for errors
        if result.get("error"):
            if "quota_exhausted" in result["error"]:
                # Mark API as exhausted
                session.quota.mark_api_exhausted()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "api_quota_exhausted",
                        "cooldown_minutes": 30,
                        "message": "API quota exhausted. Try again in 30 minutes."
                    }
                )
            else:
                return ChatMessageResponse(
                    thinking_steps=[ThinkingStep(**step) for step in result["thinking_steps"]],
                    answer="",
                    citations=[],
                    messages_remaining=session.quota.get_remaining_chat_messages(),
                    error=result["error"]
                )
        
        # Increment quota
        session.quota.increment_chat()
        
        # Add to history
        session.chat_history.append({
            "message": request.message,
            "answer": result["answer"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Clean markdown formatting
        import re
        clean_answer = result["answer"]
        # Remove markdown headers
        clean_answer = re.sub(r'^#{1,6}\s+', '', clean_answer, flags=re.MULTILINE)
        # Remove bold/italic markers
        clean_answer = clean_answer.replace("**", "").replace("__", "")
        clean_answer = re.sub(r'(?<!\*)\*(?!\*)', '', clean_answer)  # Remove single asterisks
        # Clean up bullet points - replace * with •
        clean_answer = re.sub(r'^\s*\*\s+', '• ', clean_answer, flags=re.MULTILINE)
        
        # Log to database asynchronously (don't block response)
        if result.get("metrics"):
            asyncio.create_task(log_chat_metrics_async(
                session_id=request.session_id,
                metrics=result["metrics"]
            ))
        
        return ChatMessageResponse(
            thinking_steps=[ThinkingStep(**step) for step in result["thinking_steps"]],
            answer=clean_answer,
            citations=[Citation(**cite) for cite in result["citations"]],
            messages_remaining=session.quota.get_remaining_chat_messages(),
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return ChatMessageResponse(
            thinking_steps=[],
            answer="",
            citations=[],
            messages_remaining=session.quota.get_remaining_chat_messages(),
            error=f"Internal error: {str(e)}"
        )


@app.get("/session/{session_id}/info", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    """
    Get session information, quota status, and logs.
    
    - **session_id**: Session UUID
    
    Returns session metadata, quota status, logs summary, and detailed logs.
    """
    # Get session
    session = get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    try:
        # Get quota status
        quota_status_dict = session.quota.get_status()
        quota_status = QuotaStatus(**quota_status_dict)
        
        # Build session info
        session_info = SessionInfo(
            session_id=session.session_id,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            initial_query=session.initial_query,
            loaded_papers=session.loaded_paper_titles,
            quota_status=quota_status,
            brain_searches_used=session.quota.brain_searches,
            chat_messages_used=session.quota.chat_messages
        )
        
        # Get logs summary and detailed logs
        logs_summary = session.logger.get_summary()
        
        # Return with detailed logs for dashboard
        return {
            "session_info": session_info,
            "logs_summary": logs_summary,
            "llm_calls": session.logger.api_calls_llm,
            "rag_chunks": session.logger.rag_chunks,
            "error": None
        }
        
    except Exception as e:
        return SessionInfoResponse(
            session_info=SessionInfo(
                session_id=session_id,
                created_at="",
                last_activity="",
                initial_query="",
                loaded_papers=[],
                quota_status=QuotaStatus(brain={}, chat={}, api_exhausted=False),
                brain_searches_used=0,
                chat_messages_used=0
            ),
            logs_summary={},
            error=f"Internal error: {str(e)}"
        )


@app.get("/metrics/{session_id}", response_model=MetricsResponse)
async def get_session_metrics(session_id: str):
    """
    Get session metrics from SQLite database.
    
    - **session_id**: Session UUID
    
    Returns aggregated metrics and detailed request/chunk data.
    """
    from backend.db.repository import (
        get_requests_by_session, 
        get_chunks_by_request,
        get_session_metrics
    )
    
    try:
        # Get aggregated metrics
        metrics = get_session_metrics(session_id)
        
        # Get all requests for this session
        requests = get_requests_by_session(session_id)
        
        # Get chunks for each request
        requests_with_chunks = []
        for req in requests:
            chunks = get_chunks_by_request(req['request_id'])
            
            # Calculate total tokens for this request
            total_tokens = (
                req['prompt_tokens'] + 
                req['total_chunk_tokens'] + 
                req['completion_tokens']
            )
            
            requests_with_chunks.append(MetricsRequest(
                request_id=req['request_id'],
                query=req['query'],
                prompt_tokens=req['prompt_tokens'],
                total_chunk_tokens=req['total_chunk_tokens'],
                completion_tokens=req['completion_tokens'],
                total_tokens=total_tokens,
                llm_latency_ms=req['llm_latency_ms'],
                total_latency_ms=req['total_latency_ms'],
                operation_type=req['operation_type'],
                status=req['status'],
                created_at=req['created_at'],
                chunks=chunks
            ))
        
        return MetricsResponse(
            session_id=session_id,
            total_requests=metrics.get('total_requests', 0) or 0,
            total_tokens=metrics.get('total_tokens', 0) or 0,
            avg_llm_latency=metrics.get('avg_llm_latency', 0.0) or 0.0,
            avg_total_latency=metrics.get('avg_total_latency', 0.0) or 0.0,
            requests=requests_with_chunks,
            error=None
        )
        
    except Exception as e:
        return MetricsResponse(
            session_id=session_id,
            total_requests=0,
            total_tokens=0,
            avg_llm_latency=0.0,
            avg_total_latency=0.0,
            requests=[],
            error=f"Failed to fetch metrics: {str(e)}"
        )


# ==================
# HEALTH & UTILITY
# ==================

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Paper Brain AI API",
        "version": "1.0.0",
        "status": "running",
        "active_sessions": get_session_count(),
        "endpoints": {
            "create_session": "POST /session/create",
            "brain_search": "POST /brain/search",
            "brain_load": "POST /brain/load",
            "chat_message": "POST /chat/message",
            "session_info": "GET /session/{session_id}/info"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": get_session_count()
    }


# Cleanup old sessions on startup
@app.on_event("startup")
async def startup_event():
    """Run cleanup on startup - only remove very old sessions.""" 
    deleted = cleanup_old_sessions(max_age_hours=48)  # Changed from 24 to 48 hours
    print(f"✓ FastAPI started. Cleaned up {deleted} old sessions.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

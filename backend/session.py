"""
Session Management for Paper Brain API

Manages in-memory sessions with:
- Loaded documents
- Chat history
- Quota tracking
- Session logger
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.logger import SessionLogger
from ai.quota_manager import QuotaTracker
from llama_index.core import Document
import uuid


@dataclass
class Session:
    """Session data for a user's Paper Brain session."""
    
    session_id: str
    logger: SessionLogger
    quota: QuotaTracker
    
    # Paper Brain state
    loaded_documents: List[Document] = field(default_factory=list)
    loaded_paper_titles: List[str] = field(default_factory=list)
    brain_history: List[dict] = field(default_factory=list)
    
    # Paper Chat state
    chat_history: List[dict] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    initial_query: str = ""
    
    def touch(self):
        """Update last accessed time to extend TTL."""
        self.last_accessed = datetime.now()
        self.last_activity = datetime.now()
    
    def is_expired(self, ttl_minutes: int = 30) -> bool:
        """Check if session has exceeded TTL since last access."""
        elapsed = (datetime.now() - self.last_accessed).total_seconds()
        return elapsed > (ttl_minutes * 60)


# Global in-memory session store
sessions: Dict[str, Session] = {}


def create_session(initial_query: str = "New Session") -> Session:
    """
    Create a new session with unique ID.
    
    Args:
        initial_query: User's initial query for logging
        
    Returns:
        New Session object
    """
    session_id = str(uuid.uuid4())
    
    logger = SessionLogger(
        query_title=initial_query,
        mode="paper_brain"
    )
    
    quota = QuotaTracker()
    
    session = Session(
        session_id=session_id,
        logger=logger,
        quota=quota,
        initial_query=initial_query
    )
    
    sessions[session_id] = session
    
    return session


def get_session(session_id: str, ttl_minutes: int = 30) -> Optional[Session]:
    """
    Get session by ID with TTL expiry check.
    
    Args:
        session_id: Session UUID
        ttl_minutes: Time-to-live in minutes (default 30)
        
    Returns:
        Session object, None if not found, or None if expired (also deletes it)
    """
    session = sessions.get(session_id)
    
    if not session:
        return None
    
    # Check if expired
    if session.is_expired(ttl_minutes):
        # Clean up expired session
        delete_session(session_id)
        return None
    
    # Update last accessed time
    session.touch()
    
    return session


def cleanup_expired_sessions(ttl_minutes: int = 30):
    """
    Remove sessions that have exceeded TTL since last access.
    
    Args:
        ttl_minutes: Time-to-live in minutes (default 30)
        
    Returns:
        Number of sessions cleaned up
    """
    to_delete = []
    
    for session_id, session in sessions.items():
        if session.is_expired(ttl_minutes):
            # Save logs before deletion
            try:
                session.logger.save_session()
            except:
                pass
            to_delete.append(session_id)
    
    for session_id in to_delete:
        del sessions[session_id]
    
    return len(to_delete)


def get_session_count() -> int:
    """Get total number of active sessions."""
    return len(sessions)


def delete_session(session_id: str) -> bool:
    """
    Delete a specific session.
    
    Args:
        session_id: Session UUID
        
    Returns:
        True if deleted, False if not found
    """
    if session_id in sessions:
        # Save logs before deletion
        try:
            sessions[session_id].logger.save_session()
        except:
            pass
        del sessions[session_id]
        return True
    return False

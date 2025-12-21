"""
Session Management API for maintaining context across long conversations.
Provides session summarization and context injection to overcome chat history limits.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import json
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/session", tags=["session"])

# Session storage directory
SESSION_DIR = Path(__file__).parent.parent / "static" / "appdocs" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


class SessionSummary(BaseModel):
    """Session summary data"""
    key_points: List[str] = Field(default_factory=list, description="Key points from the conversation")
    decisions: List[str] = Field(default_factory=list, description="Decisions made")
    pending_items: List[str] = Field(default_factory=list, description="Pending items or actions")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")


class SummarizeSessionRequest(BaseModel):
    """Request to create or update a session summary"""
    session_type: str = Field(..., description="Type of session: vision_meeting, requirements_meeting, sprint_review, sprint_planning, chat")
    session_id: str = Field(..., description="Unique session identifier")
    summary: SessionSummary = Field(..., description="Session summary data")
    turn_number: int = Field(..., description="Current turn number when summary was created")


class SummarizeSessionResponse(BaseModel):
    """Response from session summarization"""
    success: bool
    session_id: str
    session_file: str
    message: str


class GetContextRequest(BaseModel):
    """Request to get session context"""
    session_type: str = Field(..., description="Type of session")
    session_id: str = Field(..., description="Session identifier")


class GetContextResponse(BaseModel):
    """Response with session context"""
    success: bool
    session_id: str
    has_context: bool
    summary: Optional[SessionSummary] = None
    last_updated: Optional[str] = None
    turn_number: Optional[int] = None
    message: Optional[str] = None


class SessionStatus(BaseModel):
    """Session status information"""
    session_id: str
    session_type: str
    last_updated: str
    turn_number: int
    summary_exists: bool


class ListSessionsResponse(BaseModel):
    """Response with list of active sessions"""
    success: bool
    sessions: List[SessionStatus]
    message: str


def get_session_file_path(session_type: str, session_id: str) -> Path:
    """Get the file path for a session"""
    # Sanitize session_id to prevent path traversal
    safe_session_id = session_id.replace("/", "_").replace("\\", "_").replace("..", "_")
    filename = f"{session_type}_{safe_session_id}_session.json"
    return SESSION_DIR / filename


@router.post("/summarize", response_model=SummarizeSessionResponse)
async def summarize_session(request: SummarizeSessionRequest):
    """
    Create or update a session summary.
    
    This endpoint stores a summary of the conversation so far, which can be
    injected into future turns to overcome chat history limits.
    
    Usage:
    - Call this every 5-7 turns during long conversations
    - Summary should capture key points, decisions, and pending items
    - Context can store any additional structured data
    """
    try:
        session_file = get_session_file_path(request.session_type, request.session_id)
        
        # Create session data
        session_data = {
            "session_type": request.session_type,
            "session_id": request.session_id,
            "last_updated": datetime.now().isoformat(),
            "turn_number": request.turn_number,
            "summary": {
                "key_points": request.summary.key_points,
                "decisions": request.summary.decisions,
                "pending_items": request.summary.pending_items,
                "context": request.summary.context
            }
        }
        
        # Save to file
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        logger.info(f"Session summary saved: {session_file.name} (turn {request.turn_number})")
        
        return SummarizeSessionResponse(
            success=True,
            session_id=request.session_id,
            session_file=session_file.name,
            message=f"Session summary saved successfully at turn {request.turn_number}"
        )
        
    except Exception as e:
        logger.error(f"Error saving session summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving session summary: {str(e)}")


@router.post("/get-context", response_model=GetContextResponse)
async def get_session_context(request: GetContextRequest):
    """
    Get the current session context/summary.
    
    This endpoint retrieves the stored session summary, which should be
    injected into the conversation context to maintain continuity.
    """
    try:
        session_file = get_session_file_path(request.session_type, request.session_id)
        
        if not session_file.exists():
            return GetContextResponse(
                success=True,
                session_id=request.session_id,
                has_context=False,
                message="No session context found"
            )
        
        # Load session data
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        summary_data = session_data.get("summary", {})
        summary = SessionSummary(
            key_points=summary_data.get("key_points", []),
            decisions=summary_data.get("decisions", []),
            pending_items=summary_data.get("pending_items", []),
            context=summary_data.get("context", {})
        )
        
        logger.info(f"Session context retrieved: {session_file.name}")
        
        return GetContextResponse(
            success=True,
            session_id=request.session_id,
            has_context=True,
            summary=summary,
            last_updated=session_data.get("last_updated"),
            turn_number=session_data.get("turn_number"),
            message="Session context retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving session context: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving session context: {str(e)}")


@router.get("/list", response_model=ListSessionsResponse)
async def list_sessions():
    """List all active sessions"""
    try:
        sessions = []
        
        for session_file in SESSION_DIR.glob("*_session.json"):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                sessions.append(SessionStatus(
                    session_id=session_data.get("session_id", "unknown"),
                    session_type=session_data.get("session_type", "unknown"),
                    last_updated=session_data.get("last_updated", "unknown"),
                    turn_number=session_data.get("turn_number", 0),
                    summary_exists=True
                ))
            except Exception as e:
                logger.warning(f"Error reading session file {session_file.name}: {e}")
                continue
        
        # Sort by last_updated (most recent first)
        sessions.sort(key=lambda s: s.last_updated, reverse=True)
        
        return ListSessionsResponse(
            success=True,
            sessions=sessions,
            message=f"Found {len(sessions)} active sessions"
        )
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")


@router.delete("/clear/{session_type}/{session_id}")
async def clear_session(session_type: str, session_id: str):
    """Clear a session summary"""
    try:
        session_file = get_session_file_path(session_type, session_id)
        
        if not session_file.exists():
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        
        session_file.unlink()
        
        logger.info(f"Session cleared: {session_file.name}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Session cleared successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")


@router.get("/status")
async def get_session_status():
    """Get session management status"""
    try:
        session_count = len(list(SESSION_DIR.glob("*_session.json")))
        
        return {
            "success": True,
            "session_dir": str(SESSION_DIR),
            "session_dir_exists": SESSION_DIR.exists(),
            "active_sessions": session_count,
            "message": f"Session management active with {session_count} sessions"
        }
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting session status: {str(e)}")

"""
Conversation History Management for SPRINT_REVIEW_ALEX
Stores and retrieves conversation history to enable multi-turn context.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# History storage directory
HISTORY_DIR = Path(__file__).parent.parent / "static" / "appdocs" / "conversation_history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def get_history_file_path(session_id: str, persona_key: str) -> Path:
    """Get the file path for conversation history"""
    safe_session_id = session_id.replace("/", "_").replace("\\", "_").replace("..", "_")
    filename = f"{persona_key}_{safe_session_id}_history.json"
    return HISTORY_DIR / filename


def save_conversation_turn(
    session_id: str,
    persona_key: str,
    user_message: str,
    assistant_response: str,
    tool_calls: Optional[List[Dict]] = None
):
    """
    Save a conversation turn to history.
    
    Args:
        session_id: Unique identifier for the conversation session
        persona_key: Persona identifier (e.g., "SPRINT_REVIEW_ALEX")
        user_message: The user's message
        assistant_response: The assistant's response
        tool_calls: Optional list of tool calls made during this turn
    """
    try:
        history_file = get_history_file_path(session_id, persona_key)
        
        # Load existing history or create new
        if history_file.exists():
            with open(history_file, 'r') as f:
                history_data = json.load(f)
        else:
            history_data = {
                "session_id": session_id,
                "persona_key": persona_key,
                "created_at": datetime.now().isoformat(),
                "turns": []
            }
        
        # Add new turn
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "assistant_response": assistant_response,
            "tool_calls": tool_calls or []
        }
        
        history_data["turns"].append(turn)
        history_data["last_updated"] = datetime.now().isoformat()
        
        # Keep only last 10 turns to prevent file from growing too large
        if len(history_data["turns"]) > 10:
            history_data["turns"] = history_data["turns"][-10:]
        
        # Save to file
        with open(history_file, 'w') as f:
            json.dump(history_data, f, indent=2)
        
        logger.info(f"Saved conversation turn for {persona_key} in session {session_id}")
        
    except Exception as e:
        logger.error(f"Error saving conversation turn: {e}")


def get_conversation_history(session_id: str, persona_key: str, max_turns: int = 5) -> List[Dict]:
    """
    Get conversation history for a session.
    
    Args:
        session_id: Unique identifier for the conversation session
        persona_key: Persona identifier
        max_turns: Maximum number of turns to retrieve (default: 5)
    
    Returns:
        List of message dictionaries in OpenAI format
    """
    try:
        history_file = get_history_file_path(session_id, persona_key)
        
        if not history_file.exists():
            return []
        
        with open(history_file, 'r') as f:
            history_data = json.load(f)
        
        # Get last N turns
        turns = history_data.get("turns", [])[-max_turns:]
        
        # Convert to OpenAI message format
        messages = []
        for turn in turns:
            messages.append({
                "role": "user",
                "content": turn["user_message"]
            })
            messages.append({
                "role": "assistant",
                "content": turn["assistant_response"]
            })
        
        logger.info(f"Retrieved {len(turns)} conversation turns for {persona_key} in session {session_id}")
        return messages
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        return []


def clear_conversation_history(session_id: str, persona_key: str):
    """Clear conversation history for a session"""
    try:
        history_file = get_history_file_path(session_id, persona_key)
        if history_file.exists():
            history_file.unlink()
            logger.info(f"Cleared conversation history for {persona_key} in session {session_id}")
    except Exception as e:
        logger.error(f"Error clearing conversation history: {e}")

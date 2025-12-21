"""
Scribe API - Background meeting recorder and memory system.
Automatically captures conversations, decisions, and client agreements.
"""

import os
import json
import re
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal, Tuple
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["scribe"])

# Scribe storage directory - single source of truth
SCRIBE_DIR = Path("static/appdocs/scribe")

def ensure_scribe_dir():
    """Ensure scribe directory exists"""
    SCRIBE_DIR.mkdir(parents=True, exist_ok=True)

def get_scribe_dir(project_id: str = None) -> Path:
    """Get scribe directory for current or specified project (legacy compatibility)"""
    ensure_scribe_dir()
    return SCRIBE_DIR

# Strict Pydantic models for fail-fast validation
class Decision(BaseModel):
    title: str = Field(min_length=1)
    details: str = ""
    refs: List[str] = []

class SignOff(BaseModel):
    who: str = Field(min_length=1)
    what: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)
    
    @field_validator("timestamp")
    @classmethod
    def ts_is_iso_like(cls, v: str) -> str:
        import re
        if re.match(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", v):
            return v
        raise ValueError("timestamp must be ISO-like, e.g., 2025-10-04 20:46:02")

class ActionItem(BaseModel):
    owner: str = ""
    task: str = Field(min_length=1)
    due: str = ""

class BacklogDelta(BaseModel):
    type: Literal["add", "update", "remove", "wf"]
    id: str = ""
    title: str = ""

class Risk(BaseModel):
    risk: str
    mitigation: str = ""

class ScribeSummary(BaseModel):
    summary: str = Field(min_length=1)
    decisions: List[Decision] = []
    sign_offs: List[SignOff] = []
    actions: List[ActionItem] = []
    backlog_deltas: List[BacklogDelta] = []
    risks: List[Risk] = []
    participants: Optional[List[str]] = None

def parse_ai_summary_strict(text: str) -> ScribeSummary:
    """Parse AI summary with strict JSON validation - no fallbacks"""
    try:
        raw = json.loads(text)
    except Exception as e:
        raise ValueError(f"Invalid JSON from model: {e}")
    try:
        return ScribeSummary(**raw)
    except ValidationError as e:
        raise ValueError(f"Schema validation failed: {e}")

def new_conv_id() -> str:
    """Generate new conversation ID"""
    return uuid.uuid4().hex

def json_path_for(conv_id: str) -> Path:
    """Get JSON path for conversation ID - single source of filename truth"""
    return SCRIBE_DIR / f"conv_{conv_id}.json"

def save_scribe_json(conv_id: str, data: ScribeSummary) -> Path:
    """Save machine-readable Scribe data"""
    ensure_scribe_dir()
    p = json_path_for(conv_id)
    p.write_text(data.model_dump_json(indent=2, exclude_none=False))
    return p

def _load_all_summaries_with_mtime() -> List[Tuple[ScribeSummary, float]]:
    """Load all summaries with file modification times - strict validation"""
    ensure_scribe_dir()
    files = sorted(SCRIBE_DIR.glob("conv_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for f in files:
        raw = json.loads(f.read_text())  # fail fast on bad JSON
        summ = ScribeSummary(**raw)  # fail fast on bad schema
        out.append((summ, f.stat().st_mtime))
    return out

def build_overview(limit_recent: int = 10) -> dict:
    """Build overview from conv_*.json files with per-file mtime timestamps"""
    items = _load_all_summaries_with_mtime()
    notes_count = len(items)
    decisions_total = sum(len(s.decisions) for s, _ in items)
    agreements_total = sum(len(s.sign_offs) for s, _ in items)
    
    recent = []
    for s, mtime in items[:limit_recent]:
        ts = time.strftime("%m/%d %H:%M", time.localtime(mtime))  # per-file time
        participants = s.participants or []
        title = f"Latest meeting with {', '.join(participants) or 'team'} - {ts}"
        recent.append({
            "title": title,
            "summary": s.summary,
            "decisions": [d.model_dump() for d in s.decisions],
            "actions": [a.model_dump() for a in s.actions],
            "sign_offs": [sg.model_dump() for sg in s.sign_offs],
        })
    
    return {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "totals": {"notes": notes_count, "decisions": decisions_total, "agreements": agreements_total},
        "recent": recent
    }


class ConversationEntry(BaseModel):
    timestamp: str
    participants: List[str]
    messages: List[Dict[str, str]]  # [{"persona": "Sarah", "message": "..."}]
    summary: Optional[str] = None

class MeetingNote(BaseModel):
    id: str
    timestamp: str
    participants: List[str]
    summary: str
    key_points: List[str]
    decisions: List[str]
    action_items: List[str]
    conversation_id: Optional[str] = None

class ClientAgreement(BaseModel):
    id: str
    type: str  # "vision_approval", "requirements_signoff", "sprint_acceptance"
    content: str
    timestamp: str
    status: str  # "proposed", "agreed", "signed_off"
    related_artifact: Optional[str] = None

class Decision(BaseModel):
    id: str
    decision: str
    rationale: str
    decided_by: str
    approved_by: Optional[str] = None
    timestamp: str
    conversation_id: Optional[str] = None

class ScribeRequest(BaseModel):
    action: str  # "record_conversation", "add_decision", "add_agreement", "get_memory", "get_summary"
    conversation: Optional[ConversationEntry] = None
    decision: Optional[Decision] = None
    agreement: Optional[ClientAgreement] = None
    query: Optional[str] = None  # For memory retrieval

class ScribeResponse(BaseModel):
    success: bool
    message: str
    memory_context: Optional[List[Dict]] = None
    summary: Optional[str] = None

@router.post("/scribe")
async def handle_scribe_request(request: ScribeRequest):
    """Handle scribe operations"""
    logger.info(f"Scribe request - Action: {request.action}")
    
    if request.action == "record_conversation":
        return await record_conversation(request.conversation)
    elif request.action == "add_decision":
        return await add_decision(request.decision)
    elif request.action == "add_agreement":
        return await add_agreement(request.agreement)
    elif request.action == "get_memory":
        return await get_memory_context(request.query)
    elif request.action in ("get_summary", "overview"):
        try:
            data = build_overview(limit_recent=10)
            return JSONResponse(data)
        except Exception as e:
            logger.error(f"Scribe overview failed: {e}")
            return JSONResponse(
                {"error": "SCRIBE_OVERVIEW_ERROR", "detail": str(e)},
                status_code=500
            )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

async def record_conversation(conversation: ConversationEntry, model: str = None) -> ScribeResponse:
    """Record a conversation and automatically extract meeting notes"""
    try:
        scribe_dir = get_scribe_dir()
        
        # Generate conversation ID
        conv_id = f"conv_{uuid.uuid4().hex[:8]}"
        conversation_data = conversation.dict()
        conversation_data["id"] = conv_id
        
        # Save raw conversation
        conv_file = scribe_dir / f"conversations_{datetime.now().strftime('%Y%m%d')}.json"
        conversations = []
        if conv_file.exists():
            with open(conv_file, 'r') as f:
                conversations = json.load(f)
        
        conversations.append(conversation_data)
        with open(conv_file, 'w') as f:
            json.dump(conversations, f, indent=2)
        
        # Auto-generate meeting notes using AI processing
        meeting_note = await process_conversation_to_notes(conversation_data, model)
        if meeting_note:
            await save_meeting_note(meeting_note)
        
        logger.info(f"Recorded conversation: {conv_id}")
        return ScribeResponse(
            success=True,
            message=f"Conversation recorded and processed"
        )
        
    except Exception as e:
        logger.error(f"Error recording conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _parse_and_validate_ai_summary(result: Any, model_name: str) -> Dict[str, Any]:
    """Parse and validate AI summary response with defensive handling.
    
    Args:
        result: AI response (dict, tuple/list, or string)
        model_name: Name of the model used for logging
        
    Returns:
        Dict with keys: summary (str), decisions (list[str]), actions (list[str])
    """
    # Initialize default structure
    normalized = {
        "summary": "",
        "decisions": [],
        "actions": []
    }
    
    # Determine input type for logging
    input_type = type(result).__name__
    
    try:
        if isinstance(result, dict):
            # Extract and normalize dict fields
            summary = result.get("summary", "")
            decisions = result.get("decisions", result.get("action_items", []))
            actions = result.get("action_items", result.get("actions", []))
            
            # Type coercion
            normalized["summary"] = str(summary) if summary else ""
            normalized["decisions"] = [str(x) for x in (decisions or [])]
            normalized["actions"] = [str(x) for x in (actions or [])]
            
        elif isinstance(result, (tuple, list)):
            # Handle tuple/list unpacking
            if len(result) >= 3:
                normalized["summary"] = str(result[0]) if result[0] else ""
                normalized["decisions"] = [str(x) for x in (result[1] or [])]
                normalized["actions"] = [str(x) for x in (result[2] or [])]
            elif len(result) >= 1:
                normalized["summary"] = str(result[0]) if result[0] else ""
                
        elif isinstance(result, str):
            # String fallback - use as summary
            normalized["summary"] = result.strip() if result else ""
            
        else:
            # Unknown type fallback
            normalized["summary"] = str(result) if result else ""
            
    except Exception as parse_error:
        logger.warning(f"Error parsing AI summary from {model_name}: {parse_error}")
        # Keep defaults on parse error
    
    # Log structured info about type/shape (no content dump)
    decisions_count = len(normalized["decisions"])
    actions_count = len(normalized["actions"])
    summary_length = len(normalized["summary"])
    
    logger.info(f"scribe summary parsed from {model_name}: type={input_type}, "
                f"summary_chars={summary_length}, decisions={decisions_count}, actions={actions_count}")
    
    # WARNING only if all fields empty
    if not normalized["summary"] and not normalized["decisions"] and not normalized["actions"]:
        logger.warning(f"AI summary from {model_name} resulted in empty content across all fields")
    
    return normalized


async def process_conversation_to_notes(conversation: Dict, model: str = None) -> Optional[MeetingNote]:
    """Process conversation using AI to extract structured meeting notes with enhanced tracking"""
    try:
        # Extract key information from conversation
        messages = conversation.get("messages", [])
        if not messages:
            return None
        
        # Use AI to intelligently summarize the conversation
        from services.ai_gateway import call_openrouter_api
        from core.models_config import ModelsConfig
        
        # Use provided model or fall back to config
        if not model:
            models_config = ModelsConfig()
            favorites, default_model, meta, last_session_name = models_config.load_config()
            model = default_model
        
        # Build conversation text for AI analysis
        conversation_text = ""
        participants = conversation.get("participants", [])
        for msg in messages:
            persona = msg.get("persona", "Unknown")
            message = msg.get("message", "")
            if message.strip():  # Only include non-empty messages
                conversation_text += f"{persona}: {message}\n"
        
        # Skip if no meaningful conversation
        if not conversation_text.strip():
            logger.info("No meaningful conversation content to summarize")
            return None
        
        # Strict AI prompt matching ScribeSummary schema
        summarization_prompt = f"""Analyze this conversation as a meeting scribe and extract structured information.

Conversation:
{conversation_text}

Respond in this EXACT JSON format with objects (not strings):
{{
    "summary": "Brief 1-2 sentence summary of the meeting",
    "decisions": [
        {{"title": "Decision made", "details": "Optional details", "refs": []}}
    ],
    "sign_offs": [
        {{"who": "Person name", "what": "What they approved/agreed to", "timestamp": "2025-10-05 09:09:49"}}
    ],
    "actions": [
        {{"owner": "Person responsible", "task": "Task description", "due": "Optional due date"}}
    ],
    "backlog_deltas": [
        {{"type": "add", "id": "Optional ID", "title": "Change description"}}
    ],
    "risks": [
        {{"risk": "Risk description", "mitigation": "How to mitigate"}}
    ],
    "participants": ["Person1", "Person2"]
}}

CRITICAL: 
- decisions, sign_offs, actions, backlog_deltas, risks MUST be arrays of objects, NOT strings
- sign_offs.timestamp must be in format "YYYY-MM-DD HH:MM:SS"
- backlog_deltas.type must be one of: "add", "update", "remove", "wf"
- Empty arrays are OK, but items must be objects when present"""

        try:
            # Use provided model or fall back to config
            if not model:
                models_config = ModelsConfig()
                favorites, default_model, meta, last_session_name = models_config.load_config()
                model = default_model
            
            # Call AI for summarization
            messages_for_ai = [
                {"role": "user", "content": summarization_prompt}
            ]
            
            logger.info(f"Calling AI for conversation summarization with {len(messages)} messages")
            
            # Iterate through async generator to get final response
            ai_response = None
            async for chunk in call_openrouter_api(messages_for_ai, model, "Scribe", "SCRIBE"):
                if "content" in chunk:
                    ai_response = chunk["content"]
                    break
            
            if ai_response:
                logger.info(f"OpenRouter API success for Scribe: {len(ai_response)} chars")
                
                # Use strict parser - fail fast on invalid JSON/schema
                try:
                    scribe_data = parse_ai_summary_strict(ai_response)
                except ValueError as parse_error:
                    logger.error(f"Scribe validation error: {parse_error}")
                    # Return 422 for validation errors
                    raise HTTPException(
                        status_code=422,
                        detail={"error": "SCRIBE_VALIDATION_ERROR", "detail": str(parse_error)}
                    )
                
                # Save JSON only (MD is deprecated)
                conv_id = conversation.get("id") or new_conv_id()
                json_path = save_scribe_json(conv_id, scribe_data)
                
                logger.info(f"Scribe JSON validated and saved: {json_path}")
                
                # Extract fields for MeetingNote
                summary = scribe_data.summary or "Meeting discussion"
                decisions = [d.title for d in scribe_data.decisions]
                action_items = [a.task for a in scribe_data.actions]
                key_points = []
                
                # Extract sign-offs as client approvals for backwards compatibility
                client_approvals = [s.what for s in scribe_data.sign_offs]
                if client_approvals:
                    await auto_record_client_agreements(client_approvals, conversation.get("id"))
                
                logger.info(f"AI summarization successful: {len(decisions)} decisions, {len(action_items)} actions, {len(client_approvals)} sign-offs")
            else:
                logger.warning("No AI response received")
                raise Exception("No AI response")
                
        except Exception as ai_error:
            logger.warning(f"AI summarization failed: {ai_error}, using basic processing")
            # Fallback to basic keyword matching
            key_points = []
            decisions = []
            action_items = []
            
            for msg in messages:
                content = msg.get("message", "").lower()
                message_text = msg.get("message", "")
                
                # Look for decision indicators
                if any(word in content for word in ["decided", "agree", "approved", "will use", "going with", "sign off", "accept"]):
                    decisions.append(message_text)
                
                # Look for action items
                if any(word in content for word in ["will", "should", "need to", "action:", "todo", "next step"]):
                    action_items.append(message_text)
                
                # Key points (non-trivial messages)
                if len(message_text) > 20:
                    key_points.append(message_text)
            
            # Generate basic summary
            summary = f"Meeting with {', '.join(participants)}. {len(decisions)} decisions made, {len(action_items)} action items identified."
        
        meeting_note = MeetingNote(
            id=f"note_{uuid.uuid4().hex[:8]}",
            timestamp=conversation.get("timestamp", datetime.now().isoformat()),
            participants=conversation.get("participants", []),
            summary=summary,
            key_points=key_points[:10],  # Limit to top 10
            decisions=decisions[:5],     # Limit to top 5
            action_items=action_items[:5], # Limit to top 5
            conversation_id=conversation.get("id")
        )
        
        return meeting_note
        
    except Exception as e:
        logger.error(f"Error processing conversation: {e}")
        return None

async def auto_record_client_agreements(approvals: List[str], conversation_id: str):
    """Automatically record client agreements detected in conversations"""
    try:
        for approval in approvals:
            agreement = ClientAgreement(
                id=f"agr_{uuid.uuid4().hex[:8]}",
                type="conversation_approval",
                content=approval,
                timestamp=datetime.now().isoformat(),
                status="agreed",
                related_artifact=conversation_id
            )
            await add_agreement(agreement)
            logger.debug(f"Auto-recorded client agreement: {approval[:50]}...")
    except Exception as e:
        logger.error(f"Error auto-recording agreements: {e}")

async def save_meeting_note(note: MeetingNote):
    """Save meeting note to storage"""
    try:
        scribe_dir = get_scribe_dir()
        notes_file = scribe_dir / "meeting_notes.json"
        
        notes = []
        if notes_file.exists():
            with open(notes_file, 'r') as f:
                notes = json.load(f)
        
        notes.append(note.dict())
        with open(notes_file, 'w') as f:
            json.dump(notes, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error saving meeting note: {e}")

async def add_decision(decision: Decision) -> ScribeResponse:
    """Add a decision to the decision log"""
    try:
        scribe_dir = get_scribe_dir()
        decisions_file = scribe_dir / "decisions.json"
        
        decisions = []
        if decisions_file.exists():
            with open(decisions_file, 'r') as f:
                decisions = json.load(f)
        
        decision_data = decision.dict()
        if not decision_data.get("id"):
            decision_data["id"] = f"dec_{uuid.uuid4().hex[:8]}"
        
        decisions.append(decision_data)
        with open(decisions_file, 'w') as f:
            json.dump(decisions, f, indent=2)
        
        logger.info(f"Added decision: {decision_data['id']}")
        return ScribeResponse(
            success=True,
            message="Decision recorded"
        )
        
    except Exception as e:
        logger.error(f"Error adding decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def add_agreement(agreement: ClientAgreement) -> ScribeResponse:
    """Add a client agreement to the agreements log"""
    try:
        scribe_dir = get_scribe_dir()
        agreements_file = scribe_dir / "agreements.json"
        
        agreements = []
        if agreements_file.exists():
            with open(agreements_file, 'r') as f:
                agreements = json.load(f)
        
        agreement_data = agreement.dict()
        if not agreement_data.get("id"):
            agreement_data["id"] = f"agr_{uuid.uuid4().hex[:8]}"
        
        agreements.append(agreement_data)
        with open(agreements_file, 'w') as f:
            json.dump(agreements, f, indent=2)
        
        logger.debug(f"Added agreement: {agreement_data['id']}")
        return ScribeResponse(
            success=True,
            message="Client agreement recorded"
        )
        
    except Exception as e:
        logger.error(f"Error adding agreement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_memory_context(query: str = None) -> ScribeResponse:
    """Retrieve relevant memory context for AI personas with enhanced project continuity"""
    try:
        scribe_dir = get_scribe_dir()
        memory_context = []
        
        # Load meeting notes with enhanced context
        notes_file = scribe_dir / "meeting_notes.json"
        if notes_file.exists():
            with open(notes_file, 'r') as f:
                notes = json.load(f)
            
            # Filter by query if provided
            if query:
                query_lower = query.lower()
                relevant_notes = [
                    note for note in notes
                    if query_lower in note.get("summary", "").lower() or
                       any(query_lower in point.lower() for point in note.get("key_points", []))
                ]
            else:
                relevant_notes = notes[-5:]  # Last 5 notes
            
            memory_context.extend([{"type": "meeting_note", "data": note} for note in relevant_notes])
        
        # Load decisions
        decisions_file = scribe_dir / "decisions.json"
        if decisions_file.exists():
            with open(decisions_file, 'r') as f:
                decisions = json.load(f)
            
            if query:
                query_lower = query.lower()
                relevant_decisions = [
                    dec for dec in decisions
                    if query_lower in dec.get("decision", "").lower() or
                       query_lower in dec.get("rationale", "").lower()
                ]
            else:
                relevant_decisions = decisions[-3:]  # Last 3 decisions
            
            memory_context.extend([{"type": "decision", "data": dec} for dec in relevant_decisions])
        
        # Load agreements
        agreements_file = scribe_dir / "agreements.json"
        if agreements_file.exists():
            with open(agreements_file, 'r') as f:
                agreements = json.load(f)
            
            if query:
                query_lower = query.lower()
                relevant_agreements = [
                    agr for agr in agreements
                    if query_lower in agr.get("content", "").lower()
                ]
            else:
                relevant_agreements = agreements[-3:]  # Last 3 agreements
            
            memory_context.extend([{"type": "agreement", "data": agr} for agr in relevant_agreements])
        
        return ScribeResponse(
            success=True,
            message=f"Retrieved {len(memory_context)} memory items",
            memory_context=memory_context
        )
        
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_persona_context(persona_key: str) -> str:
    """Get relevant project context for a specific persona to enhance their responses"""
    try:
        memory_response = await get_memory_context()
        if not memory_response.success or not memory_response.memory_context:
            return ""
        
        # Build context string tailored to persona role
        context_parts = []
        
        for item in memory_response.memory_context:
            item_type = item["type"]
            data = item["data"]
            
            if item_type == "meeting_note":
                summary = data.get("summary", "")
                key_points = data.get("key_points", [])
                action_items = data.get("action_items", [])
                
                if persona_key == "PM" and (action_items or "vision" in summary.lower()):
                    context_parts.append(f"Previous meeting: {summary}")
                    if action_items:
                        context_parts.append(f"Outstanding actions: {'; '.join(action_items[:2])}")
                
                elif persona_key == "ARCHITECT" and ("design" in summary.lower() or "architecture" in summary.lower()):
                    context_parts.append(f"Architecture context: {summary}")
                    
                elif persona_key == "DEVELOPER" and ("code" in summary.lower() or "development" in summary.lower()):
                    context_parts.append(f"Development history: {summary}")
                    
                elif persona_key == "QA" and ("test" in summary.lower() or "validation" in summary.lower()):
                    context_parts.append(f"Testing context: {summary}")
            
            elif item_type == "decision" and len(context_parts) < 3:
                decision = data.get("decision", "")
                context_parts.append(f"Previous decision: {decision}")
            
            elif item_type == "agreement" and len(context_parts) < 3:
                content = data.get("content", "")
                context_parts.append(f"Client agreement: {content}")
        
        if context_parts:
            return f"\n\nProject Context:\n" + "\n".join(f"- {part}" for part in context_parts[:3])
        
        return ""
        
    except Exception as e:
        logger.error(f"Error getting persona context for {persona_key}: {e}")
        return ""

async def get_meeting_summary() -> ScribeResponse:
    """Get a human-readable summary of recent meetings and decisions"""
    try:
        scribe_dir = get_scribe_dir()
        
        # Load and analyze recent items
        notes_count = 0
        decisions_count = 0
        agreements_count = 0
        recent_conversations = []
        
        notes_file = scribe_dir / "meeting_notes.json"
        if notes_file.exists():
            with open(notes_file, 'r') as f:
                notes = json.load(f)
            notes_count = len(notes)
            
            # Get recent conversations with actual content
            for note in notes[-10:]:  # Last 10 conversations
                participants = ", ".join([p for p in note.get('participants', []) if p != 'client'])
                summary_text = note.get('summary', 'No summary available')
                key_points = note.get('key_points', [])
                action_items = note.get('action_items', [])
                
                # Format timestamp
                timestamp = note.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%m/%d %H:%M')
                    except:
                        formatted_time = timestamp[:16]  # Fallback to first 16 chars
                else:
                    formatted_time = 'Unknown time'
                
                conv_summary = f"<strong>Latest meeting with {participants} - {formatted_time}</strong><br>"
                conv_summary += f"&nbsp;&nbsp;📝 {summary_text}<br>"
                
                if key_points:
                    conv_summary += f"&nbsp;&nbsp;🔑 Key points: {'; '.join(key_points[:2])}<br>"
                
                if action_items:
                    conv_summary += f"&nbsp;&nbsp;📋 Actions: {'; '.join(action_items[:2])}<br>"
                
                recent_conversations.append(conv_summary)
        
        decisions_file = scribe_dir / "decisions.json"
        if decisions_file.exists():
            with open(decisions_file, 'r') as f:
                decisions = json.load(f)
            decisions_count = len(decisions)
        
        agreements_file = scribe_dir / "agreements.json"
        if agreements_file.exists():
            with open(agreements_file, 'r') as f:
                agreements = json.load(f)
            agreements_count = len(agreements)
        
        # Create human-readable summary with actual content and timestamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if notes_count == 0 and decisions_count == 0 and agreements_count == 0:
            summary = "📋 <strong>Project Memory</strong><br>"
            summary += "No meeting data recorded yet. Start a conversation with the AI team to begin building project memory.<br><br>"
            summary += f"<small style='color: #6c757d;'>Generated: {current_time} | Displaying: ALL available data</small>"
        else:
            summary = "📋 <strong>Project Memory Overview</strong><br><br>"
            summary += f"📝 <strong>{notes_count}</strong> meeting notes recorded<br>"
            summary += f"✅ <strong>{decisions_count}</strong> decisions logged<br>"
            summary += f"🤝 <strong>{agreements_count}</strong> client agreements tracked<br><br>"
            
            if recent_conversations:
                summary += "<strong>Recent Activity (Last 10 meetings):</strong><br>"
                for conv in recent_conversations:
                    summary += f"• {conv}<br>"
            
            summary += f"<br><small style='color: #6c757d;'>Generated: {current_time} | Displaying: ALL {notes_count} notes, {decisions_count} decisions, {agreements_count} agreements</small>"
        
        return ScribeResponse(
            success=True,
            message="Meeting summary generated",
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Conversation turn aggregation for full context capture
conversation_turns = {}
conversation_session = {}  # Track ongoing conversation sessions

async def start_conversation_turn(turn_id: str, client_message: str):
    """Start a new conversation turn with client message"""
    conversation_turns[turn_id] = {
        "timestamp": datetime.now().isoformat(),
        "client_message": client_message,
        "persona_responses": {},
        "participants": ["client"]
    }

async def add_persona_response(turn_id: str, persona: str, message: str):
    """Add a persona response to the conversation turn"""
    if turn_id in conversation_turns:
        conversation_turns[turn_id]["persona_responses"][persona] = message
        if persona not in conversation_turns[turn_id]["participants"]:
            conversation_turns[turn_id]["participants"].append(persona)

async def complete_conversation_turn(turn_id: str, model: str = None):
    """Complete and process the full conversation turn with intelligent batching"""
    if turn_id not in conversation_turns:
        return
        
    try:
        turn_data = conversation_turns[turn_id]
        client_message = turn_data["client_message"].lower().strip()
        
        # Skip recording for trivial interactions that don't need scribe attention
        trivial_patterns = [
            "hi team", "hello", "thanks", "ok", "got it", "sure", "yes", "no",
            "test", "testing", "check", "status", "ping"
        ]
        
        # Only record meaningful conversations
        is_meaningful = len(turn_data["client_message"]) > 10 and not any(
            pattern in client_message for pattern in trivial_patterns
        )
        
        # Also record if there are tool calls or significant responses
        has_tool_calls = any(
            "✅" in response or "❌" in response or len(response) > 50
            for response in turn_data["persona_responses"].values()
        )
        
        if not (is_meaningful or has_tool_calls):
            logger.debug(f"Skipping scribe recording for trivial interaction: {client_message[:50]}")
            del conversation_turns[turn_id]
            return
        
        # Build complete conversation with all messages
        messages = []
        
        # Add client message first
        messages.append({
            "persona": "client", 
            "message": turn_data["client_message"]
        })
        
        # Add all persona responses
        for persona, response in turn_data["persona_responses"].items():
            messages.append({
                "persona": persona,
                "message": response
            })
        
        # Create full conversation entry
        conversation = ConversationEntry(
            timestamp=turn_data["timestamp"],
            participants=turn_data["participants"],
            messages=messages
        )
        
        # Process the complete conversation
        await record_conversation(conversation, model)
        
        # Clean up
        del conversation_turns[turn_id]
        
    except Exception as e:
        logger.error(f"Error completing conversation turn {turn_id}: {e}")
        # Clean up on error
        if turn_id in conversation_turns:
            del conversation_turns[turn_id]

# Background conversation processing hook (deprecated - use turn-based system)
async def process_chat_message(message: str, persona: str, timestamp: str = None):
    """Hook called by chat API to automatically process conversations"""
    try:
        if not timestamp:
            timestamp = datetime.now().isoformat()
        
        # Simple conversation entry for background processing
        conversation = ConversationEntry(
            timestamp=timestamp,
            participants=["client", persona],
            messages=[{"persona": persona, "message": message}]
        )
        
        # Record in background (don't wait for response)
        await record_conversation(conversation)
        
    except Exception as e:
        logger.error(f"Background conversation processing error: {e}")
        # Don't raise - this is background processing

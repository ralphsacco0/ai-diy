"""
AI-First Streaming Endpoint - Minimal code, maximum AI intelligence.
"""
import os
import json
import uuid
import asyncio
import logging
import re
import hashlib
import random
from typing import Dict, List, AsyncGenerator
from pathlib import Path
import aiohttp
import ssl
from fastapi import HTTPException, APIRouter
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
# call_openrouter_api function is defined in this file
# load_personas function is defined in this file

# Load environment variables
load_dotenv()

# Import unified logging system
from core.logging_config import get_structured_logger
from core.project_metadata import get_project_name, get_project_name_safe

logger = get_structured_logger("streaming")

# Configuration for filtering "No comment" responses
EAT_NO_COMMENT = os.getenv("EAT_NO_COMMENT", "true").lower() in ("1", "true", "yes")
NO_COMMENT_RE = re.compile(r"^\s*(no\s+comment(?:\s*\(reason:[^)]+\))?)\s*$", re.I)

router = APIRouter(prefix="/api", tags=["streaming"])

def _hash(txt): 
    return hashlib.sha256(txt.encode("utf-8", "ignore")).hexdigest()[:10]

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Import AI gateway functions
from services.ai_gateway import load_personas, call_openrouter_api

# Helper function to get latest vision for project name extraction
def get_latest_vision_sync():
    """Get latest vision document from filesystem (sync version for project name extraction)"""
    try:
        visions_dir = Path(__file__).parent / "static" / "appdocs" / "visions"
        if not visions_dir.exists():
            return None
        
        # Get all vision JSON files
        vision_files = sorted(visions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not vision_files:
            return None
        
        # Read the most recent vision
        with open(vision_files[0], 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not read vision file: {e}")
        return None


def render_persona_output(msg: str) -> str | None:
    """Return safe string to render, or None if it should be suppressed."""
    if not msg or not msg.strip():
        return None
    text = msg.strip()
    if EAT_NO_COMMENT and NO_COMMENT_RE.match(text):
        return None
    return text

@router.post("/stream-chat")
async def stream_chat(request: dict):
    """
    AI-First streaming chat endpoint.
    Only filtering: chat room selection. Everything else is AI-driven.
    """
    message = request.get("message", "")
    # Use configured default model instead of hardcoded fallback
    from core.models_config import ModelsConfig
    models_config = ModelsConfig()
    favorites, default_model, meta, last_session_name = models_config.load_config()
    model = request.get("model", default_model)
    chat_room = request.get("chat_room", "general")
    selected_personas = request.get("selected_personas", [])
    chat_history = request.get("chat_history", [])
    
    # Log chat history count at INFO level for easy verification
    logger.info(f"📊 Chat history: {len(chat_history)} messages ({len(chat_history)//2} turns)")
    
    # Log detailed request payload for debugging
    logger.debug("=== DETAILED REQUEST PAYLOAD ===")
    logger.debug(f"Room: {chat_room}")
    logger.debug(f"Message: {message}")
    logger.debug(f"Selected personas: {selected_personas}")
    logger.debug(f"Model: {model}")
    logger.debug(f"Full JSON request:")
    logger.debug(json.dumps({
        "message": message,
        "selected_personas": selected_personas,
        "model": model,
        "chat_room": chat_room,
        "chat_history": chat_history
    }, indent=2))
    logger.debug("=== END REQUEST PAYLOAD ===")
    
    thread_id = str(uuid.uuid4())
    turn_id = str(uuid.uuid4())
    
    async def generate_response() -> AsyncGenerator[str, None]:
        try:
            personas = load_personas()
            
            # Only filter by checkbox selection - let AI decide everything else
            active_personas = []
            for persona_role in selected_personas:
                if persona_role.upper() in personas:
                    active_personas.append(persona_role.upper())
            
            
            logger.debug("Selected personas", personas=selected_personas)
            logger.debug("Available personas", personas=list(personas.keys()))
            logger.debug("Active personas", personas=active_personas)
            
            if not active_personas:
                yield f"data: {json.dumps({'type': 'error', 'content': 'No personas available in this chat room'})}\n\n"
                return
            
            # Check for meeting triggers (config-driven)
            logger.debug(f"Checking for meeting triggers in message: '{message}'")
            meeting_persona = None
            meeting_config = None
            message_lower = message.lower()
            
            for persona_key, persona_data in personas.items():
                triggers = persona_data.get("meeting_triggers", [])
                if triggers:
                    logger.debug(f"Checking {persona_key} triggers: {triggers}")
                for trigger in triggers:
                    logger.debug(f"Testing: '{trigger.lower()}' in '{message_lower}' = {trigger.lower() in message_lower}")
                    if trigger.lower() in message_lower:
                        meeting_persona = persona_key
                        meeting_config = persona_data
                        logger.info(f"✅ Meeting trigger detected: '{trigger}' -> {persona_key}")
                        break
                if meeting_persona:
                    break
            
            # If meeting detected and solo_mode enabled, override active_personas
            if meeting_persona and meeting_config.get("solo_mode", False):
                active_personas = [meeting_persona]
                
                # Allow exceptions: personas with matching persona_role (e.g., SPRINT_REVIEW_ALEX during meetings)
                persona_role_mapping = meeting_config.get("persona_role_mapping", {})
                if persona_role_mapping:
                    for persona_key, persona_config in personas.items():
                        persona_role = persona_config.get("persona_role")
                        # If this persona's role matches any mapped role, add it as an exception
                        if persona_role in persona_role_mapping:
                            mapped_persona = persona_role_mapping[persona_role]
                            if mapped_persona not in active_personas and personas.get(mapped_persona, {}).get("enabled", True):
                                active_personas.append(mapped_persona)
                                logger.info(f"Added {mapped_persona} to active personas (persona_role exception for {persona_role})")
                
                logger.info(f"Solo mode activated for {meeting_persona}, active_personas: {active_personas}")
            
            # Start event
            yield f"data: {json.dumps({'type': 'start', 'thread_id': thread_id, 'turn_id': turn_id, 'personas': active_personas})}\n\n"
            
            # If meeting detected, output system-generated announcement and STOP (wait for next user message)
            meeting_announcement_sent = False
            if meeting_persona and meeting_config.get("meeting_announcement"):
                announcement_template = meeting_config["meeting_announcement"].get("start", "")
                if announcement_template:
                    # Get project name from single source of truth
                    project_name = get_project_name()
                    
                    # Format announcement with variables
                    announcement = announcement_template.format(project_name=project_name)

                    # Emit structured meeting_started event for the UI (single source of truth)
                    meeting_type_map = {
                        "VISION_PM": "vision",
                        "REQUIREMENTS_PM": "requirements",
                        "SPRINT_PLANNING_ARCHITECT": "sprint_planning",
                        "SPRINT_EXECUTION_PM": "sprint_execution",
                        "SPRINT_REVIEW_PM": "sprint_review",
                    }
                    meeting_type = meeting_type_map.get(meeting_persona, "general")
                    meeting_display_name = meeting_config.get("meeting_display_name", "Meeting")
                    ui_persona_map = {}
                    if "ARCHITECT" in meeting_persona:
                        ui_persona_map["ARCHITECT"] = meeting_persona
                    else:
                        ui_persona_map["PM"] = meeting_persona

                    for p in active_personas:
                        if p == meeting_persona:
                            continue
                        cfg = personas.get(p, {})
                        pr = cfg.get("persona_role", "") or ""
                        base = None
                        if "developer" in pr:
                            base = "DEVELOPER"
                        elif "qa" in pr:
                            base = "QA"
                        elif "architect" in pr:
                            base = "ARCHITECT"
                        if base:
                            ui_persona_map[base] = p

                    yield f"data: {json.dumps({'type': 'meeting_started', 'meeting_type': meeting_type, 'project_name': project_name, 'persona': meeting_persona, 'meeting_display_name': meeting_display_name, 'active_personas': active_personas, 'ui_persona_map': ui_persona_map})}\n\n"

                    # Output announcement as system message from the meeting persona
                    persona_name = meeting_config.get("display_name", meeting_config.get("name", meeting_persona))
                    yield f"data: {json.dumps({'type': 'persona_response', 'persona': meeting_persona, 'name': persona_name, 'content': announcement})}\n\n"
                    logger.info(f"System-generated meeting announcement for {meeting_persona}")
                    meeting_announcement_sent = True
            
            # If we sent a meeting announcement, skip LLM call and wait for next user message
            if meeting_announcement_sent:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                logger.info("Meeting announcement sent, skipping LLM call, waiting for user's next message")
                return
            
            # Create tasks with proper isolation to avoid shared/mutated objects
            tasks = []
            for i, persona_role in enumerate(active_personas):
                # Add tiny launch stagger (except for first persona)
                if i > 0:
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                
                # Bind variables now to avoid late-binding bugs
                pk = persona_role
                pd = personas[pk]
                
                # SPRINT_REVIEW_PM only responds if explicitly addressed by name
                if pk == "SPRINT_REVIEW_PM":
                    first_word = message.strip().split()[0].lower() if message.strip() else ""
                    if first_word not in ["sarah", "sarah,", "sarah:"]:
                        logger.info(f"Skipping SPRINT_REVIEW_PM - not addressed (first word: '{first_word}')")
                        continue
                
                # Create messages list with chat history for each persona
                msgs = [{"role": "system", "content": pd["system_prompt"]}]
                
                # Inject context documents based on config
                inject_contexts = pd.get("inject_context", [])
                if inject_contexts:
                    context_parts = []
                    
                    # Inject vision if requested
                    if "vision" in inject_contexts:
                        try:
                            # Path is relative to src/ directory where this file runs
                            vision_dir = Path(__file__).parent / "static" / "appdocs" / "visions"
                            if vision_dir.exists():
                                # Find latest approved vision (not draft)
                                vision_files = sorted(vision_dir.glob("*.json"), reverse=True)
                                for vf in vision_files:
                                    with open(vf, 'r') as f:
                                        vision_data = json.load(f)
                                        if vision_data.get("client_approval"):
                                            # Extract project name from vision
                                            project_name = vision_data.get("title", "Unknown Project")
                                            context_parts.append(f"=== LATEST APPROVED VISION ===\nPROJECT: {project_name}\n\n{vision_data.get('content', '')}\n")
                                            logger.info(f"Injected vision context for {pk}: {vf.name}")
                                            break
                            else:
                                logger.warning(f"Vision directory not found at: {vision_dir}")
                        except Exception as e:
                            logger.warning(f"Could not fetch vision for {pk}: {e}")
                    
                    # Inject backlog if requested
                    if "backlog" in inject_contexts:
                        try:
                            # Path is relative to src/ directory where this file runs
                            backlog_file = Path(__file__).parent / "static" / "appdocs" / "backlog" / "Backlog.csv"
                            wireframe_metadata = {}  # Map slug -> (ID, Title)
                            
                            if backlog_file.exists():
                                with open(backlog_file, 'r') as f:
                                    backlog_content = f.read()
                                    context_parts.append(f"=== CURRENT BACKLOG ===\n{backlog_content}\n")
                                    logger.info(f"Injected backlog context for {pk}: Backlog.csv")
                                    
                                    logger.info(f"Starting wireframe metadata parsing for {pk}")
                                    # Parse wireframe metadata from CSV
                                    import csv
                                    from io import StringIO
                                    csv_reader = csv.reader(StringIO(backlog_content))
                                    for row in csv_reader:
                                        if len(row) > 13 and row[0].startswith("WF-"):
                                            wf_id = row[0]  # e.g., "WF-003"
                                            wf_title = row[1]  # e.g., "Leave Management Wireframe"
                                            wf_slug = row[12]  # e.g., "wf-003-leave-management"
                                            if wf_slug:
                                                wireframe_metadata[wf_slug] = (wf_id, wf_title)
                            else:
                                logger.warning(f"Backlog file not found at: {backlog_file}")
                            
                            logger.info(f"Starting wireframe file processing for {pk}")
                            # Also inject wireframe summaries (lightweight metadata only)
                            wireframes_dir = Path(__file__).parent / "static" / "appdocs" / "backlog" / "wireframes"
                            if wireframes_dir.exists() and wireframes_dir.is_dir():
                                wireframe_files = list(wireframes_dir.glob("*.html"))
                                if wireframe_files:
                                    context_parts.append("=== WIREFRAMES (Metadata Only) ===")
                                    logger.info(f"Processing {len(wireframe_files)} wireframe files for {pk}")
                                    for wf_file in sorted(wireframe_files):
                                        slug = wf_file.stem  # e.g., "wf-001-landing-page"
                                        wf_id, wf_title = wireframe_metadata.get(slug, (slug.upper(), "Unknown"))
                                        logger.info(f"Reading wireframe file: {wf_file.name}")
                                        
                                        with open(wf_file, 'r') as f:
                                            html_content = f.read()
                                            char_count = len(html_content)
                                            
                                            # Extract key structural elements (very lightweight)
                                            sections = []
                                            if '<header' in html_content.lower():
                                                sections.append('header')
                                            if '<nav' in html_content.lower():
                                                sections.append('navigation')
                                            if '<form' in html_content.lower():
                                                sections.append('form')
                                            if '<table' in html_content.lower():
                                                sections.append('table')
                                            if '<button' in html_content.lower():
                                                sections.append('buttons')
                                            
                                            elements_str = ', '.join(sections) if sections else 'basic layout'
                                            
                                            context_parts.append(
                                                f"\n{wf_id}: {wf_title} (slug: {slug})\n"
                                                f"  Size: {char_count:,} chars\n"
                                                f"  Elements: {elements_str}\n"
                                            )
                                    logger.info(f"Injected {len(wireframe_files)} wireframe metadata summaries for {pk}")
                            else:
                                logger.info(f"No wireframes directory found at: {wireframes_dir}")
                                
                        except Exception as e:
                            logger.warning(f"Could not fetch backlog for {pk}: {e}")
                    
                    # Inject sprint_log if requested
                    if "sprint_log" in inject_contexts:
                        try:
                            # Find the most recent completed sprint
                            sprints_dir = Path(__file__).parent / "static" / "appdocs" / "sprints"
                            if sprints_dir.exists():
                                sprint_files = list(sprints_dir.glob("SP-*.json"))
                                if sprint_files:
                                    # Sort by modification time, newest first
                                    sprint_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                                    latest_sprint = sprint_files[0]
                                    
                                    with open(latest_sprint, 'r') as f:
                                        sprint_data = json.load(f)
                                        sprint_id = sprint_data.get("sprint_id", "Unknown")
                                        
                                        # Read execution log if exists
                                        log_file = sprints_dir / f"execution_log_{sprint_id}.jsonl"
                                        if log_file.exists():
                                            with open(log_file, 'r') as log_f:
                                                lines = log_f.readlines()
                                                if lines:
                                                    # Parse ALL events to extract architecture, implementation, and tests
                                                    mike_notes = []
                                                    alex_tasks = []
                                                    jordan_tests = []
                                                    files_created = set()
                                                    summary = {}
                                                    
                                                    for line in lines:
                                                        try:
                                                            event = json.loads(line)
                                                            event_type = event.get("event_type")
                                                            data = event.get("data", {})
                                                            
                                                            if event_type == "mike_breakdown":
                                                                mike_notes.append({
                                                                    "story": data.get("story_id"),
                                                                    "architecture": data.get("technical_notes", "")
                                                                })
                                                            
                                                            elif event_type == "alex_implemented":
                                                                # Only process full events (have description), not summaries
                                                                if "description" in data and "task_id" in data:
                                                                    alex_tasks.append({
                                                                        "task": data.get("task_id"),
                                                                        "description": data.get("description", ""),
                                                                        "files": data.get("file_paths", [])
                                                                    })
                                                                    for f in data.get("file_paths", []):
                                                                        files_created.add(f)
                                                            
                                                            elif event_type == "jordan_tested":
                                                                jordan_tests.append({
                                                                    "story": data.get("story_id"),
                                                                    "passed": data.get("passed", 0),
                                                                    "failed": data.get("failed", 0),
                                                                    "test_file": data.get("test_file", "")
                                                                })
                                                            
                                                            elif event_type == "sprint_completed":
                                                                summary = data.get("summary", {})
                                                        
                                                        except json.JSONDecodeError:
                                                            continue
                                                    
                                                    # Use get_project_name() for single source of truth
                                                    try:
                                                        project_name = get_project_name()
                                                        project_name_safe = get_project_name_safe()
                                                    except Exception as name_err:
                                                        logger.warning(f"Could not get project names: {name_err}")
                                                        project_name = "Unknown"
                                                        project_name_safe = "unknown"
                                                    
                                                    # Build comprehensive context
                                                    context_text = f"=== SPRINT {sprint_id} ARCHITECTURE & IMPLEMENTATION ===\n\n"
                                                    
                                                    # Mike's Architecture
                                                    if mike_notes:
                                                        context_text += "MIKE'S TECHNICAL DESIGN:\n"
                                                        for note in mike_notes:
                                                            context_text += f"\nStory {note['story']}:\n{note['architecture']}\n"
                                                    
                                                    # Alex's Implementation
                                                    if alex_tasks:
                                                        context_text += "\n\nALEX'S IMPLEMENTATION DETAILS:\n"
                                                        for task in alex_tasks:
                                                            # Truncate very long descriptions but keep key info
                                                            desc = task['description']
                                                            if len(desc) > 200:
                                                                desc = desc[:197] + "..."
                                                            context_text += f"- {task['task']}: {desc}\n"
                                                    
                                                    # Files Created
                                                    if files_created:
                                                        context_text += f"\n\nFILES CREATED (these should exist):\n"
                                                        for f in sorted(files_created):
                                                            context_text += f"- {f}\n"
                                                    
                                                    # Jordan's Tests
                                                    if jordan_tests:
                                                        context_text += f"\n\nJORDAN'S TEST RESULTS:\n"
                                                        for test in jordan_tests:
                                                            context_text += f"- {test['story']}: {test['passed']} passed, {test['failed']} failed\n"
                                                    
                                                    # Summary
                                                    context_text += (
                                                        f"\n\nSUMMARY:\n"
                                                        f"- Stories Completed: {summary.get('stories_completed', 0)}\n"
                                                        f"- Tasks Completed: {summary.get('tasks_completed', 0)}\n"
                                                        f"- Tests Passed: {summary.get('tests_passed', 0)}\n"
                                                        f"- Tests Failed: {summary.get('tests_failed', 0)}\n"
                                                        f"\nProject Location: execution-sandbox/client-projects/{project_name_safe}/\n"
                                                    )
                                                    
                                                    context_parts.append(context_text)
                                                    logger.info(f"Injected detailed sprint_log context for {pk}: {sprint_id} ({len(mike_notes)} designs, {len(alex_tasks)} tasks, {len(jordan_tests)} test runs)")
                                        else:
                                            logger.warning(f"Execution log not found: {log_file}")
                                else:
                                    logger.warning(f"No sprint files found in: {sprints_dir}")
                            else:
                                logger.warning(f"Sprints directory not found: {sprints_dir}")
                        except Exception as e:
                            logger.warning(f"Could not fetch sprint_log for {pk}: {e}")
                    
                    # Inject architecture if requested
                    if "architecture" in inject_contexts:
                        try:
                            arch_file = Path(__file__).parent / "static" / "appdocs" / "architecture.json"
                            if arch_file.exists():
                                with open(arch_file, 'r') as f:
                                    arch_data = json.load(f)
                                    
                                    # Format architecture as readable context
                                    arch_text = f"=== LOCKED ARCHITECTURE ===\n\n"
                                    arch_text += f"Project: {arch_data.get('project_name', 'Unknown')}\n"
                                    arch_text += f"Architecture Locked: {arch_data.get('architecture_locked', False)}\n"
                                    arch_text += f"Locked at Sprint: {arch_data.get('locked_at_sprint', 'N/A')}\n\n"
                                    
                                    # Tech Stack
                                    if arch_data.get('tech_stack'):
                                        tech = arch_data['tech_stack']
                                        arch_text += "TECH STACK:\n"
                                        arch_text += f"- Backend: {tech.get('backend', 'N/A')}\n"
                                        arch_text += f"- Frontend: {tech.get('frontend', 'N/A')}\n"
                                        arch_text += f"- Database: {tech.get('database', 'N/A')}\n"
                                        arch_text += f"- Backend Port: {tech.get('backend_port', 'N/A')}\n"
                                        arch_text += f"- Frontend Port: {tech.get('frontend_port', 'N/A')}\n\n"
                                    
                                    # Conventions (the blueprint!)
                                    if arch_data.get('conventions'):
                                        arch_text += "CONVENTIONS (How to Build It):\n"
                                        arch_text += json.dumps(arch_data['conventions'], indent=2)
                                        arch_text += "\n"
                                    
                                    context_parts.append(arch_text)
                                    logger.info(f"Injected architecture context for {pk}: architecture.json")
                            else:
                                logger.warning(f"Architecture file not found at: {arch_file}")
                        except Exception as e:
                            logger.warning(f"Could not fetch architecture for {pk}: {e}")
                    
                    # Inject session context if available (for long conversations)
                    try:
                        # Determine session type and ID based on meeting context
                        session_type = "chat"  # default
                        session_id = "general"
                        
                        if meeting_persona:
                            # Map meeting persona to session type
                            session_type_map = {
                                "VISION_PM": "vision_meeting",
                                "REQUIREMENTS_PM": "requirements_meeting",
                                "SPRINT_PLANNING_ARCHITECT": "sprint_planning",
                                "SPRINT_REVIEW_PM": "sprint_review",
                                "SPRINT_EXECUTION_PM": "sprint_execution"
                            }
                            session_type = session_type_map.get(meeting_persona, "chat")
                            
                            # Use project name as session ID for meetings
                            project_name = get_project_name_safe()
                            session_id = f"{project_name}_{session_type}"
                        
                        # Try to load session context
                        session_file = Path(__file__).parent / "static" / "appdocs" / "sessions" / f"{session_type}_{session_id}_session.json"
                        
                        if session_file.exists():
                            with open(session_file, 'r') as f:
                                session_data = json.load(f)
                            
                            summary = session_data.get("summary", {})
                            turn_number = session_data.get("turn_number", 0)
                            
                            # Build session context message
                            session_context_parts = ["=== SESSION CONTEXT (from previous turns) ==="]
                            
                            if summary.get("key_points"):
                                session_context_parts.append("\nKey Points:")
                                for point in summary["key_points"]:
                                    session_context_parts.append(f"  • {point}")
                            
                            if summary.get("decisions"):
                                session_context_parts.append("\nDecisions Made:")
                                for decision in summary["decisions"]:
                                    session_context_parts.append(f"  • {decision}")
                            
                            if summary.get("pending_items"):
                                session_context_parts.append("\nPending Items:")
                                for item in summary["pending_items"]:
                                    session_context_parts.append(f"  • {item}")
                            
                            if summary.get("context"):
                                session_context_parts.append("\nAdditional Context:")
                                for key, value in summary["context"].items():
                                    session_context_parts.append(f"  {key}: {value}")
                            
                            session_context_parts.append(f"\n(Last updated at turn {turn_number})")
                            session_context_parts.append("=" * 50)
                            
                            context_parts.append("\n".join(session_context_parts))
                            logger.info(f"Injected session context for {pk}: {session_id} (turn {turn_number})")
                    
                    except Exception as e:
                        logger.warning(f"Could not fetch session context for {pk}: {e}")
                    
                    if context_parts:
                        context_message = "\n".join(context_parts)
                        msgs.append({"role": "system", "content": context_message})
                
                # Add chat history if provided
                if chat_history:
                    msgs.extend(chat_history)
                
                # Add current message
                msgs.append({"role": "user", "content": message})
                
                # Generate unique call ID and log per-persona call
                call_id = str(uuid.uuid4())[:8]
                sys_txt = pd["system_prompt"]
                usr_txt = message
                
                logger.debug("LLM CALL", 
                           call_id=call_id, 
                           persona=pk, 
                           sys_hash=_hash(sys_txt), 
                           user_preview=usr_txt[:80])
                
                # Generate session_id for conversation history (use project name or chat_room)
                from core.project_metadata import get_project_name_safe
                session_id = get_project_name_safe() or chat_room or "default_session"
                
                # Get persona's configured tools (if any)
                persona_tools = pd.get("tools", None)
                
                # Create async generator with isolated parameters - store persona_key with generator
                generator = call_openrouter_api(msgs, model, pd["name"], pk, session_id=session_id, persona_tools=persona_tools)
                tasks.append((generator, pk))  # Store generator with persona_key
            
            
            # Collect all responses for Scribe processing
            persona_responses = {}
            
            # Branch based on number of personas: single (Vision/Requirements) vs multi (team collaboration)
            if len(tasks) == 1:
                # SINGLE PERSONA PATH: Sequential processing for Vision/Requirements meetings
                # Preserves existing progress tracking and budget display
                for generator, persona_key in tasks:
                    try:
                        # Handle async generator - iterate through progress updates and final result
                        async for chunk in generator:
                            if chunk.get("type") == "progress":
                                # Forward progress updates to frontend (only for Vision/Requirements meetings)
                                if persona_key in ["VISION_PM", "REQUIREMENTS_PM"]:
                                    progress_event = {
                                        'type': 'progress',
                                        'persona': persona_key,
                                        'name': personas[persona_key]['name'],
                                        'progress': {
                                            'elapsed_seconds': chunk.get('elapsed_seconds', 0),
                                            'budget_seconds': chunk.get('budget_seconds', 0),
                                            'tokens_out': chunk.get('tokens_out', 0),
                                            'tokens_max': chunk.get('tokens_max', 0),
                                            'model': chunk.get('model', '')
                                        }
                                    }
                                    logger.debug(f"Forwarding progress update for {persona_key}: {chunk}")
                                    yield f"data: {json.dumps(progress_event)}\n\n"
                            
                            elif chunk.get("type") == "content_chunk":
                                # Forward incremental content chunks to frontend (Vision/Requirements streaming)
                                if persona_key in ["VISION_PM", "REQUIREMENTS_PM"]:
                                    content_event = {
                                        'type': 'content_chunk',
                                        'persona': persona_key,
                                        'name': personas[persona_key]['name'],
                                        'content': chunk.get('content', '')
                                    }
                                    logger.debug(f"Forwarding content chunk for {persona_key}: {len(chunk.get('content', ''))} chars")
                                    yield f"data: {json.dumps(content_event)}\n\n"
                            
                            elif "content" in chunk:
                                # Final response with content
                                response_content = chunk["content"]
                                metadata = chunk.get("metadata", {})
                                logger.debug(f"Response has metadata: {bool(metadata)}, tasks count: {len(tasks)}")
                                
                                # Store response for Scribe processing
                                persona_responses[persona_key] = response_content
                                
                                # Filter out empty responses and "No comment" responses
                                safe_content = render_persona_output(response_content)
                                if safe_content is None:
                                    logger.debug(f"Filtered out response from {persona_key}: {response_content[:50]}...")
                                    continue
                                
                                result = {
                                    'type': 'persona_response', 
                                    'persona': persona_key, 
                                    'name': personas[persona_key]['name'], 
                                    'content': safe_content
                                }
                                
                                # Include progress metadata for Vision/Requirements meetings
                                if metadata and persona_key in ["VISION_PM", "REQUIREMENTS_PM"]:
                                    result['progress'] = metadata
                                    logger.info(f"Including progress metadata for {persona_key}: {metadata}")
                                
                                logger.info("Persona response", 
                                           persona_key=persona_key, 
                                           persona_name=personas[persona_key]['name'], 
                                           response_preview=safe_content[:100])
                                yield f"data: {json.dumps(result)}\n\n"
                        
                    except Exception as e:
                        logger.error(f"Task error: {e}")
                        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            
            else:
                # MULTI-PERSONA PATH: Concurrent processing for team collaboration
                # All personas fire simultaneously and stream responses as they arrive
                response_queue = asyncio.Queue()
                pending_personas = set(pk for _, pk in tasks)
                
                async def process_persona_concurrent(generator, persona_key):
                    """Process a single persona concurrently and queue all chunks"""
                    try:
                        async for chunk in generator:
                            await response_queue.put((persona_key, chunk))
                        # Signal this persona completed
                        await response_queue.put((persona_key, {'type': 'DONE'}))
                    except Exception as e:
                        logger.error(f"Concurrent task error for {persona_key}: {e}")
                        await response_queue.put((persona_key, {'type': 'error', 'error': str(e)}))
                        await response_queue.put((persona_key, {'type': 'DONE'}))
                
                # Launch all personas concurrently
                for generator, persona_key in tasks:
                    asyncio.create_task(process_persona_concurrent(generator, persona_key))
                
                # Collect responses as they arrive from any persona
                while pending_personas:
                    persona_key, chunk = await response_queue.get()
                    
                    # Check for completion signal
                    if chunk.get("type") == "DONE":
                        pending_personas.remove(persona_key)
                        logger.debug(f"Persona {persona_key} completed, {len(pending_personas)} remaining")
                        continue
                    
                    # Handle error chunks
                    if chunk.get("type") == "error":
                        yield f"data: {json.dumps({'type': 'persona_error', 'persona': persona_key, 'error': chunk['error']})}\n\n"
                        continue
                    
                    # Handle progress chunks (not used for multi-persona, but included for completeness)
                    if chunk.get("type") == "progress":
                        # Skip progress updates for multi-persona
                        continue
                    
                    # Handle content chunks
                    if "content" in chunk:
                        response_content = chunk["content"]
                        
                        # Store response for Scribe processing
                        persona_responses[persona_key] = response_content
                        
                        # Filter out empty responses and "No comment" responses
                        safe_content = render_persona_output(response_content)
                        if safe_content is None:
                            logger.debug(f"Filtered out response from {persona_key}: {response_content[:50]}...")
                            continue
                        
                        result = {
                            'type': 'persona_response',
                            'persona': persona_key,
                            'name': personas[persona_key]['name'],
                            'content': safe_content
                        }
                        
                        logger.info("Persona response (concurrent)", 
                                   persona_key=persona_key, 
                                   persona_name=personas[persona_key]['name'], 
                                   response_preview=safe_content[:100])
                        yield f"data: {json.dumps(result)}\n\n"
            
            # Use new turn-based Scribe system for streaming conversations
            # Check if Scribe should be active: default is true, but disabled if ANY active persona has the flag set to false
            scribe_enabled = True
            logger.info(f"🔍 SCRIBE CHECK: Checking {len(active_personas)} active personas: {active_personas}")
            for persona_key in active_personas:
                if persona_key in personas:
                    persona_config = personas[persona_key]
                    scribe_flag = persona_config.get("scribe_active_during_meeting")
                    logger.info(f"🔍 Persona {persona_key}: scribe_active_during_meeting={scribe_flag}")
                    # If this persona has scribe disabled, disable Scribe for this turn
                    if scribe_flag == False:
                        scribe_enabled = False
                        logger.info(f"✅ SCRIBE DISABLED: {persona_key} has scribe_active_during_meeting=false")
                        break
            
            logger.info(f"🔍 SCRIBE DECISION: scribe_enabled={scribe_enabled}")
            if scribe_enabled:
                try:
                    from api.scribe import start_conversation_turn, add_persona_response, complete_conversation_turn
                    
                    # Notify frontend that Scribe is processing
                    yield f"data: {json.dumps({'type': 'status', 'message': 'scribe_processing'})}\n\n"
                    
                    # Start conversation turn with client message
                    await start_conversation_turn(turn_id, message)
                    
                    # Add all persona responses that were generated
                    for persona_key, response_content in persona_responses.items():
                        if response_content and not response_content.startswith("Error:"):
                            await add_persona_response(turn_id, persona_key, response_content)
                    
                    # Complete and process the full conversation turn
                    await complete_conversation_turn(turn_id, model)
                    
                except Exception as scribe_error:
                    logger.warning(f"Scribe streaming conversation turn processing error: {scribe_error}")
            else:
                logger.info("Scribe skipped - disabled for this meeting")
            
            # End event
            yield f"data: {json.dumps({'type': 'complete', 'thread_id': thread_id, 'turn_id': turn_id})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # prevents nginx proxy buffering
            "X-Requested-With": "XMLHttpRequest",  # helps with some browser buffering
            "Access-Control-Allow-Origin": "*",   # explicit CORS for streaming
            "Access-Control-Allow-Headers": "Cache-Control",  # CORS headers for streaming
        }
    )

@router.get("/stream")
async def stream_personas(message: str, personas: str = "PM,DEVELOPER,QA,ARCHITECT"):
    """Stream responses from multiple personas"""
    try:
        persona_list = [p.strip() for p in personas.split(",")]
        
        # Log full payload to file for debugging
        logger.info("Streaming request payload", 
                   message=message, 
                   personas_string=personas, 
                   parsed_personas=persona_list)
        
        return StreamingResponse(
            stream_persona_responses(message, persona_list),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Requested-With": "XMLHttpRequest",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            }
        )
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        return StreamingResponse(
            f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n",
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Requested-With": "XMLHttpRequest",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            }
        )

# Removed programmatic filtering - only checkbox selection matters




async def execute_function_calls(tool_calls, original_content, persona_key=None):
    """Execute function calls made by personas and format responses appropriately"""
    import aiohttp
    import json
    
    results = []
    if original_content:
        results.append(original_content)
    
    for tool_call in tool_calls:
        function_name = tool_call["function"]["name"]
        
        try:
            arguments = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse function arguments: {e}")
            logger.error(f"Raw arguments: {tool_call['function']['arguments']}")
            results.append(f"❌ Function call error: Invalid JSON arguments")
            continue
        
        if function_name == "http_post":
            try:
                url = arguments["url"]
                post_payload = arguments["payload"]
                headers = arguments.get("headers", {"Content-Type": "application/json"})
            except KeyError as e:
                logger.error(f"Missing required argument for http_post: {e}")
                results.append(f"❌ HTTP POST error: Missing required argument: {e}")
                continue
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=post_payload, headers=headers) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            # For Alex, append success indicator but don't format raw response
                            if persona_key == "DEVELOPER" and "change-requests" in url:
                                success_msg = "✅ Change request completed successfully"
                                results.append(success_msg)
                                logger.info(f"[DEBUG] Added success indicator for Alex: {success_msg}")
                            else:
                                # Format response based on persona and endpoint
                                formatted_response = format_persona_response(url, response_text, persona_key)
                                if formatted_response is not None:
                                    results.append(formatted_response)
                        else:
                            results.append(f"❌ HTTP POST failed (status {response.status}): {response_text}")
                            
            except Exception as e:
                results.append(f"❌ HTTP POST error: {str(e)}")
        
        elif function_name == "list_directory":
            try:
                path = arguments.get("path", ".")
                recursive = arguments.get("recursive", False)
                max_depth = arguments.get("max_depth", 3)
            except KeyError as e:
                logger.error(f"Missing required argument for list_directory: {e}")
                results.append(f"❌ list_directory error: Missing required argument: {e}")
                continue
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8000/api/sandbox/list-directory",
                        json={"path": path, "recursive": recursive, "max_depth": max_depth}
                    ) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            data = json.loads(response_text)
                            entries = data.get("entries", [])
                            result_lines = [f"📁 Directory: {data.get('path', path)}"]
                            result_lines.append(f"Found {len(entries)} entries:\n")
                            
                            for entry in entries[:50]:  # Limit to 50 entries
                                icon = "📁" if entry["type"] == "directory" else "📄"
                                size = f" ({entry['size']} bytes)" if entry.get("size") else ""
                                result_lines.append(f"{icon} {entry['name']}{size}")
                            
                            if len(entries) > 50:
                                result_lines.append(f"\n... and {len(entries) - 50} more entries")
                            
                            results.append("\n".join(result_lines))
                        else:
                            results.append(f"❌ list_directory failed (status {response.status}): {response_text}")
            except Exception as e:
                results.append(f"❌ list_directory error: {str(e)}")
        
        elif function_name == "run_command":
            try:
                project_name = arguments["project_name"]
                command = arguments["command"]
                args = arguments.get("args", [])
                working_dir = arguments.get("working_dir")
                timeout = arguments.get("timeout", 30)
            except KeyError as e:
                logger.error(f"Missing required argument for run_command: {e}")
                results.append(f"❌ run_command error: Missing required argument: {e}")
                continue
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8000/api/sandbox/execute",
                        json={
                            "project_name": project_name,
                            "command": command,
                            "args": args,
                            "working_dir": working_dir,
                            "timeout": timeout
                        }
                    ) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            data = json.loads(response_text)
                            result_lines = [f"🔧 Command: {data.get('command', command)}"]
                            
                            if data.get("stdout"):
                                result_lines.append(f"\n📤 Output:\n{data['stdout']}")
                            
                            if data.get("stderr"):
                                result_lines.append(f"\n⚠️ Errors:\n{data['stderr']}")
                            
                            result_lines.append(f"\n✅ Exit code: {data.get('exit_code', 0)}")
                            results.append("\n".join(result_lines))
                        else:
                            results.append(f"❌ run_command failed (status {response.status}): {response_text}")
            except Exception as e:
                results.append(f"❌ run_command error: {str(e)}")
        
        elif function_name == "read_file":
            try:
                project_name = arguments.get("project_name")
                file_path = arguments.get("file_path")
                if not project_name or not file_path:
                    results.append("❌ read_file error: Missing project_name or file_path")
                    continue
            except KeyError as e:
                logger.error(f"Missing required argument for read_file: {e}")
                results.append(f"❌ read_file error: Missing required argument: {e}")
                continue
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8000/api/sandbox/read-file",
                        json={"project_name": project_name, "file_path": file_path}
                    ) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            data = json.loads(response_text)
                            content = data.get("content", "")
                            result_lines = [f"📄 File: {project_name}/{file_path}"]
                            result_lines.append(f"\n{content}")
                            results.append("\n".join(result_lines))
                        else:
                            results.append(f"❌ read_file failed (status {response.status}): {response_text}")
            except Exception as e:
                results.append(f"❌ read_file error: {str(e)}")
        
        elif function_name == "write_text":
            try:
                import html
                project_name = arguments.get("project_name")
                file_path = arguments.get("file_path")
                content = arguments.get("content")
                force_replace = arguments.get("force_replace", False)  # Optional, defaults to False
                if not project_name or not file_path or content is None:
                    results.append("❌ write_text error: Missing project_name, file_path, or content")
                    continue
                
                # Decode any HTML entities that the LLM might have encoded
                content = html.unescape(content)
            except KeyError as e:
                logger.error(f"Missing required argument for write_text: {e}")
                results.append(f"❌ write_text error: Missing required argument: {e}")
                continue
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "http://localhost:8000/api/sandbox/write-file",
                        json={"project_name": project_name, "file_path": file_path, "content": content, "force_replace": force_replace}
                    ) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            data = json.loads(response_text)
                            result_lines = [f"✅ File written: {project_name}/{file_path}"]
                            if data.get("message"):
                                result_lines.append(f"Message: {data['message']}")
                            results.append("\n".join(result_lines))
                        else:
                            results.append(f"❌ write_text failed (status {response.status}): {response_text}")
            except Exception as e:
                results.append(f"❌ write_text error: {str(e)}")
    
    # For Alex, if no function call results were added but he has original content, return it
    # This handles both cases: function calls filtered out AND normal responses without function calls
    # But don't override if we successfully added function call results
    if persona_key == "DEVELOPER" and len(results) <= 1 and original_content and not any("✅" in str(r) for r in results):
        logger.info(f"[DEBUG] Returning original_content for Alex: '{original_content}'")
        return original_content
    
    final_result = "\n".join(results)
    logger.info(f"[DEBUG] Final execute_function_calls result for {persona_key}: '{final_result}'")
    return final_result


def format_persona_response(url, response_text, persona_key):
    """Format API responses according to persona instructions"""
    try:
        response_data = json.loads(response_text)
    except json.JSONDecodeError:
        return response_text
    
    # Alex (DEVELOPER) - Let Alex respond naturally, no formatting
    if persona_key == "DEVELOPER" and "change-requests" in url:
        return None  # Don't format anything - let Alex's LLM handle the response
    
    # Sarah (PM, VISION_PM) - Vision creation and management
    if persona_key in ["PM", "VISION_PM"] and "vision" in url:
        if response_data.get("success"):
            message = response_data.get("message", "")
            data = response_data.get("data", {})
            vision_id = data.get("vision_id", "")
            
            # Check if this is a delete operation
            if "deleted successfully" in message:
                return f"✅ Vision document deleted successfully!"
            else:
                # This is a save operation - use message which already contains title
                return f"✅ {message} (ID: {vision_id}). The vision is now available via the Vision button."
        else:
            return f"❌ Vision operation failed: {response_data.get('message', 'Unknown error')}"
    
    # Sarah (REQUIREMENTS_PM) - Backlog creation and management
    elif persona_key == "REQUIREMENTS_PM" and "backlog" in url:
        if response_data.get("success"):
            message = response_data.get("message", "")
            data = response_data.get("data", {})
            backlog_id = data.get("backlog_id", "")
            warnings = data.get("warnings", [])
            
            # Check if this is a delete operation
            if "deleted successfully" in message:
                return f"✅ Backlog deleted successfully!"
            else:
                # This is a save operation
                result = f"✅ {message} (ID: {backlog_id}). View it via the Backlog button."
                if warnings:
                    result += f"\n⚠️ Warnings: {'; '.join(warnings)}"
                return result
        else:
            return f"❌ Backlog operation failed: {response_data.get('message', 'Unknown error')}"
    
    # Alex (DEVELOPER) - Change requests - Let Alex's LLM handle the response formatting
    elif persona_key == "DEVELOPER" and "change-requests" in url:
        # Don't override Alex's natural response - let the LLM handle formatting
        return None
    
    # Jordan (QA) - Test results  
    elif persona_key == "QA" and "testing" in url:
        if "results" in response_data:
            results = response_data["results"]
            summary = response_data.get("summary", {})
            
            if len(results) == 1:
                test = results[0]
                status = test.get("status", "UNKNOWN")
                actual = test.get("actual", "")
                expected = test.get("expected", "")
                
                if status == "PASS":
                    return f"✅ Test passed! Output matches expected: '{actual}'"
                else:
                    error = test.get("error_message", "Unknown error")
                    return f"❌ Test failed. Expected: '{expected}', Got: '{actual}'. Error: {error}"
            else:
                passed = summary.get("passed", 0)
                failed = summary.get("failed", 0)
                return f"Test results: {passed} passed, {failed} failed"
        else:
            return f"❌ Test execution failed: {response_data.get('error', 'Unknown error')}"
    
    # Default: return original response for other cases
    return response_data.get("message", response_text) if isinstance(response_data, dict) else response_text


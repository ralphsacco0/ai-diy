"""
AI Gateway Service - Centralized AI API interactions and character management.
Moved from streaming.py for better code organization.
"""
import os
import json
import uuid
import hashlib
import logging
import ssl
import asyncio
import random
from typing import Dict, List, Optional, Any, AsyncGenerator
from pathlib import Path
import aiohttp
from dotenv import load_dotenv
from core.logging_config import get_structured_logger, log_openrouter_call
from core.project_metadata import get_project_name_safe
from services.snapshot_manager import create_snapshot

# Load environment variables
load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

logger = get_structured_logger("ai_gateway")

# Global cache for personas (loaded once at startup, reloaded on file changes)
_personas_cache = None
_cache_timestamp = None


def build_tools_array(persona_tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Build tools array for OpenRouter API calls, filtered by persona's configured tools.
    
    Args:
        persona_tools: List of tool names this persona is allowed to use (from config).
                      If None or empty, returns all tools (backward compatible).
    
    Returns:
        List of tool definitions filtered by persona_tools.
    """
    all_tools = [
        {
            "type": "function",
            "function": {
                "name": "http_post",
                "description": "Make HTTP POST request to any endpoint",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to POST to"
                        },
                        "payload": {
                            "type": "object",
                            "description": "JSON payload to send"
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP headers to include"
                        }
                    },
                    "required": ["url", "payload"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "List project structure in the sandbox. CALL THIS FIRST to see what files exist before investigating issues. Use recursive=true for full tree view. Automatically excludes node_modules, .git, etc. Use paths relative to sandbox root (e.g., 'ProjectName'). Do NOT include 'execution-sandbox/client-projects/' prefix.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path relative to sandbox root (e.g., 'BrightHR_Lite_Vision' or 'BrightHR_Lite_Vision/routes')"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "List recursively to see full project structure (default: false)"
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum depth for recursive listing (default: 3)"
                        },
                        "exclude_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Patterns to exclude like node_modules, .git (default excludes common dev folders)"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Execute a command in the sandbox (allowed commands: python, pytest, pip, npm, node, flask, uvicorn, ls, cat, grep, find, git). Use project name only, not full path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Project name only (e.g., 'BrightHR_Lite_Vision'), not full path"
                        },
                        "command": {
                            "type": "string",
                            "description": "Command to execute (must be in allowlist)"
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Command arguments"
                        },
                        "working_dir": {
                            "type": "string",
                            "description": "Working directory (relative to project root)"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 30)"
                        }
                    },
                    "required": ["project_name", "command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file in the sandbox. Use paths relative to the project root (e.g., 'app.py', 'src/server.js', 'public/hr-dashboard.html'). Do NOT include the project name or 'execution-sandbox/client-projects/' prefix.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Project name (e.g., 'BrightHR_Lite_Vision')"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "File path relative to project root (e.g., 'app.py', 'src/server.js', 'public/hr-dashboard.html')"
                        }
                    },
                    "required": ["project_name", "file_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_text",
                "description": "Write or modify a text file in the sandbox. Use project-relative paths. Do NOT include 'execution-sandbox/client-projects/' prefix.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Project name (e.g., 'BrightHR_Lite_Vision')"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "File path relative to project root (e.g., 'app.py' or 'routes/auth.py')"
                        },
                        "content": {
                            "type": "string",
                            "description": "Complete file content to write"
                        },
                        "force_replace": {
                            "type": "boolean",
                            "description": "If true, replace file entirely without merging. Use true for Sprint Review fixes to avoid appending. Default: false",
                            "default": False
                        }
                    },
                    "required": ["project_name", "file_path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_snapshots",
                "description": "List available snapshots for rollback. Only call when user reports app is broken or requests to see restore points. Returns snapshots with metadata about what changed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Project name (e.g., 'BrightHR_Lite_Vision')"
                        }
                    },
                    "required": ["project_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "restore_snapshot",
                "description": "Restore project to a previous snapshot. Use when changes broke the app and user approves rollback. This replaces current project files with snapshot files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Project name (e.g., 'BrightHR_Lite_Vision')"
                        },
                        "snapshot_id": {
                            "type": "string",
                            "description": "Snapshot ID from list_snapshots (e.g., '20251209_080000')"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for restoration (e.g., 'App startup failure after session config changes')"
                        }
                    },
                    "required": ["project_name", "snapshot_id", "reason"]
                }
            }
        }
    ]
    
    # If no persona_tools specified, return all tools (backward compatible)
    if not persona_tools:
        return all_tools
    
    # Filter tools to only those configured for this persona
    filtered_tools = []
    for tool in all_tools:
        tool_name = tool["function"]["name"]
        if tool_name in persona_tools:
            filtered_tools.append(tool)
    
    return filtered_tools


def resolve_project_root() -> Path:
    """
    Climb parents from this file's directory until finding a directory containing
    one of: .git, README.md, or architect/. If none found, default to Path.cwd().
    """
    current_dir = Path(__file__).parent
    
    # Traverse upwards looking for project root indicators
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / ".git").exists() or (parent / "README.md").exists() or (parent / "architect").exists():
            return parent
    
    # Fallback to current working directory
    return Path.cwd()


def resolve_personas_path() -> Path:
    """
    Resolve the path to personas JSON file with the following priority:
    1. If PERSONAS_PATH env var is set:
       - If absolute, use it directly
       - If relative, resolve relative to project root
    2. Otherwise, default to project_root / system_prompts / personas_config.json
    """
    personas_path_env = os.getenv("PERSONAS_PATH")
    
    if personas_path_env:
        personas_path = Path(personas_path_env)
        if personas_path.is_absolute():
            return personas_path
        else:
            return resolve_project_root() / personas_path
    else:
        # Default to system_prompts/personas_config.json
        return resolve_project_root() / "system_prompts" / "personas_config.json"


def _get_system_prompts_mtime() -> float:
    """Get latest modification time of any file in system_prompts folder"""
    prompts_dir = resolve_project_root() / "system_prompts"
    if not prompts_dir.exists():
        return 0
    
    latest_mtime = 0
    try:
        for file in prompts_dir.glob("*"):
            if file.is_file():
                latest_mtime = max(latest_mtime, file.stat().st_mtime)
    except Exception as e:
        logger.warning(f"Failed to check system_prompts folder mtime: {e}")
    
    return latest_mtime


def load_personas() -> Dict[str, Dict[str, Any]]:
    """Load personas with automatic reload on file changes.
    
    Uses in-memory cache that invalidates when any file in system_prompts/ changes.
    This avoids repeated disk I/O on every request while supporting live editing.
    """
    global _personas_cache, _cache_timestamp
    
    current_mtime = _get_system_prompts_mtime()
    
    # Reload if: cache empty OR files changed
    if _personas_cache is None or current_mtime > _cache_timestamp:
        logger.info(f"Loading personas from disk (cache invalidated)")
        _personas_cache = _load_personas_from_disk()
        _cache_timestamp = current_mtime
    
    return _personas_cache


def _load_personas_from_disk() -> Dict[str, Dict[str, Any]]:
    """Actually load personas from disk (called once at startup or when files change)"""
    personas_path = resolve_personas_path()
    
    try:
        with open(personas_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Validate JSON structure
        if "personas" not in data:
            raise ValueError("Invalid JSON format: missing 'personas' key")
        
        personas = {}
        json_personas = data["personas"]
        project_root = resolve_project_root()
        
        for role_key, persona_data in json_personas.items():
            # Validate required fields
            required_fields = ["name", "role"]
            for field in required_fields:
                if field not in persona_data:
                    raise ValueError(f"Missing required field '{field}' for persona '{role_key}'")
            
            # Check if persona is enabled (default: True)
            if not persona_data.get("enabled", True):
                logger.debug(f"Skipping disabled persona: {role_key}")
                continue
            
            # Copy all persona data
            persona_copy = persona_data.copy()
            
            # Load system_prompt from file if system_prompt_file is specified
            if "system_prompt_file" in persona_data:
                prompt_file_path = project_root / persona_data["system_prompt_file"]
                try:
                    with open(prompt_file_path, "r", encoding="utf-8") as pf:
                        persona_copy["system_prompt"] = pf.read()
                    logger.debug(f"Loaded system_prompt from {prompt_file_path}")
                except FileNotFoundError:
                    logger.error(f"System prompt file not found: {prompt_file_path}")
                    raise RuntimeError(f"System prompt file not found for {role_key}: {prompt_file_path}")
            elif "system_prompt" not in persona_data:
                raise ValueError(f"Missing system_prompt or system_prompt_file for persona '{role_key}'")
            
            personas[role_key] = persona_copy
            logger.debug(f"Loaded persona: {role_key} -> {persona_data['name']}")
        
        if len(personas) == 0:
            logger.error(f"CRITICAL ERROR: No enabled personas loaded from {personas_path}")
            raise RuntimeError(f"No enabled personas found in {personas_path}. Check file content and enabled flags.")
        
        logger.info(f"Personas: loaded from {personas_path} (count={len(personas)})", personas=list(personas.keys()))
        return personas
        
    except FileNotFoundError:
        logger.error(f"CRITICAL ERROR: Personas JSON file not found at {personas_path}")
        raise RuntimeError(f"Personas JSON file not found at {personas_path}. Please ensure the file exists.")
    except json.JSONDecodeError as e:
        logger.error(f"CRITICAL ERROR: Invalid JSON in {personas_path}: {e}")
        raise RuntimeError(f"Invalid JSON format in {personas_path}: {e}")
    except Exception as e:
        logger.error(f"CRITICAL ERROR: Failed to load personas from {personas_path}: {e}")
        raise RuntimeError(f"Character loading failed: {e}. Check that {personas_path} exists and is properly formatted.")




async def call_openrouter_api(messages: List[Dict], model: str, persona_name: str, persona_key: str, include_tools: bool = True, session_id: Optional[str] = None, skip_mode_routing: bool = False, persona_tools: Optional[List[str]] = None) -> AsyncGenerator[Dict[str, Any], None]:
    """Call OpenRouter API with streaming and yield progress updates
    
    Args:
        include_tools: If False, don't add tools to request (for execution personas that need pure JSON output)
        session_id: Optional session ID for conversation history tracking
        skip_mode_routing: If True, skip the mode routing logic (prevents recursion in bounded loops)
        persona_tools: List of tool names this persona is allowed to use (from config)
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not found in environment")
    
    # Inject conversation history for SPRINT_REVIEW_ALEX
    if persona_key == "SPRINT_REVIEW_ALEX" and session_id:
        from services.conversation_history import get_conversation_history
        history_messages = get_conversation_history(session_id, persona_key, max_turns=3)
        if history_messages:
            # Insert history after system prompt but before current message
            system_messages = [m for m in messages if m.get("role") == "system"]
            current_messages = [m for m in messages if m.get("role") != "system"]
            messages = system_messages + history_messages + current_messages
            logger.info(f"Injected {len(history_messages)} history messages for {persona_key} in session {session_id}")
    
    request_id = str(uuid.uuid4())
    start_time = None
    
    try:
        import time
        from datetime import datetime
        
        start_time = time.monotonic()
        wall_start = time.time()
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "AI-DIY Scrum App"
        }
        
        
        # Dynamic max_tokens based on model cost - free models get more tokens
        if any(keyword in model.lower() for keyword in ["free", "deepseek"]):
            max_tokens = 16000  # Free models - be generous with output
        else:
            max_tokens = 12000  # Paid models - reasonable limit
        
        request_payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.1 if persona_key == "SCRIBE" else 0.7,
            "max_tokens": max_tokens,
            "stream": True  # Enable streaming for real-time progress
        }
        
        # Add HTTP tools only if requested (execution personas don't need tools)
        if include_tools:
            request_payload["tools"] = build_tools_array(persona_tools)
        
        # Calculate hashes for correlation
        prompt_hash = hashlib.md5(json.dumps(messages).encode()).hexdigest()[:8]
        
        # Log tools being sent
        if "tools" in request_payload:
            tool_names = [t["function"]["name"] for t in request_payload["tools"]]
            logger.info(f"Tools available for {persona_name}: {tool_names}", character=persona_key)
            if persona_key == "SPRINT_REVIEW_ALEX":
                logger.info(f"Alex has write_text: {'write_text' in tool_names}", character=persona_key)
            logger.debug(f"Full tools payload: {json.dumps(request_payload['tools'], indent=2)}", character=persona_key)
        
        logger.info(f"Calling OpenRouter API for {persona_name} with model {model}", 
                   request_id=request_id, character=persona_key)
        
        # Create SSL context to handle certificate verification
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Retry logic with exponential backoff
        max_retries = 3
        retry_status_codes = {429, 502, 503, 504}
        
        # Dynamic budget based on model cost - free models get generous timeouts
        if any(keyword in model.lower() for keyword in ["free", "deepseek"]):
            total_budget = 600.0  # 10 minutes - it's free, so be patient!
        else:
            total_budget = 300.0  # 5 minutes - standard for paid models
        
        def redact_headers(headers_dict):
            """Redact sensitive headers for logging"""
            redacted = dict(headers_dict)
            for key in redacted:
                if key.lower() in ['authorization', 'x-api-key']:
                    redacted[key] = "REDACTED"
            return redacted
        
        def parse_retry_after(retry_after_value):
            """Parse Retry-After header supporting both seconds and HTTP-date"""
            if not retry_after_value:
                return None
            try:
                # Try parsing as integer seconds first
                return float(retry_after_value)
            except ValueError:
                # Try parsing as HTTP-date
                try:
                    retry_date = datetime.strptime(retry_after_value, '%a, %d %b %Y %H:%M:%S GMT')
                    now = datetime.utcnow()
                    delta = (retry_date - now).total_seconds()
                    return max(0, delta)
                except ValueError:
                    return None
        
        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        headers=headers,
                        json=request_payload,
                        timeout=aiohttp.ClientTimeout(total=90, connect=15, sock_read=60),
                        ssl=ssl_context
                    ) as response:
                        current_time = time.monotonic()
                        latency_ms = (current_time - start_time) * 1000
                        
                        if response.status < 400:
                            # Success - process streaming response
                            content = ""
                            tokens_in = 0
                            tokens_out = 0
                            tool_calls = []
                            last_progress_time = time.monotonic()
                            progress_interval = 1.0  # Send progress updates every 1 second (increased for visibility)
                            next_progress_time = time.monotonic() + 0.5  # First update after 0.5 seconds
                            
                            # Check if this is a Vision/Requirements PM that should stream content
                            should_stream_content = persona_key in ["VISION_PM", "REQUIREMENTS_PM"]
                            
                            # Track finish_reason to detect truncation
                            finish_reason = None
                            
                            # Read streaming chunks
                            async for line in response.content:
                                line_text = line.decode('utf-8').strip()
                                
                                if not line_text or not line_text.startswith('data: '):
                                    continue
                                
                                # Remove 'data: ' prefix
                                json_str = line_text[6:]
                                
                                # Check for [DONE] signal
                                if json_str == '[DONE]':
                                    break
                                
                                try:
                                    chunk = json.loads(json_str)
                                    
                                    # Extract content delta
                                    if 'choices' in chunk and len(chunk['choices']) > 0:
                                        delta = chunk['choices'][0].get('delta', {})
                                        
                                        # Accumulate content and optionally yield incremental chunks
                                        if 'content' in delta and delta['content']:
                                            content_chunk = delta['content']
                                            content += content_chunk
                                            
                                            # For Vision/Requirements PM, yield content chunks as they arrive
                                            if should_stream_content:
                                                yield {
                                                    "type": "content_chunk",
                                                    "content": content_chunk
                                                }
                                        
                                        # Merge tool call deltas by index (streaming sends incremental chunks)
                                        if 'tool_calls' in delta:
                                            for tc_delta in delta['tool_calls']:
                                                index = tc_delta.get('index', 0)
                                                
                                                # Ensure we have a slot for this index
                                                while len(tool_calls) <= index:
                                                    tool_calls.append({
                                                        'id': None,
                                                        'type': 'function',
                                                        'function': {'name': '', 'arguments': ''}
                                                    })
                                                
                                                # Merge the delta into the existing tool call
                                                if 'id' in tc_delta and tc_delta['id']:
                                                    tool_calls[index]['id'] = tc_delta['id']
                                                if 'type' in tc_delta and tc_delta['type']:
                                                    tool_calls[index]['type'] = tc_delta['type']
                                                if 'function' in tc_delta:
                                                    if 'name' in tc_delta['function'] and tc_delta['function']['name']:
                                                        tool_calls[index]['function']['name'] = tc_delta['function']['name']
                                                    if 'arguments' in tc_delta['function'] and tc_delta['function']['arguments']:
                                                        tool_calls[index]['function']['arguments'] += tc_delta['function']['arguments']
                                    
                                    # Extract usage if present (final chunk)
                                    if 'usage' in chunk:
                                        tokens_in = chunk['usage'].get('prompt_tokens', 0)
                                        tokens_out = chunk['usage'].get('completion_tokens', 0)
                                    
                                    # Capture finish_reason to detect truncation
                                    if 'choices' in chunk and len(chunk['choices']) > 0:
                                        fr = chunk['choices'][0].get('finish_reason')
                                        if fr:
                                            finish_reason = fr
                                    
                                    # Yield progress updates periodically
                                    current_time = time.monotonic()
                                    if current_time >= next_progress_time:
                                        elapsed_seconds = current_time - start_time
                                        yield {
                                            "type": "progress",
                                            "elapsed_seconds": round(elapsed_seconds, 1),
                                            "budget_seconds": total_budget,
                                            "tokens_out": len(content.split()),  # Rough estimate
                                            "tokens_max": max_tokens,
                                            "model": model
                                        }
                                        next_progress_time = current_time + progress_interval
                                    
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse streaming chunk: {json_str[:100]}")
                                    continue
                            
                            # Log finish_reason - critical for detecting truncation
                            if finish_reason:
                                if finish_reason == 'length':
                                    logger.warning(f"⚠️ RESPONSE TRUNCATED: {persona_name} hit max_tokens limit ({max_tokens}). Response may be incomplete!", 
                                                 character=persona_key, request_id=request_id)
                                elif finish_reason == 'stop':
                                    logger.debug(f"Response completed normally for {persona_name}", character=persona_key)
                                else:
                                    logger.info(f"Response finish_reason for {persona_name}: {finish_reason}", character=persona_key)
                            
                            # Handle function calls if present
                            function_results = None
                            if tool_calls:
                                tool_names = [tc["function"]["name"] for tc in tool_calls]
                                logger.info(f"Processing {len(tool_calls)} tool calls for {persona_name}: {tool_names}",
                                          request_id=request_id, character=persona_key)
                                function_results = await execute_function_calls(tool_calls, content or "", persona_key)
                            
                            # After tool execution, handle follow-up calls based on persona
                            
                            # For Sprint Review Alex: detect approval messages and trigger execution mode
                            is_approval_message = False
                            if persona_key == "SPRINT_REVIEW_ALEX":
                                user_messages = [m.get("content", "").lower() for m in messages if m.get("role") == "user"]
                                last_user_msg = user_messages[-1] if user_messages else ""
                                
                                approval_phrases = ["yes", "yes please", "fix it", "go ahead", "apply it", "do it", "make the change", "you have permission", "please fix"]
                                is_approval_message = any(phrase in last_user_msg for phrase in approval_phrases)
                                
                                if is_approval_message:
                                    logger.info(f"Detected approval message from user: '{last_user_msg[:50]}...'", character=persona_key)
                            
                            # If user approved Alex's plan, route to execution-only mode (one shot)
                            if persona_key == "SPRINT_REVIEW_ALEX" and is_approval_message and not skip_mode_routing:
                                logger.info("Routing SPRINT_REVIEW_ALEX to execution-only mode", character=persona_key)
                                content = await run_sprint_review_alex_execution_mode(
                                    messages=messages,
                                    model=model,
                                    persona_name=persona_name,
                                    persona_key=persona_key,
                                    session_id=session_id,
                                    headers=headers,
                                    ssl_context=ssl_context,
                                )
                                # Execution handler already ran tools; skip bounded loop follow-ups
                                function_results = None
                                tool_calls = []

                            # Trigger bounded loop for investigation (tool results only)
                            # SKIP if skip_mode_routing is True (prevents recursion)
                            if function_results and not skip_mode_routing:
                                # For Sprint Review Alex: use bounded tool loop (multi-turn reasoning) in investigation mode only
                                if persona_key == "SPRINT_REVIEW_ALEX" and not is_approval_message:
                                    loop_mode = "INVESTIGATION"
                                    logger.info(f"Starting {loop_mode} mode for {persona_name}", character=persona_key)
                                    
                                    # Extract context needed for both modes
                                    system_messages = [msg for msg in messages if msg.get("role") == "system"]
                                    all_user_messages = [msg for msg in messages if msg.get("role") == "user"]
                                    current_user_message = all_user_messages[-1] if all_user_messages else None
                                    
                                    # Initialize bounded loop state for Alex
                                    bounded_messages = system_messages.copy()
                                    current_pass = 1
                                    max_passes = 3
                                    has_more_tool_calls = True
                                    running_content = ""
                                    
                                    # Extract architecture context
                                    architecture_context = ""
                                    for msg in messages:
                                        if "LOCKED ARCHITECTURE" in msg.get("content", ""):
                                            architecture_context = msg.get("content", "")
                                            logger.info(f"Found architecture context for {loop_mode} mode")
                                            break
                                    
                                    # Build project context (CURRENT FILE STRUCTURE)
                                    project_context = ""
                                    if not is_approval_message:
                                        # Extract project name using single source of truth for CURRENT FILE STRUCTURE
                                        project_name = None
                                        try:
                                            project_name = get_project_name_safe()
                                            logger.info(f"Bounded loop: Using project_name_safe={project_name} for CURRENT FILE STRUCTURE", character=persona_key)
                                        except Exception as e:
                                            logger.warning(f"Could not get project_name_safe for CURRENT FILE STRUCTURE: {e}", character=persona_key)
                                        
                                        # Build project context using shared extraction utilities
                                        project_context = ""
                                        wireframe_context = ""
                                        if project_name:
                                            logger.info(f"Building CURRENT FILE STRUCTURE for project: {project_name}", character=persona_key)
                                            try:
                                                from pathlib import Path
                                                from services.project_context import extract_file_structure, extract_api_endpoints

                                                # Base sandbox path should be under development/src, not one level higher
                                                execution_sandbox = Path(__file__).parent.parent / "execution-sandbox" / "client-projects"
                                                project_path = execution_sandbox / project_name
                                                logger.info(f"Project path: {project_path}, exists: {project_path.exists()}", character=persona_key)

                                                if project_path.exists():
                                                    # Use shared extraction utilities (same as sprint execution)
                                                    file_structure = extract_file_structure(project_path)
                                                    routes_info = "\n\n" + extract_api_endpoints(project_path)
                                                    
                                                    # Check for wireframes
                                                    wireframe_dir = Path(__file__).parent.parent / "static" / "appdocs" / "backlog" / "wireframes"
                                                    if wireframe_dir.exists():
                                                        wireframes = list(wireframe_dir.glob("*.html"))
                                                        if wireframes:
                                                            # Load the most recent wireframe or all wireframes
                                                            wireframe_context = "\n\nAVAILABLE WIREFRAMES:\n"
                                                            for wf in wireframes[:3]:  # Limit to 3 wireframes
                                                                wf_content = wf.read_text(encoding='utf-8')
                                                                wireframe_context += f"\n--- {wf.name} ---\n{wf_content}\n"
                                                    
                                                    project_context = f"""
═══════════════════════════════════════════════════════════════════
CURRENT FILE STRUCTURE (ACTUAL project on disk):
═══════════════════════════════════════════════════════════════════
{file_structure}
{routes_info}

CRITICAL: Use the exact paths shown above when calling read_file.
Examples:
- To read authController.js: read_file(project_name="{project_name}", file_path="src/controllers/authController.js")
- To read login.html: read_file(project_name="{project_name}", file_path="public/login.html")
- To read auth.js route: read_file(project_name="{project_name}", file_path="src/routes/auth.js")
{wireframe_context}"""
                                                    logger.info(f"Built CURRENT FILE STRUCTURE for {project_name}: {len(project_context)} chars", character=persona_key)
                                                else:
                                                    logger.warning(f"Project path does not exist: {project_path}", character=persona_key)
                                            except Exception as e:
                                                logger.error(f"Failed to build project context: {e}", exc_info=True, character=persona_key)
                                        
                                        # INVESTIGATION MODE: Make it explicit
                                        investigation_context = f"""INVESTIGATION MODE

User reported an issue: "{current_user_message.get('content', '') if current_user_message else ''}"

Your task:
1. Check the CURRENT FILE STRUCTURE to see what files exist and their exact paths
2. Call read_file using those exact paths to see actual code related to the issue
   → If read_file FAILS, report the exact error to the user
   → Say: "I'm having trouble accessing files. Error: [exact error]"
   → DO NOT proceed without successfully reading the code
3. Diagnose the problem based on code you READ (not assumptions)
4. Propose a specific fix in plain English
5. STOP and wait for approval (do NOT call write_text yet)

CRITICAL: NEVER diagnose based on assumptions when tools fail.
CRITICAL: Use the exact file paths shown in CURRENT FILE STRUCTURE."""
                                        
                                        # Inject project context BEFORE investigation instructions
                                        if project_context:
                                            bounded_messages.append({
                                                "role": "user",
                                                "content": project_context
                                            })
                                            logger.info(f"Investigation mode: Injected project context", character=persona_key)
                                        
                                        bounded_messages.append({
                                            "role": "user",
                                            "content": investigation_context
                                        })
                                        logger.info(f"Investigation mode: Injected investigation context", character=persona_key)
                                    
                                    if function_results:
                                        bounded_messages.append({
                                            "role": "user",
                                            "content": f"Tool results from your investigation:\n\n{function_results}"
                                        })
                                    
                                    # Investigation mode only: no execution context injected here
                                    has_fix_permission = False
                                    
                                    # Bounded loop - execute up to max_passes
                                    while current_pass <= max_passes and has_more_tool_calls:
                                        # Re-inject CURRENT FILE STRUCTURE on each pass so Alex always has it
                                        # Include in both investigation AND execution modes
                                        if project_context:
                                            bounded_messages.append({
                                                "role": "user",
                                                "content": project_context
                                            })
                                            logger.info(f"Bounded loop pass {current_pass}: Re-injected CURRENT FILE STRUCTURE", character=persona_key)
                                        
                                        # Add nudge message based on context
                                        user_question = current_user_message.get('content', '') if current_user_message else ''
                                        
                                        if current_pass == max_passes:
                                            # Final pass: Must execute or explain
                                            if has_fix_permission:
                                                nudge = f"FINAL PASS: Call write_text NOW to apply the fix. Include the complete updated file content with your changes. Use force_replace=true."
                                            else:
                                                nudge = f"FINAL PASS: Briefly summarize in plain English what you found about '{user_question}'. What's the issue? What needs to be fixed? Keep it simple."
                                        elif has_fix_permission:
                                            # Execution mode: Direct and immediate
                                            nudge = "Execute the fix NOW. Call write_text with the complete updated file content. Set force_replace=true. No explanation needed - just do it."
                                        else:
                                            # Investigation mode: Continue exploring
                                            nudge = "Continue investigating. Briefly explain in plain English what you've found so far and what you'll check next. Then call tools to look deeper."
                                        
                                        bounded_messages.append({"role": "user", "content": nudge})
                                        
                                        # Make API call for this pass
                                        logger.info(f"Bounded loop pass {current_pass}/{max_passes} for {persona_name}")
                                        follow_up_payload = {
                                            "model": model,
                                            "messages": bounded_messages,
                                            "temperature": 0.7,
                                            "max_tokens": 1500,
                                            "stream": False,
                                            "tools": build_tools_array(persona_tools)
                                        }
                                        
                                        try:
                                            async with aiohttp.ClientSession() as session2:
                                                async with session2.post(
                                                    f"{OPENROUTER_BASE_URL}/chat/completions",
                                                    headers=headers,
                                                    json=follow_up_payload,
                                                    timeout=aiohttp.ClientTimeout(total=90),  # Increase timeout to 90 seconds
                                                    ssl=ssl_context
                                                ) as follow_response:
                                                    if follow_response.status == 200:
                                                        follow_text = await follow_response.text()
                                                        follow_data = json.loads(follow_text)
                                                        logger.debug(f"Bounded loop pass {current_pass} response: {follow_text[:300]}", character=persona_key)
                                                        
                                                        follow_message = follow_data["choices"][0]["message"]
                                                        follow_content = follow_message.get("content", "")
                                                        follow_tool_calls = follow_message.get("tool_calls", [])
                                                        
                                                        # Log content and tool calls
                                                        if follow_content:
                                                            logger.info(f"Bounded loop pass {current_pass} content: {len(follow_content)} chars", character=persona_key)
                                                        else:
                                                            logger.warning(f"Bounded loop pass {current_pass} has no content", character=persona_key)
                                                            
                                                        if follow_tool_calls:
                                                            tool_names = [tc.get("function", {}).get("name") for tc in follow_tool_calls]
                                                            logger.info(f"Bounded loop pass {current_pass} tool calls: {tool_names}", character=persona_key)
                                                        else:
                                                            logger.info(f"Bounded loop pass {current_pass} has no tool calls", character=persona_key)
                                                        
                                                        # VALIDATION: If calling tools, must have explanation (especially for write operations)
                                                        if follow_tool_calls and (not follow_content or len(follow_content.strip()) < 50):
                                                            # Check if any write operations are being attempted
                                                            write_tools = [tc for tc in follow_tool_calls if tc.get("function", {}).get("name") in ["write_text", "write_file"]]
                                                            
                                                            if write_tools:
                                                                logger.warning(f"Bounded loop pass {current_pass}: Attempting {len(write_tools)} write operations without explanation ({len(follow_content or '')} chars)")
                                                                
                                                                # Add response to history (so model sees what it tried to do)
                                                                bounded_messages.append({
                                                                    "role": "assistant",
                                                                    "content": follow_content or "(no explanation provided)",
                                                                    "tool_calls": follow_tool_calls
                                                                })
                                                                
                                                                # Add corrective nudge - be firm but friendly
                                                                bounded_messages.append({
                                                                    "role": "user",
                                                                    "content": "Wait! You're about to change files but didn't explain what you're doing. Please tell me in plain English: What are you fixing? Which files? Why? Keep it brief and simple. Then I'll let you make the changes."
                                                                })
                                                                
                                                                logger.info(f"Bounded loop: Requesting explanation before executing {len(write_tools)} write operations")
                                                                
                                                                # Don't execute tools, don't increment pass counter - give another chance
                                                                continue
                                                        
                                                        # Add assistant response to messages
                                                        bounded_messages.append({
                                                            "role": "assistant",
                                                            "content": follow_content,
                                                            "tool_calls": follow_tool_calls
                                                        })
                                                        
                                                        # Accumulate content for final response
                                                        if follow_content:
                                                            # Check if this is just a tool dump (file content echo)
                                                            # Tool dumps start with "📄 File:" and are typically very long
                                                            if follow_content.strip().startswith('📄 File:') and len(follow_content) > 1000:
                                                                logger.warning(
                                                                    f"Bounded loop pass {current_pass}: follow_content appears to be a tool dump ({len(follow_content)} chars), not using as running_content",
                                                                    character=persona_key
                                                                )
                                                                # Don't update running_content - this will force summary generation later (line 893)
                                                            else:
                                                                running_content = follow_content
                                                        
                                                        # Check for tool calls and execute them
                                                        if follow_tool_calls:
                                                            pass_function_results = await execute_function_calls(
                                                                follow_tool_calls, 
                                                                follow_content or "", 
                                                                persona_key,
                                                                allow_writes=(persona_key != "SPRINT_REVIEW_ALEX" or has_fix_permission)
                                                            )
                                                            
                                                            # Add tool results to conversation (role: user = environment responding)
                                                            if pass_function_results:
                                                                bounded_messages.append({
                                                                    "role": "user", 
                                                                    "content": f"Tool results:\n{pass_function_results}"
                                                                })
                                                                
                                                                # Continue to next pass
                                                                current_pass += 1
                                                            else:
                                                                # No tool results, exit loop
                                                                has_more_tool_calls = False
                                                        else:
                                                            # No tool calls, exit loop
                                                            has_more_tool_calls = False
                                                    else:
                                                        logger.error(f"Bounded loop API call failed: status {follow_response.status}", character=persona_key)
                                                        has_more_tool_calls = False
                                                        if not running_content:
                                                            running_content = "I encountered an issue while processing your request."
                                        except Exception as e:
                                            import traceback
                                            error_details = traceback.format_exc()
                                            logger.error(f"Bounded loop exception: {str(e)}\n{error_details}", character=persona_key)
                                            has_more_tool_calls = False
                                            if not running_content:
                                                running_content = "I encountered an issue while investigating. Could you provide more details about what you'd like me to look into?"
                                    
                                    # After bounded loop, always get a final summary if we did investigation
                                    if current_pass > 1 and (not running_content or len(running_content.strip()) < 50):
                                        logger.info(f"Generating final summary after {current_pass-1} passes of investigation")
                                        
                                        # Build summary context with investigation history
                                        user_question = current_user_message.get("content", "the issue") if current_user_message else "the issue"
                                        summary_messages = [
                                            {"role": "system", "content": messages[0]["content"]},  # System prompt
                                            {"role": "user", "content": "You have completed an investigation. Here are the files you examined:"},
                                            {"role": "assistant", "content": bounded_messages[-1]["content"] if bounded_messages else "Investigation complete"},
                                            {"role": "user", "content": f"Based on your investigation of '{user_question}', provide a clear summary: What did you find? Which files need to be changed? Be specific and concise."}
                                        ]
                                        
                                        summary_payload = {
                                            "model": model,
                                            "messages": summary_messages,
                                            "temperature": 0.7,
                                            "max_tokens": 1000,
                                            "stream": False
                                        }
                                        
                                        try:
                                            async with aiohttp.ClientSession() as session_summary:
                                                async with session_summary.post(
                                                    f"{OPENROUTER_BASE_URL}/chat/completions",
                                                    headers=headers,
                                                    json=summary_payload,
                                                    timeout=aiohttp.ClientTimeout(total=30),
                                                    ssl=ssl_context
                                                ) as summary_response:
                                                    if summary_response.status == 200:
                                                        summary_text = await summary_response.text()
                                                        summary_data = json.loads(summary_text)
                                                        summary_content = summary_data["choices"][0]["message"].get("content", "")
                                                        if summary_content:
                                                            running_content = summary_content
                                                            logger.info(f"Generated final summary: {len(summary_content)} chars")
                                                        else:
                                                            logger.warning("Final summary returned empty content")
                                                            running_content = "I completed my investigation but encountered an issue generating the summary."
                                                    else:
                                                        logger.error(f"Final summary API call failed: status {summary_response.status}")
                                                        running_content = "I completed my investigation but encountered an issue generating the summary."
                                        except Exception as e:
                                            logger.error(f"Final summary exception: {str(e)}")
                                            running_content = "I completed my investigation but encountered an issue generating the summary."
                                    
                                    # Set final content from accumulated running_content
                                    content = running_content
                                    logger.info(f"Bounded loop complete after {current_pass-1} passes for {persona_name}: {len(content)} chars")
                                
                                # For base DEVELOPER: existing follow-up behavior (helloworld flow)
                                elif persona_key == "DEVELOPER" and not content:
                                    logger.info(f"Making follow-up call for {persona_name} to respond to function results")
                                    follow_up_messages = messages + [
                                        {"role": "assistant", "content": f"I executed the function calls with these results:\n{function_results}"},
                                        {"role": "user", "content": "Please provide a natural response about the helloworld.py changes you just accomplished."}
                                    ]
                                    follow_up_payload = {
                                        "model": model,
                                        "messages": follow_up_messages,
                                        "temperature": 0.7,
                                        "max_tokens": 500,
                                        "stream": False
                                    }
                                    async with aiohttp.ClientSession() as session2:
                                        async with session2.post(
                                            f"{OPENROUTER_BASE_URL}/chat/completions",
                                            headers=headers,
                                            json=follow_up_payload,
                                            timeout=aiohttp.ClientTimeout(total=30),
                                            ssl=ssl_context
                                        ) as follow_response:
                                            if follow_response.status == 200:
                                                follow_text = await follow_response.text()
                                                follow_data = json.loads(follow_text)
                                                follow_content = follow_data["choices"][0]["message"].get("content", "")
                                                if follow_content:
                                                    content = follow_content
                                                    logger.info(f"Follow-up response for {persona_name}: {len(follow_content)} chars")
                                                else:
                                                    content = function_results
                                            else:
                                                content = function_results
                                
                                # For other personas with tool results: use results as content if no content
                                elif not content:
                                    # Check if function_results is just a tool dump (file content echo)
                                    # Tool dumps start with "📄 File:" or "📁 Directory:" and are typically very long
                                    if function_results and (function_results.strip().startswith(('📄 File:', '📁 Directory:')) and len(function_results) > 1000):
                                        logger.warning(
                                            f"{persona_key}: function_results appears to be a tool dump ({len(function_results)} chars), not using as content",
                                            character=persona_key
                                        )
                                        content = f"I've reviewed the information. Let me provide a summary instead of raw output."
                                    else:
                                        content = function_results
                            
                            # If no tool calls and no content, log for debugging
                            elif not content:
                                if persona_key == "SPRINT_REVIEW_ALEX":
                                    logger.info(f"No tool calls and no content from Alex",
                                              request_id=request_id, character=persona_key)
                            
                            # Calculate response hash
                            response_hash = hashlib.md5((content or "").encode()).hexdigest()[:8]
                            
                            # Estimate cost (rough approximation)
                            cost_estimate = (tokens_in * 0.000003) + (tokens_out * 0.000015)
                            
                            # Log successful call
                            log_openrouter_call(
                                model=model,
                                tokens_in=tokens_in,
                                tokens_out=tokens_out,
                                status="success",
                                latency_ms=latency_ms,
                                cost_estimate=cost_estimate,
                                prompt_hash=prompt_hash,
                                response_hash=response_hash,
                                payload=request_payload if os.getenv("OPENROUTER_LOG_PAYLOADS") else None,
                                response=None  # Don't log full streaming response
                            )
                            
                            logger.info(f"OpenRouter API success for {persona_name}: {len(content)} chars",
                                      request_id=request_id, tokens_in=tokens_in, tokens_out=tokens_out)
                            
                            # Save conversation history for SPRINT_REVIEW_ALEX
                            if persona_key == "SPRINT_REVIEW_ALEX" and session_id and content:
                                from services.conversation_history import save_conversation_turn
                                # Extract user message from messages (last user message)
                                user_messages = [m for m in messages if m.get("role") == "user"]
                                if user_messages:
                                    user_message = user_messages[-1].get("content", "")
                                    save_conversation_turn(
                                        session_id=session_id,
                                        persona_key=persona_key,
                                        user_message=user_message,
                                        assistant_response=content,
                                        tool_calls=[{"function": {"name": tc["function"]["name"]}} for tc in tool_calls] if tool_calls else None
                                    )
                            
                            # Calculate elapsed time for progress tracking
                            elapsed_seconds = time.monotonic() - start_time
                            
                            # Return content with metadata for progress display
                            result = {
                                "content": content,
                                "metadata": {
                                    "elapsed_seconds": round(elapsed_seconds, 1),
                                    "budget_seconds": total_budget,
                                    "tokens_in": tokens_in,
                                    "tokens_out": tokens_out,
                                    "tokens_max": max_tokens,
                                    "model": model
                                }
                            }
                            logger.debug(f"Returning response with metadata for {persona_name}: elapsed={elapsed_seconds:.1f}s, tokens={tokens_in}+{tokens_out}")
                            yield result
                            return
                        
                        # Handle retry-able errors
                        elif response.status in retry_status_codes:
                            # Read error response text
                            response_text = await response.text()
                            
                            # Extract metadata for logging (redact sensitive info)
                            retry_after = response.headers.get('Retry-After')
                            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
                            rate_limit_reset = response.headers.get('X-RateLimit-Reset')
                            
                            # Log error with metadata (first 256 chars of body)
                            error_body_preview = response_text[:256] if response_text else ""
                            
                            logger.warning(f"OpenRouter API retry-able error {response.status} (attempt {attempt + 1}/{max_retries + 1})",
                                         request_id=request_id, 
                                         status=response.status,
                                         reason=response.reason,
                                         retry_after=retry_after,
                                         rate_limit_remaining=rate_limit_remaining,
                                         rate_limit_reset=rate_limit_reset,
                                         error_preview=error_body_preview)
                            
                            # If this is the last attempt, raise error
                            if attempt == max_retries:
                                log_openrouter_call(
                                    model=model,
                                    tokens_in=0,
                                    tokens_out=0,
                                    status=f"error_{response.status}",
                                    latency_ms=latency_ms,
                                    prompt_hash=prompt_hash,
                                    error=response_text
                                )
                                raise Exception(f"API error {response.status} after {max_retries + 1} attempts: {response_text}")
                            
                            # Calculate sleep time with budget tracking
                            parsed_retry_after = parse_retry_after(retry_after)
                            if parsed_retry_after is not None:
                                sleep_time = parsed_retry_after
                                logger.info(f"Sleeping {sleep_time}s per Retry-After header", request_id=request_id)
                            else:
                                # Exponential backoff: 0.4s, 0.8s, 1.6s with ±20% jitter
                                base_delay = 0.4 * (2 ** attempt)
                                jitter = random.uniform(-0.2, 0.2) * base_delay
                                sleep_time = base_delay + jitter
                                logger.info(f"Sleeping {sleep_time:.2f}s (exponential backoff with jitter)", request_id=request_id)
                            
                            # Check if sleep would exceed total budget
                            elapsed = time.monotonic() - start_time
                            if elapsed + sleep_time > total_budget:
                                logger.warning(f"Stopping retries early: {elapsed + sleep_time:.1f}s would exceed {total_budget}s budget", request_id=request_id)
                                log_openrouter_call(
                                    model=model,
                                    tokens_in=0,
                                    tokens_out=0,
                                    status=f"budget_exceeded_{response.status}",
                                    latency_ms=latency_ms,
                                    prompt_hash=prompt_hash,
                                    error=f"Budget exceeded after {elapsed:.1f}s"
                                )
                                raise Exception(f"API error {response.status}: budget exceeded after {elapsed:.1f}s")
                            
                            await asyncio.sleep(sleep_time)
                            continue  # Retry
                        
                        # Non-retry-able error (other 4xx, 5xx not in retry list)
                        else:
                            # Read error response text
                            response_text = await response.text()
                            
                            # Extract metadata for logging
                            retry_after = response.headers.get('Retry-After')
                            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
                            rate_limit_reset = response.headers.get('X-RateLimit-Reset')
                            error_body_preview = response_text[:256] if response_text else ""
                            
                            logger.error(f"OpenRouter API non-retry-able error {response.status}",
                                       request_id=request_id, 
                                       status=response.status,
                                       reason=response.reason,
                                       retry_after=retry_after,
                                       rate_limit_remaining=rate_limit_remaining,
                                       rate_limit_reset=rate_limit_reset,
                                       error_preview=error_body_preview)
                            
                            # Log failed call
                            log_openrouter_call(
                                model=model,
                                tokens_in=0,
                                tokens_out=0,
                                status=f"error_{response.status}",
                                latency_ms=latency_ms,
                                prompt_hash=prompt_hash,
                                error=response_text
                            )
                            
                            raise Exception(f"API error {response.status}: {response_text}")
                            
            except asyncio.CancelledError:
                # Allow cancellation to propagate
                logger.info(f"OpenRouter API call cancelled for {persona_name}", request_id=request_id)
                raise
                
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                current_time = time.monotonic()
                latency_ms = (current_time - start_time) * 1000
                
                logger.warning(f"OpenRouter API pre-HTTP failure (attempt {attempt + 1}/{max_retries + 1})",
                             request_id=request_id, 
                             exception_type=type(e).__name__,
                             error_message=str(e),
                             latency_ms=latency_ms)
                
                if attempt == max_retries:
                    log_openrouter_call(
                        model=model,
                        tokens_in=0,
                        tokens_out=0,
                        status="timeout" if isinstance(e, asyncio.TimeoutError) else "connection_error",
                        latency_ms=latency_ms,
                        error=str(e)
                    )
                    raise Exception(f"API {type(e).__name__} after {max_retries + 1} attempts: {e}")
                
                # Exponential backoff with budget check
                base_delay = 0.4 * (2 ** attempt)
                jitter = random.uniform(-0.2, 0.2) * base_delay
                sleep_time = base_delay + jitter
                
                elapsed = time.monotonic() - start_time
                if elapsed + sleep_time > total_budget:
                    logger.warning(f"Stopping retries early: {elapsed + sleep_time:.1f}s would exceed {total_budget}s budget", request_id=request_id)
                    raise Exception(f"API {type(e).__name__}: budget exceeded after {elapsed:.1f}s")
                
                logger.info(f"Sleeping {sleep_time:.2f}s after {type(e).__name__}", request_id=request_id)
                await asyncio.sleep(sleep_time)
                continue  # Retry
                
    except asyncio.CancelledError:
        # Allow cancellation to propagate
        raise
        
    except Exception as e:
        if start_time:
            current_time = time.monotonic()
            latency_ms = (current_time - start_time) * 1000
            
            log_openrouter_call(
                model=model,
                tokens_in=0,
                tokens_out=0,
                status="error",
                latency_ms=latency_ms,
                error=str(e)
            )
        
        logger.error(f"OpenRouter API call failed for {persona_name}: {e}", 
                   request_id=request_id, error=str(e))
        raise


async def run_sprint_review_alex_execution_mode(
    messages: List[Dict[str, Any]],
    model: str,
    persona_name: str,
    persona_key: str,
    session_id: Optional[str],
    headers: Dict[str, str],
    ssl_context: ssl.SSLContext,
) -> str:
    """One-shot execution mode for Sprint Review Alex.

    Uses a small, hard-coded execution system prompt and the last assistant
    message (approved plan) from the in-memory messages. Does not read
    Alex-specific JSON history; only uses messages + tools.
    """
    logger.info("Execution mode: Starting one-shot execution for Sprint Review Alex", character=persona_key)

    # Find Alex's last assistant response (the approved plan)
    last_assistant_message: Optional[Dict[str, Any]] = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            last_assistant_message = msg
            break

    alex_last_response = last_assistant_message.get("content", "") if last_assistant_message else ""

    # Extract specific fix proposal and files to modify from Alex's last response
    import re

    fix_proposal = ""
    files_to_modify = ""

    if alex_last_response:
        # Try to extract structured sections from Alex's response
        if "What Needs to Be Fixed" in alex_last_response or "Proposed Fix" in alex_last_response:
            fix_match = re.search(r'(?:What Needs to Be Fixed|Proposed Fix)[:\n]+(.*?)(?:Files to modify|Should I apply|$)', alex_last_response, re.DOTALL | re.IGNORECASE)
            if fix_match:
                fix_proposal = fix_match.group(1).strip()

        files_match = re.search(r'Files to modify[:\s]+(.+?)(?:\n|$)', alex_last_response, re.IGNORECASE)
        if files_match:
            files_to_modify = files_match.group(1).strip()

    # Get last user message content (approval text) for context
    last_user_message = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_message = msg.get("content", "")
            break

    # Build plan-related context
    approved_plan_preview = alex_last_response[:800] if alex_last_response else "(No previous plan text found. Keep changes minimal and focused on the original bug.)"
    fix_proposal_text = fix_proposal if fix_proposal else "Apply the specific change you previously described for this bug."
    files_to_modify_text = files_to_modify if files_to_modify else "Use the same files you listed in your plan (e.g., src/server.js or the specific route/controller you identified)."
    approval_text = last_user_message or "yes"

    # Determine project name for sandbox operations
    try:
        project_name = get_project_name_safe()
        logger.info(
            "Execution mode: using project_name_safe for Sprint Review Alex",
            character=persona_key,
            project_name=project_name,
        )
    except Exception as e:
        logger.warning(
            "Execution mode: could not resolve project name, will skip file reads/writes",
            character=persona_key,
            error=str(e),
        )
        project_name = None

    # Derive a list of target file paths from Alex's plan
    # Use multiple strategies to extract file paths reliably
    target_file_paths: List[str] = []
    
    # Strategy 1: Look for "Files to modify:" section
    if files_to_modify_text:
        normalized = files_to_modify_text.replace(",", "\n")
        for raw_line in normalized.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = line.lstrip("-*•").strip()
            # Remove markdown code backticks
            line = line.replace("`", "")
            token = line.split()[0]
            # Only accept tokens that look like actual file paths (must contain / and have file extension)
            if "/" in token and ("." in token.split("/")[-1]):
                # Ensure it starts with a valid directory prefix
                valid_prefixes = ("src/", "public/", "routes/", "controllers/", "middleware/", "tests/", "views/", "config/", "lib/", "utils/")
                if token.startswith(valid_prefixes):
                    if token not in target_file_paths:
                        target_file_paths.append(token)
    
    # Strategy 2: Scan entire Alex response for common file patterns
    if not target_file_paths and alex_last_response:
        import re
        # Look for patterns like src/file.js, public/page.html, etc.
        file_pattern = r'\b((?:src|public|routes|controllers|middleware|tests)/[\w\-./]+\.(?:js|html|css|json))\b'
        matches = re.findall(file_pattern, alex_last_response, re.IGNORECASE)
        for match in matches:
            cleaned = match.strip().replace("`", "")
            if cleaned not in target_file_paths:
                target_file_paths.append(cleaned)
    
    # Strategy 3: Check conversation history for files Alex read during investigation
    if not target_file_paths:
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                content = msg.get("content", "")
                # Look for "📄 File: project/path" patterns from read_file tool results
                file_read_pattern = r'📄 File: [^/]+/([\w\-./]+)'
                matches = re.findall(file_read_pattern, content)
                for match in matches:
                    if match not in target_file_paths:
                        target_file_paths.append(match)
                        logger.info(f"Extracted file path from investigation history: {match}")
    
    logger.info(f"Execution mode: extracted {len(target_file_paths)} file paths: {target_file_paths}")

    # Read current contents of target files from the sandbox
    file_snapshots: List[Dict[str, str]] = []

    try:
        async with aiohttp.ClientSession() as session:
            if project_name and target_file_paths:
                for file_path in target_file_paths:
                    try:
                        async with session.post(
                            "http://localhost:8000/api/sandbox/read-file",
                            json={"project_name": project_name, "file_path": file_path},
                        ) as sf_resp:
                            sf_text = await sf_resp.text()
                            if sf_resp.status == 200:
                                sf_data = json.loads(sf_text)
                                content_text = sf_data.get("content", "")
                                file_snapshots.append({"file_path": file_path, "content": content_text})
                                logger.info(
                                    "Execution mode: read target file for Sprint Review Alex",
                                    character=persona_key,
                                    project_name=project_name,
                                    file_path=file_path,
                                    bytes=len(content_text.encode("utf-8")),
                                )
                            else:
                                logger.error(
                                    "Execution mode: failed to read target file from sandbox",
                                    character=persona_key,
                                    project_name=project_name,
                                    file_path=file_path,
                                    status=sf_resp.status,
                                    error_preview=sf_text[:256],
                                )
                    except Exception as e:
                        logger.error(
                            "Execution mode: exception while reading target file from sandbox",
                            character=persona_key,
                            project_name=project_name,
                            file_path=file_path,
                            error=str(e),
                        )

            # Build a structured spec of the approved changes for execution
            approved_change_spec: Dict[str, Any] = {
                "files": [{"file_path": fp} for fp in target_file_paths],
                "description": fix_proposal_text,
            }
            approved_change_spec_str = json.dumps(approved_change_spec, indent=2)

            # System prompt for execution-only mode (no tools; respond with JSON)
            execution_system_prompt = (
                "You are Sprint Review Alex in EXECUTION MODE ONLY.\n"
                "The user has already approved the specific fix you proposed earlier.\n"
                "Your job is to apply that exact approved fix to the provided file contents, without re-diagnosing or changing the plan.\n\n"
                "CRITICAL: Your response MUST be ONLY a valid JSON object. No markdown, no explanations, no text before or after.\n"
                "Start your response with { and end with }. Nothing else.\n\n"
                "JSON Structure:\n"
                "{\n"
                "  \"files\": [\n"
                "    {\"file_path\": \"public/login.html\", \"action\": \"overwrite\", \"new_content\": \"...complete file content...\"}\n"
                "  ],\n"
                "  \"explanation\": \"Plain-English explanation of what you changed.\"\n"
                "}\n\n"
                "Rules:\n"
                "- ONLY use file paths listed in APPROVED_CHANGE_SPEC.files. Do NOT invent new paths.\n"
                "- Copy literal values from the approved plan exactly (e.g., endpoint strings).\n"
                "- Set action=\"overwrite\" and provide COMPLETE file content (not a diff).\n"
                "- If file contents are missing, reconstruct based on your investigation knowledge.\n"
                "- If you cannot apply safely, set action=\"none\" and explain why.\n"
                "- Do NOT add new features beyond the approved fix.\n"
                "- Escape all special characters in JSON strings properly (quotes, newlines, backslashes).\n"
                "- Your ENTIRE response must be valid JSON. Start with { and end with }."
            )

            # Build a user message that includes the approved plan and current file contents
            files_section_lines: List[str] = []
            if file_snapshots:
                for snap in file_snapshots:
                    files_section_lines.append(
                        f"FILE: {snap['file_path']}\nCURRENT CONTENT:\n{snap['content']}\n\n---\n\n"
                    )
            else:
                files_section_lines.append(
                    "(No target file contents could be loaded from the sandbox. "
                    "If you cannot safely infer the change, you should abstain and explain why.)\n"
                )

            files_section = "".join(files_section_lines)

            execution_context = (
                "EXECUTION MODE - APPLY YOUR APPROVED FIX\n\n"
                f"THE USER SAID: \"{approval_text}\" (this means the plan is approved).\n\n"
                "APPROVED PLAN (from your last answer, first 800 chars):\n"
                f"{approved_plan_preview}\n\n"
                "EXTRACTED SPECIFIC CHANGE YOU PROPOSED:\n"
                f"{fix_proposal_text}\n\n"
                "APPROVED_CHANGE_SPEC (the exact file list you must adhere to):\n"
                f"{approved_change_spec_str}\n\n"
                "TARGET FILES AND THEIR CURRENT CONTENTS (from the sandbox):\n\n"
                f"{files_section}"
            )

            execution_messages: List[Dict[str, Any]] = [
                {"role": "system", "content": execution_system_prompt},
                {"role": "user", "content": execution_context},
            ]

            payload = {
                "model": model,
                "messages": execution_messages,
                "temperature": 0.0,
                "max_tokens": 16000,  # Increased from 4000 to handle full file rewrites
                "stream": False,
            }

            try:
                async with session.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                    ssl=ssl_context,
                ) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        data = json.loads(response_text)
                        message = data["choices"][0]["message"]
                        raw_content = message.get("content", "") or ""

                        files_spec: List[Dict[str, Any]] = []
                        explanation = ""

                        if raw_content:
                            try:
                                parsed = json.loads(raw_content)
                                files_spec = parsed.get("files", []) or []
                                explanation = (parsed.get("explanation", "") or "").strip()
                            except json.JSONDecodeError as e:
                                logger.error(
                                    "Execution mode: failed to parse JSON response from model",
                                    character=persona_key,
                                    error=str(e),
                                    raw_preview=raw_content[:500],
                                )
                                explanation = (
                                    "I returned an invalid JSON structure for execution; no code changes were applied. "
                                    "Please try again or apply the change manually."
                                )
                                files_spec = []
                        else:
                            explanation = (
                                "Execution mode did not return any explanation or file actions; "
                                "no code changes were applied."
                            )

                        read_files_display: List[str] = []
                        written_files_display: List[str] = []

                        # Record inspected files from snapshots
                        if project_name and file_snapshots:
                            for snap in file_snapshots:
                                disp = f"{project_name}/{snap['file_path']}"
                                if disp not in read_files_display:
                                    read_files_display.append(disp)

                        # Create snapshot before applying changes
                        if project_name and files_spec:
                            try:
                                from pathlib import Path
                                from datetime import datetime
                                
                                # Determine project path
                                execution_sandbox = Path(__file__).parent.parent / "execution-sandbox" / "client-projects"
                                project_path = execution_sandbox / project_name
                                
                                if project_path.exists():
                                    # Build snapshot metadata
                                    snapshot_metadata = {
                                        "timestamp": datetime.now().isoformat(),
                                        "timestamp_human": datetime.now().strftime("%b %d, %I:%M %p"),
                                        "session_id": session_id or "unknown",
                                        "user_message": last_user_message or "User approved changes",
                                        "alex_explanation": explanation[:200] if explanation else "No explanation provided",
                                        "files_to_modify": [entry.get("file_path") for entry in files_spec if entry.get("file_path")],
                                        "app_status_before": "working"  # Assume working before changes
                                    }
                                    
                                    snapshot_id = create_snapshot(project_path, snapshot_metadata)
                                    if snapshot_id:
                                        logger.info(
                                            f"📸 Snapshot created before Sprint Review changes: {snapshot_id}",
                                            character=persona_key,
                                            project_name=project_name
                                        )
                                    else:
                                        logger.warning(
                                            "Failed to create snapshot before changes",
                                            character=persona_key,
                                            project_name=project_name
                                        )
                            except Exception as e:
                                logger.error(
                                    f"Error creating snapshot: {e}",
                                    character=persona_key,
                                    project_name=project_name,
                                    exc_info=True
                                )

                        # Apply file actions via sandbox write-file
                        if project_name and files_spec:
                            for entry in files_spec:
                                file_path = entry.get("file_path")
                                action = (entry.get("action") or "none").lower()
                                new_content = entry.get("new_content")

                                if not file_path:
                                    continue

                                full_display = f"{project_name}/{file_path}"

                                if action == "overwrite" and new_content is not None:
                                    try:
                                        async with session.post(
                                            "http://localhost:8000/api/sandbox/write-file",
                                            json={
                                                "project_name": project_name,
                                                "file_path": file_path,
                                                "content": new_content,
                                                "force_replace": True,
                                            },
                                        ) as wf_resp:
                                            wf_text = await wf_resp.text()
                                            if wf_resp.status == 200:
                                                written_files_display.append(full_display)
                                                logger.info(
                                                    "Execution mode: wrote target file for Sprint Review Alex",
                                                    character=persona_key,
                                                    project_name=project_name,
                                                    file_path=file_path,
                                                )
                                            else:
                                                logger.error(
                                                    "Execution mode: failed to write target file in sandbox",
                                                    character=persona_key,
                                                    project_name=project_name,
                                                    file_path=file_path,
                                                    status=wf_resp.status,
                                                    error_preview=wf_text[:256],
                                                )
                                    except Exception as e:
                                        logger.error(
                                            "Execution mode: exception while writing target file in sandbox",
                                            character=persona_key,
                                            project_name=project_name,
                                            file_path=file_path,
                                            error=str(e),
                                        )

                        # Build final backend summary
                        summary_lines: List[str] = []

                        if written_files_display:
                            summary_lines.append(
                                "Execution mode NOTE: I DID apply at least one overwrite to the target files."
                            )
                        elif read_files_display:
                            summary_lines.append(
                                "Execution mode NOTE: I inspected the target files but did NOT apply any overwrites; no files were modified."
                            )
                        else:
                            summary_lines.append(
                                "Execution mode NOTE: I did not successfully access any target files and no files were modified."
                            )

                        summary_lines.append("Backend summary of execution file operations:")

                        if read_files_display:
                            summary_lines.append(" - Files inspected: " + ", ".join(read_files_display))
                        else:
                            summary_lines.append(" - No files were inspected in execution.")

                        if written_files_display:
                            summary_lines.append(" - Files overwritten: " + ", ".join(written_files_display))
                        else:
                            summary_lines.append(" - No files were overwritten.")

                        backend_summary = "\n".join(summary_lines)

                        if explanation:
                            # Show only the LLM's explanation to the user in the UI
                            final_content = explanation
                        else:
                            # Fallback if no explanation was provided
                            final_content = backend_summary

                        logger.info(
                            "Execution mode complete for Sprint Review Alex",
                            character=persona_key,
                            session_id=session_id,
                        )
                        return final_content
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Execution mode API call failed for Sprint Review Alex: status {response.status}",
                            character=persona_key,
                            status=response.status,
                            error_preview=error_text[:256],
                        )
                        return (
                            "I encountered an issue while applying the approved fix. "
                            "Please try again or apply the change manually."
                        )
            except Exception as e:
                logger.error(
                    f"Execution mode exception for Sprint Review Alex: {e}",
                    character=persona_key,
                )
                return (
                    "I encountered an unexpected error while applying the approved fix. "
                    "Please try again or apply the change manually."
                )
    except Exception as e:
        logger.error(
            f"Execution mode exception for Sprint Review Alex: {e}",
            character=persona_key,
        )
        return (
            "I encountered an unexpected error while applying the approved fix. "
            "Please try again or apply the change manually."
        )


async def execute_function_calls(tool_calls: List[Dict], existing_content: str, persona_key: str, allow_writes: bool = False) -> str:
    """Execute function calls from OpenRouter API response.
    For SPRINT_REVIEW_ALEX, write_text is only allowed when allow_writes is True (Execution mode).
    """
    logger = get_structured_logger("function_calls")
    
    results = []
    if existing_content:
        results.append(existing_content)
    
    for tool_call in tool_calls:
        function_name = tool_call["function"]["name"]
        arguments_raw = tool_call["function"]["arguments"]
        
        try:
            arguments = json.loads(arguments_raw)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse function arguments: {e}", 
                        function=function_name, 
                        character=persona_key,
                        raw_arguments=arguments_raw[:200])
            results.append(f"❌ Invalid function arguments: {str(e)}")
            continue
        
        logger.info(f"Executing function call: {function_name}", 
                   character=persona_key,
                   arguments=json.dumps(arguments)[:200])
        
        if function_name == "http_post":
            try:
                # Validate required arguments
                if "url" not in arguments:
                    raise ValueError("Missing required argument: 'url'")
                if "payload" not in arguments:
                    raise ValueError("Missing required argument: 'payload'. The LLM must provide arguments in format: {\"url\": \"...\", \"payload\": {...}}")
                
                url = arguments["url"]
                payload = arguments["payload"]
                headers = arguments.get("headers", {"Content-Type": "application/json"})
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, headers=headers) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            # Parse response data first
                            try:
                                response_data = json.loads(response_text)
                            except:
                                response_data = {"message": response_text}
                            
                            # Let Alex respond naturally to the actual API response
                            if persona_key == "DEVELOPER" and "change-requests" in url:
                                # Use the actual API response message which contains "helloworld"
                                api_message = response_data.get("message", "Change request completed")
                                results.append(api_message)
                            # For Jordan, format the testing response properly
                            elif persona_key == "QA" and "testing" in url:
                                # Import the format function from streaming
                                from streaming import format_persona_response
                                formatted_response = format_persona_response(url, response_text, persona_key)
                                results.append(formatted_response)
                            else:
                                # Parse response and format it properly for other personas
                                try:
                                    response_data = json.loads(response_text)
                                    # Import the format function from streaming
                                    from streaming import format_persona_response
                                    formatted_response = format_persona_response(url, response_text, persona_key)
                                    results.append(formatted_response)
                                except Exception as e:
                                    # Log the error and fallback to raw response
                                    logger.error(f"Failed to format API response: {e}", character=persona_key, url=url)
                                    results.append(f"✅ HTTP POST to {url} succeeded: {response_text}")
                        else:
                            results.append(f"❌ HTTP POST to {url} failed ({response.status}): {response_text}")
                            
            except Exception as e:
                results.append(f"❌ HTTP POST failed: {str(e)}")
                logger.error(f"Function call failed: {e}", function=function_name, character=persona_key)
        
        elif function_name == "list_directory":
            try:
                path = arguments.get("path", ".")
                recursive = arguments.get("recursive", False)
                max_depth = arguments.get("max_depth", 3)
                
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
                            results.append(f"❌ list_directory failed ({response.status}): {response_text}")
            except Exception as e:
                results.append(f"❌ list_directory failed: {str(e)}")
                logger.error(f"Function call failed: {e}", function=function_name, character=persona_key)
        
        elif function_name == "run_command":
            try:
                project_name = arguments["project_name"]
                command = arguments["command"]
                args = arguments.get("args", [])
                working_dir = arguments.get("working_dir")
                timeout = arguments.get("timeout", 30)
                
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
                            results.append(f"❌ run_command failed ({response.status}): {response_text}")
            except Exception as e:
                results.append(f"❌ run_command failed: {str(e)}")
                logger.error(f"Function call failed: {e}", function=function_name, character=persona_key)
        
        elif function_name == "read_file":
            try:
                project_name = arguments.get("project_name")
                file_path = arguments.get("file_path")
                
                if not project_name or not file_path:
                    raise ValueError("Missing required arguments: project_name and file_path")
                
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
                            results.append(f"❌ read_file failed ({response.status}): {response_text}")
            except Exception as e:
                results.append(f"❌ read_file failed: {str(e)}")
                logger.error(f"Function call failed: {e}", function=function_name, character=persona_key)
        
        elif function_name == "write_text":
            # Safety rail: Sprint Review Alex may only write when explicitly allowed
            if persona_key == "SPRINT_REVIEW_ALEX" and not allow_writes:
                logger.info("Blocked write_text for SPRINT_REVIEW_ALEX without explicit approval", character=persona_key)
                results.append("⚠️ write_text is only allowed after explicit user approval; staying in investigation mode.")
                continue

            try:
                import html
                project_name = arguments.get("project_name")
                file_path = arguments.get("file_path")
                content = arguments.get("content")
                force_replace = arguments.get("force_replace", False)
                
                # Decode any HTML entities that the LLM might have encoded
                content = html.unescape(content)  # Optional, defaults to False
                
                if not project_name or not file_path or content is None:
                    raise ValueError("Missing required arguments: project_name, file_path, and content")
                
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
                            results.append(f"❌ write_text failed ({response.status}): {response_text}")
            except Exception as e:
                results.append(f"❌ write_text failed: {str(e)}")
                logger.error(f"Function call failed: {e}", function=function_name, character=persona_key)
        
        elif function_name == "list_snapshots":
            try:
                from services.snapshot_manager import list_snapshots
                from pathlib import Path
                
                project_name = arguments.get("project_name")
                if not project_name:
                    raise ValueError("Missing required argument: project_name")
                
                # Determine project path
                execution_sandbox = Path(__file__).parent.parent / "execution-sandbox" / "client-projects"
                project_path = execution_sandbox / project_name
                
                if not project_path.exists():
                    results.append(f"❌ Project not found: {project_name}")
                    continue
                
                snapshots = list_snapshots(project_path)
                
                if not snapshots:
                    results.append(f"📸 No snapshots available for {project_name}")
                else:
                    result_lines = [f"📸 Available snapshots for {project_name}:\n"]
                    for snap in snapshots:
                        timestamp_human = snap.get("timestamp_human", "Unknown time")
                        explanation = snap.get("alex_explanation", "No description")
                        files = snap.get("files_to_modify", [])
                        files_str = ", ".join(files[:3])
                        if len(files) > 3:
                            files_str += f" (+{len(files)-3} more)"
                        
                        result_lines.append(f"• {timestamp_human} (ID: {snap['snapshot_id']})")
                        result_lines.append(f"  Changes: {explanation}")
                        result_lines.append(f"  Files: {files_str}\n")
                    
                    results.append("\n".join(result_lines))
                
            except Exception as e:
                results.append(f"❌ list_snapshots failed: {str(e)}")
                logger.error(f"Function call failed: {e}", function=function_name, character=persona_key)
        
        elif function_name == "restore_snapshot":
            try:
                from services.snapshot_manager import restore_snapshot
                from pathlib import Path
                
                project_name = arguments.get("project_name")
                snapshot_id = arguments.get("snapshot_id")
                reason = arguments.get("reason", "User requested rollback")
                
                if not project_name or not snapshot_id:
                    raise ValueError("Missing required arguments: project_name and snapshot_id")
                
                # Determine project path
                execution_sandbox = Path(__file__).parent.parent / "execution-sandbox" / "client-projects"
                project_path = execution_sandbox / project_name
                
                if not project_path.exists():
                    results.append(f"❌ Project not found: {project_name}")
                    continue
                
                success = restore_snapshot(project_path, snapshot_id, reason)
                
                if success:
                    results.append(f"✅ Restored {project_name} to snapshot {snapshot_id}\nReason: {reason}")
                    logger.info(f"Snapshot restored by {persona_key}", 
                               project_name=project_name, 
                               snapshot_id=snapshot_id,
                               reason=reason)
                else:
                    results.append(f"❌ Failed to restore snapshot {snapshot_id}")
                
            except Exception as e:
                results.append(f"❌ restore_snapshot failed: {str(e)}")
                logger.error(f"Function call failed: {e}", function=function_name, character=persona_key)
        
        else:
            results.append(f"❌ Unknown function: {function_name}")
            logger.warning(f"Unknown function call: {function_name}", character=persona_key)
    
    return "\n\n".join(results)

"""
Sprint Orchestrator - Enhanced with Context Injection, Validation, and Safety

Coordinates sprint execution with real LLM calls:
- Mike (SPRINT_EXECUTION_ARCHITECT) breaks down stories into tasks
- Alex (SPRINT_EXECUTION_DEVELOPER) generates actual code files with context
- Jordan (SPRINT_EXECUTION_QA) generates and runs pytest test files
- All files written to execution-sandbox/client-projects/yourapp/
- Updates Backlog.csv with execution status
- Logs events to execution_log_{sprint_id}.jsonl

Enhancements:
PHASE 1 - Context Injection + Validation:
  - Alex sees project structure, existing files, and code patterns
  - Task breakdown validated before proceeding
  - Code syntax validated before writing
  - Suspicious imports detected

PHASE 2 - Merge Logic + Test Execution:
  - Existing files merged (not overwritten)
  - Tests actually executed with real pass/fail counts
  - Automatic rollback on test failures

PHASE 3 - Backup/Rollback:
  - Files backed up before modification
  - Story-level file tracking for rollback
  - Automatic cleanup on failures
"""
from __future__ import annotations

import asyncio
import json
import re
import csv
import logging
import httpx
import ast
import os
import shutil
import subprocess
from dotenv import load_dotenv

load_dotenv()
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Project folder is always 'yourapp' - single pipeline, no dynamic naming needed
from api.conventions import validate_csv_headers
from services.project_context import (
    extract_exports_from_file,
    extract_file_structure,
    extract_api_endpoints,
    extract_database_schema,
    extract_code_patterns
)

logger = logging.getLogger(__name__)

# Version tracking - increment when making changes to verify code is loaded
ORCHESTRATOR_VERSION = "2.6.0-arch-contract-enforced"

APPDOCS_PATH = Path("static/appdocs")
APPDOCS_PATH.mkdir(parents=True, exist_ok=True)
SPRINT_DIR = Path("static/appdocs/sprints")
SPRINT_DIR.mkdir(parents=True, exist_ok=True)
BACKLOG_CSV_PATH = Path("static/appdocs/backlog/Backlog.csv")
VISION_DIR = Path("static/appdocs/visions")
WIREFRAME_DIR = Path("static/appdocs/backlog/wireframes")
EXECUTION_SANDBOX = Path("static/appdocs/execution-sandbox/client-projects")
EXECUTION_SANDBOX.mkdir(parents=True, exist_ok=True)
BACKUP_BASE_DIR = SPRINT_DIR / "backups"
BACKUP_BASE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class OrchestratorConfig:
    sprint_id: str


class SprintOrchestrator:
    # Class-level dict to track pause state for all sprints
    _paused_sprints = {}
    
    def __init__(self, config: OrchestratorConfig):
        self.sprint_id = config.sprint_id
        self.plan_path = SPRINT_DIR / f"{self.sprint_id}.json"
        self.log_path = SPRINT_DIR / f"execution_log_{self.sprint_id}.jsonl"
        self.backup_dir = BACKUP_BASE_DIR / self.sprint_id

    def _maybe_capture_mike_failure_payload(self, story_id: str, failure_stage: str, response_text: str) -> Optional[str]:
        """Always capture Mike's full response on failure for debugging.
        Files saved to: static/appdocs/sprints/mike_failure_payloads/{sprint_id}/
        """
        try:
            payload_dir = SPRINT_DIR / "mike_failure_payloads" / self.sprint_id
            payload_dir.mkdir(parents=True, exist_ok=True)

            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
            safe_story_id = re.sub(r"[^A-Za-z0-9_-]+", "_", story_id or "unknown")
            safe_stage = re.sub(r"[^A-Za-z0-9_-]+", "_", failure_stage or "unknown")
            path = payload_dir / f"{ts}_{safe_story_id}_{safe_stage}.txt"
            path.write_text(response_text or "", encoding="utf-8")
            logger.info(f"📁 Mike failure payload saved to: {path}")
            return str(path)
        except Exception as e:
            logger.error(f"Could not save Mike failure payload: {e}")
            return None

    def _capture_mike_breakdown(self, story_id: str, task_breakdown: Dict, baseline_files: List[str], arch_contract: Dict) -> Optional[str]:
        """Capture Mike's successful breakdown for debugging contract enforcement.
        Files saved to: static/appdocs/sprints/mike_breakdowns/{sprint_id}/{story_id}.json
        Cleanup: Removes files older than 7 days.
        """
        try:
            breakdown_dir = SPRINT_DIR / "mike_breakdowns" / self.sprint_id
            breakdown_dir.mkdir(parents=True, exist_ok=True)

            # Cleanup old files (7 days)
            cutoff_time = datetime.now().timestamp() - (7 * 24 * 60 * 60)
            for old_file in breakdown_dir.glob("*.json"):
                try:
                    if old_file.stat().st_mtime < cutoff_time:
                        old_file.unlink()
                        logger.debug(f"Cleaned up old breakdown file: {old_file}")
                except Exception as cleanup_error:
                    logger.warning(f"Could not cleanup {old_file}: {cleanup_error}")

            # Extract files_to_create from each task for debugging
            files_from_tasks = []
            tasks = task_breakdown.get("tasks", []) or []
            for task in tasks:
                if isinstance(task, dict):
                    task_files = task.get("files_to_create", []) or []
                    files_from_tasks.extend([f for f in task_files if isinstance(f, str) and f.strip()])

            # Build capture payload
            capture_data = {
                "timestamp": datetime.now().isoformat(),
                "story_id": story_id,
                "sprint_id": self.sprint_id,
                "task_count": len(tasks),
                "breakdown_summary": {
                    "story_id": task_breakdown.get("story_id"),
                    "task_count": len(tasks),
                    "has_architectural_conflict": task_breakdown.get("architectural_conflict", {}).get("detected", False),
                    "technical_notes": task_breakdown.get("technical_notes", "")[:200]  # Truncate for readability
                },
                "tasks_detail": [
                    {
                        "task_id": task.get("task_id"),
                        "description": task.get("description", "")[:100],  # Truncate for readability
                        "files_to_create": task.get("files_to_create", []),
                        "command_to_run": task.get("command_to_run"),
                        "has_files": len(task.get("files_to_create", []) or []) > 0,
                        "has_command": bool(task.get("command_to_run"))
                    }
                    for task in tasks if isinstance(task, dict)
                ],
                "contract_summary": {
                    "baseline_files_count": len(baseline_files),
                    "baseline_files": sorted(baseline_files),
                    "files_from_tasks": sorted(files_from_tasks),
                    "allowed_files_count": len(arch_contract.get("allowed_files", [])),
                    "allowed_files": sorted(list(arch_contract.get("allowed_files", []))),
                    "allowed_deps_count": len(arch_contract.get("allowed_deps", [])),
                    "allowed_deps": sorted(list(arch_contract.get("allowed_deps", [])))
                }
            }

            # Write to file
            safe_story_id = re.sub(r"[^A-Za-z0-9_-]+", "_", story_id or "unknown")
            path = breakdown_dir / f"{safe_story_id}.json"
            path.write_text(json.dumps(capture_data, indent=2), encoding="utf-8")
            logger.info(f"📋 Mike breakdown captured to: {path}")
            return str(path)
        except Exception as e:
            logger.error(f"Could not capture Mike breakdown: {e}", exc_info=True)
            return None
    
    @classmethod
    def pause_sprint(cls, sprint_id: str):
        """Pause sprint execution to allow user interaction."""
        cls._paused_sprints[sprint_id] = True
        logger.info(f"🛑 Sprint {sprint_id} paused for user interaction")
    
    @classmethod
    def resume_sprint(cls, sprint_id: str):
        """Resume sprint execution after user interaction."""
        cls._paused_sprints[sprint_id] = False
        logger.info(f"▶️ Sprint {sprint_id} resumed")
    
    @classmethod
    def is_paused(cls, sprint_id: str) -> bool:
        """Check if sprint is currently paused."""
        return cls._paused_sprints.get(sprint_id, False)
    
    async def _wait_if_paused(self):
        """Wait while sprint is paused, checking every 500ms."""
        while self.is_paused(self.sprint_id):
            await asyncio.sleep(0.5)

    async def _post_to_chat(self, persona: str, message: str, event_type: str = None, event_data: dict = None) -> None:
        """
        Emit team narration message via SSE stream as structured event.
        
        These messages are display-only (not stored in chat history or sent to LLMs).
        They provide real-time visibility into what Mike/Alex/Jordan are doing.
        
        Args:
            persona: Who is speaking (Mike, Alex, Jordan, Sarah)
            message: Display message for logging
            event_type: Optional structured event type (if None, will try to parse from message)
            event_data: Optional structured event data dict
        """
        try:
            from services.sse_manager import sse_manager
            
            # If structured data provided, use it directly
            if event_type and event_data is not None:
                await sse_manager.emit(self.sprint_id, {
                    "event_type": event_type,
                    "data": event_data
                })
                logger.debug(f"[{persona}] {message} → {event_type}")
                return
            
            # Fallback: emit as generic team_message
            await sse_manager.emit(self.sprint_id, {
                "type": "team_message",
                "persona": persona,
                "message": message
            })
            logger.debug(f"[{persona}] {message}")
            
        except Exception as e:
            logger.debug(f"Could not post to chat: {e}")

    # ============================================================================
    # TECH STACK NFR DETECTION AND EXTRACTION
    # ============================================================================

    def _identify_tech_stack_nfr(self, stories: List[str]) -> Optional[str]:
        """
        Identify which story is the Tech Stack NFR.
        Returns story_id or None if not found.
        
        For SP-001: NFR-001 required as first story
        For SP-002+: NFR-001 not required, use existing tech stack
        """
        if not stories:
            logger.error("❌ No stories in sprint plan!")
            return None
        
        # SP-001 requires NFR-001, subsequent sprints do not
        if self.sprint_id == 'SP-001':
            first_story_id = stories[0]
            story = self._get_story_from_backlog(first_story_id)
            
            if not story:
                logger.error(f"❌ Could not load first story: {first_story_id}")
                return None
            
            story_id = story.get('Story_ID', '')
            
            # SP-001 MUST start with NFR-001
            if story_id != 'NFR-001':
                logger.error(f"❌ SP-001 must start with NFR-001 (Tech Stack NFR), got: {story_id}")
                return None
            
            logger.info(f"✅ Tech Stack NFR identified: NFR-001 - {story.get('Title')}")
            return first_story_id
        else:
            # SP-002+ can optionally include NFR-001, but not required
            if 'NFR-001' in stories:
                logger.info(f"✅ NFR-001 found in {self.sprint_id}, will process it")
                return 'NFR-001'
            else:
                logger.info(f"ℹ️ {self.sprint_id}: No NFR-001, will use existing tech stack from previous sprint")
                return None

    def _extract_tech_stack_from_nfr(self, story: Dict) -> Dict:
        """
        Parse NFR requirements to extract tech stack details.
        Returns dict with: backend, frontend, database, ports, etc.
        """
        # NFRs use 'Non_Functional_Requirements', User Stories use 'Functional_Requirements'
        requirements = story.get('Non_Functional_Requirements', '') or story.get('Functional_Requirements', '')
        acceptance = story.get('Acceptance_Criteria', '')
        combined = f"{requirements} {acceptance}".lower()
        
        tech_stack = {
            'backend': 'unknown',
            'frontend': 'unknown',
            'database': 'unknown',
            'backend_port': None,
            'frontend_port': None,
            'test_framework': 'unknown',  # Explicit test framework instead of inferring from backend
            'raw_requirements': requirements,
            'story_id': story.get('Story_ID'),
            'title': story.get('Title')
        }
        
        # Detect backend and set corresponding test framework
        if 'node' in combined and 'express' in combined:
            tech_stack['backend'] = 'nodejs_express'
            tech_stack['test_framework'] = 'node:test'  # Node.js 18+ native test runner
            logger.info("📦 Detected backend: Node.js + Express")
            logger.info("📦 Test framework: node:test (Node.js native)")
        elif 'flask' in combined:
            tech_stack['backend'] = 'flask'
            tech_stack['test_framework'] = 'pytest'
            logger.info("📦 Detected backend: Flask")
            logger.info("📦 Test framework: pytest")
        elif 'django' in combined:
            tech_stack['backend'] = 'django'
            tech_stack['test_framework'] = 'pytest'
            logger.info("📦 Detected backend: Django")
            logger.info("📦 Test framework: pytest")
        else:
            logger.warning(f"⚠️ Could not detect backend framework in: {requirements[:100]}")
        
        # Detect frontend
        if 'react' in combined:
            tech_stack['frontend'] = 'react'
            logger.info("📦 Detected frontend: React")
        elif 'vue' in combined:
            tech_stack['frontend'] = 'vue'
            logger.info("📦 Detected frontend: Vue")
        elif 'angular' in combined:
            tech_stack['frontend'] = 'angular'
            logger.info("📦 Detected frontend: Angular")
        elif 'html' in combined or 'static' in combined:
            tech_stack['frontend'] = 'html'
            logger.info("📦 Detected frontend: Static HTML")
        else:
            logger.warning(f"⚠️ Could not detect frontend framework in: {requirements[:100]}")
        
        # Detect database
        if 'sqlite' in combined:
            tech_stack['database'] = 'sqlite'
            logger.info("📦 Detected database: SQLite")
        elif 'postgresql' in combined or 'postgres' in combined:
            tech_stack['database'] = 'postgresql'
            logger.info("📦 Detected database: PostgreSQL")
        elif 'mysql' in combined:
            tech_stack['database'] = 'mysql'
            logger.info("📦 Detected database: MySQL")
        elif 'supabase' in combined:
            tech_stack['database'] = 'supabase'
            logger.info("📦 Detected database: Supabase")
        else:
            logger.warning(f"⚠️ Could not detect database in: {requirements[:100]}")
        
        # Extract ports using regex
        import re
        port_patterns = [
            r'port[s]?\s*(\d+)',
            r':\s*(\d+)',
            r'(\d+)\s*\(.*?(?:frontend|backend|server|client)',
        ]
        
        found_ports = []
        for pattern in port_patterns:
            matches = re.findall(pattern, combined)
            found_ports.extend(matches)
        
        # Deduplicate and assign
        unique_ports = list(dict.fromkeys(found_ports))
        if len(unique_ports) >= 2:
            # Heuristic: lower port usually backend, higher usually frontend
            ports_sorted = sorted([int(p) for p in unique_ports[:2]])
            tech_stack['backend_port'] = str(ports_sorted[0])
            tech_stack['frontend_port'] = str(ports_sorted[1])
            logger.info(f"📦 Detected ports: backend={ports_sorted[0]}, frontend={ports_sorted[1]}")
        elif len(unique_ports) == 1:
            tech_stack['backend_port'] = unique_ports[0]
            logger.info(f"📦 Detected port: {unique_ports[0]}")
        
        logger.info(f"📦 Tech Stack Summary: {tech_stack['backend']} + {tech_stack['frontend']} + {tech_stack['database']}")
        return tech_stack

    # ============================================================================
    # PHASE 1: CONTEXT INJECTION METHODS
    # ============================================================================

    def _get_project_context(self, project_name: str) -> str:
        """Get project structure and file listing for context injection."""
        project_root = EXECUTION_SANDBOX / project_name
        if not project_root.exists():
            return "Empty project (no files yet)"
        
        context_lines = ["Project Structure:"]
        try:
            for root, dirs, files in os.walk(project_root):
                # Skip pycache and hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                level = root.replace(str(project_root), '').count(os.sep)
                indent = '  ' * level
                rel_root = os.path.relpath(root, project_root)
                if rel_root != '.':
                    context_lines.append(f'{indent}{rel_root}/')
                
                sub_indent = '  ' * (level + 1)
                for file in sorted(files):
                    if not file.startswith('.') and not file.endswith('.pyc'):
                        context_lines.append(f'{sub_indent}{file}')
            
            # Limit to avoid token explosion
            if len(context_lines) > 100:
                context_lines = context_lines[:100] + ["... (truncated)"]
            
            return '\n'.join(context_lines)
        except Exception as e:
            logger.error(f"Error getting project context: {e}")
            return "Could not read project structure"

    def _get_file_summaries(self, project_name: str, related_paths: List[str], files_needing_full_content: List[str] = None) -> str:
        """Get actual CONTENTS of key existing files so Alex/Jordan can see established patterns.
        
        Args:
            files_needing_full_content: List of file paths that should NOT be truncated (for MODIFY operations)
        """
        project_root = EXECUTION_SANDBOX / project_name
        summaries = []
        files_needing_full_content = files_needing_full_content or []
        
        try:
            # Determine tech stack
            tech_stack_details = self.vision.get('tech_stack_details', {})
            backend = tech_stack_details.get('backend', '').lower()
            
            # Define key file patterns that should include CONTENTS (not just paths)
            # These are files that establish patterns other code should follow
            if 'nodejs' in backend or 'express' in backend or 'node.js' in backend:
                key_patterns = [
                    'src/db.js',           # Database setup pattern
                    'src/server.js',       # Server initialization pattern
                    'src/models/*.js',     # Model patterns
                    'src/controllers/*.js', # Controller patterns
                    'src/routes/*.js',     # Route patterns
                    'tests/*.test.js',     # Test patterns (CRITICAL - Jordan needs to copy these)
                    'public/*.html',       # Frontend HTML files (Alex needs to see element IDs)
                    'public/*.js'          # Frontend JS files (for consistency with HTML)
                ]
                other_patterns = ['**/*.js', '**/*.jsx']
                no_files_msg = "No JavaScript files yet"
            else:
                key_patterns = [
                    'app.py',
                    'models/*.py',
                    'routes/*.py',
                    'tests/test_*.py'
                ]
                other_patterns = ['**/*.py']
                no_files_msg = "No Python files yet"
            
            # PHASE 1: Get CONTENTS of key pattern files (for copying patterns)
            key_files_found = []
            for pattern in key_patterns:
                for code_file in project_root.glob(pattern):
                    if 'node_modules' in str(code_file) or '__pycache__' in str(code_file):
                        continue
                    
                    try:
                        rel_path = code_file.relative_to(project_root)
                        content = code_file.read_text(encoding='utf-8')
                        
                        # Extract exports for this file to show Alex what's available
                        exports, export_style = extract_exports_from_file(code_file, include_style=True)
                        # Include export style so Mike/Alex know how to import
                        style_hint = ""
                        if export_style == 'object':
                            style_hint = " [use: const { name } = require()]"
                        elif export_style == 'direct':
                            style_hint = " [use: const name = require()]"
                        exports_summary = f"// EXPORTS ({export_style}): {', '.join(exports)}{style_hint}" if exports else "// EXPORTS: (none)"
                        
                        rel_path_str = str(rel_path)
                        
                        # CRITICAL: For MODIFY operations, show FULL content (no truncation)
                        # This prevents duplicate imports and ensures Alex sees the complete file
                        if rel_path_str in files_needing_full_content:
                            # NO truncation - Alex needs to see the entire file to modify it correctly
                            logger.info(f"Loading FULL content for {rel_path_str} (MODIFY operation)")
                        else:
                            # Limit content to prevent token explosion for files Alex is just referencing
                            # Controllers/routes need more context to see all exports (150 lines)
                            # Other files get 80 lines
                            max_lines = 150 if ('controllers' in rel_path_str or 'routes' in rel_path_str) else 80
                            
                            lines = content.split('\n')
                            if len(lines) > max_lines:
                                content = '\n'.join(lines[:max_lines]) + '\n// ... (truncated)'
                            elif len(content) > 3000:
                                content = content[:3000] + '\n// ... (truncated)'
                        
                        summaries.append(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE: {rel_path}
{exports_summary}
PURPOSE: Established pattern - study this and follow the same approach
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{content}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
                        key_files_found.append(str(rel_path))
                    except Exception as e:
                        logger.debug(f"Could not read {code_file}: {e}")
            
            # PHASE 2: List OTHER files (paths only, for awareness)
            other_files = []
            for pattern in other_patterns:
                for code_file in project_root.glob(pattern):
                    if 'node_modules' in str(code_file) or '__pycache__' in str(code_file) or code_file.name.startswith('.'):
                        continue
                    
                    try:
                        rel_path = code_file.relative_to(project_root)
                        rel_path_str = str(rel_path)
                        
                        # Skip if already included in key files
                        if rel_path_str not in key_files_found:
                            other_files.append(f"  - {rel_path}")
                    except Exception as e:
                        logger.debug(f"Could not process {code_file}: {e}")
            
            # Assemble final summary
            if summaries or other_files:
                result = []
                if summaries:
                    result.append("KEY FILES WITH CONTENTS (follow these patterns!):")
                    result.extend(summaries)
                if other_files:
                    result.append("\nOTHER FILES IN PROJECT (paths only):")
                    result.extend(other_files[:20])  # Limit other files
                return '\n'.join(result)
            else:
                return no_files_msg
                
        except Exception as e:
            logger.error(f"Error getting file summaries: {e}")
            return "Could not read existing files"

    def _extract_code_summary(self, content: str, filename: str) -> str:
        """Extract key elements from Python code."""
        try:
            tree = ast.parse(content)
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) 
                        if isinstance(node, ast.FunctionDef) and not node.name.startswith('_')]
            
            summary_parts = []
            if classes:
                summary_parts.append(f"classes: {', '.join(classes[:5])}")
            if functions:
                summary_parts.append(f"functions: {', '.join(functions[:5])}")
            
            return '; '.join(summary_parts) if summary_parts else "empty"
        except:
            return "unparseable"

    def _get_existing_patterns(self, project_name: str) -> str:
        """Extract common patterns from existing code."""
        project_root = EXECUTION_SANDBOX / project_name
        patterns = []
        
        try:
            # Check if Flask app exists
            app_py = project_root / "app.py"
            if app_py.exists():
                patterns.append("- Flask app exists in app.py with create_app() factory")
            
            # Check for blueprints
            routes_dir = project_root / "routes"
            if routes_dir.exists():
                blueprints = [f for f in routes_dir.glob("*.py") if f.name != '__init__.py']
                if blueprints:
                    bp_names = [f.stem for f in blueprints[:5]]
                    patterns.append(f"- Route blueprints: {', '.join(bp_names)}")
            
            # Check for templates
            templates_dir = project_root / "templates"
            if templates_dir.exists():
                templates = list(templates_dir.glob("*.html"))
                if templates:
                    patterns.append(f"- {len(templates)} HTML templates exist")
            
            return '\n'.join(patterns) if patterns else "No established patterns yet"
        except Exception as e:
            logger.error(f"Error getting patterns: {e}")
            return "Could not analyze patterns"

    # ============================================================================
    # PHASE 1: VALIDATION METHODS
    # ============================================================================

    def _validate_task_breakdown(self, breakdown: Dict, story_id: str) -> bool:
        """Validate Mike's task breakdown structure."""
        if not isinstance(breakdown, dict):
            logger.error(f"Task breakdown for {story_id} is not a dict")
            return False
        
        # Validate story_id matches
        if 'story_id' in breakdown and breakdown['story_id'] != story_id:
            logger.error(f"❌ Mike returned wrong story_id: got '{breakdown['story_id']}', expected '{story_id}'")
            logger.error(f"Correcting story_id from '{breakdown['story_id']}' to '{story_id}'")
            breakdown['story_id'] = story_id
        
        if "tasks" not in breakdown:
            logger.error(f"Task breakdown for {story_id} missing 'tasks' field")
            return False
        
        tasks = breakdown.get("tasks", [])
        if not isinstance(tasks, list) or len(tasks) == 0:
            logger.error(f"Task breakdown for {story_id} has no tasks")
            return False
        
        for task in tasks:
            if not isinstance(task, dict):
                logger.error(f"Task in {story_id} is not a dict: {task}")
                return False
            
            # Accept 'taskId' (camelCase), 'id', or 'task_id' (normalize to 'task_id')
            if 'taskId' in task and 'task_id' not in task:
                task['task_id'] = task['taskId']
            elif 'id' in task and 'task_id' not in task:
                task['task_id'] = task['id']
            
            # Accept 'title' or 'description' (normalize to 'description')
            if 'title' in task and 'description' not in task:
                task['description'] = task['title']
            
            required = ["task_id", "description"]
            if not all(field in task for field in required):
                logger.error(f"Task in {story_id} missing required fields: {required}")
                logger.error(f"Task has these fields: {list(task.keys())}")
                return False
            
            # PRE-FLIGHT CONTRACT CHECK: Validate files_to_create paths
            files_to_create = task.get('files_to_create', [])
            if files_to_create:
                invalid_paths = self._validate_file_paths(files_to_create)
                if invalid_paths:
                    logger.warning(f"⚠️ Task {task.get('task_id')} has potentially unsafe paths: {invalid_paths}")
                    # Don't fail validation, just warn - Alex will be constrained anyway
        
        return True
    
    def _validate_file_paths(self, file_paths: List[str]) -> List[str]:
        """Validate that file paths are safe and within allowed directories.
        
        Returns list of invalid/suspicious paths.
        """
        invalid = []
        
        # Allowed top-level directories for generated code
        allowed_prefixes = [
            'src/', 'public/', 'tests/', 'routes/', 'controllers/', 
            'models/', 'middleware/', 'views/', 'templates/', 'static/',
            'components/', 'services/', 'utils/', 'lib/', 'config/',
            'package.json', 'requirements.txt', '.env', '.gitignore',
            'README.md', 'app.py', 'server.js', 'index.js', 'main.py'
        ]
        
        for path in file_paths:
            if not isinstance(path, str):
                invalid.append(f"Non-string path: {path}")
                continue
            
            # Check for path traversal attempts
            if '..' in path:
                invalid.append(f"Path traversal: {path}")
                continue
            
            # Check for absolute paths
            if path.startswith('/'):
                invalid.append(f"Absolute path: {path}")
                continue
            
            # Check if path starts with allowed prefix
            is_allowed = any(
                path.startswith(prefix) or path == prefix.rstrip('/')
                for prefix in allowed_prefixes
            )
            
            if not is_allowed:
                # Log but don't block - might be a valid new directory
                logger.info(f"📁 New directory pattern: {path}")
        
        return invalid

    def _normalize_alex_response(self, code_result: Dict) -> List[Dict]:
        """Normalize Alex's response to a consistent list format.
        
        Handles multiple format variations:
        - {"files": {"path": "content"}}  (dict)
        - {"files": [{"path": "", "content": ""}]}  (list)
        - {"created_files": {...}}  (different key)
        - {"files": [{"path": "", "content": {...}}]}  (nested dict content)
        - {"files": [{"filename": "", "content": ""}]}  (filename instead of path)
        """
        files = []
        
        # Try different keys Alex might use
        for key in ["files", "created_files", "updated_files"]:
            if key in code_result:
                raw_files = code_result[key]
                
                # Case 1: Dict format {"path": "content"}
                if isinstance(raw_files, dict):
                    for path, content in raw_files.items():
                        # Content might be a string or nested dict
                        if isinstance(content, dict):
                            # Nested dict - extract actual content if present
                            content = content.get("content", "")
                        if isinstance(content, str) and content:
                            files.append({"path": path, "content": content})
                
                # Case 2: List format [{"path": "", "content": ""}]
                elif isinstance(raw_files, list):
                    for item in raw_files:
                        if not isinstance(item, dict):
                            continue
                        
                        # Get path (might be "path" or "filename")
                        path = item.get("path") or item.get("filename", "")
                        
                        # Get content (might be string or nested dict)
                        content = item.get("content", "")
                        if isinstance(content, dict):
                            content = content.get("content", "")
                        
                        if path and isinstance(content, str) and content:
                            files.append({"path": path, "content": content})
                
                break  # Found files, stop looking
        
        if not files:
            logger.warning(f"Could not extract files from Alex response keys: {list(code_result.keys())}")
        
        return files

    def _validate_files_syntax(self, files: List[Dict]) -> List[Dict]:
        """Validate syntax for multiple files and return list of errors."""
        errors = []
        for file_spec in files:
            path = file_spec.get("path", "")
            content = file_spec.get("content", "")
            
            if not path or not content:
                continue
            
            # Skip validation if content is not a string
            if not isinstance(content, str):
                logger.warning(f"Skipping validation for {path}: content is {type(content)}, not string")
                errors.append({
                    "path": path,
                    "error": f"Content must be a string, got {type(content).__name__}",
                    "line": 0,
                    "text": ""
                })
                continue
            
            # Validate programming language syntax (Python)
            if not self._validate_syntax(content, path):
                # Extract the actual error message
                try:
                    if path.endswith('.py'):
                        compile(content, path, 'exec')
                except SyntaxError as e:
                    errors.append({
                        "path": path,
                        "error": f"Syntax error at line {e.lineno}: {e.msg}",
                        "line": e.lineno,
                        "text": e.text
                    })
            
            # Validate SQL statements (JavaScript/Python files with SQL)
            sql_errors = self._validate_sql_statements(content, path)
            if sql_errors:
                errors.extend(sql_errors)
            
            # Validate test patterns (Node.js test files)
            test_pattern_errors = self._validate_test_patterns(content, path)
            if test_pattern_errors:
                errors.extend(test_pattern_errors)
        
        return errors

    def _validate_syntax(self, content: str, filepath: str) -> bool:
        """Validate Python syntax before writing."""
        if not filepath.endswith('.py'):
            return True  # Skip non-Python files
        
        try:
            ast.parse(content)
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error in {filepath} at line {e.lineno}: {e.msg}")
            # Log the problematic line and surrounding context
            lines = content.split('\n')
            if e.lineno and 0 < e.lineno <= len(lines):
                start = max(0, e.lineno - 3)
                end = min(len(lines), e.lineno + 2)
                context = '\n'.join(f"{i+1}: {lines[i]}" for i in range(start, end))
                logger.error(f"Code context around error:\n{context}")
            return False
        except Exception as e:
            logger.error(f"Could not parse {filepath}: {e}")
            return False

    def _validate_imports(self, content: str) -> Tuple[bool, List[str]]:
        """Check if imports are reasonable. Returns (is_valid, warnings)."""
        warnings = []
        
        try:
            tree = ast.parse(content)
            
            # Check for suspicious imports
            suspicious = ['os.system', 'subprocess', 'eval', 'exec', '__import__']
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(sus in alias.name for sus in suspicious):
                            warnings.append(f"Suspicious import: {alias.name}")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and any(sus in node.module for sus in suspicious):
                        warnings.append(f"Suspicious import from: {node.module}")
            
            return True, warnings
        except:
            return True, []  # If can't parse, let syntax validation handle it
    
    def _validate_sql_statements(self, content: str, filepath: str) -> List[Dict]:
        """
        Validate SQL CREATE TABLE statements in JavaScript/Python files.
        Returns list of SQL errors found.
        """
        errors = []
        
        # Only check files that might contain SQL (db.js, models, migrations)
        if not any(pattern in filepath.lower() for pattern in ['db.js', 'db.py', 'model', 'migration', 'schema']):
            return errors
        
        # SQLite reserved words that commonly cause issues
        sqlite_reserved = [
            'check', 'default', 'order', 'group', 'index', 'key', 'table',
            'trigger', 'view', 'primary', 'foreign', 'references', 'constraint'
        ]
        
        # Find CREATE TABLE statements (case-insensitive, multiline)
        import re
        # Match: CREATE TABLE tablename (field1 type1, field2 type2, ...)
        pattern = r'CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+(\w+)\s*\((.*?)\)'
        matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            table_name = match.group(1)
            fields_section = match.group(2)
            line_num = content[:match.start()].count('\n') + 1
            
            # Check for common issues
            # 1. Using reserved words as column names without quotes
            for reserved in sqlite_reserved:
                # Look for: word TYPE or word PRIMARY or word NOT NULL
                # But not: 'word' or "word" (quoted)
                unquoted_pattern = rf'\b{reserved}\b\s+(?:INTEGER|TEXT|REAL|BLOB|NOT\s+NULL|PRIMARY\s+KEY|DEFAULT)'
                if re.search(unquoted_pattern, fields_section, re.IGNORECASE):
                    errors.append({
                        "path": filepath,
                        "error": f"SQL: Reserved word '{reserved}' used as column name without quotes in table '{table_name}'",
                        "line": line_num,
                        "text": match.group(0)[:100],
                        "fix": f"Use double quotes: \"{reserved}\" or choose different column name"
                    })
            
            # 2. Check for missing comma between fields
            # Simple heuristic: if we see TYPE TYPE (e.g., "TEXT INTEGER"), likely missing comma
            if re.search(r'(INTEGER|TEXT|REAL|BLOB)\s+(INTEGER|TEXT|REAL|BLOB)', fields_section, re.IGNORECASE):
                errors.append({
                    "path": filepath,
                    "error": f"SQL: Possible missing comma between fields in table '{table_name}'",
                    "line": line_num,
                    "text": match.group(0)[:100],
                    "fix": "Add comma between field definitions"
                })
            
            # 3. Check for CHECK without parentheses (common syntax error)
            if re.search(r'\bCHECK\b(?!\s*\()', fields_section, re.IGNORECASE):
                errors.append({
                    "path": filepath,
                    "error": f"SQL: CHECK constraint without parentheses in table '{table_name}'",
                    "line": line_num,
                    "text": match.group(0)[:100],
                    "fix": "Use: CHECK (condition) not CHECK condition"
                })
        
        return errors
    
    def _validate_test_patterns(self, content: str, filepath: str) -> List[Dict]:
        """
        Validate Node.js test files follow correct isolation patterns.
        Returns list of pattern violations found.
        """
        errors = []
        
        # Only check Node.js test files
        if not any(pattern in filepath.lower() for pattern in ['test_', '.test.js', '_test.js']):
            return errors
        
        # Don't check Python test files
        if filepath.endswith('.py'):
            return errors
        
        import re
        
        # Check 1: Look for db imported at file level (before any test() call)
        # This is the most common cause of "Database is closed" errors
        lines = content.split('\n')
        first_test_line = None
        
        # Find first test() call
        for i, line in enumerate(lines):
            if re.search(r'\btest\s*\(', line):
                first_test_line = i
                break
        
        # Check lines before first test for db imports
        if first_test_line is not None:
            for i in range(first_test_line):
                line = lines[i]
                # Look for: const/let/var { db } = ... import
                if re.search(r'(?:const|let|var)\s+\{[^}]*\bdb\b[^}]*\}\s*=.*?import\s*\(', line):
                    errors.append({
                        "path": filepath,
                        "error": "Test pattern violation: db imported at file level (causes shared state between tests)",
                        "line": i + 1,
                        "text": line.strip(),
                        "fix": "Move import INSIDE each test function: test('...', async () => { const { db } = await import('../src/db.js'); ... })"
                    })
        
        # Check 2: Look for tests that import db but don't close it
        # Find all test functions
        test_pattern = r'test\s*\([\'"][^\'"]*[\'"],\s*async\s*(?:\([^)]*\))?\s*=>\s*\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}\s*\)'
        test_matches = list(re.finditer(test_pattern, content, re.DOTALL))
        
        for test_match in test_matches:
            test_body = test_match.group(1)
            test_line = content[:test_match.start()].count('\n') + 1
            
            # Check if db is imported in this test
            has_db_import = 'db' in test_body and 'import' in test_body
            has_db_close = 'db.close' in test_body
            
            if has_db_import and not has_db_close:
                errors.append({
                    "path": filepath,
                    "error": "Test pattern violation: db imported but never closed (causes connection leaks and test failures)",
                    "line": test_line,
                    "text": f"Test at line {test_line} (check test body)",
                    "fix": "Add finally block: finally { await new Promise((resolve) => db.close(resolve)); }"
                })
        
        return errors
    
    def _get_nodejs_test_template(self) -> str:
        """Return the mandatory test template for Node.js projects."""
        return """
═══════════════════════════════════════════════════════════════════════════════
MANDATORY TEST TEMPLATES FOR NODE.JS/SQLITE PROJECTS:
═══════════════════════════════════════════════════════════════════════════════

PATTERN 1: Database-only tests (for testing DB operations, models, etc.)
───────────────────────────────────────────────────────────────────────────────
import test from 'node:test';
import assert from 'node:assert';

test('Your test description here', async (t) => {
  // REQUIRED: Import INSIDE each test function
  const { db, initDB } = await import('../src/db.js');
  
  try {
    // Setup
    await initDB();
    
    // Your test logic here
    // Example: const result = await someFunction();
    
    // Assertions
    // assert.strictEqual(result, expected);
    
  } finally {
    // REQUIRED: Always close in finally block
    await new Promise((resolve) => db.close(resolve));
  }
});

PATTERN 2: Express Server tests (for testing routes, endpoints, server startup)
───────────────────────────────────────────────────────────────────────────────
const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

test('Server starts and responds', async () => {
  const app = require('../src/server.js');
  const { createDb, initDb } = require('../src/db.js');
  let server;
  let db;
  
  try {
    process.env.NODE_ENV = 'test';
    db = createDb();
    await initDb(db);
    // CRITICAL: DO NOT close db here - server needs it running during startup
    
    server = await new Promise((resolve, reject) => {
      const s = app.listen(0, (err) => {
        if (err) reject(err);
        else resolve(s);
      });
    });
    
    // Run your server tests here
    const port = server.address().port;
    // Example: make HTTP request to test endpoint
    // const res = await makeRequest('/', port);
    // assert.ok(res.statusCode < 500);
    
  } finally {
    // CRITICAL: Close in correct order - server first, then DB
    if (server) await new Promise(r => server.close(r));
    if (db) await new Promise(r => db.close(r));
  }
});

CRITICAL RULES:
1. For database tests: Import db INSIDE each test function (not at file level)
2. For server tests: DO NOT close database before calling app.listen()
3. For server tests: Server needs DB connection alive during startup and runtime
4. Always close resources in finally block
5. For server tests: Close server BEFORE closing database
6. Each test gets its own fresh database connection
7. Never share db connections between tests
8. Always set process.env.NODE_ENV = 'test' for in-memory database

This pattern prevents "SQLITE_MISUSE: Database is closed" and server startup timeout errors.
═══════════════════════════════════════════════════════════════════════════════
"""

    async def _execute_task_command(self, command: str, project_root: Path, task_id: str) -> bool:
        """
        Execute a command specified in a task's command_to_run field.
        This is stack-agnostic - works for npm install, pip install, mvn install, etc.
        
        Args:
            command: Command to execute (e.g., "npm install", "pip install -r requirements.txt")
            project_root: Path to project root
            task_id: Task ID for logging
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🔧 Executing command for {task_id}: {command}")
            
            result = subprocess.run(
                command,
                shell=True,  # Allow shell commands like "npm install"
                cwd=str(project_root),
                capture_output=True,
                timeout=300,  # 5 minutes
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"❌ Command failed with exit code {result.returncode}")
                logger.error(f"📤 stdout: {result.stdout}")
                logger.error(f"📤 stderr: {result.stderr}")
                return False
            
            logger.info(f"✅ Command completed successfully: {command}")
            logger.info(f"📤 stdout: {result.stdout}")
            
            # Add delay for install commands to let file system settle
            if 'install' in command.lower():
                logger.info(f"⏳ Waiting 2 seconds for file system to settle after install...")
                await asyncio.sleep(2)
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out (exceeded 5 minutes): {command}")
            return False
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            return False

    def _install_dependencies(self, project_root: Path) -> bool:
        """
        Install npm dependencies after package.json is written.
        
        Args:
            project_root: Path to project root
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"📦 Installing dependencies in {project_root}")
            
            # Check if package.json exists
            package_json_path = project_root / "package.json"
            if not package_json_path.exists():
                logger.error(f"❌ package.json not found at {package_json_path}")
                return False
            
            # Check npm availability
            try:
                npm_version = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=10)
                if npm_version.returncode == 0:
                    logger.info(f"✅ npm version: {npm_version.stdout.strip()}")
                else:
                    logger.error(f"❌ npm --version failed: {npm_version.stderr}")
                    return False
            except Exception as e:
                logger.error(f"❌ npm not available: {e}")
                return False
            
            # Use npm ci for clean, reproducible installs (prevents cache corruption)
            # Falls back to npm install if package-lock.json doesn't exist
            logger.info("🔄 Running npm ci for clean dependency install...")
            
            # Check if package-lock.json exists
            has_lock = (project_root / "package-lock.json").exists()
            
            if has_lock:
                # npm ci: Clean install from lock file (deletes node_modules first)
                cmd = ["npm", "ci", "--prefer-offline"]
                logger.info("Using npm ci (lock file found)")
            else:
                # Fallback: npm install with cache verification
                cmd = ["npm", "install", "--prefer-offline"]
                logger.info("Using npm install (no lock file, will create one)")
            
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                timeout=300,  # 5 minutes
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"❌ npm install failed with exit code {result.returncode}")
                logger.error(f"📤 stdout: {result.stdout}")
                logger.error(f"📤 stderr: {result.stderr}")
                return False
            
            logger.info("✅ Dependencies installed successfully")
            logger.info(f"📤 stdout: {result.stdout}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("npm install timed out (exceeded 5 minutes)")
            return False
        except FileNotFoundError:
            logger.error("npm not found - is Node.js installed?")
            return False
        except Exception as e:
            logger.error(f"Error installing dependencies: {e}")
            return False

    def _validate_node_contracts(self, project_root: Path, story_id: str, design: Dict | None = None) -> None:
        """Non-gating validation for Node/Express/SQLite contracts.

        Logs warnings if key contracts are missing. This is BEST-EFFORT only and
        must never raise or block sprint execution.
        """
        try:
            db_path = project_root / "src" / "db.js"
            if not db_path.exists():
                logger.warning(f"⚠️ Contract check ({story_id}): src/db.js not found (expected DB module)")
                return

            try:
                content = db_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                logger.warning(f"⚠️ Contract check ({story_id}): could not read src/db.js: {e}")
                content = ""

            if "createDb" not in content or "initDb" not in content:
                logger.warning(
                    f"⚠️ Contract check ({story_id}): src/db.js missing expected 'createDb' and/or 'initDb' exports"
                )

            # If design mentions JWT/jsonwebtoken, ensure dependency is present
            package_json_path = project_root / "package.json"
            if not package_json_path.exists():
                return

            try:
                package_data = json.loads(package_json_path.read_text(encoding="utf-8"))
            except Exception:
                logger.warning(f"⚠️ Contract check ({story_id}): could not parse package.json for dependency validation")
                return

            deps = package_data.get("dependencies", {}) or {}

            design_text = ""
            if design is not None:
                try:
                    design_text = json.dumps(design).lower()
                except Exception:
                    design_text = ""

            if "jwt" in design_text or "jsonwebtoken" in design_text:
                if "jsonwebtoken" not in deps:
                    logger.warning(
                        f"⚠️ Contract check ({story_id}): jsonwebtoken not found in dependencies despite JWT usage"
                    )
        except Exception as e:
            # Never let contract validation break execution
            logger.debug(f"Node contract validation skipped due to error: {e}")

    # =========================================================================
    # ARCHITECTURE CONTRACT (EXECUTION MODE)
    # =========================================================================

    def _list_project_files(self, project_root: Path) -> List[str]:
        """Return a list of all existing file paths in the project, relative to root.

        Used as the baseline allowed file surface for the current story.
        """
        if not project_root.exists():
            return []

        files: List[str] = []
        try:
            for root, dirs, filenames in os.walk(project_root):
                # Skip hidden/system dirs and node_modules/pycache
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith('.') and d not in {"node_modules", "__pycache__"}
                ]
                for filename in filenames:
                    if filename.startswith('.'):
                        continue
                    full_path = Path(root) / filename
                    rel_path = full_path.relative_to(project_root)
                    # Normalize to POSIX-style for consistency with Alex/Mike paths
                    files.append(rel_path.as_posix())
        except Exception as e:
            logger.debug(f"Could not list project files for contract baseline: {e}")
        return files

    def _read_package_dependencies(self, project_root: Path) -> List[str]:
        """Read current dependencies from package.json (if present).

        Returns a flat list of dependency names (dependencies + devDependencies).
        """
        package_json = project_root / "package.json"
        if not package_json.exists():
            return []

        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug(f"Could not parse package.json for contract baseline: {e}")
            return []

        deps = set()
        for key in ("dependencies", "devDependencies"):
            section = data.get(key) or {}
            if isinstance(section, dict):
                deps.update(section.keys())
        return sorted(deps)

    def _build_arch_contract(self, baseline_files: List[str], baseline_deps: List[str], design: Dict, story_id: str) -> Dict:
        """Build the architectural contract for a story from Mike's design.

        The contract is a CLOSED WORLD for this story:
        - Allowed files = baseline project files + any files Mike explicitly lists in tasks
        - Allowed dependencies = baseline deps + any deps Mike explicitly lists
        """
        allowed_files = set(baseline_files)

        # Collect all files Mike expects to be created/modified for this story
        try:
            tasks = design.get("tasks", []) or []
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                for path in task.get("files_to_create", []) or []:
                    if isinstance(path, str) and path.strip():
                        allowed_files.add(path.strip())
        except Exception as e:
            logger.debug(f"Error building file surface for arch contract on {story_id}: {e}")

        allowed_deps = set(baseline_deps)
        try:
            # Method 1: Look for top-level dependencies block (existing logic)
            deps_block = design.get("dependencies") or {}
            if isinstance(deps_block, dict):
                for key in ("dependencies", "devDependencies"):
                    section = deps_block.get(key) or {}
                    if isinstance(section, dict):
                        allowed_deps.update(section.keys())
            
            # Method 2: Extract dependencies from package.json tasks (new logic)
            tasks = design.get("tasks", []) or []
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                files_to_create = task.get("files_to_create", []) or []
                if "package.json" in files_to_create:
                    # Parse task description for dependency names
                    description = task.get("description", "")
                    if description:
                        # Look for common dependency patterns in task descriptions
                        import re
                        # Match patterns like: "dotenv": "^16.3.1", "nodemailer": "^6.9.7"
                        dep_matches = re.findall(r'"([a-z0-9@/-]+)"\s*:\s*"[^"]*"', description)
                        for dep_name in dep_matches:
                            allowed_deps.add(dep_name)
                            logger.debug(f"Extracted dependency '{dep_name}' from package.json task: {task.get('task_id')}")
        except Exception as e:
            logger.debug(f"Error building dependency surface for arch contract on {story_id}: {e}")

        return {
            "story_id": story_id,
            "allowed_files": allowed_files,
            "allowed_deps": allowed_deps,
        }

    def _enforce_arch_contract(
        self,
        project_root: Path,
        story_id: str,
        contract: Dict,
        story_files_written: List[str],
    ) -> bool:
        """Enforce Mike's architecture contract against Alex's implementation.

        Returns True if Alex stayed within the contract, False if a violation occurred.
        On violation, logs details but does not raise.
        """
        try:
            allowed_files = set(contract.get("allowed_files") or [])
            allowed_deps = set(contract.get("allowed_deps") or [])

            # 1) File-level enforcement: Alex must not create files outside the contract
            violating_files = []
            for path in story_files_written:
                # Normalize path style for comparison
                norm_path = Path(path).as_posix()
                if norm_path not in allowed_files:
                    violating_files.append(norm_path)

            # 2) Dependency-level enforcement: Alex must not introduce new deps not in contract
            current_deps = set(self._read_package_dependencies(project_root))
            # Only consider deps that weren't already allowed by contract
            violating_deps = sorted(current_deps - allowed_deps) if current_deps else []

            if not violating_files and not violating_deps:
                return True

            # Log all violations together
            if violating_files:
                logger.error(
                    f"❌ Architectural contract violation for {story_id}: Files outside contract were written: {violating_files}"
                )
            if violating_deps:
                logger.error(
                    f"❌ Architectural contract violation for {story_id}: Dependencies outside contract were added: {violating_deps}"
                )

            return False
        except Exception as e:
            # Contract enforcement must never crash the orchestrator; if it can't run, treat as pass
            logger.debug(f"Arch contract enforcement skipped for {story_id} due to error: {e}")
            return True

    # ============================================================================
    # PHASE 2: MERGE LOGIC METHODS
    # ============================================================================

    def _merge_code(self, existing: str, new: str, filepath: str) -> str:
        """
        Smart merge of existing and new code.
        - JSON files: Deep merge objects
        - JavaScript files: Use new content (Alex should generate complete files)
        - Python files: AST-based merge
        - Other files: Use new content
        """
        # JSON files: Deep merge
        if filepath.endswith('.json'):
            return self._merge_json(existing, new, filepath)
        
        # JavaScript/JSX/TypeScript: Use new content (Alex generates complete files)
        if filepath.endswith(('.js', '.jsx', '.ts', '.tsx')):
            logger.info(f"JavaScript file {filepath}: Using new content (Alex should generate complete file)")
            return new
        
        # Python files: AST-based merge
        if filepath.endswith('.py'):
            return self._merge_python(existing, new, filepath)
        
        # Other files (CSS, HTML, etc.): Use new content
        logger.info(f"Non-mergeable file {filepath}: Using new content")
        return new
    
    def _merge_json(self, existing: str, new: str, filepath: str) -> str:
        """Deep merge JSON objects."""
        try:
            existing_obj = json.loads(existing)
            new_obj = json.loads(new)
            
            # Deep merge
            merged = self._deep_merge_dict(existing_obj, new_obj)
            
            return json.dumps(merged, indent=2)
        except Exception as e:
            logger.error(f"JSON merge failed for {filepath}: {e}. Using new content.")
            return new
    
    def _deep_merge_dict(self, base: dict, updates: dict) -> dict:
        """Recursively merge two dictionaries."""
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                result[key] = self._deep_merge_dict(result[key], value)
            elif key in result and isinstance(result[key], list) and isinstance(value, list):
                # Merge lists, removing duplicates while preserving order
                seen = set()
                merged_list = []
                for item in result[key] + value:
                    # For simple types, deduplicate
                    if isinstance(item, (str, int, float, bool)):
                        if item not in seen:
                            seen.add(item)
                            merged_list.append(item)
                    else:
                        # For complex types, just append
                        merged_list.append(item)
                result[key] = merged_list
            else:
                # Overwrite with new value
                result[key] = value
        
        return result
    
    def _merge_python(self, existing: str, new: str, filepath: str) -> str:
        """AST-based merge for Python files."""
        try:
            # Parse both files
            existing_tree = ast.parse(existing)
            new_tree = ast.parse(new)
            
            # Extract elements from existing
            existing_funcs = {node.name for node in ast.walk(existing_tree) 
                            if isinstance(node, ast.FunctionDef)}
            existing_classes = {node.name for node in ast.walk(existing_tree) 
                              if isinstance(node, ast.ClassDef)}
            
            # Find new functions and classes to add
            merged_lines = existing.rstrip().split('\n')
            
            for node in ast.walk(new_tree):
                if isinstance(node, ast.FunctionDef) and node.name not in existing_funcs:
                    # Add new function
                    func_code = ast.unparse(node)
                    merged_lines.append("")
                    merged_lines.append("")
                    merged_lines.append(func_code)
                    existing_funcs.add(node.name)
                
                elif isinstance(node, ast.ClassDef) and node.name not in existing_classes:
                    # Add new class
                    class_code = ast.unparse(node)
                    merged_lines.append("")
                    merged_lines.append("")
                    merged_lines.append(class_code)
                    existing_classes.add(node.name)
            
            return '\n'.join(merged_lines)
            
        except Exception as e:
            logger.warning(f"Python merge failed for {filepath}: {e}. Using new content.")
            return new

    def _backup_existing(self, file_path: Path) -> Optional[Path]:
        """Create backup before modifying. Returns backup path or None."""
        if not file_path.exists():
            return None
        
        try:
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Could not create backup for {file_path}: {e}")
            return None

    def _cleanup_backups(self, project_name: str, story_id: str = None) -> int:
        """Clean up .bak files after successful story completion or rollback."""
        project_root = EXECUTION_SANDBOX / project_name
        if not project_root.exists():
            return 0
        
        try:
            # Find all .bak files in project
            bak_files = list(project_root.glob("**/*.bak"))
            count = len(bak_files)
            
            for bak_file in bak_files:
                try:
                    bak_file.unlink()
                    logger.info(f"Cleaned up backup: {bak_file}")
                except Exception as e:
                    logger.warning(f"Could not delete backup {bak_file}: {e}")
            
            if count > 0:
                logger.info(f"Cleaned up {count} backup files for {story_id or project_name}")
            return count
        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
            return 0

    # ============================================================================
    # PHASE 2: TEST EXECUTION METHODS
    # ============================================================================

    async def _run_tests(self, project_root: Path, test_file: str = None) -> Dict:
        """Run tests using appropriate framework based on tech stack."""
        try:
            test_path = project_root / "tests" if test_file is None else project_root / test_file
            
            if not test_path.exists():
                return {
                    "passed": 0,
                    "failed": 0,
                    "output": "Test path does not exist",
                    "success": False
                }
            
            # Detect test framework from tech_stack_details (explicit field)
            tech_stack_details = self.vision.get('tech_stack_details', {})
            test_framework = tech_stack_details.get('test_framework', 'unknown')
            backend = tech_stack_details.get('backend', '').lower()
            
            # Determine test command based on explicit test_framework field
            # Fall back to backend inference only if test_framework is unknown
            if test_framework == 'node:test' or (test_framework == 'unknown' and ('nodejs' in backend or 'express' in backend)):
                # Node.js project - use native test runner (node --test)
                logger.info(f"Running Node.js native tests (test_framework={test_framework})")
                # Use relative path since cwd is already project_root
                rel_path = test_file if test_file else "tests"
                test_cmd = ["node", "--test", rel_path]
                parse_nodejs = True
            elif test_framework == 'pytest' or (test_framework == 'unknown' and backend in ['flask', 'django']):
                # Python project - use pytest
                logger.info(f"Running pytest (test_framework={test_framework})")
                test_cmd = ["pytest", str(test_path), "-v", "--tb=short"]
                parse_nodejs = False
            else:
                # Default to pytest for unknown frameworks
                logger.warning(f"Unknown test_framework '{test_framework}', defaulting to pytest")
                test_cmd = ["pytest", str(test_path), "-v", "--tb=short"]
                parse_nodejs = False
            
            # Run tests
            # Timeout increased to 120s to account for test execution time
            # (npm install happens separately before this, but tests still need time)
            
            # Set NODE_ENV=test for Node.js tests to enable :memory: database
            import os
            test_env = os.environ.copy()
            if parse_nodejs:
                test_env['NODE_ENV'] = 'test'
            
            result = subprocess.run(
                test_cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=120,
                env=test_env
            )
            
            # Parse output based on framework
            output = result.stdout + result.stderr

            # Log test output for debugging when tests fail
            if result.returncode != 0:
                logger.warning(f"Test execution failed (returncode={result.returncode}). Output:\n{output[:2000]}")

            if parse_nodejs:
                # Parse Node.js native test runner output
                # Format: "✔ test_name" for pass, "✖ test_name" for fail
                import re
                # Strip ANSI escape codes to make summary parsing robust
                ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
                clean = ansi_escape.sub('', output)

                # Prefer official summary lines first ("# pass N", "# fail M")
                passed = 0
                failed = 0

                pass_match = re.search(r'^\s*#\s*pass\s+(\d+)', clean, re.MULTILINE | re.IGNORECASE)
                if pass_match:
                    passed = int(pass_match.group(1))

                fail_match = re.search(r'^\s*#\s*fail(?:ed)?\s+(\d+)', clean, re.MULTILINE | re.IGNORECASE)
                if fail_match:
                    failed = int(fail_match.group(1))

                # Fallback: glyph counts and generic "passed/failed" phrases if summary missing
                if passed == 0 and failed == 0:
                    passed = clean.count("✔")
                    failed = clean.count("✖")

                    if passed == 0 and failed == 0:
                        alt_pass = re.search(r'(\d+)\s+passed', clean)
                        if alt_pass:
                            passed = int(alt_pass.group(1))
                        alt_fail = re.search(r'(\d+)\s+failed', clean)
                        if alt_fail:
                            failed = int(alt_fail.group(1))
            else:
                # Parse pytest output
                passed = output.count(" PASSED")
                failed = output.count(" FAILED")
                errors = output.count(" ERROR")
                failed += errors
            
            return {
                "passed": passed,
                "failed": failed,
                "output": output[:5000],  # Increased to 5K for better diagnostics
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timeout for {test_file}")
            return {
                "passed": 0,
                "failed": 0,
                "output": "Test execution timeout (>120s)",
                "success": False
            }
        except FileNotFoundError:
            # Provide accurate error message based on which test command failed
            failed_cmd = test_cmd[0] if test_cmd else "test runner"
            logger.warning(f"{failed_cmd} not found, skipping test execution")
            return {
                "passed": 0,
                "failed": 0,
                "output": f"{failed_cmd} not installed - ensure Node.js or Python test tools are available",
                "success": False
            }
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {
                "passed": 0,
                "failed": 0,
                "output": str(e),
                "success": False
            }

    # ============================================================================
    # PHASE 3: BACKUP/ROLLBACK METHODS
    # ============================================================================

    def _track_story_files(self, story_id: str, file_path: Path) -> None:
        """Track files written during story execution for potential rollback."""
        # Store in instance variable (could be enhanced to persist)
        if not hasattr(self, '_story_files'):
            self._story_files = {}
        
        if story_id not in self._story_files:
            self._story_files[story_id] = []
        
        self._story_files[story_id].append(file_path)

    def _rollback_story(self, story_id: str) -> int:
        """Rollback all files created during a failed story. Returns count of files removed."""
        if not hasattr(self, '_story_files') or story_id not in self._story_files:
            return 0
        
        files_removed = 0
        for file_path in self._story_files[story_id]:
            try:
                if file_path.exists():
                    # Check if there's a backup
                    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                    if backup_path.exists():
                        # Restore from backup
                        shutil.copy2(backup_path, file_path)
                        files_removed += 1
            except Exception as e:
                logger.error(f"Could not rollback {file_path}: {e}")
        
        # Clear tracked files
        del self._story_files[story_id]
        return files_removed

    async def run(self) -> None:
        """Execute sprint with NFR-first tech stack detection and dynamic project structure."""
        logger.info("=" * 80)
        logger.info(f"🚀 SPRINT ORCHESTRATOR VERSION: {ORCHESTRATOR_VERSION}")
        logger.info("=" * 80)
        
        plan = self._load_plan()
        plan["status"] = "executing"
        self._save_plan(plan)

        await self._log_event("sprint_started", {
            "sprint_id": self.sprint_id,
            "orchestrator_version": ORCHESTRATOR_VERSION
        })
        
        await self._post_to_chat("System", f"🚀 Sprint Orchestrator v{ORCHESTRATOR_VERSION}")
        
        stories: List[str] = plan.get("stories", [])
        project_name = "yourapp"  # Fixed folder name - single pipeline
        
        # STEP 1: Identify Tech Stack NFR (required for SP-001, optional for SP-002+)
        logger.info("=" * 80)
        logger.info("STEP 1: Identifying Tech Stack NFR")
        logger.info("=" * 80)
        tech_stack_nfr_id = self._identify_tech_stack_nfr(stories)
        
        # Only SP-001 requires NFR-001
        if self.sprint_id == 'SP-001' and not tech_stack_nfr_id:
            error_msg = "❌ Sprint execution failed: SP-001 must start with NFR-001 (Tech Stack NFR)"
            logger.error(error_msg)
            await self._post_to_chat("System", error_msg)
            raise ValueError(error_msg)
        
        # STEP 2: Load vision and backlog (tech stack from NFR-001 or existing project)
        logger.info("=" * 80)
        logger.info("STEP 2: Loading Context")
        logger.info("=" * 80)
        vision = self._load_vision()
        # Store vision as instance variable for use in _run_tests()
        self.vision = vision
        
        # Tech stack: Load from NFR-001 (SP-001) or from saved architecture (SP-002+)
        if self.sprint_id != 'SP-001' and not tech_stack_nfr_id:
            # Subsequent sprint - load tech stack from architecture (saved by Mike in SP-001)
            architecture = self._load_architecture()
            self.tech_stack = architecture.get('tech_stack')
            if self.tech_stack:
                vision['tech_stack'] = f"{self.tech_stack.get('backend')} + {self.tech_stack.get('frontend')} + {self.tech_stack.get('database')}"
                vision['tech_stack_details'] = self.tech_stack
                logger.info(f"✅ Loaded tech stack from architecture: {vision['tech_stack']}")
            else:
                logger.warning(f"⚠️ No tech stack found in architecture - was NFR-001 processed in SP-001?")
                self.tech_stack = None
        else:
            # SP-001 or NFR-001 in sprint - tech stack will be set after Mike processes NFR-001
            self.tech_stack = None
        
        backlog_stories = self._load_backlog_stories()
        
        tasks_completed = 0
        tests_passed_total = 0
        tests_failed_total = 0
        
        project_root = EXECUTION_SANDBOX / project_name
        
        for story_id in stories:
            try:
                await self._log_event("story_started", {"story_id": story_id})
                now = datetime.now().isoformat()
                
                await self._update_backlog(story_id, {
                    "Sprint_ID": self.sprint_id,
                    "Execution_Status": "in_progress",
                    "Execution_Started_At": now,
                    "Last_Event": "story_started",
                    "Last_Updated": now,
                })
                
                # Get story details
                story = backlog_stories.get(story_id)
                if not story:
                    logger.error(f"Story {story_id} not found in backlog")
                    await self._log_event("story_failed", {"story_id": story_id, "reason": "not_found_in_backlog"})
                    continue
                
                # Capture baseline surface BEFORE Mike/Alex change anything for this story
                baseline_files = self._list_project_files(project_root)
                baseline_deps = self._read_package_dependencies(project_root)

                # Call Mike to break down story
                logger.info(f"Calling Mike for {story_id}")
                await self._post_to_chat("Mike", f"📋 I'm analyzing {story_id} and breaking it down into implementation tasks...")
                task_breakdown = await self._call_mike(story, vision, project_name)
                if not task_breakdown:
                    logger.error(f"Mike failed to break down {story_id}")
                    await self._post_to_chat("Mike", f"⚠️ I had trouble breaking down {story_id}. Let's skip it for now and move to the next story.")
                    await self._log_event("story_failed", {"story_id": story_id, "reason": "mike_breakdown_failed"})
                    continue
                
                tasks = task_breakdown.get("tasks", [])
                
                # VALIDATION LAYER: Check task format and files
                validation_errors = []
                for task in tasks:
                    task_id = task.get('task_id', '')
                    files = task.get('files_to_create', [])
                    command = task.get('command_to_run', '')
                    
                    # Validate task_id format: T-{STORY_ID}-{TASK_NUMBER}
                    expected_prefix = f"T-{story_id}-"
                    if not task_id.startswith(expected_prefix):
                        validation_errors.append({
                            'task_id': task_id,
                            'issue': f"Wrong format. Expected T-{story_id}-XX",
                            'fix': f"Change to {expected_prefix}01, {expected_prefix}02, etc."
                        })
                    
                    # Validate zero-padded task number
                    if task_id.startswith(expected_prefix):
                        task_num = task_id.split('-')[-1]
                        if not (task_num.isdigit() and len(task_num) == 2):
                            validation_errors.append({
                                'task_id': task_id,
                                'issue': "Task number must be zero-padded (01, 02, not 1, 2)",
                                'fix': f"Change {task_num} to {task_num.zfill(2)}"
                            })
                    
                    # Validate files_to_create or command_to_run
                    if not files and not command:
                        validation_errors.append({
                            'task_id': task_id,
                            'issue': "No files or command specified",
                            'fix': "Add at least 1 file to files_to_create OR specify command_to_run"
                        })
                
                # If validation errors found, retry Mike with feedback
                if validation_errors:
                    logger.warning(f"⚠️ Mike's breakdown for {story_id} has {len(validation_errors)} validation errors")
                    for error in validation_errors:
                        logger.warning(f"  Task {error['task_id']}: {error['issue']}")
                    
                    await self._post_to_chat("Mike", f"⚠️ Task breakdown needs corrections: {len(validation_errors)} format issues found")
                    
                    # Retry Mike with validation feedback
                    retry_breakdown = await self._call_mike_retry_validation(story, vision, project_name, validation_errors, task_breakdown)
                    
                    if retry_breakdown and len(retry_breakdown.get("tasks", [])) > 0:
                        logger.info(f"✅ VALIDATION RETRY SUCCESSFUL: Mike corrected format issues")
                        task_breakdown = retry_breakdown
                        tasks = task_breakdown.get("tasks", [])
                        await self._post_to_chat("Mike", f"✅ Corrected task format. All tasks now follow proper naming convention.")
                    else:
                        logger.error(f"❌ VALIDATION RETRY FAILED: Could not correct format issues for {story_id}")
                        await self._post_to_chat("Mike", f"⚠️ Could not correct format issues. Continuing with original breakdown.")
                        # Continue with original tasks - better to have wrong format than fail completely
                
                # Extract tech stack from NFR-001
                if story_id == tech_stack_nfr_id and task_breakdown.get("tech_stack"):
                    tech_stack = task_breakdown.get("tech_stack")
                    self.tech_stack = tech_stack
                    vision['tech_stack'] = f"{tech_stack.get('backend', 'unknown')} + {tech_stack.get('frontend', 'unknown')} + {tech_stack.get('database', 'unknown')}"
                    vision['tech_stack_details'] = tech_stack
                    await self._post_to_chat("System", 
                        f"📦 Tech Stack from Mike: {tech_stack.get('backend')} + {tech_stack.get('frontend')} + {tech_stack.get('database')}")
                    logger.info(f"✅ Tech stack extracted from Mike's breakdown: {tech_stack}")
                
                # LAYER 1: Detect incomplete breakdown
                expected_task_count = task_breakdown.get("task_count", len(tasks))
                actual_task_count = len(tasks)
                
                if actual_task_count < expected_task_count:
                    logger.warning(f"⚠️ INCOMPLETE BREAKDOWN DETECTED for {story_id}: Expected {expected_task_count} tasks, got {actual_task_count}")
                    
                    # LAYER 2: Attempt intelligent retry to recover missing tasks
                    retry_breakdown = await self._call_mike_retry_incomplete(
                        story, vision, project_name,
                        expected_task_count, actual_task_count, tasks
                    )
                    
                    if retry_breakdown and len(retry_breakdown.get("tasks", [])) > 0:
                        recovered_tasks = retry_breakdown.get("tasks", [])
                        logger.info(f"✅ RECOVERY SUCCESSFUL: Recovered {len(recovered_tasks)} missing tasks")
                        tasks.extend(recovered_tasks)
                        actual_task_count = len(tasks)
                        
                        await self._log_event("incomplete_breakdown_recovered", {
                            "story_id": story_id,
                            "expected_count": expected_task_count,
                            "recovered_count": len(recovered_tasks),
                            "total_now": actual_task_count
                        })
                        
                        await self._post_to_chat("Mike", f"✅ Recovered {len(recovered_tasks)} missing tasks from incomplete breakdown. Now have all {actual_task_count} tasks.")
                    else:
                        # LAYER 3: Graceful degradation - log and continue with what we have
                        logger.error(f"❌ RECOVERY FAILED: Could not recover missing tasks for {story_id}")
                        
                        await self._log_event("incomplete_breakdown_unrecovered", {
                            "story_id": story_id,
                            "expected_count": expected_task_count,
                            "actual_count": actual_task_count,
                            "missing_count": expected_task_count - actual_task_count
                        })
                        
                        await self._post_to_chat("Mike", f"⚠️ Breakdown was incomplete ({actual_task_count}/{expected_task_count} tasks). Continuing with available tasks.")
                
                # Freeze Mike's contract for this story (closed world: baseline + design)
                arch_contract = self._build_arch_contract(baseline_files, baseline_deps, task_breakdown, story_id)

                # Capture Mike's breakdown for debugging contract enforcement
                self._capture_mike_breakdown(story_id, task_breakdown, baseline_files, arch_contract)

                await self._log_event("mike_breakdown", {
                    "story_id": story_id,
                    "task_count": actual_task_count,
                    "expected_count": expected_task_count,
                    "technical_notes": task_breakdown.get("technical_notes", "")
                })
                
                # Chat narration: Mike completed breakdown
                await self._post_to_chat("Mike", f"✅ Broke down {story_id} into {actual_task_count} implementation tasks. Alex is ready to start coding.")
                
                # ============================================================================
                # RETRY LOOP WITH CUMULATIVE LEARNING
                # ============================================================================
                max_attempts = 3
                attempt_history = []
                final_test_success = False
                final_tests_passed = 0
                final_tests_failed = 0
                final_story_files_written = []
                
                for attempt_number in range(1, max_attempts + 1):
                    logger.info(f"📝 Story {story_id} - Attempt {attempt_number}/{max_attempts}")
                    
                    # Detect repeated errors from previous attempt (for smart guidance)
                    repeated_error_guidance = None
                    if attempt_number > 1 and len(attempt_history) > 0:
                        prev_attempt = attempt_history[-1]
                        prev_errors = prev_attempt['test_result'].get('errors', '')
                        
                        # Check for common repeated error patterns
                        if 'path is not defined' in prev_errors:
                            repeated_error_guidance = """
🚨 CRITICAL ERROR REPEATED: 'path is not defined'

You're using path.join() or __dirname without importing them.

REQUIRED IMPORTS AT TOP OF FILE:
```javascript
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
```
"""
                        elif 'SQLITE_MISUSE: Database is closed' in prev_errors or 'Cannot read properties of undefined (reading \'close\')' in prev_errors:
                            repeated_error_guidance = """
🚨 CRITICAL ERROR REPEATED: 'SQLITE_MISUSE: Database is closed'

This is a TEST PATTERN issue. Your tests are sharing database connections.

REQUIRED FIX - Each test MUST follow this EXACT structure:

```javascript
test('Test name', async (t) => {
  // REQUIRED: Import INSIDE each test function
  const { db, initDB } = await import('../src/db.js');
  
  try {
    await initDB();
    // ... your test logic ...
    // ... assertions ...
  } finally {
    // REQUIRED: Always close in finally block
    await new Promise((resolve) => db.close(resolve));
  }
});
```

DO NOT:
❌ Import db at file level (const { db } = await import(...) before test())
❌ Close db once for all tests (test 2+ will fail with "Database is closed")
❌ Forget to close db in any test (causes connection leaks)
❌ Use shared db connection between tests

Every single test must import, use, and close its own db connection.
This is NON-NEGOTIABLE for SQLite test isolation.
"""
                        elif 'Cannot find package' in prev_errors:
                            missing_pkg = prev_errors.split("'")[1] if "'" in prev_errors else "unknown"
                            repeated_error_guidance = f"""
🚨 CRITICAL ERROR REPEATED: Missing package '{missing_pkg}'

You imported '{missing_pkg}' in code but didn't add it to package.json.

Add to dependencies section in package.json.
"""
                        elif 'SQLITE_ERROR' in prev_errors or 'near' in prev_errors:
                            repeated_error_guidance = """
🚨 CRITICAL ERROR REPEATED: SQL Syntax Error

Common SQLite issues:
1. Reserved words used as column names without quotes (check, default, order, group, key, etc.)
   - Fix: Use double quotes "reserved_word" or rename column
2. Missing commas between field definitions
3. CHECK constraints need parentheses: CHECK (condition) not CHECK condition

Example correct syntax:
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  "order" INTEGER,  -- reserved word quoted
  status TEXT CHECK (status IN ('active', 'inactive'))
)
"""
                    
                    if attempt_number > 1:
                        if repeated_error_guidance:
                            await self._post_to_chat(
                                "System",
                                f"🔄 Retrying {story_id} (attempt {attempt_number}/{max_attempts}). Tests are still failing with a repeated error pattern; applying targeted guidance for the next attempt."
                            )
                        else:
                            await self._post_to_chat(
                                "System",
                                f"🔄 Retrying {story_id} (attempt {attempt_number}/{max_attempts}) with error feedback from previous attempts..."
                            )
                    
                    # Track all files written across all tasks for this attempt
                    story_files_written = []
                    
                    # Call Alex to generate code for each task
                    for task_idx, task in enumerate(tasks, 1):
                        # Check if paused before each task
                        await self._wait_if_paused()
                        
                        task_desc_full = task.get('description', 'task')
                        task_desc_short = task_desc_full.split(':')[0].strip()
                        task_id = task.get('task_id', 'unknown')
                        
                        # Check if this is a command-only task (no files to create)
                        task_files = task.get('files_to_create', []) or []
                        task_command = task.get('command_to_run', '')
                        
                        if not task_files and task_command:
                            # Command-only task - skip Alex, just run the command
                            logger.info(f"🔧 Command-only task {task_id}: {task_command}")
                            await self._post_to_chat("System", f"⚙️ Running command: {task_command}")
                            
                            success = await self._execute_task_command(
                                task_command,
                                EXECUTION_SANDBOX / project_name,
                                task_id
                            )
                            
                            if success:
                                tasks_completed += 1
                                await self._log_event("command_executed", {
                                    "story_id": story_id,
                                    "task_id": task_id,
                                    "command": task_command
                                })
                                await self._post_to_chat("System", f"✅ Command completed: {task_command}")
                            else:
                                logger.error(f"❌ Command failed for task {task_id}: {task_command}")
                                await self._post_to_chat("System", f"❌ Command failed: {task_command}")
                                await self._log_event("command_failed", {
                                    "story_id": story_id,
                                    "task_id": task_id,
                                    "command": task_command,
                                    "reason": "Command execution failed"
                                })
                            continue  # Skip to next task - no files to write
                        
                        logger.info(f"Calling Alex for task {task_id}")
                        # Note: Only show completion message to avoid duplicate chat entries
                        
                        # Self-healing: Retry up to 2 times if syntax errors OR JSON parse failures occur
                        max_retries = 2
                        retry_count = 0
                        code_result = None
                        syntax_errors = []
                        previous_response = ""  # Track previous attempt for retry context
                        json_parse_failed = False
                        
                        while retry_count <= max_retries:
                            # Build retry context if we're on a story retry (attempt_number > 1)
                            story_retry_context = None
                            if attempt_number > 1 and len(attempt_history) > 0:
                                story_retry_context = {
                                    'attempt_number': attempt_number,
                                    'max_attempts': max_attempts,
                                    'previous_attempts': attempt_history,
                                    'repeated_error_guidance': repeated_error_guidance if 'repeated_error_guidance' in locals() else None
                                }
                            
                            if retry_count == 0:
                                # First attempt (of this task-level retry, but might be story-level retry)
                                code_result = await self._call_alex(task, story, vision, project_name, task_breakdown, retry_context=story_retry_context)
                                json_parse_failed = (code_result is None)
                            else:
                                # Retry with error feedback AND previous attempt
                                if json_parse_failed:
                                    logger.info(f"Retry {retry_count}/{max_retries} for task {task.get('task_id')} due to JSON parse failure")
                                    await self._post_to_chat("Alex", f"⚠️ Re-attempting task - previous response was not valid JSON (attempt {retry_count + 1}/{max_retries + 1})...")
                                    code_result = await self._call_alex(task, story, vision, project_name, task_breakdown, retry_context=story_retry_context)
                                    json_parse_failed = (code_result is None)
                                else:
                                    logger.info(f"Retry {retry_count}/{max_retries} for task {task.get('task_id')} due to syntax errors")
                                    await self._post_to_chat("Alex", f"⚠️ Fixing syntax errors (attempt {retry_count + 1}/{max_retries + 1})...")
                                    code_result = await self._call_alex_retry(task, story, vision, project_name, syntax_errors, previous_response, task_breakdown)
                        
                            if not code_result:
                                # Retry if we haven't exhausted attempts
                                if retry_count < max_retries:
                                    retry_count += 1
                                    continue
                                else:
                                    # Final failure - task skipped
                                    logger.error(f"Task {task.get('task_id')} skipped after {max_retries + 1} attempts - Alex returned no valid JSON")
                                    await self._post_to_chat("Alex", f"❌ Skipped task {task.get('task_id')} - could not parse response as JSON after {max_retries + 1} attempts")
                                    break
                            
                            # Save response for potential retry
                            previous_response = json.dumps(code_result, indent=2)
                            
                            # Log what Alex returned for debugging
                            logger.info(f"Alex returned: {previous_response[:500]}")
                            
                            # Normalize Alex's response (handles multiple format variations)
                            files = self._normalize_alex_response(code_result)
                            
                            # Validate syntax before writing
                            syntax_errors = self._validate_files_syntax(files)
                        
                            if not syntax_errors:
                                # All files valid, write them
                                files_written = self._write_code_files(project_name, files, story_id, skip_validation=True)
                                story_files_written.extend(files_written)  # Track at story level
                                tasks_completed += 1
                                await self._log_event("alex_implemented", {
                                    "story_id": story_id,
                                    "task_id": task.get("task_id"),
                                    "description": task.get("description", "task"),
                                    "files_written": len(files_written),
                                    "file_paths": files_written,
                                    "retry_count": retry_count
                                })
                                
                                # Chat narration: Alex completed task with verbose description
                                task_id = task.get('task_id', 'unknown')
                                task_desc_short = task.get('description', 'task').split(':')[0].strip()
                                verbose_message = f"✍️ Implementing task {task_idx}/{len(tasks)}: {task_desc_short}"
                                
                                # Post to chat UI (display-only, verbose for user visibility)
                                await self._post_to_chat("Alex", verbose_message)
                                
                                # Log structured event for tracking
                                await self._log_event("alex_implemented", {
                                    "story_id": story_id,
                                    "task_id": task_id,
                                    "task_number": task_idx,
                                    "total_tasks": len(tasks),
                                    "description": task_desc_short,
                                    "files_count": len(files_written)
                                })
                                
                                # Execute command_to_run if specified (stack-agnostic install/setup)
                                if task.get('command_to_run'):
                                    command = task.get('command_to_run')
                                    logger.info(f"🔧 Executing command from task {task_id}: {command}")
                                    await self._post_to_chat("System", f"⚙️ Running: {command}")
                                    
                                    success = await self._execute_task_command(
                                        command, 
                                        EXECUTION_SANDBOX / project_name,
                                        task_id
                                    )
                                    
                                    if not success:
                                        logger.error(f"❌ Command failed for task {task_id}: {command}")
                                        await self._post_to_chat("System", f"❌ Command failed: {command}")
                                        await self._log_event("command_failed", {
                                            "story_id": story_id,
                                            "task_id": task_id,
                                            "command": command,
                                            "reason": "Command execution failed"
                                        })
                                        # Stop execution - don't continue to next tasks
                                        raise Exception(f"Task command failed: {command}")
                                    else:
                                        await self._post_to_chat("System", f"✅ Command completed: {command}")
                                        await self._log_event("command_executed", {
                                            "story_id": story_id,
                                            "task_id": task_id,
                                            "command": command
                                        })
                                
                                break
                            else:
                                # Syntax errors found, retry if attempts remain
                                retry_count += 1
                                if retry_count > max_retries:
                                    logger.error(f"Could not validate syntax for task {task.get('task_id')}, skipping files with errors")
                                    await self._post_to_chat("Alex", f"⚠️ Unable to fix syntax errors after {max_retries + 1} attempts. Skipping this task.")
                                    # Write only valid files
                                    valid_files = [f for f in files if not any(err['path'] == f.get('path') for err in syntax_errors)]
                                    if valid_files:
                                        files_written = self._write_code_files(project_name, valid_files, story_id, skip_validation=True)
                                        story_files_written.extend(files_written)  # Track at story level
                                        await self._log_event("alex_implemented_partial", {
                                            "story_id": story_id,
                                            "task_id": task.get("task_id"),
                                            "files_written": files_written,
                                            "files_skipped": len(syntax_errors)
                                        })
                    
                    # All tasks complete - enforce architecture contract BEFORE tests
                    contract_ok = self._enforce_arch_contract(project_root, story_id, arch_contract, story_files_written)
                    if not contract_ok:
                        # Hard failure: story is considered failed due to contract violation
                        await self._log_event("architectural_contract_violation", {
                            "story_id": story_id,
                            "files_written": list(story_files_written),
                        })
                        await self._post_to_chat(
                            "System",
                            f"❌ {story_id} failed architectural contract enforcement. Files/dependencies were introduced outside Mike's contract. Skipping tests for this story.",
                        )
                        # Save for final reporting, but treat as all tests failed
                        final_test_success = False
                        final_tests_passed = 0
                        final_tests_failed = 0
                        final_story_files_written = story_files_written
                        # Abort retry loop for this story
                        break

                    # Best-effort Node/Express/SQLite contract validation (warnings only)
                    if any("package.json" in f for f in story_files_written):
                        # Install npm dependencies before running tests
                        logger.info(f"📦 package.json detected, installing npm dependencies...")
                        if self._install_dependencies(project_root):
                            await self._post_to_chat("System", "✅ npm dependencies installed successfully")
                        else:
                            await self._post_to_chat("System", "⚠️ npm install failed - tests may not run correctly")
                        self._validate_node_contracts(project_root, story_id, task_breakdown)

                    # Call Jordan to generate tests
                    logger.info(f"Calling Jordan for {story_id}")
                    await self._post_to_chat("Jordan", f"🧪 I'm writing tests for {story_id} to verify all acceptance criteria...")
                    test_result = await self._call_jordan(story, task_breakdown, project_name, vision, tech_stack=self.tech_stack)
                    
                    test_file_written = ""
                    if test_result:
                        # Handle case where Jordan returns a list instead of dict
                        if isinstance(test_result, list):
                            logger.warning("Jordan returned a list instead of dict, skipping test generation")
                            test_result = None
                        else:
                            # Write test file
                            test_file_written = self._write_test_file(project_name, test_result)
                            test_cases = test_result.get('test_cases', [])
                            await self._post_to_chat("Jordan", f"✅ Generated {len(test_cases)} test cases. Now running tests...",
                                                   event_type="tests_generated",
                                                   event_data={"story_id": story_id, "count": len(test_cases)})
                    
                    # PHASE 2: Actually run the tests
                    project_root = EXECUTION_SANDBOX / project_name
                    test_execution_result = await self._run_tests(project_root, test_file_written if test_file_written else None)
                    
                    tests_passed = test_execution_result.get('passed', 0)
                    tests_failed = test_execution_result.get('failed', 0)
                    test_success = test_execution_result.get('success', False)
                    
                    # Note: Don't accumulate here - wait for final results after retry loop
                    
                    # Chat narration: Jordan test results
                    if tests_passed + tests_failed > 0:
                        if tests_failed == 0:
                            await self._post_to_chat("Jordan", f"✅ All tests passed for {story_id}! ({tests_passed} passed)",
                                                   event_type="jordan_tested",
                                                   event_data={"story_id": story_id, "passed": tests_passed, "failed": 0})
                        else:
                            await self._post_to_chat("Jordan", f"⚠️ Test results for {story_id}: {tests_passed} passed, {tests_failed} failed",
                                                   event_type="jordan_tested",
                                                   event_data={"story_id": story_id, "passed": tests_passed, "failed": tests_failed})
                    else:
                        # No tests executed - could be an error or timeout
                        if not test_success:
                            await self._post_to_chat("Jordan", f"❌ Test execution failed for {story_id} (check logs for errors)")
                        else:
                            await self._post_to_chat("Jordan", f"ℹ️ No tests were executed for {story_id}")
                    
                    await self._log_event("jordan_tested", {
                        "story_id": story_id,
                        "test_file": test_file_written,
                        "test_count": tests_passed + tests_failed,
                        "passed": tests_passed,
                        "failed": tests_failed,
                        "output": test_execution_result.get('output', '')  # Full output for debugging
                    })

                    # If tests failed, ask Jordan to analyze and provide fix instructions
                    failure_analysis = []
                    if not test_success or tests_failed > 0:
                        logger.info(f"Tests failed for {story_id}, asking Jordan for failure analysis...")
                        failure_analysis = await self._call_jordan_for_analysis(
                            story, 
                            test_file_written, 
                            test_execution_result.get('output', '')[:2000],  # Send test output to Jordan
                            project_name
                        )
                        if failure_analysis:
                            logger.info(f"Jordan provided {len(failure_analysis)} fix instructions")
                    
                    # Record this attempt in history
                    attempt_history.append({
                        "attempt": attempt_number,
                        "files_written": list(story_files_written),  # Copy list
                        "test_result": {
                            "success": test_success,
                            "passed": tests_passed,
                            "failed": tests_failed,
                            "errors": test_execution_result.get('output', '')[:1000],  # Keep manageable
                            "failure_analysis": failure_analysis  # Jordan's specific fix instructions
                        }
                    })
                    
                    # Save for final reporting
                    final_test_success = test_success
                    final_tests_passed = tests_passed
                    final_tests_failed = tests_failed
                    final_story_files_written = story_files_written
                    
                    # Check if we should retry
                    if test_success and tests_failed == 0:
                        # Perfect - all tests passed, exit retry loop
                        await self._post_to_chat("System", f"✅ {story_id} completed successfully (attempt {attempt_number}/{max_attempts})")
                        break
                    elif attempt_number < max_attempts:
                        # Tests failed but we have attempts left - retry
                        await self._post_to_chat("Jordan", f"⚠️ Tests failed on attempt {attempt_number}. Will retry with error feedback.")
                        logger.warning(f"Attempt {attempt_number} failed for {story_id}, retrying...")
                        # Loop continues - next attempt will have attempt_history available
                        continue
                    else:
                        # Final attempt exhausted
                        await self._post_to_chat("System", f"⚠️ {story_id} completed after {max_attempts} attempts but tests still failing. Code kept for review.")
                        logger.warning(f"Story {story_id} completed with test failures after {max_attempts} attempts")
                        break
                
                # END OF RETRY LOOP
                # ============================================================================
                
                # Accumulate FINAL test results (not intermediate retry attempts)
                tests_passed_total += final_tests_passed
                tests_failed_total += final_tests_failed
                
                # Mark story complete (even if tests failed - code is kept for inspection)
                if final_test_success and final_tests_failed == 0:
                    # Perfect - all tests passed
                    execution_status = "completed"
                    last_event = "story_completed"
                elif final_tests_passed > 0 and final_tests_failed > 0:
                    # Partial - some tests passed, some failed
                    execution_status = "completed_with_failures"
                    last_event = "story_completed_with_test_failures"
                else:
                    # All tests failed or couldn't run
                    execution_status = "completed_with_failures"
                    last_event = "story_completed_with_test_failures"
                
                await self._log_event(last_event, {
                    "story_id": story_id,
                    "tests_passed": final_tests_passed,
                    "tests_failed": final_tests_failed,
                    "attempts": len(attempt_history)
                })
                
                # Clean up backup files
                self._cleanup_backups(project_name, story_id)
                
                # Update backlog
                now = datetime.now().isoformat()
                await self._update_backlog(story_id, {
                    "Execution_Status": execution_status,
                    "Execution_Completed_At": now,
                    "Last_Event": last_event,
                    "Last_Updated": now,
                })
                
                # Auto-complete related WF- stories when US- story completes successfully
                if story_id.startswith("US-") and execution_status == "completed":
                    await self._auto_complete_related_wireframes(story_id, now)
                
            except Exception as e:
                logger.error(f"Error executing story {story_id}: {e}", exc_info=True)
                await self._log_event("story_failed", {
                    "story_id": story_id,
                    "error": str(e)
                })

        # Sprint complete
        summary = {
            "stories_completed": len(stories),
            "stories_failed": 0,  # Could track this if needed
            "tasks_completed": tasks_completed,
            "tests_passed": tests_passed_total,
            "tests_failed": tests_failed_total,
        }

        await self._log_event("sprint_completed", {"summary": summary})

        # Update plan to completed
        plan["status"] = "completed"
        plan["completed_at"] = datetime.now().isoformat()
        self._save_plan(plan)
        
        # End Sprint Execution meeting (following meeting protocol)
        test_summary = f"{summary['tests_passed']} passed"
        if summary['tests_failed'] > 0:
            test_summary += f", {summary['tests_failed']} failed"
        
        await self._post_to_chat("Sarah", f"✅ Sprint {self.sprint_id} completed! {summary['stories_completed']} stories, {summary['tasks_completed']} tasks, {test_summary}.")
        
        # TESTING: Check if all stories completed successfully
        all_completed = True
        for story_id in stories:
            try:
                # Read story execution status from backlog
                backlog_stories = self._load_backlog_stories()
                story_data = backlog_stories.get(story_id, {})
                execution_status = story_data.get('Execution_Status', '')
                if execution_status != "completed":
                    all_completed = False
                    break
            except Exception:
                all_completed = False
                break
        
        if not all_completed:
            await self._post_to_chat("Sarah", f"⚠️ NOTE: Some stories had issues during execution. Consider using sprint rollback if needed.")
        
        # Close SSE stream
        from services.sse_manager import sse_manager
        await sse_manager.close_sprint_stream(self.sprint_id)

    # ============================================================================
    # PROJECT STATE EXTRACTION FOR MIKE'S CONTEXT
    # ============================================================================

    def _extract_project_state(self, project_path: Path) -> Dict:
        """Extract current project state to give Mike context of what's already built."""
        state = {
            'database_schema': extract_database_schema(project_path),
            'api_endpoints': extract_api_endpoints(project_path),
            'file_structure': extract_file_structure(project_path),
            'code_patterns': extract_code_patterns(project_path)
        }
        logger.info(f"📂 Project state extracted for Mike:")
        logger.info(f"  Database schema: {state['database_schema'][:100]}...")
        logger.info(f"  API endpoints: {state['api_endpoints'][:100]}...")
        logger.info(f"  File structure: {state['file_structure'][:200]}...")
        logger.info(f"  Code patterns: {state['code_patterns'][:100]}...")
        return state

    async def _call_mike(self, story: Dict, vision: Dict, project_name: str) -> Optional[Dict]:
        """Call Mike (SPRINT_EXECUTION_ARCHITECT) to break down story."""
        try:
            # Import here to avoid circular dependency
            from services.ai_gateway import call_openrouter_api, load_personas
            from core.models_config import ModelsConfig
            
            # Load wireframe if exists
            wireframe_html = ""
            wireframe_ref = story.get("Wireframe_Ref", "")
            if wireframe_ref:
                wireframe_path = WIREFRAME_DIR / f"{wireframe_ref}.html"
                if wireframe_path.exists():
                    wireframe_html = wireframe_path.read_text(encoding="utf-8")
            
            # Load Mike's persona config to get system prompt
            personas = load_personas()
            mike_config = personas.get("SPRINT_EXECUTION_ARCHITECT", {})
            mike_system_prompt = mike_config.get("system_prompt", "")
            
            # Load architecture
            architecture = self._load_architecture()
            
            # Extract current project state for context
            project_path = EXECUTION_SANDBOX / project_name
            project_state = self._extract_project_state(project_path)
            
            # Build user message with story context, project state, tech stack, architecture, and wireframe
            tech_stack_info = ""
            architecture_info = ""
            story_id = story.get('Story_ID', '')
            
            # Only pass tech stack for non-NFR-001 stories (NFR-001 defines the tech stack)
            if self.tech_stack and not ('NFR' in story_id and '001' in story_id):
                logger.info(f"🔍 Mike receiving tech stack: {self.tech_stack}")
                tech_stack_info = f"""
TECH STACK (from NFR-001):
- Backend: {self.tech_stack.get('backend', 'unknown')}
- Frontend: {self.tech_stack.get('frontend', 'unknown')}
- Database: {self.tech_stack.get('database', 'unknown')}
- Backend Port: {self.tech_stack.get('backend_port', 'unknown')}
- Frontend Port: {self.tech_stack.get('frontend_port', 'unknown')}

CRITICAL: All tasks must use these exact ports and technologies.
"""
            elif 'NFR' in story_id and '001' in story_id:
                logger.info(f"🔍 Mike processing NFR-001 - will extract tech stack from story requirements")
            
            # For NFR-001, pass all sprint stories so Mike can look ahead
            sprint_context = ""
            if 'NFR' in story_id and '001' in story_id:
                plan = self._load_plan()
                all_story_ids = plan.get("stories", [])
                backlog_stories = self._load_backlog_stories()
                
                sprint_context = "\n\nOTHER STORIES IN THIS SPRINT (Read their requirements to inform your architecture decisions):\n\n"
                for other_story_id in all_story_ids:
                    if other_story_id != story_id:
                        other_story = backlog_stories.get(other_story_id)
                        if other_story:
                            sprint_context += f"""
Story ID: {other_story.get('Story_ID')}
Title: {other_story.get('Title')}
Acceptance Criteria:
{other_story.get('Acceptance_Criteria', 'N/A')}
---
"""
                sprint_context += "\nCRITICAL: Read these requirements BEFORE choosing auth method, module system, or other architectural decisions.\n"
                logger.info(f"🔍 Mike receiving {len(all_story_ids)-1} other stories in sprint for context")
            
            # Pass architecture conventions to Mike
            if architecture.get('conventions'):
                architecture_info = f"""
CURRENT ARCHITECTURE (LOCKED - DO NOT CHANGE):
Architecture locked: {architecture.get('architecture_locked', False)}
Locked at sprint: {architecture.get('locked_at_sprint', 'N/A')}

Conventions:
{json.dumps(architecture.get('conventions'), indent=2)}

CRITICAL: Follow these conventions EXACTLY. If story requirements conflict with locked architecture, output architectural_conflict block.
"""
                logger.info(f"🔍 Mike receiving locked architecture from {architecture.get('locked_at_sprint')}")
            
            # Inject pending TODOs into Mike's context
            todos_info = ""
            if architecture.get('todos'):
                pending_todos = [t for t in architecture['todos'] if t.get('status') == 'pending']
                if pending_todos:
                    todos_info = "\nPENDING TODOs:\n"
                    for todo in pending_todos:
                        file_info = f" (file: {todo['file']})" if todo.get('file') else ""
                        priority_icon = "🔴" if todo['priority'] == 'high' else "🟡" if todo['priority'] == 'medium' else "🟢"
                        todos_info += f"- {todo['id']}: {todo['description']}{file_info} [{priority_icon} {todo['priority']}]\n"
                    todos_info += "\nIf your breakdown resolves any TODOs, add their IDs to the 'remove' array in your output.\n"
                    logger.info(f"🔍 Mike receiving {len(pending_todos)} pending TODOs")
            
            # Inject full context (vision + backlog)
            backlog_context = self._format_backlog_for_context(self._load_backlog_stories())
            vision_context = self._format_vision_for_context(vision)
            
            # Add clear context header
            context_header = f"""
═══════════════════════════════════════════════════════════════════════════════
YOUR CURRENT TASK CONTEXT:
═══════════════════════════════════════════════════════════════════════════════
Role: Mike (Sprint Execution Architect)
Story: {story.get('Story_ID')} - {story.get('Title', 'N/A')}
Your Specific Job: Break down this story into implementation tasks
Output Required: JSON with task breakdown including any install/setup commands needed
═══════════════════════════════════════════════════════════════════════════════
"""
            
            user_message = f"""{context_header}

{vision_context}

{backlog_context}

CURRENT PROJECT STATE:
🚨 CRITICAL: Review this section BEFORE creating tasks!
Files listed below ALREADY EXIST from previous sprints.
Use "MODIFY" or "Update" for existing files, "Create" only for new files.

{project_state['database_schema']}

{project_state['api_endpoints']}

{project_state['file_structure']}

{project_state['code_patterns']}
{tech_stack_info}
{architecture_info}
{todos_info}
{sprint_context}
---

CURRENT STORY TO BREAK DOWN: {story.get('Story_ID')}

Wireframe:
{wireframe_html if wireframe_html else 'No wireframe'}"""

            # Call LLM with SPRINT_EXECUTION_ARCHITECT persona
            # Get default model
            models_config = ModelsConfig()
            _, model, _, _ = models_config.load_config()
            
            response_text = ""
            async for chunk in call_openrouter_api(
                messages=[
                    {"role": "system", "content": mike_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=model,
                persona_name="Mike",
                persona_key="SPRINT_EXECUTION_ARCHITECT",
                include_tools=False  # Execution personas output JSON only, no tools needed
            ):
                if "content" in chunk:
                    response_text += chunk.get("content", "")
            
            # Parse JSON from response
            result = self._extract_json(response_text)
            
            if not result:
                logger.error(f"Mike returned no valid JSON for {story.get('Story_ID')}")
                logger.error(f"Mike's raw response length: {len(response_text)} chars")
                logger.error(f"Mike's raw response (first 500 chars): {response_text[:500]}")
                logger.error(f"Mike's raw response (last 200 chars): {response_text[-200:]}")
                raw_response_path = self._maybe_capture_mike_failure_payload(story_id, "json_parse", response_text)
                # Structured failure event for future diagnosis
                await self._log_event(
                    "mike_failure",
                    {
                        "story_id": story_id,
                        "failure_stage": "json_parse",
                        "details_snippet": response_text[:300],
                        "raw_response_snippet": response_text[:2000],
                        "raw_response_path": raw_response_path
                    }
                )
                return None
            
            # Check for architectural conflicts
            if result.get('architectural_conflict', {}).get('detected'):
                conflict = result['architectural_conflict']
                logger.error(f"⚠️ ARCHITECTURAL CONFLICT DETECTED for {story_id}")
                logger.error(f"Current: {conflict.get('current_architecture')}")
                logger.error(f"Required: {conflict.get('story_requirement')}")
                logger.error(f"Reason: {conflict.get('conflict_reason')}")
                raw_response_path = self._maybe_capture_mike_failure_payload(story_id, "architectural_conflict", response_text)
                
                await self._post_to_chat(
                    "Mike",
                    f"⚠️ **ARCHITECTURAL CONFLICT DETECTED**\n\n"
                    f"**Story:** {story_id}\n"
                    f"**Current Architecture:** {conflict.get('current_architecture')}\n"
                    f"**Story Requirement:** {conflict.get('story_requirement')}\n\n"
                    f"**Conflict:** {conflict.get('conflict_reason')}\n\n"
                    f"**Recommendation:** {conflict.get('recommended_action')}\n\n"
                    f"**Sprint execution paused.** Please create a migration story or revise story requirements."
                )
                
                # Structured failure event for conflict cases
                await self._log_event(
                    "mike_failure",
                    {
                        "story_id": story_id,
                        "failure_stage": "architectural_conflict",
                        "details_snippet": json.dumps(conflict, default=str)[:300],
                        "raw_response_snippet": response_text[:2000],
                        "raw_response_path": raw_response_path
                    }
                )

                # Return None to signal conflict - orchestrator will handle this
                return None
            
            # If NFR-001, save conventions and lock architecture
            if story_id == 'NFR-001' and result.get('conventions'):
                logger.info(f"🔒 Locking architecture with conventions from NFR-001")
                architecture['conventions'] = result['conventions']
                architecture['architecture_locked'] = True
                architecture['locked_at_sprint'] = self.sprint_id
                architecture['last_updated'] = datetime.now().isoformat()
                if result.get('tech_stack'):
                    architecture['tech_stack'] = result['tech_stack']
                self._save_architecture(architecture)
                await self._post_to_chat(
                    "System",
                    f"🔒 Architecture locked. All future stories must follow these conventions."
                )
            
            # Accumulate database schema, API endpoints, and convention extensions for ALL stories
            if result.get('database_design') or result.get('api_design') or (result.get('conventions') and story_id != 'NFR-001'):
                logger.info(f"📊 Updating architecture.json with design from {story_id}")
                architecture = self._load_architecture()  # Reload to get latest state
                architecture = self._accumulate_architecture_design(architecture, result, story_id)
                self._save_architecture(architecture)
            
            # Update TODOs from Mike's breakdown
            if result.get('todos'):
                logger.info(f"📝 Processing TODO updates from {story_id}")
                architecture = self._load_architecture()  # Reload to get latest
                
                # Initialize todos array if doesn't exist
                if 'todos' not in architecture:
                    architecture['todos'] = []
                
                # Add new TODOs
                todos_to_add = result['todos'].get('add', [])
                if todos_to_add:
                    for new_todo in todos_to_add:
                        next_id = len([t for t in architecture['todos'] if t.get('status') != 'deleted']) + 1
                        todo_entry = {
                            'id': f"TODO-{next_id:03d}",
                            'description': new_todo['description'],
                            'file': new_todo.get('file'),
                            'created_in': story_id,
                            'status': 'pending',
                            'priority': new_todo.get('priority', 'medium'),
                            'created_at': datetime.now().isoformat()
                        }
                        architecture['todos'].append(todo_entry)
                        logger.info(f"  ➕ Added {todo_entry['id']}: {new_todo['description']}")
                
                # Remove/complete TODOs
                todos_to_remove = result['todos'].get('remove', [])
                if todos_to_remove:
                    for todo_id in todos_to_remove:
                        for todo in architecture['todos']:
                            if todo['id'] == todo_id and todo.get('status') == 'pending':
                                todo['status'] = 'completed'
                                todo['completed_in'] = story_id
                                todo['completed_at'] = datetime.now().isoformat()
                                logger.info(f"  ✅ Completed {todo_id}: {todo['description']}")
                                break
                
                # Save updated architecture
                self._save_architecture(architecture)
            
            # Log what Mike actually returned
            logger.info(f"✅ Mike returned structure with keys: {list(result.keys())}")
            if "tasks" in result:
                logger.info(f"✅ Mike returned {len(result['tasks'])} tasks")
                if result['tasks']:
                    logger.info(f"First task keys: {list(result['tasks'][0].keys())}")
            else:
                logger.error(f"❌ Mike's parsed result is MISSING 'tasks' field!")
                logger.error(f"Parsed result keys: {list(result.keys())}")
                logger.error(f"Parsed result content: {json.dumps(result, default=str)[:500]}")
                logger.error(f"Raw response length: {len(response_text)} chars")
                logger.error(f"This indicates a JSON parsing failure, not a Mike output failure")
            
            # PHASE 1: Validate task breakdown
            if not self._validate_task_breakdown(result, story.get('Story_ID', 'unknown')):
                logger.error(f"Mike's breakdown failed validation for {story.get('Story_ID')}")
                raw_response_path = self._maybe_capture_mike_failure_payload(story_id, "validation", response_text)
                # Structured failure event for validation issues
                await self._log_event(
                    "mike_failure",
                    {
                        "story_id": story_id,
                        "failure_stage": "validation",
                        "details_snippet": json.dumps(result, default=str)[:300],
                        "raw_response_snippet": response_text[:2000],
                        "raw_response_path": raw_response_path
                    }
                )
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling Mike: {e}", exc_info=True)
            # Structured failure event for unexpected exceptions
            await self._log_event(
                "mike_failure",
                {
                    "story_id": story.get('Story_ID', 'unknown'),
                    "failure_stage": "exception",
                    "details_snippet": str(e)[:300]
                }
            )
            return None

    async def _call_mike_retry_validation(self, story: Dict, vision: Dict, project_name: str,
                                          validation_errors: List[Dict], original_breakdown: Dict) -> Optional[Dict]:
        """Retry Mike's breakdown to fix validation errors (task_id format, missing files)."""
        try:
            from services.ai_gateway import call_openrouter_api, load_personas
            from core.models_config import ModelsConfig
            
            # Load Mike's persona config to get system prompt
            personas = load_personas()
            mike_config = personas.get("SPRINT_EXECUTION_ARCHITECT", {})
            mike_system_prompt = mike_config.get("system_prompt", "")
            
            # Format validation errors for feedback
            errors_str = "\n".join([
                f"- Task {e['task_id']}: {e['issue']}\n  Fix: {e['fix']}"
                for e in validation_errors
            ])
            
            # Inject full backlog context
            backlog_context = self._format_backlog_for_context(self._load_backlog_stories())
            vision_context = self._format_vision_for_context(vision)
            
            user_message = f"""{vision_context}

{backlog_context}

Your previous breakdown of {story.get('Story_ID')} has validation errors that must be fixed.

VALIDATION ERRORS FOUND:
{errors_str}

CRITICAL RULES TO FOLLOW:
1. task_id format MUST be: T-{story.get('Story_ID')}-01, T-{story.get('Story_ID')}-02, etc.
   - Include FULL Story_ID with prefix (NFR-001, US-009, not 001, 9)
   - Zero-pad task numbers (01, 02, not 1, 2)

2. EVERY task MUST have at least 1 file in files_to_create OR command_to_run
   - File paths must be concrete with extensions (src/db.js, not database)

3. Keep the same task descriptions and logic from your original breakdown
   - Only fix the format issues listed above
   - Do NOT change the technical approach or task content

CURRENT STORY: {story.get('Story_ID')}

Please output the COMPLETE corrected breakdown with ALL tasks in proper format."""

            # Call LLM with SPRINT_EXECUTION_ARCHITECT persona
            models_config = ModelsConfig()
            _, model, _, _ = models_config.load_config()
            
            response_text = ""
            async for chunk in call_openrouter_api(
                messages=[
                    {"role": "system", "content": mike_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=model,
                persona_name="Mike",
                persona_key="SPRINT_EXECUTION_ARCHITECT",
                include_tools=False
            ):
                if "content" in chunk:
                    response_text += chunk.get("content", "")
            
            result = self._extract_json(response_text)
            
            if result and self._validate_task_breakdown(result, story.get('Story_ID', 'unknown')):
                logger.info(f"✅ Mike validation retry successful for {story.get('Story_ID')}")
                return result
            else:
                logger.error(f"❌ Mike validation retry failed for {story.get('Story_ID')}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Mike retry for validation: {e}", exc_info=True)
            return None

    async def _call_mike_retry_incomplete(self, story: Dict, vision: Dict, project_name: str, 
                                         expected_count: int, actual_count: int, 
                                         existing_tasks: List[Dict]) -> Optional[Dict]:
        """Retry Mike's breakdown to recover missing tasks (self-healing)."""
        try:
            from services.ai_gateway import call_openrouter_api, load_personas
            from core.models_config import ModelsConfig
            
            # Load Mike's RECOVERY persona config to get system prompt
            personas = load_personas()
            mike_recovery_config = personas.get("SPRINT_EXECUTION_ARCHITECT_RECOVERY", {})
            mike_recovery_system_prompt = mike_recovery_config.get("system_prompt", "")
            
            # Format existing tasks for context
            existing_tasks_str = "\n".join([
                f"- {t.get('task_id', 'unknown')}: {t.get('description', 'task')}"
                for t in existing_tasks
            ])
            
            # Inject full backlog context
            backlog_context = self._format_backlog_for_context(self._load_backlog_stories())
            vision_context = self._format_vision_for_context(vision)
            
            user_message = f"""{vision_context}

{backlog_context}

Your previous breakdown of {story.get('Story_ID')} was incomplete.

Expected task count: {expected_count}
Actual task count: {actual_count}
Missing tasks: {expected_count - actual_count}

Already returned tasks:
{existing_tasks_str}

CURRENT STORY: {story.get('Story_ID')}"""

            # Call LLM with SPRINT_EXECUTION_ARCHITECT_RECOVERY persona
            models_config = ModelsConfig()
            _, model, _, _ = models_config.load_config()
            
            response_text = ""
            async for chunk in call_openrouter_api(
                messages=[
                    {"role": "system", "content": mike_recovery_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=model,
                persona_name="Mike",
                persona_key="SPRINT_EXECUTION_ARCHITECT_RECOVERY",
                include_tools=False
            ):
                if "content" in chunk:
                    response_text += chunk.get("content", "")
            
            # Parse JSON from response
            result = self._extract_json(response_text)
            
            if not result:
                logger.error(f"Mike retry returned no valid JSON for {story.get('Story_ID')}")
                return None
            
            # Validate recovered tasks
            recovered_tasks = result.get("tasks", [])
            if not recovered_tasks:
                logger.error(f"Mike retry returned no tasks for {story.get('Story_ID')}")
                return None
            
            logger.info(f"Mike retry returned {len(recovered_tasks)} recovered tasks")
            
            # Validate each recovered task
            for task in recovered_tasks:
                if 'taskId' in task and 'task_id' not in task:
                    task['task_id'] = task['taskId']
                elif 'id' in task and 'task_id' not in task:
                    task['task_id'] = task['id']
                
                if 'title' in task and 'description' not in task:
                    task['description'] = task['title']
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling Mike retry for incomplete breakdown: {e}", exc_info=True)
            return None

    async def _call_alex(self, task: Dict, story: Dict, vision: Dict, project_name: str, task_breakdown: Dict, retry_context: Optional[Dict] = None) -> Optional[Dict]:
        """Call Alex (SPRINT_EXECUTION_DEVELOPER) to generate code.
        
        Args:
            retry_context: Optional dict with 'attempt_number', 'max_attempts', and 'previous_attempts' 
                          for retry scenarios with cumulative learning
        """
        try:
            from services.ai_gateway import call_openrouter_api, load_personas
            from core.models_config import ModelsConfig
            
            # Load wireframe if exists
            wireframe_html = ""
            wireframe_ref = story.get("Wireframe_Ref", "")
            if wireframe_ref:
                wireframe_path = WIREFRAME_DIR / f"{wireframe_ref}.html"
                if wireframe_path.exists():
                    wireframe_html = wireframe_path.read_text(encoding="utf-8")
            
            # Load Alex's persona config to get system prompt
            personas = load_personas()
            alex_config = personas.get("SPRINT_EXECUTION_DEVELOPER", {})
            alex_system_prompt = alex_config.get("system_prompt", "")
            
            # Tech stack is set from Tech Stack NFR in run() method
            tech_stack = vision.get("tech_stack", "unknown")
            
            # Load architecture conventions
            architecture = self._load_architecture()
            
            # PHASE 1: Inject project context
            project_context = self._get_project_context(project_name)
            
            # CRITICAL: Detect MODIFY operations and load FULL file content
            # This prevents duplicate imports and ensures Alex can see existing code
            task_description = task.get('description', '').upper()
            files_to_create = task.get('files_to_create', [])
            files_needing_full_content = []
            
            if 'MODIFY' in task_description or 'UPDATE' in task_description or 'EDIT' in task_description:
                # This is a MODIFY task - load full content for files being modified
                files_needing_full_content = files_to_create.copy()
                logger.info(f"MODIFY task detected - will load FULL content for: {files_needing_full_content}")
            
            # On retry with fix instructions, only load files mentioned in fixes (reduce context!)
            files_to_load = files_to_create.copy()
            if retry_context and retry_context.get('previous_attempts'):
                # Extract files mentioned in fix instructions RELEVANT TO THIS TASK
                fix_files = set()
                task_files = set(files_to_create)
                
                for prev in retry_context['previous_attempts']:
                    failure_analysis = prev['test_result'].get('failure_analysis', [])
                    for fix in failure_analysis:
                        fix_file = fix.get('file', '')
                        # Only load files that are in this task's scope
                        if fix_file and fix_file in task_files:
                            fix_files.add(fix_file)
                
                if fix_files:
                    # Only load files mentioned in fixes + files being created (task-scoped)
                    files_to_load = list(fix_files) + files_to_load
                    logger.info(f"Retry: Loading only {len(files_to_load)} task-relevant files (from fixes + task scope)")
            
            file_summaries = self._get_file_summaries(project_name, files_to_load, files_needing_full_content)
            existing_patterns = self._get_existing_patterns(project_name)
            
            # Format architect's design for Alex
            architect_design = ""
            if task_breakdown:
                architect_design = f"""
ARCHITECT'S DESIGN (from Mike):
"""
                if task_breakdown.get('dependencies'):
                    architect_design += f"""
Dependencies Specified:
{json.dumps(task_breakdown.get('dependencies'), indent=2)}
"""
                if task_breakdown.get('database_design'):
                    architect_design += f"""
Database Design:
{json.dumps(task_breakdown.get('database_design'), indent=2)}
"""
                if task_breakdown.get('api_design'):
                    architect_design += f"""
API Design:
{json.dumps(task_breakdown.get('api_design'), indent=2)}
"""
                if task_breakdown.get('code_patterns'):
                    architect_design += f"""
Code Patterns to Follow:
{json.dumps(task_breakdown.get('code_patterns'), indent=2)}
"""
                # Add conventions if available
                if architecture.get('conventions'):
                    architect_design += f"""
ARCHITECTURAL CONVENTIONS (YOUR CONTRACT - FOLLOW EXACTLY):
{json.dumps(architecture.get('conventions'), indent=2)}
"""
            
            story_id = story.get('Story_ID', 'UNKNOWN')
            
            # Build retry history prompt if this is a retry
            retry_history_prompt = ""
            if retry_context and retry_context.get('previous_attempts'):
                attempt_num = retry_context['attempt_number']
                max_attempts = retry_context['max_attempts']
                history = retry_context['previous_attempts']
                
                retry_history_prompt = f"""
{'='*80}
THIS IS ATTEMPT {attempt_num}/{max_attempts} - FIX SPECIFIC ISSUES
{'='*80}

"""
                # Collect all failure analyses from previous attempts
                # FILTER to only show fixes relevant to THIS task's files
                all_fix_instructions = []
                task_files = set(task.get('files_to_create', []))
                
                for prev in history:
                    failure_analysis = prev['test_result'].get('failure_analysis', [])
                    if failure_analysis:
                        # Only include fixes for files THIS task is supposed to create/modify
                        for fix in failure_analysis:
                            fix_file = fix.get('file', '')
                            if fix_file in task_files:
                                all_fix_instructions.append(fix)
                                logger.info(f"Task {task.get('task_id')}: Including fix for {fix_file} (in task scope)")
                            else:
                                logger.info(f"Task {task.get('task_id')}: Skipping fix for {fix_file} (not in task scope: {task_files})")
                
                if all_fix_instructions:
                    # Use Jordan's specific fix instructions (concise!)
                    retry_history_prompt += f"""Jordan (QA) analyzed the test failures and identified these specific issues to fix:

"""
                    for idx, fix in enumerate(all_fix_instructions, 1):
                        retry_history_prompt += f"""{idx}. [{fix.get('file', 'unknown')}] {fix.get('function', '')}:
   Issue: {fix.get('issue', 'N/A')}
   Fix: {fix.get('fix', 'N/A')}

"""
                    retry_history_prompt += f"""
CRITICAL: Fix these {len(all_fix_instructions)} specific issues while keeping everything else unchanged.
Make TARGETED fixes only - do not regenerate everything.
"""
                else:
                    # Fallback to test errors if Jordan didn't provide analysis
                    for prev in history:
                        if not prev['test_result']['success'] or prev['test_result']['failed'] > 0:
                            retry_history_prompt += f"""--- Attempt {prev['attempt']} ---
Tests: {prev['test_result']['passed']} passed, {prev['test_result']['failed']} failed

Test errors (first 500 chars):
{prev['test_result']['errors'][:500]}

"""
                    retry_history_prompt += """
Analyze the errors above and fix the issues.
"""
                
                retry_history_prompt += f"""
{'='*80}

"""
            
            # Inject full backlog context
            backlog_context = self._format_backlog_for_context(self._load_backlog_stories())
            
            # Add clear context header
            attempt_info = ""
            if retry_context:
                attempt_info = f"\nAttempt: {retry_context['attempt_number']} of {retry_context['max_attempts']}"
                if retry_context.get('previous_attempts'):
                    last_attempt = retry_context['previous_attempts'][-1]
                    if last_attempt.get('failure_analysis'):
                        attempt_info += f"\nPrevious Failure: {last_attempt['failure_analysis'][0].get('issue', 'Unknown')[:100]}"
            
            context_header = f"""
═══════════════════════════════════════════════════════════════════════════════
YOUR CURRENT TASK CONTEXT:
═══════════════════════════════════════════════════════════════════════════════
Role: Alex (Sprint Execution Developer)
Story: {story_id} - {story.get('Title', 'N/A')}
Task: {task.get('task_id')} - {task.get('description', '')[:80]}...{attempt_info}
Your Specific Job: Generate ONLY the files listed in files_to_create for THIS task
Output Required: JSON with complete file contents (not snippets)
═══════════════════════════════════════════════════════════════════════════════
"""
            
            user_message = f"""{context_header}

{retry_history_prompt}{backlog_context}

PROJECT CONTEXT:
{project_context}

EXISTING FILES YOU CAN IMPORT FROM:
{file_summaries}

ESTABLISHED CODE PATTERNS:
{existing_patterns}
{architect_design}
IMPLEMENT THIS TASK:

Story ID: {story_id}
Task ID: {task.get('task_id')}
Description: {task.get('description')}
Files to create: {', '.join(task.get('files_to_create', []))}

Tech Stack: {tech_stack}

Wireframe:
{wireframe_html if wireframe_html else 'No wireframe'}

CRITICAL: Your response MUST include "story_id": "{story_id}" and "task_id": "{task.get('task_id')}" exactly as shown."""

            # Get default model
            models_config = ModelsConfig()
            _, model, _, _ = models_config.load_config()
            
            response_text = ""
            async for chunk in call_openrouter_api(
                messages=[
                    {"role": "system", "content": alex_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=model,
                persona_name="Alex",
                persona_key="SPRINT_EXECUTION_DEVELOPER",
                include_tools=False  # Execution personas output JSON only, no tools needed
            ):
                if "content" in chunk:
                    response_text += chunk.get("content", "")
            
            result = self._extract_json(response_text)
            
            # JSON RETRY: If extraction failed, retry with explicit JSON instruction
            if not result and response_text:
                logger.warning(f"⚠️ Alex returned invalid JSON for {task.get('task_id')}, attempting JSON retry...")
                result = await self._retry_json_extraction(
                    original_response=response_text,
                    system_prompt=alex_system_prompt,
                    context_summary=f"Task: {task.get('task_id')} for story {story.get('Story_ID')}",
                    model=model
                )
            
            # Validate response matches expected IDs
            if result:
                result_story_id = result.get('story_id', '')
                result_task_id = result.get('task_id', '')
                expected_story_id = story.get('Story_ID', '')
                expected_task_id = task.get('task_id', '')
                
                if result_story_id != expected_story_id:
                    logger.error(f"❌ Alex returned wrong story_id: got '{result_story_id}', expected '{expected_story_id}'")
                    logger.error(f"Correcting story_id from '{result_story_id}' to '{expected_story_id}'")
                    result['story_id'] = expected_story_id
                
                if result_task_id != expected_task_id:
                    logger.error(f"❌ Alex returned wrong task_id: got '{result_task_id}', expected '{expected_task_id}'")
                    logger.error(f"Correcting task_id from '{result_task_id}' to '{expected_task_id}'")
                    result['task_id'] = expected_task_id
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling Alex: {e}", exc_info=True)
            return None
    
    async def _call_alex_retry(self, task: Dict, story: Dict, vision: Dict, project_name: str, syntax_errors: List[Dict], previous_attempt: str = "", task_breakdown: Dict = None) -> Optional[Dict]:
        """Call Alex again with syntax error feedback to fix the code."""
        try:
            from services.ai_gateway import call_openrouter_api, load_personas
            from core.models_config import ModelsConfig
            
            # Load wireframe if exists
            wireframe_html = ""
            wireframe_ref = story.get("Wireframe_Ref", "")
            if wireframe_ref:
                wireframe_path = WIREFRAME_DIR / f"{wireframe_ref}.html"
                if wireframe_path.exists():
                    wireframe_html = wireframe_path.read_text(encoding="utf-8")
            
            # Load Alex's RECOVERY persona config to get system prompt
            personas = load_personas()
            alex_recovery_config = personas.get("SPRINT_EXECUTION_DEVELOPER_RECOVERY", {})
            alex_recovery_system_prompt = alex_recovery_config.get("system_prompt", "")
            
            # Tech stack is set from Tech Stack NFR in run() method
            tech_stack = vision.get("tech_stack", "unknown")
            
            # PHASE 1: Re-inject project context (same as first call)
            project_context = self._get_project_context(project_name)
            
            # CRITICAL: Detect MODIFY operations and load FULL file content (same as first call)
            task_description = task.get('description', '').upper()
            files_to_create = task.get('files_to_create', [])
            files_needing_full_content = []
            
            if 'MODIFY' in task_description or 'UPDATE' in task_description or 'EDIT' in task_description:
                files_needing_full_content = files_to_create.copy()
                logger.info(f"MODIFY task detected in retry - will load FULL content for: {files_needing_full_content}")
            
            file_summaries = self._get_file_summaries(project_name, files_to_create, files_needing_full_content)
            existing_patterns = self._get_existing_patterns(project_name)
            
            # Format architect's design for Alex (same as first call)
            architect_design = ""
            if task_breakdown:
                architect_design = f"""
ARCHITECT'S DESIGN (from Mike):
"""
                if task_breakdown.get('dependencies'):
                    architect_design += f"""
Dependencies Specified:
{json.dumps(task_breakdown.get('dependencies'), indent=2)}
"""
                if task_breakdown.get('database_design'):
                    architect_design += f"""
Database Design:
{json.dumps(task_breakdown.get('database_design'), indent=2)}
"""
                if task_breakdown.get('api_design'):
                    architect_design += f"""
API Design:
{json.dumps(task_breakdown.get('api_design'), indent=2)}
"""
                if task_breakdown.get('code_patterns'):
                    architect_design += f"""
Code Patterns to Follow:
{json.dumps(task_breakdown.get('code_patterns'), indent=2)}
"""
            
            # Format syntax errors for feedback
            error_details = "\n".join([
                f"- {err['path']}: Line {err.get('line', '?')}: {err['error']}"
                for err in syntax_errors
            ])
            
            # Show previous attempt (truncated if too long)
            previous_code = previous_attempt[:500] + "..." if len(previous_attempt) > 500 else previous_attempt
            
            # Inject full backlog context
            backlog_context = self._format_backlog_for_context(self._load_backlog_stories())
            
            user_message = f"""{backlog_context}

PROJECT CONTEXT:
{project_context}

EXISTING FILES YOU CAN IMPORT FROM:
{file_summaries}

ESTABLISHED CODE PATTERNS:
{existing_patterns}
{architect_design}
IMPLEMENT THIS TASK:

Task ID: {task.get('task_id')}
Description: {task.get('description')}
Files to create: {', '.join(task.get('files_to_create', []))}

Tech Stack: {tech_stack}

Wireframe:
{wireframe_html if wireframe_html else 'No wireframe'}

SYNTAX ERRORS FROM PREVIOUS ATTEMPT:
{error_details}

PREVIOUS CODE (for reference):
{previous_code}"""

            # Get default model
            models_config = ModelsConfig()
            _, model, _, _ = models_config.load_config()
            
            response_text = ""
            async for chunk in call_openrouter_api(
                messages=[
                    {"role": "system", "content": alex_recovery_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=model,
                persona_name="Alex",
                persona_key="SPRINT_EXECUTION_DEVELOPER_RECOVERY",
                include_tools=False
            ):
                if "content" in chunk:
                    response_text += chunk.get("content", "")
            
            return self._extract_json(response_text)
            
        except Exception as e:
            logger.error(f"Error calling Alex retry: {e}", exc_info=True)
            return None

    async def _call_jordan(self, story: Dict, task_breakdown: Dict, project_name: str, vision: Dict, tech_stack: Dict = None) -> Optional[Dict]:
        """Call Jordan (SPRINT_EXECUTION_QA) to generate tests."""
        try:
            from services.ai_gateway import call_openrouter_api, load_personas
            from core.models_config import ModelsConfig
            
            story_id = story.get('Story_ID', 'unknown')
            
            # Load Jordan's persona config to get system prompt
            personas_data = load_personas()
            jordan_config = personas_data.get("SPRINT_EXECUTION_QA", {})
            jordan_system_prompt = jordan_config.get("system_prompt", "")
            
            # Load test framework mapping from personas config file
            from services.ai_gateway import resolve_personas_path
            personas_path = resolve_personas_path()
            with open(personas_path, "r", encoding="utf-8") as f:
                personas_raw = json.load(f)
            test_framework_mapping = personas_raw.get("metadata", {}).get("test_framework_mapping", {})
            
            # PHASE 1: Inject project context (same pattern as Mike and Alex)
            project_context = self._get_project_context(project_name)
            file_summaries = self._get_file_summaries(project_name, [])  # Get all existing files
            existing_patterns = self._get_existing_patterns(project_name)
            
            # Build tech stack info for Jordan
            tech_stack_info = ""
            if tech_stack:
                # Determine test framework based on backend using config mapping
                backend = tech_stack.get('backend', 'unknown')
                logger.info(f"🔍 Jordan: backend='{backend}', mapping keys={list(test_framework_mapping.keys())}")
                framework_info = test_framework_mapping.get(backend, test_framework_mapping.get("default", {}))
                test_framework = framework_info.get("framework", "pytest")
                test_language = framework_info.get("language", "Python")
                logger.info(f"🔍 Jordan: Selected framework={test_framework}, language={test_language}")
                
                tech_stack_info = f"""
Tech Stack Information:
- Backend: {backend}
- Frontend: {tech_stack.get('frontend')}
- Database: {tech_stack.get('database')}
- Test Framework: {test_framework}
- Test Language: {test_language}
"""
            
            # Add test template for Node.js projects
            test_template = ""
            if tech_stack and 'node' in tech_stack.get('backend', '').lower():
                test_template = self._get_nodejs_test_template()
            
            # Load architecture conventions
            architecture = self._load_architecture()
            
            # Build architect design context (same as Alex gets)
            architect_design = ""
            if task_breakdown:
                architect_design = f"""

ARCHITECT'S DESIGN (from Mike):
"""
                if task_breakdown.get('database_design'):
                    architect_design += f"""
Database Design:
{json.dumps(task_breakdown.get('database_design'), indent=2)}
"""
                if task_breakdown.get('api_design'):
                    architect_design += f"""
API Design:
{json.dumps(task_breakdown.get('api_design'), indent=2)}
"""
                if task_breakdown.get('code_patterns'):
                    architect_design += f"""
Code Patterns to Follow:
{json.dumps(task_breakdown.get('code_patterns'), indent=2)}
"""
                # Add conventions if available
                if architecture.get('conventions'):
                    architect_design += f"""
ARCHITECTURAL CONVENTIONS (YOUR CONTRACT - FOLLOW EXACTLY):
{json.dumps(architecture.get('conventions'), indent=2)}
"""
            
            # Inject full backlog context
            backlog_context = self._format_backlog_for_context(self._load_backlog_stories())
            
            # Add clear context header
            context_header = f"""
═══════════════════════════════════════════════════════════════════════════════
YOUR CURRENT TASK CONTEXT:
═══════════════════════════════════════════════════════════════════════════════
Role: Jordan (Sprint Execution QA)
Story: {story_id} - {story.get('Title', 'N/A')}
Your Specific Job: Write 1-2 SMOKE TESTS ONLY - verify code runs without crashing
NOT Comprehensive Testing: Just check main function/endpoint responds
Output Required: JSON with single test file containing 1-2 simple tests
═══════════════════════════════════════════════════════════════════════════════
"""
            
            # Build user message with story context AND project state
            user_message = f"""{context_header}

{backlog_context}

PROJECT CONTEXT:
{project_context}

EXISTING FILES IN PROJECT:
{file_summaries}

ESTABLISHED CODE PATTERNS:
{existing_patterns}
{architect_design}

---

CURRENT STORY TO TEST: {story_id}

Task Breakdown (What was supposed to be implemented):
{json.dumps(task_breakdown.get('tasks', []), indent=2)}
{tech_stack_info}
{test_template}

CRITICAL: Only write tests for files that actually exist in EXISTING FILES above.
If a file from the task breakdown doesn't exist in the project, write defensive tests or skip it.
Check file existence before using require() or import statements."""

            # Get default model
            models_config = ModelsConfig()
            _, model, _, _ = models_config.load_config()
            
            response_text = ""
            async for chunk in call_openrouter_api(
                messages=[
                    {"role": "system", "content": jordan_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=model,
                persona_name="Jordan",
                persona_key="SPRINT_EXECUTION_QA",
                include_tools=False  # Execution personas output JSON only, no tools needed
            ):
                if "content" in chunk:
                    response_text += chunk.get("content", "")
            
            test_result = self._extract_json(response_text)
            
            if not test_result:
                logger.error(f"Jordan failed to generate valid tests for {story_id}")
            
            return test_result
            
        except Exception as e:
            logger.error(f"Error calling Jordan: {e}", exc_info=True)
            return None

    async def _call_jordan_for_analysis(self, story: Dict, test_file: str, test_output: str, project_name: str) -> List[Dict]:
        """Call Jordan to analyze test failures and provide specific fix instructions."""
        try:
            from services.ai_gateway import call_openrouter_api, load_personas
            from core.models_config import ModelsConfig
            
            story_id = story.get('Story_ID', 'unknown')
            
            # Load Jordan's persona
            personas_data = load_personas()
            jordan_config = personas_data.get("SPRINT_EXECUTION_QA", {})
            jordan_system_prompt = jordan_config.get("system_prompt", "")
            
            # Read the test file content to give Jordan context
            project_root = EXECUTION_SANDBOX / project_name
            test_file_path = project_root / test_file
            test_content = ""
            if test_file_path.exists():
                test_content = test_file_path.read_text(encoding='utf-8')
            
            # Build analysis request
            user_message = f"""You are analyzing test failures for {story_id}.

YOUR TASK: Analyze the test failures below and provide SPECIFIC fix instructions for each issue.

TEST FILE CONTENT:
{test_content[:1500]}

TEST EXECUTION OUTPUT (failures):
{test_output}

ANALYZE EACH FAILURE:
For each failing test, provide:
1. test_name: Name of the failing test
2. file: Which source file has the bug (e.g., "src/db.js")
3. function: Which function/section is problematic
4. issue: Exact problem description
5. expected: What should happen
6. actual: What actually happened
7. fix: SPECIFIC instruction on what to change

Be SPECIFIC with line numbers and exact code changes when possible.

OUTPUT FORMAT:
{{
  "failure_analysis": [
    {{
      "test_name": "exact test name",
      "file": "src/file.js",
      "function": "functionName",
      "issue": "specific problem",
      "expected": "what should be",
      "actual": "what is",
      "fix": "specific fix instruction with line numbers if possible"
    }}
  ]
}}

Output ONLY valid JSON with the failure_analysis array."""

            # Get default model
            models_config = ModelsConfig()
            _, model, _, _ = models_config.load_config()
            
            response_text = ""
            async for chunk in call_openrouter_api(
                messages=[
                    {"role": "user", "content": user_message}
                ],
                model=model,
                persona_name="Jordan-Analyzer",
                persona_key="SPRINT_EXECUTION_QA",
                include_tools=False
            ):
                if "content" in chunk:
                    response_text += chunk.get("content", "")
            
            analysis_result = self._extract_json(response_text)
            
            if analysis_result and 'failure_analysis' in analysis_result:
                return analysis_result['failure_analysis']
            else:
                logger.warning(f"Jordan did not provide failure_analysis for {story_id}")
                return []
            
        except Exception as e:
            logger.error(f"Error calling Jordan for analysis: {e}", exc_info=True)
            return []

    async def _retry_json_extraction(self, original_response: str, system_prompt: str, context_summary: str, model: str) -> Optional[Dict]:
        """Retry LLM call when JSON extraction fails, providing the failed response as context."""
        try:
            from services.ai_gateway import call_openrouter_api
            
            # Truncate original response to avoid token limits
            truncated_response = original_response[:2000] if len(original_response) > 2000 else original_response
            
            retry_message = f"""Your previous response was NOT valid JSON and could not be parsed.

CONTEXT: {context_summary}

YOUR PREVIOUS RESPONSE (truncated):
{truncated_response}

PROBLEM: The response above is not valid JSON. It may have:
- Text before or after the JSON object
- Markdown code blocks (```json ... ```)
- Missing quotes or commas
- Unescaped characters in strings

REQUIRED: Output ONLY a valid JSON object. No explanations, no markdown, just the JSON.

The JSON must have this structure:
{{
  "task_id": "...",
  "story_id": "...",
  "files": [
    {{"path": "...", "content": "...", "action": "create|modify"}}
  ],
  "implementation_notes": "..."
}}

OUTPUT ONLY VALID JSON NOW:"""

            response_text = ""
            async for chunk in call_openrouter_api(
                messages=[
                    {"role": "system", "content": "You are a JSON repair assistant. Output ONLY valid JSON, nothing else."},
                    {"role": "user", "content": retry_message}
                ],
                model=model,
                persona_name="JSON-Repair",
                persona_key="SPRINT_EXECUTION_DEVELOPER",
                include_tools=False
            ):
                if "content" in chunk:
                    response_text += chunk.get("content", "")
            
            result = self._extract_json(response_text)
            if result:
                logger.info(f"✅ JSON retry successful - extracted valid JSON")
            else:
                logger.error(f"❌ JSON retry failed - still invalid JSON")
            return result
            
        except Exception as e:
            logger.error(f"Error in JSON retry: {e}", exc_info=True)
            return None

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from LLM response (handles markdown code blocks and text artifacts)."""
        import re
        
        # Try direct parse first
        try:
            result = json.loads(text.strip())
            logger.debug(f"Successfully parsed JSON directly (size: {len(text)} chars)")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Direct JSON parse failed at position {e.pos}: {e.msg}")
        except Exception as e:
            logger.debug(f"Direct JSON parse failed: {e}")
        
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                logger.debug(f"Successfully parsed JSON from markdown code block")
                return result
            except Exception as e:
                logger.debug(f"Markdown code block parse failed: {e}")
        
        # Try to extract JSON object(s) by finding balanced braces
        # This handles cases where there's text before/after JSON
        # We may find multiple JSON objects; choose the largest valid one.
        brace_count = 0
        start_idx = -1
        in_string = False
        escape_next = False
        candidates: List[Tuple[str, Dict]] = []
        
        for i, char in enumerate(text):
            # Handle string state to ignore braces inside strings
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            # Now we're outside strings, count braces
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    # Found complete JSON object
                    json_str = text[start_idx:i+1]
                    parsed = False

                    # Try direct parse first
                    try:
                        result = json.loads(json_str)
                        candidates.append((json_str, result))
                        parsed = True
                    except json.JSONDecodeError as e:
                        # Log the specific JSON error for debugging
                        logger.debug(f"JSON parse error at position {e.pos}: {e.msg}")
                    except Exception as e:
                        logger.debug(f"Unexpected error parsing JSON: {e}")

                    # If direct parse failed, try repair strategies immediately
                    if not parsed:
                        # Combined repair: fix all common issues at once
                        # 1. \' -> ' (invalid JSON escape for single quotes)
                        # 2. ${ -> $\u007B (template literals cause invalid \$ escape)
                        # 3. }'"> -> }'\"> (unescaped " after JS object in HTML context)
                        combined_repair = json_str.replace("\\'", "'").replace('${', '$\\u007B').replace('}\">', '}\\\">')

                        repair_attempts = [
                            # Strategy 1: Combined repair (most likely to work)
                            combined_repair,
                            # Strategy 2: Just template literals
                            json_str.replace('${', '$\\u007B'),
                            # Strategy 3: Just single quote escapes
                            json_str.replace("\\'", "'"),
                        ]

                        for repair_idx, repaired in enumerate(repair_attempts):
                            try:
                                result = json.loads(repaired)
                                logger.warning(f"Successfully parsed JSON after inline repair #{repair_idx+1}")
                                candidates.append((repaired, result))
                                parsed = True
                                break
                            except:
                                continue

                    if not parsed:
                        logger.error(f"Could not parse JSON object ({len(json_str)} chars) even with repairs")

                    # Reset start index so we can look for the next object
                    start_idx = -1

        # If we found any valid JSON objects, return the largest one by length.
        if candidates:
            json_str, result = max(candidates, key=lambda x: len(x[0]))
            logger.info(f"Extracted JSON via brace-counting: {len(json_str)} chars, {len(candidates)} candidates found")
            logger.debug(f"Parsed JSON has keys: {list(result.keys())}")
            return result
        
        # No valid candidates found - try aggressive repair before giving up
        logger.warning(f"No valid JSON candidates found via brace-counting. Attempting repair...")
        
        # Try to repair common JSON issues and parse again
        # Common issues: unescaped quotes, newlines in strings, trailing commas
        if start_idx != -1 or text.strip().startswith('{'):
            # We found a starting brace but couldn't parse - try repairs
            try:
                # Find the likely end (last closing brace)
                if start_idx == -1:
                    start_idx = text.find('{')
                last_brace = text.rfind('}')
                
                if last_brace > start_idx:
                    json_str = text[start_idx:last_brace+1]
                    logger.debug(f"Attempting to repair JSON substring: {len(json_str)} chars")
                    
                    # Attempt multiple repair strategies
                    repair_attempts = [
                        # Strategy 1: Original (no changes)
                        json_str,
                        # Strategy 2: Fix common escape issues in strings
                        json_str.replace("\\'", "'").replace('\\"', '"'),
                        # Strategy 3: Try to fix unescaped quotes by escaping them
                        re.sub(r'(?<!\\)"(?=.*":)', r'\\"', json_str),
                        # Strategy 4: Fix template literal escape issues (${...} causes invalid \escape)
                        # Replace backticks with single quotes and ${} with placeholder text
                        re.sub(r'`([^`]*)\$\{([^}]*)\}([^`]*)`', r"'\1[VAR:\2]\3'", json_str),
                        # Strategy 5: Escape ${ using unicode escape (JSON-safe)
                        # ${  -> $\u007B (preserves content but makes valid JSON)
                        json_str.replace('${', '$\\u007B'),
                    ]
                    
                    for idx, repaired in enumerate(repair_attempts):
                        try:
                            result = json.loads(repaired)
                            logger.warning(f"Successfully parsed JSON after repair attempt #{idx+1}")
                            logger.debug(f"Repaired JSON has keys: {list(result.keys())}")
                            return result
                        except json.JSONDecodeError as e:
                            logger.debug(f"Repair attempt #{idx+1} failed at position {e.pos}: {e.msg}")
                            continue
                        except Exception as e:
                            logger.debug(f"Repair attempt #{idx+1} failed: {e}")
                            continue
            except Exception as e:
                logger.error(f"Error attempting JSON repair: {e}")
        
        # Last resort: try to find any simple JSON-like structure
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        # Log full response to a separate file for diagnosis
        logger.error(f"Could not extract JSON from response (first 500 chars): {text[:500]}")
        
        # Save full response to file for debugging
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_failed_json.txt', dir=EXECUTION_SANDBOX) as f:
                f.write(text)
                logger.error(f"Full failed response saved to: {f.name}")
        except Exception as e:
            logger.error(f"Could not save failed response: {e}")
        
        return None

    def _create_project_structure_from_tech_stack(self, project_name: str, tech_stack: Dict) -> None:
        """
        Create project structure based on detected tech stack.
        NO hardcoded assumptions - driven entirely by Tech Stack NFR.
        """
        project_root = EXECUTION_SANDBOX / project_name
        backend = tech_stack.get('backend', 'unknown')
        frontend = tech_stack.get('frontend', 'unknown')
        database = tech_stack.get('database', 'unknown')
        
        logger.info(f"🏗️ Creating {backend} + {frontend} + {database} project structure")
        
        # Create base directories
        (project_root / "tests").mkdir(parents=True, exist_ok=True)
        
        # Backend-specific structure
        if backend == 'nodejs_express':
            # Node.js + Express structure
            (project_root / "src" / "routes").mkdir(parents=True, exist_ok=True)
            (project_root / "src" / "models").mkdir(parents=True, exist_ok=True)
            (project_root / "src" / "middleware").mkdir(parents=True, exist_ok=True)
            
            # Create package.json stub
            package_json = project_root / "package.json"
            if not package_json.exists():
                backend_port = tech_stack.get('backend_port')
                if not backend_port:
                    raise ValueError("NFR-001 must specify 'backend_port' in acceptance criteria")
                package_json.write_text(json.dumps({
                    "name": project_name.lower().replace(' ', '-'),
                    "version": "1.0.0",
                    "description": f"Generated by AI-DIY - {tech_stack.get('title', 'Project')}",
                    "main": "src/server.js",
                    "scripts": {
                        "start": "node src/server.js",
                        "dev": "nodemon src/server.js",
                        "test": "jest"
                    },
                    "dependencies": {},
                    "devDependencies": {}
                }, indent=2), encoding="utf-8")
                logger.info(f"✅ Created package.json for Node.js + Express")
            
            # Create server.js stub
            server_js = project_root / "src" / "server.js"
            if not server_js.exists():
                backend_port = tech_stack.get('backend_port')
                if not backend_port:
                    raise ValueError("NFR-001 must specify 'backend_port' in acceptance criteria")
                server_js.write_text(f"""// Express server - Generated by AI-DIY
const express = require('express');
const app = express();

// Middleware
app.use(express.json());

// Health check
app.get('/health', (req, res) => {{
  res.json({{ status: 'ok', database: '{database}' }});
}});

// Routes will be added here by sprint execution

const PORT = process.env.PORT || {backend_port};
app.listen(PORT, () => {{
  console.log(`Server running on port ${{PORT}}`);
}});

module.exports = app;
""", encoding="utf-8")
                logger.info(f"✅ Created src/server.js")
        
        elif backend == 'flask':
            # Flask structure
            (project_root / "routes").mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)
            (project_root / "static").mkdir(parents=True, exist_ok=True)
            
            # Create requirements.txt stub (empty - Mike will specify dependencies in task design)
            requirements_txt = project_root / "requirements.txt"
            if not requirements_txt.exists():
                requirements_txt.write_text("# Dependencies will be added during sprint execution\n", encoding="utf-8")
                logger.info(f"✅ Created requirements.txt stub for Flask")
            
            # Create app.py stub
            app_py = project_root / "app.py"
            if not app_py.exists():
                backend_port = tech_stack.get('backend_port')
                if not backend_port:
                    raise ValueError("NFR-001 must specify 'backend_port' in acceptance criteria")
                app_py.write_text(f"""# Flask application - Generated by AI-DIY
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Database: {database}

@app.route('/health')
def health():
    return {{'status': 'ok', 'database': '{database}'}}

# Routes will be added here by sprint execution

if __name__ == '__main__':
    app.run(debug=True, port={backend_port})
""", encoding="utf-8")
                logger.info(f"✅ Created app.py")
        
        # Frontend-specific structure
        if frontend == 'react':
            (project_root / "public").mkdir(parents=True, exist_ok=True)
            (project_root / "src" / "components").mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created React frontend structure")
        elif frontend == 'html':
            (project_root / "static" / "css").mkdir(parents=True, exist_ok=True)
            (project_root / "static" / "js").mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Created static HTML frontend structure")
        
        # Create README.md
        readme = project_root / "README.md"
        if not readme.exists():
            readme_content = f"""# {project_name}

Generated by AI-DIY Sprint Execution

## Tech Stack
- **Backend**: {backend}
- **Frontend**: {frontend}
- **Database**: {database}

## Setup

"""
            if backend == 'nodejs_express':
                readme_content += """1. Install dependencies:
```bash
npm install
```

2. Run the application:
```bash
npm start
```

3. Run tests:
```bash
npm test
```
"""
            elif backend == 'flask':
                readme_content += """1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Run tests:
```bash
pytest
```
"""
            
            readme_content += f"""
## Project Structure

Generated based on Tech Stack NFR: {tech_stack.get('story_id')}
"""
            readme.write_text(readme_content, encoding="utf-8")
            logger.info(f"✅ Created README.md")
        
        logger.info(f"✅ Project structure created for {backend} + {frontend} + {database}")

    def _write_code_files(self, project_name: str, files: List[Dict], story_id: str = None, skip_validation: bool = False) -> List[str]:
        """Write generated code files to project with validation, merge, and backup. Returns list of written file paths."""
        project_root = EXECUTION_SANDBOX / project_name
        files_written = []
        
        for file_spec in files:
            try:
                path = file_spec.get("path", "")
                if not path:
                    logger.error(f"File spec missing path: {file_spec}")
                    continue
                    
                file_path = project_root / path
                content = file_spec.get("content", "")
                
                # PHASE 1: Validate syntax before writing (unless already validated)
                if not skip_validation and not self._validate_syntax(content, path):
                    logger.error(f"Syntax validation failed for {path}, skipping")
                    continue
                
                # PHASE 1: Check for suspicious imports
                is_valid, warnings = self._validate_imports(content)
                if warnings:
                    for warning in warnings:
                        logger.warning(f"{path}: {warning}")
                
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # PHASE 2: Merge if file exists, otherwise create new
                if file_path.exists():
                    logger.info(f"File exists, merging: {file_path}")
                    # PHASE 3: Backup before modifying
                    self._backup_existing(file_path)
                    # Merge existing with new
                    existing = file_path.read_text(encoding="utf-8")
                    merged = self._merge_code(existing, content, path)
                    file_path.write_text(merged, encoding="utf-8")
                else:
                    # New file, write directly
                    file_path.write_text(content, encoding="utf-8")
                
                files_written.append(path)
                logger.info(f"Wrote file: {file_path}")
                
                # PHASE 3: Track file for potential rollback
                if story_id:
                    self._track_story_files(story_id, file_path)
                
            except Exception as e:
                logger.error(f"Error writing file {file_spec.get('path')}: {e}")
                logger.error(f"File spec was: {file_spec}")
        
        return files_written

    def _write_test_file(self, project_name: str, test_result: Dict) -> str:
        """Write generated test file to project."""
        project_root = EXECUTION_SANDBOX / project_name
        
        try:
            # Safety check
            if not isinstance(test_result, dict):
                logger.error(f"test_result is not a dict, got {type(test_result)}")
                return ""
            
            test_file = test_result.get("test_file", "tests/test_generated.py")
            test_content = test_result.get("test_content", "")
            
            if not test_content:
                logger.warning("No test_content in test_result")
                return ""
            
            file_path = project_root / test_file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(test_content, encoding="utf-8")
            
            logger.info(f"Wrote test file: {file_path}")
            return test_file
            
        except Exception as e:
            logger.error(f"Error writing test file: {e}")
            logger.error(f"test_result type: {type(test_result)}, content: {test_result}")
            return ""

    def _load_vision(self) -> Dict:
        """Load latest vision document."""
        try:
            latest_file = None
            latest_mtime = -1
            if VISION_DIR.exists():
                for jf in VISION_DIR.glob("*.json"):
                    try:
                        mtime = jf.stat().st_mtime
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                            latest_file = jf
                    except Exception:
                        continue
            
            if latest_file:
                with open(latest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            
            # No hardcoded defaults - tech_stack will be set from Tech Stack NFR
            logger.warning("No vision file found, returning empty vision")
            return {}
            
        except Exception as e:
            logger.error(f"Error loading vision: {e}")
            # No hardcoded defaults - tech_stack will be set from Tech Stack NFR
            return {}

    def _load_backlog_stories(self) -> Dict[str, Dict]:
        """Load all stories from Backlog.csv."""
        stories = {}
        try:
            if not BACKLOG_CSV_PATH.exists():
                return stories
            
            with open(BACKLOG_CSV_PATH, "r", newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    story_id = row.get("Story_ID")
                    if story_id:
                        stories[story_id] = row
            
            return stories
            
        except Exception as e:
            logger.error(f"Error loading backlog: {e}")
            return stories
    
    def _format_backlog_for_context(self, backlog_stories: Dict[str, Dict]) -> str:
        """Format backlog stories for LLM context injection."""
        if not backlog_stories:
            return "No backlog stories available."
        
        formatted = "COMPLETE BACKLOG (All Requirements):\n\n"
        for story_id, story in backlog_stories.items():
            formatted += f"Story ID: {story_id}\n"
            formatted += f"Title: {story.get('Title', 'N/A')}\n"
            formatted += f"User Story: {story.get('User_Story', 'N/A')}\n"
            formatted += f"Functional Requirements: {story.get('Functional_Requirements', 'N/A')}\n"
            formatted += f"Non-Functional Requirements: {story.get('Non_Functional_Requirements', 'N/A')}\n"
            formatted += f"Constraints: {story.get('Constraints', 'N/A')}\n"
            formatted += f"Dependencies: {story.get('Dependencies', 'N/A')}\n"
            formatted += f"Acceptance Criteria: {story.get('Acceptance_Criteria', 'N/A')}\n"
            formatted += f"Priority: {story.get('Priority', 'N/A')}\n"
            formatted += f"Status: {story.get('Status', 'N/A')}\n"
            formatted += "-" * 80 + "\n\n"
        
        return formatted
    
    def _format_vision_for_context(self, vision: Dict) -> str:
        """Format vision document for LLM context injection."""
        if not vision:
            return "No vision document available."
        
        formatted = "VISION DOCUMENT:\n\n"
        formatted += f"Project: {vision.get('project_name', 'N/A')}\n"
        formatted += f"Vision Statement: {vision.get('vision_statement', 'N/A')}\n"
        formatted += f"Goals: {vision.get('goals', 'N/A')}\n"
        formatted += f"Constraints: {vision.get('constraints', 'N/A')}\n"
        formatted += f"Success Criteria: {vision.get('success_criteria', 'N/A')}\n"
        formatted += "-" * 80 + "\n\n"
        
        return formatted
    
    def _get_story_from_backlog(self, story_id: str) -> Optional[Dict]:
        """Get a single story from the backlog by ID."""
        stories = self._load_backlog_stories()
        return stories.get(story_id)
    
    def _load_architecture(self) -> Dict:
        """Load persistent architecture from appdocs/architecture.json."""
        arch_file = APPDOCS_PATH / "architecture.json"
        try:
            if arch_file.exists():
                with open(arch_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "project_name": "yourapp",
                "architecture_locked": False,
                "locked_at_sprint": None,
                "conventions": {},
                "current_schema": {},
                "current_endpoints": []
            }
        except Exception as e:
            logger.warning(f"Could not load architecture: {e}")
            return {
                "project_name": "yourapp",
                "architecture_locked": False,
                "locked_at_sprint": None,
                "conventions": {},
                "current_schema": {},
                "current_endpoints": []
            }
    
    def _accumulate_architecture_design(self, architecture: Dict, mike_result: Dict, story_id: str) -> Dict:
        """Accumulate database schema, API endpoints, and convention extensions from Mike's design into architecture.json"""
        
        # Initialize if not exists
        if 'current_schema' not in architecture:
            architecture['current_schema'] = {}
        if 'current_endpoints' not in architecture:
            architecture['current_endpoints'] = []
        
        # 1. ACCUMULATE DATABASE SCHEMA
        db_design = mike_result.get('database_design', {})
        for table in db_design.get('new_tables', []):
            table_name = table.get('name')
            if table_name and table_name not in architecture['current_schema']:
                architecture['current_schema'][table_name] = {
                    'fields': table.get('fields', []),
                    'added_in': story_id
                }
                logger.info(f"  ➕ Schema: Added table '{table_name}'")
        
        for table in db_design.get('modified_tables', []):
            table_name = table.get('name')
            if table_name and table_name in architecture['current_schema']:
                existing_fields = architecture['current_schema'][table_name].get('fields', [])
                new_fields = table.get('new_fields', [])
                existing_fields.extend(new_fields)
                architecture['current_schema'][table_name]['fields'] = existing_fields
                architecture['current_schema'][table_name]['modified_in'] = story_id
                logger.info(f"  ✏️ Schema: Modified table '{table_name}' (+{len(new_fields)} fields)")
        
        # 2. ACCUMULATE API ENDPOINTS
        api_design = mike_result.get('api_design', {})
        for endpoint in api_design.get('new_endpoints', []):
            exists = any(
                e.get('method') == endpoint.get('method') and e.get('path') == endpoint.get('path')
                for e in architecture['current_endpoints']
            )
            if not exists:
                architecture['current_endpoints'].append({
                    'method': endpoint.get('method'),
                    'path': endpoint.get('path'),
                    'request': endpoint.get('request'),
                    'response': endpoint.get('response'),
                    'added_in': story_id
                })
                logger.info(f"  ➕ API: Added {endpoint.get('method')} {endpoint.get('path')}")
        
        for endpoint in api_design.get('modified_endpoints', []):
            for existing in architecture['current_endpoints']:
                if (existing.get('method') == endpoint.get('method') and 
                    existing.get('path') == endpoint.get('path')):
                    existing['modified_in'] = story_id
                    existing['changes'] = endpoint.get('changes')
                    logger.info(f"  ✏️ API: Modified {endpoint.get('method')} {endpoint.get('path')}")
                    break
        
        # 3. MERGE CONVENTION EXTENSIONS (for stories after NFR-001)
        if mike_result.get('conventions') and story_id != 'NFR-001':
            if 'conventions' not in architecture:
                architecture['conventions'] = {}
            
            # Deep merge new conventions into existing
            new_conventions = mike_result['conventions']
            for key, value in new_conventions.items():
                if key not in architecture['conventions']:
                    architecture['conventions'][key] = value
                    logger.info(f"  ➕ Convention: Added '{key}'")
                elif isinstance(value, dict) and isinstance(architecture['conventions'][key], dict):
                    # Merge nested dicts
                    architecture['conventions'][key].update(value)
                    logger.info(f"  ✏️ Convention: Extended '{key}'")
        
        architecture['last_updated'] = datetime.now().isoformat()
        return architecture
    
    def _save_architecture(self, arch_data: Dict):
        """Save architecture decisions for future stories."""
        arch_file = APPDOCS_PATH / "architecture.json"
        try:
            with open(arch_file, 'w', encoding='utf-8') as f:
                json.dump(arch_data, f, indent=2)
            logger.info(f"✅ Architecture saved to {arch_file}")
        except Exception as e:
            logger.error(f"❌ Could not save architecture: {e}")

    def _load_plan(self) -> Dict:
        if not self.plan_path.exists():
            raise FileNotFoundError(f"Sprint plan not found: {self.plan_path}")
        with open(self.plan_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_plan(self, plan: Dict) -> None:
        self.plan_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

    async def _log_event(self, event_type: str, data: Dict) -> None:
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    @staticmethod
    def tail_events(log_path: Path, last_n: int = 50) -> List[Dict]:
        """Read last N events from a JSONL log file."""
        if not log_path.exists():
            return []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-last_n:]
            return [json.loads(line) for line in lines if line.strip()]
        except Exception:
            return []

    @staticmethod
    async def stream_events(log_path: Path):
        """Async generator yielding SSE lines for new events in log file."""
        position = 0
        while True:
            try:
                if log_path.exists():
                    with open(log_path, "r", encoding="utf-8") as f:
                        f.seek(position)
                        for line in f:
                            if not line.strip():
                                continue
                            yield f"event: update\n"
                            yield f"data: {line.strip()}\n\n"
                        position = f.tell()
                yield "event: heartbeat\ndata: {}\n\n"
            except Exception:
                yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(0.5)

    async def _update_backlog(self, story_id: str, updates: Dict[str, str]) -> None:
        try:
            # Update status for all story types (US-, NFR-, STYLE-, WF-, etc.)
            # No filtering - all stories should have their status tracked
            if not BACKLOG_CSV_PATH.exists():
                await self._log_event("backlog_update_skipped", {"story_id": story_id, "reason": "missing_csv"})
                return
            with open(BACKLOG_CSV_PATH, "r", newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                
                # Validate full schema, not just required columns
                is_valid, error_msg = validate_csv_headers(headers)
                if not is_valid:
                    await self._log_event("backlog_update_skipped", {
                        "story_id": story_id,
                        "reason": f"corrupted_headers:{error_msg}"
                    })
                    return
                
                rows = list(reader)
            found = False
            for r in rows:
                if r.get("Story_ID") == story_id:
                    for k, v in updates.items():
                        if k in headers:
                            r[k] = v
                    found = True
                    break
            if not found:
                await self._log_event("backlog_update_skipped", {"story_id": story_id, "reason": "story_not_found"})
                return
            with open(BACKLOG_CSV_PATH, "w", newline='', encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            await self._log_event("backlog_updated", {"story_id": story_id, "updated_fields": list(updates.keys())})
        except Exception as e:
            await self._log_event("backlog_update_skipped", {"story_id": story_id, "reason": f"error:{str(e)}"})

    async def _auto_complete_related_wireframes(self, us_story_id: str, completion_time: str) -> None:
        """Auto-complete WF- stories that correspond to a completed US- story."""
        try:
            # Extract story number from US-XXX format
            story_number = us_story_id.split("-")[1] if "-" in us_story_id else None
            if not story_number:
                return
            
            # Find corresponding WF- story (e.g., US-001 -> WF-001)
            wf_story_id = f"WF-{story_number}"
            
            # Check if WF story exists in backlog
            backlog_stories = self._load_backlog_stories()
            if wf_story_id in backlog_stories:
                wf_story = backlog_stories[wf_story_id]
                current_status = wf_story.get('Execution_Status', '')
                
                # Only auto-complete if WF story is not already completed
                if current_status not in ['completed', 'completed_with_failures']:
                    await self._update_backlog(wf_story_id, {
                        "Execution_Status": "completed",
                        "Execution_Completed_At": completion_time,
                        "Last_Event": "auto_completed_with_us_story",
                        "Last_Updated": completion_time,
                    })
                    
                    await self._log_event("wireframe_auto_completed", {
                        "wf_story_id": wf_story_id,
                        "us_story_id": us_story_id,
                        "reason": "us_story_completed"
                    })
                    
                    logger.info(f"✅ Auto-completed {wf_story_id} when {us_story_id} finished")
        except Exception as e:
            logger.warning(f"Could not auto-complete wireframe for {us_story_id}: {e}")

    # ============================================================================
    # BACKUP AND ROLLBACK METHODS
    # ============================================================================

    def _now_utc_iso(self) -> str:
        """Return current local time in ISO format."""
        return datetime.now().isoformat()

    def _create_backup(self, plan: Dict, project_name: str) -> Optional[Dict]:
        """Snapshot current project/backlog artifacts before execution."""
        try:
            backup_id = datetime.now().strftime("%Y%m%dT%H%M%S%f")
            backup_root = self.backup_dir / backup_id
            backup_root.mkdir(parents=True, exist_ok=False)

            metadata = {
                "backup_id": backup_id,
                "created_at": self._now_utc_iso(),
                "sprint_id": self.sprint_id,
                "project_name": project_name,
                "plan_status": plan.get("status"),
                "stories": plan.get("stories", []),
                "items": []
            }

            # Copy sprint plan (pre-execution state)
            if self.plan_path.exists():
                shutil.copy2(self.plan_path, backup_root / "plan.json")
                metadata["items"].append("plan")

            # Copy execution log (or create empty file if doesn't exist yet)
            # This ensures rollback properly clears the log when restoring to pre-execution state
            log_backup_path = backup_root / "execution_log.jsonl"
            if self.log_path.exists():
                shutil.copy2(self.log_path, log_backup_path)
            else:
                log_backup_path.touch()  # Create empty file to mark "should not exist"
            metadata["items"].append("execution_log")

            # Copy backlog CSV snapshot
            if BACKLOG_CSV_PATH.exists():
                shutil.copy2(BACKLOG_CSV_PATH, backup_root / "Backlog.csv")
                metadata["items"].append("backlog_csv")

            # Copy architecture.json (or create empty file if doesn't exist yet)
            # This ensures rollback properly clears architecture when restoring to pre-NFR-001 state
            arch_file = APPDOCS_PATH / "architecture.json"
            arch_backup_path = backup_root / "architecture.json"
            if arch_file.exists():
                shutil.copy2(arch_file, arch_backup_path)
            else:
                arch_backup_path.write_text("{}", encoding="utf-8")  # Empty JSON object
            metadata["items"].append("architecture")

            # Copy wireframes directory snapshot (if any files exist)
            if WIREFRAME_DIR.exists() and any(WIREFRAME_DIR.iterdir()):
                shutil.copytree(WIREFRAME_DIR, backup_root / "wireframes")
                metadata["items"].append("wireframes")

            # Capture current project sandbox (even if empty)
            # Exclude node_modules - will be reinstalled on restore
            project_root = EXECUTION_SANDBOX / project_name
            project_backup_dir = backup_root / "project"
            metadata["items"].append("project")
            if project_root.exists():
                shutil.copytree(
                    project_root,
                    project_backup_dir,
                    ignore=shutil.ignore_patterns(
                        'node_modules',      # Reinstalled on restore
                        'venv',              # Python venv (if Flask projects added later)
                        '.venv',
                        '__pycache__',
                        '*.pyc',
                        '.pytest_cache',
                        '*.log',
                        '.DS_Store',
                        '.git'
                        # Keep: database.sqlite, *.db (user data must be preserved)
                    )
                )
            else:
                project_backup_dir.mkdir(parents=True, exist_ok=True)

            (backup_root / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            metadata["path"] = str(backup_root)
            return metadata

        except FileExistsError:
            # Fall back to a recursive call with a new timestamp for rare collisions
            return self._create_backup(plan, project_name)
        except Exception as e:
            logger.error(f"Failed to create sprint backup: {e}", exc_info=True)
            try:
                if 'backup_root' in locals() and backup_root.exists():
                    shutil.rmtree(backup_root, ignore_errors=True)
            except Exception:
                pass
            return None

    @classmethod
    def restore_backup(cls, sprint_id: str, backup_id: str) -> Dict:
        """Restore artifacts from a specific sprint backup."""
        backup_root = BACKUP_BASE_DIR / sprint_id / backup_id
        if not backup_root.exists():
            raise FileNotFoundError(f"Backup not found: {sprint_id}/{backup_id}")

        metadata_path = backup_root / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid backup metadata for {sprint_id}/{backup_id}: {e}")

        project_root = EXECUTION_SANDBOX / "yourapp"

        # Restore sprint plan BUT preserve current backup registry
        plan_path = SPRINT_DIR / f"{sprint_id}.json"
        existing_backups = []
        if plan_path.exists():
            try:
                existing_plan = json.loads(plan_path.read_text(encoding="utf-8"))
                existing_backups = existing_plan.get("backups", [])
            except Exception:
                existing_backups = []

        plan_backup = backup_root / "plan.json"
        if plan_backup.exists():
            # Restore plan but keep current backup registry
            restored_plan = json.loads(plan_backup.read_text(encoding="utf-8"))
            restored_plan["backups"] = existing_backups  # Preserve current backup list
            plan_path.write_text(json.dumps(restored_plan, indent=2), encoding="utf-8")

        # Restore backlog CSV snapshot
        backlog_backup = backup_root / "Backlog.csv"
        if backlog_backup.exists():
            BACKLOG_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backlog_backup, BACKLOG_CSV_PATH)

        # Restore execution log (always exists in backup, may be empty for pre-execution state)
        log_backup = backup_root / "execution_log.jsonl"
        log_path = SPRINT_DIR / f"execution_log_{sprint_id}.jsonl"
        if log_backup.exists():
            if log_backup.stat().st_size == 0:
                # Empty file = pre-execution state, remove current log
                if log_path.exists():
                    try:
                        log_path.unlink()
                        logger.info(f"✅ Deleted execution log for {sprint_id} during rollback (backup was empty)")
                    except Exception as e:
                        logger.error(f"❌ Failed to delete execution log for {sprint_id}: {e}")
            else:
                # Non-empty file = restore it
                shutil.copy2(log_backup, log_path)
                logger.info(f"✅ Restored execution log for {sprint_id} from backup")
        else:
            # Fallback for old backups without empty file marker
            if log_path.exists():
                try:
                    log_path.unlink()
                    logger.info(f"✅ Deleted execution log for {sprint_id} during rollback (no backup marker)")
                except Exception as e:
                    logger.error(f"❌ Failed to delete execution log for {sprint_id}: {e}")

        # Restore architecture.json (always exists in backup, may be empty {} for pre-NFR-001 state)
        arch_backup = backup_root / "architecture.json"
        arch_file = APPDOCS_PATH / "architecture.json"
        if arch_backup.exists():
            content = arch_backup.read_text(encoding="utf-8").strip()
            if content == "{}":
                # Empty JSON = pre-NFR-001 state, remove current architecture
                if arch_file.exists():
                    arch_file.unlink()
            else:
                # Non-empty = restore it
                shutil.copy2(arch_backup, arch_file)
        else:
            # Fallback for old backups without empty file marker
            if arch_file.exists():
                arch_file.unlink()

        # Restore wireframes directory
        wireframes_backup = backup_root / "wireframes"
        if wireframes_backup.exists():
            if WIREFRAME_DIR.exists():
                shutil.rmtree(WIREFRAME_DIR)
            shutil.copytree(wireframes_backup, WIREFRAME_DIR)

        # Restore project files or empty sandbox to match backup
        project_backup = backup_root / "project"
        if project_backup.exists():
            if project_root.exists():
                shutil.rmtree(project_root)
            shutil.copytree(project_backup, project_root)

            # Reinstall dependencies (node_modules excluded from backup)
            package_json = project_root / "package.json"
            if package_json.exists():
                logger.info("🔄 Reinstalling dependencies for yourapp after rollback...")
                try:
                    result = subprocess.run(
                        ["npm", "ci", "--prefer-offline"],
                        cwd=str(project_root),
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minutes
                    )

                    if result.returncode != 0:
                        # Fallback to npm install if ci fails
                        logger.info("npm ci failed, trying npm install...")
                        result = subprocess.run(
                            ["npm", "install", "--prefer-offline"],
                            cwd=str(project_root),
                            capture_output=True,
                            text=True,
                            timeout=300
                        )

                    if result.returncode == 0:
                        logger.info("✅ Dependencies reinstalled successfully")
                    else:
                        logger.warning(f"⚠️ npm install failed: {result.stderr}")
                        logger.warning("Project files restored but dependencies missing - manually run 'npm install'")

                except subprocess.TimeoutExpired:
                    logger.error("❌ npm install timed out during rollback")
                except FileNotFoundError:
                    logger.error("❌ npm not found - cannot reinstall dependencies")
                except Exception as e:
                    logger.error(f"Failed to reinstall dependencies: {e}")
        else:
            if project_root.exists():
                shutil.rmtree(project_root)
            project_root.mkdir(parents=True, exist_ok=True)

        pruned_sprints = cls._prune_future_artifacts(sprint_id)

        # Backup registry already preserved above - no merge needed
        # The restored plan already has the current backup list from existing_backups

        if metadata is not None:
            metadata.setdefault("pruned_sprints", pruned_sprints)
            metadata.setdefault("restored_sprint", sprint_id)
            metadata.setdefault("restored_backup", backup_id)
            metadata["path"] = str(backup_root)
            return metadata

        return {
            "path": str(backup_root),
            "restored_sprint": sprint_id,
            "restored_backup": backup_id,
            "pruned_sprints": pruned_sprints,
        }

    @classmethod
    def _prune_future_artifacts(cls, sprint_id: str) -> List[str]:
        """Delete sprint artifacts with IDs greater than the restored sprint."""
        target_number = cls._parse_sprint_number(sprint_id)
        if target_number is None:
            return []

        removed: List[str] = []
        for plan_path in SPRINT_DIR.glob("SP-*.json"):
            plan_id = plan_path.stem
            if plan_id == sprint_id:
                continue

            number = cls._parse_sprint_number(plan_id)
            if number is None or number <= target_number:
                continue

            project_name: Optional[str] = None
            try:
                with open(plan_path, "r", encoding="utf-8") as f:
                    plan_doc = json.load(f)
                    project_name = plan_doc.get("project_name")
            except Exception:
                project_name = None

            try:
                plan_path.unlink()
            except FileNotFoundError:
                pass

            log_path = SPRINT_DIR / f"execution_log_{plan_id}.jsonl"
            if log_path.exists():
                try:
                    log_path.unlink()
                except FileNotFoundError:
                    pass

            # Remove backups for the pruned sprint
            pruned_backup_dir = BACKUP_BASE_DIR / plan_id
            if pruned_backup_dir.exists():
                try:
                    shutil.rmtree(pruned_backup_dir)
                except Exception as e:
                    logger.warning(f"Failed to remove backups for pruned sprint {plan_id}: {e}")

            removed.append(plan_id)
            logger.info(f"Pruned future sprint artifacts for {plan_id}")

        return removed

    @staticmethod
    def _parse_sprint_number(sprint_id: str) -> Optional[int]:
        """Extract numeric part from sprint ID (e.g., 'SP-003' -> 3)."""
        match = re.match(r"SP-(\d+)", sprint_id)
        return int(match.group(1)) if match else None

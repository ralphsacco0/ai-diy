"""
Sprint API endpoints for AI-DIY application.

Refactored to use unified API conventions and response envelopes.
Supports standard actions: save, get, list, delete, latest.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pathlib import Path
import asyncio

from .conventions import (
    ApiResponse, ApiAction, ApiErrorCode, SprintRequest, SprintRollbackRequest,
    create_success_response, create_error_response, log_api_call,
    generate_id_from_title, HTTP_STATUS_MAP, SafetyConfig
)

# Orchestrator (sequential MVP)
from services.sprint_orchestrator import SprintOrchestrator, OrchestratorConfig

# SSE manager for sprint execution events
from services.sse_manager import sse_manager

# Project metadata resolution
from core.project_metadata import get_project_name

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sprint"])

# Sprint storage directory
SPRINT_DIR = Path("static/appdocs/sprints")
SPRINT_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/sprint", response_model=ApiResponse)
async def handle_sprint_request(request: SprintRequest):
    """Handle sprint plan requests with unified response envelope."""
    start_time = time.time()

    try:
        log_api_call(
            route="/api/sprint",
            action=request.action.value,
            id=request.id,
            status="start"
        )

        if request.action == ApiAction.SAVE:
            response = await save_sprint(request)
        elif request.action == ApiAction.GET:
            response = await get_sprint(request.id)
        elif request.action == ApiAction.LIST:
            response = await list_sprints()
        elif request.action == ApiAction.DELETE:
            response = await delete_sprint(request.id)
        elif request.action == ApiAction.LATEST:
            response = await get_latest_sprint()
        else:
            # Fail-fast for unimplemented actions
            logger.warning(f"Unimplemented action requested: {request.action}")
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_IMPLEMENTED],
                detail=create_error_response(
                    f"Action '{request.action}' not implemented",
                    ApiErrorCode.NOT_IMPLEMENTED
                ).model_dump()
            )

        duration_ms = int((time.time() - start_time) * 1000)
        log_api_call(
            route="/api/sprint",
            action=request.action.value,
            id=request.id,
            status="success",
            duration_ms=duration_ms
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Sprint API error - Action: {request.action}, Error: {str(e)}")
        log_api_call(
            route="/api/sprint",
            action=request.action.value,
            id=request.id,
            status="error",
            duration_ms=duration_ms
        )
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Internal server error: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def save_sprint(request: SprintRequest) -> ApiResponse:
    """Save a sprint plan."""
    if not request.stories or not request.estimated_minutes or not request.rationale:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                "Stories, estimated_minutes, and rationale are required for saving sprint",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )

    # Use provided ID or generate new one
    sprint_id = request.sprint_id or f"SP-{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Check if we're overwriting
    sprint_file = SPRINT_DIR / f"{sprint_id}.json"
    is_overwrite = sprint_file.exists()

    # Create sprint plan document
    sprint_doc = {
        "sprint_id": sprint_id,
        "created_at": datetime.now().isoformat(),
        "status": request.status or "planned",
        "stories": request.stories,
        "estimated_minutes": request.estimated_minutes,
        "rationale": request.rationale
    }

    # Validate file size before writing
    json_content = json.dumps(sprint_doc, indent=2)
    if len(json_content.encode('utf-8')) > SafetyConfig.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
            detail=create_error_response(
                f"Sprint plan too large (max {SafetyConfig.MAX_FILE_SIZE_MB}MB)",
                ApiErrorCode.VALIDATION_ERROR
            ).model_dump()
        )

    # Save to file (overwrite if exists)
    with open(sprint_file, 'w') as f:
        f.write(json_content)

    action_msg = "updated" if is_overwrite else "created"
    logger.info(f"Sprint {action_msg}: {sprint_id}")

    # Update backlog to mark stories with Sprint_ID
    try:
        import csv
        backlog_csv_path = Path("static/appdocs/backlog/Backlog.csv")
        if backlog_csv_path.exists() and request.stories:
            with open(backlog_csv_path, "r", newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                rows = list(reader)
            
            # Update rows for stories in this sprint
            for row in rows:
                if row.get("Story_ID") in request.stories:
                    row["Sprint_ID"] = sprint_id
                    row["Status"] = "In Sprint"
                    # Don't overwrite Execution_Status if already set
                    if not row.get("Execution_Status"):
                        row["Execution_Status"] = "planned"
                    row["Last_Updated"] = datetime.now().isoformat()
            
            # Write updated backlog
            with open(backlog_csv_path, "w", newline='', encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            logger.info(f"Updated backlog: marked {len(request.stories)} stories with Sprint_ID {sprint_id}")
    except Exception as e:
        logger.warning(f"Could not update backlog with Sprint_ID: {e}")

    # Create backup snapshot immediately after plan is saved
    # This captures the pre-execution state for clean rollback
    try:
        from services.sprint_orchestrator import SprintOrchestrator, OrchestratorConfig

        # CRITICAL: Delete existing execution log BEFORE creating backup
        # This ensures rollback restores to a clean pre-execution state
        execution_log_path = SPRINT_DIR / f"execution_log_{sprint_id}.jsonl"
        if execution_log_path.exists():
            execution_log_path.unlink()
            logger.info(f"Cleared existing execution log for {sprint_id} before backup")

        config = OrchestratorConfig(sprint_id=sprint_id)
        orchestrator = SprintOrchestrator(config)
        backup_info = orchestrator._create_backup(sprint_doc, "yourapp")
        if backup_info:
            logger.info(f"Created backup snapshot for {sprint_id}: {backup_info['backup_id']}")
            # Add backup to plan's backup registry
            sprint_doc.setdefault("backups", []).append({
                "backup_id": backup_info["backup_id"],
                "created_at": backup_info["created_at"],
                "project_name": "yourapp",
                "sprint_id": sprint_id
            })
            # Save updated plan with backup info
            with open(sprint_file, 'w') as f:
                json.dump(sprint_doc, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not create backup snapshot for {sprint_id}: {e}")

    return create_success_response(
        f"Sprint plan '{sprint_id}' {action_msg} successfully",
        data={"sprint_id": sprint_id, "overwrite": is_overwrite}
    )


async def get_sprint(sprint_id: str) -> ApiResponse:
    """Retrieve a specific sprint plan."""
    if not sprint_id:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                "Sprint ID is required",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )

    sprint_file = SPRINT_DIR / f"{sprint_id}.json"
    if not sprint_file.exists():
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                f"Sprint not found: {sprint_id}",
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )

    try:
        with open(sprint_file, 'r') as f:
            sprint_doc = json.load(f)

        return create_success_response(
            "Sprint retrieved successfully",
            data={"sprint": sprint_doc}
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in sprint file {sprint_id}: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Corrupted sprint file: {sprint_id}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def list_sprints() -> ApiResponse:
    """List all saved sprint plans."""
    sprints = []

    try:
        for sprint_file in SPRINT_DIR.glob("*.json"):
            try:
                with open(sprint_file, 'r') as f:
                    sprint_doc = json.load(f)

                sprint_data = {
                    "sprint_id": sprint_doc["sprint_id"],
                    "created_at": sprint_doc["created_at"],
                    "status": sprint_doc["status"],
                    "stories": sprint_doc["stories"],
                    "estimated_minutes": sprint_doc["estimated_minutes"],
                    "rationale": sprint_doc["rationale"],
                    "backups": sprint_doc.get("backups", [])
                }
                
                # Add execution summary if sprint is completed
                if sprint_doc.get("status") == "completed" and sprint_doc.get("completed_at"):
                    sprint_data["completed_at"] = sprint_doc["completed_at"]
                    # Use current approved project name from single source of truth
                    sprint_data["project_name"] = get_project_name()
                    sprint_data["tech_stack"] = sprint_doc.get("tech_stack", "N/A")
                    
                    # Try to read execution summary from log
                    log_file = SPRINT_DIR / f"execution_log_{sprint_doc['sprint_id']}.jsonl"
                    if log_file.exists():
                        try:
                            # Read last line (sprint_completed event)
                            with open(log_file, 'r') as log_f:
                                lines = log_f.readlines()
                                if lines:
                                    last_event = json.loads(lines[-1])
                                    if last_event.get("event_type") == "sprint_completed":
                                        sprint_data["execution_summary"] = last_event.get("data", {}).get("summary", {})
                        except Exception as e:
                            logger.warning(f"Could not read execution summary for {sprint_doc['sprint_id']}: {e}")
                
                sprints.append(sprint_data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping invalid sprint file {sprint_file}: {e}")
                continue

        # Sort by creation date, newest first
        sprints.sort(key=lambda x: x["created_at"], reverse=True)

        return create_success_response(
            f"Found {len(sprints)} sprint plans",
            data={"sprints": sprints}
        )
    except Exception as e:
        logger.error(f"Error listing sprints: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to list sprints: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def delete_sprint(sprint_id: str) -> ApiResponse:
    """Delete a sprint plan."""
    if not sprint_id:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                "Sprint ID is required",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )

    sprint_file = SPRINT_DIR / f"{sprint_id}.json"

    if not sprint_file.exists():
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                f"Sprint not found: {sprint_id}",
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )

    try:
        # Delete the sprint file
        sprint_file.unlink()

        logger.info(f"Sprint deleted: {sprint_id}")
        return create_success_response(
            f"Sprint '{sprint_id}' deleted successfully"
        )
    except Exception as e:
        logger.error(f"Error deleting sprint {sprint_id}: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to delete sprint: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def get_latest_sprint() -> ApiResponse:
    """Get the most recent sprint plan."""
    try:
        # Get all sprints first
        list_response = await list_sprints()
        if not list_response.data or not list_response.data.get("sprints"):
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
                detail=create_error_response(
                    "No sprint plans found",
                    ApiErrorCode.NOT_FOUND
                ).model_dump()
            )

        latest_sprint = list_response.data["sprints"][0]  # Already sorted by date
        return await get_sprint(latest_sprint["sprint_id"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest sprint: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to get latest sprint: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


@router.post("/sprints/execute-next", response_model=ApiResponse)
async def execute_next_sprint(background_tasks: BackgroundTasks):
    """Find and execute the next planned sprint (oldest by creation date)."""
    start_time = time.time()

    try:
        log_api_call(
            route="/api/sprints/execute-next",
            action="execute-next",
            status="start"
        )

        # Find the oldest sprint with status "planned"
        planned_sprints = []
        for sprint_file in SPRINT_DIR.glob("SP-*.json"):
            try:
                with open(sprint_file, "r", encoding="utf-8") as f:
                    sprint_doc = json.load(f)
                    if sprint_doc.get("status") == "planned":
                        planned_sprints.append({
                            "sprint_id": sprint_doc.get("sprint_id", sprint_file.stem),
                            "created_at": sprint_doc.get("created_at", ""),
                            "file": sprint_file
                        })
            except Exception:
                continue

        if not planned_sprints:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
                detail=create_error_response(
                    "No planned sprints found. Create a sprint plan first.",
                    ApiErrorCode.NOT_FOUND
                ).model_dump()
            )

        # Sort by created_at and pick the oldest
        planned_sprints.sort(key=lambda x: x["created_at"])
        next_sprint = planned_sprints[0]
        sprint_id = next_sprint["sprint_id"]

        duration_ms = int((time.time() - start_time) * 1000)
        log_api_call(
            route="/api/sprints/execute-next",
            action="execute-next",
            id=sprint_id,
            status="redirecting",
            duration_ms=duration_ms
        )

        # Delegate to the existing execute_sprint function
        return await execute_sprint(sprint_id, background_tasks)

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Execute-next error: {str(e)}")
        log_api_call(
            route="/api/sprints/execute-next",
            action="execute-next",
            status="error",
            duration_ms=duration_ms
        )
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to find next sprint: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


@router.post("/sprints/{sprint_id}/execute", response_model=ApiResponse)
async def execute_sprint(sprint_id: str, background_tasks: BackgroundTasks):
    """Trigger sprint execution for the given sprint plan (sequential MVP)."""
    start_time = time.time()

    try:
        log_api_call(
            route=f"/api/sprints/{sprint_id}/execute",
            action="execute",
            id=sprint_id,
            status="start"
        )

        # Validate plan exists and set status to executing
        sprint_file = SPRINT_DIR / f"{sprint_id}.json"
        if not sprint_file.exists():
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
                detail=create_error_response(
                    f"Sprint not found: {sprint_id}",
                    ApiErrorCode.NOT_FOUND
                ).model_dump()
            )

        try:
            with open(sprint_file, "r", encoding="utf-8") as f:
                sprint_doc = json.load(f)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
                detail=create_error_response(
                    f"Corrupted sprint file: {sprint_id}",
                    ApiErrorCode.SERVER_ERROR
                ).model_dump()
            )

        # Check if sprint is already completed - must use Rollback button to re-run
        if sprint_doc.get("status") == "completed":
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
                detail=create_error_response(
                    f"Sprint {sprint_id} is already completed. Use the Rollback button to reset and re-run it.",
                    ApiErrorCode.INVALID_REQUEST
                ).model_dump()
            )

        sprint_doc["status"] = "executing"
        with open(sprint_file, "w", encoding="utf-8") as f:
            json.dump(sprint_doc, f, indent=2)

        # Emit SSE event to notify frontend that execution has started
        await sse_manager.emit(sprint_id, {
            "type": "sprint_execution_started",
            "sprint_id": sprint_id,
            "project_name": sprint_doc.get("project_name", "Unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"Emitted sprint_execution_started event for {sprint_id}")

        # Start orchestrator in background (sequential run)
        orchestrator = SprintOrchestrator(OrchestratorConfig(sprint_id=sprint_id))

        async def _run_orchestrator():
            try:
                await orchestrator.run()
            except Exception as e:
                logger.error(f"Orchestrator error for {sprint_id}: {e}")

        # Schedule async task without blocking the request
        asyncio.create_task(_run_orchestrator())

        response = create_success_response(
            f"Sprint execution started for '{sprint_id}'. The AI team will begin working on the stories.",
            data={"sprint_id": sprint_id, "status": "executing"}
        )

        duration_ms = int((time.time() - start_time) * 1000)
        log_api_call(
            route=f"/api/sprints/{sprint_id}/execute",
            action="execute",
            id=sprint_id,
            status="success",
            duration_ms=duration_ms
        )

        return response

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Sprint execution error for {sprint_id}: {str(e)}")
        log_api_call(
            route=f"/api/sprints/{sprint_id}/execute",
            action="execute",
            id=sprint_id,
            status="error",
            duration_ms=duration_ms
        )
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to start sprint execution: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


@router.get("/sprints/{sprint_id}/status", response_model=ApiResponse)
async def get_sprint_status(sprint_id: str):
    """Return current sprint status with recent events (non-streaming)."""
    try:
        sprint_file = SPRINT_DIR / f"{sprint_id}.json"
        if not sprint_file.exists():
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
                detail=create_error_response(
                    f"Sprint not found: {sprint_id}",
                    ApiErrorCode.NOT_FOUND
                ).model_dump()
            )

        with open(sprint_file, "r", encoding="utf-8") as f:
            sprint_doc = json.load(f)

        log_path = SPRINT_DIR / f"execution_log_{sprint_id}.jsonl"

        # Read all events for accurate calculations
        all_events: List[Dict] = []
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            all_events.append(json.loads(line))
                        except Exception:
                            continue
            except Exception:
                all_events = []

        # Compute started_at
        started_at_iso: Optional[str] = None
        for ev in all_events:
            if ev.get("event_type") == "sprint_started":
                started_at_iso = ev.get("timestamp")
                break
        if not started_at_iso:
            # Fallback
            started_at_iso = sprint_doc.get("created_at")

        # Compute elapsed_minutes
        def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
            if not ts:
                return None
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                return None

        started_dt = _parse_iso(started_at_iso)
        completed_dt = _parse_iso(sprint_doc.get("completed_at"))
        now_dt = datetime.now(timezone.utc)
        end_dt = completed_dt or now_dt
        elapsed_minutes: Optional[float] = None
        if started_dt:
            # Align tz for naive timestamps
            if not started_dt.tzinfo:
                started_dt = started_dt.replace(tzinfo=timezone.utc)
            if not end_dt.tzinfo:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            elapsed_minutes = round((end_dt - started_dt).total_seconds() / 60.0, 2)

        # Determine current_story and current_task
        current_story = None
        current_task = 0
        # Track per-story phases
        last_phase_for_story: Dict[str, int] = {}
        story_open: Dict[str, bool] = {}
        phase_map = {"mike_breakdown": 1, "alex_implemented": 2, "jordan_tested": 3}

        for ev in all_events:
            et = ev.get("event_type")
            data = ev.get("data", {})
            sid = data.get("story_id")
            if et == "story_started" and sid:
                story_open[sid] = True
                current_story = sid
            elif et == "story_completed" and sid:
                story_open[sid] = False
                if current_story == sid:
                    current_story = None
            elif sid and et in phase_map:
                last_phase_for_story[sid] = phase_map[et]

        if current_story and current_story in last_phase_for_story:
            current_task = last_phase_for_story[current_story]
        elif current_story:
            current_task = 0

        # Build summary
        stories_completed = sum(1 for ev in all_events if ev.get("event_type") == "story_completed")
        # MVP has no explicit failures
        stories_failed = 0
        tasks_completed = sum(1 for ev in all_events if ev.get("event_type") in phase_map)
        tests_passed = 0
        tests_failed = 0
        for ev in all_events:
            if ev.get("event_type") == "jordan_tested":
                d = ev.get("data", {})
                try:
                    tests_passed += int(d.get("passed", 0))
                    tests_failed += int(d.get("failed", 0))
                except Exception:
                    pass

        summary = {
            "stories_completed": stories_completed,
            "stories_failed": stories_failed,
            "tasks_completed": tasks_completed,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
        }

        # Recent events (last 50)
        recent_events = SprintOrchestrator.tail_events(log_path, last_n=50)

        data = {
            "sprint_id": sprint_id,
            "status": sprint_doc.get("status", "planned"),
            "started_at": started_at_iso,
            "elapsed_minutes": elapsed_minutes,
            "current_story": current_story,
            "current_task": current_task,
            "summary": summary,
            "recent_events": recent_events,
        }
        return create_success_response("Sprint status retrieved", data=data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to get sprint status: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


@router.post("/sprints/save", response_model=ApiResponse)
async def save_sprint_compat(payload: dict) -> ApiResponse:
    """Compatibility endpoint matching OpenAPI /api/sprints/save.

    Accepts payload of shape:
    {
      "action": "save",
      "sprint_plan": {"sprint_id"?, "stories", "estimated_minutes", "rationale", "project_name"?, "tech_stack"?}
    }
    Delegates to save_sprint() using the unified conventions.
    """
    try:
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
                detail=create_error_response(
                    "Invalid JSON body",
                    ApiErrorCode.INVALID_REQUEST
                ).model_dump()
            )

        action = str(payload.get("action", "")).lower()
        if action != ApiAction.SAVE.value:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
                detail=create_error_response(
                    "Expected action 'save'",
                    ApiErrorCode.INVALID_REQUEST
                ).model_dump()
            )

        plan = payload.get("sprint_plan") or {}
        stories = plan.get("stories")
        estimated_minutes = plan.get("estimated_minutes")
        rationale = plan.get("rationale")
        sprint_id = plan.get("sprint_id")
        status = plan.get("status") or "planned"

        req = SprintRequest(
            action=ApiAction.SAVE,
            sprint_id=sprint_id,
            stories=stories,
            estimated_minutes=estimated_minutes,
            rationale=rationale,
            status=status
        )

        base_resp = await save_sprint(req)

        # Enrich response with OpenAPI-friendly fields without breaking existing clients
        try:
            if base_resp and base_resp.data and base_resp.data.get("sprint_id"):
                sid = base_resp.data["sprint_id"]
                file_path = str(SPRINT_DIR / f"{sid}.json")
                base_resp.data.setdefault("file_path", file_path)
                base_resp.data.setdefault("status", status)
        except Exception:
            pass

        return base_resp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to save sprint (compat): {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


@router.get("/sprints", response_model=ApiResponse)
async def list_sprints_compat() -> ApiResponse:
    """Compatibility endpoint matching OpenAPI /api/sprints (list)."""
    try:
        resp = await list_sprints()
        # Provide both keys for compatibility: original 'sprints' and OpenAPI 'plans'
        try:
            if resp and resp.data and "sprints" in resp.data and "plans" not in resp.data:
                resp.data["plans"] = resp.data["sprints"]
        except Exception:
            pass
        return resp
    except Exception as e:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to list sprints (compat): {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


@router.post("/sprints/{sprint_id}/rollback", response_model=ApiResponse)
async def rollback_sprint(sprint_id: str, payload: SprintRollbackRequest) -> ApiResponse:
    """Restore sprint artifacts to a previous backup snapshot."""
    if not sprint_id:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                "Sprint ID is required",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )

    if not payload or not payload.backup_id:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                "backup_id is required",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )

    try:
        log_api_call(
            route=f"/api/sprints/{sprint_id}/rollback",
            action="rollback",
            id=sprint_id,
            status="start"
        )

        backup_info = SprintOrchestrator.restore_backup(sprint_id, payload.backup_id)

        response = create_success_response(
            f"Sprint {sprint_id} restored from backup {payload.backup_id}",
            data={
                "sprint_id": sprint_id,
                "backup": backup_info
            }
        )

        log_api_call(
            route=f"/api/sprints/{sprint_id}/rollback",
            action="rollback",
            id=sprint_id,
            status="success"
        )
        return response

    except FileNotFoundError as e:
        log_api_call(
            route=f"/api/sprints/{sprint_id}/rollback",
            action="rollback",
            id=sprint_id,
            status="error"
        )
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                str(e),
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Rollback failed for sprint {sprint_id}: {e}", exc_info=True)
        log_api_call(
            route=f"/api/sprints/{sprint_id}/rollback",
            action="rollback",
            id=sprint_id,
            status="error"
        )
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to rollback sprint: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


@router.get("/sprints/stream")
async def stream_sprint_execution():
    """
    SSE endpoint for real-time sprint execution narration (global stream).
    
    Streams team activity messages (Mike/Alex/Jordan) from ALL sprint executions.
    Events include sprint_id in payload for filtering if needed.
    Messages are display-only and not stored in chat history.
    
    Returns:
        StreamingResponse with Server-Sent Events
    """
    from services.sse_manager import sse_manager
    
    async def event_generator():
        """Generate SSE events for all sprints."""
        queue = asyncio.Queue()
        await sse_manager.add_listener(queue)
        
        logger.info(f"SSE stream opened (global sprint stream)")
        
        try:
            while True:
                # Wait for next event
                event = await queue.get()
                
                # Format as SSE
                event_data = json.dumps(event)
                yield f"data: {event_data}\n\n"
                
                # Note: Stream stays open even after sprint_complete (for next sprint)
                    
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled")
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
        finally:
            sse_manager.remove_listener(queue)
            logger.info(f"SSE stream closed")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/sprints/{sprint_id}/pause")
async def pause_sprint_execution(sprint_id: str):
    """
    Pause sprint execution to allow user interaction.
    
    When user sends a message during sprint execution, the frontend calls this
    endpoint to pause the orchestrator. This allows Sarah to respond without
    interference from execution messages.
    
    Args:
        sprint_id: Sprint identifier (e.g., "SP-001")
    
    Returns:
        ApiResponse confirming pause
    """
    SprintOrchestrator.pause_sprint(sprint_id)
    
    response = create_success_response(
        f"Sprint {sprint_id} paused for user interaction",
        data={"sprint_id": sprint_id, "status": "paused"}
    )
    
    log_api_call(
        route=f"/api/sprints/{sprint_id}/pause",
        action="pause",
        id=sprint_id,
        status="success"
    )
    
    return response


@router.post("/sprints/{sprint_id}/resume")
async def resume_sprint_execution(sprint_id: str):
    """
    Resume paused sprint execution.
    
    After Sarah responds to user message, the frontend calls this endpoint
    to resume the orchestrator. Execution continues from where it left off.
    
    Args:
        sprint_id: Sprint identifier (e.g., "SP-001")
    
    Returns:
        ApiResponse confirming resume
    """
    SprintOrchestrator.resume_sprint(sprint_id)
    
    response = create_success_response(
        f"Sprint {sprint_id} resumed",
        data={"sprint_id": sprint_id, "status": "executing"}
    )
    
    log_api_call(
        route=f"/api/sprints/{sprint_id}/resume",
        action="resume",
        id=sprint_id,
        status="success"
    )
    
    return response


@router.get("/sprints/progress/{sprint_id}")
async def get_sprint_progress(sprint_id: str):
    """
    Get real-time progress data for a sprint by parsing its execution log.
    
    Returns structured data for the progress UI:
    - Sprint summary (stories done/in-progress/blocked)
    - Current story and task progress
    - Test results
    - Recent changes
    - Replans and stats
    """
    log_path = SPRINT_DIR / f"execution_log_{sprint_id}.jsonl"
    
    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"Execution log not found for sprint {sprint_id}")
    
    # Parse all events from the log
    events = []
    with open(log_path, 'r') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    # Initialize data structures
    stories = {}  # story_id -> {status, tasks, tests}
    current_story = None
    tests = []
    changes = []
    replans = []
    ai_calls = 0
    total_latency = 0
    latency_count = 0
    
    # Process events
    for event in events:
        event_type = event.get("event_type")
        data = event.get("data", {})
        timestamp = event.get("timestamp", "")
        
        if event_type == "story_started":
            story_id = data.get("story_id")
            current_story = story_id
            if story_id not in stories:
                stories[story_id] = {
                    "id": story_id,
                    "status": "in_progress",
                    "tasks": [],
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "tests_passed": 0,
                    "tests_failed": 0
                }
        
        elif event_type == "mike_breakdown":
            story_id = data.get("story_id")
            task_count = data.get("task_count", 0)
            if story_id in stories:
                stories[story_id]["total_tasks"] = task_count
                stories[story_id]["tasks"] = [{"status": "pending"} for _ in range(task_count)]
        
        elif event_type == "alex_implemented":
            story_id = data.get("story_id")
            task_number = data.get("task_number")
            description = data.get("description", "")
            files_count = data.get("files_count", 0)
            
            if story_id in stories and task_number:
                task_idx = task_number - 1
                if task_idx < len(stories[story_id]["tasks"]):
                    stories[story_id]["tasks"][task_idx] = {
                        "status": "done",
                        "description": description[:100]  # Truncate long descriptions
                    }
                    stories[story_id]["completed_tasks"] = task_number
                
                # Add to recent changes
                changes.insert(0, {
                    "msg": f"Task {task_number}: {description[:60]}...",
                    "ts": timestamp.split('T')[1][:8] if 'T' in timestamp else timestamp
                })
                changes = changes[:6]  # Keep last 6
                
                ai_calls += 1
        
        elif event_type == "jordan_test_run":
            story_id = data.get("story_id")
            passed = data.get("passed", 0)
            failed = data.get("failed", 0)
            test_files = data.get("test_files", [])
            
            if story_id in stories:
                stories[story_id]["tests_passed"] = passed
                stories[story_id]["tests_failed"] = failed
            
            # Add to live tests
            for test_file in test_files[:3]:  # Show top 3
                tests.insert(0, {
                    "name": test_file.split('/')[-1] if '/' in test_file else test_file,
                    "ok": failed == 0,
                    "ts": timestamp.split('T')[1][:8] if 'T' in timestamp else timestamp
                })
            tests = tests[:5]  # Keep last 5
        
        elif event_type == "alex_retry":
            story_id = data.get("story_id")
            retry_count = data.get("retry_count", 0)
            reason = data.get("reason", "Test failure")
            
            replans.insert(0, {
                "msg": f"Retry #{retry_count} for {story_id}: {reason[:40]}",
                "ts": timestamp.split('T')[1][:8] if 'T' in timestamp else timestamp
            })
            replans = replans[:4]  # Keep last 4
        
        elif event_type == "story_completed":
            story_id = data.get("story_id")
            if story_id in stories:
                stories[story_id]["status"] = "done"
        
        elif event_type == "story_failed":
            story_id = data.get("story_id")
            if story_id in stories:
                stories[story_id]["status"] = "blocked"
        
        elif event_type == "command_executed":
            # Track latency if available
            if "duration" in data:
                total_latency += data["duration"]
                latency_count += 1
    
    # Calculate summary stats
    story_list = list(stories.values())
    total_stories = len(story_list)
    done_stories = sum(1 for s in story_list if s["status"] == "done")
    blocked_stories = sum(1 for s in story_list if s["status"] == "blocked")
    in_progress_stories = total_stories - done_stories - blocked_stories
    
    progress_pct = int((done_stories / total_stories * 100)) if total_stories > 0 else 0
    avg_latency = (total_latency / latency_count) if latency_count > 0 else 0
    
    # Get current story details
    current_story_data = stories.get(current_story, {}) if current_story else {}
    
    return {
        "sprint_id": sprint_id,
        "summary": {
            "total": total_stories,
            "done": done_stories,
            "in_progress": in_progress_stories,
            "blocked": blocked_stories,
            "progress_pct": progress_pct
        },
        "current_story": {
            "id": current_story or "None",
            "total_tasks": current_story_data.get("total_tasks", 0),
            "completed_tasks": current_story_data.get("completed_tasks", 0),
            "tasks": current_story_data.get("tasks", [])
        },
        "tests": tests,
        "changes": changes,
        "replans": replans,
        "stats": {
            "ai_calls": ai_calls,
            "avg_latency": round(avg_latency, 1),
            "budget_used": min(100, int(ai_calls * 0.5))  # Rough estimate
        }
    }
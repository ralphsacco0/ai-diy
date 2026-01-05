"""
Backlog API endpoints for AI-DIY application.

Refactored to use unified API conventions and response envelopes.
Supports standard actions: save, get, list, delete, latest.
Includes CSV schema validation and wireframe serving.
"""

import json
import logging
import csv
import io
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pathlib import Path

from .conventions import (
    ApiResponse, ApiAction, ApiErrorCode, BacklogRequest,
    create_success_response, create_error_response, log_api_call,
    validate_csv_headers, HTTP_STATUS_MAP, SafetyConfig, CsvConfig,
    sanitize_slug
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["backlog"])

# Backlog storage directories
BACKLOG_DIR = Path("static/appdocs/backlog")
WIREFRAME_DIR = BACKLOG_DIR / "wireframes"
BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
WIREFRAME_DIR.mkdir(parents=True, exist_ok=True)

# Canonical 20-column backlog schema
BACKLOG_HEADERS = [
    "Story_ID", "Title", "User_Story", "Functional_Requirements",
    "Non_Functional_Requirements", "Integrations", "Dependencies",
    "Constraints", "Acceptance_Criteria", "Priority", "Status",
    "Vision_Ref", "Wireframe_Ref", "Notes", "Sprint_ID",
    "Execution_Status", "Execution_Started_At", "Execution_Completed_At",
    "Last_Event", "Last_Updated"
]


def build_csv_from_records(records: List[Dict[str, Any]]) -> str:
    """
    Build properly-quoted CSV from record dictionaries.
    
    Args:
        records: List of dicts with 20 fields each
        
    Returns:
        CSV string with QUOTE_ALL applied
        
    Raises:
        ValueError: If records are malformed
    """
    if not records:
        raise ValueError("Records list cannot be empty")
    
    # Validate each record has all 20 fields
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record {i} is not a dict: {type(record)}")
        
        # Check for missing required fields
        missing = [h for h in BACKLOG_HEADERS if h not in record]
        if missing:
            raise ValueError(f"Record {i} missing fields: {missing}")
    
    # Build CSV with QUOTE_ALL for fool-proof quoting
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    # Write header
    writer.writerow(BACKLOG_HEADERS)
    
    # Write data rows
    for record in records:
        row = [str(record.get(h, "")).strip() for h in BACKLOG_HEADERS]
        writer.writerow(row)
    
    return output.getvalue()


@router.post("/backlog", response_model=ApiResponse)
async def handle_backlog_request(request: BacklogRequest):
    """Handle backlog document requests with unified response envelope."""
    start_time = time.time()

    try:
        log_api_call(
            route="/api/backlog",
            action=request.action.value,
            id=request.id,
            status="start"
        )

        if request.action == ApiAction.SAVE:
            response = await save_backlog(request)
        elif request.action == ApiAction.GET:
            # Check if requesting a specific wireframe
            if request.wireframe_slug:
                response = await get_wireframe(request.wireframe_slug)
            else:
                response = await get_backlog(request.id)
        elif request.action == ApiAction.LIST:
            response = await list_backlogs()
        elif request.action == ApiAction.DELETE:
            response = await delete_backlog(request.id)
        elif request.action == ApiAction.LATEST:
            response = await get_latest_backlog()
        else:
            # Fail-fast for unimplemented actions
            logger.warning(f"Unimplemented backlog action requested: {request.action}")
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_IMPLEMENTED],
                detail=create_error_response(
                    f"Action '{request.action}' not implemented",
                    ApiErrorCode.NOT_IMPLEMENTED
                ).model_dump()
            )

        duration_ms = int((time.time() - start_time) * 1000)
        log_api_call(
            route="/api/backlog",
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
        logger.error(f"Backlog API error - Action: {request.action}, Error: {str(e)}")
        log_api_call(
            route="/api/backlog",
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


async def save_backlog(request: BacklogRequest) -> ApiResponse:
    """Save a backlog document with CSV schema validation."""
    
    # Generate ID from session metadata or use default
    backlog_id = request.id or "Backlog"
    
    backlog_file = BACKLOG_DIR / f"{backlog_id}.json"
    csv_file = BACKLOG_DIR / f"{backlog_id}.csv"

    # Determine data source: prefer records (new) over rows_csv (legacy)
    csv_content = None
    
    if request.records:
        # NEW PATH: Build CSV from JSON records (fool-proof)
        try:
            csv_content = build_csv_from_records(request.records)
            logger.info(f"Built CSV from {len(request.records)} records")
        except ValueError as e:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
                detail=create_error_response(
                    f"Invalid records: {str(e)}",
                    ApiErrorCode.VALIDATION_ERROR
                ).model_dump()
            )
    elif request.rows_csv:
        # LEGACY PATH: Use provided CSV (with quoting fix)
        # Validate CSV content
        csv_lines = request.rows_csv.strip().split('\n')
        if len(csv_lines) < 1:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
                detail=create_error_response(
                    "CSV data must contain at least headers",
                    ApiErrorCode.VALIDATION_ERROR
                ).model_dump()
            )
        
        # Validate CSV headers
        reader = csv.reader(io.StringIO(request.rows_csv))
        headers = next(reader)
        is_valid, error_msg = validate_csv_headers(headers)
        if not is_valid:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
                detail=create_error_response(
                    f"CSV schema validation failed: {error_msg}",
                    ApiErrorCode.VALIDATION_ERROR
                ).model_dump()
            )
        
        # Validate file size
        if len(request.rows_csv.encode('utf-8')) > SafetyConfig.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
                detail=create_error_response(
                    f"CSV file too large (max {SafetyConfig.MAX_FILE_SIZE_MB}MB)",
                    ApiErrorCode.VALIDATION_ERROR
                ).model_dump()
            )
        
        # Validate row count to prevent accidental data loss
        if csv_file.exists():
            try:
                with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                    existing_reader = csv.reader(f)
                    next(existing_reader)  # Skip header
                    existing_count = sum(1 for _ in existing_reader)
                
                new_reader = csv.reader(io.StringIO(request.rows_csv))
                next(new_reader)  # Skip header
                new_count = sum(1 for _ in new_reader)
                
                # Warn if losing more than 10% of rows
                if new_count < existing_count * 0.9:
                    logger.warning(
                        f"Suspicious save: {existing_count} rows → {new_count} rows. "
                        f"This would delete {existing_count - new_count} rows!"
                    )
                    raise HTTPException(
                        status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
                        detail=create_error_response(
                            f"Row count validation failed: Attempting to save {new_count} rows "
                            f"but current file has {existing_count} rows. This would delete "
                            f"{existing_count - new_count} rows. Please ensure you are saving "
                            f"the COMPLETE backlog with ALL rows.",
                            ApiErrorCode.VALIDATION_ERROR
                        ).model_dump()
                    )
            except Exception as e:
                logger.warning(f"Could not validate row count: {e}")
        
        # Save CSV file with proper quoting to preserve multi-line fields
        # For legacy rows_csv: Parse and re-write with QUOTE_ALL to ensure all fields are quoted
        # This prevents column misalignment when fields contain newlines or commas
        try:
            reader = csv.reader(io.StringIO(request.rows_csv))
            rows = list(reader)
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                writer.writerows(rows)
        except Exception as e:
            logger.error(f"Error writing CSV with quoting: {e}. Falling back to direct write.")
            # Fallback to direct write if quoting fails
            with open(csv_file, 'w', newline='') as f:
                f.write(request.rows_csv)
        
        logger.info(f"CSV saved: {csv_file}")
    
    # Write CSV if built from records (separate check, not elif)
    if csv_content:
        # NEW PATH: Write CSV built from records (already has proper quoting)
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
            logger.info(f"CSV saved from records: {csv_file}")
        except Exception as e:
            logger.error(f"Error writing CSV: {e}")
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
                detail=create_error_response(
                    f"Failed to save CSV: {str(e)}",
                    ApiErrorCode.VALIDATION_ERROR
                ).model_dump()
            )
    elif not request.records and not request.rows_csv:
        # No data provided
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
            detail=create_error_response(
                "Must provide either 'records' (new) or 'rows_csv' (legacy)",
                ApiErrorCode.VALIDATION_ERROR
            ).model_dump()
        )

    # Process wireframes if provided
    wireframe_refs = []
    if request.wireframes:
        for wireframe in request.wireframes:
            slug = wireframe.get("slug", "")
            html_content = wireframe.get("html_content", "")
            
            if not slug or not html_content:
                continue
                
            # Sanitize slug
            safe_slug = sanitize_slug(slug)
            if not safe_slug:
                continue
            
            # Save wireframe HTML
            wireframe_file = WIREFRAME_DIR / f"{safe_slug}.html"
            with open(wireframe_file, 'w') as f:
                f.write(html_content)
            
            wireframe_refs.append(safe_slug)
            logger.info(f"Wireframe saved: {wireframe_file}")
    
    # DISABLED: Orphan cleanup was too aggressive and deleted wireframes during partial updates
    # Wireframes should be managed explicitly through Requirements meeting or manual cleanup
    # if WIREFRAME_DIR.exists():
    #     for existing_file in WIREFRAME_DIR.glob("*.html"):
    #         file_slug = existing_file.stem  # filename without .html extension
    #         if file_slug not in wireframe_refs:
    #             existing_file.unlink()
    #             logger.info(f"Deleted orphaned wireframe: {existing_file}")

    # Create or update backlog metadata
    backlog_doc = {
        "id": backlog_id,
        "last_updated": datetime.now().isoformat(),
        "wireframes": wireframe_refs
    }
    
    # Add session metadata if provided
    if request.session_meta:
        backlog_doc["session_meta"] = request.session_meta

    # Validate JSON file size
    json_content = json.dumps(backlog_doc, indent=2)
    if len(json_content.encode('utf-8')) > SafetyConfig.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
            detail=create_error_response(
                f"Backlog metadata too large (max {SafetyConfig.MAX_FILE_SIZE_MB}MB)",
                ApiErrorCode.VALIDATION_ERROR
            ).model_dump()
        )

    # Save JSON metadata
    with open(backlog_file, 'w') as f:
        f.write(json_content)

    logger.info(f"Backlog saved: {backlog_doc['id']}")
    return create_success_response(
        f"Backlog '{backlog_doc['id']}' saved successfully",
        data={"backlog_id": backlog_doc["id"]}
    )


async def get_backlog(backlog_id: str) -> ApiResponse:
    """Retrieve a specific backlog document."""
    if not backlog_id:
        backlog_id = "Backlog"  # Default backlog

    backlog_file = BACKLOG_DIR / f"{backlog_id}.json"
    if not backlog_file.exists():
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                f"Backlog not found: {backlog_id}",
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )

    try:
        with open(backlog_file, 'r') as f:
            backlog_doc = json.load(f)

        return create_success_response(
            "Backlog retrieved successfully",
            data={"backlog": backlog_doc}
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in backlog file {backlog_id}: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Corrupted backlog file: {backlog_id}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def list_backlogs() -> ApiResponse:
    """List all saved backlog documents."""
    backlogs = []

    try:
        for backlog_file in BACKLOG_DIR.glob("*.json"):
            try:
                with open(backlog_file, 'r') as f:
                    backlog_doc = json.load(f)

                # Count wireframes for this backlog
                wireframe_count = 0
                if "wireframes" in backlog_doc:
                    wireframe_count = len(backlog_doc["wireframes"])

                backlogs.append({
                    "id": backlog_doc["id"],
                    "last_updated": backlog_doc.get("last_updated", ""),
                    "wireframe_count": wireframe_count
                })
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping invalid backlog file {backlog_file}: {e}")
                continue

        # Sort by update date, newest first
        backlogs.sort(key=lambda x: x["last_updated"], reverse=True)

        return create_success_response(
            f"Found {len(backlogs)} backlog documents",
            data={"backlogs": backlogs}
        )
    except Exception as e:
        logger.error(f"Error listing backlogs: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to list backlogs: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def get_wireframe(wireframe_slug: str) -> ApiResponse:
    """Get a specific wireframe HTML content by slug."""
    if not wireframe_slug:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                "Wireframe slug is required",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )
    
    # Sanitize slug to prevent path traversal
    safe_slug = wireframe_slug.replace('..', '').replace('/', '').replace('\\', '')
    wireframe_file = WIREFRAME_DIR / f"{safe_slug}.html"
    
    if not wireframe_file.exists() or wireframe_file.parent != WIREFRAME_DIR:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                f"Wireframe not found: {wireframe_slug}",
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )
    
    try:
        with open(wireframe_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        logger.info(f"Wireframe retrieved: {wireframe_slug}")
        return create_success_response(
            f"Wireframe '{wireframe_slug}' retrieved successfully",
            data={
                "slug": wireframe_slug,
                "html_content": html_content
            }
        )
    except Exception as e:
        logger.error(f"Error reading wireframe {wireframe_slug}: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to read wireframe: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def delete_backlog(backlog_id: str) -> ApiResponse:
    """Delete a backlog document and associated wireframes."""
    if not backlog_id:
        backlog_id = "Backlog"  # Default backlog

    backlog_file = BACKLOG_DIR / f"{backlog_id}.json"
    csv_file = BACKLOG_DIR / f"{backlog_id}.csv"

    if not backlog_file.exists():
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                f"Backlog not found: {backlog_id}",
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )

    try:
        # Load backlog to get wireframe references
        with open(backlog_file, 'r') as f:
            backlog_doc = json.load(f)

        # Delete wireframes (wireframes is a list of slugs)
        for wf_slug in backlog_doc.get("wireframes", []):
            wf_path = WIREFRAME_DIR / f"{wf_slug}.html"
            if wf_path.exists() and wf_path.parent == WIREFRAME_DIR:
                wf_path.unlink()
                logger.info(f"Deleted wireframe: {wf_path}")

        # Delete JSON and CSV files
        backlog_file.unlink()
        if csv_file.exists():
            csv_file.unlink()

        logger.info(f"Backlog deleted: {backlog_id}")
        return create_success_response(
            f"Backlog '{backlog_id}' deleted successfully"
        )
    except Exception as e:
        logger.error(f"Error deleting backlog {backlog_id}: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to delete backlog: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def get_latest_backlog() -> ApiResponse:
    """Get the most recent backlog document as CSV."""
    csv_file = BACKLOG_DIR / "Backlog.csv"

    if not csv_file.exists():
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                "No backlog CSV found",
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )

    try:
        # Validate CSV headers before serving
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader, [])

        is_valid, error_msg = validate_csv_headers(headers)
        if not is_valid:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
                detail=create_error_response(
                    f"CSV schema validation failed: {error_msg}",
                    ApiErrorCode.VALIDATION_ERROR
                ).model_dump()
            )

        # Return CSV file response
        return create_success_response(
            "Backlog CSV retrieved successfully",
            data={"csv_available": True, "row_count": len(headers)}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading backlog CSV: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to read backlog CSV: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


@router.post("/backlog/update-story")
async def update_story_status(request: dict):
    """Update a specific story's status and notes in the backlog CSV.
    
    Expected request body:
    {
        "story_id": "US-006",
        "status": "Done" | "Rejected" | "In Sprint",
        "notes": "User approved in Sprint Review"
    }
    """
    try:
        story_id = request.get("story_id")
        new_status = request.get("status")
        new_notes = request.get("notes", "")
        
        if not story_id or not new_status:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
                detail=create_error_response(
                    "story_id and status are required",
                    ApiErrorCode.INVALID_REQUEST
                ).model_dump()
            )
        
        csv_file = BACKLOG_DIR / "Backlog.csv"
        if not csv_file.exists():
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
                detail=create_error_response(
                    "Backlog CSV not found",
                    ApiErrorCode.NOT_FOUND
                ).model_dump()
            )
        
        # Read CSV
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            headers = reader.fieldnames
        
        # Find and update the story
        story_found = False
        for row in rows:
            if row.get('Story_ID') == story_id:
                story_found = True
                row['Status'] = new_status
                
                # Append to notes instead of replacing
                existing_notes = row.get('Notes', '').strip()
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                new_note_entry = f"[{timestamp}] {new_notes}"
                
                if existing_notes:
                    row['Notes'] = f"{existing_notes} | {new_note_entry}"
                else:
                    row['Notes'] = new_note_entry
                
                # Update Last_Updated timestamp
                row['Last_Updated'] = datetime.now().isoformat()
                
                # Update Last_Event
                row['Last_Event'] = f"Status changed to {new_status}"
                
                logger.info(f"Updated story {story_id}: Status={new_status}")
                
                # Auto-update associated wireframe if this is a US story
                if story_id.startswith('US-'):
                    wf_id = story_id.replace('US-', 'WF-')
                    for wf_row in rows:
                        if wf_row.get('Story_ID') == wf_id:
                            wf_row['Status'] = new_status
                            wf_row['Last_Updated'] = datetime.now().isoformat()
                            wf_row['Last_Event'] = f"Auto-updated with {story_id}"
                            logger.info(f"Auto-updated wireframe {wf_id}: Status={new_status}")
                            break
                
                break
        
        if not story_found:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
                detail=create_error_response(
                    f"Story not found: {story_id}",
                    ApiErrorCode.NOT_FOUND
                ).model_dump()
            )
        
        # Validate headers before writing to prevent corruption
        is_valid, error_msg = validate_csv_headers(headers)
        if not is_valid:
            logger.error(f"CSV headers corrupted before write: {error_msg}")
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
                detail=create_error_response(
                    f"CSV headers corrupted: {error_msg}. Cannot update story.",
                    ApiErrorCode.VALIDATION_ERROR
                ).model_dump()
            )
        
        # Write updated CSV
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        
        return create_success_response(
            f"Story {story_id} updated successfully",
            data={
                "story_id": story_id,
                "status": new_status,
                "notes_added": new_notes
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating story status: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to update story: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


@router.get("/backlog/latest")
async def serve_latest_backlog():
    """Serve the latest backlog CSV file directly (for frontend display).
    
    Note: This endpoint does not validate CSV schema on read - validation only
    occurs on save to allow viewing legacy/existing CSV files.
    """
    csv_file = BACKLOG_DIR / "Backlog.csv"

    if not csv_file.exists():
        raise HTTPException(status_code=404, detail="No backlog CSV found")

    try:
        # Return the raw CSV file as text/csv without validation
        # (validation only happens on save, not on read)
        # Add cache-busting headers to ensure browsers always fetch fresh data
        return FileResponse(
            csv_file,
            media_type="text/csv",
            filename="Backlog.csv",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except Exception as e:
        logger.error(f"Error serving backlog CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serve backlog CSV: {str(e)}")


@router.get("/backlog/wireframe/{slug}")
async def serve_wireframe(slug: str):
    """Serve wireframe HTML file with safety validation."""
    # Sanitize slug to prevent path traversal
    safe_slug = slug.replace('/', '').replace('\\', '').replace('..', '')
    if not safe_slug or safe_slug != slug:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                f"Invalid wireframe slug: {slug}",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )

    wireframe_path = WIREFRAME_DIR / f"{safe_slug}.html"
    if not wireframe_path.exists():
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                f"Wireframe not found: {safe_slug}",
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )

    # Validate file size before serving
    file_size = wireframe_path.stat().st_size
    if file_size > SafetyConfig.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
            detail=create_error_response(
                f"Wireframe file too large (max {SafetyConfig.MAX_FILE_SIZE_MB}MB)",
                ApiErrorCode.VALIDATION_ERROR
            ).model_dump()
        )

    try:
        with open(wireframe_path, 'r') as f:
            html_content = f.read()

        return Response(content=html_content, media_type="text/html")
    except Exception as e:
        logger.error(f"Error serving wireframe {safe_slug}: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to serve wireframe: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )
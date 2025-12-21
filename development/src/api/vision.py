"""
Vision API endpoints for AI-DIY application.

Refactored to use unified API conventions and response envelopes.
Supports standard actions: save, get, list, delete, latest.
"""

import json
import logging
import shutil
import time
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pathlib import Path

from .conventions import (
    ApiResponse, ApiAction, ApiErrorCode, VisionRequest,
    create_success_response, create_error_response, log_api_call,
    generate_id_from_title, HTTP_STATUS_MAP, SafetyConfig
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["vision"])

# Vision storage directory
VISION_DIR = Path("static/appdocs/visions")
VISION_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/vision", response_model=ApiResponse)
async def handle_vision_request(request: VisionRequest):
    """Handle vision document requests with unified response envelope."""
    start_time = time.time()

    try:
        log_api_call(
            route="/api/vision",
            action=request.action.value,
            id=request.id,
            status="start"
        )

        if request.action == ApiAction.SAVE:
            response = await save_vision(request)
        elif request.action == ApiAction.GET:
            response = await get_vision(request.id)
        elif request.action == ApiAction.LIST:
            response = await list_visions()
        elif request.action == ApiAction.DELETE:
            response = await delete_vision(request.id)
        elif request.action == ApiAction.LATEST:
            response = await get_latest_vision()
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
            route="/api/vision",
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
        logger.error(f"Vision API error - Action: {request.action}, Error: {str(e)}")
        log_api_call(
            route="/api/vision",
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


async def save_vision(request: VisionRequest) -> ApiResponse:
    """Save a vision document with overwrite support for existing IDs."""
    if not request.title or not request.content:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                "Title and content are required for saving",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )

    # ALWAYS use canonical vision ID (single vision file per project)
    vision_id = "vision"

    # Define file paths
    vision_file = VISION_DIR / f"{vision_id}.json"
    md_file = VISION_DIR / f"{vision_id}.md"
    is_overwrite = vision_file.exists()

    # Create backup before overwriting existing vision
    if is_overwrite:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = VISION_DIR / "backups"
            backup_dir.mkdir(exist_ok=True)

            # Backup both JSON and MD files
            shutil.copy(vision_file, backup_dir / f"vision_{timestamp}.json")
            if md_file.exists():
                shutil.copy(md_file, backup_dir / f"vision_{timestamp}.md")

            logger.info(f"Vision backup created: vision_{timestamp}")
        except Exception as e:
            logger.warning(f"Failed to create vision backup: {e}")

    # SAFEGUARD: If approving this vision, unapprove any previously approved vision
    if request.client_approval:
        try:
            for existing_file in VISION_DIR.glob("*.json"):
                try:
                    with open(existing_file, 'r') as f:
                        existing_doc = json.load(f)
                    
                    # If this is a different vision that's approved, unapprove it
                    if existing_doc.get("id") != vision_id and existing_doc.get("client_approval"):
                        existing_doc["client_approval"] = False
                        existing_doc["status"] = "draft"
                        existing_doc["updated_at"] = datetime.now().isoformat()
                        
                        with open(existing_file, 'w') as f:
                            json.dump(existing_doc, f, indent=2)
                        
                        logger.info(f"Vision approval transition: unapproved previous vision {existing_doc.get('id')}")
                except (json.JSONDecodeError, KeyError):
                    continue
        except Exception as e:
            logger.warning(f"Error during vision approval safeguard: {e}")

    # Create vision document
    vision_doc = {
        "id": vision_id,
        "title": request.title,
        "content": request.content,
        "client_approval": request.client_approval,
        "updated_at": datetime.now().isoformat(),
        "status": "approved" if request.client_approval else "draft"
    }

    # Validate file size before writing
    json_content = json.dumps(vision_doc, indent=2)
    if len(json_content.encode('utf-8')) > SafetyConfig.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.VALIDATION_ERROR],
            detail=create_error_response(
                f"Vision document too large (max {SafetyConfig.MAX_FILE_SIZE_MB}MB)",
                ApiErrorCode.VALIDATION_ERROR
            ).model_dump()
        )

    # Save to file (overwrite if exists)
    with open(vision_file, 'w') as f:
        f.write(json_content)

    # Also create a markdown version for easy reading
    with open(md_file, 'w') as f:
        f.write(f"# {request.title}\n\n")
        f.write(f"**Status:** {vision_doc['status'].title()}\n")
        f.write(f"**Updated:** {vision_doc['updated_at']}\n")
        f.write(f"**Client Approval:** {'Yes' if request.client_approval else 'No'}\n\n")
        f.write("---\n\n")
        f.write(request.content)

    # UPDATE PROJECT METADATA: If vision is approved, update the single source of truth
    if request.client_approval:
        try:
            metadata_file = VISION_DIR.parent / "project_metadata.json"
            metadata = {
                "approved_vision_id": vision_id,
                "project_name": request.title,
                "last_updated": datetime.now().isoformat()
            }
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Project metadata updated: approved_vision_id={vision_id}, project_name={request.title}")
        except Exception as e:
            logger.error(f"Error updating project metadata: {e}")

    action_msg = "updated" if is_overwrite else "created"
    approval_msg = " (approved)" if request.client_approval else ""
    logger.info(f"Vision {action_msg}: {vision_id}{approval_msg}")

    return create_success_response(
        f"Vision '{request.title}' {action_msg} successfully",
        data={"vision_id": vision_id, "overwrite": is_overwrite, "approved": request.client_approval}
    )


async def get_vision(vision_id: str) -> ApiResponse:
    """Retrieve a specific vision document."""
    if not vision_id:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                "Vision ID is required",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )

    vision_file = VISION_DIR / f"{vision_id}.json"
    if not vision_file.exists():
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                f"Vision not found: {vision_id}",
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )

    try:
        with open(vision_file, 'r') as f:
            vision_doc = json.load(f)

        return create_success_response(
            "Vision retrieved successfully",
            data={"vision": vision_doc}
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in vision file {vision_id}: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Corrupted vision file: {vision_id}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def list_visions() -> ApiResponse:
    """List all saved vision documents."""
    visions = []

    try:
        for vision_file in VISION_DIR.glob("*.json"):
            try:
                with open(vision_file, 'r') as f:
                    vision_doc = json.load(f)

                visions.append({
                    "id": vision_doc["id"],
                    "title": vision_doc["title"],
                    "status": vision_doc["status"],
                    "updated_at": vision_doc["updated_at"],
                    "client_approval": vision_doc["client_approval"]
                })
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping invalid vision file {vision_file}: {e}")
                continue

        # Sort by update date, newest first
        visions.sort(key=lambda x: x["updated_at"], reverse=True)

        return create_success_response(
            f"Found {len(visions)} vision documents",
            data={"visions": visions}
        )
    except Exception as e:
        logger.error(f"Error listing visions: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to list visions: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def delete_vision(vision_id: str) -> ApiResponse:
    """Delete a vision document."""
    if not vision_id:
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.INVALID_REQUEST],
            detail=create_error_response(
                "Vision ID is required",
                ApiErrorCode.INVALID_REQUEST
            ).model_dump()
        )

    vision_file = VISION_DIR / f"{vision_id}.json"
    md_file = VISION_DIR / f"{vision_id}.md"

    if not vision_file.exists():
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
            detail=create_error_response(
                f"Vision not found: {vision_id}",
                ApiErrorCode.NOT_FOUND
            ).model_dump()
        )

    try:
        # Delete both JSON and MD files
        vision_file.unlink()
        if md_file.exists():
            md_file.unlink()

        logger.info(f"Vision deleted: {vision_id}")
        return create_success_response(
            f"Vision '{vision_id}' deleted successfully"
        )
    except Exception as e:
        logger.error(f"Error deleting vision {vision_id}: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to delete vision: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )


async def get_latest_vision() -> ApiResponse:
    """Get the most recent approved vision document."""
    try:
        # Get all visions first
        list_response = await list_visions()
        if not list_response.data or not list_response.data.get("visions"):
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
                detail=create_error_response(
                    "No vision documents found",
                    ApiErrorCode.NOT_FOUND
                ).model_dump()
            )

        # Find the latest approved vision
        approved_visions = [
            v for v in list_response.data["visions"]
            if v["client_approval"]
        ]

        if not approved_visions:
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.NOT_FOUND],
                detail=create_error_response(
                    "No approved vision documents found",
                    ApiErrorCode.NOT_FOUND
                ).model_dump()
            )

        latest_vision = approved_visions[0]  # Already sorted by date
        return await get_vision(latest_vision["id"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest vision: {e}")
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to get latest vision: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )
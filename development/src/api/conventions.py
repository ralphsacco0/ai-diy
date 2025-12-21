"""
Common API conventions and utilities for AI-DIY application.

This module provides standardized response envelopes, error handling,
and utility functions used across all API endpoints.
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from enum import Enum
from pathlib import Path


# Configure logging for this module
logger = logging.getLogger(__name__)


class ApiResponse(BaseModel):
    """Unified response envelope for all API endpoints."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ApiAction(str, Enum):
    """Standard actions supported by API endpoints."""

    SAVE = "save"
    GET = "get"
    LIST = "list"
    DELETE = "delete"
    LATEST = "latest"


class ApiErrorCode(str, Enum):
    """Standard error codes for machine-readable error handling."""

    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    SERVER_ERROR = "SERVER_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class ApiError(BaseModel):
    """Standard error response with error code."""

    success: bool = False
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[ApiErrorCode] = None


# Request models
class BaseRequest(BaseModel):
    """Base request model with common fields."""

    action: ApiAction
    id: Optional[str] = None


class VisionRequest(BaseRequest):
    """Vision-specific request model."""

    title: Optional[str] = None
    content: Optional[str] = None
    client_approval: Optional[bool] = False


class BacklogRequest(BaseRequest):
    """Backlog-specific request model."""

    rows_csv: Optional[str] = None  # Legacy: raw CSV (deprecated, use records instead)
    records: Optional[List[Dict[str, Any]]] = None  # New: JSON records with 20 fields each
    wireframes: Optional[List[Dict[str, str]]] = None
    session_meta: Optional[Dict[str, Any]] = None
    wireframe_slug: Optional[str] = None  # For GET action to retrieve specific wireframe


class SprintRequest(BaseRequest):
    """Sprint-specific request model."""

    sprint_id: Optional[str] = None
    stories: Optional[List[str]] = None
    estimated_minutes: Optional[int] = None
    rationale: Optional[str] = None
    status: Optional[str] = None


class SprintRollbackRequest(BaseModel):
    """Sprint rollback request model."""

    backup_id: str


# Response data models
class VisionData(BaseModel):
    """Vision document data structure."""

    id: str
    title: str
    content: str
    client_approval: bool
    updated_at: str


class BacklogData(BaseModel):
    """Backlog document data structure."""

    id: str
    last_updated: str
    wireframe_count: int


class SprintData(BaseModel):
    """Sprint plan data structure."""

    sprint_id: str
    created_at: str
    status: str
    stories: List[str]
    estimated_minutes: int
    rationale: str


# Configuration constants
class SafetyConfig:
    """Centralized safety configuration."""

    DEFAULT_TIMEOUT_SECONDS = 90
    MAX_FILE_SIZE_MB = 10
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class CsvConfig:
    """CSV configuration constants."""

    CANONICAL_HEADERS = [
        "Story_ID", "Title", "User_Story", "Functional_Requirements",
        "Non_Functional_Requirements", "Integrations", "Dependencies",
        "Constraints", "Acceptance_Criteria", "Priority", "Status",
        "Vision_Ref", "Wireframe_Ref", "Notes",
        "Sprint_ID", "Execution_Status", "Execution_Started_At",
        "Execution_Completed_At", "Last_Event", "Last_Updated"
    ]


# Utility functions
def create_success_response(message: str, data: Optional[Dict[str, Any]] = None) -> ApiResponse:
    """Create a successful API response."""
    return ApiResponse(success=True, message=message, data=data)


def create_error_response(
    message: str,
    error_code: ApiErrorCode = ApiErrorCode.SERVER_ERROR,
    data: Optional[Dict[str, Any]] = None
) -> ApiResponse:
    """Create an error API response with error code."""
    return ApiResponse(success=False, message=message, data={"error_code": error_code.value, **(data or {})})


def create_api_error(
    message: str,
    error_code: ApiErrorCode = ApiErrorCode.SERVER_ERROR,
    data: Optional[Dict[str, Any]] = None
) -> ApiError:
    """Create a full API error response."""
    return ApiError(
        success=False,
        message=message,
        error_code=error_code,
        data=data
    )


def validate_csv_headers(actual_headers: List[str]) -> tuple[bool, str]:
    """Validate that CSV headers match the canonical schema."""
    if actual_headers != CsvConfig.CANONICAL_HEADERS:
        missing = set(CsvConfig.CANONICAL_HEADERS) - set(actual_headers)
        extra = set(actual_headers) - set(CsvConfig.CANONICAL_HEADERS)
        error_msg = "CSV header mismatch: "
        if missing:
            error_msg += f"missing={list(missing)} "
        if extra:
            error_msg += f"extra={list(extra)}"
        return False, error_msg.strip()
    return True, ""


def sanitize_slug(slug: str) -> str:
    """Sanitize a slug to prevent path traversal and ensure safe filenames."""
    import re
    if not slug:
        return ""

    # Allow only alphanumeric, hyphens, and underscores
    sanitized = re.sub(r'[^\w\-]', '', slug)
    # Remove multiple consecutive hyphens/underscores
    sanitized = re.sub(r'[-_]+', '-', sanitized)
    # Trim and ensure reasonable length
    return sanitized.strip()[:50]


def generate_id_from_title(title: str, timestamp: Optional[str] = None) -> str:
    """Generate a safe ID from title and timestamp."""
    if not title:
        raise ValueError("Title is required for ID generation")

    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')
    safe_title = sanitize_slug(safe_title)

    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"{safe_title}_{timestamp}"


def log_api_call(
    route: str,
    action: str,
    id: Optional[str] = None,
    status: str = "success",
    persona: Optional[str] = None,
    meeting_mode: Optional[str] = None,
    duration_ms: Optional[int] = None,
    **kwargs
):
    """Log API call in standardized JSON format."""
    log_entry = {
        "ts": datetime.now().isoformat(),
        "route": route,
        "action": action,
        "id": id,
        "status": status,
        "persona": persona,
        "meeting_mode": meeting_mode,
        "duration_ms": duration_ms,
        **kwargs
    }

    # Remove None values for cleaner logs
    log_entry = {k: v for k, v in log_entry.items() if v is not None}

    logger.info(f"API_CALL: {json.dumps(log_entry)}")


def validate_required_config(config_keys: List[str], config_source: Dict[str, Any]) -> List[str]:
    """Validate that all required configuration keys are present."""
    missing = []
    for key in config_keys:
        if key not in config_source or config_source[key] is None:
            missing.append(key)
    return missing


def fail_fast_on_missing_config(missing_keys: List[str]) -> None:
    """Fail fast with clear error message for missing configuration."""
    if missing_keys:
        error_msg = f"Missing required configuration: {', '.join(missing_keys)}"
        logger.error(f"CONFIG_ERROR: {error_msg}")
        raise ValueError(error_msg)


# HTTP status code mappings for errors
HTTP_STATUS_MAP = {
    ApiErrorCode.INVALID_REQUEST: 400,
    ApiErrorCode.NOT_FOUND: 404,
    ApiErrorCode.CONFLICT: 409,
    ApiErrorCode.SERVER_ERROR: 500,
    ApiErrorCode.NOT_IMPLEMENTED: 501,
    ApiErrorCode.VALIDATION_ERROR: 400,
}
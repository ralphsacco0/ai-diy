"""
Logging middleware and utilities for AI-DIY application.

Implements structured JSON-line logging for API calls with all required fields:
ts, route, action, id, status, persona, meeting_mode, duration_ms
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import traceback

from .config_manager import config_manager


class StructuredLogger:
    """Handles structured JSON-line logging for the application."""

    def __init__(self):
        self.logger = logging.getLogger("ai_diy.api")

    def log_api_call(
        self,
        route: str,
        action: str,
        id: Optional[str] = None,
        status: str = "success",
        persona: Optional[str] = None,
        meeting_mode: Optional[str] = None,
        duration_ms: Optional[int] = None,
        **kwargs
    ):
        """Log API call in structured JSON format."""
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

        # Log as JSON line
        self.logger.info(f"API_CALL: {json.dumps(log_entry)}")

    def log_error(
        self,
        route: str,
        action: str,
        error: Exception,
        id: Optional[str] = None,
        persona: Optional[str] = None,
        meeting_mode: Optional[str] = None,
        **kwargs
    ):
        """Log API errors with stack trace."""
        log_entry = {
            "ts": datetime.now().isoformat(),
            "route": route,
            "action": action,
            "id": id,
            "status": "error",
            "persona": persona,
            "meeting_mode": meeting_mode,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            **kwargs
        }

        # Remove None values
        log_entry = {k: v for k, v in log_entry.items() if v is not None}

        self.logger.error(f"API_ERROR: {json.dumps(log_entry)}")


# Global structured logger
structured_logger = StructuredLogger()


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    FastAPI middleware for structured logging of API calls.

    Captures all required fields: ts, route, action, id, status, duration_ms
    """
    start_time = time.time()

    # Extract route and action from request
    route = str(request.url.path)
    action = None
    api_id = None

    # Try to extract action and ID from request body (for POST requests)
    if request.method == "POST" and route.startswith("/api/"):
        try:
            body = await request.body()
            if body:
                request_body = json.loads(body)
                action = request_body.get("action")
                api_id = request_body.get("id")
        except:
            pass  # Ignore errors in body parsing for logging

    try:
        response = await call_next(request)

        duration_ms = int((time.time() - start_time) * 1000)

        # Log successful API call
        structured_logger.log_api_call(
            route=route,
            action=action,
            id=api_id,
            status="success",
            duration_ms=duration_ms
        )

        # Add logging headers to response for debugging
        response.headers["X-Request-ID"] = f"req_{int(time.time()*1000)}"
        response.headers["X-Duration-MS"] = str(duration_ms)

        return response

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        # Log error
        structured_logger.log_error(
            route=route,
            action=action,
            error=e,
            id=api_id,
            duration_ms=duration_ms
        )

        # Return error response with structured format
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Internal server error: {str(e)}",
                "data": {"error_code": "SERVER_ERROR"}
            }
        )


def setup_structured_logging(app_config) -> None:
    """Setup structured logging configuration."""

    # Get log level from configuration
    log_level = getattr(logging, app_config.log_level.upper(), logging.INFO)

    # Create formatters
    json_formatter = logging.Formatter('%(message)s')  # For JSON lines
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure API logger for JSON lines
    api_logger = logging.getLogger("ai_diy.api")
    api_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    api_logger.handlers.clear()

    # Add JSON handler for API calls
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(json_formatter)
    api_logger.addHandler(json_handler)

    # Add file handler for persistent logs if in production
    if app_config.is_production:
        try:
            log_file = Path("logs") / f"ai_diy_api_{datetime.now().strftime('%Y%m%d')}.jsonl"
            log_file.parent.mkdir(exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(json_formatter)
            api_logger.addHandler(file_handler)
        except Exception as e:
            # Fallback to console if file logging fails
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            api_logger.addHandler(console_handler)

    # Configure root logger for general application logs
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Add console handler for non-API logs
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(console_handler)


def extract_persona_from_request(request_body: Dict[str, Any]) -> Optional[str]:
    """Extract persona information from request context."""
    # This would be enhanced to extract from actual persona context
    # For now, return None as persona info comes from other sources
    return None


def extract_meeting_mode_from_request(request_body: Dict[str, Any]) -> Optional[str]:
    """Extract meeting mode information from request context."""
    # This would be enhanced to extract from actual meeting context
    # For now, return None as meeting mode comes from other sources
    return None


def get_request_metadata(request: Request) -> Dict[str, Any]:
    """Extract metadata from request for logging."""
    return {
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent")
    }
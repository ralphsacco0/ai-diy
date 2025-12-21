"""
Security middleware and utilities for AI-DIY application.

Implements comprehensive security measures including:
- Security headers and CORS protection
- Input validation and sanitization
- Rate limiting and resource monitoring
- Path traversal protection
- Security audit logging
"""

import time
import logging
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config_manager import config_manager
from .api.conventions import create_error_response, ApiErrorCode, HTTP_STATUS_MAP

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("ai_diy.security")


class SecurityConfig:
    """Security configuration constants."""

    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE = 100
    RATE_LIMIT_BURST = 20

    # Request size limits
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024     # 10MB

    # Input validation
    MAX_STRING_LENGTH = 10000
    MAX_ARRAY_LENGTH = 1000

    # Path traversal protection
    ALLOWED_PATHS = [
        "static/appdocs",
        "static/appdocs/visions",
        "static/appdocs/backlog",
        "static/appdocs/backlog/wireframes"
    ]

    # File type allowlist
    ALLOWED_EXTENSIONS = {'.json', '.csv', '.md', '.html', '.txt'}
    ALLOWED_MIME_TYPES = {
        'application/json', 'text/csv', 'text/markdown',
        'text/html', 'text/plain'
    }


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests = defaultdict(list)
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """Check if request is allowed and return remaining allowance."""
        now = time.time()

        # Cleanup old requests periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_requests(now)

        # Get recent requests for this client
        client_requests = self.requests[client_id]
        minute_ago = now - 60

        # Count requests in the last minute
        recent_requests = [req_time for req_time in client_requests if req_time > minute_ago]

        if len(recent_requests) >= SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE:
            return False, 0

        # Add current request
        client_requests.append(now)

        # Calculate remaining allowance
        remaining = SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE - len(recent_requests)
        return True, remaining

    def _cleanup_old_requests(self, now: float) -> None:
        """Remove old requests to prevent memory leaks."""
        cutoff = now - 60
        for client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > cutoff
            ]
        self.last_cleanup = now


class InputValidator:
    """Comprehensive input validation utilities."""

    @staticmethod
    def validate_string_length(value: str, max_length: int = SecurityConfig.MAX_STRING_LENGTH) -> bool:
        """Validate string length."""
        return len(value) <= max_length

    @staticmethod
    def validate_array_length(value: List, max_length: int = SecurityConfig.MAX_ARRAY_LENGTH) -> bool:
        """Validate array length."""
        return len(value) <= max_length

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            return str(value)

        # Remove null bytes and control characters
        sanitized = value.replace('\x00', '').replace('\r', '').replace('\n', ' ')
        # Trim whitespace
        sanitized = sanitized.strip()
        # Limit length
        if len(sanitized) > SecurityConfig.MAX_STRING_LENGTH:
            sanitized = sanitized[:SecurityConfig.MAX_STRING_LENGTH]

        return sanitized

    @staticmethod
    def validate_filename(filename: str) -> Tuple[bool, str]:
        """Validate filename for security."""
        if not filename:
            return False, "Filename cannot be empty"

        # Check length
        if len(filename) > 255:
            return False, "Filename too long"

        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False, "Invalid characters in filename"

        # Check for dangerous patterns
        dangerous_patterns = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in filename for char in dangerous_patterns):
            return False, "Dangerous characters in filename"

        return True, ""

    @staticmethod
    def validate_json_input(data: Any) -> Tuple[bool, str]:
        """Validate JSON input for security."""
        try:
            # Check if it's valid JSON
            json_str = json.dumps(data)
            parsed = json.loads(json_str)

            # Check for excessive nesting (basic protection)
            if InputValidator._check_json_depth(parsed) > 10:
                return False, "JSON structure too deeply nested"

            # Check for reasonable size
            if len(json_str) > SecurityConfig.MAX_REQUEST_SIZE:
                return False, "JSON payload too large"

            return True, ""
        except (TypeError, ValueError, OverflowError):
            return False, "Invalid JSON structure"

    @staticmethod
    def _check_json_depth(obj, depth: int = 0) -> int:
        """Check maximum depth of JSON structure."""
        if depth > 20:  # Prevent infinite recursion
            return depth

        if isinstance(obj, dict):
            return max([InputValidator._check_json_depth(v, depth + 1) for v in obj.values()] + [depth + 1])
        elif isinstance(obj, list):
            return max([InputValidator._check_json_depth(item, depth + 1) for item in obj] + [depth + 1])
        else:
            return depth + 1


class PathTraversalProtector:
    """Protects against path traversal attacks."""

    @staticmethod
    def is_safe_path(path: str, allowed_base_paths: List[str]) -> Tuple[bool, str]:
        """Check if path is safe and within allowed directories."""
        try:
            # Normalize path
            normalized_path = Path(path).resolve()

            # Check if path is within allowed directories
            for base_path in allowed_base_paths:
                base_resolved = Path(base_path).resolve()
                try:
                    normalized_path.relative_to(base_resolved)
                    return True, str(normalized_path)
                except ValueError:
                    continue

            return False, f"Path not allowed: {path}"

        except (OSError, ValueError) as e:
            return False, f"Invalid path: {e}"

    @staticmethod
    def sanitize_path_component(component: str) -> str:
        """Sanitize individual path component."""
        # Remove path traversal attempts
        sanitized = component.replace('..', '').replace('/', '').replace('\\', '')
        # Remove dangerous characters
        sanitized = re.sub(r'[<>:"|?*]', '', sanitized)
        # Limit length
        return sanitized[:100]


class SecurityAuditLogger:
    """Logs security-related events."""

    def log_suspicious_activity(self, event: str, details: Dict[str, Any], severity: str = "medium"):
        """Log suspicious security events."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "severity": severity,
            "details": details
        }

        if severity == "high":
            security_logger.error(f"SECURITY_AUDIT: {json.dumps(audit_entry)}")
        elif severity == "medium":
            security_logger.warning(f"SECURITY_AUDIT: {json.dumps(audit_entry)}")
        else:
            security_logger.info(f"SECURITY_AUDIT: {json.dumps(audit_entry)}")

    def log_rate_limit_exceeded(self, client_id: str, request_count: int):
        """Log rate limit violations."""
        self.log_suspicious_activity(
            "rate_limit_exceeded",
            {"client_id": client_id, "request_count": request_count},
            "medium"
        )

    def log_path_traversal_attempt(self, path: str, client_ip: str):
        """Log path traversal attempts."""
        self.log_suspicious_activity(
            "path_traversal_attempt",
            {"path": path, "client_ip": client_ip},
            "high"
        )


# Global instances
rate_limiter = RateLimiter()
security_audit = SecurityAuditLogger()


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with security checks."""
        start_time = time.time()

        try:
            # Get client identifier (IP or user agent based)
            client_id = self._get_client_id(request)

            # Rate limiting check
            allowed, remaining = rate_limiter.is_allowed(client_id)
            if not allowed:
                security_audit.log_rate_limit_exceeded(client_id, SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE)
                return JSONResponse(
                    status_code=429,
                    content=create_error_response(
                        "Rate limit exceeded. Please try again later.",
                        ApiErrorCode.VALIDATION_ERROR
                    ).model_dump(),
                    headers={"X-RateLimit-Remaining": "0"}
                )

            # Validate request size
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > SecurityConfig.MAX_REQUEST_SIZE:
                security_audit.log_suspicious_activity(
                    "oversized_request",
                    {"content_length": content_length, "client_ip": request.client.host},
                    "medium"
                )
                return JSONResponse(
                    status_code=413,
                    content=create_error_response(
                        "Request too large",
                        ApiErrorCode.VALIDATION_ERROR
                    ).model_dump()
                )

            # Process request
            response = await call_next(request)

            # Add security headers
            self._add_security_headers(response)

            # Add rate limit headers
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Limit"] = str(SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE)

            # Log successful request
            duration_ms = int((time.time() - start_time) * 1000)
            if duration_ms > 5000:  # Log slow requests
                security_logger.warning(f"Slow request: {request.method} {request.url.path} took {duration_ms}ms")

            return response

        except Exception as e:
            security_logger.error(f"Security middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content=create_error_response(
                    "Internal server error",
                    ApiErrorCode.SERVER_ERROR
                ).model_dump()
            )

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use X-Forwarded-For if available (for proxies), otherwise client IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Use user agent as fallback (less ideal but better than nothing)
        user_agent = request.headers.get("user-agent", "unknown")
        return f"ua:{hash(user_agent) % 10000}"

    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        # Basic security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (restrictive but functional)
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

        # Additional security headers
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Input validation middleware."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Validate request inputs."""
        # Only validate POST requests with JSON content
        if request.method == "POST" and "application/json" in request.headers.get("content-type", ""):
            try:
                # Read and validate request body
                body = await request.body()
                if body:
                    json_data = json.loads(body)

                    # Validate JSON structure
                    is_valid, error_msg = InputValidator.validate_json_input(json_data)
                    if not is_valid:
                        security_audit.log_suspicious_activity(
                            "invalid_json_input",
                            {"error": error_msg, "client_ip": request.client.host},
                            "medium"
                        )
                        return JSONResponse(
                            status_code=400,
                            content=create_error_response(
                                f"Invalid input: {error_msg}",
                                ApiErrorCode.VALIDATION_ERROR
                            ).model_dump()
                        )

                    # Sanitize string fields
                    sanitized_data = self._sanitize_request_data(json_data)

                    # Replace request body with sanitized version
                    request._body = json.dumps(sanitized_data).encode()

            except json.JSONDecodeError:
                security_audit.log_suspicious_activity(
                    "malformed_json",
                    {"client_ip": request.client.host},
                    "medium"
                )
                return JSONResponse(
                    status_code=400,
                    content=create_error_response(
                        "Invalid JSON format",
                        ApiErrorCode.VALIDATION_ERROR
                    ).model_dump()
                )
            except Exception as e:
                security_logger.error(f"Input validation error: {e}")
                return JSONResponse(
                    status_code=400,
                    content=create_error_response(
                        "Input validation failed",
                        ApiErrorCode.VALIDATION_ERROR
                    ).model_dump()
                )

        return await call_next(request)

    def _sanitize_request_data(self, data: Any) -> Any:
        """Recursively sanitize request data."""
        if isinstance(data, str):
            return InputValidator.sanitize_string(data)
        elif isinstance(data, list):
            return [self._sanitize_request_data(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._sanitize_request_data(value) for key, value in data.items()}
        else:
            return data


def validate_file_operation(file_path: str, operation: str) -> Tuple[bool, str]:
    """Validate file operations for security."""
    # Check path safety
    is_safe, resolved_path = PathTraversalProtector.is_safe_path(
        file_path, SecurityConfig.ALLOWED_PATHS
    )

    if not is_safe:
        return False, resolved_path

    # Check file extension
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in SecurityConfig.ALLOWED_EXTENSIONS:
        return False, f"File type not allowed: {file_ext}"

    # Additional validation based on operation
    if operation == "write":
        # Check if parent directory exists and is writable
        parent_dir = Path(file_path).parent
        if not parent_dir.exists():
            return False, "Parent directory does not exist"

    return True, resolved_path


def log_security_event(event: str, details: Dict[str, Any], severity: str = "info"):
    """Log security events."""
    security_audit.log_suspicious_activity(event, details, severity)


def check_resource_usage() -> Dict[str, Any]:
    """Check current resource usage."""
    import psutil
    import os

    try:
        process = psutil.Process(os.getpid())

        return {
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "cpu_percent": process.cpu_percent(),
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
    except Exception as e:
        logger.warning(f"Resource usage check failed: {e}")
        return {"error": str(e)}
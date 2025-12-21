"""
Enhanced security utilities for AI-DIY application.

Provides comprehensive security functions including:
- Input sanitization and validation
- Path traversal protection
- File type validation
- Security monitoring and alerting
"""

import re
import mimetypes
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging

from .config_manager import config_manager
from .api.conventions import SafetyConfig

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("ai_diy.security")


class SecurityUtils:
    """Comprehensive security utility functions."""

    # Dangerous file extensions to block
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.sh', '.py', '.pl', '.rb', '.php', '.asp', '.jsp', '.war', '.ear'
    }

    # Dangerous file patterns
    DANGEROUS_PATTERNS = [
        r'\.\./',  # Path traversal
        r'/\.\./',  # Path traversal with leading slash
        r'\\\.\.\\',  # Windows path traversal
        r'<script',  # Script injection
        r'javascript:',  # JavaScript protocol
        r'vbscript:',  # VBScript protocol
        r'on\w+\s*=',  # Event handlers
    ]

    @staticmethod
    def validate_file_path(file_path: str, allowed_base_paths: List[str]) -> Tuple[bool, str, str]:
        """
        Comprehensive file path validation.

        Returns:
            (is_valid, error_message, sanitized_path)
        """
        try:
            # Basic path normalization
            path = Path(file_path)

            # Check for dangerous extensions
            if path.suffix.lower() in SecurityUtils.DANGEROUS_EXTENSIONS:
                return False, f"Dangerous file type: {path.suffix}", ""

            # Check for path traversal
            if '..' in str(path) or path.is_absolute():
                return False, "Path traversal detected", ""

            # Check against allowed base paths
            for base_path in allowed_base_paths:
                base = Path(base_path)
                try:
                    # Check if path is within base directory
                    resolved_path = (base / path).resolve()
                    resolved_base = base.resolve()

                    # Ensure resolved path is within base directory
                    if resolved_base in resolved_path.parents or resolved_path == resolved_base:
                        return True, "", str(resolved_path)
                except (OSError, ValueError):
                    continue

            return False, f"Path not in allowed directories: {file_path}", ""

        except Exception as e:
            return False, f"Path validation error: {e}", ""

    @staticmethod
    def sanitize_content(content: str) -> Tuple[str, List[str]]:
        """Sanitize content and return warnings."""
        warnings = []

        # Check for dangerous patterns
        for pattern in SecurityUtils.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Dangerous pattern detected: {pattern}")

        # Sanitize content
        sanitized = content

        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')

        # Normalize line endings
        sanitized = sanitized.replace('\r\n', '\n').replace('\r', '\n')

        # Check length
        if len(sanitized) > SafetyConfig.MAX_FILE_SIZE_BYTES:
            warnings.append(f"Content truncated: exceeds {SafetyConfig.MAX_FILE_SIZE_MB}MB limit")

        return sanitized[:SafetyConfig.MAX_FILE_SIZE_BYTES], warnings

    @staticmethod
    def validate_content_type(content_type: str) -> bool:
        """Validate content type against allowlist."""
        if not content_type:
            return False

        # Check exact matches
        allowed_types = {
            'application/json',
            'text/csv',
            'text/markdown',
            'text/html',
            'text/plain',
            'application/octet-stream'  # For file uploads
        }

        return content_type.lower() in allowed_types

    @staticmethod
    def detect_malicious_content(content: str) -> List[str]:
        """Detect potentially malicious content patterns."""
        warnings = []

        # Check for script injection
        script_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=\s*["\'][^"\']*["\']',
            r'expression\s*\(',
            r'eval\s*\(',
        ]

        for pattern in script_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Potential script injection: {pattern}")

        # Check for SQL injection patterns (basic)
        sql_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+\w+\s+set',
        ]

        for pattern in sql_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Potential SQL injection: {pattern}")

        # Check for path traversal in content
        if '../' in content or '..\\' in content:
            warnings.append("Path traversal patterns in content")

        return warnings

    @staticmethod
    def validate_request_size(headers: Dict[str, str]) -> Tuple[bool, str]:
        """Validate request size from headers."""
        content_length = headers.get('content-length')
        if content_length:
            try:
                size = int(content_length)
                if size > SafetyConfig.MAX_REQUEST_SIZE:
                    return False, f"Request too large: {size} bytes (max: {SafetyConfig.MAX_REQUEST_SIZE})"
            except ValueError:
                return False, "Invalid content-length header"

        return True, ""

    @staticmethod
    def generate_security_report() -> Dict[str, Any]:
        """Generate security status report."""
        try:
            from .security_middleware import rate_limiter, check_resource_usage

            resource_usage = check_resource_usage()

            # Get rate limiter stats (simplified)
            rate_limiter_size = len(rate_limiter.requests)

            return {
                "timestamp": datetime.now().isoformat(),
                "security_enabled": True,
                "rate_limiter_active_clients": rate_limiter_size,
                "max_rate_limit": SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE,
                "resource_usage": resource_usage,
                "allowed_paths": SecurityConfig.ALLOWED_PATHS,
                "allowed_extensions": list(SecurityConfig.ALLOWED_EXTENSIONS)
            }
        except Exception as e:
            logger.error(f"Security report generation failed: {e}")
            return {"error": str(e)}


class FileSecurityValidator:
    """File-specific security validation."""

    @staticmethod
    def validate_upload_file(file_path: str, original_filename: str) -> Tuple[bool, str, str]:
        """
        Validate uploaded file for security.

        Returns:
            (is_valid, error_message, sanitized_filename)
        """
        # Validate filename
        is_valid, error_msg = InputValidator.validate_filename(original_filename)
        if not is_valid:
            return False, error_msg, ""

        # Sanitize filename
        sanitized_filename = PathTraversalProtector.sanitize_path_component(original_filename)

        # Validate file path
        is_valid, error_msg, resolved_path = SecurityUtils.validate_file_path(
            file_path, SecurityConfig.ALLOWED_PATHS
        )

        if not is_valid:
            return False, error_msg, ""

        return True, "", sanitized_filename

    @staticmethod
    def scan_file_content(file_path: str) -> List[str]:
        """Scan file content for security issues."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            return SecurityUtils.detect_malicious_content(content)

        except Exception as e:
            return [f"File scan error: {e}"]


class APISecurityDecorator:
    """Decorator for adding security validation to API endpoints."""

    def __init__(self, require_auth: bool = False, rate_limit: int = None):
        self.require_auth = require_auth
        self.rate_limit = rate_limit or SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE

    def __call__(self, func):
        """Apply security checks to function."""
        async def wrapper(*args, **kwargs):
            # Add security validation logic here
            # For now, just call the original function
            return await func(*args, **kwargs)
        return wrapper


def secure_api_endpoint(require_auth: bool = False, rate_limit: int = None):
    """Decorator for securing API endpoints."""
    def decorator(func):
        return APISecurityDecorator(require_auth, rate_limit)(func)
    return decorator


def validate_api_input(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate API input data."""
    try:
        # Validate JSON structure
        is_valid, error_msg = InputValidator.validate_json_input(data)
        if not is_valid:
            return False, error_msg

        # Check for reasonable data sizes
        data_str = json.dumps(data)
        if len(data_str) > SafetyConfig.MAX_REQUEST_SIZE:
            return False, "Input data too large"

        return True, ""
    except Exception as e:
        return False, f"Input validation error: {e}"


def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "info"):
    """Log security events."""
    security_logger.log(
        severity.upper(),
        f"Security event: {event_type}",
        extra={"event_type": event_type, "details": details}
    )
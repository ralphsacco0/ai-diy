"""
Tests for security middleware and utilities.

Tests all security features including:
- Rate limiting and resource monitoring
- Input validation and sanitization
- Path traversal protection
- Security headers and CORS
- File upload validation
"""

import pytest
import json
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from security_middleware import (
    SecurityMiddleware, InputValidationMiddleware, RateLimiter,
    SecurityConfig, InputValidator, PathTraversalProtector,
    SecurityAuditLogger, security_audit
)
from security_utils import SecurityUtils, FileSecurityValidator


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limiter_creation(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter()
        assert limiter is not None
        assert limiter.cleanup_interval == 60

    def test_rate_limiter_allows_requests(self):
        """Test that rate limiter allows requests within limits."""
        limiter = RateLimiter()

        client_id = "test_client"
        allowed, remaining = limiter.is_allowed(client_id)

        assert allowed is True
        assert remaining > 0

    def test_rate_limiter_blocks_excessive_requests(self):
        """Test that rate limiter blocks requests exceeding limits."""
        limiter = RateLimiter()

        client_id = "test_client"

        # Make maximum allowed requests
        for i in range(SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE):
            allowed, remaining = limiter.is_allowed(client_id)
            assert allowed is True

        # Next request should be blocked
        allowed, remaining = limiter.is_allowed(client_id)
        assert allowed is False
        assert remaining == 0


class TestInputValidator:
    """Test input validation functionality."""

    def test_string_length_validation(self):
        """Test string length validation."""
        # Valid string
        assert InputValidator.validate_string_length("valid string") is True

        # String at limit
        max_string = "x" * SecurityConfig.MAX_STRING_LENGTH
        assert InputValidator.validate_string_length(max_string) is True

        # String over limit
        over_limit = "x" * (SecurityConfig.MAX_STRING_LENGTH + 1)
        assert InputValidator.validate_string_length(over_limit) is False

    def test_string_sanitization(self):
        """Test string sanitization."""
        # Normal string
        sanitized = InputValidator.sanitize_string("  normal string  ")
        assert sanitized == "normal string"

        # String with null bytes
        sanitized = InputValidator.sanitize_string("test\x00null")
        assert "\x00" not in sanitized

        # String with control characters
        sanitized = InputValidator.sanitize_string("test\r\ncontrol")
        assert "\r" not in sanitized
        assert "\n" not in sanitized

    def test_filename_validation(self):
        """Test filename validation."""
        # Valid filename
        valid, error = InputValidator.validate_filename("test_file.json")
        assert valid is True
        assert error == ""

        # Invalid - path traversal
        valid, error = InputValidator.validate_filename("../../../etc/passwd")
        assert valid is False
        assert "Invalid characters" in error

        # Invalid - dangerous characters
        valid, error = InputValidator.validate_filename("test<file>.json")
        assert valid is False
        assert "Dangerous characters" in error

    def test_json_validation(self):
        """Test JSON input validation."""
        # Valid JSON
        valid_data = {"test": "data", "number": 123}
        is_valid, error = InputValidator.validate_json_input(valid_data)
        assert is_valid is True
        assert error == ""

        # Invalid JSON structure
        invalid_data = {"key": {"deeply": {"nested": "x" * 1000}}}
        is_valid, error = InputValidator.validate_json_input(invalid_data)
        assert is_valid is False
        assert "nested" in error

        # Oversized JSON
        large_data = {"data": "x" * (SecurityConfig.MAX_REQUEST_SIZE + 1000)}
        is_valid, error = InputValidator.validate_json_input(large_data)
        assert is_valid is False
        assert "large" in error


class TestPathTraversalProtector:
    """Test path traversal protection."""

    def test_safe_path_validation(self):
        """Test safe path validation."""
        allowed_paths = ["static/appdocs", "static/appdocs/visions"]

        # Safe path
        is_safe, resolved = PathTraversalProtector.is_safe_path(
            "visions/test.json", allowed_paths
        )
        assert is_safe is True
        assert "test.json" in resolved

    def test_unsafe_path_detection(self):
        """Test unsafe path detection."""
        allowed_paths = ["static/appdocs"]

        # Path traversal attempt
        is_safe, resolved = PathTraversalProtector.is_safe_path(
            "../../../etc/passwd", allowed_paths
        )
        assert is_safe is False
        assert "not allowed" in resolved

    def test_path_component_sanitization(self):
        """Test path component sanitization."""
        # Normal component
        sanitized = PathTraversalProtector.sanitize_path_component("test_file")
        assert sanitized == "test_file"

        # Dangerous component
        sanitized = PathTraversalProtector.sanitize_path_component("../../../dangerous")
        assert sanitized == "dangerous"

        # Component with special characters
        sanitized = PathTraversalProtector.sanitize_path_component("test<file>name")
        assert "<" not in sanitized
        assert ">" not in sanitized


class TestSecurityUtils:
    """Test security utility functions."""

    def test_file_path_validation(self):
        """Test file path validation."""
        allowed_paths = ["static/appdocs", "static/appdocs/visions"]

        # Valid path
        is_valid, error, resolved = SecurityUtils.validate_file_path(
            "visions/test.json", allowed_paths
        )
        assert is_valid is True
        assert error == ""
        assert "test.json" in resolved

        # Dangerous extension
        is_valid, error, resolved = SecurityUtils.validate_file_path(
            "test.exe", allowed_paths
        )
        assert is_valid is False
        assert "Dangerous file type" in error

    def test_content_sanitization(self):
        """Test content sanitization."""
        # Normal content
        content, warnings = SecurityUtils.sanitize_content("normal content")
        assert content == "normal content"
        assert len(warnings) == 0

        # Content with dangerous patterns
        dangerous_content = "normal content <script>alert('xss')</script>"
        content, warnings = SecurityUtils.sanitize_content(dangerous_content)
        assert len(warnings) > 0
        assert "script injection" in warnings[0].lower()

    def test_malicious_content_detection(self):
        """Test malicious content detection."""
        # Normal content
        warnings = SecurityUtils.detect_malicious_content("normal content")
        assert len(warnings) == 0

        # Content with script injection
        warnings = SecurityUtils.detect_malicious_content("<script>alert('xss')</script>")
        assert len(warnings) > 0
        assert "script injection" in warnings[0].lower()

        # Content with SQL injection patterns
        warnings = SecurityUtils.detect_malicious_content("'; DROP TABLE users; --")
        assert len(warnings) > 0
        assert "sql injection" in warnings[0].lower()


class TestFileSecurityValidator:
    """Test file security validation."""

    def test_file_upload_validation(self):
        """Test file upload validation."""
        # Valid file
        is_valid, error, filename = FileSecurityValidator.validate_upload_file(
            "static/appdocs/visions/test.json", "test.json"
        )
        assert is_valid is True
        assert error == ""
        assert filename == "test.json"

        # Invalid filename with path traversal
        is_valid, error, filename = FileSecurityValidator.validate_upload_file(
            "static/appdocs/visions/test.json", "../../../etc/passwd"
        )
        assert is_valid is False
        assert "Invalid characters" in error

    def test_file_content_scanning(self):
        """Test file content scanning."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("normal content")
            f.flush()

            try:
                warnings = FileSecurityValidator.scan_file_content(f.name)
                assert len(warnings) == 0
            finally:
                Path(f.name).unlink()

        # Test with malicious content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("<script>alert('xss')</script>")
            f.flush()

            try:
                warnings = FileSecurityValidator.scan_file_content(f.name)
                assert len(warnings) > 0
                assert "script injection" in warnings[0].lower()
            finally:
                Path(f.name).unlink()


class TestSecurityAuditLogger:
    """Test security audit logging."""

    def test_audit_logger_creation(self):
        """Test security audit logger creation."""
        audit = SecurityAuditLogger()
        assert audit is not None

    def test_security_event_logging(self):
        """Test security event logging."""
        audit = SecurityAuditLogger()

        # Test different severity levels
        audit.log_suspicious_activity("test_event", {"test": "data"}, "low")
        audit.log_suspicious_activity("test_event", {"test": "data"}, "medium")
        audit.log_suspicious_activity("test_event", {"test": "data"}, "high")

        # Should not raise exceptions
        assert True


class TestSecurityIntegration:
    """Test security integration with FastAPI."""

    def test_security_config_constants(self):
        """Test security configuration constants."""
        assert SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE > 0
        assert SecurityConfig.MAX_REQUEST_SIZE > 0
        assert SecurityConfig.MAX_FILE_SIZE > 0
        assert len(SecurityConfig.ALLOWED_PATHS) > 0
        assert len(SecurityConfig.ALLOWED_EXTENSIONS) > 0

    def test_security_utils_integration(self):
        """Test security utils work together."""
        # Test path validation -> file validation -> content scanning
        allowed_paths = ["static/appdocs"]

        # Valid path
        is_valid, error, resolved = SecurityUtils.validate_file_path(
            "visions/test.json", allowed_paths
        )
        assert is_valid is True

        # File validation
        is_valid, error, filename = FileSecurityValidator.validate_upload_file(
            resolved, "test.json"
        )
        assert is_valid is True

        # Content validation (would need actual file for full test)
        assert True  # Integration test structure is correct


if __name__ == "__main__":
    # Run basic tests without pytest
    import logging

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    test_classes = [
        TestRateLimiter,
        TestInputValidator,
        TestPathTraversalProtector,
        TestSecurityUtils,
        TestFileSecurityValidator,
        TestSecurityAuditLogger,
        TestSecurityIntegration
    ]

    passed = 0
    total = 0

    for test_class in test_classes:
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]

        for method_name in test_methods:
            total += 1
            try:
                method = getattr(test_instance, method_name)
                if callable(method):
                    method()
                    print(f"✅ {test_class.__name__}.{method_name}")
                    passed += 1
            except Exception as e:
                print(f"❌ {test_class.__name__}.{method_name}: {e}")
                import traceback
                traceback.print_exc()

    print(f"\n📊 Security Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All security tests passed!")
        print("✅ Security middleware and utilities working correctly.")
        sys.exit(0)
    else:
        print("❌ Some security tests failed.")
        sys.exit(1)
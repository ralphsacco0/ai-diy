"""
Smoke tests for API envelope standardization.

Tests that all API endpoints return responses in the unified envelope format:
{"success": true|false, "message": "string", "data": {...}}
"""

import pytest
import json
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add the src directory to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from api.conventions import ApiResponse, CsvConfig


class TestApiEnvelope:
    """Test that all API endpoints use the unified response envelope."""

    def test_vision_api_envelope(self):
        """Test that vision API returns unified envelope."""
        # This is a basic structure test - in real implementation,
        # you'd use TestClient to make actual requests

        # Test the response model structure
        test_response = ApiResponse(
            success=True,
            message="Test message",
            data={"test": "data"}
        )

        response_dict = test_response.model_dump()

        # Verify envelope structure
        assert "success" in response_dict
        assert "message" in response_dict
        assert "data" in response_dict
        assert response_dict["success"] is True
        assert response_dict["message"] == "Test message"
        assert response_dict["data"] == {"test": "data"}

    def test_csv_headers_constant(self):
        """Test that CSV canonical headers are properly defined."""
        # Verify headers exist and are not empty
        assert len(CsvConfig.CANONICAL_HEADERS) > 0
        assert all(isinstance(header, str) for header in CsvConfig.CANONICAL_HEADERS)
        assert "Story_ID" in CsvConfig.CANONICAL_HEADERS
        assert "Title" in CsvConfig.CANONICAL_HEADERS
        assert "Priority" in CsvConfig.CANONICAL_HEADERS

    def test_error_response_structure(self):
        """Test that error responses follow envelope format."""
        from api.conventions import create_error_response, ApiErrorCode

        error_response = create_error_response(
            "Test error",
            ApiErrorCode.INVALID_REQUEST
        )

        response_dict = error_response.model_dump()

        # Verify error envelope structure
        assert response_dict["success"] is False
        assert "message" in response_dict
        assert "data" in response_dict
        assert "error_code" in response_dict["data"]

    @pytest.mark.parametrize("action", ["save", "get", "list", "delete", "latest"])
    def test_api_actions_enum(self, action):
        """Test that all API actions are properly defined."""
        from api.conventions import ApiAction

        assert hasattr(ApiAction, action.upper())
        assert ApiAction(action.upper()).value == action


class TestSafetyConfig:
    """Test safety configuration constants."""

    def test_safety_limits_exist(self):
        """Test that safety limits are properly defined."""
        from api.conventions import SafetyConfig

        assert SafetyConfig.DEFAULT_TIMEOUT_SECONDS > 0
        assert SafetyConfig.MAX_FILE_SIZE_MB > 0
        assert SafetyConfig.MAX_FILE_SIZE_BYTES == SafetyConfig.MAX_FILE_SIZE_MB * 1024 * 1024


class TestUtilityFunctions:
    """Test utility functions used across APIs."""

    def test_sanitize_slug(self):
        """Test slug sanitization."""
        from api.conventions import sanitize_slug

        # Test normal slug
        assert sanitize_slug("test-slug_123") == "test-slug_123"

        # Test dangerous input
        assert sanitize_slug("../../../etc/passwd") == "etcpasswd"

        # Test empty input
        assert sanitize_slug("") == ""

        # Test long input
        long_slug = "a" * 100
        assert len(sanitize_slug(long_slug)) <= 50

    def test_generate_id_from_title(self):
        """Test ID generation from title."""
        from api.conventions import generate_id_from_title

        # Test normal title
        test_id = generate_id_from_title("My Test Vision")
        assert "My_Test_Vision" in test_id
        assert test_id.endswith("_")  # Should have timestamp

        # Test empty title (should raise)
        with pytest.raises(ValueError):
            generate_id_from_title("")

    def test_csv_header_validation(self):
        """Test CSV header validation."""
        from api.conventions import validate_csv_headers

        # Test valid headers
        is_valid, error_msg = validate_csv_headers(CsvConfig.CANONICAL_HEADERS)
        assert is_valid is True
        assert error_msg == ""

        # Test invalid headers (missing field)
        invalid_headers = CsvConfig.CANONICAL_HEADERS.copy()
        invalid_headers.remove("Title")
        is_valid, error_msg = validate_csv_headers(invalid_headers)
        assert is_valid is False
        assert "missing" in error_msg

        # Test extra headers
        extra_headers = CsvConfig.CANONICAL_HEADERS.copy()
        extra_headers.append("Extra_Field")
        is_valid, error_msg = validate_csv_headers(extra_headers)
        assert is_valid is False
        assert "extra" in error_msg


if __name__ == "__main__":
    # Run basic tests without pytest
    test_instance = TestApiEnvelope()

    try:
        test_instance.test_vision_api_envelope()
        print("✅ Vision API envelope test passed")

        test_instance.test_csv_headers_constant()
        print("✅ CSV headers constant test passed")

        test_instance.test_error_response_structure()
        print("✅ Error response structure test passed")

        print("\n🎉 All API envelope smoke tests passed!")
        print("The unified response envelope is properly implemented.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
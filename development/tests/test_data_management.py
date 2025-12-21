"""
Tests for data management functionality.

Tests overwrite-on-save behavior, CSV schema validation,
and data validation with fail-fast error handling.
"""

import pytest
import json
import csv
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent / "src"))

from data_manager import (
    DataManager, CsvValidator, SaveResult, ValidationResult,
    validate_and_save_vision, validate_and_save_backlog_csv,
    CsvConfig
)


class TestOverwriteOnSave:
    """Test overwrite-on-save behavior for visions."""

    def test_create_new_vision(self):
        """Test creating a new vision when no ID provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            vision_data = {
                "title": "Test Vision",
                "content": "Test content",
                "client_approval": True
            }

            result = manager.save_vision(vision_data)

            assert result.success is True
            assert result.is_overwrite is False
            assert "Test Vision" in result.message
            assert result.file_path.exists()

            # Verify file contents
            with open(result.file_path, 'r') as f:
                saved_data = json.load(f)

            assert saved_data["title"] == "Test Vision"
            assert saved_data["content"] == "Test content"
            assert saved_data["client_approval"] is True
            assert "id" in saved_data
            assert "updated_at" in saved_data

    def test_overwrite_existing_vision(self):
        """Test overwriting existing vision when ID provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            # Create initial vision
            vision_data = {
                "title": "Original Vision",
                "content": "Original content",
                "client_approval": False
            }

            result1 = manager.save_vision(vision_data)
            vision_id = result1.id

            # Overwrite with new data
            updated_data = {
                "title": "Updated Vision",
                "content": "Updated content",
                "client_approval": True
            }

            result2 = manager.save_vision(updated_data, vision_id)

            assert result2.success is True
            assert result2.is_overwrite is True
            assert result2.id == vision_id
            assert "updated" in result2.message

            # Verify updated contents
            with open(result2.file_path, 'r') as f:
                saved_data = json.load(f)

            assert saved_data["title"] == "Updated Vision"
            assert saved_data["content"] == "Updated content"
            assert saved_data["client_approval"] is True


class TestCsvSchemaValidation:
    """Test CSV schema validation."""

    def test_valid_csv_with_canonical_headers(self):
        """Test CSV with correct canonical headers."""
        csv_content = """Story_ID,Title,User_Story,Functional_Requirements,Non_Functional_Requirements,Integrations,Dependencies,Constraints,Acceptance_Criteria,Priority,Status,Vision_Ref,Wireframe_Ref,Notes
TR-1,Test Story,As a user...,Must have feature X,Should be fast,API integration,None,None,Must work in Chrome,"User can complete task",High,Open,VISION-1,test-wireframe,Notes here
TR-2,Another Story,As a user...,Must have feature Y,Should be secure,Database,None,None,Must work in Firefox,"User can see result",Medium,Open,VISION-1,,More notes"""

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            validation = manager._validate_csv_content(csv_content)

            assert validation.is_valid is True
            assert len(validation.errors) == 0

    def test_invalid_csv_missing_headers(self):
        """Test CSV with missing headers."""
        csv_content = """ID,Title,Description
1,Test,Missing headers"""

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            validation = manager._validate_csv_content(csv_content)

            assert validation.is_valid is False
            assert len(validation.errors) > 0
            assert any("missing" in error.lower() for error in validation.errors)

    def test_invalid_csv_extra_headers(self):
        """Test CSV with extra headers."""
        csv_content = """Story_ID,Title,User_Story,Extra_Column
TR-1,Test,As a user...,Extra data"""

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            validation = manager._validate_csv_content(csv_content)

            assert validation.is_valid is False
            assert len(validation.errors) > 0
            assert any("extra" in error.lower() for error in validation.errors)

    def test_invalid_csv_wrong_column_count(self):
        """Test CSV with wrong number of columns in data rows."""
        csv_content = """Story_ID,Title,User_Story
TR-1,Test Story,As a user...,Extra column
TR-2,Another Story,Missing column"""

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            validation = manager._validate_csv_content(csv_content)

            assert validation.is_valid is False
            assert len(validation.errors) > 0

    def test_empty_csv(self):
        """Test empty CSV content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            validation = manager._validate_csv_content("")

            assert validation.is_valid is False
            assert len(validation.errors) > 0
            assert any("empty" in error.lower() for error in validation.errors)

    def test_csv_headers_constant(self):
        """Test that CSV canonical headers constant is properly defined."""
        # Test that all expected headers are present
        required_headers = [
            "Story_ID", "Title", "User_Story", "Functional_Requirements",
            "Non_Functional_Requirements", "Integrations", "Dependencies",
            "Constraints", "Acceptance_Criteria", "Priority", "Status",
            "Vision_Ref", "Wireframe_Ref", "Notes"
        ]

        assert len(CsvConfig.CANONICAL_HEADERS) == len(required_headers)
        assert CsvConfig.CANONICAL_HEADERS == required_headers


class TestVisionValidation:
    """Test vision data validation."""

    def test_valid_vision_data(self):
        """Test valid vision data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            vision_data = {
                "title": "Valid Vision",
                "content": "Valid content",
                "client_approval": True
            }

            validation = manager._validate_vision_data(vision_data)

            assert validation.is_valid is True
            assert len(validation.errors) == 0

    def test_invalid_vision_missing_title(self):
        """Test vision data missing title."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            vision_data = {
                "content": "Content without title",
                "client_approval": True
            }

            validation = manager._validate_vision_data(vision_data)

            assert validation.is_valid is False
            assert len(validation.errors) > 0
            assert any("title" in error.lower() for error in validation.errors)

    def test_invalid_vision_missing_content(self):
        """Test vision data missing content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            vision_data = {
                "title": "Title without content",
                "client_approval": True
            }

            validation = manager._validate_vision_data(vision_data)

            assert validation.is_valid is False
            assert len(validation.errors) > 0
            assert any("content" in error.lower() for error in validation.errors)

    def test_invalid_vision_bad_client_approval(self):
        """Test vision data with invalid client_approval type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            vision_data = {
                "title": "Test Vision",
                "content": "Test content",
                "client_approval": "yes"  # Should be boolean
            }

            validation = manager._validate_vision_data(vision_data)

            assert validation.is_valid is False
            assert len(validation.errors) > 0
            assert any("boolean" in error.lower() for error in validation.errors)


class TestFileSizeLimits:
    """Test file size limits."""

    def test_vision_file_size_limit(self):
        """Test that vision files respect size limits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            # Create vision data that exceeds size limit
            large_content = "x" * (SafetyConfig.MAX_FILE_SIZE_BYTES + 1000)
            vision_data = {
                "title": "Large Vision",
                "content": large_content,
                "client_approval": True
            }

            with pytest.raises(ValueError) as exc_info:
                manager.save_vision(vision_data)

            assert "too large" in str(exc_info.value)


class TestCsvValidator:
    """Test CSV validator static methods."""

    def test_validate_csv_file_valid(self):
        """Test validating a valid CSV file."""
        csv_content = """Story_ID,Title,User_Story
TR-1,Test,As a user..."""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                is_valid, errors = CsvValidator.validate_csv_file(Path(f.name))
                assert is_valid is True
                assert len(errors) == 0
            finally:
                Path(f.name).unlink()

    def test_validate_csv_file_invalid(self):
        """Test validating an invalid CSV file."""
        csv_content = """Invalid,CSV,Format
Missing,Headers"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                is_valid, errors = CsvValidator.validate_csv_file(Path(f.name))
                assert is_valid is False
                assert len(errors) > 0
            finally:
                Path(f.name).unlink()

    def test_get_csv_headers(self):
        """Test getting CSV headers."""
        csv_content = """Header1,Header2,Header3
Value1,Value2,Value3"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                headers = CsvValidator.get_csv_headers(Path(f.name))
                assert headers == ["Header1", "Header2", "Header3"]
            finally:
                Path(f.name).unlink()


class TestIntegration:
    """Integration tests for data management."""

    def test_vision_save_and_retrieve(self):
        """Test saving and retrieving vision documents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            vision_data = {
                "title": "Integration Test Vision",
                "content": "Test content for integration",
                "client_approval": True
            }

            # Save vision
            result = manager.save_vision(vision_data)
            assert result.success is True

            # Retrieve vision
            retrieved = manager.get_vision(result.id)
            assert retrieved is not None
            assert retrieved["title"] == "Integration Test Vision"
            assert retrieved["content"] == "Test content for integration"

            # List visions
            visions = manager.list_visions()
            assert len(visions) == 1
            assert visions[0]["id"] == result.id

    def test_backlog_csv_save_and_validate(self):
        """Test saving and validating backlog CSV."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataManager(temp_dir)

            csv_content = """Story_ID,Title,User_Story,Functional_Requirements,Non_Functional_Requirements,Integrations,Dependencies,Constraints,Acceptance_Criteria,Priority,Status,Vision_Ref,Wireframe_Ref,Notes
TR-1,Test Feature,As a user...,Must have X,Should be fast,API,None,None,Works in browser,"User sees result",High,Open,VISION-1,test-frame,Notes"""

            # Save CSV
            result = manager.save_backlog_csv(csv_content)
            assert result.success is True

            # Verify file exists and has correct content
            assert result.file_path.exists()
            with open(result.file_path, 'r') as f:
                saved_content = f.read()
            assert "Test Feature" in saved_content


if __name__ == "__main__":
    # Run basic tests without pytest
    import sys

    test_classes = [
        TestOverwriteOnSave,
        TestCsvSchemaValidation,
        TestVisionValidation,
        TestCsvValidator,
        TestIntegration
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

    print(f"\n📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All data management tests passed!")
        print("✅ Overwrite-on-save behavior and CSV validation working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed.")
        sys.exit(1)
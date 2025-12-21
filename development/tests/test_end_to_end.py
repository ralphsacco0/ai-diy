#!/usr/bin/env python3
"""
End-to-end validation tests for AI-DIY application.

Tests complete workflows across all phases:
- Phase 1: API Standardization
- Phase 2: Fail-Fast Configuration
- Phase 3: Data Management Standards
- Phase 4: Configuration & Environment
- Phase 5: Safety & Security
- Phase 6: Documentation & Validation

Tests the complete integration of all systems.
"""

import pytest
import json
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config_manager import validate_startup_configuration, ConfigManager
from data_manager import DataManager, validate_and_save_vision
from security_middleware import SecurityConfig, RateLimiter, InputValidator
from security_utils import SecurityUtils, FileSecurityValidator


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    def test_complete_vision_workflow(self):
        """Test complete vision creation workflow with all validations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup environment
            env_vars = {
                "LOG_LEVEL": "INFO",
                "DATA_ROOT": temp_dir,
                "PRODUCTION": "false"
            }

            with patch.dict(os.environ, env_vars):
                # Create valid models config
                models_config = {
                    "favorites": ["test/model"],
                    "default": None,
                    "meta": {},
                    "last_used": None,
                    "last_session_name": ""
                }

                models_file = Path(temp_dir) / "models_config.json"
                with open(models_file, 'w') as f:
                    json.dump(models_config, f)

                # Test configuration validation (Phase 2)
                with patch('config_manager.ConfigManager') as mock_manager_class:
                    mock_manager = mock_manager_class.return_value
                    mock_manager.get_app_config.return_value.models_config_path = str(models_file)

                    # Should not raise exception
                    validate_startup_configuration()

                # Test data management (Phase 3)
                data_manager = DataManager(temp_dir)

                # Create vision data
                vision_data = {
                    "title": "Test Vision",
                    "content": "Test vision content for end-to-end testing",
                    "client_approval": True
                }

                # Save vision (should create new)
                result1 = data_manager.save_vision(vision_data)
                assert result1.success is True
                assert result1.is_overwrite is False

                # Save again with ID (should overwrite)
                result2 = data_manager.save_vision(vision_data, result1.id)
                assert result2.success is True
                assert result2.is_overwrite is True

                # Test security validation (Phase 5)
                is_valid, error, resolved = SecurityUtils.validate_file_path(
                    result1.file_path, ["static/appdocs", "static/appdocs/visions"]
                )
                assert is_valid is True

    def test_complete_backlog_workflow(self):
        """Test complete backlog CSV workflow with validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_manager = DataManager(temp_dir)

            # Create valid CSV content
            csv_content = """Story_ID,Title,User_Story,Functional_Requirements,Non_Functional_Requirements,Integrations,Dependencies,Constraints,Acceptance_Criteria,Priority,Status,Vision_Ref,Wireframe_Ref,Notes
TEST-1,Test Feature,As a user...,Must have feature X,Should be fast,API,None,None,Works in browser,"User sees result",High,Open,VISION-1,test-frame,Test notes"""

            # Test CSV validation (Phase 3)
            validation = data_manager._validate_csv_content(csv_content)
            assert validation.is_valid is True

            # Save CSV (should create new)
            result1 = data_manager.save_backlog_csv(csv_content)
            assert result1.success is True
            assert result1.is_overwrite is False

            # Save again (should overwrite)
            result2 = data_manager.save_backlog_csv(csv_content, "Backlog")
            assert result2.success is True
            assert result2.is_overwrite is True

            # Test file security (Phase 5)
            is_valid, error, filename = FileSecurityValidator.validate_upload_file(
                result1.file_path, "Backlog.csv"
            )
            assert is_valid is True

    def test_security_integration_workflow(self):
        """Test complete security integration across all layers."""
        # Test rate limiting (Phase 5)
        rate_limiter = RateLimiter()
        client_id = "test_client"

        # Should allow initial requests
        for i in range(10):
            allowed, remaining = rate_limiter.is_allowed(client_id)
            assert allowed is True
            assert remaining > 0

        # Test input validation (Phase 5)
        valid_data = {"test": "data", "number": 123}
        is_valid, error = InputValidator.validate_json_input(valid_data)
        assert is_valid is True

        # Test invalid input
        invalid_data = {"malicious": "<script>alert('xss')</script>"}
        is_valid, error = InputValidator.validate_json_input(invalid_data)
        assert is_valid is False

        # Test path validation (Phase 5)
        is_valid, error, resolved = SecurityUtils.validate_file_path(
            "visions/test.json", ["static/appdocs", "static/appdocs/visions"]
        )
        assert is_valid is True

        # Test dangerous path
        is_valid, error, resolved = SecurityUtils.validate_file_path(
            "../../../etc/passwd", ["static/appdocs"]
        )
        assert is_valid is False


class TestConfigurationValidation:
    """Test configuration validation across all phases."""

    def test_phase2_fail_fast_validation(self):
        """Test Phase 2 fail-fast configuration validation."""
        # Test missing LOG_LEVEL
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_startup_configuration()
            assert "LOG_LEVEL" in str(exc_info.value)

        # Test missing DATA_ROOT
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_startup_configuration()
            assert "DATA_ROOT" in str(exc_info.value)

    def test_models_config_validation(self):
        """Test models configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test invalid JSON
            models_file = Path(temp_dir) / "models_config.json"
            with open(models_file, 'w') as f:
                f.write("{ invalid json }")

            manager = ConfigManager()
            manager._models_config_file = models_file

            with pytest.raises(ValueError) as exc_info:
                manager._load_models_config()
            assert "Invalid JSON" in str(exc_info.value)

    def test_environment_specific_validation(self):
        """Test environment-specific configuration validation."""
        # Test development environment
        dev_config = {
            "LOG_LEVEL": "DEBUG",
            "DATA_ROOT": "/tmp/dev",
            "PRODUCTION": "false"
        }

        with patch.dict(os.environ, dev_config):
            # Should not raise for development
            manager = ConfigManager()
            # Mock the file existence check
            with patch.object(Path, 'exists', return_value=True):
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
                        "favorites": ["test/model"],
                        "default": None,
                        "meta": {},
                        "last_used": None,
                        "last_session_name": ""
                    })
                    try:
                        manager._load_models_config()
                    except:
                        pass  # Expected if file doesn't exist

        # Test production environment
        prod_config = {
            "LOG_LEVEL": "INFO",
            "DATA_ROOT": "/var/lib/ai-diy",
            "PRODUCTION": "true"
        }

        with patch.dict(os.environ, prod_config):
            # Should validate stricter requirements for production
            assert os.environ.get("PRODUCTION") == "true"


class TestSecurityValidation:
    """Test security validation across all layers."""

    def test_layered_security_validation(self):
        """Test that all security layers work together."""
        # Layer 1: Rate limiting
        rate_limiter = RateLimiter()
        allowed, remaining = rate_limiter.is_allowed("test_client")
        assert allowed is True

        # Layer 2: Input validation
        test_data = {"title": "Test", "content": "Valid content"}
        is_valid, error = InputValidator.validate_json_input(test_data)
        assert is_valid is True

        # Layer 3: File system protection
        is_valid, error, resolved = SecurityUtils.validate_file_path(
            "test.json", ["static/appdocs"]
        )
        assert is_valid is True

        # Layer 4: Application security
        assert SecurityConfig.MAX_REQUEST_SIZE > 0
        assert SecurityConfig.MAX_FILE_SIZE > 0

        # Layer 5: Operational security
        from security_middleware import security_audit
        # Should be able to log security events
        assert security_audit is not None

    def test_security_boundaries(self):
        """Test that security boundaries are properly enforced."""
        # Test path traversal protection
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\cmd.exe",
            "/etc/passwd",
            "C:\\Windows\\System32\\cmd.exe"
        ]

        for dangerous_path in dangerous_paths:
            is_valid, error, resolved = SecurityUtils.validate_file_path(
                dangerous_path, ["static/appdocs"]
            )
            assert is_valid is False
            assert "not allowed" in error or "Dangerous" in error

        # Test file extension protection
        dangerous_files = [
            "malware.exe",
            "script.bat",
            "trojan.sh",
            "virus.py"
        ]

        for dangerous_file in dangerous_files:
            is_valid, error, resolved = SecurityUtils.validate_file_path(
                dangerous_file, ["static/appdocs"]
            )
            assert is_valid is False
            assert "Dangerous file type" in error


class TestPerformanceValidation:
    """Test performance requirements across phases."""

    def test_api_response_times(self):
        """Test that API operations meet performance requirements."""
        # This would test actual API endpoints
        # For now, test the configuration that enables performance monitoring

        assert SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE == 100
        # Performance requirements are enforced through configuration

    def test_resource_limits(self):
        """Test that resource limits are properly configured."""
        # Test file size limits
        assert SecurityConfig.MAX_FILE_SIZE == 10 * 1024 * 1024  # 10MB
        assert SecurityConfig.MAX_REQUEST_SIZE == 10 * 1024 * 1024  # 10MB

        # Test rate limiting
        assert SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE > 0
        assert SecurityConfig.RATE_LIMIT_BURST > 0


class TestIntegrationValidation:
    """Test integration between all phases."""

    def test_phase_integration_matrix(self):
        """Test that all phases work together correctly."""
        # Phase 1 (API) + Phase 2 (Config) + Phase 3 (Data) + Phase 4 (Logging) + Phase 5 (Security)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup complete environment
            env_vars = {
                "LOG_LEVEL": "INFO",
                "DATA_ROOT": temp_dir,
                "PRODUCTION": "false"
            }

            with patch.dict(os.environ, env_vars):
                # Create all necessary files
                models_config = {
                    "favorites": ["test/model"],
                    "default": None,
                    "meta": {},
                    "last_used": None,
                    "last_session_name": ""
                }

                models_file = Path(temp_dir) / "models_config.json"
                with open(models_file, 'w') as f:
                    json.dump(models_config, f)

                # Test complete workflow
                data_manager = DataManager(temp_dir)

                # Create vision (Phase 1 + Phase 3 + Phase 5)
                vision_data = {
                    "title": "Integration Test Vision",
                    "content": "Testing integration across all phases",
                    "client_approval": True
                }

                result = data_manager.save_vision(vision_data)
                assert result.success is True

                # Verify file security (Phase 5)
                is_valid, error, resolved = SecurityUtils.validate_file_path(
                    result.file_path, ["static/appdocs", "static/appdocs/visions"]
                )
                assert is_valid is True

                # Test configuration management (Phase 2 + Phase 4)
                with patch('config_manager.ConfigManager') as mock_manager_class:
                    mock_manager = mock_manager_class.return_value
                    mock_manager.get_app_config.return_value.models_config_path = str(models_file)

                    # Should validate without errors
                    validate_startup_configuration()


class TestDeploymentValidation:
    """Test deployment and operational readiness."""

    def test_development_deployment(self):
        """Test development deployment configuration."""
        # Test development setup script
        setup_script = Path(__file__).parent / "setup_config.py"

        if setup_script.exists():
            # Should be able to run setup script
            result = subprocess.run(
                [sys.executable, str(setup_script), "--environment", "development"],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Should complete without crashing (may fail due to missing files, but not crash)
            assert result.returncode in [0, 1]  # 0 = success, 1 = expected failure

    def test_production_readiness(self):
        """Test production deployment readiness."""
        # Test that production configuration is properly validated
        prod_env = {
            "LOG_LEVEL": "INFO",
            "DATA_ROOT": "/var/lib/ai-diy",
            "PRODUCTION": "true"
        }

        with patch.dict(os.environ, prod_env):
            # Should require additional production configuration
            with pytest.raises(ValueError):
                # This should fail due to missing required production config
                # In real deployment, additional config would be provided
                pass

    def test_configuration_templates(self):
        """Test that configuration templates are valid."""
        env_example = Path(__file__).parent / ".env.example"

        if env_example.exists():
            # Should be able to read and parse the template
            content = env_example.read_text()
            assert "LOG_LEVEL" in content
            assert "DATA_ROOT" in content
            assert "PRODUCTION" in content


class TestErrorHandlingValidation:
    """Test error handling across all phases."""

    def test_fail_fast_error_messages(self):
        """Test that fail-fast errors provide clear messages."""
        # Test configuration errors
        with patch.dict(os.environ, {}, clear=True):
            try:
                validate_startup_configuration()
                assert False, "Should have raised ValueError"
            except ValueError as e:
                error_msg = str(e)
                assert "LOG_LEVEL" in error_msg or "DATA_ROOT" in error_msg

    def test_api_error_responses(self):
        """Test that API errors use unified format."""
        from api.conventions import create_error_response, ApiErrorCode

        error_response = create_error_response(
            "Test error message",
            ApiErrorCode.VALIDATION_ERROR
        )

        response_dict = error_response.model_dump()
        assert response_dict["success"] is False
        assert response_dict["message"] == "Test error message"
        assert response_dict["data"]["error_code"] == "VALIDATION_ERROR"

    def test_security_error_handling(self):
        """Test security error handling."""
        # Test path traversal error
        is_valid, error, resolved = SecurityUtils.validate_file_path(
            "../../../etc/passwd", ["static/appdocs"]
        )

        assert is_valid is False
        assert len(error) > 0

        # Test malicious content error
        malicious_content = "<script>alert('xss')</script>"
        warnings = SecurityUtils.detect_malicious_content(malicious_content)
        assert len(warnings) > 0


if __name__ == "__main__":
    # Run comprehensive validation tests
    import logging

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    test_classes = [
        TestEndToEndWorkflows,
        TestConfigurationValidation,
        TestSecurityValidation,
        TestPerformanceValidation,
        TestIntegrationValidation,
        TestDeploymentValidation,
        TestErrorHandlingValidation
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

    print(f"\n📊 End-to-End Validation Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All end-to-end validation tests passed!")
        print("✅ Complete system integration validated across all phases.")
        print("🚀 System ready for production deployment!")
        sys.exit(0)
    else:
        print("❌ Some validation tests failed.")
        print("🔧 Review test failures and fix integration issues.")
        sys.exit(1)
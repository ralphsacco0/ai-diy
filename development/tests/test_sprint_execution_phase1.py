"""
Unit tests for Phase 1: Context Injection & Validation

Tests the following:
- Context injection methods
- Task breakdown validation
- Code output validation
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# Import the orchestrator
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.sprint_orchestrator import SprintOrchestrator, OrchestratorConfig


@dataclass
class TestConfig:
    """Test configuration"""
    sprint_id: str = "SP-TEST-001"


class TestContextInjection:
    """Test context injection methods"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_get_project_context_new_project(self, orchestrator):
        """Test context for new project (doesn't exist yet)"""
        context = orchestrator._get_project_context("NonExistentProject")
        assert isinstance(context, str)
        assert "does not exist yet" in context or "PROJECT STRUCTURE" in context
    
    def test_get_project_context_returns_string(self, orchestrator):
        """Test that project context returns a string"""
        context = orchestrator._get_project_context("TestProject")
        assert isinstance(context, str)
        assert len(context) > 0
    
    def test_get_file_summaries_no_files(self, orchestrator):
        """Test file summaries with no files to modify"""
        summaries = orchestrator._get_file_summaries("TestProject", [])
        assert isinstance(summaries, str)
        assert "No existing files" in summaries or len(summaries) > 0
    
    def test_get_file_summaries_returns_string(self, orchestrator):
        """Test that file summaries returns a string"""
        summaries = orchestrator._get_file_summaries("TestProject", ["routes/auth.py"])
        assert isinstance(summaries, str)
        assert len(summaries) > 0
    
    def test_get_existing_patterns_returns_string(self, orchestrator):
        """Test that existing patterns returns a string"""
        patterns = orchestrator._get_existing_patterns("TestProject")
        assert isinstance(patterns, str)
        assert "EXISTING CODE PATTERNS" in patterns or len(patterns) > 0
    
    def test_get_existing_patterns_contains_conventions(self, orchestrator):
        """Test that patterns include naming conventions"""
        patterns = orchestrator._get_existing_patterns("TestProject")
        assert "Naming Conventions" in patterns or "naming" in patterns.lower()


class TestTaskBreakdownValidation:
    """Test task breakdown validation"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_valid_breakdown_passes(self, orchestrator):
        """Test that valid breakdown passes validation"""
        valid_breakdown = {
            "tasks": [
                {"task_id": "1", "description": "Create auth routes"},
                {"task_id": "2", "description": "Create user model"}
            ]
        }
        assert orchestrator._validate_task_breakdown(valid_breakdown) is True
    
    def test_empty_tasks_fails(self, orchestrator):
        """Test that breakdown with no tasks fails"""
        invalid_breakdown = {"tasks": []}
        assert orchestrator._validate_task_breakdown(invalid_breakdown) is False
    
    def test_missing_task_id_fails(self, orchestrator):
        """Test that task missing task_id fails"""
        invalid_breakdown = {
            "tasks": [
                {"description": "Create auth routes"}  # Missing task_id
            ]
        }
        assert orchestrator._validate_task_breakdown(invalid_breakdown) is False
    
    def test_missing_description_fails(self, orchestrator):
        """Test that task missing description fails"""
        invalid_breakdown = {
            "tasks": [
                {"task_id": "1"}  # Missing description
            ]
        }
        assert orchestrator._validate_task_breakdown(invalid_breakdown) is False
    
    def test_duplicate_task_ids_fails(self, orchestrator):
        """Test that duplicate task IDs fail"""
        invalid_breakdown = {
            "tasks": [
                {"task_id": "1", "description": "Task 1"},
                {"task_id": "1", "description": "Task 2"}  # Duplicate ID
            ]
        }
        assert orchestrator._validate_task_breakdown(invalid_breakdown) is False
    
    def test_not_dict_fails(self, orchestrator):
        """Test that non-dict breakdown fails"""
        assert orchestrator._validate_task_breakdown("not a dict") is False
    
    def test_tasks_not_list_fails(self, orchestrator):
        """Test that tasks not being a list fails"""
        invalid_breakdown = {"tasks": "not a list"}
        assert orchestrator._validate_task_breakdown(invalid_breakdown) is False


class TestCodeOutputValidation:
    """Test code output validation"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_valid_code_passes(self, orchestrator):
        """Test that valid code passes validation"""
        valid_code = {
            "files": [
                {"path": "routes/auth.py", "content": "def login(): pass"}
            ]
        }
        assert orchestrator._validate_code_output(valid_code) is True
    
    def test_valid_code_multiple_files(self, orchestrator):
        """Test that valid code with multiple files passes"""
        valid_code = {
            "files": [
                {"path": "routes/auth.py", "content": "def login(): pass"},
                {"path": "templates/login.html", "content": "<html></html>"}
            ]
        }
        assert orchestrator._validate_code_output(valid_code) is True
    
    def test_dict_format_files_passes(self, orchestrator):
        """Test that dict format for files passes (converted to list)"""
        valid_code = {
            "files": {
                "routes/auth.py": "def login(): pass",
                "templates/login.html": "<html></html>"
            }
        }
        assert orchestrator._validate_code_output(valid_code) is True
    
    def test_missing_files_field_fails(self, orchestrator):
        """Test that missing files field fails"""
        invalid_code = {"task_id": "1"}  # Missing files field
        assert orchestrator._validate_code_output(invalid_code) is False
    
    def test_empty_files_fails(self, orchestrator):
        """Test that empty files list fails"""
        invalid_code = {"files": []}
        assert orchestrator._validate_code_output(invalid_code) is False
    
    def test_missing_path_fails(self, orchestrator):
        """Test that file missing path fails"""
        invalid_code = {
            "files": [
                {"content": "def login(): pass"}  # Missing path
            ]
        }
        assert orchestrator._validate_code_output(invalid_code) is False
    
    def test_missing_content_fails(self, orchestrator):
        """Test that file missing content fails"""
        invalid_code = {
            "files": [
                {"path": "routes/auth.py"}  # Missing content
            ]
        }
        assert orchestrator._validate_code_output(invalid_code) is False
    
    def test_path_traversal_fails(self, orchestrator):
        """Test that path traversal attempts fail"""
        invalid_code = {
            "files": [
                {"path": "../../../etc/passwd", "content": "malicious"}
            ]
        }
        assert orchestrator._validate_code_output(invalid_code) is False
    
    def test_absolute_path_fails(self, orchestrator):
        """Test that absolute paths fail"""
        invalid_code = {
            "files": [
                {"path": "/etc/passwd", "content": "malicious"}
            ]
        }
        assert orchestrator._validate_code_output(invalid_code) is False
    
    def test_python_syntax_error_fails(self, orchestrator):
        """Test that Python syntax errors fail"""
        invalid_code = {
            "files": [
                {"path": "routes/auth.py", "content": "def login( pass"}  # Syntax error
            ]
        }
        assert orchestrator._validate_code_output(invalid_code) is False
    
    def test_valid_python_syntax_passes(self, orchestrator):
        """Test that valid Python syntax passes"""
        valid_code = {
            "files": [
                {"path": "routes/auth.py", "content": """
def login(username, password):
    if not username or not password:
        return {"status": "error", "message": "Missing credentials"}
    return {"status": "ok", "data": {"token": "abc123"}}
"""}
            ]
        }
        assert orchestrator._validate_code_output(valid_code) is True
    
    def test_not_dict_fails(self, orchestrator):
        """Test that non-dict code result fails"""
        assert orchestrator._validate_code_output("not a dict") is False
    
    def test_files_not_list_fails(self, orchestrator):
        """Test that files not being list or dict fails"""
        invalid_code = {"files": "not a list"}
        assert orchestrator._validate_code_output(invalid_code) is False


class TestValidationIntegration:
    """Integration tests for validation in context"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_realistic_task_breakdown(self, orchestrator):
        """Test realistic task breakdown from Mike"""
        realistic_breakdown = {
            "tasks": [
                {
                    "task_id": "1",
                    "description": "Create Flask app entry point",
                    "files_to_create": ["app.py"]
                },
                {
                    "task_id": "2",
                    "description": "Create authentication routes",
                    "files_to_create": ["routes/auth.py"]
                },
                {
                    "task_id": "3",
                    "description": "Create user model",
                    "files_to_create": ["models/user.py"]
                }
            ],
            "technical_notes": "Start with app.py, then routes, then models"
        }
        assert orchestrator._validate_task_breakdown(realistic_breakdown) is True
    
    def test_realistic_code_output(self, orchestrator):
        """Test realistic code output from Alex"""
        realistic_code = {
            "task_id": "1",
            "story_id": "US-001",
            "files": [
                {
                    "path": "app.py",
                    "content": """from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
""",
                    "action": "create"
                }
            ],
            "implementation_notes": "Basic Flask app setup"
        }
        assert orchestrator._validate_code_output(realistic_code) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

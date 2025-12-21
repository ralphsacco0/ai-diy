"""
Unit tests for Phase 3: Autonomous Bug Fixing

Tests the following:
- Issue tracking and reporting
- Bug fix workflow
- Feedback loop
- Scope guardrails
- Sprint review workflow
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dataclasses import dataclass

# Import the orchestrator
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.sprint_orchestrator import SprintOrchestrator, OrchestratorConfig


class TestIssueTracking:
    """Test issue tracking and reporting"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_create_issue(self, orchestrator):
        """Test creating an issue"""
        issue = orchestrator._create_issue(
            project_name="TestProject",
            story_id="US-001",
            issue_type="test_failure",
            description="Login test failing",
            error_message="AssertionError: Expected 200, got 500",
            file_path="routes/auth.py",
            line_number=42
        )
        
        assert issue.issue_id.startswith("ISSUE-")
        assert issue.project_name == "TestProject"
        assert issue.story_id == "US-001"
        assert issue.issue_type == "test_failure"
        assert issue.description == "Login test failing"
        assert issue.file_path == "routes/auth.py"
        assert issue.line_number == 42
    
    def test_issue_to_dict(self, orchestrator):
        """Test converting issue to dict"""
        issue = orchestrator._create_issue(
            project_name="TestProject",
            story_id="US-001",
            issue_type="syntax_error",
            description="Syntax error in auth.py",
            error_message="SyntaxError: invalid syntax"
        )
        
        issue_dict = issue.to_dict()
        assert isinstance(issue_dict, dict)
        assert issue_dict["issue_id"] == issue.issue_id
        assert issue_dict["project_name"] == "TestProject"
        assert issue_dict["issue_type"] == "syntax_error"
    
    def test_report_issue(self, orchestrator):
        """Test reporting an issue"""
        issue = orchestrator._create_issue(
            project_name="TestProject",
            story_id="US-001",
            issue_type="test_failure",
            description="Test failed",
            error_message="Error details"
        )
        
        result = orchestrator._report_issue(issue)
        assert result is True
    
    def test_issue_types(self, orchestrator):
        """Test different issue types"""
        issue_types = ["test_failure", "syntax_error", "import_error", "runtime_error"]
        
        for issue_type in issue_types:
            issue = orchestrator._create_issue(
                project_name="TestProject",
                story_id="US-001",
                issue_type=issue_type,
                description=f"Test {issue_type}",
                error_message="Error"
            )
            assert issue.issue_type == issue_type


class TestBugFixWorkflow:
    """Test bug fix workflow"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_fix_bug_scope_violation_do_not_modify(self, orchestrator):
        """Test that fix respects do-not-modify list"""
        issue = orchestrator._create_issue(
            project_name="TestProject",
            story_id="US-001",
            issue_type="test_failure",
            description="Test failed",
            error_message="Error"
        )
        
        original_requirement = {
            "story_id": "US-001",
            "title": "User login",
            "user_story": "As a user, I can log in",
            "acceptance_criteria": "User enters email and password"
        }
        
        scope_files = ["routes/auth.py"]
        do_not_modify = ["models/user.py", "app.py"]
        
        # Mock the API call to return code that violates scope
        with patch.object(orchestrator, 'call_openrouter_api') as mock_api:
            mock_api.return_value = json.dumps({
                "files": [
                    {"path": "models/user.py", "content": "# Modified user model"}
                ]
            })
            
            result = orchestrator._fix_bug(
                "TestProject", issue, original_requirement,
                scope_files, do_not_modify
            )
            
            # Should fail because it tried to modify do_not_modify file
            assert result is None
    
    def test_fix_bug_scope_violation_not_in_scope(self, orchestrator):
        """Test that fix only modifies allowed files"""
        issue = orchestrator._create_issue(
            project_name="TestProject",
            story_id="US-001",
            issue_type="test_failure",
            description="Test failed",
            error_message="Error"
        )
        
        original_requirement = {
            "story_id": "US-001",
            "title": "User login",
            "user_story": "As a user, I can log in",
            "acceptance_criteria": "User enters email and password"
        }
        
        scope_files = ["routes/auth.py"]
        do_not_modify = []
        
        # Mock the API call to return code for wrong file
        with patch.object(orchestrator, 'call_openrouter_api') as mock_api:
            mock_api.return_value = json.dumps({
                "files": [
                    {"path": "routes/users.py", "content": "# Wrong file"}
                ]
            })
            
            result = orchestrator._fix_bug(
                "TestProject", issue, original_requirement,
                scope_files, do_not_modify
            )
            
            # Should fail because file not in scope
            assert result is None
    
    def test_fix_bug_valid_scope(self, orchestrator):
        """Test that fix within scope passes"""
        issue = orchestrator._create_issue(
            project_name="TestProject",
            story_id="US-001",
            issue_type="test_failure",
            description="Test failed",
            error_message="Error"
        )
        
        original_requirement = {
            "story_id": "US-001",
            "title": "User login",
            "user_story": "As a user, I can log in",
            "acceptance_criteria": "User enters email and password"
        }
        
        scope_files = ["routes/auth.py"]
        do_not_modify = []
        
        # Mock the API call to return valid code
        with patch.object(orchestrator, 'call_openrouter_api') as mock_api:
            mock_api.return_value = json.dumps({
                "files": [
                    {"path": "routes/auth.py", "content": "def login(): pass"}
                ]
            })
            
            result = orchestrator._fix_bug(
                "TestProject", issue, original_requirement,
                scope_files, do_not_modify
            )
            
            # Should succeed
            assert result is not None
            assert "files" in result


class TestScopeGuardrails:
    """Test scope guardrails"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_scope_boundary_enforcement(self, orchestrator):
        """Test that scope boundaries are enforced"""
        issue = orchestrator._create_issue(
            project_name="TestProject",
            story_id="US-001",
            issue_type="test_failure",
            description="Test failed",
            error_message="Error"
        )
        
        original_requirement = {
            "story_id": "US-001",
            "title": "User login",
            "user_story": "As a user, I can log in",
            "acceptance_criteria": "User enters email and password"
        }
        
        # Only auth.py can be modified
        scope_files = ["routes/auth.py"]
        do_not_modify = ["models/user.py", "app.py", "config.py"]
        
        # Mock API to return code for allowed file
        with patch.object(orchestrator, 'call_openrouter_api') as mock_api:
            mock_api.return_value = json.dumps({
                "files": [
                    {"path": "routes/auth.py", "content": "def login(): pass"}
                ]
            })
            
            result = orchestrator._fix_bug(
                "TestProject", issue, original_requirement,
                scope_files, do_not_modify
            )
            
            assert result is not None
    
    def test_do_not_modify_list_respected(self, orchestrator):
        """Test that do-not-modify list is respected"""
        issue = orchestrator._create_issue(
            project_name="TestProject",
            story_id="US-001",
            issue_type="test_failure",
            description="Test failed",
            error_message="Error"
        )
        
        original_requirement = {
            "story_id": "US-001",
            "title": "User login",
            "user_story": "As a user, I can log in",
            "acceptance_criteria": "User enters email and password"
        }
        
        scope_files = ["routes/auth.py"]
        do_not_modify = ["app.py", "config.py"]
        
        # Mock API to try to modify app.py
        with patch.object(orchestrator, 'call_openrouter_api') as mock_api:
            mock_api.return_value = json.dumps({
                "files": [
                    {"path": "app.py", "content": "# Modified app"}
                ]
            })
            
            result = orchestrator._fix_bug(
                "TestProject", issue, original_requirement,
                scope_files, do_not_modify
            )
            
            # Should fail
            assert result is None


class TestSprintReview:
    """Test sprint review workflow"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    @pytest.mark.asyncio
    async def test_sprint_review_no_issues(self, orchestrator):
        """Test sprint review when all tests pass"""
        # Mock _run_tests to return success
        with patch.object(orchestrator, '_run_tests', new_callable=AsyncMock) as mock_tests:
            mock_tests.return_value = {
                "success": True,
                "test_count": 5,
                "passed": 5,
                "failed": 0,
                "error": None
            }
            
            result = await orchestrator.sprint_review("TestProject", [])
            
            assert result["status"] == "success"
            assert result["issues_found"] == 0
            assert result["issues_fixed"] == 0
    
    @pytest.mark.asyncio
    async def test_sprint_review_with_failures(self, orchestrator):
        """Test sprint review when tests fail"""
        # Mock _run_tests to return failures
        with patch.object(orchestrator, '_run_tests', new_callable=AsyncMock) as mock_tests:
            mock_tests.return_value = {
                "success": False,
                "test_count": 5,
                "passed": 3,
                "failed": 2,
                "error": "Some tests failed"
            }
            
            with patch.object(orchestrator, '_autonomous_fix_loop', new_callable=AsyncMock) as mock_fix:
                mock_fix.return_value = True  # Fix succeeds
                
                stories = [{
                    "Story_ID": "US-001",
                    "Title": "User login",
                    "User_Story": "As a user, I can log in",
                    "Acceptance_Criteria": "User enters email and password",
                    "files_to_create": ["routes/auth.py"]
                }]
                
                result = await orchestrator.sprint_review("TestProject", stories)
                
                assert result["issues_found"] == 2
                assert result["issues_fixed"] == 2


class TestIntegrationPhase3:
    """Integration tests for Phase 3"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_realistic_issue_scenario(self, orchestrator):
        """Test realistic issue scenario"""
        # Create an issue
        issue = orchestrator._create_issue(
            project_name="LoginApp",
            story_id="US-001",
            issue_type="test_failure",
            description="Login endpoint returns 500 instead of 200",
            error_message="AssertionError: Expected 200, got 500",
            file_path="routes/auth.py",
            line_number=42
        )
        
        # Report it
        reported = orchestrator._report_issue(issue)
        assert reported is True
        
        # Verify issue has all required fields
        assert issue.issue_id
        assert issue.project_name == "LoginApp"
        assert issue.story_id == "US-001"
        assert issue.issue_type == "test_failure"
        assert issue.timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

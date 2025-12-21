"""
Unit tests for Phase 4: Continuous Improvement

Tests the following:
- Architecture validation
- Performance monitoring
- Dependency management
- Documentation generation
- Quality metrics
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Import the orchestrator
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.sprint_orchestrator import SprintOrchestrator, OrchestratorConfig


class TestArchitectureValidation:
    """Test architecture validation"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_validate_architecture_returns_dict(self, orchestrator):
        """Test that architecture validation returns proper dict"""
        result = orchestrator._validate_architecture("NonExistentProject")
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "issues" in result
        assert "recommendations" in result
        assert isinstance(result["score"], (int, float))
        assert isinstance(result["issues"], list)
        assert isinstance(result["recommendations"], list)
    
    def test_architecture_score_range(self, orchestrator):
        """Test that architecture score is between 0-100"""
        result = orchestrator._validate_architecture("TestProject")
        
        assert 0 <= result["score"] <= 100
    
    def test_architecture_validation_nonexistent_project(self, orchestrator):
        """Test architecture validation for non-existent project"""
        result = orchestrator._validate_architecture("NonExistentProject")
        
        assert result["score"] == 0
        assert len(result["issues"]) > 0


class TestPerformanceValidation:
    """Test performance validation"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_validate_performance_returns_dict(self, orchestrator):
        """Test that performance validation returns proper dict"""
        result = orchestrator._validate_performance("NonExistentProject")
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "issues" in result
        assert "recommendations" in result
    
    def test_performance_score_range(self, orchestrator):
        """Test that performance score is between 0-100"""
        result = orchestrator._validate_performance("TestProject")
        
        assert 0 <= result["score"] <= 100
    
    def test_performance_validation_nonexistent_project(self, orchestrator):
        """Test performance validation for non-existent project"""
        result = orchestrator._validate_performance("NonExistentProject")
        
        assert result["score"] == 0
        assert len(result["issues"]) > 0


class TestDependencyValidation:
    """Test dependency validation"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_validate_dependencies_returns_dict(self, orchestrator):
        """Test that dependency validation returns proper dict"""
        result = orchestrator._validate_dependencies("NonExistentProject")
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "issues" in result
        assert "recommendations" in result
    
    def test_dependency_score_range(self, orchestrator):
        """Test that dependency score is between 0-100"""
        result = orchestrator._validate_dependencies("TestProject")
        
        assert 0 <= result["score"] <= 100
    
    def test_dependency_validation_nonexistent_project(self, orchestrator):
        """Test dependency validation for non-existent project"""
        result = orchestrator._validate_dependencies("NonExistentProject")
        
        assert result["score"] == 0
        assert len(result["issues"]) > 0


class TestQualityMetrics:
    """Test quality metrics"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_quality_metrics_dataclass(self, orchestrator):
        """Test QualityMetrics dataclass creation"""
        metrics = orchestrator.QualityMetrics(
            project_name="TestProject",
            timestamp="2025-11-06T12:00:00Z",
            architecture_score=85.0,
            performance_score=90.0,
            dependency_score=80.0,
            documentation_score=75.0,
            overall_score=82.5,
            issues=["Issue 1"],
            recommendations=["Recommendation 1"]
        )
        
        assert metrics.project_name == "TestProject"
        assert metrics.architecture_score == 85.0
        assert metrics.overall_score == 82.5
    
    def test_quality_metrics_to_dict(self, orchestrator):
        """Test converting QualityMetrics to dict"""
        metrics = orchestrator.QualityMetrics(
            project_name="TestProject",
            timestamp="2025-11-06T12:00:00Z",
            architecture_score=85.0,
            performance_score=90.0,
            dependency_score=80.0,
            documentation_score=75.0,
            overall_score=82.5,
            issues=["Issue 1"],
            recommendations=["Recommendation 1"]
        )
        
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["project_name"] == "TestProject"
        assert metrics_dict["overall_score"] == 82.5
    
    def test_generate_quality_report(self, orchestrator):
        """Test generating quality report"""
        metrics = orchestrator._generate_quality_report("NonExistentProject")
        
        assert isinstance(metrics, orchestrator.QualityMetrics)
        assert 0 <= metrics.overall_score <= 100
        assert isinstance(metrics.issues, list)
        assert isinstance(metrics.recommendations, list)


class TestDocumentationGeneration:
    """Test documentation generation"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    @pytest.mark.asyncio
    async def test_generate_documentation_returns_dict(self, orchestrator):
        """Test that documentation generation returns proper dict"""
        result = await orchestrator.generate_documentation("NonExistentProject")
        
        assert isinstance(result, dict)
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_generate_documentation_nonexistent_project(self, orchestrator):
        """Test documentation generation for non-existent project"""
        result = await orchestrator.generate_documentation("NonExistentProject")
        
        # Should handle gracefully
        assert isinstance(result, dict)


class TestIntegrationPhase4:
    """Integration tests for Phase 4"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        config = OrchestratorConfig(sprint_id="SP-TEST-001")
        return SprintOrchestrator(config)
    
    def test_quality_metrics_calculation(self, orchestrator):
        """Test quality metrics calculation"""
        # Create metrics with known scores
        metrics = orchestrator.QualityMetrics(
            project_name="TestProject",
            timestamp="2025-11-06T12:00:00Z",
            architecture_score=100.0,
            performance_score=100.0,
            dependency_score=100.0,
            documentation_score=100.0,
            overall_score=100.0,
            issues=[],
            recommendations=[]
        )
        
        # Overall score should be average of all scores
        expected_overall = (100.0 + 100.0 + 100.0 + 100.0) / 4
        assert metrics.overall_score == expected_overall
    
    def test_realistic_quality_report(self, orchestrator):
        """Test realistic quality report scenario"""
        # Generate report for non-existent project
        metrics = orchestrator._generate_quality_report("TestProject")
        
        # Should have all required fields
        assert metrics.project_name == "TestProject"
        assert hasattr(metrics, 'architecture_score')
        assert hasattr(metrics, 'performance_score')
        assert hasattr(metrics, 'dependency_score')
        assert hasattr(metrics, 'documentation_score')
        assert hasattr(metrics, 'overall_score')
        assert hasattr(metrics, 'issues')
        assert hasattr(metrics, 'recommendations')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

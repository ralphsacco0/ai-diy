"""
Test personas loader functionality with JSON-only path resolution.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch
import tempfile
import json
import sys

# Add the src directory to the path so we can import from services
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.ai_gateway import resolve_project_root, resolve_personas_path, load_personas


class TestPersonasPathResolution:
    """Test path resolution functionality for config_personas.json"""
    
    def test_resolve_project_root_with_git(self):
        """Test that resolve_project_root() finds the .git directory"""
        # This should find the actual repo root since we're in a git repo
        root = resolve_project_root()
        assert root.exists()
        # Should find one of our project indicators
        assert (root / ".git").exists() or (root / "README.md").exists() or (root / "architect").exists()
    
    def test_resolve_personas_path_default(self):
        """Test that resolve_personas_path() points to repo-root config_personas.json when PERSONAS_PATH is unset"""
        with patch.dict(os.environ, {}, clear=True):
            # Clear PERSONAS_PATH if it exists
            if 'PERSONAS_PATH' in os.environ:
                del os.environ['PERSONAS_PATH']
            
            personas_path = resolve_personas_path()
            root = resolve_project_root()
            expected_path = root / "config_personas.json"
            
            assert personas_path == expected_path
            assert personas_path.name == "config_personas.json"
    
    def test_personas_path_override_absolute(self):
        """Test that PERSONAS_PATH override works for absolute paths"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
            try:
                with patch.dict(os.environ, {'PERSONAS_PATH': str(tmp_path)}):
                    personas_path = resolve_personas_path()
                    assert personas_path == tmp_path
                    assert personas_path.is_absolute()
            finally:
                # Clean up
                if tmp_path.exists():
                    tmp_path.unlink()
    
    def test_personas_path_override_relative(self):
        """Test that PERSONAS_PATH override works for relative paths"""
        relative_path = "custom/personas.json"
        
        with patch.dict(os.environ, {'PERSONAS_PATH': relative_path}):
            personas_path = resolve_personas_path()
            root = resolve_project_root()
            expected_path = root / relative_path
            
            assert personas_path == expected_path
            assert personas_path.is_absolute()
    
    def test_load_personas_returns_non_empty_mapping(self):
        """Test that load_personas() returns a non-empty mapping (skip if config_personas.json not present)"""
        try:
            personas = load_personas()
            assert isinstance(personas, dict)
            assert len(personas) > 0
            
            # Check that each character has the expected structure
            for character_key, character_data in personas.items():
                assert isinstance(character_key, str)
                assert isinstance(character_data, dict)
                assert "name" in character_data
                assert "role" in character_data
                assert "system_prompt" in character_data
                assert isinstance(character_data["name"], str)
                assert isinstance(character_data["role"], str)
                assert isinstance(character_data["system_prompt"], str)
                
        except (FileNotFoundError, RuntimeError) as e:
            # Skip test if config_personas.json is not present (e.g., in CI)
            pytest.skip(f"Skipping test due to missing config_personas.json: {e}")
    
    def test_load_personas_uses_resolved_path(self):
        """Test that load_personas() uses the resolved path"""
        # Create a temporary personas file with minimal JSON content
        minimal_personas_content = {
            "metadata": {"version": "1.0"},
            "personas": {
                "TEST": {
                    "name": "TestUser",
                    "role": "Test Role (TEST)",
                    "system_prompt": "This is a test character for testing.",
                    "enabled": True
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp_file:
            json.dump(minimal_personas_content, tmp_file)
            tmp_path = Path(tmp_file.name)
        
        try:
            # Override PERSONAS_PATH to point to our test file
            with patch.dict(os.environ, {'PERSONAS_PATH': str(tmp_path)}):
                personas = load_personas()
                
                assert isinstance(personas, dict)
                assert len(personas) == 1
                assert "TEST" in personas
                assert personas["TEST"]["name"] == "TestUser"
                assert personas["TEST"]["role"] == "Test Role (TEST)"
                assert "test character" in personas["TEST"]["system_prompt"].lower()
                
        finally:
            # Clean up
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])

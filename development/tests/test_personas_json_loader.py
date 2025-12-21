"""
Test personas JSON loader functionality.
"""
import os
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import sys

# Add the src directory to the path so we can import from services
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.ai_gateway import resolve_personas_path, load_personas_json, load_personas


class TestPersonasJsonLoader:
    """Test JSON-only personas loader functionality"""
    
    def test_default_path_resolves_to_config_personas_json(self):
        """Test that default path resolves to config_personas.json"""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any PERSONAS_PATH if it exists
            if 'PERSONAS_PATH' in os.environ:
                del os.environ['PERSONAS_PATH']
            
            path = resolve_personas_path()
            assert str(path).endswith('config_personas.json')
            assert path.name == "config_personas.json"
    
    def test_personas_path_override_absolute(self):
        """Test PERSONAS_PATH override with absolute path"""
        custom_path = "/custom/path/my_personas.json"
        
        with patch.dict(os.environ, {'PERSONAS_PATH': custom_path}):
            path = resolve_personas_path()
            assert str(path) == custom_path
    
    def test_personas_path_override_relative(self):
        """Test PERSONAS_PATH override with relative path"""
        custom_path = "custom/my_personas.json"
        
        with patch.dict(os.environ, {'PERSONAS_PATH': custom_path}):
            path = resolve_personas_path()
            # Should be resolved relative to project root
            assert path.is_absolute()
            assert str(path).endswith(custom_path)
    
    def test_json_loader_validates_required_fields(self):
        """Test JSON loader validates required fields"""
        # Valid JSON
        valid_json = {
            "metadata": {"version": "1.0"},
            "personas": {
                "TEST1": {
                    "name": "TestUser1",
                    "role": "Test Role 1",
                    "system_prompt": "Test prompt 1",
                    "enabled": True
                },
                "TEST2": {
                    "name": "TestUser2", 
                    "role": "Test Role 2",
                    "system_prompt": "Test prompt 2"
                    # enabled defaults to True
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp_file:
            json.dump(valid_json, tmp_file)
            tmp_path = Path(tmp_file.name)
        
        try:
            with patch.dict(os.environ, {'PERSONAS_PATH': str(tmp_path)}):
                personas = load_personas_json()
                assert len(personas) == 2
                assert "TEST1" in personas
                assert "TEST2" in personas
                assert personas["TEST1"]["name"] == "TestUser1"
                assert personas["TEST2"]["name"] == "TestUser2"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    
    def test_json_loader_skips_disabled_personas(self):
        """Test JSON loader skips personas with enabled=false"""
        json_data = {
            "metadata": {"version": "1.0"},
            "personas": {
                "ENABLED": {
                    "name": "Enabled User",
                    "role": "Enabled Role",
                    "system_prompt": "Enabled prompt",
                    "enabled": True
                },
                "DISABLED": {
                    "name": "Disabled User",
                    "role": "Disabled Role", 
                    "system_prompt": "Disabled prompt",
                    "enabled": False
                },
                "DEFAULT_ENABLED": {
                    "name": "Default User",
                    "role": "Default Role",
                    "system_prompt": "Default prompt"
                    # enabled defaults to True
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp_file:
            json.dump(json_data, tmp_file)
            tmp_path = Path(tmp_file.name)
        
        try:
            with patch.dict(os.environ, {'PERSONAS_PATH': str(tmp_path)}):
                personas = load_personas_json()
                assert "ENABLED" in personas
                assert "DEFAULT_ENABLED" in personas
                assert "DISABLED" not in personas
                assert len(personas) == 2
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    
    def test_json_loader_fails_on_missing_file(self):
        """Test JSON loader fails fast on missing file"""
        nonexistent_path = "/nonexistent/path/personas.json"
        
        with patch.dict(os.environ, {'PERSONAS_PATH': nonexistent_path}):
            with pytest.raises(RuntimeError, match="not found"):
                load_personas_json()
    
    def test_json_loader_fails_on_invalid_json(self):
        """Test JSON loader fails fast on invalid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp_file:
            tmp_file.write("{ invalid json content")
            tmp_path = Path(tmp_file.name)
        
        try:
            with patch.dict(os.environ, {'PERSONAS_PATH': str(tmp_path)}):
                with pytest.raises(RuntimeError, match="Invalid JSON"):
                    load_personas_json()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    
    def test_json_loader_fails_on_missing_personas_key(self):
        """Test JSON loader fails on missing 'personas' key"""
        invalid_json = {
            "metadata": {"version": "1.0"}
            # Missing "personas" key
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp_file:
            json.dump(invalid_json, tmp_file)
            tmp_path = Path(tmp_file.name)
        
        try:
            with patch.dict(os.environ, {'PERSONAS_PATH': str(tmp_path)}):
                with pytest.raises(RuntimeError, match="missing 'personas' key"):
                    load_personas_json()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    
    def test_json_loader_fails_on_missing_required_fields(self):
        """Test JSON loader fails on missing required fields"""
        # Missing 'system_prompt' field
        invalid_json = {
            "metadata": {"version": "1.0"},
            "personas": {
                "INVALID": {
                    "name": "Test User",
                    "role": "Test Role"
                    # Missing "system_prompt"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp_file:
            json.dump(invalid_json, tmp_file)
            tmp_path = Path(tmp_file.name)
        
        try:
            with patch.dict(os.environ, {'PERSONAS_PATH': str(tmp_path)}):
                with pytest.raises(RuntimeError, match="Missing required field 'system_prompt'"):
                    load_personas_json()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    
    def test_json_loader_fails_on_no_enabled_personas(self):
        """Test JSON loader fails when no personas are enabled"""
        json_data = {
            "metadata": {"version": "1.0"},
            "personas": {
                "DISABLED1": {
                    "name": "Disabled User 1",
                    "role": "Disabled Role 1",
                    "system_prompt": "Disabled prompt 1",
                    "enabled": False
                },
                "DISABLED2": {
                    "name": "Disabled User 2",
                    "role": "Disabled Role 2", 
                    "system_prompt": "Disabled prompt 2",
                    "enabled": False
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp_file:
            json.dump(json_data, tmp_file)
            tmp_path = Path(tmp_file.name)
        
        try:
            with patch.dict(os.environ, {'PERSONAS_PATH': str(tmp_path)}):
                with pytest.raises(RuntimeError, match="No enabled personas"):
                    load_personas_json()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    
    def test_load_personas_calls_json_loader(self):
        """Test that load_personas() calls load_personas_json() only"""
        # Create valid JSON file
        valid_json = {
            "metadata": {"version": "1.0"},
            "personas": {
                "TEST": {
                    "name": "Test User",
                    "role": "Test Role",
                    "system_prompt": "Test prompt",
                    "enabled": True
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp_file:
            json.dump(valid_json, tmp_file)
            tmp_path = Path(tmp_file.name)
        
        try:
            with patch.dict(os.environ, {'PERSONAS_PATH': str(tmp_path)}):
                personas = load_personas()
                assert isinstance(personas, dict)
                assert len(personas) == 1
                assert "TEST" in personas
                assert personas["TEST"]["name"] == "Test User"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    
    def test_json_structure_validation(self):
        """Test JSON structure matches expected format"""
        # Test with actual config_personas.json structure
        try:
            personas = load_personas()
            
            # Should be a dictionary
            assert isinstance(personas, dict)
            assert len(personas) > 0
            
            # Each persona should have required fields
            for role_key, persona_data in personas.items():
                assert isinstance(role_key, str)
                assert isinstance(persona_data, dict)
                
                # Required fields
                assert "name" in persona_data
                assert "role" in persona_data  
                assert "system_prompt" in persona_data
                
                # Field types
                assert isinstance(persona_data["name"], str)
                assert isinstance(persona_data["role"], str)
                assert isinstance(persona_data["system_prompt"], str)
                
                # Non-empty values
                assert len(persona_data["name"]) > 0
                assert len(persona_data["role"]) > 0
                assert len(persona_data["system_prompt"]) > 0
                
        except (FileNotFoundError, RuntimeError) as e:
            # Skip test if config_personas.json is not present
            pytest.skip(f"Skipping validation test due to missing config_personas.json: {e}")


if __name__ == "__main__":
    pytest.main([__file__])

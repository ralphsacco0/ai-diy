"""
Simplified Builder Executor - Direct patch application to main directory
"""
import os
import subprocess
import tempfile
from pathlib import Path
import fnmatch
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class BuilderExecutor:
    def __init__(self):
        self.allowlist = os.getenv("ALLOWLIST", "*").split(",")
        self.max_patch_bytes = int(os.getenv("PATCH_MAX_BYTES", "131072"))  # 128KB
        self.dry_run = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")
        self.builder_enabled = os.getenv("BUILDER_ENABLED", "true").lower() in ("1", "true", "yes")
        self.run_unit_tests = os.getenv("RUN_UNIT_TESTS", "true").lower() in ("1", "true", "yes")
        self.project_root = Path(__file__).parent.parent.parent  # Go up to ai-diy root
        
    def execute(self, change_request: Dict) -> Dict:
        """
        Execute a change request directly in the main project directory.
        
        Args:
            change_request: Dict with keys: story_id, title, patch_unified, etc.
            
        Returns:
            Dict with status: "green"/"red", and details
        """
        try:
            # Kill switch check
            if not self.builder_enabled:
                return {
                    "status": "red",
                    "error": "builder_disabled", 
                    "reason": "BUILDER_ENABLED=false; no changes performed"
                }
            
            story_id = change_request.get("story_id", "unknown")
            patch_content = change_request.get("patch_unified", "")
            
            # Validate patch
            validation_result = self._validate_patch(patch_content)
            if not validation_result["valid"]:
                return {
                    "status": "red",
                    "error": "patch_validation_failed",
                    "reason": f"Patch validation failed: {validation_result['error']}",
                    "story_id": story_id
                }
            
            # Dry run mode - validate only
            if self.dry_run:
                dry_run_result = self._validate_patch_application(patch_content)
                if not dry_run_result["success"]:
                    return {
                        "status": "red",
                        "error": "dry_run_failed",
                        "reason": f"Dry run validation failed: {dry_run_result['error']}",
                        "story_id": story_id
                    }
                
                return {
                    "status": "green",
                    "dry_run": True,
                    "files_touched": dry_run_result["files_touched"],
                    "story_id": story_id
                }
            
            # Apply patch directly to main directory
            apply_result = self._apply_patch_directly(patch_content)
            if not apply_result["success"]:
                return {
                    "status": "red",
                    "error": "patch_application_failed", 
                    "reason": f"Patch application failed: {apply_result['error']}",
                    "story_id": story_id
                }
            
            # Run unit tests if enabled
            if self.run_unit_tests:
                test_result = self._run_unit_tests()
                if test_result["success"]:
                    return {
                        "status": "green",
                        "story_id": story_id,
                        "files_touched": apply_result["files_touched"],
                        "tests": [{"kind": "unit", "pass": True}]
                    }
                else:
                    return {
                        "status": "red",
                        "error": "unit_tests_failed",
                        "reason": f"Unit tests failed: {test_result['error']}",
                        "story_id": story_id,
                        "files_touched": apply_result["files_touched"],
                        "tests": [{"kind": "unit", "pass": False}]
                    }
            
            # No tests - return success
            return {
                "status": "green",
                "story_id": story_id,
                "files_touched": apply_result["files_touched"]
            }
            
        except Exception as e:
            logger.error(f"Builder execution failed: {e}")
            return {
                "status": "red",
                "error": "unexpected_error",
                "reason": f"Unexpected error: {str(e)}",
                "story_id": change_request.get("story_id", "unknown")
            }

    def _validate_patch(self, patch_content: str) -> Dict:
        """Validate patch format and size"""
        if not patch_content or not patch_content.strip():
            return {"valid": False, "error": "Empty patch content"}
        
        # Check size limit
        if len(patch_content.encode('utf-8')) > self.max_patch_bytes:
            return {"valid": False, "error": f"Patch exceeds {self.max_patch_bytes} bytes"}
        
        # Basic unified diff format check
        lines = patch_content.strip().split('\n')
        has_diff_header = any(line.startswith('---') or line.startswith('+++') for line in lines[:10])
        has_hunk_header = any(line.startswith('@@') for line in lines)
        
        if not (has_diff_header and has_hunk_header):
            return {"valid": False, "error": "Invalid unified diff format"}
        
        # Check allowlist compliance
        allowlist_result = self._check_allowlist_compliance(patch_content)
        if not allowlist_result["compliant"]:
            return {"valid": False, "error": allowlist_result["error"]}
        
        return {"valid": True}
    
    def _check_allowlist_compliance(self, patch_content: str) -> Dict:
        """Check if all file paths in patch comply with allowlist and strict path validation"""
        lines = patch_content.split('\n')
        file_paths = []
        
        for line in lines:
            if line.startswith('---') or line.startswith('+++'):
                # Extract file path from diff header
                parts = line.split('\t')[0].split(' ', 1)
                if len(parts) > 1:
                    path = parts[1].strip()
                    if path != '/dev/null' and not path.startswith('a/') and not path.startswith('b/'):
                        file_paths.append(path)
                    elif path.startswith('a/') or path.startswith('b/'):
                        file_paths.append(path[2:])  # Remove a/ or b/ prefix
        
        # Strict path validation
        project_real = os.path.realpath(self.project_root)
        violating_paths = []
        
        for file_path in file_paths:
            # Check for absolute paths
            if os.path.isabs(file_path):
                violating_paths.append(file_path)
                continue
                
            # Check for .. segments that could escape project
            if '..' in file_path.split(os.sep):
                violating_paths.append(file_path)
                continue
                
            # Check if resolved path escapes project directory
            try:
                full_path = os.path.join(project_real, file_path)
                resolved_path = os.path.realpath(full_path)
                if not resolved_path.startswith(project_real + os.sep) and resolved_path != project_real:
                    violating_paths.append(file_path)
                    continue
            except Exception:
                violating_paths.append(file_path)
                continue
            
            # Check allowlist compliance
            allowed = False
            for pattern in self.allowlist:
                if fnmatch.fnmatch(file_path, pattern.strip()):
                    allowed = True
                    break
            
            if not allowed:
                violating_paths.append(file_path)
        
        if violating_paths:
            return {
                "compliant": False,
                "error": "allowlist_violation",
                "reason": "path outside allowlist or project directory",
                "paths": violating_paths
            }
        
        return {"compliant": True, "files": file_paths}

    def _apply_patch_directly(self, patch_content: str) -> Dict:
        """Apply patch directly to execution sandbox directory"""
        original_cwd = os.getcwd()
        patch_file_path = None
        
        try:
            # Change to execution-sandbox/client-projects where the files are
            sandbox_dir = self.project_root / "execution-sandbox" / "client-projects"
            os.chdir(sandbox_dir)
            
            # Apply patch using patch command instead of git apply
            result = subprocess.run(
                ['patch', '-p0'],
                input=patch_content,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Extract files that were touched
                files_touched = self._extract_files_from_patch(patch_content)
                return {
                    "success": True,
                    "files_touched": files_touched
                }
            else:
                return {
                    "success": False,
                    "error": f"Patch application failed: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Patch application timed out"}
        except Exception as e:
            return {"success": False, "error": f"Patch application error: {str(e)}"}
        finally:
            os.chdir(original_cwd)

    def _validate_patch_application(self, patch_content: str) -> Dict:
        """Validate patch can be applied without errors (dry run)"""
        original_cwd = os.getcwd()
        patch_file_path = None
        
        try:
            # Change to execution-sandbox/client-projects where the files are
            sandbox_dir = self.project_root / "execution-sandbox" / "client-projects"
            os.chdir(sandbox_dir)
            
            # Create temporary patch file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
                f.write(patch_content)
                patch_file_path = f.name
            
            # Test patch application with --dry-run
            result = subprocess.run(
                ['git', 'apply', '--dry-run', '--verbose', patch_file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Extract files that would be touched
                files_touched = self._extract_files_from_patch(patch_content)
                return {
                    "success": True,
                    "files_touched": files_touched
                }
            else:
                return {
                    "success": False,
                    "error": f"Patch dry-run failed: {result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Patch validation timed out"}
        except Exception as e:
            return {"success": False, "error": f"Patch validation error: {str(e)}"}
        finally:
            if original_cwd:
                os.chdir(original_cwd)
            if patch_file_path and os.path.exists(patch_file_path):
                os.unlink(patch_file_path)

    def _run_unit_tests(self) -> Dict:
        """Run unit tests in execution sandbox directory"""
        original_cwd = os.getcwd()
        
        try:
            # Change to execution-sandbox/client-projects where the files are
            sandbox_dir = self.project_root / "execution-sandbox" / "client-projects"
            os.chdir(sandbox_dir)
            
            # Run pytest -q with virtual environment
            venv_python = self.project_root / ".venv" / "bin" / "python"
            if venv_python.exists():
                test_result = subprocess.run(
                    [str(venv_python), '-m', 'pytest', '-q'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            else:
                # Fallback to system python
                test_result = subprocess.run(
                    ['python', '-m', 'pytest', '-q'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            if test_result.returncode == 0:
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": f"pytest failed: {test_result.stdout}\n{test_result.stderr}"
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Unit tests timed out"}
        except Exception as e:
            return {"success": False, "error": f"Unit test execution error: {str(e)}"}
        finally:
            os.chdir(original_cwd)

    def _extract_files_from_patch(self, patch_content: str) -> list:
        """Extract list of files that would be modified by patch"""
        files = []
        lines = patch_content.split('\n')
        
        for line in lines:
            if line.startswith('---') or line.startswith('+++'):
                # Extract file path from diff header
                parts = line.split('\t')[0].split(' ', 1)
                if len(parts) > 1:
                    path = parts[1].strip()
                    if path != '/dev/null' and not path.startswith('a/') and not path.startswith('b/'):
                        if path not in files:
                            files.append(path)
                    elif path.startswith('a/') or path.startswith('b/'):
                        clean_path = path[2:]  # Remove a/ or b/ prefix
                        if clean_path not in files:
                            files.append(clean_path)
        
        return files


# Global instance
builder = BuilderExecutor()

# Convenience function for windsurf_integration
def execute(change_request: Dict) -> Dict:
    """Execute change request using global builder instance"""
    return builder.execute(change_request)

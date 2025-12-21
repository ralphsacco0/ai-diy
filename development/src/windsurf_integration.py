"""
Enhanced Windsurf/Cascade integration for reliable AI development.
Bridges the new FastAPI architecture with actual code execution via Cascade.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

# Import builder for dual-executor routing
try:
    from builder import builder
    BUILDER_AVAILABLE = True
except ImportError:
    BUILDER_AVAILABLE = False
    logging.warning("Builder module not available")

# Add parent directory to path to import original windsurf integration
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# This class is now self-contained and does not depend on an external integration.
WINDSURF_AVAILABLE = True
    
class ChangeStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

logger = logging.getLogger(__name__)

class EnhancedWindsurfIntegration:
    """Enhanced Windsurf integration that works with the new FastAPI architecture."""
    
    def __init__(self, project_root: str = None, target_workspace: str = None):
        """Initialize enhanced Windsurf integration.
        
        Args:
            project_root: Root directory for the Virtual Scrum
            target_workspace: The actual workspace where code changes should be applied
        """
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.target_workspace = Path(target_workspace) if target_workspace else self.project_root
        logger.info(f"Windsurf integration initialized for workspace: {self.target_workspace}")
        
        self.change_requests = {}  # Track change requests
        self.default_executor = os.getenv("EXECUTOR", "cascade")
        logger.info(f"Default executor set to: {self.default_executor} (from env EXECUTOR={os.getenv('EXECUTOR', 'NOT_SET')})")
    
    def create_change_request(self, 
                            description: str, 
                            target_files: List[str] = None,
                            context: str = "",
                            task_id: Optional[int] = None,
                            model: str = None) -> Optional[str]:
        """Create a change request to be executed by Windsurf/Cascade.
        
        Args:
            description: Description of the change to make
            target_files: List of files to target (optional)
            context: Additional context for the change
            task_id: Associated task ID from the database
            model: AI model to use for the change request
            
        Returns:
            Request ID if successful, None if failed
        """
        try:
            # Create a unique request ID
            request_id = f"req_{int(datetime.now().timestamp())}"
            normalized_description = self._normalize_task_description(description)
            
            # Store request metadata
            self.change_requests[request_id] = {
                "description": description,
                "normalized_description": normalized_description,
                "target_files": target_files,
                "context": context,
                "task_id": task_id,
                "created_at": datetime.now().isoformat(),
                "status": ChangeStatus.PENDING
            }
            
            logger.info(f"Created change request {request_id}: {normalized_description}")
            return request_id
                
        except Exception as e:
            logger.error(f"Error creating change request: {e}")
            return None
    
    def execute_change_request(self, request_id: str, executor_override: str = None) -> bool:
        """Execute a change request via selected executor (Cascade or Builder).
        
        Args:
            request_id: The change request ID to execute
            executor_override: Override the default executor for this request
            
        Returns:
            True if execution was successful, False otherwise
        """
        try:
            if request_id not in self.change_requests:
                logger.error(f"Change request {request_id} not found")
                return False
            
            request_info = self.change_requests[request_id]
            description = request_info["description"]
            
            # Determine which executor to use
            executor = executor_override or self.default_executor
            logger.info(f"Executing change request {request_id} via {executor}: {description}")
            
            self.change_requests[request_id]["status"] = ChangeStatus.IN_PROGRESS
            self.change_requests[request_id]["executor"] = executor
            
            success = False
            
            if executor == "builder" and BUILDER_AVAILABLE:
                # Route to Builder executor
                success = self._execute_via_builder(request_id, request_info)
            else:
                # Route to Cascade executor (default)
                success = self._execute_via_cascade(request_id, request_info)
            
            # Log the outcome to progress.log
            self._log_progress(request_id, executor, success)
            
            if success:
                logger.info(f"Change request {request_id} executed successfully via {executor}")
                self.change_requests[request_id]["status"] = ChangeStatus.COMPLETED
            else:
                logger.error(f"Change request {request_id} execution failed via {executor}")
                self.change_requests[request_id]["status"] = ChangeStatus.FAILED
            
            return success
            
        except Exception as e:
            logger.error(f"Error executing change request {request_id}: {e}")
            if request_id in self.change_requests:
                self.change_requests[request_id]["status"] = ChangeStatus.FAILED
            return False
    
    def _execute_via_builder(self, request_id: str, request_info: Dict) -> bool:
        """Execute change request via Builder executor."""
        try:
            # For greeting changes, generate a unified diff
            description = request_info["description"]
            patch_unified = request_info.get("patch_unified", "")
            
            # If no patch provided, generate one for greeting changes
            if not patch_unified and ("greeting" in description.lower() or "helloworld" in description.lower() or "change" in description.lower()):
                patch_unified = self._generate_greeting_patch(description)
            
            # Convert request to builder format
            builder_request = {
                "story_id": request_id,
                "title": description,
                "patch_unified": patch_unified,
                "target_files": request_info.get("target_files", [])
            }
            
            logger.info(f"Builder request: {builder_request}")
            
            # Execute via builder
            result = builder.execute(builder_request)
            
            logger.info(f"Builder result: {result}")
            
            # Store builder response
            self.change_requests[request_id]["builder_response"] = result
            
            return result.get("status") == "green"
            
        except Exception as e:
            logger.error(f"Builder execution failed: {e}")
            return False
    
    def _generate_greeting_patch(self, description: str) -> str:
        """Generate a unified diff patch for greeting changes."""
        try:
            # Extract the target greeting from description
            import re
            # Try quoted patterns first
            match = re.search(r"'([^']+)'", description)
            if not match:
                match = re.search(r'"([^"]+)"', description)
            
            # If no quotes, try patterns like "say X" or "to X"
            if not match:
                match = re.search(r"say\s+(.+)", description, re.IGNORECASE)
            if not match:
                match = re.search(r"to\s+(.+)", description, re.IGNORECASE)
            
            if not match:
                return ""
            
            target_greeting = match.group(1).strip()
            
            # Read current helloworld.py content from execution sandbox
            helloworld_path = Path(self.target_workspace) / "helloworld.py"
            if not helloworld_path.exists():
                # Create new file patch - use simple path for new files
                return f"""--- /dev/null
+++ helloworld.py
@@ -0,0 +1,4 @@
+def greeting():
+    return "{target_greeting}"
+
+if __name__ == "__main__":
+    print(greeting())
"""
            
            # Read current content
            with open(helloworld_path, 'r') as f:
                current_content = f.read()
            
            # Generate new content
            new_content = current_content
            if 'return "' in current_content:
                # Replace existing greeting
                new_content = re.sub(r'return "([^"]*)"', f'return "{target_greeting}"', current_content)
            elif "return '" in current_content:
                new_content = re.sub(r"return '([^']*)'", f'return "{target_greeting}"', current_content)
            
            # Generate unified diff with correct path for builder allowlist
            import difflib
            # Use just the filename since builder changes to the target directory
            file_path = "helloworld.py"
            diff = difflib.unified_diff(
                current_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=file_path,
                tofile=file_path,
                lineterm='\n'
            )
            
            # Join and ensure proper formatting with line breaks
            patch = ''.join(diff)
            if patch and not patch.endswith('\n'):
                patch += '\n'
            return patch
            
        except Exception as e:
            logger.error(f"Failed to generate greeting patch: {e}")
            return ""
    
    def _execute_via_cascade(self, request_id: str, request_info: Dict) -> bool:
        """Execute change request via Cascade executor (original logic)."""
        try:
            description = request_info["description"]
            success = False
            cascade_response = ""
            
            # Handle greeting changes for helloworld.py
            if "change greeting to" in description.lower():
                try:
                    # Extract the target greeting from the description
                    import re
                    match = re.search(r"change greeting to ['\"]([^'\"]+)['\"]", description, re.IGNORECASE)
                    if match:
                        target_greeting = match.group(1)
                    else:
                        # Fallback: try to extract from description without quotes
                        parts = description.lower().split("change greeting to ")
                        if len(parts) > 1:
                            target_greeting = parts[1].strip().strip("'\"")
                        else:
                            target_greeting = "Hello, World!"
                    
                    logger.info(f"Extracted target greeting: '{target_greeting}'")
                    
                    # Update helloworld.py
                    helloworld_path = self.target_workspace / "helloworld.py"
                    
                    # Create the file with the new greeting
                    new_content = f'''def greeting():
    return "{target_greeting}"

if __name__ == "__main__":
    print(greeting())
'''
                    
                    with open(helloworld_path, "w") as f:
                        f.write(new_content)
                    
                    logger.info(f"Updated {helloworld_path} with greeting: '{target_greeting}'")
                    
                    # Auto-commit the change (optional)
                    try:
                        subprocess.run(["git", "add", "helloworld.py"], cwd=str(self.target_workspace), check=True)
                        subprocess.run(["git", "commit", "-m", f"Auto-commit: Changed greeting to '{target_greeting}'"], cwd=str(self.target_workspace), check=True)
                        subprocess.run(["git", "push"], cwd=str(self.target_workspace), check=True)
                        logger.info(f"Auto-committed and pushed change: '{target_greeting}'")
                    except Exception as e:
                        logger.warning(f"Auto-commit failed: {e}")
                    
                    cascade_response = f"Successfully changed greeting to '{target_greeting}'"
                    logger.info(cascade_response)
                    success = True

                except Exception as e:
                    logger.error(f"Execution failed: {e}")
                    cascade_response = f"Change request execution failed: {e}"
                    success = False
                
                self.change_requests[request_id]["cascade_response"] = cascade_response
            else:
                logger.error(f"Unsupported change request: {description}")
                success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Cascade execution failed: {e}")
            return False
    
    def _log_progress(self, request_id: str, executor: str, success: bool):
        """Log change request outcome to progress.log."""
        try:
            request_info = self.change_requests.get(request_id, {})
            
            # Get result details for tests field
            tests = []
            if executor == "builder":
                builder_response = request_info.get("builder_response", {})
                tests = builder_response.get("tests", [])
            
            log_entry = {
                "ts": datetime.now().timestamp(),
                "story": request_id,
                "executor": executor,
                "status": "success" if success else "failure", 
                "files": request_info.get("target_files", []),
                "tests": tests
            }
            
            # Append to progress.log
            with open("progress.log", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.warning(f"Failed to log progress: {e}")
    
    def wait_for_completion(self, request_id: str, timeout: int = 30) -> bool:
        """Wait for change request completion acknowledgment.
        
        Args:
            request_id: The change request ID
            timeout: Timeout in seconds
            
        Returns:
            True if acknowledgment received, False otherwise
        """
        # This method is no longer needed as execution is synchronous.
        logger.info(f"Request {request_id} completion is synchronous.")
        return True
            

    
    def get_change_status(self, request_id: str) -> Dict[str, Any]:
        """Get the status of a change request.
        
        Args:
            request_id: The change request ID
            
        Returns:
            Dictionary with status information
        """
        if request_id not in self.change_requests:
            return {"error": "Request ID not found"}
        
        request_info = self.change_requests[request_id]
        
        return {
            "request_id": request_id,
            "status": request_info.get("status", ChangeStatus.PENDING),
            "description": request_info["description"],
            "created_at": request_info["created_at"],
            "target_files": request_info.get("target_files", []),
            "cascade_response": request_info.get("cascade_response", "")
        }
    
    def run_tests(self, test_path: str = None) -> Dict[str, Any]:
        """Run tests in the target workspace.
        
        Args:
            test_path: Optional specific test path to run
            
        Returns:
            Dictionary with test results
        """
        try:
            # Run pytest in the target workspace
            cmd = ["pytest", "-v", "--tb=short"]
            if test_path:
                cmd.append(test_path)
            
            result = subprocess.run(
                cmd,
                cwd=str(self.target_workspace),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "workspace": str(self.target_workspace)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timed out",
                "workspace": str(self.target_workspace)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "workspace": str(self.target_workspace)
            }
    
    def create_git_snapshot(self, message: str = None) -> Optional[str]:
        """Create a git snapshot of the current state.
        
        Args:
            message: Commit message
            
        Returns:
            Commit hash if successful, None if failed
        """
        try:
            if not message:
                message = f"Snapshot created by Virtual Scrum at {datetime.now().isoformat()}"
            
            # Add all changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self.target_workspace),
                check=True,
                capture_output=True
            )
            
            # Commit changes
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self.target_workspace),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(self.target_workspace),
                    capture_output=True,
                    text=True,
                    check=True
                )
                commit_hash = hash_result.stdout.strip()
                logger.info(f"Created git snapshot: {commit_hash}")
                return commit_hash
            else:
                logger.warning(f"No changes to commit: {result.stderr}")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating git snapshot: {e}")
            return None
    
    def rollback_to_snapshot(self, commit_hash: str) -> bool:
        """Rollback to a specific git snapshot.
        
        Args:
            commit_hash: The commit hash to rollback to
            
        Returns:
            True if successful, False if failed
        """
        try:
            subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                cwd=str(self.target_workspace),
                check=True,
                capture_output=True
            )
            logger.info(f"Rolled back to snapshot: {commit_hash}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Rollback failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False
    
    def _normalize_task_description(self, description: str) -> str:
        """Normalize task description for better Windsurf understanding."""
        desc = description.strip().lower()
        
        # Handle common greeting modifications
        if "remove" in desc and "exclamation" in desc:
            return "Change the greeting in helloworld.py to 'Hello world' (remove the exclamation mark)"
        elif "add" in desc and "exclamation" in desc:
            return "Change the greeting in helloworld.py to 'Hello world!' (add exclamation mark)"
        elif "hello world" in desc and "print" in desc:
            if "!" in description:
                return "Modify helloworld.py to print 'Hello world!'"
            else:
                return "Modify helloworld.py to print 'Hello world'"
        
        # Return original if no normalization needed
        return description
    

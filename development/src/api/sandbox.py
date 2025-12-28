"""
Sandbox API endpoints for safe command execution and file exploration.
Provides controlled access to the execution sandbox for Sprint Review debugging.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import subprocess
import os
import json
from pathlib import Path
import logging
import ast
import shutil

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

# Sandbox root directory - matches sprint_orchestrator.py pattern
# Use absolute path to avoid issues when API runs from different directories
# This file is at: development/src/api/sandbox.py
# SANDBOX_ROOT should be: development/src/static/appdocs/execution-sandbox/client-projects
SANDBOX_ROOT = Path(__file__).parent.parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"

# Security: Allowlist of commands that can be executed
ALLOWED_COMMANDS = [
    "python", "python3",
    "pytest", "py.test",
    "pip", "pip3",
    "npm", "node",
    "flask", "uvicorn",
    "ls", "cat", "head", "tail",
    "grep", "find",
    "git"
]

# Security: Restricted paths that cannot be accessed
RESTRICTED_PATHS = [
    "/",
    "/Users",
    "/System",
    "/Library",
    "/bin",
    "/sbin",
    "/usr",
    "/etc",
    "/var",
    "/tmp"
]


class ListDirectoryRequest(BaseModel):
    """Request to list directory contents"""
    path: str = Field(..., description="Path to list (relative to sandbox root or absolute within sandbox)")
    recursive: bool = Field(False, description="List recursively")
    max_depth: int = Field(3, description="Maximum depth for recursive listing")
    exclude_patterns: List[str] = Field(
        default_factory=lambda: ["node_modules", ".git", ".snapshots", "__pycache__", ".venv", "*.pyc", ".pytest_cache", "dist", "build", ".DS_Store"],
        description="Patterns to exclude (glob format)"
    )


class DirectoryEntry(BaseModel):
    """Directory entry information"""
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    modified: Optional[str] = None


class ListDirectoryResponse(BaseModel):
    """Response with directory contents"""
    success: bool
    path: str
    entries: List[DirectoryEntry]
    message: Optional[str] = None


class ExecuteCommandRequest(BaseModel):
    """Request to execute a command in the sandbox"""
    project_name: str = Field(default="yourapp", description="Project folder (defaults to 'yourapp')")
    command: str = Field(..., description="Command to execute (must be in allowlist)")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    working_dir: Optional[str] = Field(None, description="Working directory (relative to project root)")
    timeout: int = Field(30, description="Timeout in seconds")


class ExecuteCommandResponse(BaseModel):
    """Response from command execution"""
    success: bool
    command: str
    stdout: str
    stderr: str
    exit_code: int
    message: Optional[str] = None


def validate_path(path: str, base_path: Path) -> Path:
    """
    Validate and resolve a path to ensure it's within the sandbox.
    
    Args:
        path: Path to validate (can be relative or absolute)
        base_path: Base path to resolve against
        
    Returns:
        Resolved absolute path
        
    Raises:
        HTTPException: If path is invalid or outside sandbox
    """
    # Resolve sandbox root to absolute path
    sandbox_root_resolved = SANDBOX_ROOT.resolve()
    
    # Convert to Path object
    if os.path.isabs(path):
        resolved = Path(path).resolve()
    else:
        resolved = (base_path / path).resolve()
    
    # Check if path is within sandbox - this is the primary security check
    try:
        resolved.relative_to(sandbox_root_resolved)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: Path outside sandbox: {path}"
        )
    
    # If path is within sandbox, it's allowed
    # No need to check restricted paths since sandbox is our safe zone
    return resolved


def validate_command(command: str) -> str:
    """
    Validate that a command is in the allowlist.
    
    Args:
        command: Command to validate
        
    Returns:
        Validated command
        
    Raises:
        HTTPException: If command is not allowed
    """
    if command not in ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=403,
            detail=f"Command not allowed: {command}. Allowed commands: {', '.join(ALLOWED_COMMANDS)}"
        )
    return command


@router.post("/list-directory", response_model=ListDirectoryResponse)
async def list_directory(request: ListDirectoryRequest):
    """
    List contents of a directory in the sandbox.
    
    Security:
    - Path must be within sandbox root
    - Cannot access restricted system paths
    """
    try:
        # Resolve sandbox root to absolute path for comparisons
        sandbox_root_resolved = SANDBOX_ROOT.resolve()
        
        # Validate and resolve path
        target_path = validate_path(request.path, SANDBOX_ROOT)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")
        
        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.path}")
        
        # List directory contents
        entries = []
        
        if request.recursive:
            # Recursive listing with depth limit and exclusions
            for item in target_path.rglob("*"):
                # Check if item or any parent matches exclusion patterns
                skip = False
                for pattern in request.exclude_patterns:
                    # Check if item itself matches
                    if item.match(pattern):
                        skip = True
                        break
                    # Check if any parent directory matches (e.g., skip everything under node_modules)
                    for parent in item.parents:
                        if parent.match(pattern) or parent.name == pattern:
                            skip = True
                            break
                    if skip:
                        break
                
                if skip:
                    continue
                
                # Check depth
                try:
                    rel_path = item.relative_to(target_path)
                    depth = len(rel_path.parts)
                    if depth > request.max_depth:
                        continue
                except ValueError:
                    continue
                
                entry = DirectoryEntry(
                    name=item.name,
                    path=str(item.relative_to(sandbox_root_resolved)),
                    type="directory" if item.is_dir() else "file",
                    size=item.stat().st_size if item.is_file() else None,
                    modified=str(item.stat().st_mtime) if item.exists() else None
                )
                entries.append(entry)
        else:
            # Non-recursive listing with exclusions
            for item in target_path.iterdir():
                # Check if item matches exclusion patterns
                skip = False
                for pattern in request.exclude_patterns:
                    if item.match(pattern) or item.name == pattern:
                        skip = True
                        break
                
                if skip:
                    continue
                
                entry = DirectoryEntry(
                    name=item.name,
                    path=str(item.relative_to(sandbox_root_resolved)),
                    type="directory" if item.is_dir() else "file",
                    size=item.stat().st_size if item.is_file() else None,
                    modified=str(item.stat().st_mtime) if item.exists() else None
                )
                entries.append(entry)
        
        # Sort entries: directories first, then files, alphabetically
        entries.sort(key=lambda e: (e.type != "directory", e.name.lower()))
        
        logger.info(f"Listed directory: {target_path} ({len(entries)} entries)")
        
        return ListDirectoryResponse(
            success=True,
            path=str(target_path.relative_to(sandbox_root_resolved)),
            entries=entries,
            message=f"Found {len(entries)} entries"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing directory: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing directory: {str(e)}")


@router.post("/execute", response_model=ExecuteCommandResponse)
async def execute_command(request: ExecuteCommandRequest):
    """
    Execute a command in the sandbox.
    
    Security:
    - Command must be in allowlist
    - Execution is within project directory only
    - Timeout enforced
    - Cannot access restricted paths
    """
    try:
        # Validate command
        command = validate_command(request.command)
        
        # Validate project path
        project_path = SANDBOX_ROOT / request.project_name
        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project not found: {request.project_name}")
        
        # Determine working directory
        if request.working_dir:
            working_dir = validate_path(request.working_dir, project_path)
        else:
            working_dir = project_path
        
        # Build full command
        full_command = [command] + request.args
        
        logger.info(f"Executing command in sandbox: {' '.join(full_command)} (cwd: {working_dir})")
        
        # Execute command with timeout
        # FUDGE TEST: Force PORT=3000 for generated apps so they don't conflict with AI-DIY on 8000
        cmd_env = {**os.environ, "PYTHONUNBUFFERED": "1", "PORT": "3000"}
        result = subprocess.run(
            full_command,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            timeout=request.timeout,
            env=cmd_env
        )
        
        logger.info(f"Command completed with exit code: {result.returncode}")
        
        return ExecuteCommandResponse(
            success=result.returncode == 0,
            command=' '.join(full_command),
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            message="Command executed successfully" if result.returncode == 0 else f"Command failed with exit code {result.returncode}"
        )
        
    except subprocess.TimeoutExpired:
        logger.error(f"Command timeout: {request.command}")
        raise HTTPException(status_code=408, detail=f"Command timeout after {request.timeout} seconds")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise HTTPException(status_code=500, detail=f"Error executing command: {str(e)}")


class ReadFileRequest(BaseModel):
    """Request to read a file from the sandbox"""
    project_name: str = Field(default="yourapp", description="Project folder (defaults to 'yourapp')")
    file_path: str = Field(..., description="File path relative to project root")


class ReadFileResponse(BaseModel):
    """Response with file contents"""
    success: bool
    project_name: str
    file_path: str
    content: str
    message: Optional[str] = None


class WriteFileRequest(BaseModel):
    """Request to write a file to the sandbox"""
    project_name: str = Field(default="yourapp", description="Project folder (defaults to 'yourapp')")
    file_path: str = Field(..., description="File path relative to project root")
    content: str = Field(..., description="File content to write")
    force_replace: bool = Field(default=False, description="If True, skip merge and replace file entirely (used by Sprint Review)")


class WriteFileResponse(BaseModel):
    """Response from file write operation"""
    success: bool
    project_name: str
    file_path: str
    message: Optional[str] = None


@router.post("/read-file", response_model=ReadFileResponse)
async def read_file(request: ReadFileRequest):
    """
    Read a file from the sandbox.
    
    Security:
    - File must be within project directory
    - Cannot access restricted paths
    """
    try:
        # Validate project path
        project_path = SANDBOX_ROOT / request.project_name
        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project not found: {request.project_name}")
        
        # Validate and resolve file path
        file_path = validate_path(request.file_path, project_path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {request.file_path}")
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"Read file: {file_path} ({len(content)} bytes)")
        
        return ReadFileResponse(
            success=True,
            project_name=request.project_name,
            file_path=request.file_path,
            content=content,
            message=f"File read successfully ({len(content)} bytes)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


def merge_code(existing: str, new: str, filepath: str) -> str:
    """Smart merge of existing and new code. Returns merged content."""
    
    # JavaScript/TypeScript: Replace (match orchestrator behavior)
    # Alex should generate complete files for these
    if filepath.endswith(('.js', '.jsx', '.ts', '.tsx')):
        logger.info(f"JavaScript file {filepath}: Using new content (complete file expected)")
        return new
    
    # Python: AST-based merge
    if filepath.endswith('.py'):
        try:
            # Parse both files
            existing_tree = ast.parse(existing)
            new_tree = ast.parse(new)
            
            # Extract elements from existing
            existing_funcs = {node.name for node in ast.walk(existing_tree) 
                            if isinstance(node, ast.FunctionDef)}
            existing_classes = {node.name for node in ast.walk(existing_tree) 
                              if isinstance(node, ast.ClassDef)}
            
            # Find new functions and classes to add
            merged_lines = existing.rstrip().split('\n')
            
            for node in ast.walk(new_tree):
                if isinstance(node, ast.FunctionDef) and node.name not in existing_funcs:
                    # Add new function
                    func_code = ast.unparse(node)
                    merged_lines.append("")
                    merged_lines.append("")
                    merged_lines.append(func_code)
                    existing_funcs.add(node.name)
                
                elif isinstance(node, ast.ClassDef) and node.name not in existing_classes:
                    # Add new class
                    class_code = ast.unparse(node)
                    merged_lines.append("")
                    merged_lines.append("")
                    merged_lines.append(class_code)
                    existing_classes.add(node.name)
            
            return '\n'.join(merged_lines)
            
        except Exception as e:
            logger.warning(f"Could not merge Python {filepath}: {e}. Appending instead.")
            separator = "\n\n# === Added by Sprint Execution ===\n"
            return f"{existing}{separator}{new}"
    
    # Other files (CSS, HTML, JSON, etc.): Replace if looks complete, else append
    # Check if new content looks like a complete file
    if len(new.strip()) > 100 or any(marker in new for marker in ['<!DOCTYPE', '<html', '{', 'import ', 'export ']):
        logger.info(f"Non-code file {filepath}: Using new content (looks complete)")
        return new
    else:
        # Partial content, append with proper comment syntax
        separator = "\n\n// === Added by Sprint Execution ===\n"  # Use // not #
        return f"{existing}{separator}{new}"


@router.post("/write-file", response_model=WriteFileResponse)
async def write_file(request: WriteFileRequest):
    """
    Write a file to the sandbox.
    
    Security:
    - File must be within project directory
    - Cannot access restricted paths
    - Creates parent directories if needed
    """
    try:
        # Validate project path
        project_path = SANDBOX_ROOT / request.project_name
        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project not found: {request.project_name}")
        
        # Validate and resolve file path
        file_path = validate_path(request.file_path, project_path)
        
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists and merge if needed (unless force_replace is True)
        content_to_write = request.content
        if file_path.exists() and not request.force_replace:
            logger.info(f"File exists, merging: {file_path}")
            # Create backup before modifying
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            
            # Read existing content and merge
            existing = file_path.read_text(encoding='utf-8')
            content_to_write = merge_code(existing, request.content, request.file_path)
            logger.info(f"Merged {len(existing)} bytes existing + {len(request.content)} bytes new = {len(content_to_write)} bytes total")
        elif file_path.exists() and request.force_replace:
            logger.info(f"File exists, force replacing: {file_path}")
            # Create backup before replacing
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
        
        # Write file content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content_to_write)
        
        logger.info(f"Wrote file: {file_path} ({len(content_to_write)} bytes)")
        
        return WriteFileResponse(
            success=True,
            project_name=request.project_name,
            file_path=request.file_path,
            message=f"File written successfully ({len(content_to_write)} bytes)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error writing file: {e}")
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")


@router.get("/status")
async def get_sandbox_status():
    """Get sandbox status and configuration"""
    return {
        "success": True,
        "sandbox_root": str(SANDBOX_ROOT),
        "sandbox_exists": SANDBOX_ROOT.exists(),
        "allowed_commands": ALLOWED_COMMANDS,
        "restricted_paths": RESTRICTED_PATHS,
        "projects": [p.name for p in SANDBOX_ROOT.iterdir() if p.is_dir()] if SANDBOX_ROOT.exists() else []
    }

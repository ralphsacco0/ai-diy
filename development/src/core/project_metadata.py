"""
Unified project metadata resolution - single source of truth.

All components use this module to get the current approved project name.
Priority:
1. Read project_metadata.json (created when vision is approved)
2. Fall back to latest approved vision title
3. Fall back to "Unknown"
"""
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def get_project_name(appdocs_base_path: Path = None) -> str:
    """
    Get project name from single source of truth.
    
    Priority:
    1. Read project_metadata.json (created when vision is approved)
    2. Fall back to latest approved vision title
    3. Fall back to "Unknown"
    
    Args:
        appdocs_base_path: Base path to appdocs directory. If None, uses relative path.
    
    Returns:
        Project name string
    """
    try:
        if appdocs_base_path is None:
            # Assume we're being called from src/ or a subdirectory
            appdocs_base_path = Path(__file__).parent.parent / "static" / "appdocs"
        
        metadata_file = appdocs_base_path / "project_metadata.json"
        
        # Try to read project metadata (single source of truth)
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    project_name = metadata.get("project_name")
                    if project_name:
                        logger.debug(f"Project name from metadata: {project_name}")
                        return project_name
            except Exception as e:
                logger.warning(f"Could not read project metadata: {e}")
        
        # Fall back to latest approved vision
        visions_dir = appdocs_base_path / "visions"
        if visions_dir.exists():
            vision_files = sorted(visions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            for vf in vision_files:
                try:
                    with open(vf, 'r') as f:
                        vision_doc = json.load(f)
                        if vision_doc.get("client_approval"):
                            project_name = vision_doc.get("title", "Unknown")
                            logger.debug(f"Project name from approved vision: {project_name}")
                            return project_name
                except Exception:
                    continue
        
        logger.debug("No approved vision found, using default project name")
        return "Unknown"
    
    except Exception as e:
        logger.warning(f"Error getting project name: {e}")
        return "Unknown"


def get_project_name_safe(appdocs_base_path: Path = None) -> str:
    """
    Get project name and convert to safe format for file paths.
    
    Converts spaces to underscores and removes special characters.
    Used for creating project directories and file paths.
    
    Args:
        appdocs_base_path: Base path to appdocs directory. If None, uses relative path.
    
    Returns:
        Safe project name string (alphanumeric, underscores, hyphens only)
    """
    project_name = get_project_name(appdocs_base_path)
    raw = str(project_name).strip().replace(" ", "_")
    safe = re.sub(r"[^A-Za-z0-9_-]", "", raw)
    return safe[:50] or "default_project"

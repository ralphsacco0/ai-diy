"""
Snapshot Manager for Sprint Review Alex
Creates and restores project snapshots before code changes
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Directories/files to exclude from snapshots
EXCLUDE_PATTERNS = [
    'node_modules',
    '.git',
    '.snapshots',
    '*.log',
    '.DS_Store',
    '__pycache__',
    '*.pyc',
    '.env.local',
    'npm-debug.log*',
    'yarn-debug.log*',
    'yarn-error.log*'
]

MAX_SNAPSHOTS = 5  # Keep last 5 snapshots per project


def create_snapshot(
    project_path: Path,
    metadata: Dict
) -> Optional[str]:
    """
    Create a snapshot of the project before changes.
    
    Args:
        project_path: Path to the project directory
        metadata: Dict with snapshot metadata (timestamp, changes, etc.)
    
    Returns:
        Snapshot timestamp string, or None if failed
    """
    try:
        if not project_path.exists():
            logger.error(f"Project path does not exist: {project_path}")
            return None
        
        # Create .snapshots directory inside project
        snapshots_dir = project_path / ".snapshots"
        snapshots_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for snapshot folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_dir = snapshots_dir / timestamp
        
        logger.info(f"Creating snapshot: {snapshot_dir}")
        
        # Copy project files to snapshot (excluding patterns)
        _copy_project(project_path, snapshot_dir)
        
        # Save metadata
        meta_file = snapshot_dir / ".snapshot_meta.json"
        with open(meta_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Snapshot created: {timestamp}")
        
        # Cleanup old snapshots
        _cleanup_old_snapshots(snapshots_dir)
        
        return timestamp
        
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}", exc_info=True)
        return None


def list_snapshots(project_path: Path) -> List[Dict]:
    """
    List all available snapshots for a project.
    
    Args:
        project_path: Path to the project directory
    
    Returns:
        List of snapshot metadata dicts, sorted by timestamp (newest first)
    """
    try:
        snapshots_dir = project_path / ".snapshots"
        if not snapshots_dir.exists():
            return []
        
        snapshots = []
        for snapshot_dir in snapshots_dir.iterdir():
            if not snapshot_dir.is_dir():
                continue
            
            meta_file = snapshot_dir / ".snapshot_meta.json"
            if meta_file.exists():
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                    metadata['snapshot_id'] = snapshot_dir.name
                    snapshots.append(metadata)
        
        # Sort by timestamp (newest first)
        snapshots.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return snapshots
        
    except Exception as e:
        logger.error(f"Failed to list snapshots: {e}", exc_info=True)
        return []


def restore_snapshot(
    project_path: Path,
    snapshot_id: str,
    reason: str = ""
) -> bool:
    """
    Restore project from a snapshot.
    
    Args:
        project_path: Path to the project directory
        snapshot_id: Snapshot timestamp/ID to restore
        reason: Reason for restoration (for logging)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        snapshots_dir = project_path / ".snapshots"
        snapshot_dir = snapshots_dir / snapshot_id
        
        if not snapshot_dir.exists():
            logger.error(f"Snapshot not found: {snapshot_id}")
            return False
        
        logger.info(f"Restoring snapshot: {snapshot_id}")
        if reason:
            logger.info(f"Reason: {reason}")
        
        # Get list of files/dirs to restore (exclude .snapshots itself)
        items_to_restore = [
            item for item in snapshot_dir.iterdir()
            if item.name != ".snapshot_meta.json"
        ]
        
        # Remove current project files (except .snapshots)
        for item in project_path.iterdir():
            if item.name == ".snapshots":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        
        # Copy snapshot files back to project
        for item in items_to_restore:
            dest = project_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        logger.info(f"✅ Snapshot restored: {snapshot_id}")

        # Reinstall dependencies (node_modules excluded from snapshot)
        package_json = project_path / "package.json"
        if package_json.exists():
            logger.info("🔄 Reinstalling dependencies after snapshot restore...")
            import subprocess
            try:
                result = subprocess.run(
                    ["npm", "ci", "--prefer-offline"],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes
                )

                if result.returncode != 0:
                    # Fallback to npm install if ci fails
                    logger.info("npm ci failed, trying npm install...")
                    result = subprocess.run(
                        ["npm", "install", "--prefer-offline"],
                        cwd=str(project_path),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                if result.returncode == 0:
                    logger.info("✅ Dependencies reinstalled successfully")
                else:
                    logger.warning(f"⚠️ npm install failed: {result.stderr}")
                    logger.warning("Snapshot restored but dependencies missing - manually run 'npm install'")

            except subprocess.TimeoutExpired:
                logger.error("❌ npm install timed out during snapshot restore")
            except FileNotFoundError:
                logger.error("❌ npm not found - cannot reinstall dependencies")
            except Exception as e:
                logger.error(f"Failed to reinstall dependencies: {e}")

        return True
        
    except Exception as e:
        logger.error(f"Failed to restore snapshot: {e}", exc_info=True)
        return False


def _copy_project(src: Path, dest: Path):
    """
    Copy project files, excluding patterns.
    """
    dest.mkdir(parents=True, exist_ok=True)
    
    for item in src.iterdir():
        # Skip excluded patterns
        if _should_exclude(item.name):
            continue
        
        dest_item = dest / item.name
        
        if item.is_dir():
            shutil.copytree(item, dest_item, ignore=_ignore_patterns)
        else:
            shutil.copy2(item, dest_item)


def _should_exclude(name: str) -> bool:
    """
    Check if file/dir should be excluded from snapshot.
    """
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith('*'):
            # Wildcard pattern
            if name.endswith(pattern[1:]):
                return True
        else:
            # Exact match
            if name == pattern:
                return True
    return False


def _ignore_patterns(dir, files):
    """
    Ignore function for shutil.copytree.
    """
    return [f for f in files if _should_exclude(f)]


def _cleanup_old_snapshots(snapshots_dir: Path):
    """
    Keep only the last MAX_SNAPSHOTS snapshots, delete older ones.
    """
    try:
        snapshots = sorted(
            [d for d in snapshots_dir.iterdir() if d.is_dir()],
            key=lambda x: x.name,
            reverse=True
        )
        
        if len(snapshots) > MAX_SNAPSHOTS:
            for old_snapshot in snapshots[MAX_SNAPSHOTS:]:
                logger.info(f"Removing old snapshot: {old_snapshot.name}")
                shutil.rmtree(old_snapshot)
                
    except Exception as e:
        logger.warning(f"Failed to cleanup old snapshots: {e}")

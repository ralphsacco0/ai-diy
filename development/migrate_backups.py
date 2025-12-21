#!/usr/bin/env python3
"""
Migrate existing backup directories to new format with metadata.
Populates the 'backups' array in sprint plan files.
"""
import json
from pathlib import Path
from datetime import datetime

SPRINT_DIR = Path("src/static/appdocs/sprints")
BACKUP_BASE_DIR = SPRINT_DIR / "backups"

def migrate_backups():
    """Scan backup directories and update sprint plans."""
    if not BACKUP_BASE_DIR.exists():
        print("No backups directory found")
        return
    
    for sprint_dir in BACKUP_BASE_DIR.iterdir():
        if not sprint_dir.is_dir() or not sprint_dir.name.startswith("SP-"):
            continue
        
        sprint_id = sprint_dir.name
        plan_path = SPRINT_DIR / f"{sprint_id}.json"
        
        if not plan_path.exists():
            print(f"⚠️  Plan not found for {sprint_id}, skipping")
            continue
        
        # Load plan
        with open(plan_path, 'r') as f:
            plan = json.load(f)
        
        # Scan backup directories
        backups = []
        for backup_dir in sorted(sprint_dir.iterdir()):
            if not backup_dir.is_dir():
                continue
            
            backup_id = backup_dir.name
            metadata_path = backup_dir / "metadata.json"
            
            # Check if metadata exists
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    backups.append({
                        "backup_id": metadata.get("backup_id", backup_id),
                        "created_at": metadata.get("created_at", ""),
                        "project_name": metadata.get("project_name", plan.get("project_name", ""))
                    })
            else:
                # Old backup without metadata - create minimal entry
                # Try to parse timestamp from backup_id (format: YYYYMMDDTHHMMSSffffff)
                try:
                    dt = datetime.strptime(backup_id[:15], "%Y%m%dT%H%M%S")
                    created_at = dt.isoformat()
                except:
                    created_at = ""
                
                backups.append({
                    "backup_id": backup_id,
                    "created_at": created_at,
                    "project_name": plan.get("project_name", "")
                })
                
                # Create metadata.json for old backup
                metadata = {
                    "backup_id": backup_id,
                    "created_at": created_at,
                    "sprint_id": sprint_id,
                    "project_name": plan.get("project_name", ""),
                    "plan_status": plan.get("status", ""),
                    "stories": plan.get("stories", []),
                    "items": ["project", "wireframes"]  # What we know exists
                }
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                print(f"  ✅ Created metadata for {sprint_id}/{backup_id}")
        
        # Update plan with backups array
        plan["backups"] = backups
        with open(plan_path, 'w') as f:
            json.dump(plan, f, indent=2)
        
        print(f"✅ Updated {sprint_id} with {len(backups)} backups")

if __name__ == "__main__":
    print("🔄 Migrating backup metadata...")
    migrate_backups()
    print("✅ Migration complete!")

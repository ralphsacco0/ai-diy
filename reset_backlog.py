#!/usr/bin/env python3
"""
Reset Backlog Script
Resets all story statuses to "Backlog" and clears execution-related fields.
"""

import csv
from pathlib import Path

# Path to the live backlog file
BACKLOG_PATH = Path("development/src/static/appdocs/backlog/Backlog.csv")

def reset_backlog():
    """Reset all stories to Backlog status and clear execution fields."""
    
    if not BACKLOG_PATH.exists():
        print(f"Error: Backlog file not found at {BACKLOG_PATH}")
        return
    
    # Read the backlog
    rows = []
    with open(BACKLOG_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        
        # Find column indices
        status_idx = header.index('Status')
        sprint_id_idx = header.index('Sprint_ID')
        exec_status_idx = header.index('Execution_Status')
        exec_started_idx = header.index('Execution_Started_At')
        exec_completed_idx = header.index('Execution_Completed_At')
        last_event_idx = header.index('Last_Event')
        last_updated_idx = header.index('Last_Updated')
        
        # Process each row
        for row in reader:
            if len(row) > status_idx:
                # Reset ALL stories to Backlog
                row[status_idx] = 'Backlog'
                
                # Clear execution fields for all stories
                if len(row) > sprint_id_idx:
                    row[sprint_id_idx] = ''
                if len(row) > exec_status_idx:
                    row[exec_status_idx] = ''
                if len(row) > exec_started_idx:
                    row[exec_started_idx] = ''
                if len(row) > exec_completed_idx:
                    row[exec_completed_idx] = ''
                if len(row) > last_event_idx:
                    row[last_event_idx] = ''
                if len(row) > last_updated_idx:
                    row[last_updated_idx] = ''
            
            rows.append(row)
    
    # Write back to file
    with open(BACKLOG_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"✅ Backlog reset complete!")
    print(f"   - ALL stories set to 'Backlog'")
    print(f"   - All execution fields cleared")
    print(f"   - File: {BACKLOG_PATH}")

if __name__ == "__main__":
    reset_backlog()

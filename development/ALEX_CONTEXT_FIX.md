# Alex Context Fix - Full File Loading for MODIFY Operations

## Problem Identified

**Date:** 2025-11-25  
**Sprint:** Sprint 1 (Re-run), Story US-009  
**Error:** `SyntaxError: Identifier 'fileURLToPath' has already been declared`

### Root Cause

Alex was **coding partially blind** when modifying existing files:

1. **File Truncation:** The orchestrator only showed Alex the **first 80 lines** of most files (150 for controllers/routes)
2. **Everything after was cut off** with `// ... (truncated)`
3. **When modifying files**, Alex couldn't see:
   - Existing imports (might be beyond line 80)
   - Existing exports
   - What's already declared in the file

### Example Scenario

**File:** `src/server.js` (120 lines long)

```
Line 1-80:  ✅ Alex can see this
Line 81-120: ❌ TRUNCATED - Alex can't see this
```

If line 85 already has `import { fileURLToPath } from 'url';`, Alex doesn't see it and adds it again at line 5, causing a duplicate declaration error.

---

## Solution Implemented

**Option 3: On MODIFY tasks, load FULL file content (no truncation)**

### Changes Made to `sprint_orchestrator.py`:

#### 1. Updated `_get_file_summaries()` signature (line 312)
```python
def _get_file_summaries(
    self, 
    project_name: str, 
    related_paths: List[str], 
    files_needing_full_content: List[str] = None  # ← NEW parameter
) -> str:
```

#### 2. Added smart truncation logic (lines 367-382)
```python
# CRITICAL: For MODIFY operations, show FULL content (no truncation)
# This prevents duplicate imports and ensures Alex sees the complete file
if rel_path_str in files_needing_full_content:
    # NO truncation - Alex needs to see the entire file to modify it correctly
    logger.info(f"Loading FULL content for {rel_path_str} (MODIFY operation)")
else:
    # Limit content to prevent token explosion for files Alex is just referencing
    max_lines = 150 if ('controllers' in rel_path_str or 'routes' in rel_path_str) else 80
    
    lines = content.split('\n')
    if len(lines) > max_lines:
        content = '\n'.join(lines[:max_lines]) + '\n// ... (truncated)'
```

#### 3. Added MODIFY detection in `_call_alex()` (lines 2445-2454)
```python
# CRITICAL: Detect MODIFY operations and load FULL file content
# This prevents duplicate imports and ensures Alex can see existing code
task_description = task.get('description', '').upper()
files_to_create = task.get('files_to_create', [])
files_needing_full_content = []

if 'MODIFY' in task_description or 'UPDATE' in task_description or 'EDIT' in task_description:
    # This is a MODIFY task - load full content for files being modified
    files_needing_full_content = files_to_create.copy()
    logger.info(f"MODIFY task detected - will load FULL content for: {files_needing_full_content}")
```

#### 4. Added same detection in `_call_alex_retry()` (lines 2698-2707)
Same logic applied to retry attempts to ensure consistency.

---

## How It Works

### Before Fix:
```
Task: "MODIFY src/server.js - Add authentication middleware"
Alex receives: First 80 lines of server.js (truncated)
Result: ❌ Duplicate imports, missing context
```

### After Fix:
```
Task: "MODIFY src/server.js - Add authentication middleware"
Orchestrator detects: "MODIFY" keyword in task description
Alex receives: COMPLETE server.js (no truncation)
Result: ✅ Can see all existing imports, no duplicates
```

---

## Benefits

1. **Prevents Duplicate Imports:** Alex can see all existing imports in the file
2. **Prevents Syntax Errors:** Alex knows what's already declared
3. **Better Understanding:** Alex sees the full context of the file structure
4. **Targeted Fix:** Only loads full content for files being MODIFIED, saves tokens for other files
5. **Consistency:** Works for both initial attempts and retries

---

## Keywords Detected

The fix detects these keywords in task descriptions (case-insensitive):
- `MODIFY`
- `UPDATE`
- `EDIT`

If any of these keywords are present, full file content is loaded for all files in `files_to_create`.

---

## Impact on Token Usage

**Minimal** - Only files being modified get full content. Other files still use smart truncation:
- Controllers/routes: 150 lines max
- Other files: 80 lines max

**Example:**
- Task modifies 1 file (200 lines) → Extra ~120 lines loaded
- Task references 5 files (not modified) → Still truncated at 80 lines each

---

## Testing

To verify this fix works:
1. Run a sprint with MODIFY tasks
2. Check logs for: `"MODIFY task detected - will load FULL content for: ['src/server.js']"`
3. Verify no duplicate import errors
4. Check execution log for successful test passes

---

## Future Enhancements

Potential improvements:
1. Add more keywords: `APPEND`, `INSERT`, `REFACTOR`
2. Smart loading: Show imports section + modified section + exports section
3. File diff: Show only changed parts on retry
4. Configurable truncation limits per file type

---

**Status:** ✅ Implemented and ready for testing
**Next Steps:** Restart server, re-run Sprint 1, verify no duplicate import errors

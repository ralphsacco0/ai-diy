# Turnover: Structured Template Format for Mike's Output

**Date:** December 31, 2025  
**Author:** Cascade  
**Status:** Deployed to Railway  

---

## Problem Statement

Mike (SPRINT_EXECUTION_ARCHITECT) was consistently producing invalid JSON output, causing sprint failures. The root cause was JSON escaping complexity:

- Template literals (`${}`) and backticks caused parse errors
- Backslash escaping rules were error-prone for LLMs
- Special characters required complex escaping
- JSON syntax errors blocked sprint execution

**Example failures:**
- `"description": "Use query like \`%${search}%\`"` → JSON parse error
- Regex patterns with unescaped backslashes
- Code snippets in descriptions breaking JSON structure

---

## Solution Implemented

Replaced JSON output format with **structured template format** that eliminates escaping issues.

### Template Format Example

```
STORY: US-999
CONFLICT: none

TASK: T-US-999-01
FILES: src/db.js, src/server.js
DEPENDS: none
DEPENDENCY_REASON: Foundation task
DESCRIPTION:
Create src/db.js with createDb() factory function.
Use pattern: const db = new sqlite3.Database(dbPath);
Validate email with regex: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
Template literals OK: `SELECT * FROM users WHERE name LIKE '%${search}%'`
All special characters work: $, {}, backticks, quotes, backslashes!
END_TASK

TECHNICAL_NOTES:
Your technical notes here
END_NOTES
```

### Key Benefits

1. **No escaping needed** - Write naturally with any characters
2. **Clear structure** - Delimited by keywords (TASK:, END_TASK, etc.)
3. **LLM-friendly** - Focus on content, not syntax
4. **Backward compatible** - JSON fallback preserved
5. **Better debugging** - Human-readable format

---

## Files Changed

### 1. `development/src/services/sprint_orchestrator.py`

**Added:** `_parse_structured_template()` function (~140 lines)
- Parses template format into JSON structure
- Handles STORY, CONFLICT, TASK blocks
- Extracts FILES, DEPENDS, DESCRIPTION fields
- Case-insensitive keyword matching
- Robust error handling

**Modified:** `_call_mike()` function
- Try template parser first
- Fall back to JSON parser if template fails
- Maintains backward compatibility
- Logs which format was used

**Location:** Lines 3658-3795 (new parser), Lines 2625-2636 (modified call)

### 2. `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt`

**Replaced:** All JSON format instructions with template format
- Section 1: Output format (lines 10-48)
- Section 2: Task structure examples (lines 76-91)
- Section 7: Complete example output (lines 474-543)

**Removed:** JSON escaping rules (no longer needed)

**Added:** Template format benefits and examples

**Total changes:** ~150 lines modified

---

## How It Works

### Parser Flow

1. **Template Parser** (`_parse_structured_template`)
   - Searches for `STORY:` keyword → extracts story ID
   - Searches for `CONFLICT:` → checks if "none" or conflict details
   - Finds all `TASK:` blocks → splits on keyword
   - For each task:
     - Extract task ID (first line after TASK:)
     - Extract FILES (comma-separated list)
     - Extract COMMAND (optional)
     - Extract DEPENDS (comma-separated or "none")
     - Extract DESCRIPTION (between DESCRIPTION: and END_TASK)
   - Extract TECHNICAL_NOTES (between TECHNICAL_NOTES: and END_NOTES)
   - Returns structured dict matching JSON schema

2. **Fallback to JSON** (`_extract_json`)
   - If template parse fails, try JSON parsing
   - Handles markdown code blocks
   - Attempts repair strategies
   - Returns None if both fail

3. **Validation** (`_validate_task_breakdown`)
   - Same validation as before
   - Works with both template and JSON output
   - Checks required fields, task IDs, etc.

### Backward Compatibility

- **JSON still works** - Old format supported via fallback
- **No breaking changes** - Existing architecture.json files unaffected
- **Gradual transition** - Mike will use template, but JSON accepted

---

## Testing & Verification

### What to Test

1. **New sprint execution** - Verify Mike uses template format
2. **Check logs** - Should see "✅ Mike used template format"
3. **Contract validation** - Ensure parser extracts all fields correctly
4. **Edge cases** - Special characters, long descriptions, nested quotes

### Expected Behavior

**Success indicators:**
```
✅ Mike used template format for US-XXX
✅ Successfully parsed template format: N tasks
```

**Fallback indicators:**
```
Template parse failed, trying JSON format for US-XXX
✅ Mike used JSON format for US-XXX
```

**Failure indicators:**
```
Mike returned no valid output (neither template nor JSON)
```

### Debugging

**If template parser fails:**
1. Check mike_failure_payloads/ for raw output
2. Verify keywords are present (STORY:, TASK:, END_TASK, etc.)
3. Check for missing END_TASK markers
4. Verify task IDs follow T-{STORY}-{NN} format

**If contract validation fails:**
1. Parser may have extracted wrong fields
2. Check FILES field - should be comma-separated paths
3. Check DEPENDS field - should be "none" or task IDs
4. Verify DESCRIPTION field was captured correctly

---

## Known Limitations

1. **Case sensitivity** - Parser uses case-insensitive matching, but Mike should use exact keywords
2. **Missing END_TASK** - Parser requires END_TASK marker for each task
3. **Comma-separated lists** - FILES and DEPENDS must use commas, not other delimiters
4. **No nested blocks** - Template format doesn't support nested structures

---

## Rollback Plan

If template format causes issues:

1. **Revert orchestrator changes:**
   ```bash
   git revert 8803afb  # Revert template parser commit
   git push
   railway up
   ```

2. **Or disable template parser:**
   - Comment out `_parse_structured_template()` call in `_call_mike()`
   - Force JSON-only parsing
   - Redeploy

3. **Revert Mike's prompt:**
   ```bash
   git checkout HEAD~1 system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt
   git commit -m "Revert to JSON format"
   git push
   railway up
   ```

---

## Future Improvements

1. **Better error messages** - More specific parser failure reasons
2. **Acceptance tests support** - Parse ACCEPTANCE_TESTS blocks
3. **Validation improvements** - Catch common template format mistakes
4. **Mike feedback** - If parser fails, tell Mike what's wrong
5. **Metrics** - Track template vs JSON usage rates

---

## Related Documentation

- **LLM_ONBOARDING.md** - References Mike's prompt for output format
- **system-flow.md** - Sprint execution flow (Mike → Alex → Jordan)
- **Mike's prompt** - `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt`
- **Orchestrator** - `development/src/services/sprint_orchestrator.py`

---

## Commit Information

**Commit:** 8803afb  
**Message:** "Implement structured template format for Mike's output"  
**Date:** December 31, 2025  
**Branch:** main  
**Deployed:** Railway (ai-diy-dev-production)

---

## Questions or Issues

If you encounter problems:

1. Check Railway logs for parser errors
2. Review mike_failure_payloads/ for raw output
3. Verify Mike's prompt still has template format instructions
4. Test with a simple story first (NFR-001)
5. Check if JSON fallback is working

**Contact:** Review this document and the commit for implementation details.

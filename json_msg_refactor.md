# JSON Message Format Refactor - Postmortem & Specification

**Date:** December 31, 2025  
**Author:** Cascade (AI Assistant)  
**Status:** Failed Implementation - Requires Proper Redesign

---

## Executive Summary

The template parser refactor was implemented to solve JSON escape character issues in Mike's output. While the core parsing logic works, **the implementation was incomplete and broke critical functionality**:

1. ✅ **What worked:** Template parsing, file path extraction
2. ❌ **What broke:** Dependency tracking, tech stack detection, test execution
3. 🎯 **Root cause:** Changed data structure instead of just changing parsing method

**Impact:** Contract enforcement fails for all stories with npm dependencies. Tests default to pytest instead of Node.js test runner.

---

## What Was Done

### Original Problem
Mike (Architect LLM) was outputting invalid JSON due to:
- Unescaped backslashes in regex patterns
- Template literals with `${}` syntax
- Code snippets with special characters
- Nested quotes causing parse failures

### Attempted Solution
Created a "structured template format" to replace JSON:
```
STORY: US-009
CONFLICT: none

TASK: T-US-009-01
FILES: package.json
DEPENDS: none
DESCRIPTION:
Create package.json...
END_TASK

TECHNICAL_NOTES:
Notes here...
END_NOTES
```

### Implementation Steps
1. Created `_parse_structured_template()` method in orchestrator
2. Modified Mike's prompt to output template format instead of JSON
3. Added fallback to JSON parsing for backward compatibility
4. Deployed to production

---

## What Was Done Incorrectly

### Critical Mistake #1: Incomplete Data Structure Migration

**Old JSON format had these top-level fields:**
```json
{
  "story_id": "NFR-001",
  "architectural_conflict": {...},
  "tasks": [...],
  "tech_stack": {                    // ❌ REMOVED
    "backend": "nodejs_express",
    "frontend": "html_css_js",
    "database": "sqlite",
    "test_framework": "node:test"
  },
  "dependencies": {                  // ❌ REMOVED
    "dependencies": {...},
    "devDependencies": {...}
  },
  "conventions": {...},              // ❌ REMOVED
  "technical_notes": "..."
}
```

**Template format only included:**
```
STORY: NFR-001
CONFLICT: none
TASK: ...
TECHNICAL_NOTES: ...
```

**Missing:**
- `TECH_STACK` section
- `DEPENDENCIES` section  
- `CONVENTIONS` section

### Critical Mistake #2: No Comprehensive Testing

**What should have been tested:**
1. ✅ Template parsing works
2. ❌ Contract enforcement still works
3. ❌ Dependency tracking still works
4. ❌ Tech stack detection still works
5. ❌ Test execution framework detection still works
6. ❌ Full end-to-end sprint execution

**What was actually tested:**
- Only verified template parsing succeeded
- Did not run full sprint to verify downstream impacts

### Critical Mistake #3: Assumed Orchestrator Logic Would Adapt

**Incorrect assumption:**
"The orchestrator will figure it out from the tasks"

**Reality:**
The orchestrator has explicit logic that depends on these fields:

```python
# Contract enforcement (line 1307)
deps_block = design.get("dependencies") or {}
if isinstance(deps_block, dict):
    for key in ("dependencies", "devDependencies"):
        section = deps_block.get(key) or {}
        allowed_deps.update(section.keys())

# Test execution (line 1543)
tech_stack_details = self.vision.get('tech_stack_details', {})
test_framework = tech_stack_details.get('test_framework', 'unknown')
backend = tech_stack_details.get('backend', '').lower()

# Tech stack extraction (line 1859)
if story_id == tech_stack_nfr_id and task_breakdown.get("tech_stack"):
    tech_stack = task_breakdown.get("tech_stack")
    vision['tech_stack_details'] = tech_stack
```

**These code paths require specific data structure - they don't infer from tasks.**

### Critical Mistake #4: Incremental Deployment Without Rollback Plan

**What happened:**
1. Deployed template parser
2. Contract enforcement failed
3. Fixed dependencies (partial fix)
4. Tests still failing (tech_stack missing)
5. Now discovering more missing fields

**What should have happened:**
1. Full implementation with ALL fields
2. Local testing of complete sprint
3. Staged rollout with monitoring
4. Immediate rollback capability

---

## Lessons Learned

### Lesson 1: Data Structure vs. Serialization Format
**Wrong thinking:** "Template format is easier, so let's redesign the output"  
**Right thinking:** "Keep the SAME data structure, just parse it differently"

The problem was **serialization** (JSON escaping), not **data structure**.

### Lesson 2: Downstream Dependencies Are Hidden
The orchestrator has dozens of code paths that depend on Mike's output structure:
- Contract enforcement
- Tech stack detection
- Test framework selection
- Architecture saving
- Project state extraction

**You can't see all dependencies by reading code once.**

### Lesson 3: "It Parses" ≠ "It Works"
Successful parsing is only 10% of the solution. The other 90% is:
- Does contract enforcement work?
- Do tests run correctly?
- Does tech stack propagate?
- Does retry logic work?
- Does architecture save correctly?

### Lesson 4: Refactoring Requires Complete Specification
Before changing a data format that flows through multiple systems:
1. Document EVERY field in the current format
2. Map EVERY consumer of each field
3. Verify EVERY code path still works
4. Test EVERY downstream system

### Lesson 5: Consult Before Major Changes
**What I should have done:**
"Ralph, I want to change Mike's output format to fix JSON escaping. Here's my complete specification including all fields. Can you review before I implement?"

**What I actually did:**
Implemented partial solution and discovered missing pieces in production.

---

## Proper Implementation Specification

### Phase 1: Complete Data Structure Mapping

**Document every field in current JSON format:**

```json
{
  // Core fields
  "story_id": "string",
  "architectural_conflict": {
    "detected": boolean,
    "reason": "string (optional)",
    "current_architecture": "string (optional)",
    "story_requirement": "string (optional)",
    "conflict_reason": "string (optional)",
    "recommended_action": "string (optional)"
  },
  
  // Tasks
  "tasks": [
    {
      "task_id": "string",
      "description": "string",
      "files_to_create": ["string"],
      "command_to_run": "string (optional)",
      "dependencies": ["string"],
      "dependency_reason": "string"
    }
  ],
  
  // Tech stack (NFR-001 only)
  "tech_stack": {
    "backend": "string",
    "frontend": "string",
    "database": "string",
    "test_framework": "string (optional)"
  },
  
  // Dependencies (all stories)
  "dependencies": {
    "dependencies": {"pkg": "version"},
    "devDependencies": {"pkg": "version"}
  },
  
  // Conventions (NFR-001 only)
  "conventions": {
    "module_system": "string",
    "database_entry_point": "string",
    "database_factory": "string",
    "init_function": "string",
    "auth_method": "string",
    "export_pattern": "string",
    "api_response_format": "string",
    "error_handling": "string"
  },
  
  // Technical notes
  "technical_notes": "string",
  
  // Optional fields
  "acceptance_tests_text": "string (optional)",
  "task_count": number
}
```

### Phase 2: Template Format Design

**Map EVERY JSON field to template syntax:**

```
STORY: [story_id]

CONFLICT: none
// OR
CONFLICT: detected
CONFLICT_REASON: [reason]
CURRENT_ARCHITECTURE: [current]
STORY_REQUIREMENT: [requirement]
RECOMMENDED_ACTION: [action]
END_CONFLICT

TECH_STACK:
backend: [backend]
frontend: [frontend]
database: [database]
test_framework: [framework]
END_TECH_STACK

CONVENTIONS:
module_system: [system]
database_entry_point: [path]
database_factory: [function]
init_function: [function]
auth_method: [method]
export_pattern: [pattern]
api_response_format: [format]
error_handling: [pattern]
END_CONVENTIONS

DEPENDENCIES:
dependencies: [pkg1, pkg2, pkg3]
devDependencies: [pkg1, pkg2]
END_DEPENDENCIES

TASK: [task_id]
FILES: [file1, file2]
COMMAND: [command]
DEPENDS: [task_id1, task_id2]
DEPENDENCY_REASON: [reason]
DESCRIPTION:
[multi-line description]
END_TASK

TECHNICAL_NOTES:
[multi-line notes]
END_NOTES
```

### Phase 3: Parser Implementation

**Complete parser that handles ALL fields:**

```python
def _parse_structured_template(self, text: str) -> Optional[Dict]:
    """Parse Mike's structured template into exact same structure as JSON."""
    result = {
        "story_id": None,
        "architectural_conflict": {"detected": False},
        "tasks": [],
        "technical_notes": ""
    }
    
    # Extract story ID (required)
    story_match = re.search(r'STORY:\s*(\S+)', text, re.IGNORECASE)
    if not story_match:
        return None
    result["story_id"] = story_match.group(1).strip()
    
    # Extract architectural conflict
    conflict_match = re.search(r'CONFLICT:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
    if conflict_match and conflict_match.group(1).strip().lower() != 'none':
        result["architectural_conflict"]["detected"] = True
        # Extract conflict details...
    
    # Extract tech_stack (NFR-001 only)
    tech_stack_match = re.search(r'TECH_STACK:\s*(.+?)\s*END_TECH_STACK', text, re.DOTALL | re.IGNORECASE)
    if tech_stack_match:
        tech_block = tech_stack_match.group(1).strip()
        result["tech_stack"] = {}
        # Parse backend, frontend, database, test_framework lines...
    
    # Extract conventions (NFR-001 only)
    conventions_match = re.search(r'CONVENTIONS:\s*(.+?)\s*END_CONVENTIONS', text, re.DOTALL | re.IGNORECASE)
    if conventions_match:
        conv_block = conventions_match.group(1).strip()
        result["conventions"] = {}
        # Parse all convention fields...
    
    # Extract dependencies
    deps_match = re.search(r'DEPENDENCIES:\s*(.+?)\s*END_DEPENDENCIES', text, re.DOTALL | re.IGNORECASE)
    if deps_match:
        deps_block = deps_match.group(1).strip()
        result["dependencies"] = {"dependencies": {}, "devDependencies": {}}
        # Parse dependencies and devDependencies lines...
    
    # Extract tasks
    # ... (existing task parsing logic)
    
    # Extract technical notes
    # ... (existing notes parsing logic)
    
    return result
```

### Phase 4: Comprehensive Testing

**Test matrix:**

| Test Case | Input | Expected Output | Actual Output | Status |
|-----------|-------|----------------|---------------|--------|
| Template parsing | Template format | Dict with all fields | ? | ❌ |
| JSON fallback | JSON format | Dict with all fields | ? | ❌ |
| Contract enforcement | Template → contract | allowed_deps populated | ? | ❌ |
| Tech stack extraction | NFR-001 template | vision.tech_stack_details set | ? | ❌ |
| Test execution | Node.js project | node --test runs | ? | ❌ |
| Full sprint | SP-001 with NFR-001 | All stories pass | ? | ❌ |

**Each test must PASS before deployment.**

### Phase 5: Staged Deployment

1. **Local testing:** Run complete sprint locally
2. **Validation:** Verify all downstream systems work
3. **Commit:** Push to git with comprehensive commit message
4. **Monitor:** Watch first production sprint closely
5. **Rollback plan:** Keep old JSON format code for quick revert

---

## Current State & Next Steps

### What's Fixed
- ✅ Template parser core logic
- ✅ File path extraction
- ✅ Dependencies extraction (partial - added after initial deploy)

### What's Broken
- ❌ Tech stack extraction (missing TECH_STACK section)
- ❌ Test framework detection (defaults to pytest)
- ❌ Conventions extraction (missing CONVENTIONS section)
- ❌ Full contract enforcement (dependencies now work, but was broken)

### Recommended Action

**Option 1: Complete the refactor properly**
- Add TECH_STACK section to template format
- Add CONVENTIONS section to template format
- Update parser to extract both sections
- Test complete sprint end-to-end
- Deploy with monitoring

**Option 2: Rollback to JSON format**
- Revert Mike's prompt to JSON output
- Remove template parser code
- Keep JSON escape character fixes in prompt
- Accept that JSON is harder to write but works

**Option 3: Hybrid approach**
- Keep template format for task descriptions (where escaping is worst)
- Use JSON for structured fields (tech_stack, dependencies, conventions)
- Combine both in parser

---

## Conclusion

This refactor failed because:
1. **Incomplete specification** - Didn't map all fields before starting
2. **Insufficient testing** - Only tested parsing, not downstream impacts
3. **Incremental discovery** - Found missing pieces in production
4. **Wrong abstraction** - Changed data structure instead of just serialization

**Key takeaway:** When refactoring a data format that flows through multiple systems, you must:
- Document EVERY field in current format
- Map EVERY consumer of each field
- Test EVERY downstream system
- Deploy ONLY when 100% complete

**The proper approach:** Keep the SAME data structure, just parse it differently. The problem was JSON escaping, not the data model itself.

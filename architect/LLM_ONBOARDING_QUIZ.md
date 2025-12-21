# LLM Onboarding Quiz - Answer Key

**Purpose**: Verify LLM has actually read and understood the documentation  
**Usage**: Keep this file separate/private. Ask LLM to answer questions from LLM_ONBOARDING.md Section 1  
**Last Updated**: 2025-12-08

---

## Quiz Questions and Answers

### Question 1: What is the canonical ID for the Vision living document?
**Answer**: `vision`

**Location**: `architect/architecture.md` - Pattern 2: Living Document (Backlog & Vision)
- Vision uses a single canonical JSON + MD pair (`vision.json`, `vision.md`) per project
- Fixed ID: `vision`

**Why This Matters**: LLMs often try to create versioned vision files like `vision_20251208_120000.json`, which violates the living document pattern and causes data management issues.

---

### Question 2: What format MUST task IDs follow in Mike's design output?
**Answer**: `T-{STORY_ID}-{TASK_NUMBER}` where TASK_NUMBER is zero-padded two digits

**Examples**: 
- ✅ Correct: `T-NFR-001-01`, `T-US-009-02`, `T-WF-003-10`
- ❌ Wrong: `T-NFR-001-1`, `T001`, `TASK-004`, `T-US-009-2`

**Location**: `architect/system-flow.md` - Section 4.1.2 Mike's 5-Phase Design Process, Phase 3

**Why This Matters**: Non-zero-padded task IDs break the orchestrator's validation and cause execution failures.

---

### Question 3: Where do ALL data files get stored (the root directory)?
**Answer**: `static/appdocs/`

**Subdirectories**:
- `static/appdocs/visions/` - Vision documents
- `static/appdocs/backlog/` - Backlog CSV and wireframes
- `static/appdocs/sprints/` - Sprint plans and execution logs

**Location**: `architect/PATTERNS_AND_METHODS.md` - Data Storage Patterns

**Why This Matters**: Storing files outside this directory breaks data management, backups, and security validation.

---

### Question 4: Which two files are the "gold standard" to copy when creating new API endpoints?
**Answer**: 
1. `development/src/api/vision.py` - For simple document storage
2. `development/src/api/backlog.py` - For CSV/tabular data with wireframes

**Location**: `architect/PATTERNS_AND_METHODS.md` - Quick Starts: Add a New API Endpoint

**Why This Matters**: These files implement all required patterns (unified response format, 5 standard actions, proper error handling). Inventing new patterns causes inconsistency.

---

### Question 5: What are the 5 standard actions ALL API endpoints must support?
**Answer**:
1. **save** - Create or update resource
2. **get** - Retrieve specific resource by ID
3. **list** - List all resources with metadata
4. **delete** - Remove resource
5. **latest** - Get most recent resource

**Location**: `architect/architecture.md` - API Architecture: Standard Actions

**Why This Matters**: Consistent API actions make the frontend predictable and reduce code duplication.

---

### Question 6: Where do persona definitions live (both metadata AND prompts)?
**Answer**: 
- **Metadata and wiring**: `system_prompts/personas_config.json`
- **System prompts**: `system_prompts/*_system_prompt.txt` (one file per persona)

**Location**: `architect/summary.md` - Section 2.2 Persona Configuration

**Why This Matters**: Persona behavior must live in configuration (JSON + text files), NOT in Python code. This allows non-coders to modify behavior.

---

### Question 7: What is the unified API response format that ALL endpoints must return?
**Answer**:
```json
{
  "success": true|false,
  "message": "string",
  "data": { ... }
}
```

**Error responses include**:
```json
{
  "success": false,
  "message": "Error description",
  "data": {
    "error_code": "VALIDATION_ERROR"
  }
}
```

**Location**: `architect/architecture.md` - API Architecture: Unified Response Format

**Why This Matters**: Custom response formats break the frontend and violate ADR-002.

---

### Question 8: What are the 5 sections Mike MUST output in his design (before tasks)?
**Answer**:
1. **Database Design** - NEW tables and MODIFIED tables with exact field specifications
2. **API Design** - NEW endpoints and MODIFIED endpoints with request/response formats
3. **File Structure** - Which files to create and which to modify
4. **Code Patterns** - How this follows established patterns (error handling, async/await, response format)
5. **Dependencies** - ALL npm/pip packages required with versions and dev/regular classification

**Location**: `architect/system-flow.md` - Section 4.1.2 Mike's 5-Phase Design Process, Phase 2

**Why This Matters**: Missing dependencies cause runtime errors. Missing design sections leave Alex without context for implementation.

---

### Question 9: What is the FIRST story in every sprint, and why is it critical?
**Answer**: **NFR-001** (Tech Stack NFR)

**Why Critical**:
- Sprint orchestrator extracts tech stack from NFR-001 before processing other stories
- Tech stack determines project structure, test framework, and implementation patterns
- All other stories depend on tech stack being established
- If NFR-001 is missing or not first, sprint execution fails immediately

**Location**: `architect/system-flow.md` - Section 4.1.1 Tech Stack NFR Requirement

**Why This Matters**: Skipping NFR-001 or putting it later in the sprint causes immediate execution failure.

---

### Question 10: How many smoke tests should Jordan write per story?
**Answer**: **1-2 tests ONLY** (not comprehensive tests)

**Critical Rules**:
- ✅ Write EXACTLY 1-2 tests per story - NO MORE
- ✅ Smoke tests verify code runs without crashing
- ❌ DO NOT write comprehensive tests
- ❌ DO NOT test every acceptance criterion
- ❌ DO NOT spawn child processes (spawn, exec, fork)
- ❌ DO NOT parse log output to find ports
- ✅ ALWAYS import modules directly
- ✅ ALWAYS use native test utilities (app.listen(0), app.address().port)

**Location**: `architect/system-flow.md` - Section 4.1.3 Jordan's Smoke Test Pattern

**Why This Matters**: Comprehensive tests slow down sprints and lead to infinite bug discovery loops. Smoke tests just verify "it runs."

---

## Scoring Guide

**10/10**: LLM has read and understood the documentation  
**7-9/10**: LLM has read most docs but missed some details  
**4-6/10**: LLM skimmed the docs, needs to read more carefully  
**0-3/10**: LLM did not read the docs, STOP and require full reading

---

## How to Use This Quiz

### At Session Start
1. Ask the LLM to answer the 10 questions from `LLM_ONBOARDING.md` Section 1
2. Compare their answers to this answer key
3. If they score below 7/10, require them to read the specific documents they missed
4. Only proceed with work once they demonstrate understanding

### Red Flags
- LLM says "I've read the docs" but can't answer basic questions
- LLM gives vague answers instead of specific details
- LLM guesses instead of citing documentation
- LLM tries to skip the quiz

### When LLM Fails Quiz
Don't just give them the answers. Instead:
1. Tell them which questions they got wrong
2. Point them to the specific document and section
3. Require them to read that section and try again
4. Verify understanding before allowing work to proceed

---

## Common Wrong Answers (What to Watch For)

### Question 1 - Vision ID
- ❌ "vision_20251208_120000" (versioned pattern - WRONG)
- ❌ "Vision" (capitalized - WRONG)
- ❌ "latest vision" (vague - WRONG)
- ✅ "vision" (correct)

### Question 2 - Task ID Format
- ❌ "T-US-009-1" (not zero-padded - WRONG)
- ❌ "T001" (missing story ID - WRONG)
- ❌ "TASK-004" (wrong prefix - WRONG)
- ✅ "T-US-009-01" (correct)

### Question 3 - Data Storage
- ❌ "src/data/" (WRONG)
- ❌ "anywhere in the project" (WRONG)
- ❌ "development/data/" (WRONG)
- ✅ "static/appdocs/" (correct)

### Question 4 - Gold Standard Files
- ❌ "main.py" (WRONG - that's the entry point)
- ❌ "any API file" (too vague - WRONG)
- ❌ "I'll create a new pattern" (RED FLAG - WRONG)
- ✅ "vision.py or backlog.py" (correct)

### Question 5 - Standard Actions
- ❌ Lists only 3-4 actions (incomplete - WRONG)
- ❌ Includes non-standard actions like "update" or "patch" (WRONG)
- ❌ "Whatever actions are needed" (RED FLAG - WRONG)
- ✅ Lists all 5: save, get, list, delete, latest (correct)

### Question 6 - Persona Locations
- ❌ "In Python files" (RED FLAG - WRONG)
- ❌ "Just personas_config.json" (incomplete - WRONG)
- ❌ "In the database" (WRONG)
- ✅ "personas_config.json AND *_system_prompt.txt files" (correct)

### Question 7 - API Response Format
- ❌ Describes a custom format (RED FLAG - WRONG)
- ❌ "Whatever format makes sense" (RED FLAG - WRONG)
- ❌ Missing the data field (incomplete - WRONG)
- ✅ Correctly describes {success, message, data} (correct)

### Question 8 - Mike's 5 Sections
- ❌ Lists only tasks (missing design sections - WRONG)
- ❌ Lists 3-4 sections (incomplete - WRONG)
- ❌ "Whatever design is needed" (RED FLAG - WRONG)
- ✅ Lists all 5: Database, API, File Structure, Code Patterns, Dependencies (correct)

### Question 9 - First Story
- ❌ "Any story can be first" (WRONG)
- ❌ "US-001" (WRONG)
- ❌ "The most important user story" (WRONG)
- ✅ "NFR-001 (Tech Stack NFR)" with explanation of why (correct)

### Question 10 - Jordan's Test Count
- ❌ "As many as needed" (RED FLAG - WRONG)
- ❌ "Comprehensive tests" (RED FLAG - WRONG)
- ❌ "3-5 tests" (WRONG)
- ✅ "1-2 smoke tests only" (correct)

---

**End of Quiz Answer Key**

*Keep this file private. Use it to verify LLM comprehension before allowing work to proceed.*

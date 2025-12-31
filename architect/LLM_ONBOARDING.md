# LLM Onboarding: Mandatory Pre-Flight for AI-DIY Work

**Status**: Canonical - MUST READ before any work session  
**Audience**: LLMs working on AI-DIY platform  
**Purpose**: Prevent "2 steps forward, 1 step back" by ensuring deep understanding  
**Last Updated**: 2025-12-30

---

## 🚨 CRITICAL: Read This FIRST, Every Session

If you are an LLM starting work on AI-DIY:

1. **DO NOT** claim you've read the documentation unless you actually have
2. **DO NOT** take shortcuts or invent new patterns
3. **DO NOT** make changes without completing the verification checklist below
4. **DO** answer the comprehension quiz to prove you understand the architecture

**This system has a complex, deliberate design. Shortcuts cause rework.**

---

## CRITICAL: MAC AND RAILWAY ARE SEPARATE SYSTEMS

⚠️ ⚠️ ⚠️ MAC AND RAILWAY ARE 2 DIFFERENT SYSTEMS WITH THE SAME CODEBASE 
⚠️ THERE IS NO EXPECTATION THAT THEY SHOULD BE IN SYNC ⚠️

---

## Section 1: Comprehension Quiz

Answer these questions to prove you've read the core documentation. If you cannot answer these without looking them up, **STOP and read the docs first**.

### Quiz Questions

1. **What is the canonical ID for the Vision living document?**
   - Hint: Check `architect/architecture.md` - Living Document pattern

2. **What format MUST task IDs follow in Mike's design output?**
   - Hint: Check `architect/system-flow.md` - Mike's 5-Phase Design Process

3. **Where do ALL data files get stored (the root directory)?**
   - Hint: Check `architect/PATTERNS_AND_METHODS.md` - Data Storage Patterns

4. **Which two files are the "gold standard" to copy when creating new API endpoints?**
   - Hint: Check `architect/PATTERNS_AND_METHODS.md` - Quick Starts

5. **What are the 5 standard actions ALL API endpoints must support?**
   - Hint: Check `architect/architecture.md` - API Architecture

6. **Where do persona definitions live (both metadata AND prompts)?**
   - Hint: Check `architect/summary.md` - Persona Configuration

7. **What is the unified API response format that ALL endpoints must return?**
   - Hint: Check `architect/architecture.md` - Unified Response Format

8. **What are the 5 sections Mike MUST output in his design (before tasks)?**
   - Hint: Check `architect/system-flow.md` - Mike's 5-Phase Design Process, Phase 2

9. **What is the FIRST story in every sprint, and why is it critical?**
   - Hint: Check `architect/system-flow.md` - Tech Stack NFR Requirement

10. **How many smoke tests should Jordan write per story?**
    - Hint: Check `architect/system-flow.md` - Jordan's Smoke Test Pattern

### Answer Key Location
Answers are embedded in the hints above. If you cannot find them, you haven't read the documentation carefully enough.

---

## Section 2: Critical Anti-Patterns (The "Don't Do This" List)

These are the mistakes that cause "2 steps forward, 1 step back." **NEVER** do these:

### Data Storage Anti-Patterns
- ❌ **DON'T** store files outside `static/appdocs/` (breaks data management)
- ❌ **DON'T** create versioned Vision files (Vision is a living document with ID `vision`)
- ❌ **DON'T** create new Backlog files (Backlog is a living document: `Backlog.csv`)
- ❌ **DON'T** skip rotating backups when saving Backlog or Vision
- ❌ **DON'T** modify CSV headers or add columns without ADR approval
 - ❌ Missing `static/appdocs` in execution-sandbox paths (e.g., `development/src/execution-sandbox/...` is wrong)
 - ❌ Using `project-sandbox` or `client projects` (with a space). Correct: `execution-sandbox/client-projects/`
 - ❌ Using dynamic or legacy app folder names for generated apps. Folder name is fixed: `yourapp`

### API Anti-Patterns
- ❌ **DON'T** create custom response formats (use `api/conventions.py`)
- ❌ **DON'T** invent new endpoint patterns (copy `vision.py` or `backlog.py`)
- ❌ **DON'T** skip the 5 standard actions (save, get, list, delete, latest)
- ❌ **DON'T** forget to register new routers in `main.py`
- ❌ **DON'T** hardcode paths (use `Path()` and relative paths)

### Persona Anti-Patterns
- ❌ **DON'T** put persona logic in Python code (belongs in JSON config)
- ❌ **DON'T** modify `personas_config.json` without understanding meeting triggers
- ❌ **DON'T** create duplicate personas for the same person (use role mapping)
- ❌ **DON'T** forget `enabled: true` (persona won't load)
- ❌ **DON'T** give Scribe `meeting_triggers` (breaks isolation pattern)
- ❌ **DON'T** assume all personas get all tools (tools are filtered by config)
- ❌ **DON'T** rely on prompt-based gating for critical behavior (use hard gates like SPRINT_REVIEW_PM name check)

### Sprint Execution Anti-Patterns
- ❌ **DON'T** let Mike skip the 5-phase design process
- ❌ **DON'T** let Mike output tasks without `files_to_create` (causes failures)
- ❌ **DON'T** let Mike forget the `dependencies` section (missing npm packages)
- ❌ **DON'T** use non-zero-padded task IDs (`T-US-009-1` instead of `T-US-009-01`)
- ❌ **DON'T** let Jordan write more than 1-2 smoke tests per story
- ❌ **DON'T** let Jordan use `spawn/exec/fork` in tests (use direct imports)
- ❌ **DON'T** let Jordan forget `res.resume()` in HTTP tests (causes 120s timeout)
- ❌ **DON'T** skip NFR-001 as the first story (sprint will fail)
- ❌ **DON'T** add `<base href="/">` or any `<base>` tag to HTML files (breaks navigation on Railway)
- ❌ **DON'T** let Mike specify `<base>` tags in technical notes (contradicts platform requirements)

### Governance Anti-Patterns
- ❌ **DON'T** make changes without explaining them first
- ❌ **DON'T** skip waiting for Ralph's approval
- ❌ **DON'T** create new documentation files (update existing ones)
- ❌ **DON'T** contradict existing ADRs without proposing a new ADR
- ❌ **DON'T** use defaults or silent fallbacks (fail fast with clear errors)

#### Git Workflow
- ✅ **DO** commit and push to main for all approved changes
- ✅ **DO** use focused, descriptive commit messages
- ❌ **DON'T** use long-lived feature branches (this repo uses trunk-based development)

### Configuration Anti-Patterns
- ❌ **DON'T** hardcode configuration in Python (use JSON or environment variables)
- ❌ **DON'T** use default values for missing config (fail fast instead)
- ❌ **DON'T** put system prompts in Python strings (use `*_system_prompt.txt` files)

---

## Section 3: SEMINAL SPECIFICATION - Module System & Architecture Decisions

**Status**: CANONICAL - This is the definitive specification  
**Purpose**: Prevent "sonnet in claude code" conflicts between architecture.json and package.json  
**Reference this section**: When an LLM wants to go another way on module system decisions  

### The Fundamental Truth

**THE AI-DIY PLATFORM USES ONLY COMMONJS MODULE SYSTEM. PERIOD.**

This is not negotiable, not configurable, not dependent on user preferences. It is hardcoded into the platform architecture for stability and consistency.

### Source of Truth Hierarchy

1. **ULTIMATE SOURCE**: Mike's system prompt (`SPRINT_EXECUTION_ARCHITECT_system_prompt.txt`)
   - Lines 97-102: "COMMONJS MODULE SYSTEM (MANDATORY)" 
   - Line 98: "NEVER add 'type': 'module' to package.json"
   - Line 322: "module_system: 'commonjs'" (for NFR-001)

2. **Generated Artifacts**: architecture.json and package.json are OUTPUTS, not inputs
   - architecture.json gets `"module_system": "commonjs"` because Mike's prompt mandates it
   - package.json should NEVER get `"type": "module"` because Mike's prompt forbids it

3. **Downstream Prompts**: Alex and Jordan must align with Mike's decisions
   - If they don't align → sprint failures occur
   - If they contradict → "require is not defined in ES module scope" errors

### The Decision Chain (How It Should Work)

```
Mike's Prompt: "COMMONJS MODULE SYSTEM (MANDATORY)"
    ↓
Mike generates: architecture.json with "module_system": "commonjs"
    ↓  
Alex receives: Mike's architecture + Alex follows CommonJS rules
    ↓
Alex generates: package.json WITHOUT "type": "module"
    ↓
Jordan receives: Mike's conventions + Alex's files
    ↓
Jordan writes: Tests using require() and module.exports
    ↓
Result: Consistent CommonJS throughout entire application
```

### The Failure Chain (What Happens When Prompts Conflict)

```
Mike's Prompt: "NEVER add 'type': 'module'"
    ↓ BUT ↓
Alex's Prompt: "If ES6: Add 'type': 'module'"  ← CONTRADICTION!
    ↓
Alex sometimes adds: "type": "module" to package.json
    ↓
Jordan's Prompt: "Check package.json for module type"  ← AMPLIFIES ERROR!
    ↓
Jordan writes: Tests using import/export (because package.json says ES modules)
    ↓
Node.js: Treats ALL .js files as ES modules
    ↓
Mike's/Alex's CommonJS code: Uses require() and module.exports
    ↓
FAILURE: "require is not defined in ES module scope"
```

### Canonical Rules for All Personas

**FOR MIKE (Architect)**:
- ✅ ALWAYS output `"module_system": "commonjs"` in architecture.json
- ✅ ALWAYS include the "COMMONJS MODULE SYSTEM (MANDATORY)" rule in task guidance
- ❌ NEVER allow ES modules, even if user requests them

**FOR ALEX (Developer)**:
- ✅ ALWAYS use require() and module.exports in ALL .js files
- ✅ ALWAYS omit "type" field from package.json (CommonJS is default)
- ❌ NEVER add `"type": "module"` to package.json under ANY circumstances
- ❌ NEVER use import/export statements in .js files
- 🚨 IF you see ES module instructions in your prompt: IGNORE THEM and use CommonJS

**FOR JORDAN (QA)**:
- ✅ ALWAYS use require('node:test') and require('node:assert') in tests
- ✅ ALWAYS use require() to import app modules: `const app = require('../src/server.js')`
- ❌ NEVER use import statements in test files
- 🚨 IF package.json has `"type": "module"`: IGNORE IT and use CommonJS anyway

**FOR SPRINT REVIEW ALEX**:
- ✅ When fixing bugs, restore code to CommonJS if it diverged
- ✅ Remove `"type": "module"` from package.json if present
- ❌ Never "fix" CommonJS code by converting it to ES modules

### Why This Specification Exists

**Historical Problem**: LLMs were receiving contradictory instructions:
- Mike's prompt: "NEVER add 'type': 'module'"
- Alex's prompt: "IF ES6: add 'type': 'module'" 
- Jordan's prompt: "Check package.json for module type"

**Result**: ~30% first-sprint failure rate due to module system conflicts

**Solution**: This specification removes all ambiguity. CommonJS is the only option.

### Troubleshooting Module System Failures

**Symptom**: "require is not defined in ES module scope"
**Root Cause**: Someone added `"type": "module"` to package.json
**Fix**: Remove the `"type": "module"` line and restart

**Symptom**: "Cannot use import statement outside a module"  
**Root Cause**: ES module syntax in .js file with CommonJS package.json
**Fix**: Convert import/export to require/module.exports

**Symptom**: Tests fail with module errors
**Root Cause**: Test files mixing module systems  
**Fix**: Ensure ALL test files use require() for imports

### The 8 Touch Points for Module System Consistency

When auditing or changing module system behavior, these are ALL the files that must align:

| # | Component | File Path | What to Check | Expected Value |
|---|-----------|-----------|---------------|----------------|
| 1 | **Vision Prompt** | `system_prompts/VISION_PM_system_prompt.txt` | Lines 51-59: Tech stack specification | Node.js + Express, no mention of ES modules |
| 2 | **Requirements Prompt** | `system_prompts/REQUIREMENTS_PM_system_prompt.txt` | Lines 255-269: NFR-001 conflict detection | Must flag ES6 modules as conflicts |
| 3 | **Sprint Orchestrator** | `development/src/services/sprint_orchestrator.py` | Lines 475-478: Export style hints | CommonJS patterns only |
| 4 | **Mike's Prompt** | `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt` | Lines 97-102: Module system rules | "COMMONJS MODULE SYSTEM (MANDATORY)" |
| 5 | **Alex's Prompt** | `system_prompts/SPRINT_EXECUTION_DEVELOPER_system_prompt.txt` | Lines 69-80: Module system handling | 🚨 CONFLICTS - remove ES module options |
| 6 | **Jordan's Prompt** | `system_prompts/SPRINT_EXECUTION_QA_system_prompt.txt` | Line 433: Module system detection | 🚨 CONFLICTS - check architecture, not package.json |
| 7 | **Sprint Review Alex** | `system_prompts/SPRINT_REVIEW_ALEX_system_prompt.txt` | Lines 232, 244: Architecture compliance | References locked architecture as source |
| 8 | **Generated Architecture** | `static/appdocs/architecture.json` | Line 6: module_system field | Always "commonjs" (output, not input) |

### Touch Point Audit Checklist

Before making ANY module system changes, verify ALL 8 touch points align:

- [ ] **Vision Prompt**: Specifies Node.js + Express only, no ES module mentions
- [ ] **Requirements Prompt**: Flags ES6 modules as conflicts in NFR-001 detection
- [ ] **Sprint Orchestrator**: Uses CommonJS patterns in export hints
- [ ] **Mike's Prompt**: Enforces "COMMONJS MODULE SYSTEM (MANDATORY)"
- [ ] **Alex's Prompt**: Uses ONLY CommonJS instructions (no ES module options)
- [ ] **Jordan's Prompt**: Checks architecture.json, not package.json for module system
- [ ] **Sprint Review Alex**: References locked architecture as source of truth
- [ ] **Generated Architecture**: Contains `"module_system": "commonjs"` (result of above)

### Reference for Future LLMs

When working on AI-DIY and you encounter module system decisions:

1. **Read this section first** - Don't rely on other prompts
2. **Use CommonJS everywhere** - No exceptions, no configurations  
3. **Check all 8 touch points** - Use the audit checklist above
4. **Report conflicts** - If your prompt contradicts this spec, flag it to Ralph
5. **Stay consistent** - One module system, all the time, every sprint

This specification supersedes any conflicting instructions in individual persona prompts.

---

## Section 4: Pre-Change Verification Checklist

**BEFORE making ANY change, complete this checklist:**

### Step 1: Understand the Request
- [ ] I understand what the user is asking for
- [ ] I know which part of the system this affects (API, persona, meeting, data storage)
- [ ] I have identified any ambiguities and will ask for clarification

### Step 2: Identify the Pattern
- [ ] I have identified which pattern applies from `PATTERNS_AND_METHODS.md`
- [ ] I know which existing file to copy as a template (if applicable)
- [ ] I understand why this pattern exists and what it prevents

### Step 3: Review Relevant Documentation
- [ ] I have read the relevant sections of `summary.md`
- [ ] I have read the relevant sections of `architecture.md`
- [ ] I have read the relevant sections of `system-flow.md` (if meeting-related)
- [ ] I have read the relevant sections of `PATTERNS_AND_METHODS.md`
- [ ] I have checked `ADRs.md` for related decisions
- [ ] I have reviewed `GOVERNANCE.md` for approval requirements

### Step 4: Plan the Change
- [ ] I can cite specific line numbers from the docs that support my approach
- [ ] I have identified all files that need to be modified
- [ ] I know which pattern I'm following (with file reference)
- [ ] I have checked for related ADRs that might be affected

### Step 5: Explain and Wait for Approval
- [ ] I have explained the change in plain English
- [ ] I have stated which pattern I'm following
- [ ] I have listed which files will be modified
- [ ] I have waited for Ralph's explicit approval before proceeding

### Step 6: Implement Correctly
- [ ] I am copying an existing pattern, not inventing a new one
- [ ] I am using the unified API response format (if API change)
- [ ] I am storing files in `static/appdocs/` (if data change)
- [ ] I am updating documentation as part of this change (if needed)
- [ ] I am following the existing code style and naming conventions

### Step 7: Verify the Change
- [ ] I have tested the change (or provided test commands)
- [ ] I have updated relevant documentation
- [ ] I have not introduced any anti-patterns from Section 2
- [ ] I have not contradicted any existing ADRs

---

## Section 4: Quick Reference Card

### File Locations (Where Things Live)

| What | Where | Notes |
|------|-------|-------|
| All data files | `static/appdocs/` | NEVER store outside this |
| Vision (living doc) | `static/appdocs/visions/vision.json` | Single canonical file, ID = `vision` |
| Backlog (living doc) | `static/appdocs/backlog/Backlog.csv` | Single canonical file |
| Wireframes | `static/appdocs/backlog/wireframes/` | HTML files |
| Sprint plans | `static/appdocs/sprints/` | JSON files |
| Persona config | `system_prompts/personas_config.json` | Metadata and wiring |
| Persona prompts | `system_prompts/*_system_prompt.txt` | One file per persona |
| API endpoints | `development/src/api/` | Copy vision.py or backlog.py |
| API conventions | `development/src/api/conventions.py` | Response formats |
| Main entry point | `development/src/main.py` | Single consolidated entry |
| Logs | `development/src/logs/app.jsonl` | Structured JSONL |
| Documentation | `architect/` | All canonical docs |

_Generated app sandbox (fixed):_ `static/appdocs/execution-sandbox/client-projects/yourapp/` _(Railway adds `/app` prefix)._ 

### Key Patterns (Which File to Copy for What)

| Need to... | Copy this file | Key points |
|------------|---------------|------------|
| Add API endpoint | `api/vision.py` or `api/backlog.py` | Use unified response format, 5 standard actions |
| Add persona | Existing persona in `personas_config.json` | Same person can have multiple roles |
| Add meeting type | Existing meeting config | Use meeting triggers, role mapping |
| Store versioned docs | N/A (Vision no longer uses this) | For future features only |
| Store living doc | `api/vision.py` (living doc pattern) | Single file, fixed ID |
| Store tabular data | `api/backlog.py` (CSV pattern) | Single CSV, row-based items |

### Critical Rules (The "Always" Rules)

✅ **ALWAYS** fail fast with clear error messages  
✅ **ALWAYS** check for existing patterns before coding  
✅ **ALWAYS** use the unified API response format  
✅ **ALWAYS** store configuration in JSON (human-editable)  
✅ **ALWAYS** explain intended changes and wait for confirmation  
✅ **ALWAYS** follow governance (propose → discuss → approve → implement)  
✅ **ALWAYS** update documentation as part of Definition of Done  
✅ **ALWAYS** use `static/appdocs/` for data storage  
✅ **ALWAYS** copy existing patterns, never invent new ones  
✅ **ALWAYS** preserve existing CSV headers and schema  

### Common Gotchas (Mistakes That Cause Rework)

1. **Vision is a living document** - Don't create `vision_20251208_120000.json`, use `vision.json`
2. **Backlog is a living document** - Don't create multiple Backlog files, update `Backlog.csv`
3. **Task IDs must be zero-padded** - `T-US-009-01` not `T-US-009-1`
4. **Mike must output 5 design sections** - Database, API, File Structure, Code Patterns, Dependencies
5. **NFR-001 must be first** - Every sprint starts with Tech Stack NFR
6. **Jordan writes 1-2 tests only** - Smoke tests, not comprehensive tests
7. **No spawn/exec in tests** - Use direct imports and native test utilities
8. **HTTP tests need res.resume()** - Without it, 'end' event never fires and test times out after 120s
9. **Personas live in config** - Not in Python code
10. **API responses use conventions.py** - Not custom formats
11. **Files go in static/appdocs/** - Not anywhere else
12. **NEVER use `<base>` tag in HTML** - Breaks navigation on Railway; relative paths work without it

### The 5 Standard API Actions

Every API endpoint MUST support:
1. **save** - Create or update resource
2. **get** - Retrieve specific resource by ID
3. **list** - List all resources with metadata
4. **delete** - Remove resource
5. **latest** - Get most recent resource

### The 5 Phases of Mike's Design

Mike MUST output these sections before tasks:
1. **Database Design** - NEW and MODIFIED tables
2. **API Design** - NEW and MODIFIED endpoints
3. **File Structure** - Which files to create/modify
4. **Code Patterns** - How this follows established patterns
5. **Dependencies** - ALL npm/pip packages with versions

### Meeting Types and Personas

**CRITICAL CONCEPT**: There are 4 **base personas** (Sarah, Mike, Alex, Jordan), but each has **specialized versions** for different meetings with different prompts and context.

**Base Personas**:
- **Sarah** (PM) - Base project manager
- **Mike** (Architect) - Base architect
- **Alex** (Developer) - Base developer
- **Jordan** (QA) - Base QA tester

**Specialized Versions** (same person, different context/prompts):
- Sarah: `PM`, `VISION_PM`, `REQUIREMENTS_PM`, `SPRINT_EXECUTION_PM`, `SPRINT_REVIEW_PM`
- Mike: `ARCHITECT`, `SPRINT_PLANNING_ARCHITECT`, `SPRINT_EXECUTION_ARCHITECT`
- Alex: `DEVELOPER`, `SPRINT_EXECUTION_DEVELOPER`, `SPRINT_REVIEW_ALEX`
- Jordan: `QA`, `SPRINT_EXECUTION_QA`

**Configuration**:
- Metadata/wiring: `system_prompts/personas_config.json`
- System prompts: `system_prompts/*_system_prompt.txt` (one file per specialized persona)

| Meeting | Lead Persona | Purpose | Output |
|---------|-------------|---------|--------|
| Vision | VISION_PM (Sarah) | Capture vision | `vision.json` / `vision.md` |
| Requirements | REQUIREMENTS_PM (Sarah) | Build backlog | `Backlog.csv` + wireframes |
| Sprint Planning | SPRINT_PLANNING_ARCHITECT (Mike) | Define scope | Sprint plan JSON |
| Sprint Execution | SPRINT_EXECUTION_PM (Sarah) | Build & test | Working software |
| Sprint Review | SPRINT_REVIEW_PM (Sarah) + SPRINT_REVIEW_ALEX | Review & debug | Feedback, fixes |

---

## Section 5: Production Deployment (Railway)

### Current State: Mac to Railway Migration

AI-DIY was originally built to run locally on Mac. It is now being migrated to also run on Railway while maintaining Mac compatibility. This means:

**What works on both:**
- The main AI-DIY application (FastAPI backend, frontend)
- All meeting types and personas
- Sprint planning, execution, and review

**Key differences:**
- **Generated app execution**: On Mac, used shell scripts. On Railway, uses Python subprocess with cross-platform paths.
- **Volume persistence**: Railway uses a mounted volume at `/app/development/src/static/appdocs` - this is separate from local Mac files.
- **Authentication**: Railway requires HTTP Basic Auth; local Mac does not.

### Generated App Output Path

Generated apps are written to the **execution sandbox** at a fixed path on both platforms (folder is always `yourapp`, files accumulate across sprints):

| Environment | Generated app location |
|-------------|------------------------|
| Railway | `/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp/` (mounted volume) |
| Mac | `development/src/static/appdocs/execution-sandbox/client-projects/yourapp/` (local filesystem) |

**Single source of truth for names**

- `get_project_name_safe()` → returns the fixed folder name `yourapp` for all filesystem paths.
- `get_project_name()` → returns the human-facing project title from the Vision document; used only for UI/meeting display.

**Script/Test Path Resolver Standard**

- Python example:

```python
from pathlib import Path

def resolve_project_dir() -> Path:
    railway = Path("/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp")
    if railway.exists():
        return railway
    # Fallback to repo-relative path (adjust base as needed for the caller)
    return Path(__file__).resolve().parents[1] / "development" / "src" / "static" / "appdocs" / "execution-sandbox" / "client-projects" / "yourapp"
```

- Bash example:

```bash
APP_DIR="/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp"
if [ ! -d "$APP_DIR" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  LOCAL_DIR="$SCRIPT_DIR/../static/appdocs/execution-sandbox/client-projects/yourapp"
  APP_DIR="$LOCAL_DIR"
fi
```

**Do not:**

- Reference `project-sandbox` or `client projects` (with a space)
- Omit `static/appdocs` from the sandbox path
- Use dynamic/legacy folder names (must be `yourapp`)

**Other key data paths (same structure on both platforms):**

| Data Type | Relative Path |
|-----------|---------------|
| Visions | `static/appdocs/visions/` |
| Backlog | `static/appdocs/backlog/Backlog.csv` |
| Wireframes | `static/appdocs/backlog/wireframes/` |
| Sprint plans | `static/appdocs/sprints/` |
| Sprint backups | `static/appdocs/sprints/backups/` |
| Execution logs | `static/appdocs/sprints/execution_log_{sprint_id}.jsonl` |
| Mike breakdowns | `static/appdocs/sprints/mike_breakdowns/{sprint_id}/{story_id}.json` (7-day retention) |
| Scribe notes | `static/appdocs/scribe/` |
| Sessions | `static/appdocs/sessions/` |

> **TODO**: Add Mike breakdown capture mechanism to architecture documents. This diagnostic feature captures Mike's task breakdowns with all `files_to_create` arrays and contract summaries to debug architectural contract enforcement failures. Files auto-cleanup after 7 days.

**How generated apps are accessed:**
1. Start the app via `POST /api/control-app` with `{"action": "start"}`
2. Access the running app at `{BASE_URL}/yourapp/` (e.g., `/yourapp/login`, `/yourapp/api/users`)
3. AI-DIY proxies requests from `/yourapp/*` to the generated app running on port 3000

### Reverse Proxy Path Handling

Generated apps run behind a Caddy reverse proxy at `/yourapp/` on Railway. On Mac (local dev), apps are accessed directly at `http://localhost:3000/`. The same code works in both environments.

**How it works:**
- **Railway**: Caddy routes `/yourapp/*` → generated app on port 3000
- **Mac**: Direct access to `http://localhost:3000/` (no proxy)
- Generated apps use standard **absolute paths** with leading `/` for server-side routes (e.g., `router.get('/dashboard', ...)`)
- Generated apps use **relative paths without leading /** for client-side navigation (e.g., `href="dashboard"`)
**Nested URLs:** Apps can use nested URLs (e.g., `/employees/4/edit`). For cross-depth navigation (nested → parent), use server-side POST redirects, not client-side links.

**Architecture:**

Railway (Production):
```
Internet → Caddy (:$PORT/8000) → FastAPI (127.0.0.1:8001)
                              → Generated Apps (127.0.0.1:3000) via /yourapp/*
```

Mac (Local Dev):
```
localhost:8000 → FastAPI
localhost:3000 → Generated App (direct access, no proxy)
```

**Code patterns (standard Express):**

| Context | Pattern | Why |
|---------|---------|-----|
| Routes | `router.get('/login', ...)` | Absolute - Caddy strips prefix on Railway, works directly on Mac |
| Redirects | `res.redirect('/dashboard')` | Absolute - Caddy rewrites Location header on Railway |
| Form actions | `<form action="api/auth/login">` | **Relative** - no leading `/` |
| Links | `<a href="dashboard">` | **Relative** - no leading `/` |
| Fetch | `fetch('api/user')` | **Relative** - no leading `/` |

**IMPORTANT**: HTML paths (forms, links, fetch) must be **relative** (no leading `/`) so they resolve relative to the current URL. Server-side redirects use absolute paths because Caddy rewrites the `Location` header.

**Cross-Depth Navigation (Nested URLs):**

For navigation between different URL depths, use server-side redirects via POST endpoints:

```html
<!-- Cancel button in employees-edit.html -->
<form action="cancel-edit" method="POST" style="display:inline">
  <button type="submit">Cancel</button>
</form>
```

```javascript
// In server.js or routes file
router.post('/employees/:id/cancel-edit', (req, res) => {
  res.redirect('/employees');
});
```

❌ NEVER use `../` paths (href="../employees") - violates architecture
✅ Use POST endpoints that redirect with absolute server paths

**CRITICAL - DO NOT USE `<base>` TAG:**
```html
❌ <base href="/">           <!-- NEVER use this - breaks navigation on Railway -->
❌ <base href="/yourapp/">   <!-- NEVER use this - breaks navigation on Mac -->
✅ (no base tag)             <!-- Correct - relative paths work in both environments -->
```

**Why the `<base>` tag breaks navigation:**
- With `<base href="/">`: Forces all URLs to resolve from root
  - Railway: At `/yourapp/dashboard`, clicking `href="employees"` → `/employees` (404, should be `/yourapp/employees`)
  - Mac: At `/dashboard`, clicking `href="employees"` → `/employees` (works by accident)
- Without `<base>` tag: URLs resolve relative to current path
  - Railway: At `/yourapp/dashboard`, clicking `href="employees"` → `/yourapp/employees` ✅
  - Mac: At `/dashboard`, clicking `href="employees"` → `/employees` ✅

**Example - Correct navigation HTML:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dashboard</title>
    <!-- NO <base> tag -->
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <nav>
        <a href="dashboard">Dashboard</a>          <!-- Relative, no leading / -->
        <a href="employees">Employees</a>          <!-- Relative, no leading / -->
        <button onclick="logout()">Logout</button>
    </nav>
    <script>
        function logout() {
            fetch('api/auth/logout', { method: 'POST' })  // Relative, no leading /
                .then(res => res.json())
                .then(data => {
                    window.location.href = data.redirect;  // Server returns 'login' (relative)
                });
        }
    </script>
</body>
</html>
```

**Cross-platform requirements:**
- Use `process.env.PORT || 3000`
- Use `bcryptjs` (not `bcrypt` - requires native compilation)
- CommonJS module system (`require`/`module.exports`)
- Database sharing via `app.locals.db`

**When making changes:**
- Avoid Mac-specific paths or shell scripts
- Use `Path()` for cross-platform file paths
- Test that changes work in both environments
- Remember: Railway volume data and local Mac data can diverge

### Overview

The AI-DIY application is deployed to Railway at **https://ai-diy-dev-production.up.railway.app**. The deployment uses Docker containerization for consistency and portability.

### Authentication

The production site is protected with HTTP Basic Authentication to prevent unauthorized access and unexpected API charges. Access is controlled via the `BASIC_AUTH_USERS` environment variable in Railway (format: `username1:password1,username2:password2`). Current authorized users are documented separately.

### Key Railway Configuration Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container build instructions |
| `Caddyfile` | Caddy reverse proxy config - routes /yourapp/* to generated apps |
| `start.sh` | Startup script - launches FastAPI then Caddy |
| `railway.json` | Railway deployment settings (uses Dockerfile builder) |
| `development/src/auth_middleware.py` | HTTP Basic Auth implementation |

### Environment Variables

**Required in Railway:**
- `PRODUCTION=true` - Enables production mode and authentication
- `OPENROUTER_API_KEY` - API key for AI model access
- `BASIC_AUTH_USERS` - Comma-separated username:password pairs

**Optional (have sensible defaults):**
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `DATA_ROOT` - Data storage location (default: static/appdocs)
- `PORT` - Server port (Railway sets this automatically)

### Management

Use Railway MCP tools AND CLI for deployment management. The Claude Code environment has Railway MCP configured for direct project access.

**Railway MCP Tools (Use These):**
- `mcp__Railway__get-logs` - View deployment logs with optional `filter` parameter
- `mcp__Railway__list-deployments` - Check deployment status and history
- `mcp__Railway__deploy` - Trigger manual deployment when auto-deploy fails
- `mcp__Railway__list-services` - List services in the linked project

**Railway CLI for File Access (PREFERRED for volume operations):**
- ✅ `railway ssh <command>` - Run non-interactive commands on Railway container
- ❌ `railway ssh` (no args) - Interactive mode, requires TTY, doesn't work in Claude Code

**Local vs Railway Behavior:**
- **Local Mac**: No authentication required (PRODUCTION not set)
- **Railway**: HTTP Basic Auth required (PRODUCTION=true)
- Same codebase, different behavior based on environment variables

### CRITICAL: Accessing Railway Data (Not Local Mac)

When debugging Railway issues, you MUST access data FROM Railway, not local Mac files.

**PREFERRED: Use `railway ssh` with commands (non-interactive):**
```bash
# List files on Railway volume
railway ssh ls -la /app/development/src/static/appdocs/

# Read a file from Railway
railway ssh cat /app/development/src/static/appdocs/sprints/execution_log_SP-001.jsonl

# Write/edit files on Railway
railway ssh "echo 'content' > /app/path/to/file.txt"

# Run scripts on Railway
railway ssh python /app/development/src/some_script.py

# Check running processes
railway ssh ps aux
```

**Alternative: Authenticated curl (for files served by the app):**
```bash
curl -s -u "Ralph:!password321!" "https://ai-diy-dev-production.up.railway.app/static/appdocs/path/to/file.json"
```

**File Paths on Railway:**
- Railway container root: `/app/`
- Sprint logs: `/app/development/src/static/appdocs/sprints/`
- Generated app: `/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp/`
- Backlog: `/app/development/src/static/appdocs/backlog/Backlog.csv`
- Visions: `/app/development/src/static/appdocs/visions/`

**API Endpoints for Railway Data:**
- `GET /api/sprints` - List all sprints with execution summaries
- `GET /static/appdocs/sprints/execution_log_SP-XXX.jsonl` - Raw execution log
- `GET /api/sandbox/status` - Sandbox configuration

**Common Mistake:** Reading local files when Railway is the target environment. Local Mac has different sprint history than Railway. Always verify which environment you're debugging.

---

## Section 6: How to Use This Document

### Every Session Start
1. Read this document completely
2. Answer the quiz questions (prove comprehension)
3. Review the anti-patterns list
4. Keep the quick reference card open

### Before Every Change
1. Complete the Pre-Change Verification Checklist (Section 3)
2. Explain your intended change in plain English
3. State which pattern you're following (with file reference)
4. Wait for Ralph's approval
5. Implement using the existing pattern

### When Stuck
1. Check the Quick Reference Card (Section 4)
2. Search `PATTERNS_AND_METHODS.md` for the pattern
3. Look at `architecture.md` for the big picture
4. Review `system-flow.md` for meeting/persona behavior
5. Ask Ralph for clarification (don't guess)

---

## Section 6: Documentation Map

When you need detailed information, read these in order:

### Start Here (Required Reading)
1. **This document** (`LLM_ONBOARDING.md`) - You are here
2. **`summary.md`** - One-page working summary, mental map
3. **`DOCUMENTATION_INDEX.md`** - Map of all documentation

### For Specific Tasks
- **Adding API endpoint** → `PATTERNS_AND_METHODS.md` (Quick Starts) + `architecture.md` (API Architecture)
- **Modifying personas** → `summary.md` (Persona Configuration) + `system-flow.md` (Persona flows)
- **Working on meetings** → `system-flow.md` (Meeting Flow Details) + `myvision.md` (Meeting definitions)
- **Touching backlog/vision** → `dataflow-and-schema.md` (CSV schema) + `architecture.md` (Living Document pattern)
- **Sprint execution** → `system-flow.md` (Sprint Execution) + `PATTERNS_AND_METHODS.md` (Sprint Execution Method)
- **Making architectural changes** → `GOVERNANCE.md` + `ADRs.md` + `architecture.md`

### Full Documentation Set
- `README.md` - Entry point, quick start
- `summary.md` - Working summary for LLMs (START HERE)
- `myvision.md` - Product vision and goals
- `architecture.md` - System architecture and components
- `system-flow.md` - Meeting flows and persona behavior
- `dataflow-and-schema.md` - CSV schemas and data contracts
- `PATTERNS_AND_METHODS.md` - How to code here (patterns and examples)
- `GOVERNANCE.md` - Decision process and approval requirements
- `ADRs.md` - Architecture Decision Records
- `DOCUMENTATION_INDEX.md` - Index of all documentation

---

## Section 7: Red Flags (Stop and Ask)

If you encounter any of these situations, **STOP and ask Ralph**:

🚩 **You're about to create a new documentation file**  
→ Update existing docs instead (per GOVERNANCE.md)

🚩 **You can't find an existing pattern for what you need to do**  
→ Don't invent one, ask Ralph first

🚩 **The change contradicts an existing ADR**  
→ Propose a new ADR, don't silently reverse it

🚩 **You need to modify the Backlog CSV schema**  
→ Requires ADR approval and documentation update

🚩 **You're adding a new meeting type**  
→ Major architectural change, requires full governance process

🚩 **You're changing how personas are loaded or configured**  
→ Core system change, requires ADR and testing

🚩 **You're modifying the unified API response format**  
→ Breaking change, requires ADR and migration plan

🚩 **You're storing files outside `static/appdocs/`**  
→ Violates data management pattern, find another way

🚩 **You're adding default values or silent fallbacks**  
→ Violates fail-fast principle (ADR-001)

🚩 **You're not sure which pattern applies**  
→ Ask Ralph, don't guess

---

## Section 8: Success Criteria

You know you're doing it right when:

✅ You can answer all quiz questions without looking them up  
✅ You complete the verification checklist before every change  
✅ You cite specific file and line numbers when explaining your approach  
✅ You copy existing patterns instead of inventing new ones  
✅ You explain changes in plain English before implementing  
✅ You wait for Ralph's approval before proceeding  
✅ You update documentation as part of every change  
✅ You don't introduce any anti-patterns from Section 2  
✅ Ralph says "yes, that's exactly right" instead of "no, that's not how it works"  

---

## Appendix A: Common Session Patterns

### Pattern 1: "I need to add a new API endpoint"

**Correct Approach:**
1. Read `PATTERNS_AND_METHODS.md` - Quick Starts section
2. Identify: Copy `vision.py` or `backlog.py`
3. Explain: "I'll copy vision.py, change VISION_DIR to SPRINT_DIR, update request/response models, register in main.py"
4. Wait for approval
5. Implement following the 5-step pattern
6. Test with curl command

**Incorrect Approach:**
- ❌ "I'll create a custom endpoint with a new response format"
- ❌ Skipping the explanation and approval step
- ❌ Not registering the router in main.py
- ❌ Inventing a new pattern instead of copying

### Pattern 2: "I need to modify persona behavior"

**Correct Approach:**
1. Read `system-flow.md` - Persona Configuration section
2. Identify: Modify `system_prompts/personas_config.json` and/or `*_system_prompt.txt`
3. Explain: "I'll update VISION_PM's inject_context to add 'backlog' so Sarah can see requirements during vision meetings"
4. Wait for approval
5. Modify JSON config only (not Python)
6. Test the persona behavior

**Incorrect Approach:**
- ❌ Adding persona logic to Python code
- ❌ Creating a new persona file instead of using config
- ❌ Not understanding meeting_triggers and inject_context
- ❌ Forgetting `enabled: true`

### Pattern 3: "I need to fix a bug in sprint execution"

**Correct Approach:**
1. Read `system-flow.md` - Sprint Execution section
2. Read `PATTERNS_AND_METHODS.md` - Sprint Execution Method
3. Identify the specific phase (Mike/Alex/Jordan)
4. Explain: "The bug is in Mike's task breakdown - he's not zero-padding task IDs. I'll update the orchestrator validation to enforce T-{STORY}-{NN} format"
5. Wait for approval
6. Implement the fix
7. Update documentation if the fix changes behavior

**Incorrect Approach:**
- ❌ Guessing at the fix without reading the docs
- ❌ Changing the pattern instead of fixing the implementation
- ❌ Not explaining the root cause
- ❌ Skipping documentation updates

---

## Final Checklist: Am I Ready to Work?

Before you start ANY work on AI-DIY, verify:

- [ ] I have read this entire document
- [ ] I can answer all 10 quiz questions
- [ ] I understand the anti-patterns and why they're wrong
- [ ] I know where to find the documentation I need
- [ ] I will complete the verification checklist before every change
- [ ] I will explain changes and wait for approval
- [ ] I will copy existing patterns, not invent new ones
- [ ] I will update documentation as part of Definition of Done
- [ ] I understand that shortcuts cause rework
- [ ] I am committed to deep understanding, not surface-level implementation

**If you checked all boxes, you're ready. If not, read the docs again.**

---

## Remember

This system has a **complex, deliberate design**. Every pattern exists for a reason. Every rule prevents a specific problem. Every anti-pattern represents a mistake that has caused rework in the past.

**Your job is not to reinvent the system. Your job is to work within it.**

Read. Understand. Follow the patterns. Wait for approval. Implement correctly.

That's how we move forward without going backward.

---

**End of LLM Onboarding Document**

*For questions or clarifications, ask Ralph. For detailed patterns, see the documentation map in Section 6.*


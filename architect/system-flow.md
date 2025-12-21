# System Flow (Updated with Clarifications)

## Overview
The system flow describes how the AI-DIY application transitions from free-form chat to structured meeting workflows and how specialized personas coordinate across development stages.

This document consolidates how the app works in practice — the flows, persona logic, and integration points.

---

## 1. Persona Configuration and Core Characteristics

The personas configuration lives in `system_prompts/personas_config.json` plus a set of `*_system_prompt.txt` files in the `system_prompts/` folder. Together, these define both **base personas** and **meeting-specific specializations**. There are four base personas:

- **Sarah** – PM (Project Management)
- **Mike** – Architect
- **Alex** – Developer
- **Jordan** – QA

Each base persona can assume specialized roles depending on the meeting type.

### 1.1 Base vs Specialized Personas
The app models four base people  Sarah (PM), Mike (Architect), Alex (Developer), and Jordan (QA)  and derives multiple **specialized personas** from each base person.

Specialized personas differ by:
- **Meeting type** (Vision, Requirements, Sprint Planning, Sprint Execution, Sprint Review)
- **Role in that meeting** (facilitator, architect, developer, QA)
- **Tools and context** they receive (`tools`, `inject_context`, `meeting_triggers`, etc.)

All persona variants are defined **purely in configuration**:
- `system_prompts/personas_config.json`  persona metadata, tools, triggers, and wiring
- `system_prompts/*_system_prompt.txt`  per-persona prompt text

**Examples (not exhaustive):**

- **Sarah (PM)**
  - `PM`  general project manager for free-form chat
  - `VISION_PM`  leads Vision meetings; injects `vision` context
  - `REQUIREMENTS_PM`  leads Requirements/Backlog meetings; injects `vision` and `backlog`
  - `SPRINT_PLANNING_ARCHITECT` works with Sarah in Sprint Planning (Mike persona) to decompose work
  - `SPRINT_EXECUTION_PM` and `SPRINT_REVIEW_PM` coordinate sprint execution and review

- **Alex (Developer)**
  - `DEVELOPER`  base developer persona
  - `SPRINT_EXECUTION_DEVELOPER`  implements stories during Sprint Execution
  - `SPRINT_REVIEW_ALEX`  joins Sprint Review as a debugging/execution helper when that meeting runs

The **canonical persona list and configuration** is always the combination of `system_prompts/personas_config.json` plus the corresponding `system_prompts/*_system_prompt.txt` files. This document describes the pattern rather than enumerating every persona.

### 1.2 Selection Logic
- Only personas **activated in the conversation** (selected in UI) participate in the thread.
- Specialized personas respond when **their meeting role and name are called** or when a **consensus action** is requested.
- If no meeting is active, base personas default to free-form collaboration.

---

## 2. Free-form / Plan Chat vs Meeting Mode

The app operates in two modes:

### 2.1 Free-form Mode
- The user can chat with any subset of personas.
- No meeting orchestration or file writes occur.
- Context is conversational — ideal for planning, brainstorming, or design discussions.

### 2.2 Meeting Mode
- Triggered by phrases such as `start a vision meeting`, `start a backlog meeting`, etc.
- Specialized personas for that meeting type are loaded.
- Meeting lifecycle (start → participate → log → close) is orchestrated by the active PM persona.

---

## 3. Meeting Flow Details

Each meeting type follows the same general lifecycle, with specialized personas managing their phase.

### 3.1 Vision Meeting
- Initiated by Sarah (Vision_PM)
- Goal: Capture high-level objectives
- Outputs: Vision artifacts, priorities

### 3.2 Requirements / Backlog Meeting
- Managed by Requirements_PM
- Collaborates with Architect to validate stories and acceptance criteria
- Artifacts: Backlog CSV, structured story records

### 3.3 Sprint Planning Meeting
- Orchestrated by Planning_PM
- Architect (Mike) confirms design assumptions
- Dev (Alex) provides feasibility, QA (Jordan) reviews for testability

### 3.4 Sprint Execution Meeting
- Coordinated by Execution_PM
- Real-time progress tracked through **SSE streaming** (see below)
- Flow: Architect → Dev → QA → PM

### 3.5 Sprint Review Meeting
- Led by Review_PM
- Aggregates test and performance reports
- Produces summary outputs and logs for archival

---

## 4. Sprint Execution Operational Details

### 4.1 Live Status Streaming (SSE) with Concurrent Messaging
Sprint Execution uses **Server-Sent Events (SSE)** to provide real-time updates in the **main chat UI window**.
These messages reflect the persona handoff sequence (Mike → Alex → Jordan) and show progress, logs, and test outcomes as they occur.

**Concurrent Messaging**: Users can ask Sarah questions during sprint execution. Sarah's responses appear immediately in the chat alongside execution progress. Execution messages are styled with a purple accent to distinguish them from user messages and Sarah's responses.

This stream is distinct from the background **Progress tab** used for long-running tasks.
The chat SSE channel flushes messages after each step and remains open until Sprint Execution completes or encounters an error.

Reconnect and error-handling improvements are planned to ensure continuous delivery if the stream drops or stalls.

> ⚠ **Note:** Sprint Execution updates Backlog.csv at a per-story (row-scoped) level using `_update_backlog`: it reads the full CSV, validates headers, finds the matching `Story_ID`, updates only that row's execution fields, and rewrites the file. If the schema is corrupted or the story is missing, the update is skipped and logged. Safety for larger failures comes from the sprint-level snapshot of `Backlog.csv` taken before execution starts.

### 4.1.1 Tech Stack NFR Requirement

**Critical Requirement**: The first story in any sprint MUST be a Tech Stack NFR (NFR-001).

**Why This Matters**:
- Sprint orchestrator extracts tech stack from NFR-001 before processing other stories
- Tech stack determines project structure, test framework, and implementation patterns
- All other stories depend on tech stack being established

**Tech Stack NFR Content** (NFR-001):
- Title: "Local Mac Environment Setup" or similar
- Acceptance Criteria must specify:
  - Backend framework (Node.js Express, Flask, Django, etc.)
  - Frontend framework (React, Vue, Angular, etc.)
  - Database (SQLite, PostgreSQL, MySQL, etc.)
  - Testing framework (Jest, pytest, JUnit, etc.)
  - Ports and configuration details

**Example NFR-001 Acceptance Criteria**:
```
Run entirely locally on macOS (Ventura+)
Use SQLite as lightweight, file-based DB
Node.js v18+ backend with Express
React frontend on localhost (ports 3000 for frontend, 3001 for backend)
Include npm scripts: "start" and "stop"
Tests pass locally (e.g., Jest smoke test after start)
```

**Enforcement**:
- Sprint orchestrator validates: `if first_story_id != "NFR-001": raise error`
- If NFR-001 is missing or not first, sprint execution fails immediately
- Clear error message: "First story must be NFR-001 (Tech Stack NFR)"

---

### 4.1.2 Mike's 5-Phase Design Process (Architect Role)

**Input**: Story with Acceptance Criteria + Current Project State (database schema, API endpoints, file structure, code patterns)

**Mike's 5-Phase Design Process**:

#### PHASE 1: ANALYZE PROJECT STATE
Mike receives the current project state showing:
- Existing database schema (tables, fields, types)
- Existing API endpoints (methods, paths, response formats)
- Existing file structure (controllers, models, routes, components)
- Established code patterns (error handling, async/await, response format, etc.)

**Critical**: Mike must study this context carefully to:
1. Extend existing tables (don't recreate them)
2. Follow existing API patterns (same response format, error handling)
3. Reuse existing files and patterns (don't duplicate code)
4. Specify NEW vs. MODIFYING EXISTING for every element

#### PHASE 2: DESIGN THE SYSTEM
For each story, Mike must design:

1. **DATABASE SCHEMA**:
   - NEW tables: exact name, fields (name, type, constraints)
   - MODIFIED tables: which existing table, what new/changed fields
   - Example: "NEW table 'leave_requests' with fields: id (INTEGER PRIMARY KEY), employee_id (INTEGER), start_date (TEXT), end_date (TEXT), status (TEXT DEFAULT 'pending')"

2. **API ENDPOINTS**:
   - NEW endpoints: method (GET/POST/PUT/DELETE), path, request format, response format
   - MODIFIED endpoints: which endpoint, what changes
   - Example: "NEW endpoint: POST /api/leave with request {employee_id, start_date, end_date} returns {id, status}"

3. **FILE STRUCTURE**:
   - Which existing files will be modified?
   - What new files will be created?
   - Example: "Modify src/server/controllers/authController.js to add leave request logic"

4. **CODE PATTERNS**:
   - How does this follow established patterns?
   - Example: "Will use try/catch for errors like authController.js"
   - Example: "Will use async/await like existing routes"

5. **DEPENDENCIES** (CRITICAL FOR COMPLETENESS):
   - List ALL npm/pip packages required for this story
   - Include version numbers (e.g., "jsonwebtoken@^9.1.2", "bcrypt@^5.1.1")
   - Specify if regular dependency or devDependency
   - Example: "dependencies: {express: ^4.18.2, jsonwebtoken: ^9.1.2, bcrypt: ^5.1.1}"
   - **Why**: Alex uses this to update package.json. Missing dependencies cause runtime errors.

6. **SERVER TESTABILITY** (CRITICAL FOR HTTP APPS):
   - For NFR-001 or any HTTP server story, specify testability pattern
   - Server modules MUST export app object for testing
   - Pattern: `export const app = express(); if (import.meta.url === \`file://\${process.argv[1]}\`) { app.listen(port); }`
   - **Why**: Allows Jordan to import server without auto-start for testing
   - Document in architectural conventions so Alex exports app correctly

#### PHASE 3: BREAK DOWN INTO TASKS
Mike breaks the design into concrete, implementable tasks (3-10 based on complexity):
- Simple stories (1-2 screens, single layer): 3-4 tasks
- Medium stories (3-5 screens, 2 layers): 5-7 tasks
- Complex stories (multi-layer, infrastructure): 8-10 tasks

**Task ID Format** (CRITICAL):
- Format: `T-{STORY_ID}-{TASK_NUMBER}` (e.g., `T-NFR-001-01`, `T-US-009-02`)
- TASK_NUMBER must be zero-padded two digits (-01, -02, not -1, -2)
- NOT: `T001`, `TASK-004`, `T-NFR-001-1`

**For Each Task**:
- **task_id**: Formatted correctly (T-STORY-##)
- **description**: Clear, specific description of what the task does
- **files_to_create**: ALWAYS list concrete file paths (never empty)
  - Include file extension: "src/server.js" not "src/server"
  - Each task creates 1-3 files minimum
  - If task has 0 files, it's too abstract
- **command_to_run** (optional): Shell command to execute after files written
  - Node.js: `"npm install"` or `"npm ci"`
  - Python: `"pip install -r requirements.txt"`
  - Java: `"mvn install"`
  - Ruby: `"bundle install"`
  - **Why**: Stack-agnostic dependency installation
- **dependencies**: List task IDs that must complete first
- **dependency_reason**: Explain WHY (e.g., "depends on T-US-009-01 because database schema must exist first")

**Output**: JSON with all 5 design sections + tasks array

**Example Mike Output**:
```json
{
  "story_id": "US-009",
  "database_design": { "new_tables": [...], "modified_tables": [...] },
  "api_design": { "new_endpoints": [...], "modified_endpoints": [...] },
  "code_patterns": { "error_handling": "...", "async_pattern": "...", ... },
  "dependencies": { "dependencies": { "express": "^4.18.2", "jsonwebtoken": "^9.1.2" }, "devDependencies": { "jest": "^29.7.0" } },
  "tasks": [ { "task_id": "T-US-009-01", "description": "...", "files_to_create": [...], "dependencies": [], "dependency_reason": "..." }, ... ]
}
```

**Enforcement**:
- Sprint orchestrator validates task ID format
- Self-healing detects 0-file tasks and retries Mike
- Alex validates all dependencies in package.json before marking tasks complete
- Execution logs show task quality metrics (files per task, dependency reasons)

---

### 4.1.3 Jordan's Smoke Test Pattern (QA Role)

**Input**: Story with Acceptance Criteria, Mike's architectural conventions, Alex's task breakdown

**Jordan's Job**: Write 1-2 SMOKE TESTS ONLY (not comprehensive tests)

**Critical Rules**:
1. ✅ Write EXACTLY 1-2 tests per story - NO MORE
2. ✅ Smoke tests verify code runs without crashing
3. ❌ DO NOT write comprehensive tests
4. ❌ DO NOT test every acceptance criterion
5. ❌ DO NOT spawn child processes (spawn, exec, fork)
6. ❌ DO NOT parse log output to find ports
7. ✅ ALWAYS import modules directly
8. ✅ ALWAYS use native test utilities (app.listen(0), app.address().port)

**Smoke Test Patterns**:

**HTTP Server Apps**: Import server, start on random port, make ONE request, cleanup
```javascript
const { app } = await import('../src/server.js');
const server = app.listen(0);
const port = server.address().port;
// fetch, assert, server.close()
```

**Database Apps**: Import db, initialize, simple check, cleanup
```javascript
const { getDb, initDb } = await import('../src/db.js');
const db = getDb();
await initDb(db);
// simple query, assert, db.close()
```

**Combined (HTTP + DB)**: Setup db, start server, make request, cleanup both

**Output**: JSON with test_file path and test_content

**Enforcement**:
- Jordan's prompt enforces 1-2 test maximum
- Forbids spawn/exec/fork and log parsing
- Requires direct imports and native test utilities
- Tests run with appropriate framework (Node.js test runner, pytest, etc.)

---

### 4.2 End-to-End Flow (Trigger → Stream → Display)

- Trigger
  - User says: “start sprint 1” (or similar)
  - Sarah (SPRINT_EXECUTION_PM) calls `POST /api/sprints/{sprint_id}/execute`
  - Sarah announces: “Sprint execution started for SP-XXX”
  - Frontend opens the EventSource stream on that announcement

- Streaming
  - Endpoint: `GET /api/sprints/stream` (single global stream; events include `sprint_id` for filtering)
  - SSE emits default "message" events (no named `event:`); payload is JSON
  - SSE Manager buffers up to ~200 messages if the UI connects late

- Parsing and Display
  - Frontend listens on the default `message` event
  - Parser accepts both shapes:
    - Primary: `{ "event_type": "<name>", "data": { ... } }`
    - Fallback: `{ "type": "<name>", ... }` including `team_message` and `sprint_complete`
  - Displayed events (chat): `sprint_started`, `story_started`, `mike_breakdown`, `alex_implemented`, `jordan_tested`, `story_completed`, `sprint_completed|sprint_complete`
  - Hidden (noise): `backlog_updated` (still in logs)

- Pause / Resume
  - On user input during execution, the UI calls `POST /api/sprints/{id}/pause`
  - After Sarah replies, the UI calls `POST /api/sprints/{id}/resume` and re-opens the SSE
  - Buffered messages during the pause are delivered on reconnect (within the buffer limit)

- Completion
  - Story: “✅ Completed US-XXX”
  - Sprint: “✅ Sprint execution completed” when `sprint_completed` or `sprint_complete` arrives

---

## 5. Backlog Update and Safeguards

Backlog updates follow a multi-step process:

1. Validate the data (including CSV headers)
2. Backup existing CSV (via sprint snapshot before execution, plus API-level safety checks)
3. Write new data
4. Verify integrity
5. Rollback on failure (via sprint rollback restoring `Backlog.csv` from snapshot)

> ⚠ **Note:** Row-scoped updates are implemented in two layers: (1) Sprint Execution uses `_update_backlog` to update only the matching story's execution fields while rewriting the CSV, and (2) Sprint Review and planning flows use `/api/backlog/update-story` for row-level status/notes updates. Full-file writes remain for requirements-mode saves, which is why independent backlog versioning is still recommended.

---

## 6. Logging and Artifacts

The application records structured logs for all meetings and execution flows.

- Logs are stored under `/static/appdocs/` directories.
- JSONL format is used for append-only audit trails.

> ⚠ **Note:** Logging is configured via `core/logging_config` and, when available, `logging_middleware` as described in `architecture.md` (Logging Architecture) and `PATTERNS_AND_METHODS.md` (Logging Patterns). This section focuses on where artifacts live, not on logging configuration details.

---

## 7. Known Gaps

| Area | Status | Notes |
|------|---------|-------|
| Row-scoped backlog writes | ✅ Verified | Sprint Execution uses `_update_backlog` to update only the matching story's execution fields while rewriting the CSV; Sprint Review and planning use `/api/backlog/update-story` for row-level status/notes. Full-file writes remain for requirements-mode saves, so separate backlog versioning is still recommended. |
| JSONL logger initialization | ✅ Verified | Configured via `core/logging_config` and optional `logging_middleware` (see Logging Architecture in `architecture.md`) |
| Dev base role mapping | ✅ Verified | Base Dev and specializations (e.g., `DEVELOPER`, `SPRINT_EXECUTION_DEVELOPER`, `SPRINT_REVIEW_ALEX`) are defined in `system_prompts/personas_config.json` |

---

## 8. Summary

All critical process flows, persona activations, and meeting orchestration logic match the implemented system. Minor documentation clarifications (noted above) track where verification is still pending.

This document remains the authoritative system reference for architecture and behavior alignment.

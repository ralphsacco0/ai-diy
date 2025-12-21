# Architecture Decision Records (ADRs)

## Overview

This document contains Architecture Decision Records for significant decisions made during the AI-DIY implementation. Each ADR documents a decision, its rationale, and enforcement points.

## ADR Format

Each ADR follows this format:
- **Title**: Brief description of the decision
- **Status**: proposed | accepted | rejected | deprecated | superseded
- **Date**: When the decision was made
- **Rationale**: Why this decision was made
- **Implementation**: How the decision is implemented
- **Enforcement**: Where and how the decision is enforced
- **Related ADRs**: Links to related decisions

---

## Phase 1-6 Implementation ADRs

### ADR-001: Fail-Fast Configuration Architecture

**Status**: Accepted and Implemented
**Date**: 2025-10-07
**Supersedes**: Previous default-based configuration approaches

**Rationale**:
- Previous implementations used silent fallbacks and defaults, leading to unpredictable behavior
- User feedback emphasized the need for explicit configuration and immediate failure on missing setup
- Fail-fast approach prevents silent failures and ensures system integrity

**Implementation**:
- `config_manager.py` (when present) implements startup validation that fails immediately on missing configuration, enabled dynamically by `main.py`
- In deployments where `config_manager` is enabled, configuration must be explicitly provided (no silent fallbacks)
- Clear error messages guide users to fix configuration issues

**Enforcement**:
- `validate_startup_configuration()` is called from `main.py` before application startup when `config_manager` is available
- Configuration loading functions fail fast with descriptive errors when managed by `config_manager`
- Environment variables such as `LOG_LEVEL` must be explicitly set for consistent behavior

**Related ADRs**:
- ADR-002 (Unified API Response Format)
- ADR-003 (Structured Logging)

---

### ADR-002: Unified API Response Format

**Status**: Accepted and Implemented
**Date**: 2025-10-07

**Rationale**:
- Previous API endpoints had inconsistent response formats
- Need for machine-readable error codes for programmatic handling
- User requirement for predictable API behavior across all endpoints

**Implementation**:
- All API endpoints return `{"success": true|false, "message": "string", "data": {...}}`
- Error responses include machine-readable `error_code` in data field
- Standard actions (save, get, list, delete, latest) supported across all endpoints

**Enforcement**:
- `api/conventions.py` defines Pydantic models for response formats
- All API endpoints use `create_success_response()` and `create_error_response()`
- Test suite validates response format consistency

**Related ADRs**:
- ADR-001 (Fail-Fast Configuration)
- ADR-004 (Comprehensive Security)

---

### ADR-003: Structured JSON-Line Logging

**Status**: Accepted and Implemented
**Date**: 2025-10-07

**Rationale**:
- Need for operational visibility and security monitoring
- Previous logging was inconsistent and not machine-readable
- Production deployment requires structured logs for analysis

**Implementation**:
- When `logging_middleware.py` is available and enabled by `main.py`, API calls are logged in JSON-line format with required fields
- FastAPI middleware captures request metadata automatically when enabled
- Separate security logger for audit trails

**Enforcement**:
- `logging_middleware.py` implements structured logging middleware that can be dynamically attached in `main.py`
- API endpoints are logged with complete context when the logging middleware is enabled
- Log format: `{"ts": "ISO", "route": "/path", "action": "save", "id": "id", "status": "success", "duration_ms": 150}`

**Related ADRs**:
- ADR-001 (Fail-Fast Configuration)
- ADR-004 (Comprehensive Security)

---

### ADR-004: Comprehensive Security Architecture

**Status**: Accepted and Implemented
**Date**: 2025-10-07

**Rationale**:
- Production deployment requires enterprise-grade security
- Multiple layers of protection needed against common attack vectors
- User feedback emphasized security as critical requirement

**Implementation**:
- Multi-layer security: rate limiting, input validation, path protection, application security, operational security
- FastAPI middleware for security headers and request validation when `security_middleware.py` is enabled by `main.py`
- File operation security with path allowlist and extension validation (e.g., in `api/sandbox.py`)

**Enforcement**:
- `security_middleware.py` implements comprehensive security middleware that can be dynamically attached in `main.py`
- `security_utils.py` provides security utilities and validation functions
- File operations interacting with the sandbox are validated against security constraints

**Related ADRs**:
- ADR-002 (Unified API Response Format)
- ADR-005 (Overwrite-on-Save Data Management)

---

### ADR-012: Default SSE “message” Listening and Tolerant Event Parsing for Sprint Narration

**Status**: Accepted and Implemented  
**Date**: 2025-11-14  
**Related**: ADR-008 (Sequential Orchestrator MVP)

**Context**:
- Sprint execution narration was not reliably visible in the chat because the frontend listened for named SSE events (e.g., `update`), while the backend streamed JSON-only lines without an `event:` field (default "message").
- Event shapes vary slightly across emitters: primary `{event_type, data}`; fallback `{type, persona, message}`; completion variants `sprint_completed` vs `sprint_complete`.

**Decision**:
- Frontend listens on the default SSE `message` event for `/api/sprints/stream` (global endpoint) and filters events client-side by `sprint_id` in the payload.
- Frontend parser is tolerant:
  - Accepts `event_type` OR `type`.
  - Supports `type: team_message` with `persona` and `message`.
  - Recognizes `sprint_completed` and `sprint_complete` as equivalent completion signals.
  - For Alex, uses `files_written` when `files_count` is absent.
  - For Mike, shows `task_count` when `summary` is absent.
- UI opens the stream after Sarah announces “Sprint execution started for SP-XXX” (no regex dependency beyond this minimal phrase).

**Rationale**:
- Aligns frontend with backend SSE format (default `message`).
- Removes fragile dependency on strict LLM output formatting.
- Increases robustness to small schema differences without backend churn.

**Implementation**:
- Frontend (`development/src/static/index.html`):
  - EventSource listens on default `message`.
  - Parser updated to accept both event shapes and completion variants; displays Mike/Alex/Jordan/system reliably.
  - Opens SSE on Sarah’s start announcement; supports pause/resume behavior.

**Enforcement/References**:
- API: `development/src/api/sprint.py` streams default `message` events.
- SSE Manager: `development/src/services/sse_manager.py` buffers per sprint and emits completion close signal.
- Docs updated: `architect/architecture.md`, `architect/system-flow.md`, `architect/dataflow-and-schema.md`, `architect/PATTERNS_AND_METHODS.md`.

---

### ADR-005: Overwrite-on-Save Data Management

**Status**: Accepted and Implemented
**Date**: 2025-10-07

**Rationale**:
- Need for predictable file management behavior
- Previous systems had inconsistent create vs update behavior
- Clear operation feedback required for user experience

**Implementation**:
- Save operations create when ID absent, overwrite when ID present
- Return `is_overwrite` flag in response for clear operation tracking
- Preserve creation metadata while updating modification time

**Enforcement**:
- `data_manager.py` implements overwrite-on-save logic for visions and backlog CSVs via `validate_and_save_vision()` and `validate_and_save_backlog_csv()`
- Backlog and vision APIs (`api/backlog.py`, `api/vision.py`) follow overwrite-on-save semantics when persisting data
- Test suite validates create vs overwrite behavior

**Related ADRs**:
- ADR-004 (Comprehensive Security)
- ADR-006 (CSV Schema Validation)

---

### ADR-006: CSV Schema Validation

**Status**: Accepted and Implemented
**Date**: 2025-10-07

**Rationale**:
- Backlog data integrity requires strict schema enforcement
- Previous CSV handling was inconsistent and error-prone
- Need for canonical schema definition and validation

**Implementation**:
- Canonical headers defined in `CsvConfig.CANONICAL_HEADERS`
- Strict validation against schema with clear error messages
- Column count validation ensures data integrity

**Enforcement**:
- `validate_csv_headers()` in `api/conventions.py` enforces the canonical schema
- CSV operations in `data_manager.py` and `api/backlog.py` validate against canonical headers
- 400 errors returned for schema violations in API paths that accept CSV input

**Related ADRs**:
- ADR-005 (Overwrite-on-Save Data Management)
- ADR-007 (Environment Standards)

---

### ADR-007: Environment Standards

**Status**: Accepted and Implemented
**Date**: 2025-10-07

**Rationale**:
- Clear separation needed between development and production
- Previous deployments had inconsistent environment handling
- Production requires stricter security and validation

**Implementation**:
- `PRODUCTION` environment variable controls behavior
- Development: debug logging, relaxed CORS, local file storage
- Production: security headers, strict validation, secure file storage

**Enforcement**:
- `main_secure.py` implements production-ready configuration
- Environment-specific middleware and security settings
- Configuration templates for both environments

---

## Legacy ADR References

### ADR-002 (Legacy): No Personas in Code
**Status**: Accepted (superseded by enhanced implementation)
**Original Date**: 2025-09-17

**Current Status**:
- Enhanced with security integration and structured logging
- Persona context included in security audit logs
- Input validation applied to all persona operations

### ADR-003 (Legacy): Requirements Workflow
**Status**: Accepted (superseded by enhanced implementation)
**Original Date**: 2025-10-06

**Current Status**:
- Enhanced with CSV schema validation and security scanning
- Wireframe generation includes malicious content detection
- File operations validated against security constraints

### ADR-004 (Legacy): Vision Workflow
**Status**: Accepted (superseded by enhanced implementation)
**Original Date**: 2025-09-17

**Current Status**:
- Enhanced with overwrite-on-save behavior and security validation
- File operations include path traversal protection
- Input validation and sanitization applied to all vision data

---

## Decision Making Process

### When to Create an ADR

ADRs are created for decisions that:
- **Change system behavior** in significant ways
- **Affect multiple components** or phases
- **Have security implications**
- **Impact operational procedures**
- **Change API contracts** or user interfaces

### ADR Review Process

1. **Draft ADR** for significant decisions before implementation
2. **Review with stakeholders** for feedback and validation
3. **Update implementation** based on ADR decisions
4. **Mark as Accepted** when implementation complete
5. **Archive superseded** ADRs when replaced by better decisions

### ADR Maintenance

- **Regular review** of active ADRs during planning sessions
- **Update status** as decisions evolve or are superseded
- **Link related ADRs** to show decision relationships
- **Archive obsolete** ADRs when no longer relevant

---

## Current ADR Status Summary

| ADR | Title | Status | Implementation |
|-----|-------|--------|----------------|
| ADR-001 | Fail-Fast Configuration | ✅ Accepted | `config_manager.py` |
| ADR-002 | Unified API Response | ✅ Accepted | `api/conventions.py` |
| ADR-003 | Structured Logging | ✅ Accepted | `logging_middleware.py` |
| ADR-004 | Security Architecture | ✅ Accepted | `security_middleware.py` |
| ADR-005 | Overwrite-on-Save | ✅ Accepted | `data_manager.py`, `api/backlog.py`, `api/vision.py` |
| ADR-006 | CSV Schema Validation | ✅ Accepted | `api/conventions.py`, `data_manager.py`, `api/backlog.py` |
| ADR-007 | Environment Standards | ✅ Accepted | `main_secure.py` |
| ADR-011 | Project Name Single Source of Truth | ✅ Accepted | `core/project_metadata.py` |
| ADR-012 | Default SSE "message" Listening | ✅ Accepted | `api/sprint.py`, `index.html` |
| ADR-013 | Tech Stack Inference from NFRs | ✅ Accepted | `system_prompts/personas_config.json`, `sprint_orchestrator.py` |
| ADR-014 | Task Breakdown Quality Standards | ✅ Accepted | `system_prompts/personas_config.json`, `sprint_orchestrator.py` |
| ADR-016 | Externalized Persona Prompts and Cached Loader | ✅ Accepted | `system_prompts/personas_config.json`, `services/ai_gateway.py` |
| ADR-017 | Orchestrator Reliability Fixes | ✅ Accepted | `system_prompts/*_system_prompt.txt`, `sprint_orchestrator.py` |

**Total ADRs**: 13 (13 accepted, 1 proposed, 0 rejected)

---

## Proposed ADRs

### ADR-008: Adopt Sprint Execution v4 with Sequential Orchestrator (MVP)

**Status**: proposed
**Date**: 2025-10-29
**Related ADRs**: ADR-001 (Fail-Fast Configuration), ADR-002 (Unified API Response), ADR-005 (Overwrite-on-Save), ADR-006 (CSV Schema Validation), ADR-009 (Guardrails: OpenAPI + AC→Tests)

**Rationale**:
- Aligns with myvision.md: turn natural conversation into tested, deployable software
- Minimizes risk and complexity by executing sprint tasks sequentially (no concurrency)
- Preserves strict separation between platform artifacts and generated app code
- Builds on existing patterns: meeting framework, unified response envelopes, file-based storage

**Implementation (MVP Scope)**:
- Sprint Planning: Persist sprint plans via `/api/sprints/save` following `vision.py` pattern; files under `static/appdocs/sprints/`
- Orchestrator (sequential): `services/sprint_orchestrator.py` coordinates execution-mode personas in order (Mike → Alex → Jordan), updates Backlog.csv statuses, writes `execution_log_{sprint_id}.json`
- Execution-Mode Personas: Config-only, respond ONLY to orchestrator during execution
- Progress Visibility: Minimal global SSE endpoint `/api/sprints/stream` emitting recent events (including `sprint_id`); simple UI view wired to existing Progress button
- Meetings: Sprint Review and Retrospective as config-driven personas (no new routing logic)
- Tests: Start from generated stubs; evolve to runnable assertions within MVP

**Enforcement (Planned Points)**:
- API router: `development/src/api/sprints.py` (unified envelope, standard actions)
- Orchestrator service: `development/src/services/sprint_orchestrator.py`
- Storage locations: `static/appdocs/sprints/*` (plans/logs), `execution-sandbox/client-projects/{ProjectName}` (generated code)
- Persona configs: `system_prompts/personas_config.json` entries (plus `system_prompts/*_system_prompt.txt`) for execution-mode personas

---

### ADR-011: Sprint Execution Robustness Fixes (Session 2)

**Status**: Accepted and Implemented
**Date**: 2025-11-12
**Related ADRs**: ADR-008 (Sequential Orchestrator MVP)

**Context**:
After initial Sprint Execution testing, identified critical issues with message display, token limits, and validation:
1. SSE messages not appearing in UI (text parsing fragile and regex-dependent)
2. Mike's JSON responses truncated mid-response (token limits too low for large breakdowns)
3. Mike's validation failing (camelCase vs snake_case field name mismatch)
4. Sprint messages not user-friendly (plain text with no persona context)

**Decision**:
Implement four targeted fixes to improve robustness and user experience:

1. **Structured Event Architecture**: Backend emits `sprint_execution_started` event immediately when `/api/sprints/{sprint_id}/execute` is called. Frontend listens for structured event instead of parsing Sarah's message text. No dependency on message format.

2. **Increased Token Limits**: Execution personas (Mike, Alex, Jordan) get 20,000 tokens (vs 12,000 for other personas). Execution personas need room for large JSON outputs with multiple tasks and detailed breakdowns.

3. **Flexible Field Normalization**: Accept `"taskId"` (camelCase), `"id"` (shorthand), or `"task_id"` (snake_case) in Mike's breakdown. Normalize all variants to `"task_id"` before validation. Same for `"title"` → `"description"`.

4. **Action-Focused Message Formatting**: Messages show as `[Persona · Role]: [Action] [Details]` format. Example: "Mike · ARCHITECT: Breaking down US-001: analyzing requirements". Black text headers (no background bar) to match Sarah's style.

**Implementation**:
- `/development/src/api/sprint.py` (lines 27-28, 374-381) - Import SSE manager, emit `sprint_execution_started` event
- `/development/src/static/index.html` (lines 1268-1277, 2945) - Add event listener for `sprint_execution_started`, open SSE stream
- `/development/src/services/ai_gateway.py` (lines 299-308) - Dynamic token allocation: 20,000 for execution personas, 12,000 for others
- `/development/src/services/sprint_orchestrator.py` (lines 228-236) - Field normalization in `_validate_task_breakdown()`
- `/development/src/static/index.html` (lines 1215-1249, 1251-1270, 1295) - Message formatting with persona and action

**Consequences**:
- ✅ Messages reliably flow to UI in real-time (no regex dependency)
- ✅ Larger task breakdowns complete without truncation
- ✅ Mike's breakdowns validate correctly regardless of field naming
- ✅ Sprint execution messages are clear, concise, and properly formatted
- ✅ Zero breaking changes (backward compatible)

**Status**: Complete and tested (2025-11-12)

---

### ADR-009: Guardrails (Phased) — OpenAPI Contract and AC→Tests Bridge

**Status**: proposed
**Date**: 2025-10-29
**Related ADRs**: ADR-002 (Unified API Response), ADR-008 (Sequential Orchestrator MVP), ADR-011 (Robustness Fixes)

**Rationale**:
- Prevent drift between implementation and documentation (contract-first)
- Ensure traceability from acceptance criteria to tests (quality gate)
- Avoid early over-constraint: adopt in phases to keep MVP delivery moving

**Implementation (Phased)**:
- Phase A (MVP): Add `development/src/api/openapi.yml` as reference contract for sprint endpoints; no runtime validation yet
- Phase B: Introduce generated server/client stubs and contract tests post-MVP hardening
- AC→Tests: Add `development/src/services/ac_test_generator.py` to produce test stubs from Backlog acceptance criteria; Jordan upgrades stubs to runnable tests within MVP

**Enforcement (Planned Points)**:
- Contracts: `openapi.yml` maintained alongside API changes; referenced in ADRs and docs
- Test Generation: Orchestrator calls AC→Tests generator at story start and logs `tests_generated` events
- CI (post-MVP): Add contract tests to ensure API responses conform

---

### ADR-011: Project Name Single Source of Truth

**Status**: Accepted and Implemented
**Date**: 2025-11-08
**Related ADRs**: ADR-002 (Unified API Response), ADR-005 (Overwrite-on-Save)

**Problem**:
- Multiple code paths resolved project name independently (streaming.py, sprint_orchestrator.py, api/sprint.py)
- Led to inconsistency: different meetings/components showed different project names
- No central authority for "current approved project name"
- Difficult to maintain and test

**Decision**:
- Create single unified `get_project_name()` function in `core/project_metadata.py`
- Implement vision approval safeguard: only one approved vision at a time
- Create `project_metadata.json` as single source of truth when vision approved
- All components import and use `get_project_name()` or `get_project_name_safe()`

**Rationale**:
- Consistency: All meetings, sprint execution, and APIs use same project name
- Single source of truth: `project_metadata.json` is authoritative
- Maintainability: One code path to test and maintain
- Graceful degradation: Fallback chain (metadata → approved vision → "Unknown")
- Vision integrity: Safeguard ensures only one approved vision exists

**Implementation**:
- `core/project_metadata.py` module with two functions:
  - `get_project_name()` - Returns display name (e.g., "BrightHR Lite Vision")
  - `get_project_name_safe()` - Returns safe path name (e.g., "BrightHR_Lite_Vision")
- Priority chain:
  1. Read `project_metadata.json` (fastest, most current)
  2. Fall back to latest approved vision title
  3. Fall back to "Unknown"
- Vision approval safeguard in `api/vision.py`:
  - When vision approved, automatically unapprove any previously approved vision
  - Create/update `project_metadata.json` with new approved vision ID and name
  - Log all transitions for audit trail

**Enforcement**:
- All meetings use `get_project_name()` for announcements (except VISION_PM which uses inline extraction)
- Sprint execution uses `get_project_name_safe()` for directory creation
- Sprint list API uses `get_project_name()` for current project name
- Code review: Reject any new project name resolution code outside `core/project_metadata.py`
- Tests: Unit tests for fallback chain, integration tests for vision approval safeguard

**Files Changed**:
- `core/project_metadata.py` (NEW)
- `streaming.py` (import from core, removed duplicate)
- `api/vision.py` (added safeguard and metadata creation)
- `api/sprint.py` (import from core)
- `services/sprint_orchestrator.py` (import from core, removed method)

**Related ADRs**:
- ADR-002 (Unified API Response Format)
- ADR-005 (Overwrite-on-Save Data Management)

---

## Future ADR Considerations

---

## Sprint Review & Session Management ADRs

### ADR-010: Natural Sprint Review Collaboration

**Status**: Accepted and Implemented
**Date**: 2025-11-08

**Rationale**:
- Previous Sprint Review was rigid and mechanical (demo → test → approve cycle)
- User feedback: "I want it to act like I am talking to you (Cascade)"
- Limited debugging capabilities prevented effective issue resolution
- Chat history limits (9-10 turns) killed long debugging sessions
- No dynamic code exploration or command execution

**Implementation**:
Three-phase approach:

**Phase 1 - Persona Updates**:
- SPRINT_REVIEW_PM: Conversational facilitator (not prescriptive)
- DEBUG_ALEX → SPRINT_REVIEW_ALEX: Natural code expert (always available)
- Added tools: `list_directory`, `run_command`
- Config: `system_prompts/personas_config.json` + corresponding `system_prompts/*_system_prompt.txt` entries for sprint review personas

**Phase 2 - Sandbox Command Execution**:
- New API: `/api/sandbox` with list-directory and execute endpoints
- Security: Command allowlist, path validation, timeout enforcement
- Tool handlers in streaming.py (lines 705-784)
- Tool definitions in ai_gateway.py (lines 193-251)

**Phase 3 - Session Management**:
- New API: `/api/session` for summarization and context retrieval
- Generic design: Works for all meeting types and regular chat
- Automatic context injection in streaming.py (lines 377-438)
- Storage: `/static/appdocs/sessions/`

  **Enforcement**:
  - Persona behavior defined in `system_prompts/personas_config.json` + `system_prompts/*_system_prompt.txt`
  - Sandbox security enforced in `api/sandbox.py`
  - Session context automatically injected in `streaming.py`
  - Tool availability documented in persona config; runtime enforcement is not applied today (enhancement candidate)

**Benefits**:
- Natural collaboration (feels like real development team)
- Full code access (explore, run commands, debug)
- Extended conversations (overcome chat history limits)
- Scope control (clear boundaries maintained)
- Debugging power (iterative fixing without rigid gates)

**Related ADRs**:
- ADR-007 (Meeting Simplification)
- ADR-008 (Persona Role Mapping)

**Documentation**:
 - `architect/archive/SPRINT_REVIEW_REDESIGN.md` - Complete implementation guide

---

### ADR-011: Generic Session Management Architecture

**Status**: Accepted and Implemented
**Date**: 2025-11-08

**Rationale**:
- Chat history limits (9-10 turns) prevent deep work in all meeting types
- Context loss causes repetition and confusion
- Need applies to Vision, Requirements, Sprint Planning, Sprint Review, and regular chat
- Solution must be generic and reusable across all conversation types

**Implementation**:
**Generic Session API** (`/api/session`):
- `POST /summarize` - Create/update session summary
- `POST /get-context` - Retrieve session context
- `GET /list` - List active sessions
- `DELETE /clear/{type}/{id}` - Clear session
- `GET /status` - Get status

**Session Types**:
- `vision_meeting`
- `requirements_meeting`
- `sprint_planning`
- `sprint_review`
- `sprint_execution`
- `chat` (regular conversations)

**Automatic Detection**:
- Session type derived from meeting persona
- Session ID combines project name + session type
- No manual configuration required

**Context Structure**:
```json
{
  "key_points": ["..."],
  "decisions": ["..."],
  "pending_items": ["..."],
  "context": {}
}
```

**Enforcement**:
- Session detection in `streaming.py` (lines 377-438)
- Context injected automatically on every turn
- Storage in `/static/appdocs/sessions/`
- File naming: `{session_type}_{session_id}_session.json`

**Benefits**:
- Overcomes chat history limits everywhere
- Maintains context across long sessions
- Generic design (no meeting-specific logic)
- Persistent (survives across days)
- Automatic (no user intervention)

**Future Enhancement**:
Auto-trigger summarization every 5-7 turns (currently manual via API)

**Related ADRs**:
- ADR-010 (Sprint Review Redesign)

---

---

### ADR-013: Mike's Prompt Design - Tech Stack Inference from NFRs

**Status**: Accepted and Implemented
**Date**: 2025-11-15
**Related ADRs**: ADR-008 (Sequential Orchestrator MVP), ADR-011 (Robustness Fixes)

**Problem**:
- Mike's prompt received hardcoded tech stack parameter (e.g., `Tech Stack: Node.js/React`)
- This approach is project-specific and not reusable for different tech stacks (Oracle, Python, Go, etc.)
- Hardcoding violates the principle of treating Mike like a real architect who reads requirements

**Decision**:
Mike should infer tech stack from acceptance criteria and story context, not receive it as a hardcoded parameter.

**Rationale**:
- **Reusability**: Works for any tech stack without code changes
- **Realistic**: Mike reads what he needs to know, like a real architect
- **Flexibility**: Tech stack can change mid-project without updating Mike's prompt
- **Self-contained**: All information is in the story/criteria, not hardcoded

**Implementation**:
- `system_prompts/personas_config.json`: Mike's system_prompt (in external prompt file) includes "Infer the tech stack from the acceptance criteria and story context"
- `sprint_orchestrator.py` line 1181: Removed `Tech Stack: {tech_stack}` parameter from Mike's prompt
- NFR-001 (Tech Stack NFR) is enforced as first story, containing all tech stack details
- Mike receives full Acceptance Criteria which mentions tech stack details (Node.js, Express, React, SQLite, Jest, etc.)

**Enforcement**:
- Sprint orchestrator validates that NFR-001 is first story (contains tech stack)
- Mike's system prompt requires tech stack inference from criteria
- No hardcoded tech stack passed to Mike in the prompt
- Tech stack variable still used internally for project structure creation

**Consequences**:
- ✅ System works for any tech stack
- ✅ Mike acts like a real architect (reads, infers, decides)
- ✅ No code changes needed when tech stack changes
- ✅ Acceptance criteria is single source of truth

**Related ADRs**:
- ADR-011 (Project Name Single Source of Truth) - Similar principle of single source of truth

---

### ADR-014: Task Breakdown Quality Standards

**Status**: Accepted and Implemented
**Date**: 2025-11-15
**Related ADRs**: ADR-008 (Sequential Orchestrator MVP), ADR-011 (Robustness Fixes)

**Problem**:
- Previous task breakdowns had tasks with 0 files (too abstract)
- Tasks like "Configure backend" or "Initialize project" didn't specify concrete files
- Alex couldn't implement abstract tasks, leading to incomplete implementations
- Dependencies were listed but not explained, making it hard to understand constraints

**Decision**:
Enforce concrete, implementable task standards with clear dependencies and file specifications.

**Rationale**:
- **Concrete**: Each task must create 1-3 files (never 0)
- **Implementable**: Alex can read task description and files_to_create and implement
- **Clear Dependencies**: Explain WHY each dependency exists
- **Traceable**: Task IDs must follow strict format for logging and tracking

**Implementation**:
- `system_prompts/personas_config.json`: Mike's system_prompt requires:
  1. `files_to_create` never empty (1-3 files per task minimum)
  2. Include file extension (e.g., "src/server.js", not "src/server")
  3. `dependency_reason` field explaining WHY each dependency exists
  4. Task ID format: `T-{STORY_ID}-{TASK_NUMBER}` with zero-padded numbers (-01, -02, not -1, -2)
  5. Example in prompt shows concrete files and dependency reasons

**Enforcement**:
- Mike's system prompt validates these rules
- Sprint orchestrator logs task quality metrics (files per task, dependency reasons)
- Self-healing detects incomplete breakdowns (0-file tasks) and retries Mike
- Execution logs show task descriptions and file counts for visibility

**Consequences**:
- ✅ No more 0-file tasks
- ✅ Alex receives concrete, implementable tasks
- ✅ Dependencies are clear and explained
- ✅ Task IDs are consistent and traceable
- ✅ Execution logs show quality metrics

**Related ADRs**:
- ADR-011 (Robustness Fixes) - Self-healing catches incomplete breakdowns

---

### ADR-015: Mike's 5-Phase Design Process with Dependencies

**Status**: Accepted and Implemented
**Date**: 2025-11-15
**Related ADRs**: ADR-008 (Sequential Orchestrator MVP), ADR-014 (Task Breakdown Quality Standards)

**Problem**:
- Alex was generating code that required npm packages (jsonwebtoken, bcrypt) that weren't in package.json
- Runtime errors: `MODULE_NOT_FOUND` prevented apps from starting
- Mike was only outputting task breakdowns without design specifications
- Alex lacked context about database schema, API endpoints, file structure, and code patterns
- Incremental development was impossible - Alex couldn't extend existing code without seeing it

**Decision**:
Mike (Architect) must output a complete 5-phase design specification before Alex implements:
1. **Analyze Project State** - Study existing database, APIs, files, patterns
2. **Design the System** - Database schema, API endpoints, file structure, code patterns, **dependencies**
3. **Break Down into Tasks** - Concrete, implementable tasks with clear dependencies

**Rationale**:
- **Prevents Missing Dependencies**: Mike explicitly lists all npm/pip packages with versions
- **Enables Incremental Design**: Mike sees what's already built and extends it
- **Prevents Duplicate Code**: Mike specifies NEW vs. MODIFYING for every element
- **Prevents Schema Conflicts**: Mike designs schema changes, not recreations
- **Complete Context for Alex**: Alex knows exactly what to implement and what dependencies to add
- **Reduces Rework**: Clear design prevents incomplete implementations

**Implementation**:
- `system_prompts/personas_config.json`: Mike's system_prompt includes 5-phase design process
- Mike outputs JSON with 5 sections:
  ```json
  {
    "database_design": { "new_tables": [...], "modified_tables": [...] },
    "api_design": { "new_endpoints": [...], "modified_endpoints": [...] },
    "code_patterns": { "error_handling": "...", "async_pattern": "...", ... },
    "dependencies": { "dependencies": {...}, "devDependencies": {...} },
    "tasks": [...]
  }
  ```
- `sprint_orchestrator.py`: Extracts project state (database schema, API endpoints, file structure, code patterns) before calling Mike
- Mike receives current project state in user message before story details

**Enforcement**:
- Sprint orchestrator validates Mike's output includes all 5 sections
- Alex validates all dependencies are in package.json before marking tasks complete
- Self-healing detects missing dependencies and retries Mike
- Execution logs show design quality metrics (dependencies listed, schema changes specified, etc.)

**Consequences**:
- ✅ No more missing dependencies causing runtime errors
- ✅ Incremental development works correctly (extending existing code)
- ✅ Schema conflicts prevented (NEW vs. MODIFYING specified)
- ✅ Alex has complete context for implementation
- ✅ Code quality improved (follows established patterns)
- ✅ Apps run on first try (all dependencies included)

**Related ADRs**:
- ADR-008 (Sequential Orchestrator MVP) - Foundation for Mike→Alex→Jordan flow
- ADR-014 (Task Breakdown Quality Standards) - Tasks are concrete and implementable

---

### ADR-016: Externalized Persona Prompts and Cached Loader

**Status**: Accepted and Implemented  
**Date**: 2025-11-16  
**Related ADRs**: ADR-001 (Fail-Fast Configuration Architecture), ADR-002 (Unified API Response), ADR-010 (Sprint Review Redesign)

**Rationale**:
- Persona system prompts stored inline in a single JSON file (`config_personas.json`) were hard to read and edit due to escaped newlines and dense content.
- Persona configuration was reloaded on every request, creating unnecessary disk I/O and coupling behavior to a monolithic file.
- Development workflow requires fast iteration on persona prompts without restarting the app, while production needs predictable performance.

**Decision**:
- Move canonical persona configuration to `system_prompts/personas_config.json`.
- Store each persona’s system prompt in a separate, plain-text file under `system_prompts/`, referenced via `system_prompt_file`.
- Introduce a cached loader (`load_personas`) that:
  - Loads personas from disk on first use.
  - Watches the `system_prompts/` folder mtime.
  - Reloads personas only when any file in that folder changes.

**Implementation**:
- Config:
  - `system_prompts/personas_config.json` defines persona metadata (names, roles, tools, flags, `system_prompt_file` references).
  - `system_prompts/*_system_prompt.txt` contain the actual system prompt text per persona.
- Loader:
  - `development/src/services/ai_gateway.py`:
    - `load_personas()` maintains an in-memory cache of personas.
    - `_get_system_prompts_mtime()` computes the latest mtime in `system_prompts/`.
    - `_load_personas_from_disk()` reads `personas_config.json`, loads all referenced prompt files, and builds the in-memory persona map.

**Enforcement**:
- All persona behavior changes must go through `system_prompts/personas_config.json` and the corresponding `*_system_prompt.txt` files.
- Python code must not hardcode persona behavior; it reads from the loader only.
- Documentation:
  - `summary.md`, `architecture.md`, `system-flow.md`, and `PATTERNS_AND_METHODS.md` updated to reference the new structure and loader behavior.

**Related ADRs**:
- ADR-001 (Fail-Fast Configuration Architecture)
- ADR-002 (Unified API Response Format)

---

### ADR-017: Orchestrator Reliability Fixes - Stack-Agnostic, Testability, Smoke Tests

**Status**: Accepted and Implemented
**Date**: 2025-11-23
**Related ADRs**: ADR-008 (Sequential Orchestrator MVP), ADR-011 (Robustness Fixes), ADR-014 (Task Breakdown Quality Standards)

**Context**:
Initial Sprint 1 execution (NFR-001 + US-009) revealed critical orchestrator issues:
1. **Hardcoded npm install** - Not stack-agnostic, failed for non-Node.js projects
2. **Server auto-start on import** - Made HTTP servers untestable (tests hung)
3. **Jordan writing comprehensive tests** - Ignored "smoke test only" instructions, wrote 5+ tests
4. **Missing architectural specifications** - Mike didn't provide complete patterns for Alex/Jordan

These issues caused:
- Missing dependencies (express-session not installed)
- Test timeouts (server spawned as child process, waited for log output)
- Conflicting instructions to LLM personas (unclear context)

**Decision**:
Implement four critical fixes to make orchestrator reliable and stack-agnostic:

**1. Stack-Agnostic Dependency Installation**
- Remove hardcoded `npm install` logic from orchestrator
- Add `command_to_run` field to task schema
- Mike specifies install commands in task breakdown (npm, pip, mvn, bundle, etc.)
- Orchestrator executes any command with proper error logging and stop-on-failure

**2. Server Testability Pattern**
- Mike must specify in NFR-001: "Server modules export app object for testing"
- Pattern: `export const app = express(); if (import.meta.url === \`file://\${process.argv[1]}\`) { app.listen(port); }`
- Allows Jordan to import server without auto-start: `const { app } = await import('../src/server.js')`
- Server starts conditionally only when run directly, not when imported by tests

**3. Jordan Smoke Test Enforcement**
- Rewrite Jordan's prompt to make "1-2 tests MAXIMUM" the primary directive
- Add explicit patterns by app type (HTTP, Database, CLI, Combined)
- Forbid: spawn(), exec(), fork(), log parsing
- Require: Direct imports, native test utilities (app.listen(0), app.address().port)

**4. Mike's Comprehensive Architectural Specifications**
- Expand Mike's architectural principles from 7 to 10 categories
- Add: Environment & Configuration, Database Patterns, Async/Await Consistency
- Enhance: API Consistency (middleware order), Server Testability
- Mike must specify all patterns in NFR-001 for Alex and Jordan to follow

**Rationale**:
- **Stack-Agnostic**: Works for any tech stack (Node.js, Python, Java, Ruby, Go)
- **Testable**: HTTP servers can be imported and tested without hanging
- **Focused Testing**: Smoke tests verify code runs, not comprehensive functionality
- **Complete Context**: Mike provides all architectural patterns upfront

**Implementation**:
- `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt`:
  - Added `command_to_run` field to task schema (lines 274-299)
  - Added 10 architectural principles including server testability (lines 214-285)
  - Added environment config, database patterns, async/await specs
- `system_prompts/SPRINT_EXECUTION_QA_system_prompt.txt`:
  - Made "1-2 tests MAXIMUM" primary directive (lines 3-18)
  - Added 4 stack-specific smoke test patterns (lines 73-187)
  - Forbid spawn/exec, require direct imports
- `development/src/services/sprint_orchestrator.py`:
  - Added `_execute_task_command()` method for generic command execution (lines 821-862)
  - Execute `command_to_run` after files written with error handling (lines 1603-1611)
  - Removed hardcoded npm install logic (lines 1704-1715)
  - Added context headers to Mike/Alex/Jordan calls (lines 2054-2079, 2409-2423, 2703-2708)

**Enforcement**:
- Mike's prompt requires `command_to_run` for install tasks
- Mike's prompt requires server testability pattern in NFR-001
- Jordan's prompt enforces 1-2 test maximum with explicit patterns
- Orchestrator validates and executes commands, stops on failure
- Context headers clarify role/story/attempt for each persona call

**Consequences**:
**Positive:**
- ✅ Orchestrator works for any tech stack (Python, Java, Ruby, Go, etc.)
- ✅ HTTP servers testable without hanging or spawning processes
- ✅ Jordan writes focused smoke tests (1-2 per story)
- ✅ Mike provides complete architectural contract
- ✅ Clear context reduces LLM confusion
- ✅ Validated with successful Sprint 1 execution (NFR-001 + US-009)

**Negative:**
- Mike's NFR-001 output is more verbose (10 architectural categories)
- Requires Mike to think through testability patterns upfront

**Status**: Accepted - Validated with Sprint 1 (NFR-001 + US-009) on 2025-11-23

---

### ADR-011: Persona Tool Filtering and Sprint Review PM Gating

**Status**: Accepted and Implemented  
**Date**: 2025-12-10  

**Rationale**:
- All personas were receiving all available tools (http_post, list_directory, run_command, read_file, write_text) regardless of their `personas_config.json` tool configuration
- This caused SPRINT_REVIEW_PM (Sarah) to call file tools and dump raw file contents into chat during Sprint Review meetings
- Sarah was also responding to technical questions directed at Alex, despite prompt instructions to stay silent
- Prompt-based gating ("stay silent" or "No comment") was unreliable due to LLM non-compliance

**Implementation**:
1. **Tool Filtering** (`development/src/services/ai_gateway.py`):
   - Modified `build_tools_array(persona_tools=None)` to accept and filter by persona's configured tools (lines 35-241)
   - Updated `call_openrouter_api()` signature to accept `persona_tools` parameter (line 384)
   - Updated all calls to `build_tools_array()` to pass `persona_tools` (lines 441, 807)
   - Updated `streaming.py` to extract and pass persona tools from config (lines 597-601)

2. **Tool Dump Suppression** (`development/src/services/ai_gateway.py`):
   - Added check in Alex's bounded loop to prevent tool dumps (>1000 chars starting with "📄 File:" or "📁 Directory:") from becoming `running_content` (lines 853-862)
   - Added same check for all personas at fallback path where `function_results` becomes `content` (lines 1010-1019)

3. **Hard Gate for SPRINT_REVIEW_PM** (`development/src/streaming.py`):
   - Added name-based filter: Sarah only responds if message starts with "sarah", "Sarah", or "SARAH" (lines 242-247)
   - Uses `continue` to skip Sarah entirely if not addressed by name
   - Happens before context injection or API calls

**Enforcement**:
- `build_tools_array()` filters tools based on `persona_tools` parameter (backward compatible: returns all tools if None)
- Tool dump checks use length (>1000 chars) and prefix patterns ("📄 File:", "📁 Directory:")
- SPRINT_REVIEW_PM hard gate checks first word of message (case-insensitive)
- Only affects SPRINT_REVIEW_PM; all other personas unaffected

**Consequences**:
**Positive:**
- ✅ SPRINT_REVIEW_PM only gets `http_post` tool (as configured)
- ✅ SPRINT_REVIEW_ALEX gets all tools (read_file, write_text, etc.) as configured
- ✅ No raw file dumps appear in chat from any persona
- ✅ Sarah only responds when explicitly addressed by name
- ✅ Saves API costs by not calling Sarah for technical questions
- ✅ All other meetings (Vision, Requirements, Planning, Execution) unaffected
- ✅ Backward compatible: personas without tool config still get all tools

**Negative:**
- User must explicitly say "Sarah" to address PM during Sprint Review
- Hard gate is more restrictive than prompt-based gating

**Related ADRs**:
- ADR-010 (Scribe Meeting Isolation) - Similar config-driven behavior control

---

### Potential Future Decisions

1. **Database Integration**: Consider moving from file-based storage to database
2. **Authentication System**: User authentication and authorization
3. **API Versioning**: Version management for API evolution
4. **Microservices Architecture**: Breaking into smaller services
5. **Container Orchestration**: Kubernetes or similar deployment
6. **Automatic Session Summarization**: Trigger summarization every 5-7 turns

Each of these would require new ADRs if pursued, following the established decision-making process.
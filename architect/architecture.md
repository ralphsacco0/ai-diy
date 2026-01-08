# AI-DIY Architecture (Current Implementation Status)
 Status: Canonical
 Audience: Developers, Architects
 Last Updated: 2026-01-07
 Related: [PATTERNS_AND_METHODS.md](./PATTERNS_AND_METHODS.md) · [GOVERNANCE.md](./GOVERNANCE.md) · [DESIGN_PRINCIPLES.md](./DESIGN_PRINCIPLES.md)

## Overview and Scope

This document describes the AI-DIY system architecture and current implementation status. The system provides a meeting-driven AI application with persona-orchestrated flows. Enhanced features for security, logging, and fail-fast configuration have been implemented and are dynamically activated when their modules are available.

- **Goal**: Reliable, secure, meeting-driven AI app with fail-fast configuration, structured logging, and comprehensive safety mechanisms.
- **Non-goal**: Duplicating executable content or maintaining legacy patterns.

### System Vision
AI-DIY enables non-coders to guide an AI development team through structured meetings to produce working, tested software. The system features:
- **Core functionality** with Vision and Backlog workflows
- **Multi-persona architecture** with meeting framework
- **Enhanced features implemented and dynamically loaded when available** (fail-fast config, security, structured logging)
- **Unified API response patterns** defined in conventions.py
 Related methodology: see [PATTERNS_AND_METHODS.md](./PATTERNS_AND_METHODS.md) → [Cascade-Style Context Injection](./PATTERNS_AND_METHODS.md#pattern-cascade-style-context-regular-conversations), [Investigation + Execution Mode](./PATTERNS_AND_METHODS.md#pattern-sprint-review-alex-investigation--execution), [Sprint Execution Method](./PATTERNS_AND_METHODS.md#sprint-execution-method-sequential-orchestrator).

---

## Capabilities and Activation Status

This table summarizes the main runtime capabilities, where they live, how they are activated, and how to verify their status.

| Capability | What it does | Where it lives | How it activates | How to check |
|-----------|--------------|----------------|------------------|-------------|
| Fail-fast configuration | Validates environment and configuration at startup | `development/src/config_manager.py` | Dynamically loaded by `development/src/main.py`; falls back to environment-only configuration if missing | `/api/env.features.config_manager` |
| Structured logging | Structured/JSON logging middleware for requests | `development/src/logging_middleware.py` | Dynamically loaded by `development/src/main.py` when available | `/api/env.features.logging_middleware` |
| Security middleware | Rate limiting, input validation, path protection, security headers | `development/src/security_middleware.py`, `development/src/security_utils.py` | Dynamically loaded by `development/src/main.py` when available | `/api/env.features.security_middleware` |
| Data management | Overwrite-on-save behavior and CSV schema validation for backlog and vision | `development/src/data_manager.py`, `development/src/api/backlog.py`, `development/src/api/vision.py` | Provides shared helpers that implement the overwrite-on-save and CSV validation rules used by Vision/Backlog flows and status endpoints | See `architect/dataflow-and-schema.md` for behavioral details |

---

## Meeting-Driven Workflow

### Meeting Types

| Meeting | Persona | Purpose | Output |
|---------|---------|---------|--------|
| Vision | VISION_PM | Create vision statement | Vision document (living doc with backups) |
| Requirements | REQUIREMENTS_PM | Clarify and prioritize backlog | Backlog CSV (living document) |
| Sprint Planning | SPRINT_PLANNING_ARCHITECT | Define scope and decomposition | Sprint definition |
| Sprint Execution | SPRINT_EXECUTION_PM | Build and test code | Working software |
| Sprint Review | SPRINT_REVIEW_PM + SPRINT_REVIEW_ALEX | Demo and gather feedback | Feedback, bug fixes |

_Note: A Retrospective meeting type was originally planned but is not implemented in the current MVP, so it is omitted from this table._

### Meeting Activation (Solo Mode + Additional Personas)

"SPRINT_REVIEW_PM" uses solo_mode with an additional SPRINT_REVIEW_ALEX persona so Sarah leads while Alex can debug during the meeting.

 Related methodology: See [Solo Mode with Additional Personas](./PATTERNS_AND_METHODS.md#pattern-solo-mode-with-additional-personas).

---

## Sprint Execution

### Concurrent User Messaging

During sprint execution, users can ask Sarah questions and receive immediate responses in the chat. Execution messages (from Mike, Alex, and Jordan) are displayed with a purple accent styling to distinguish them from user messages and Sarah's responses. This allows the team to interact with Sarah while the sprint runs in the background.

**Implementation**: Execution messages flow through the same chat rendering pipeline as normal persona responses, enabling concurrent messaging without interference.

### API Endpoints

Sprint Execution provides the following REST API endpoints:

- **Execute Sprint**: POST `/api/sprints/{sprint_id}/execute`
  - Triggers sprint execution for a saved sprint plan
  - Starts orchestrator in background (non-blocking)
  - Frontend opens the SSE stream after Sarah says: "Sprint execution started for SP-XXX"
  - Returns immediately with status "executing"
  - Implementation: `development/src/api/sprint.py` (lines 334-427)

- **Stream Progress**: GET `/api/sprints/stream`
  - Server-Sent Events (SSE) endpoint for real-time execution updates (global, not per-sprint)
  - Streams Mike/Alex/Jordan activity messages from all sprint executions
  - Events include `sprint_id` in payload for client-side filtering
  - Queue-based listener management with graceful cleanup
  - Stream stays open after `sprint_complete` (supports consecutive sprints)
  - Global buffer replays last ~200 events to new listeners
  - Implementation: `development/src/api/sprint.py`

- **Get Status**: GET `/api/sprints/{sprint_id}/status`
  - Non-streaming status endpoint
  - Returns current sprint status, progress, and recent events
  - Includes stories completed, tasks completed, test results
  - Implementation: `development/src/api/sprint.py` (lines 430-571)

- **Rollback Sprint**: POST `/api/sprints/{sprint_id}/rollback`
  - Restores sprint to a previous backup snapshot
  - Requires `backup_id` in request body
  - Implementation: `development/src/api/sprint.py` (lines 676-751)

### Sprint Execution Runtime Path (Orchestrator → UI)

- Orchestrator emits execution events per sprint
  - Primary shape: `{ "event_type": "<name>", "data": { ... } }`
  - Fallback shape(s):
    - `{ "type": "team_message", "persona": "mike|alex|jordan", "message": "..." }`
    - `{ "type": "sprint_complete", "sprint_id": "SP-XXX" }` (close signal)
- SSE Manager (global fan-out)
  - Single global buffer (~200 messages) replayed to new listeners
  - Emits to all active listeners; events include `sprint_id` for client filtering
- API streaming endpoint
  - GET `/api/sprints/stream` yields default SSE "message" events (`data: {json}`)
  - No named `event:` field is set; events contain `sprint_id` for filtering
- Frontend behavior
  - Opens EventSource when Sarah confirms: "Sprint execution started for SP-XXX"
  - Listens on default `message` event, maps events to Mike/Alex/Jordan/system lines
  - Pause/Resume: on user input → POST `/pause`; after Sarah replies → POST `/resume` and re-open SSE; buffered messages are delivered on reconnect

### Sprint Snapshot and Rollback (UI + API)

- **What is snapshotted**
  - plan.json (pre-execution state)
  - Backlog.csv
  - wireframes/ (if present)
  - execution_log.jsonl (if present)
  - execution-sandbox/client-projects/{project_name}
  - Note: Vision is not included.

- **When**
  - Snapshot is taken automatically at sprint start (pre-execution).

- **Storage layout**
  - Path: static/appdocs/sprints/backups/{sprint_id}/{backup_id}/
  - Metadata: metadata.json includes backup_id, created_at, sprint_id, project_name, items.

- **UI controls**
  - Sprint plans modal → “Rollback Sprint to Snapshot”.
  - A dropdown of existing backups appears only when `plan.backups` is non-empty.
  - Clicking “Rollback” posts to `/api/sprints/{sprint_id}/rollback` with `{ backup_id }`.

- **API**
  - List: GET `/api/sprints` returns plans with `backups`.
  - Rollback: POST `/api/sprints/{sprint_id}/rollback` with `{ "backup_id": "<id>" }`.

- **Behavior on rollback**
  - Restores: plan, Backlog.csv, execution_log.jsonl (or removes it if the backup had none), wireframes, and the project sandbox for `project_name`.
  - Merges backup registry into the restored plan so the plan reflects available backups.

- **Pruning after rollback**
  - Deletes future sprint artifacts with IDs greater than the restored sprint:
    - Their plan files, execution logs, and backup folders.
  - Project sandbox is preserved during prune.

- **Troubleshooting**
  - If the rollback control isn’t visible:
    - Confirm `plan.backups` in the sprint plan file has entries.
    - Confirm backup directories exist under static/appdocs/sprints/backups/{sprint_id}/.

- **References**
  - UI: development/src/static/index.html (sprint plans modal, rollback handlers)
  - API: development/src/api/sprint.py (`/api/sprints`, `/api/sprints/{sprint_id}/rollback`)
  - Orchestrator: development/src/services/sprint_orchestrator.py (snapshot, restore, prune)

## Multi-Persona System

### Configuration-Driven Personas

All persona behavior is defined in configuration (not Python). Each persona entry in `system_prompts/personas_config.json` has `name`, `role`, `enabled`, `tools`, `inject_context`, `meeting_triggers`, and meeting flags. The actual system prompts for each persona live in separate `*_system_prompt.txt` files under `system_prompts/`, referenced by `system_prompt_file` fields.

Together, `personas_config.json` plus the prompt files form the single source of truth for persona behavior.

### Single Person, Multiple Personas

Same person can have multiple personas for different contexts (e.g., Sarah: `PM`, `VISION_PM`, `REQUIREMENTS_PM`).

### Persona Role Mapping (Alex → SPRINT_REVIEW_ALEX in Sprint Review)

Use `persona_role` on personas and `persona_role_mapping` on meeting config to map a person to the right persona for that meeting.

Related methodology: See [Meeting Personas with Role Mapping](./PATTERNS_AND_METHODS.md#pattern-meeting-personas-with-role-mapping).

### Scribe Isolation During Meetings

Set `scribe_active_during_meeting: false` on all meeting personas so Scribe does not respond during structured meetings.

Related methodology: See [Scribe Isolation During Meetings](./PATTERNS_AND_METHODS.md#pattern-scribe-isolation-during-meetings).

### Persona Tool Filtering (ADR-011)

**Implementation**: `development/src/services/ai_gateway.py` + `development/src/streaming.py`

Personas only receive the tools specified in their `personas_config.json` `tools` array. The `build_tools_array(persona_tools)` function filters the available tools based on the persona's configuration.

**Available Tools**:
- `http_post` - Make HTTP POST requests to internal APIs
- `list_directory` - List project structure in sandbox
- `run_command` - Execute commands in sandbox
- `read_file` - Read file contents from sandbox
- `write_text` - Write/modify files in sandbox
- `list_snapshots` - List available rollback points
- `restore_snapshot` - Restore project to previous snapshot

**Example Configurations**:
- `SPRINT_REVIEW_PM`: `["http_post"]` - Only API calls, no file access
- `SPRINT_REVIEW_ALEX`: `["read_file", "write_text", "http_post", "list_directory", "run_command", "list_snapshots", "restore_snapshot"]` - Full access for debugging and fixes
- `VISION_PM`, `REQUIREMENTS_PM`, `SPRINT_PLANNING_ARCHITECT`: `["http_post"]` - Only need to save data

**Backward Compatibility**: If `persona_tools` is `None` or empty, all tools are provided (for personas without explicit tool configuration).

**Tool Dump Suppression**: Raw tool outputs (file contents >1000 chars starting with "📄 File:" or "📁 Directory:") are prevented from becoming persona responses. This ensures personas provide natural language summaries instead of echoing raw file dumps.

### SPRINT_REVIEW_PM Hard Gate (ADR-011)

**Implementation**: `development/src/streaming.py` lines 242-247

SPRINT_REVIEW_PM (Sarah) only responds if the user message starts with "sarah", "Sarah", or "SARAH". This hard gate prevents Sarah from:
- Responding to technical questions directed at Alex
- Answering approval messages like "yes" or "no"
- Generating unnecessary API calls and costs

This is a code-level gate (hard gate) rather than a prompt-level instruction (soft gate), making it more reliable than relying on LLM compliance with "stay silent" instructions.

**Only affects SPRINT_REVIEW_PM**. All other personas respond normally to all messages.

---

## Application Entry Point

### Consolidated Main Entry Point
**File**: `development/src/main.py`
- **Used by**: `development/start.command` (runs `uvicorn main:app`)
- **Architecture**: Single consolidated entry point with graceful feature degradation
- **Core Features**: Streaming, models, change requests, testing, chat, vision, backlog, scribe APIs

### Intelligent Feature Loading
The application automatically detects and activates enhanced features based on available dependencies:

**Phase 2: Fail-Fast Configuration** (Auto-detected)
- Loads `config_manager` if available
- Falls back to environment variables if not available
- Validates configuration at startup when active

**Phase 3: Data Management** (Auto-detected)
- Loads `data_manager` if available
- Provides overwrite-on-save and CSV validation when active

**Phase 4: Structured Logging** (Auto-detected)
- Loads `logging_middleware` if available
- Falls back to basic logging if not available
- Provides JSON-line logging when active

**Phase 5: Security Middleware** (Auto-detected)
- Loads `security_middleware` if available
- Falls back to basic security headers if not available
- Provides rate limiting, input validation, and audit logging when active

### Feature Status Visibility
Check which features are active:
- **`GET /api/env`** - Shows active features and configuration
- **`GET /health`** - Comprehensive health check with feature validation
- **Startup logs** - Display which features loaded successfully

### Design Benefits
- ✅ **No breaking changes**: Works with or without enhanced modules
- ✅ **Graceful degradation**: Missing dependencies don't crash the app
- ✅ **Single entry point**: No confusion about which main.py to use
- ✅ **Easy testing**: Can test with/without enhanced features
- ✅ **Clear visibility**: Startup logs show exactly what's active

## Logging Architecture

### Core Logging (Always On)
- **Module**: `development/src/core/logging_config.py`
- **Behavior**:
  - Initializes root logging on import via `setup_logging()`
  - Writes structured JSONL logs to `development/src/logs/app.jsonl` with rotation
  - Adds console logging with human-readable format at `LOG_LEVEL`
- **Configuration**:
  - `LOG_LEVEL` controls overall verbosity (DEBUG/INFO/WARNING/ERROR)

### API Logging Middleware (Enhanced Layer)
- **Module**: `development/src/logging_middleware.py`
- **Activation**:
  - `development/src/main.py` attempts to import `logging_middleware` and `setup_structured_logging`
  - When available, `setup_structured_logging(app_config)` is called and `logging_middleware` is attached as FastAPI middleware
  - Activation visible via `/api/env.features.logging_middleware`
- **Behavior**:
  - Logs each `/api/...` request and error as JSON on logger `ai_diy.api`
  - In production, writes per-day JSONL files under a `logs/` directory when file logging is enabled

### Model and User Activity Logging
- **Model Calls**:
  - `log_openrouter_call(...)` logs OpenRouter calls with token counts, latency, status, and optional hashes/payloads
  - Controlled by `OPENROUTER_LOG_PAYLOADS`, `OPENROUTER_LOG_SAMPLE`, and `OPENROUTER_LOG_MAX_CHARS`
- **User Actions**:
  - `log_user_action(action, **kwargs)` logs user activity when `USER_LOG_ENABLED` is true
  - `USER_LOG_ID` and `USER_LOG_LEVEL` control identity and minimum level for user logs

For detailed logging configuration guidance and recommended values, see [PATTERNS_AND_METHODS.md](./PATTERNS_AND_METHODS.md#logging-patterns).

---

## Personas Contract (Enhanced)

### Enhanced Requirements
- **Configuration Location**: `system_prompts/personas_config.json` (canonical by default)
- **System Prompts Location**: `system_prompts/*_system_prompt.txt` (one file per persona)
- **Runtime Override**: `PERSONAS_PATH` environment variable can point to an alternative personas config file (absolute path, or relative to project root)
- **Fail-Fast Validation**: Invalid JSON or missing required fields cause immediate startup failure when configuration validation is enabled
- **Security Integration**: Persona context available in structured logs

### Persona Definitions
All persona definitions are loaded from `system_prompts/personas_config.json` plus the referenced system prompt files. The JSON defines structure and wiring (names, roles, tools, meeting flags); the external text files define the detailed behavior instructions.
- **Meeting Context**: Personas receive meeting mode and context in logs
- **Security Headers**: All responses include security headers in production
- **Input Validation**: All persona inputs validated and sanitized
- **Rate Limiting**: Persona requests subject to rate limiting

### Context Management (2025-10-24)

**Vision PM Persona**:
- Enhanced with awareness of conversation history limits (9-10 turns typical)
- Implements periodic natural recaps to maintain context continuity
- Handles graceful degradation when early messages fall out of history
- Documentation: `docs/personas/vision-pm.md`

**Strategy**:
- Personas know their typical history capacity
- Natural summaries keep critical information fresh
- Injected context (vision docs, backlog) persists independently
- No mechanical turn counting - personas decide when recaps make sense

---

## Data Storage Patterns

### Pattern 1: Living Document with Backups (Vision API)

**Design Philosophy**: Single canonical document that evolves over time, with timestamped backups for recovery

- **File Strategy**: Fixed canonical file with backups on each save
- **ID Format**: `"vision"` (fixed, not generated)
- **Storage Location**: `static/appdocs/visions/`
- **File Types**: `vision.json` (canonical) + `vision.md` (human-readable) + `backups/vision_YYYYMMDD_HHMMSS.json`

**Rationale**:
- Vision is a living document - one source of truth per project
- Backups provide rollback capability without cluttering the main directory
- Approval workflow tracked via `client_approval` flag in the document
- Simpler than versioning - just overwrite and backup

**Operations** (see `api/vision.py:save_vision()`):
- **save**: Overwrites `vision.json`, creates timestamped backup in `backups/`
- **list**: Returns vision metadata
- **latest**: Returns current vision (always the same file)
- **get**: Retrieves current vision
- **delete**: Removes vision file

### Pattern 2: Living Document (Backlog API)

**Design Philosophy**: Single evolving document containing multiple items as rows

- **File Strategy**: One file containing all items, fixed ID
- **ID Format**: `Backlog` (single, consistent ID)
- **Storage Location**: `static/appdocs/backlog/`
- **File Types**: `Backlog.csv` (canonical) + `Backlog.json` (metadata) + `wireframes/*.html`
- **Individual Items**: Identified by `Story_ID` column within CSV (e.g., NEW-002, NEW-003, WF-001)

**Rationale**:
- Backlog is a living document that gets updated, not versioned
- All requirements managed together for easier viewing and updates
- Requirements are rows in a table, not separate documents
- Overwrite-on-save updates the entire backlog atomically
- Simpler UI display (one file to fetch, not multiple)

**Operations**:
- **save**: Overwrites entire `Backlog.csv` file with new content
- **list**: Returns metadata about the single backlog file
- **latest**: Returns metadata about the current backlog; raw CSV is available at `GET /api/backlog/latest`
- **get**: Returns current backlog metadata (JSON)
- **delete**: Removes the backlog file (rare operation)

### When to Use Each Pattern

| Use Pattern 1 (Living Doc + Backups) When... | Use Pattern 2 (Living Document CSV) When... |
|----------------------------------------------|---------------------------------------------|
| Single canonical document per project | Data is tabular (rows and columns) |
| Need rollback via timestamped backups | All items viewed together in one file |
| Approval workflow (flag in document) | Items are rows, not separate documents |
| Examples: Vision, Project Config | Examples: Backlog, Sprint Plans |

---

## API Architecture

### Unified Response Format
All API endpoints return responses in the unified envelope format:
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    "vision_id": "vision_20251007_180400",
    "overwrite": false
  }
}
```

### Error Response Format
Error responses include machine-readable error codes:
```json
{
  "success": false,
  "message": "Validation failed: missing required fields",
  "data": {
    "error_code": "VALIDATION_ERROR"
  }
}
```

### Standard Actions
All endpoints support standard actions:
- **save**: Create or update resource with overwrite-on-save behavior
- **get**: Retrieve specific resource by ID
- **list**: List all resources with metadata
- **delete**: Remove resource and associated files
- **latest**: Get most recent resource (with approval status for visions)

---

## Workflow Integration

### Vision Creation Workflow [WF-vision] (Enhanced)
**Process Documentation**: See `docs/vision_process.md` for complete workflow details

**Security and validation hooks** (when security/logging middleware is active)
- **Input Validation**: All vision data validated and sanitized
- **Security Logging**: Vision operations logged with security context
- **Path Protection**: File operations validated against allowlist
- **Size Limits**: Content validated against size constraints
- **Meeting Mode**: Vision PM persona leads structured Vision Meeting
- **Approval Workflow**: Tracks draft vs. approved status with timestamps
- **Versioning**: Each vision saved as separate timestamped file

### Requirements Creation Workflow [WF-requirements] (Enhanced)
**Process Documentation**: See `docs/requirements_process.md` for complete workflow details

**Security and validation hooks** (when security/logging middleware is active)
- **CSV Validation**: Backlog CSV validated against canonical schema
- **Wireframe Security**: HTML wireframes scanned for malicious content
- **File Protection**: All file operations validated and sandboxed
- **Content Sanitization**: User input sanitized before processing
- **Meeting Mode**: Requirements PM persona leads structured Requirements Meeting
- **Living Document**: All requirements stored in single `Backlog.csv` file
- **Wireframe Generation**: HTML wireframes created with Tailwind CSS

---

## Operational Standards (Enhanced)

### Local Timezone Handling
- **Rule**: All user-facing timestamps use system local timezone
- **Implementation**: `datetime.now()` respects system timezone configuration
- **Logging**: All log timestamps in ISO format with timezone

### Enhanced Guardrails
- **No Silent Failures**: All errors result in clear, actionable error messages
- **Configuration Validation**: Startup fails immediately on invalid configuration
- **Security First**: All operations validated for security before execution
- **Audit Trails**: All operations logged with complete context for compliance

### Performance Standards
- **Response Times**: API operations complete within 90 seconds
- **Resource Limits**: Memory and CPU usage monitored and limited
- **Concurrent Requests**: Rate limiting prevents resource exhaustion
- **Error Recovery**: Graceful degradation with clear error reporting

---

## ADRs (Architecture Decision Records) (Updated)

### Phase 1-5 Implementation ADRs

#### ADR-001: Fail-Fast Configuration Architecture ✅
**Status**: Accepted and Implemented
- **Decision**: Implement fail-fast configuration with no defaults or silent fallbacks
- **Rationale**: Prevents silent failures and ensures explicit configuration
- **Implementation**: `config_manager.py` with startup validation
- **Enforcement**: All configuration must be explicitly provided

#### ADR-002: Unified API Response Format ✅
**Status**: Accepted and Implemented
- **Decision**: All API endpoints use unified response envelope format
- **Rationale**: Enables consistent client handling and machine-readable errors
- **Implementation**: `api/conventions.py` with Pydantic models
- **Enforcement**: All endpoints return `{"success": true|false, "message": "string", "data": {...}}`

#### ADR-003: Structured JSON-Line Logging ✅
**Status**: Accepted and Implemented
- **Decision**: Implement structured logging with JSON-line format for all API calls
- **Rationale**: Enables operational visibility and security monitoring
- **Implementation**: `logging_middleware.py` with FastAPI middleware
- **Enforcement**: All API calls logged with required fields

#### ADR-004: Comprehensive Security Architecture ✅
**Status**: Accepted and Implemented
- **Decision**: Implement multi-layer security with rate limiting, input validation, and audit logging
- **Rationale**: Ensures production-ready security and compliance
- **Implementation**: `security_middleware.py` and `security_utils.py`
- **Enforcement**: Security validation on all requests and file operations

#### ADR-005: Overwrite-on-Save Data Management ✅
**Status**: Accepted and Implemented
- **Decision**: Implement overwrite-on-save behavior for all data operations
- **Rationale**: Provides predictable file management and clear operation feedback
- **Implementation**: `data_manager.py` with create vs overwrite logic
- **Enforcement**: All save operations return `is_overwrite` status

#### ADR-006: Chat History Sliding Window ✅
**Status**: Accepted and Active
- **Decision**: Implement 19-message sliding window for chat history sent to backend
- **Rationale**: Balances context retention with token limits and costs; provides 9-12 turns for Vision Meetings, 5-6 turns for full team conversations
- **Implementation**: Frontend `chatHistory` array (20 max), sends 19 via `.slice(0, -1)`
- **Context Management**: Personas enhanced with awareness of limits; use recaps to maintain continuity
- **Testing**: Confirmed at turn 12-14, earliest messages drop out; personas handle gracefully
- **Documentation**: `docs/chat-history-limits.md`, `docs/personas/vision-pm.md`

---

## Deployment Architecture

### Environment Configurations

#### Local Development
```bash
# Set development environment variables
export LOG_LEVEL=DEBUG
export PRODUCTION=false

# Run with uvicorn (used by start.command)
cd development/src && uvicorn main:app --reload --port 8000
```

#### Railway Production
The application deploys to Railway with Caddy as reverse proxy. See [Generated App Routing Patterns](./PATTERNS_AND_METHODS.md#generated-app-routing-patterns) for details on how routing works between local and Railway.

```bash
# Railway environment variables (set in Railway dashboard)
LOG_LEVEL=INFO
PORT=8000  # Railway sets this automatically
```

### Entry Point
- **Single entry point**: `development/src/main.py`
- **Start script**: `development/start.command` runs `uvicorn main:app`
- **Dynamic feature loading**: Enhanced modules (security, logging) loaded if available

---

## Monitoring and Observability

### Health Check Endpoints
- **`/health`**: Comprehensive system health with security status
- **`/api/env`**: Environment and configuration status
- **`/api/security/status`**: Security system status and metrics
- **`/api/data/status`**: Data management system status

### Log Analysis
- **API Logs**: JSON-line format for programmatic analysis
- **Security Logs**: Separate logger for security event correlation
- **Performance Logs**: Duration tracking for optimization
- **Error Logs**: Stack traces and context for debugging

### Metrics and Alerting
- **Rate Limit Violations**: Logged for security analysis
- **Resource Usage**: Monitored for capacity planning
- **Error Rates**: Tracked for operational health
- **Security Events**: Alerted for immediate response

---

## Development Workflow

### Code Organization
```
development/src/
├── api/                    # API endpoints with validation
│   ├── conventions.py      # Unified response formats
│   ├── vision.py           # Vision API using versioned-document pattern
│   └── backlog.py          # Backlog API with CSV validation
├── config_manager.py       # Fail-fast configuration management
├── data_manager.py         # Overwrite-on-save data operations
├── logging_middleware.py   # Structured logging implementation
├── security_middleware.py  # Comprehensive security middleware
├── security_utils.py       # Security utilities and validation
└── main.py                 # Consolidated application entry point (dynamic feature loading)

development/tests/          # Comprehensive test suites
├── test_api_envelope.py    # API standardization tests
├── test_data_management.py # Data management tests
├── test_security.py        # Security feature tests
└── test_integration.py     # End-to-end integration tests
```

### Testing Strategy
- **Unit Tests**: Individual component validation
- **Integration Tests**: Cross-component functionality
- **Security Tests**: Comprehensive security validation
- **End-to-End Tests**: Complete workflow validation

### Code Quality Standards
- **No Defaults**: All configuration must be explicit
- **Fail-Fast**: Clear errors for any missing or invalid setup
- **Security First**: All code validated for security implications
- **Documentation**: All functions and classes fully documented

---

## Integrity Manifest (Complete Implementation)

### Core System Files
- **system_prompts/personas_config.json**: Persona definitions and wiring (canonical config)
- **system_prompts/*_system_prompt.txt**: Individual persona system prompts (plain text)
- **development/src/main.py**: Consolidated application entry point (dynamic feature loading)
- **development/src/config_manager.py**: Fail-fast configuration management
- **development/src/security_middleware.py**: Comprehensive security middleware
- **development/src/data_manager.py**: Overwrite-on-save data management
- **docs/chat-history-limits.md**: Chat history management documentation
- **docs/personas/vision-pm.md**: Vision PM persona documentation with context management

### API Endpoints
- **development/src/api/conventions.py**: Unified API response standards
- **development/src/api/vision.py**: Vision API with security and data validation
- **development/src/api/backlog.py**: Backlog API with CSV schema validation

### Security Components
- **development/src/security_utils.py**: File validation and content scanning
- **development/src/logging_middleware.py**: Structured logging implementation

### Configuration Files
- **development/.env.example**: Complete configuration template
- **development/setup_config.py**: Automated environment setup
- **development/validate_config.py**: Configuration validation script

### Test Suites
- **tests/test_*.py**: Comprehensive test coverage for all phases

---

---

## Developer Guide: How to Extend AI-DIY

This section provides clear, actionable guidance for developers adding features to AI-DIY.

### 🎯 Core Principle: Copy Existing Patterns

**NEVER create a new pattern without first checking if an existing one solves your problem.**

The system has established patterns that work. Your job is to identify the right pattern and copy it, not invent new approaches.

---

### 📋 How to Add a New API Endpoint

**Gold Standard Pattern**: Copy from `development/src/api/vision.py` or `development/src/api/backlog.py`

#### Step-by-Step Process:

**1. Choose Your Model Endpoint**
- Simple document storage? → Copy `vision.py`
- CSV/tabular data with wireframes? → Copy `backlog.py`
- Both use the same pattern with minor variations

**2. Create Your API File**
```python
# development/src/api/your_feature.py
"""
[Feature] API - Handle creation, storage, and retrieval of [feature] documents.
Mirrors vision.py pattern exactly.
"""
```

**3. Use Standard Actions (REQUIRED)**
Every endpoint MUST support these actions:
- `save`: Create or update resource
- `get`: Retrieve specific resource by ID  
- `list`: List all resources with metadata
- `delete`: Remove resource
- `latest`: Get most recent resource (if applicable)

**4. Use Standard Response Format (REQUIRED)**
```python
class YourFeatureResponse(BaseModel):
    success: bool
    message: str
    your_feature_id: Optional[str] = None
    content: Optional[str] = None
    your_features: Optional[List[Dict]] = None
```

**5. Store Files in Standard Location (REQUIRED)**
```python
# ALWAYS use static/appdocs/ as root
FEATURE_DIR = Path("static/appdocs/your_feature_name")
FEATURE_DIR.mkdir(parents=True, exist_ok=True)
```

**Note**: Application logs are stored in `development/src/logs/app.jsonl`. Both `static/appdocs/` and `development/src/logs/` directories are created automatically at runtime.

**6. Register Your Router in main.py**
```python
# development/src/main.py
from api.your_feature import router as your_feature_router
app.include_router(your_feature_router)
```

**Example - Adding a "Sprint" endpoint:**
1. Copy `development/src/api/vision.py` → `development/src/api/sprint.py`
2. Change: `VISION_DIR` → `SPRINT_DIR = Path("static/appdocs/sprints")`
3. Change: `VisionRequest` → `SprintRequest`
4. Change: `VisionResponse` → `SprintResponse`
5. Update all function names and docstrings
6. Register router in `main.py`

---

### 👤 How to Add or Modify Personas

**Core Rule**: All persona configuration lives in `system_prompts/personas_config.json` plus the `system_prompts/*_system_prompt.txt` files. Minimize logic hidden in Python code.

#### Adding a New Persona Role

**1. Edit system_prompts/personas_config.json**
```json
{
  "personas": {
    "NEW_ROLE_KEY": {
      "name": "PersonName",
      "display_name": "PersonName · Role Title",
      "role": "Full Role Description",
      "role_key": "NEW_ROLE_KEY",
      "system_prompt_file": "system_prompts/NEW_ROLE_KEY_system_prompt.txt",
      "enabled": true,
      "priority": 5,
      "tools": ["http_post"]
    }
  }
}
```

**2. Create or update the system prompt file**

Create `system_prompts/NEW_ROLE_KEY_system_prompt.txt` with the full prompt content (plain text, real newlines).

**3. Key Fields Explained**
- `role_key`: MUST be uppercase, used in code (e.g., "DEVELOPER", "PM")
- `name`: Person's name (e.g., "Alex", "Sarah")
- `system_prompt_file`: Path to .txt file with full prompt (NOT inline `system_prompt`)
- `enabled`: Set false to temporarily disable without deleting
- `priority`: Lower number = responds first (1 = highest priority)
- `tools`: ["http_post"] if persona needs to call APIs, [] otherwise

**4. One Person, Multiple Roles**
Notice Sarah has 6 personas:
- `PM`: General project management
- `VISION_PM`: Vision meeting facilitator
- `REQUIREMENTS_PM`: Requirements meeting facilitator
- `SPRINT_REVIEW_PM`: Sprint review facilitator
- `SPRINT_EXECUTION_PM`: Sprint execution facilitator
- `SPRINT_RETROSPECTIVE_PM`: Retrospective facilitator

Same person, different roles/contexts. This is the pattern for meeting-specific behaviors.

**5. System Prompt Guidelines**
- Be EXPLICIT about when to respond vs stay silent
- Include exact matching patterns if workflow-driven
- Specify exact API endpoints to call with http_post()
- Include response format examples
- Use "You are [Name]" not "I am [Name]"

#### NO Python Code Changes Needed
The system automatically loads all enabled personas from JSON. No code changes required unless you're adding new infrastructure.

---

### ⚙️ Configuration Management Rules

**Core Philosophy**: **Fail Fast, No Defaults**

#### Decision Tree: JSON Config vs Environment Variable

**Use JSON Configuration When:**
- Human-readable/editable settings (personas, models, etc.)
- Application-specific configuration
- Data that changes during development
- Settings with complex structure

**Use Environment Variables When:**
- Deployment-specific values (host, port, production flag)
- Secrets and API keys
- System-level configuration (log level, data root)

**NEVER Use Defaults When:**
- Adding new features
- Introducing new configuration requirements
- If configuration is missing → FAIL FAST with clear error message

#### Configuration Files Location
```
Repository Root:
  system_prompts/personas_config.json   # Persona definitions and wiring (canonical)
  system_prompts/*_system_prompt.txt    # Individual persona system prompts
  models_config.json                    # AI model configuration
  .env                                  # Environment variables (not in git)

development/:
  .env.example              # Template showing all env vars
```

#### Example: Adding New Configuration

❌ **WRONG - Using Defaults**
```python
timeout = config.get("api_timeout", 30)  # Silent default!
```

✅ **RIGHT - Fail Fast**
```python
timeout = config.get("api_timeout")
if timeout is None:
    raise ValueError("Missing required config: api_timeout")
```

---

### 🚫 The No-Nos: Anti-Patterns to Avoid

#### Critical Rules - NEVER Do These:

**1. NEVER Use Silent Defaults or Fallbacks**
```python
# ❌ WRONG
model = config.get("model", "some-default-model")

# ✅ RIGHT  
model = config.get("model")
if not model:
    raise ValueError("Model configuration required. Set 'model' in config.")
```

**2. NEVER Create New Patterns Without Checking Existing Ones**
Before writing code, ask:
- "Does vision.py or backlog.py solve this?"
- "Is there a conventions.py function for this?"
- "Does data_manager.py already handle this?"

**3. NEVER Hardcode Model Names in Code**
```python
# ❌ WRONG
model = "anthropic/claude-3.5-sonnet"

# ✅ RIGHT
model = request.get("model")  # From request
# OR
model = models_config.favorites[0]  # From config
```

**4. NEVER Bypass Unified Response Format**
```python
# ❌ WRONG
return {"result": "success", "data": {...}}

# ✅ RIGHT
from api.conventions import create_success_response
return create_success_response("Operation completed", data={...})
```

**5. NEVER Store Data Outside static/appdocs/**
```python
# ❌ WRONG
DATA_DIR = Path("my_custom_location/data")

# ✅ RIGHT
DATA_DIR = Path("static/appdocs/my_feature")
```

**6. NEVER Put Persona Logic in Python Code**
```python
# ❌ WRONG - Logic in Python
if message.contains("vision"):
    persona = "VISION_PM"

# ✅ RIGHT - Logic in persona system prompt files referenced by personas_config.json
"system_prompt_file": "system_prompts/VISION_PM_system_prompt.txt"
```

**7. NEVER Mix Response Formats**
ALL endpoints must return the unified format from conventions.py:
```python
{
  "success": true/false,
  "message": "string",
  "data": {...}
}
```

**8. NEVER Create Files Without Parent Directory Check**
```python
# ❌ WRONG
with open(file_path, 'w') as f:
    f.write(content)

# ✅ RIGHT
file_path.parent.mkdir(parents=True, exist_ok=True)
with open(file_path, 'w') as f:
    f.write(content)
```

---

### 📚 Reference: Where to Find Patterns

When you need to understand how to implement something, look here:

| What You Need | Reference File | Key Pattern |
|--------------|----------------|-------------|
| **New API Endpoint** | `development/src/api/vision.py` | Complete CRUD pattern with standard actions |
| **CSV Data Handling** | `development/src/api/backlog.py` | CSV validation, headers, wireframe storage |
| **Response Formats** | `development/src/api/conventions.py` | ApiResponse, ApiError, create_success_response() |
| **Data Storage** | `development/src/data_manager.py` | Overwrite-on-save, validation patterns |
| **Configuration** | `development/src/config_manager.py` | Fail-fast validation, no-defaults pattern |
| **Logging** | `development/src/api/conventions.py` | log_api_call() structured JSON logging |
| **Persona System** | `system_prompts/personas_config.json` + `system_prompts/*_system_prompt.txt` | Complete persona definition and prompts |
| **AI Integration** | `development/src/services/ai_gateway.py` | OpenRouter API calls, persona loading |
| **Streaming Chat** | `development/src/streaming.py` | Multi-persona concurrent responses |
| **Frontend/UI** | `development/src/static/index.html` | Status displays, event handling, UI components |
| **UI Status System** | `docs/ui_status_system.md` | Progressive status, budget display, streaming |
| **Chat History** | `docs/chat-history-limits.md` | Sliding window, capacity limits, context management |

---

### 🔍 Pattern Decision Tree

**"I need to add a new feature..."**

```
START: What type of feature?
│
├─ New API endpoint for data storage?
│  └─ Copy: development/src/api/vision.py
│     • Change: storage directory, request/response models
│     • Keep: action pattern (save/get/list/delete/latest)
│     • Keep: unified response format
│
├─ New AI persona or role?
│  └─ Edit: system_prompts/personas_config.json
│     • Add new persona object and system_prompt_file reference
│     • Create or update corresponding `*_system_prompt.txt` file
│     • No Python code changes needed
│
├─ New configuration option?
│  ├─ Human-editable? → Add to JSON config file
│  ├─ Deployment-specific? → Add to environment variable
│  └─ Remember: NO DEFAULTS, fail fast if missing
│
├─ New data validation?
│  └─ Check: development/src/data_manager.py
│     • Use existing ValidationResult pattern
│     • Add validation method to DataManager class
│
└─ New meeting type or workflow?
   └─ Update: personas configuration and prompts
      • Add meeting detection keywords in the relevant persona system prompt files
      • Adjust meeting behavior in those prompts as needed
      • No Python routing logic needed
```

---

### 🎓 Example Walkthrough: Adding "Design Review" Feature

Let's walk through adding a complete new feature to demonstrate the patterns:

**Goal**: Add a design review feature where designers can submit and review UI designs.

**Step 1: Create API Endpoint**
```bash
cp development/src/api/vision.py development/src/api/design_review.py
```

**Step 2: Customize the File**
```python
# development/src/api/design_review.py
"""
Design Review API - Handle creation, storage, and retrieval of design review documents.
Mirrors vision.py pattern exactly.
"""

# Change storage location
DESIGN_DIR = Path("static/appdocs/design_reviews")
DESIGN_DIR.mkdir(parents=True, exist_ok=True)

# Change models
class DesignReviewRequest(BaseModel):
    action: str  # "save", "get", "list", "delete", "latest"
    design_name: Optional[str] = None
    design_content: Optional[str] = None
    approved: Optional[bool] = False
    design_id: Optional[str] = None

class DesignReviewResponse(BaseModel):
    success: bool
    message: str
    design_id: Optional[str] = None
    content: Optional[str] = None
    designs: Optional[List[Dict]] = None

# Update all function names and references
@router.post("/design-review", response_model=DesignReviewResponse)
async def handle_design_review_request(request: DesignReviewRequest):
    # ... (copy pattern from vision.py)
```

**Step 3: Register in main.py**
```python
# development/src/main.py
from api.design_review import router as design_review_router
app.include_router(design_review_router)
```

**Step 4: Add Designer Persona (if needed)**
```json
// system_prompts/personas_config.json
{
  "personas": {
    "DESIGNER": {
      "name": "Jamie",
      "display_name": "Jamie · Designer",
      "role": "UI/UX Designer",
      "role_key": "DESIGNER",
      "system_prompt_file": "system_prompts/DESIGNER_system_prompt.txt",
      "enabled": true,
      "priority": 6,
      "tools": ["http_post"]
    }
  }
}
```

**Step 5: Test**
```bash
curl -X POST http://localhost:8000/api/design-review \
  -H "Content-Type: application/json" \
  -d '{"action": "save", "design_name": "Login Page", "design_content": "..."}'
```

**That's it!** No framework changes, no complex setup. Just copy the pattern and customize.

---

### 💡 Quick Decision Reference

**"Should I...?"**

| Question | Answer | Reference |
|----------|--------|-----------|
| Add a default value? | ❌ NO - Fail fast instead | config_manager.py line 89-92 |
| Create custom response format? | ❌ NO - Use conventions.py | conventions.py line 123-134 |
| Store files outside static/appdocs/? | ❌ NO - Use standard location | vision.py line 19-20 |
| Add persona logic in Python? | ❌ NO - Put in personas configuration | system_prompts/personas_config.json |
| Create new action types? | ❌ NO - Use standard actions | conventions.py line 30-37 |
| Hardcode a model name? | ❌ NO - Use config or request | models_config.json |
| Copy an existing pattern? | ✅ YES - Always check first | See Reference table above |
| Fail fast on missing config? | ✅ YES - Always for new features | config_manager.py line 70-88 |

---

## Implementation Timeline (Architecture Work)

These entries record when major architecture phases and supporting code/ADRs were introduced. The **current activation status** of each capability is summarized in [Capabilities and Activation Status](#capabilities-and-activation-status) and is also visible at runtime via `/api/env`.

- **2025-10-24**: Added chat history management architecture with frontend sliding window (19 messages), context management strategy for Vision PM persona, and comprehensive documentation of practical capacity limits by meeting type
- **2025-10-10**: Added comprehensive Developer Guide with patterns, anti-patterns, and step-by-step examples
- **2025-10-07**: Phase 6 implementation work completed (code + ADRs) - Documentation & validation framework with comprehensive architecture updates, security integration, and operational documentation
- **2025-10-07**: Phase 5 implementation work completed (code + ADRs) - Safety & security enhancement with multi-layer security architecture, rate limiting, input validation, and audit logging
- **2025-10-07**: Phase 4 implementation work completed (code + ADRs) - Configuration & environment standards with structured logging, environment management, and integration testing
- **2025-10-07**: Phase 3 implementation work completed (code + ADRs) - Data management standards with overwrite-on-save behavior, CSV schema validation, and comprehensive testing
- **2025-10-07**: Phase 2 implementation work completed (code + ADRs) - Fail-fast implementation with configuration validation, startup checks, and no-defaults policy
- **2025-10-07**: Phase 1 implementation work completed (code + ADRs) - API standardization with unified response envelopes, error codes, and refactored endpoints
- **2025-10-06**: Added comprehensive requirements workflow with wireframe generation, CSV validation, and UI integration
- **2025-09-17**: Added vision workflow with structured meeting lifecycle and persona switching

## Operational Reliability and Enhancements
> **Backlog Write-Through Safeguards**  
> _Added: 2025-11-12_  
> Backlog write-through safeguards operate at a per-story (row-scoped) level for sprint execution and review flows.  
> - Sprint Execution uses the orchestrator's `_update_backlog` to read the full CSV, validate headers, locate the matching `Story_ID`, update only that row's execution fields, and rewrite the file.  
> - Sprint Review and planning flows use the `/api/backlog/update-story` endpoint for row-level status/notes updates.  
> - Requirements-mode saves still use full-file writes, which is why independent backlog versioning remains recommended in `dataflow-and-schema.md`.  
> Validation and backup (via sprint-level snapshots of `Backlog.csv`) remain mandatory checks for all future refactors of the Sprint Execution pipeline.

### Sprint Execution Enhancements (2025-11-23)

Sprint Execution uses a **Sequential Orchestrator** pattern with four implementation phases:

**Phase 1: Context Injection + Validation**
- Alex sees existing project structure, file summaries, and code patterns
- Task breakdowns validated before proceeding
- Code syntax validated before writing to disk
- Suspicious imports detected and blocked
- Clear context headers added to persona calls (role, story, attempt, specific job)

**Phase 2: Merge Logic + Test Execution**
- Existing files are merged (not overwritten) using smart Python AST parsing
- Backup files (.bak) created before any modifications
- Tests actually execute via appropriate framework (Node.js test runner, pytest, etc.)
- Real pass/fail results logged
- Jordan writes 1-2 smoke tests only (not comprehensive tests)

**Phase 3: Stack-Agnostic Dependency Installation**
- Mike specifies install commands in task breakdown via `command_to_run` field
- Orchestrator executes any command (npm install, pip install, mvn install, etc.)
- Proper error logging and stop-on-failure for install commands
- No hardcoded stack-specific logic in orchestrator

**Phase 4: Backup/Rollback**
- Story-level file tracking for granular rollback
- Automatic rollback on test failures
- Sprint-level snapshots created before execution starts
- Failed stories marked in backlog, execution continues to next story

**Key Methods** (in `development/src/services/sprint_orchestrator.py`):
- Context: `_get_project_context()`, `_get_file_summaries()`, `_get_existing_patterns()`
- Validation: `_validate_task_breakdown()`, `_validate_syntax()`, `_validate_imports()`
- Merge: `_merge_code()`, `_backup_existing()`, `_write_code_files()`
- Commands: `_execute_task_command()` (stack-agnostic command execution)
- Testing: `_run_tests()`
- Rollback: `_track_story_files()`, `_rollback_story()`, `_create_backup()`

**Architectural Patterns Enforced**:
- **Server Testability**: HTTP servers export app object, conditionally start only when run directly
- **Smoke Testing**: Jordan writes 1-2 tests max, uses direct imports, no spawn/exec
- **Stack-Agnostic**: Works for Node.js, Python, Java, Ruby, Go, etc.
- **Complete Specifications**: Mike provides 10 architectural categories in NFR-001

See [PATTERNS_AND_METHODS.md](./PATTERNS_AND_METHODS.md#sprint-execution-method-sequential-orchestrator) for implementation details and testing checklist.
See [DESIGN_PRINCIPLES.md](./DESIGN_PRINCIPLES.md) for the Sequential Orchestrator, Row-Scoped Updates, and Hard Gates principles.

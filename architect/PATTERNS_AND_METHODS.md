# Patterns and Methods: The Developer's Working Reference

Status: Canonical
Audience: Developers
**Purpose**: Single source of truth for "how we do things" in AI-DIY. Read this before coding to prevent spaghetti code.
**Last Updated**: January 7, 2026
Related: [architecture.md](./architecture.md) · [GOVERNANCE.md](./GOVERNANCE.md)

---

## How to Maintain This Document

**Principle**: Documentation explains *why* and *when*, code shows *what*. Don't duplicate code here.

**When updating a section:**
1. **Verify against actual code** - Read the source files, not just the docs
2. **Keep examples minimal** - 3-5 lines max to illustrate a concept
3. **Point to code, don't copy it** - Use "See `file.py:function_name()`" references
4. **Remove stale details** - Line numbers, full implementations, anything that will drift
5. **Focus on decisions** - Why this pattern? What problem does it solve? What are the gotchas?

**Each pattern section should have:**
- **When to use**: The problem this pattern solves
- **Why**: The reasoning behind the approach
- **Where**: File/function references (not copied code)
- **Common Mistakes**: What NOT to do

**Each pattern section should NOT have:**
- Full function implementations (read the code instead)
- Line numbers (they go stale)
- Details that duplicate what `grep` would show you

**To audit this document:** Compare each section against Railway production code. If the doc says X but the code does Y, update the doc (or flag the code as wrong).

---

## Always Rules

✅ **ALWAYS** fail fast with clear error messages  
✅ **ALWAYS** check for existing patterns before coding  
✅ **ALWAYS** use the unified API response format  
✅ **ALWAYS** store configuration in JSON for human-editable settings  
✅ **ALWAYS** explain intended changes and wait for confirmation before implementing  
✅ **ALWAYS** follow governance (propose → discuss → approve → implement)  

---

## Table of Contents

1. [Guiding Philosophy](#guiding-philosophy)
2. [Quick Starts](#quick-starts)
3. [Data Storage Patterns](#data-storage-patterns)
4. [Persona Patterns](#persona-patterns)
5. [API Patterns](#api-patterns)
6. [Generated App Routing Patterns](#generated-app-routing-patterns)
7. [Logging Patterns](#logging-patterns)
8. [Context Injection Patterns](#context-injection-patterns)
9. [File Modification Patterns](#file-modification-patterns)
10. [Configuration Patterns](#configuration-patterns)
11. [Meeting Patterns](#meeting-patterns)
12. [Always Rules](#always-rules)

---

## Methodology Index

- Cascade-Style Context Injection (Scoped: Sprint Review Alex) → [Pattern link](#pattern-cascade-style-context-regular-conversations)
- Investigation + Execution Mode (Scoped: Sprint Review Alex) → [Pattern link](#pattern-sprint-review-alex-investigation--execution)
- Sprint Execution Method (Sequential Orchestrator) → [Pattern link](#sprint-execution-method-sequential-orchestrator)

---

## Guiding Philosophy

- **Copy, Don’t Create**: Reuse established patterns. Start by copying `vision.py` or `backlog.py` for APIs; copy existing persona JSON for new personas.
- **Fail Fast for Critical Config**: API keys and model names must be explicit - raise clear errors if missing. Sensible defaults are allowed for local dev convenience (paths, ports, log levels).
  ```python
  # ✅ Good - critical config fails fast
  api_key = os.getenv("OPENROUTER_API_KEY")
  if not api_key:
      raise ValueError("Missing required config: OPENROUTER_API_KEY")

  # ✅ OK - sensible defaults for local dev
  log_level = os.getenv("LOG_LEVEL", "INFO")
  personas_path = os.getenv("PERSONAS_PATH") or "system_prompts/personas_config.json"

  # ❌ Bad - silent default for critical operational config
  model = os.getenv("MODEL_NAME", "some-random-model")
  ```
- **Personas in Config, Not Code**: All AI behavior lives in configuration, not Python code. Persona metadata lives in `system_prompts/personas_config.json`; system prompts live in `system_prompts/*_system_prompt.txt`. Keep Python free of persona logic.

---

## Quick Starts

### Add a New API Endpoint (5 steps)

1) Copy the gold standard pattern
```bash
cp development/src/api/vision.py development/src/api/sprint.py
```

2) Edit `sprint.py` — change these
- `VISION_DIR` → `SPRINT_DIR = Path("static/appdocs/sprints")`
- `VisionRequest` → `SprintRequest`
- `VisionResponse` → `SprintResponse`
- Update function names/docstrings and router prefix: `@router.post("/api/sprint")`

3) Register in `main.py`
```python
from api.sprint import router as sprint_router
app.include_router(sprint_router)
```

4) Test it
```bash
curl -X POST http://localhost:8000/api/sprint \
  -H "Content-Type: application/json" \
  -d '{"action": "save", "title": "Sprint 1", "content": "..."}'
```

5) Done — framework handles validation, responses, logging

Key pattern: use unified response format
```python
from api.conventions import create_success_response, create_error_response
return create_success_response(message="Saved", data={"id": id_value})
```

### Add a New Persona (simple process)

Add this under `personas` in `system_prompts/personas_config.json` and create a matching prompt file:

```json
"DESIGNER": {
  "name": "Jamie",
  "display_name": "Jamie · Designer",
  "role": "UI/UX Designer",
  "role_key": "DESIGNER",
  "system_prompt_file": "system_prompts/DESIGNER_system_prompt.txt",
  "enabled": true,
  "priority": 6,
  "tools": ["http_post"],
  "inject_context": ["vision", "backlog"],
  "meeting_triggers": []
}
```

And in `system_prompts/DESIGNER_system_prompt.txt`:

```text
You are Jamie, the Designer persona...
[full prompt text]
```

Notes:
- Same person, multiple roles: e.g., Sarah has `PM`, `VISION_PM`, `REQUIREMENTS_PM`.
- Keep behavior in JSON; avoid Python conditionals per persona.

---

## Data Storage Patterns

### Decision Tree: Which Pattern to Use?

```
Need to store data?
├─ Single canonical document? → Living Document with Backups (Vision)
├─ Tabular data with rows? → Living Document CSV (Backlog)
└─ Need rollback? → Both patterns include rotating backups
```

### Pattern: Living Document with Backups (Vision)

**When to use**: Single canonical document that evolves over time

**Why**: Simple single source of truth, with backups for recovery

**Where**: `api/vision.py`, `static/appdocs/visions/vision.json`

**The Pattern**:
- Fixed canonical file: `vision.json` (ID is always `"vision"`)
- Timestamped backups created on each save: `backups/vision_YYYYMMDD_HHMMSS.json`
- Markdown version maintained for readability: `vision.md`

**Key Points** (see `api/vision.py:save_vision()`):
- `vision_id = "vision"` - fixed, not generated
- Backups go to `visions/backups/` subdirectory
- `client_approval` flag tracked in the document

**Common Mistakes**:
- ❌ Creating timestamped IDs for the main file (Vision is single source of truth)
- ❌ Storing outside `static/appdocs/` (breaks data management)
- ❌ Skipping backup before overwrite (loses history)

---

### Pattern: Living Document CSV (Backlog)

**When to use**: Single evolving document where all items are rows

**Why**: Simpler than versioning, easier to search/filter, natural for tabular data

**Where it's used**: `/development/src/api/backlog.py`, `static/appdocs/backlog/Backlog.csv`

**The Pattern**:
- One file containing all items (rows in CSV)
- Fixed ID: `Backlog.csv` (single, consistent)
- Individual items identified by column (e.g., Story_ID)
- Related assets in subdirectory: `wireframes/`

**How to Apply It**:
```python
import csv
backlog_path = Path("static/appdocs/backlog/Backlog.csv")
# Read, modify in memory, overwrite entire file
```

**Common Mistakes**:
- ❌ Creating new file for each update (defeats purpose)
- ❌ Not overwriting, just appending (creates duplicates)
- ❌ Storing wireframes in root (messy)

---

## Persona Patterns

### Decision Tree: Which Persona Pattern?

```
Need a persona?
├─ Same person, different contexts? → Multiple Personas Per Person
├─ Multiple personas in one meeting? → Meeting Personas with Role Mapping
├─ Track AI behavior? → Configuration-Driven Personas
└─ Hidden persona for background? → Scribe Isolation Pattern
```

### Pattern: Single Person, Multiple Personas

**When to use**: Same person (Sarah) needs different behavior in different contexts

**Why**: Keeps config clean, avoids duplicate prompts, enables context-specific behavior

**Where it's used**: Sarah has 6 personas for different contexts:
- `PM` - General project management
- `VISION_PM` - Vision meeting facilitator
- `REQUIREMENTS_PM` - Requirements/backlog meeting facilitator
- `SPRINT_PLANNING_ARCHITECT` - (Mike, not Sarah, but same pattern)
- `SPRINT_REVIEW_PM` - Sprint review facilitator
- `SPRINT_EXECUTION_PM` - Sprint execution facilitator

**The Pattern** (see `system_prompts/personas_config.json`):
```json
"PM": { "name": "Sarah", "role": "Project Manager (PM)", "meeting_triggers": [] },
"VISION_PM": { "name": "Sarah", "meeting_triggers": ["start vision meeting"], "solo_mode": true },
"REQUIREMENTS_PM": { "name": "Sarah", "meeting_triggers": ["start requirements meeting"], "solo_mode": true }
```

**Common Mistakes**:
- ❌ Creating separate people (breaks continuity)
- ❌ Duplicating system prompts (hard to maintain)
- ❌ Forgetting meeting_triggers (persona never activates)

---

### Pattern: Meeting Personas with Role Mapping

**When to use**: Multiple personas active in same meeting (Sarah + Alex in Sprint Review)

**Why**: Enables debugging during meetings without breaking solo_mode

**Where it's used**: Sprint Review has `SPRINT_REVIEW_PM` + `SPRINT_REVIEW_ALEX`

**The Pattern**:
```json
"DEVELOPER": { "persona_role": "developer_alex" },
"SPRINT_REVIEW_ALEX": { "persona_role": "developer_alex" },
"SPRINT_REVIEW_PM": {
  "additional_meeting_personas": ["SPRINT_REVIEW_ALEX"],
  "persona_role_mapping": { "developer_alex": "SPRINT_REVIEW_ALEX" }
}
```

**How It Works**:
1. User checks "Alex" box → System sees `persona_role: "developer_alex"`
2. Meeting config maps "developer_alex" → "SPRINT_REVIEW_ALEX"
3. Alex joins as SPRINT_REVIEW_ALEX in Sprint Review

**Common Mistakes**:
- ❌ Different persona_role values (mapping won't work)
- ❌ Forgetting additional_meeting_personas (persona never joins)
- ❌ Using different names (confuses user)

---

### Pattern: Configuration-Driven Personas

**When to use**: All AI behavior should live in config, not Python code

**Why**: Non-coders can modify behavior, easier to maintain

**Where it's used**: `system_prompts/personas_config.json` (metadata + config) + `system_prompts/*_system_prompt.txt` (actual prompts)

**The Pattern** (actual field names from config):
```json
{
  "PERSONA_KEY": {
    "name": "Sarah",
    "display_name": "Sarah · Project Manager",
    "role": "Project Manager (PM)",
    "role_key": "PERSONA_KEY",
    "system_prompt_file": "system_prompts/PM_system_prompt.txt",
    "enabled": true,
    "priority": 1,
    "tools": ["http_post"],
    "inject_context": ["vision", "backlog"],
    "meeting_triggers": ["start vision meeting"],
    "solo_mode": true
  }
}
```

**Key Fields**:
- `system_prompt_file` - Path to .txt file with full prompt (NOT inline `system_prompt`)
- `persona_role` - Used for meeting role mapping (e.g., `"developer_alex"`)
- `solo_mode` - When true, only this persona responds in meeting context
- `inject_context` - Which documents to inject (vision, backlog, sprint_log, etc.)

**Common Mistakes**:
- ❌ Hardcoding persona logic in Python (defeats purpose)
- ❌ Forgetting `enabled: true` (persona won't load)
- ❌ Using inline `system_prompt` instead of `system_prompt_file` (actual config uses file references)

---

### Pattern: Scribe Isolation During Meetings

**When to use**: Scribe should record during conversations but NOT during meetings

**Why**: Meetings are real team discussions, Scribe shouldn't interfere

**Where it's used**: All meeting personas have `scribe_active_during_meeting: false`

**The Pattern**:
```json
"SPRINT_REVIEW_PM": { "scribe_active_during_meeting": false },
"SCRIBE": { "meeting_triggers": [] }
```

**Common Mistakes**:
- ❌ Forgetting the flag (Scribe responds during meetings)
- ❌ Giving Scribe meeting_triggers (Scribe auto-joins meetings)

---

## Architect Design Specifications (Mike's 5-Phase Pattern)

### Pattern: Complete Design Output for Incremental Development

**When to use**: Every story in Sprint Execution requires Mike (Architect) to design the system before Alex (Developer) implements

**Why**: Prevents missing dependencies, duplicate code, schema conflicts, and incomplete implementations. Enables incremental development where each story extends existing code rather than recreating it.

**Where it's used**: `SPRINT_EXECUTION_ARCHITECT` persona configured in `system_prompts/personas_config.json`, executed during Sprint Execution

**The 5-Phase Design Process**:

#### Phase 1: Analyze Project State
Mike receives current project state:
- Existing database schema (tables, fields, types)
- Existing API endpoints (methods, paths, response formats)
- Existing file structure (controllers, models, routes, components)
- Established code patterns (error handling, async/await, response format)

**Mike's responsibility**: Study this context to extend existing code, not recreate it.

#### Phase 2: Design the System
Mike outputs 5 design sections:

1. **Database Design** - NEW tables and MODIFIED tables with exact field specifications
2. **API Design** - NEW endpoints and MODIFIED endpoints with request/response formats
3. **File Structure** - Which files to create and which to modify
4. **Code Patterns** - How this follows established patterns (error handling, async/await, response format)
5. **Dependencies** (CRITICAL) - ALL npm/pip packages required with versions and dev/regular classification

**Why Dependencies Matter**:
- Alex uses this to update `package.json`
- Missing dependencies cause runtime errors (`MODULE_NOT_FOUND`)
- Must include versions (e.g., `jsonwebtoken@^9.1.2`, `bcrypt@^5.1.1`)

#### Phase 3: Break Down into Tasks
Mike creates 3-10 concrete tasks with:
- **task_id**: Formatted as `T-{STORY_ID}-{TASK_NUMBER}` (e.g., `T-US-009-01`)
- **description**: Clear, specific description
- **files_to_create**: ALWAYS list concrete file paths (never empty)
- **dependencies**: Task IDs that must complete first
- **dependency_reason**: Explain WHY (e.g., "depends on T-US-009-01 because database schema must exist first")

**Example Mike Output**:
```json
{
  "story_id": "US-009",
  "database_design": {
    "new_tables": [
      {
        "name": "leave_requests",
        "fields": [
          {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
          {"name": "employee_id", "type": "INTEGER NOT NULL"},
          {"name": "start_date", "type": "TEXT NOT NULL"},
          {"name": "status", "type": "TEXT DEFAULT 'pending'"}
        ]
      }
    ],
    "modified_tables": []
  },
  "api_design": {
    "new_endpoints": [
      {
        "method": "POST",
        "path": "/api/leave",
        "request": "{employee_id, start_date, end_date}",
        "response": "{id, status, created_at}"
      }
    ],
    "modified_endpoints": []
  },
  "code_patterns": {
    "error_handling": "Use try/catch blocks like authController.js",
    "async_pattern": "Use async/await like existing routes",
    "response_format": "Return res.status(code).json({success, data, error})"
  },
  "dependencies": {
    "dependencies": {
      "express": "^4.18.2",
      "jsonwebtoken": "^9.1.2",
      "bcrypt": "^5.1.1"
    },
    "devDependencies": {
      "jest": "^29.7.0"
    }
  },
  "tasks": [
    {
      "task_id": "T-US-009-01",
      "description": "Create leave_requests table with schema",
      "files_to_create": ["src/server/models/leaveSchema.sql"],
      "dependencies": [],
      "dependency_reason": "No dependencies - this is the foundation"
    },
    {
      "task_id": "T-US-009-02",
      "description": "Implement POST /api/leave endpoint",
      "files_to_create": ["src/server/controllers/leaveController.js", "src/server/routes/leave.js"],
      "dependencies": ["T-US-009-01"],
      "dependency_reason": "Depends on T-US-009-01 because database schema must exist first"
    }
  ],
  "technical_notes": "Inferred tech stack: Node.js Express backend, SQLite database, JWT auth. All code follows existing patterns."
}
```

**Enforcement**:
- Sprint orchestrator validates task ID format
- Alex validates all dependencies are in `package.json` before marking tasks complete
- Self-healing detects 0-file tasks and retries Mike
- Execution logs show task quality metrics

**Common Mistakes**:
- ❌ Mike outputs only tasks without design sections (Alex lacks context)
- ❌ Missing dependencies section (causes runtime errors)
- ❌ Recreating existing tables instead of modifying (schema conflicts)
- ❌ Tasks with 0 files (too abstract, not implementable)
- ❌ Task IDs not zero-padded (T-US-009-1 instead of T-US-009-01)

---

## API Patterns

### Pattern: Unified Response Format

**When to use**: Every API endpoint should return consistent format

**Why**: Frontend knows what to expect, easier to debug

**Where it's used**: `/development/src/api/conventions.py`

**The Pattern**:
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { "id": "value", "status": "ok" }
}
```

**How to Apply It**:
```python
from api.conventions import create_success_response, create_error_response, ApiErrorCode
return create_success_response(message="Saved", data={"id": id_value})
return create_error_response(message="Not found", error_code=ApiErrorCode.NOT_FOUND)
```

**Common Mistakes**:
- ❌ Custom response formats (frontend breaks)
- ❌ Not using conventions.py (duplicates code)

---

### Pattern: API Endpoint Structure

**When to use**: Adding new API endpoint

**Why**: Consistent structure, easier to maintain

**Where it's used**: Copy `/development/src/api/vision.py` as template

**How to Apply It**:
1. Copy vision.py as template
2. Update: prefix, request class, action handlers
3. Register in main.py: `app.include_router(myresource_router)`
4. Test: `curl -X POST http://localhost:8000/api/myresource ...`

**Common Mistakes**:
- ❌ Not copying pattern (invents new structure)
- ❌ Forgetting to register in main.py (endpoint not accessible)
- ❌ Hardcoding paths (breaks on deployment)

---

## Generated App Routing Patterns

### Overview

Generated apps must work in **two environments without code changes**:
- **Local (Mac)**: `http://localhost:3000` - direct access
- **Railway**: `https://<host>/yourapp/` - behind Caddy proxy that strips `/yourapp/` prefix

This section defines the mandatory routing patterns that make this work.

### The Proxy Problem

On Railway, Caddy's `handle_path /yourapp/*` directive:
1. Receives request: `/yourapp/api/auth/login`
2. **Strips** `/yourapp/` prefix
3. Forwards to Express: `/api/auth/login`

The app **never sees** `/yourapp/` in any request. This means:
- Server-side code is identical for both environments
- Client-side paths must be **relative** (no leading `/`) so they resolve correctly from the current URL

### Non-Negotiable Rules

**Rule 0: No environment detection**
- ❌ No `apiPrefix`, `BASE_PATH`, `isRailway` variables
- ❌ No `window.location.pathname` prefix hacks
- ✅ Same code runs everywhere

**Rule 1: Never use `<base>` tags**
- ❌ `<base href="/">` breaks Railway (forces URLs to root)
- ❌ `<base href="/yourapp/">` breaks Mac (path doesn't exist)
- ✅ Relative paths work in both without `<base>`

**Rule 2: Server-side vs Client-side path styles**

| Context | Path Style | Example |
|---------|------------|---------|
| Express routes | Absolute (with `/`) | `app.get('/login', ...)` |
| Server redirects (HTML) | Absolute (with `/`) | `res.redirect('/dashboard')` |
| Server redirects (JSON) | Relative (no `/`) | `res.json({ redirect: 'dashboard' })` |
| HTML links | Relative (no `/`) | `href="dashboard"` |
| HTML forms | Self-submit | `action="#"` |
| JavaScript fetch | Relative (no `/`) | `fetch('api/auth/login')` |

**Rule 3: API namespace is mandatory**
- All data endpoints under `/api/*`
- Auth endpoints under `/api/auth/*`
- Prevents collisions with page routes

**Rule 4: Flat pages only**
- ✅ `/login`, `/dashboard`, `/employees`
- ❌ `/employees/123`, `/dashboard/settings`
- Use query strings for details: `/employees?id=123`

**Rule 5: No trailing slashes**
- ✅ `/employees`
- ❌ `/employees/`

### Pattern: Client-Side Navigation and API Calls

```html
<!-- HTML links - RELATIVE, no leading / -->
<a href="dashboard">Dashboard</a>
<a href="employees">Employees</a>

<!-- Forms - ALWAYS action="#" with JS fetch -->
<form action="#" method="POST">
  <input name="email" type="email">
  <button type="submit">Login</button>
</form>

<script>
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const data = Object.fromEntries(formData);

  // Fetch - RELATIVE path, no leading /
  const response = await fetch('api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data)
  });
  const result = await response.json();

  if (result.success) {
    // Redirect value from server is RELATIVE
    window.location.href = result.redirect;
  }
});
</script>
```

### Pattern: Server-Side Routes and Responses

```javascript
// Route definitions - ABSOLUTE paths
app.get('/login', (req, res) => {
  res.redirect('/login.html');  // Absolute - Caddy rewrites for Railway
});

app.get('/dashboard', isAuthenticated, (req, res) => {
  res.redirect('/dashboard.html');
});

// API mount points
app.use('/api/auth', authRouter);  // Auth at /api/auth/*
app.use('/api', dataRouter);       // Data at /api/*

// In authRouter - paths relative to mount point
router.post('/login', async (req, res) => {
  // ... validate user ...
  // JSON redirect - RELATIVE (consumed by client JS)
  res.json({ success: true, redirect: 'dashboard' });
});

router.post('/logout', (req, res) => {
  req.session.destroy(() => {
    res.json({ success: true, redirect: 'login' });
  });
});
```

### Pattern: File Serving (Standard Express)

```javascript
// Setup - use express.static
app.use(express.static('public'));

// Page routes - redirect to .html files
app.get('/login', (req, res) => {
  res.redirect('/login.html');
});

app.get('/dashboard', isAuthenticated, (req, res) => {
  res.redirect('/dashboard.html');
});
```

**Why redirect, not sendFile:**
- `express.static` handles file serving automatically
- No path calculations needed (`__dirname`, `..`, `path.join()`)
- Eliminates common mistakes with wrong directory traversal

### Pattern: Session Configuration

```javascript
app.use(session({
  secret: process.env.SESSION_SECRET || 'dev-secret',
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: false,    // Required - app is HTTP behind HTTPS proxy
    sameSite: 'lax',  // Required - prevents cookie blocking
    maxAge: 1800000
  }
}));
```

### Why Each Pattern Matters

| Pattern | Without It | Result |
|---------|------------|--------|
| Relative client paths | `fetch('/api/...')` | Request goes to FastAPI, not generated app |
| Absolute server redirects | `res.redirect('dashboard')` | Caddy can't rewrite Location header |
| Relative JSON redirects | `{ redirect: '/dashboard' }` | Client navigates to wrong URL on Railway |
| No `<base>` tag | `<base href="/">` | All relative URLs resolve from wrong root |
| `action="#"` forms | `action="/login"` | Form submits bypass Caddy on Railway |
| `secure: false` cookie | `secure: true` | Cookies rejected (HTTP behind HTTPS proxy) |

### Troubleshooting

**Symptom: "Works on Mac, 404 on Railway"**
- Check: Client using absolute paths (`/api/...`)
- Check: Trailing slash causing wrong relative resolution
- Fix: Use relative paths in all client-side code

**Symptom: "Infinite redirect loop"**
- Check: Session cookie `secure: true` or missing `sameSite`
- Fix: Set `secure: false, sameSite: 'lax'`

**Symptom: "Login works, but dashboard 404"**
- Check: JSON response has `redirect: '/dashboard'` (absolute)
- Fix: Use `redirect: 'dashboard'` (relative)

### Canonical Reference

The working example is the app on Railway at:
`/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp/`

---

## Logging Patterns

### Goals

- **Structured, queryable logs** for debugging, observability, and audits
- **Configurable verbosity** via environment variables
- **Safe handling of model payloads** with sampling and truncation

### Logging Layers

- **Core Application Logging** (`development/src/core/logging_config.py`)
  - Initialized on import; applies to the whole app
  - Writes structured JSONL to `development/src/logs/app.jsonl` with rotation
  - Sets up console logging with human-readable format at `LOG_LEVEL`

- **API Logging Middleware** (`development/src/logging_middleware.py`)
  - When importable, `development/src/main.py` calls `setup_structured_logging(app_config)` and attaches `logging_middleware`
  - Logs each `/api/...` request as a JSON line on logger `ai_diy.api`
  - In production, writes per-day JSONL files under a `logs/` directory

- **Model and User Activity Logging** (`development/src/core/logging_config.py`)
  - `log_openrouter_call(...)` – logs model calls with token counts, latency, status, optional hashes/payloads
  - `log_user_action(action, **kwargs)` – logs user activity when enabled

### Environment Configuration (Overview)

- **Verbosity**
  - `LOG_LEVEL` – `DEBUG`, `INFO`, `WARNING`, or `ERROR` (default `INFO`)

- **Model Call Logging**
  - `OPENROUTER_LOG_PAYLOADS` – `true/false`; when `true`, logs request/response payloads (with truncation)
  - `OPENROUTER_LOG_SAMPLE` – float between 0.0 and 1.0; sample rate for logging payloads
  - `OPENROUTER_LOG_MAX_CHARS` – maximum characters for payload / response fields

- **User Activity Logging**
  - `USER_LOG_ENABLED` – `true/false`; when `true`, enables `log_user_action`
  - `USER_LOG_ID` – identifier attached to user logs (e.g., `"anonymous"`, `"dev-ralph"`)
  - `USER_LOG_LEVEL` – minimum level for user logs (e.g., `INFO`)

### Usage Guidance

- **Local debugging**
  - Set `LOG_LEVEL=DEBUG` for more detail
  - Keep `OPENROUTER_LOG_PAYLOADS=false` unless you explicitly need payloads and are comfortable logging them

- **Normal development**
  - Use `LOG_LEVEL=INFO`
  - Optionally set a small `OPENROUTER_LOG_SAMPLE` (e.g., `0.05`) to log occasional payloads

- **Privacy-sensitive / production-like**
  - Keep `OPENROUTER_LOG_PAYLOADS=false`
  - Rely on token counts, status, and hashes for correlation
  - Use `USER_LOG_ENABLED` only when you have a clear purpose and safe storage for user logs

---

## Context Injection Patterns

### Decision Tree: Which Context Pattern?

```
Need to inject context?
├─ First turn? → Full context (system + backlog + sprint_log + history + user)
├─ Subsequent turns? → Lean context (system + history + user, skip static)
├─ Inside investigation loop? → Lean context (system + architecture + "INVESTIGATION MODE" + tool results)
├─ Inside execution loop? → Lean context (system + architecture + "EXECUTION MODE ACTIVATED" + investigation context + file contents)
└─ During meeting? → Meeting context (vision + backlog + sprint_log)
```

### Pattern: Cascade-Style Context (Regular Conversations)

**When to use**: Regular conversation with SPRINT_REVIEW_ALEX

**Why**: Reduces context size after first turn, improves response time

**Where it's used (code anchors)**:
- `services/ai_gateway.py` → history injection in `call_openrouter_api()`
- `services/streaming.py` → conditional skip of static context when history exists

**The Pattern**:
```
First Turn:
  - System prompt
  - Backlog (SENT ONCE)
  - Sprint log (SENT ONCE)
  - User message
  Size: ~8KB, Time: ~10s

Subsequent Turns:
  - System prompt
  - Conversation history (previous exchanges)
  - User message
  Size: ~4KB, Time: ~5s
  (Backlog and sprint_log NOT re-injected)
```

**How to Apply It**:
```python
# In streaming.py, check for conversation history
if not has_conversation_history:
    # Inject backlog and sprint_log
else:
    # Skip backlog and sprint_log, use history instead

# In ai_gateway.py, inject history into messages
if persona_key == "SPRINT_REVIEW_ALEX" and session_id:
    history_messages = get_conversation_history(session_id, persona_key, max_turns=3)
    messages = system_messages + history_messages + current_messages
```

**Common Mistakes**:
- ❌ Re-injecting static context every turn (context explosion)
- ❌ Not checking for conversation history (can't optimize)
- ❌ Losing conversation history (Alex can't reference previous turns)

---

### Pattern: Sprint Review Alex Investigation + Execution

**When to use**: SPRINT_REVIEW_ALEX debugging workflow

**Why**: Separates investigation (diagnose and propose) from execution (apply fix), prevents execution from drifting away from approved plan

**Where**: `services/ai_gateway.py:run_sprint_review_alex_execution_mode()` and `call_openrouter_api()`

**The Two Phases**:

1. **Investigation Phase** (tool-based)
   - Alex uses `list_directory` and `read_file` tools to diagnose
   - Proposes a fix and lists files to modify
   - Waits for user approval

2. **Execution Phase** (backend-orchestrated, NO tools)
   - Triggered by approval phrases: "yes", "fix it", "go ahead", etc.
   - Backend reads file contents from sandbox
   - Backend calls `run_sprint_review_alex_execution_mode()` which:
     - Extracts approved plan from Alex's last response
     - Builds `APPROVED_CHANGE_SPEC` with file paths
     - Calls LLM once with NO tools, expects JSON response
     - Backend applies changes via sandbox write API

**Key Design Decision**: Execution uses JSON-only LLM response (no tool calls) to prevent drift from the approved plan.

**Common Mistakes**:
- ❌ Thinking execution still uses `write_text` tool (it doesn't - backend applies changes)
- ❌ Adding new features during execution (only apply the approved fix)
- ❌ Using file paths not in the approved plan (constrained by `APPROVED_CHANGE_SPEC`)
- ❌ Allowing testing in execution mode (leads to infinite bug loops)
- ❌ Not reinjecting investigation context into execution loop (agent forgets what to fix)

---

## Sprint Execution Method (Sequential Orchestrator)

**When to use**: Running sprint execution in development.

**Why**: Deterministic, observable workflow: plan → implement → test → log.

**Where it's used (code anchors)**:
- `services/sprint_orchestrator.py`
  - `SprintOrchestrator.run()` – main loop over stories
  - `_call_mike()` – task breakdown (execution architect)
  - `_call_alex()` – code generation (execution developer)
  - `_call_jordan()` – test generation (execution QA)
  - `_write_code_files()` / `_write_test_file()` – file outputs
  - `_log_event()` – JSONL event logging
  - `_update_backlog()` – updates Backlog.csv

**How to Apply It**:
1. Create a sprint plan JSON at `static/appdocs/sprints/Sprint-{id}.json` with `stories: [Story_ID...]`.
2. Start execution (background task) with that `sprint_id`.
3. Orchestrator flow per story:
   - Mike breaks down story into tasks → log `mike_breakdown`.
   - Alex implements tasks → writes files to `execution-sandbox/client-projects/{safe_name}` → log `alex_implemented`.
   - Jordan generates tests → writes test file → log `jordan_tested`.
   - Update Backlog.csv status/fields via `_update_backlog()`.
4. Meeting protocol: Sarah announces start/end messages in chat.
5. Summary logged at completion; plan JSON updated to `status: completed`.

**Guardrails**:
- Use `core.project_metadata.get_project_name_safe()` for paths.
- Write files under `execution-sandbox/client-projects/{safe_name}` only.
- Fail gracefully if Backlog.csv or vision is missing; log and continue.

**Verification checklist**:
- After execution: files exist in execution-sandbox; tests file created.
- Backlog.csv shows updated fields for each Story_ID processed.
- `static/appdocs/sprints/execution_log_{sprint_id}.jsonl` contains chronological events.

### Implementation Phases

#### Phase 1: Context Injection + Validation ✅ IMPLEMENTED

**Purpose**: Alex sees existing code and can import from it. Task 2 knows what Task 1 created. Syntax errors caught before disk write.

**Methods**:
- `_get_project_context()` - Maps project file structure (directories, files, sizes)
- `_get_file_summaries()` - Summarizes existing Python files (classes, functions, imports)
- `_extract_code_summary()` - Parses AST to extract code elements
- `_get_existing_patterns()` - Identifies established patterns (Flask app, blueprints, templates)
- `_validate_task_breakdown()` - Validates Mike's JSON output structure
- `_validate_syntax()` - Checks Python syntax using `ast.parse()` before writing
- `_validate_imports()` - Detects suspicious imports (os.system, eval, exec, __import__)
- `_validate_files_syntax()` - Batch validation for all files in Alex's response

**Integration**:
- Context injected into Alex's prompt before each task
- Mike's breakdown validated before proceeding to Alex
- Syntax validated before `_write_code_files()` writes to disk

**Impact**:
- Cross-task dependencies work (Task 2 can import from Task 1)
- Hallucinations reduced (~50%) due to context awareness
- Syntax errors caught before writing (~90% detection rate)

#### Phase 2: Merge Logic + Test Execution ✅ IMPLEMENTED

**Purpose**: Existing files are merged (not overwritten). Tests actually run and verify code works.

**Methods**:
- `_merge_code()` - Smart Python merging using AST (adds new functions/classes, preserves existing)
- `_backup_existing()` - Creates .bak files before modifying
- `_run_tests()` - **Actually executes pytest subprocess** (lines 445-503)
  - Runs: `pytest <test_path> -v --tb=short`
  - Parses real stdout/stderr for PASSED/FAILED counts
  - 60-second timeout
  - Returns actual pytest exit code
  - Handles pytest not installed gracefully
- `_write_code_files()` - Validates syntax → backs up → merges → writes → tracks files

**Integration**:
- Files backed up before modification
- Existing files merged (not overwritten)
- Tests execute after Jordan generates them via subprocess.run()
- Real test counts logged (parsed from pytest output, not fake)
- Test output captured and logged (first 1000 chars)

**Impact**:
- Task 2 won't overwrite Task 1's code
- Existing features preserved when adding new ones
- Tests verify code actually works (real pytest execution)
- Test failures detected immediately with accurate counts

#### Phase 3: Backup/Rollback ✅ IMPLEMENTED

**Purpose**: Failed stories don't leave partial state. Easy recovery from failures. Automatic rollback on test failure.

**Methods**:
- `_track_story_files()` - Tracks all files written during a story
- `_rollback_story()` - Reverts all changes for a failed story (lines 520-547)
  - Restores modified files from .bak backups
  - Removes newly created files (no backup)
  - Returns count of files removed
- `_create_backup()` - Creates snapshot before execution starts

**Automatic Rollback Trigger** (lines 747-763):
```python
if tests_failed > 0 and test_success == False:
    files_removed = self._rollback_story(story_id)
    await self._update_backlog(story_id, {
        "Execution_Status": "failed",
        "Last_Event": "tests_failed_rollback"
    })
    continue  # Skip to next story
```

**Integration**:
- Files tracked per story during write
- **Automatic rollback on test failure** (no manual intervention)
- Modified files restored from .bak backups
- New files removed completely
- Failed stories marked in backlog with "failed" status
- Sprint continues to next story after rollback
- Rollback event logged with files_removed count

**Impact**:
- Failed stories don't leave partial state
- Easy recovery from failures
- No manual cleanup needed
- Sprint doesn't stop on single story failure

### Testing Checklist

**Test 1: Simple New Features** (Validates Phase 1)
- Create sprint with 1 story, 2 tasks, separate files
- Verify context shows in logs
- Verify files created successfully
- Verify no syntax errors

**Test 2: Same File Modification** (Validates Phase 2)
- Create story with 2 tasks both modifying `app.py`
- Task 1: Add login route
- Task 2: Add dashboard route
- Verify both routes exist in app.py (no overwrite)
- Verify .bak file created

**Test 3: Cross-Task Dependencies** (Validates Phase 1)
- Task 1: Create `utils.py` with helper function
- Task 2: Import from utils.py and use it
- Verify Task 2 can see Task 1's exports
- Verify import works

**Test 4: Test Execution** (Validates Phase 2)
- Generate code with Jordan's tests
- Verify pytest actually runs
- Check logs show real pass/fail counts
- Verify not all tests marked as "passed"

**Test 5: Test Failure Rollback** (Validates Phase 3)
- Intentionally create code with bug
- Verify tests fail
- Verify rollback happens
- Verify files removed/restored
- Verify backlog marked as "failed"

### Known Limitations

1. **Pytest Required**: Test execution requires pytest installed. If not found, logs warning but continues.
2. **Python-Only Merge**: Smart merge only works for Python files. Other files are appended with separator comment.
3. **Simple Merge Logic**: Adds new functions/classes, doesn't handle function modifications. For that, Alex needs to generate complete replacement.
4. **Backup Cleanup**: .bak files accumulate. Could add cleanup routine if needed.
5. **Test Timeout**: Tests timeout after 60 seconds. Adjust if needed for slow tests.

**Backlog Update Rules (Backlog CSV Schema)**:
- Update the following fields as execution proceeds: `Execution_Status`, `Execution_Started_At`, `Execution_Completed_At`, `Last_Event`, `Last_Updated`.
- Keep Status lifecycle consistent across meetings: `Backlog` → `In Sprint` → `Done` or `Rejected` (Requirements/Planning/Review personas manage `Status`).
- See references:
  - `architect/BACKLOG_CSV_SCHEMA.md`
  - `architect/DATA_FLOW_BACKLOG_CSV.md`

**Common Mistakes**:
- ❌ Including conversation history in execution mode (hallucination)
- ❌ Re-injecting backlog/sprint_log in loop (wastes tokens)
- ❌ Not extracting current_user_message (gets confused by history)
- ❌ Overwriting files instead of merging (use Phase 2 merge logic)
- ❌ Not validating syntax before writing (use Phase 1 validation)
- ❌ Not running tests after writing (use Phase 2 test execution)

---

## File Modification Patterns

### Pattern: Safe File Modification (Merge, Don't Overwrite)

**When to use**: Modifying existing files (not creating new ones)

**Why**: Preserves existing code, prevents data loss, enables incremental changes

**Where it's used**: Sprint execution when modifying existing code

**The Pattern**:
1. Read existing file
2. Parse structure (functions, classes, imports)
3. Merge changes (add/update specific sections)
4. Validate syntax before writing
5. Write back to file
6. Run tests to verify

**How to Apply It**:
```python
# Read existing file
with open(file_path, 'r') as f:
    existing_content = f.read()

# Parse and identify sections to modify
# Merge new code with existing code
merged_content = merge_code(existing_content, new_code)

# Validate syntax
compile(merged_content, file_path, 'exec')

# Write back
with open(file_path, 'w') as f:
    f.write(merged_content)

# Run tests
run_tests()
```

**Common Mistakes**:
- ❌ Overwriting entire file (loses existing code)
- ❌ Not validating syntax (broken code written)
- ❌ Not running tests (bugs slip through)
- ❌ No rollback on failure (partial state left)

---

## Configuration Patterns

### Pattern: Configuration Decision Tree

**When to use**: Need to add configuration

**Why**: Consistent approach, prevents confusion

**The Pattern**:
```
Need configuration?
├─ Human-readable/editable? → JSON config file
├─ Deployment-specific? → Environment variable
├─ Secret (API key)? → Environment variable (never commit)
└─ Missing? → FAIL FAST with clear error
```

### Pattern: Fail-Fast Configuration

**When to use**: Configuration is missing or invalid

**Why**: Clear error messages, prevents silent failures

**Where it's used**: All config loading in `/development/src/`

**The Pattern**:
```python
# ❌ BAD: Silent default
model = os.getenv("MODEL_NAME", "default-model")

# ✅ GOOD: Fail fast
model = os.getenv("MODEL_NAME")
if not model:
    raise ValueError("Missing required config: MODEL_NAME")
```

**Common Mistakes**:
- ❌ Using silent defaults (hides bugs)
- ❌ Generic error messages (user confused)
- ❌ Not validating config at startup (bugs appear later)

---

## Meeting Patterns

### Pattern: Solo Mode with Additional Personas

**When to use**: Meeting needs multiple personas but one is primary

**Why**: Enables debugging/fixing during meetings without breaking solo_mode

**Where it's used**: Sprint Review has SPRINT_REVIEW_PM (primary) + SPRINT_REVIEW_ALEX (additional)

**The Pattern**:
```json
"SPRINT_REVIEW_PM": {
  "solo_mode": true,
  "additional_meeting_personas": ["SPRINT_REVIEW_ALEX"]
}
```

**How It Works**:
1. Meeting starts with SPRINT_REVIEW_PM
2. System checks additional_meeting_personas
3. Extends active_personas with SPRINT_REVIEW_ALEX
4. Both Sarah and Alex are active in meeting

**Common Mistakes**:
- ❌ Forgetting additional_meeting_personas (persona never joins)
- ❌ Setting solo_mode to false (breaks meeting structure)

---

## Quick Reference: When to Use Each Pattern

| I Need To... | Use This Pattern | Key File |
|---|---|---|
| Store canonical doc with backups | Living Document with Backups | `/development/src/api/vision.py` |
| Store tabular data (rows) | Living Document CSV | `/development/src/api/backlog.py` |
| Add new persona | Configuration-Driven Personas | `system_prompts/personas_config.json` |
| Same person, different contexts | Multiple Personas Per Person | `system_prompts/personas_config.json` |
| Multiple personas in meeting | Meeting Personas with Role Mapping | `system_prompts/personas_config.json` |
| Add new API endpoint | API Endpoint Structure | `/development/src/api/vision.py` |
| Modify existing file | Safe File Modification | Sprint orchestrator |
| Run sprint execution | Sprint Execution Method | `/development/src/services/sprint_orchestrator.py` |
| Inject context | Cascade-Style Context | `/development/src/services/ai_gateway.py` |
| Add configuration | Configuration Decision Tree | `.env` or `system_prompts/personas_config.json` |
| Handle errors | Error Handling | `/development/src/api/conventions.py` |

---

## Anti-Patterns: What NOT to Do

❌ **NEVER** use silent defaults for critical config (API keys, model names)  
❌ **NEVER** hardcode model names in code  
❌ **NEVER** store data outside `static/appdocs/`  
❌ **NEVER** put persona logic in Python (use configuration: `system_prompts/personas_config.json` + `system_prompts/*_system_prompt.txt`)  
❌ **NEVER** create custom response formats (use `conventions.py`)  
❌ **NEVER** create new patterns without checking existing ones first  
❌ **NEVER** overwrite files without merging (use safe modification)  
❌ **NEVER** re-inject static context every turn (use Cascade-style)  
❌ **NEVER** include conversation history in execution mode (use lean context)  
❌ **NEVER** write code without validating syntax first  

---

## How to Use This Document

1. **Before coding**: Find your use case in the decision trees
2. **During coding**: Follow the "How to Apply It" steps
3. **After coding**: Check "Common Mistakes" to catch issues
4. **When stuck**: Look at "Where it's used" to see real examples
5. **When extending**: Check "Related Patterns" for connected concepts

**Remember**: This document is your guide to keeping the codebase solid and consistent.

---

## Sprint Execution Persona Patterns

### Mike (Architect) - Task Breakdown Pattern

**Input**: Story with Acceptance Criteria (includes tech stack details)

**Mike's Job**:
1. **Infer tech stack** from acceptance criteria (don't assume, read what's provided)
   - Look for keywords: Node.js, Express, React, SQLite, Jest, etc.
   - Example: "Run entirely locally on macOS; Use SQLite as lightweight, file-based DB; Node.js v18+ backend with Express; React frontend"
2. **Break down into concrete tasks** (3-10 based on complexity)
   - Simple stories (1-2 screens): 3-4 tasks
   - Medium stories (3-5 screens, 2 layers): 5-7 tasks
   - Complex stories (multi-layer, infrastructure): 8-10 tasks
3. **Specify concrete files** for each task (never empty)
   - Include file extension: "src/server.js" not "src/server"
   - Each task creates 1-3 files minimum
   - If task has 0 files, it's too abstract - break it down or combine it
4. **Include install commands** using `command_to_run` field (stack-agnostic)
   - Node.js: `"command_to_run": "npm install"`
   - Python: `"command_to_run": "pip install -r requirements.txt"`
   - Java: `"command_to_run": "mvn install"`
   - Ruby: `"command_to_run": "bundle install"`
5. **Specify server testability** in NFR-001 (for HTTP apps)
   - Server modules must export app object
   - Pattern: `export const app = express(); if (import.meta.url === \`file://\${process.argv[1]}\`) { app.listen(port); }`
   - This allows Jordan to import and test without auto-start
6. **Explain dependencies** clearly
   - Include WHY each dependency exists
   - Example: "depends on T-NFR-001-01 because project structure must exist first"
   - Avoid circular dependencies

**Output Format** (JSON only):
```json
{
  "story_id": "NFR-001",
  "tasks": [
    {
      "task_id": "T-NFR-001-01",
      "description": "Initialize project structure with separate directories for backend and frontend",
      "files_to_create": ["src/server/.gitkeep", "src/client/.gitkeep", "package.json"],
      "dependencies": [],
      "dependency_reason": "No dependencies - this is the foundation"
    },
    {
      "task_id": "T-NFR-001-02",
      "description": "Configure backend Express server on port 3001 with SQLite database connection",
      "files_to_create": ["src/server.js", "src/models/db.js", "src/config/database.js"],
      "dependencies": ["T-NFR-001-01"],
      "dependency_reason": "Depends on T-NFR-001-01 because project structure must exist first"
    }
  ],
  "technical_notes": "Inferred tech stack from criteria: Node.js Express backend, React frontend, SQLite database"
}
```

**Task ID Format** (CRITICAL):
- Format: `T-{STORY_ID}-{TASK_NUMBER}` (e.g., `T-NFR-001-01`, `T-US-009-02`)
- TASK_NUMBER must be zero-padded two digits (-01, -02, not -1, -2)
- NOT: `T001`, `TASK-004`, `T-NFR-001-1`

**Enforcement**:
- Sprint orchestrator validates task ID format
- Self-healing detects 0-file tasks and retries Mike
- Execution logs show task quality metrics

---

### Alex (Developer) - Implementation Pattern

**Input**: Task with concrete description and files_to_create

**Alex's Job**:
1. Read task description and understand what to build
2. Read files_to_create list to know which files to generate
3. Generate complete, syntactically correct code
4. Output JSON with file paths and complete content

**Key Pattern**:
- Always generate COMPLETE files (not snippets)
- Include all imports, all functions, all classes
- For JavaScript/JSON: Orchestrator will REPLACE the file (no merging)
- For Python: Orchestrator will merge new functions/classes

**Output Format** (JSON only):
```json
{
  "files": [
    {
      "path": "src/server.js",
      "content": "const express = require('express');\nconst app = express();\n..."
    }
  ]
}
```

---

### Jordan (QA) - Smoke Test Pattern

**Input**: Story with Acceptance Criteria, task breakdown, Mike's architectural conventions

**Jordan's Job**: Write 1-2 SMOKE TESTS ONLY (not comprehensive tests)

**Critical Rules**:
1. ✅ Write EXACTLY 1-2 tests per story - NO MORE
2. ✅ Smoke tests verify code runs without crashing
3. ❌ DO NOT write comprehensive tests
4. ❌ DO NOT test every acceptance criterion
5. ❌ DO NOT test edge cases or error handling
6. ❌ DO NOT spawn child processes (spawn, exec, fork)
7. ❌ DO NOT parse log output to find ports

**Smoke Test Patterns by App Type**:

**Pattern 1: HTTP Server Apps (Node.js/Express)**
```javascript
test('Story - Server responds to main endpoint', async () => {
  // Import server directly (NOT spawn)
  const { app } = await import('../src/server.js');
  
  // Start on random port
  const server = app.listen(0);
  const port = server.address().port;
  
  try {
    // Make ONE request to main endpoint
    const response = await fetch(`http://localhost:${port}/`);
    assert.strictEqual(response.status, 200);
  } finally {
    // ALWAYS cleanup
    server.close();
  }
});
```

**Pattern 2: Database Apps**
```javascript
test('Story - Database initializes without errors', async () => {
  const { getDb, initDb } = await import('../src/db.js');
  const db = getDb();
  
  try {
    await initDb(db);
    // Simple check (optional)
    const count = await new Promise((resolve, reject) => {
      db.get('SELECT COUNT(*) as count FROM users', (err, row) => {
        if (err) reject(err);
        else resolve(row.count);
      });
    });
    assert.ok(count >= 0);
  } finally {
    await new Promise((resolve) => db.close(resolve));
  }
});
```

**Pattern 3: Combined (HTTP + Database)**
```javascript
test('Story - Server and database work together', async () => {
  // Setup database first
  const { getDb, initDb } = await import('../src/db.js');
  const db = getDb();
  await initDb(db);
  
  // Start server
  const { app } = await import('../src/server.js');
  const server = app.listen(0);
  const port = server.address().port;
  
  try {
    const response = await fetch(`http://localhost:${port}/api/endpoint`);
    assert.ok(response.status === 200 || response.status === 400);
  } finally {
    server.close();
    await new Promise((resolve) => db.close(resolve));
  }
});
```

**Output Format** (JSON only):
```json
{
  "test_file": "tests/test_NFR-001.test.js",
  "test_content": "import test from 'node:test';\nimport assert from 'node:assert';\n\ntest('NFR-001 - Database initializes', async () => {\n  // smoke test code\n});"
}
```

**Enforcement**:
- Jordan's prompt enforces 1-2 test maximum
- Forbids spawn/exec/fork and log parsing
- Requires direct imports and native test utilities
- Tests run with appropriate framework (Node.js test runner, pytest, etc.)
- Execution logs show test count and pass/fail results

---

## Event Tolerance Guidelines (SSE)

- Frontend should listen on default SSE `message` events unless backend explicitly sets `event:` names.
- Accept both event shapes:
  - Primary: `{ event_type, data }`
  - Fallback: `{ type, ... }` including `team_message` (with `persona`, `message`) and `sprint_complete` (close signal)
- Prefer `files_written` for counts; fall back to `files_count` when needed.
- For `mike_breakdown`, show `summary` or `task_count` when `summary` is absent.
- Recognize both `sprint_completed` and `sprint_complete` as sprint end.
- Do not rely on persona text formatting to trigger UI; use minimal phrases (e.g., Sarah’s “Sprint execution started for SP-XXX”) only to open streams; rely on structured events thereafter.

### Sprint Review Alex Execution Details

See [Pattern: Sprint Review Alex Investigation + Execution](#pattern-sprint-review-alex-investigation--execution) for the full pattern.

**Source of truth**: `services/ai_gateway.py:run_sprint_review_alex_execution_mode()`

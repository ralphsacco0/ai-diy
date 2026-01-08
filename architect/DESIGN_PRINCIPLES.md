# Design Principles

These are the core design principles that govern AI-DIY platform development. All changes must work within these principles.

---

## 1. Chat Is the Only User Interface

**The user interacts only through chat. All project artifacts are created and updated by the bots.**

Users don't edit files, run commands, or use dashboards. They talk to the team. Sarah, Mike, Alex, and Jordan handle everything: vision documents, backlog CSV, code files, tests, deployments.

**Why**: Non-coders can build software by having a conversation, not by learning tools.

---

## 2. Four People, Many Roles, Seamless Experience

**There are 4 base personas (Sarah PM, Mike Architect, Alex Developer, Jordan QA) plus a hidden Scribe. Each takes different specialized roles depending on meeting context, but to the user it looks like the same people doing context-appropriate work.**

- Same person, different prompts and tools per meeting type
- Vision Meeting Sarah ≠ Sprint Review Sarah (different prompts, different tools)
- Transitions happen automatically when meetings start/end
- User sees continuity; system handles the switching

**Implementation**: `personas_config.json` defines all role variants. Backend loads the right variant based on meeting state.

---

## 3. Safety-First: Snapshot Before Every Destructive Action

**Every potentially destructive operation takes a snapshot first. Users can always roll back.**

| When | What Gets Snapshotted | How to Roll Back |
|------|----------------------|------------------|
| Sprint plan saved | Backlog.csv, project files | UI: Sprint Plans → Rollback |
| Sprint execution starts | Full project state | UI: Sprint Plans → Rollback |
| Sprint Review Alex makes changes | Project files (.bak files) | Alex can restore via `restore_snapshot` tool |
| Vision saved | Previous vision.json | Timestamped backups in `visions/backups/` |
| Backlog full-file save | Previous state | Sprint-level snapshots; backlog versioning recommended |

**Why**: Users can experiment without fear. Bad changes are reversible.

**Implementation**:
- Sprint snapshots: `sprint_orchestrator.py` → `_create_backup()`
- Vision backups: `api/vision.py` → timestamped copies
- Alex rollback: `list_snapshots` and `restore_snapshot` tools

---

## 4. Fail-Fast Configuration

**No defaults. No silent fallbacks. Missing config crashes at startup.**

If a required environment variable or config value is missing, the app fails immediately with a clear error message. This prevents silent failures and makes configuration problems obvious.

**Implementation**: `config_manager.py` validates all required env vars on load.

---

## 2. Unified API Response Format

**All API endpoints return the same envelope: `{success, message, data}`**

```json
{"success": true, "message": "Vision saved", "data": {...}}
{"success": false, "message": "Story not found", "data": null}
```

No exceptions. Clients can always parse responses the same way.

**Implementation**: `api/conventions.py` defines Pydantic models for all responses.

---

## 3. Structured JSON-Line Logging

**All logs are JSON-line format with required fields. No `print()` or `console.log()`.**

Every log entry includes: timestamp, level, component, message, and correlation ID when available. This enables grep, jq, and log aggregation tools.

**Implementation**: `core/logging_config.py` configures structured logging.

---

## 4. Overwrite-on-Save (Living Documents)

**Save = replace entire file. No partial updates. No merge conflicts.**

Vision and Backlog are "living documents" - one canonical file that gets overwritten on each save. Vision gets timestamped backups for recovery. This is simpler than versioning.

**Implementation**: `api/vision.py` and `api/backlog.py` implement overwrite semantics.

---

## 5. Row-Scoped Backlog Updates

**When updating a single story, read the full CSV, update one row, write the full CSV.**

Never try to edit a CSV in place. The pattern:
1. Read entire `Backlog.csv`
2. Find the matching `Story_ID`
3. Update only that row's fields
4. Write entire file back

This prevents corruption and column misalignment.

**Implementation**: `_update_backlog()` in `sprint_orchestrator.py`

---

## 6. Sequential Orchestrator

**Stories execute one at a time: Mike (design) → Alex (code) → Jordan (test).**

No parallelism. Each story completes before the next begins. This makes debugging straightforward and keeps the system predictable.

**Why**: Parallel execution sounds faster but creates race conditions, interleaved logs, and hard-to-debug failures. Sequential is simpler and reliable.

**Implementation**: `sprint_orchestrator.py` processes stories in order.

---

## 10. Hard Gates in Sprint Review

**Sprint Review PM blocks progress until all tests pass.**

If Jordan reports test failures, Sprint Review PM does not allow marking stories as "Done". The user must either fix the issues or explicitly reject the story.

**Implementation**: `SPRINT_REVIEW_PM_system_prompt.txt` enforces this behavior.

---

## 11. Configuration-Driven Personas

**All personas are defined in JSON + text files. No Python code changes to add personas.**

- `system_prompts/personas_config.json` - metadata, tools, triggers
- `system_prompts/*_system_prompt.txt` - prompt content

One person (e.g., Sarah) can have multiple personas (PM, VISION_PM, REQUIREMENTS_PM, etc.) for different meeting contexts.

**Implementation**: `personas_config.json` is the source of truth.

---

## 12. Global SSE Stream

**One SSE endpoint for all sprint execution updates. Events include `sprint_id` for filtering.**

The stream stays open across sprint boundaries. A global buffer replays ~200 recent events to late-connecting listeners.

**Why**: Simpler than per-sprint streams. No reconnection dance between sprints.

**Implementation**: `GET /api/sprints/stream` in `api/sprint.py`

---

## 13. SP-001 Must Start with NFR-001

**The first sprint must begin with the Tech Stack NFR to establish architecture.**

NFR-001 defines: backend framework, database, testing framework, ports. This gets locked into `architecture.json` and subsequent sprints inherit it.

**Why**: Without a defined tech stack, Mike and Alex can't make consistent decisions.

**Implementation**: Orchestrator validates `first_story_id == "NFR-001"` for SP-001.

---

## Summary Table

| # | Principle | One-Line Summary |
|---|-----------|------------------|
| 1 | Chat-Only UI | Users talk to the team; bots do all artifact work |
| 2 | Four People, Many Roles | Same people, different prompts/tools per meeting, seamless to user |
| 3 | Safety-First Snapshots | Snapshot before every destructive action; always reversible |
| 4 | Fail-Fast Config | Missing config = crash at startup |
| 5 | Unified Response | All APIs return `{success, message, data}` |
| 6 | Structured Logging | JSON-line format, no print statements |
| 7 | Overwrite-on-Save | Living docs get replaced, not merged |
| 8 | Row-Scoped Updates | Update one row by rewriting entire CSV |
| 9 | Sequential Orchestrator | Mike → Alex → Jordan, one story at a time |
| 10 | Hard Gates | No "Done" until tests pass |
| 11 | Config-Driven Personas | JSON + txt files, no code changes |
| 12 | Global SSE | One stream, events include sprint_id |
| 13 | NFR-001 First | SP-001 must define tech stack |

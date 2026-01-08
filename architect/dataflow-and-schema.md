# Dataflow and Schema

This document is the authoritative reference for **Backlog CSV Dataflow** and **Backlog CSV Schema**.

---

## 1) Backlog CSV Dataflow

_Migrated from: `architect/DATA_FLOW_BACKLOG_CSV.md`_

# Backlog CSV Data Flow Documentation

## CRITICAL: Data Loss Prevention

**PROBLEM IDENTIFIED:** The backlog CSV can be accidentally overwritten if personas don't follow the correct save procedure.

---

## Schema Definition

### CSV Headers (20 columns - EXACT ORDER)
```
Story_ID,Title,User_Story,Functional_Requirements,Non_Functional_Requirements,Integrations,Dependencies,Constraints,Acceptance_Criteria,Priority,Status,Vision_Ref,Wireframe_Ref,Notes,Sprint_ID,Execution_Status,Execution_Started_At,Execution_Completed_At,Last_Event,Last_Updated
```

### Field Definitions

| Column | Type | Values | Purpose |
|--------|------|--------|---------|
| Story_ID | String | US-XXX, WF-XXX, NFR-XXX, STYLE-XXX | Unique identifier |
| Title | String | Any | Short description |
| User_Story | String | "As a X, I want Y, so that Z" | User story format |
| Functional_Requirements | String | Semicolon-separated list | What it must do |
| Non_Functional_Requirements | String | Semicolon-separated list | How it must perform |
| Integrations | String | Semicolon-separated list | External systems |
| Dependencies | String | Semicolon-separated list | What it depends on |
| Constraints | String | Semicolon-separated list | Limitations |
| Acceptance_Criteria | String | Semicolon-separated list | How to verify |
| Priority | Enum | High, Medium, Low | Importance |
| Status | Enum | Backlog, In Sprint, Done, Rejected | Current state |
| Vision_Ref | String | Any | Link to vision doc |
| Wireframe_Ref | String | wf-xxx-slug | Link to wireframe |
| Notes | String | Timestamped entries separated by " \| " | Audit trail |
| Sprint_ID | String | SP-XXX | Which sprint contains this |
| Execution_Status | String | pending, planned, in_progress, completed, completed_with_failures, failed | Sprint execution state |
| Execution_Started_At | ISO DateTime | YYYY-MM-DDTHH:MM:SS | When execution started |
| Execution_Completed_At | ISO DateTime | YYYY-MM-DDTHH:MM:SS | When execution finished |
| Last_Event | String | Any | Last thing that happened |
| Last_Updated | ISO DateTime | YYYY-MM-DDTHH:MM:SS | Last modification time |

---

## Data Flow: Who Touches the Backlog and When

### 1. REQUIREMENTS MEETING (Sarah as REQUIREMENTS_PM)

**Purpose:** Create and maintain the backlog

**Operations:**
- **CREATE** new stories (US-XXX, WF-XXX, NFR-XXX, STYLE-XXX)
- **UPDATE** existing stories (modify fields)
- **DELETE** stories (remove rows)

**CRITICAL SAVE PROCEDURE (NEW - JSON Records):**
```
STEP 1: Read current backlog from injected context
STEP 2: Parse backlog into JSON records (list of objects)
STEP 3: Modify specific records
STEP 4: Send COMPLETE records array with ALL records (modified + unmodified)
```

**Recommended API Call (JSON Records - FOOL-PROOF):**
```json
POST /api/backlog
{
  "action": "save",
  "id": "Backlog",
  "records": [
    {
      "Story_ID": "US-001",
      "Title": "...",
      ... (all 20 fields)
    },
    {
      "Story_ID": "US-002",
      "Title": "...",
      ... (all 20 fields)
    }
  ],
  "wireframes": [{"slug": "wf-xxx", "html_content": "..."}],
  "session_meta": {"project_name": "PROJECT_NAME"}
}
```

**Legacy API Call (Raw CSV - Deprecated):**
```json
POST /api/backlog
{
  "action": "save",
  "id": "Backlog",
  "rows_csv": "[COMPLETE CSV WITH HEADERS + ALL ROWS]",
  "wireframes": [{"slug": "wf-xxx", "html_content": "..."}],
  "session_meta": {"project_name": "PROJECT_NAME"}
}
```

**⚠️ DANGER:** If Sarah only sends modified records/rows, ALL other records/rows will be DELETED!
**✅ SAFE:** JSON records approach guarantees proper CSV quoting and prevents column misalignment

---

### 2. SPRINT PLANNING MEETING (via Sprint API)

**Purpose:** Select stories for sprint and update their status

**Operations:**
- **READ** backlog to see available stories
- **UPDATE** selected stories: Set Sprint_ID, Status="In Sprint", Execution_Status="planned"

**Current Behavior:** When a sprint plan is saved via `POST /api/sprints`, the backend automatically updates the backlog CSV for all selected stories. It sets `Sprint_ID`, `Status="In Sprint"`, and `Execution_Status="planned"` (if not already set). For US- stories, corresponding WF- wireframes are also updated.

**Implementation:** `api/sprint.py` lines 166-198

---

### 3. SPRINT EXECUTION (Orchestrator)

**Purpose:** Execute sprint tasks and update execution status

**Operations:**
- **READ** sprint plan (SP-XXX.json)
- **UPDATE** stories: Set Execution_Status, Execution_Started_At, Execution_Completed_At

**Current Behavior:** Orchestrator writes to `execution_log_SP-XXX.jsonl` **and** updates `Backlog.csv` via `_update_backlog()`.
**Details:** On story start it sets `Sprint_ID`, `Execution_Status="in_progress"`, `Execution_Started_At`, plus `Last_Event` and `Last_Updated`. On story completion it sets `Execution_Status` to `"completed"` when all tests pass or `"completed_with_failures"` when tests fail, and fills `Execution_Completed_At`, `Last_Event`, and `Last_Updated`.

---

### 4. SPRINT REVIEW MEETING (Sarah as SPRINT_REVIEW_PM)

**Purpose:** Review completed work and update story status based on user feedback

**Operations:**
- **READ** sprint execution summary
- **UPDATE** individual stories: Set Status="Done" or "Rejected", append Notes

**API Call:**
```json
POST /api/backlog/update-story
{
  "story_id": "US-006",
  "status": "Done",
  "notes": "User approved in Sprint Review. All criteria met."
}
```

**This is SAFE** - only updates one story at a time, preserves all other rows

---

## API Endpoints

### POST /api/backlog (Overwrites entire file - TWO SAFE METHODS)

**Actions:**
- `save` - Replaces entire CSV with request.records (NEW - RECOMMENDED) or request.rows_csv (legacy)
- `get` - Returns backlog JSON metadata
- `list` - Lists all backlogs
- `delete` - Deletes backlog and wireframes
- `latest` - Returns CSV file

**⚠️ WARNING:** Action "save" with incomplete data will DELETE all other rows!

#### Method 1: JSON Records (NEW - RECOMMENDED)

**Fool-proof approach:** Send JSON records, backend builds CSV with guaranteed proper quoting.

**Request:**
```json
POST /api/backlog
{
  "action": "save",
  "id": "Backlog",
  "records": [
    {
      "Story_ID": "US-001",
      "Title": "Employee Directory Search",
      "User_Story": "As an HR manager, I want to search the employee directory so that I can quickly find employee details.",
      "Functional_Requirements": "Search by name or email; Display results in table; Pagination if >10 results",
      "Non_Functional_Requirements": "Response time <2s; Secure access (login required)",
      "Integrations": "Database for employee data",
      "Dependencies": "US-015 for adding employees",
      "Constraints": "GDPR compliance",
      "Acceptance_Criteria": "1. User logs in; 2. Enters search term; 3. Results display accurately; 4. No results message if empty",
      "Priority": "High",
      "Status": "Backlog",
      "Vision_Ref": "KEY FEATURES: Employee directory",
      "Wireframe_Ref": "wf-001-employee-directory-search",
      "Notes": "Traces to Vision MVP must-haves",
      "Sprint_ID": "",
      "Execution_Status": "",
      "Execution_Started_At": "",
      "Execution_Completed_At": "",
      "Last_Event": "",
      "Last_Updated": ""
    }
  ],
  "wireframes": [
    {
      "slug": "wf-001-employee-directory-search",
      "html_content": "[FULL HTML WITH TAILWIND CSS]"
    }
  ],
  "session_meta": {"project_name": "PROJECT_NAME"}
}
```

**Backend Processing:**
1. Validates each record has all 20 required fields
2. Builds CSV from records using `csv.writer()` with `QUOTE_ALL`
3. Guarantees proper quoting for multi-line fields, commas, and special characters
4. Writes CSV file with schema validation
5. Saves wireframes if provided

**Advantages:**
- ✅ Structured data (JSON) is safer than raw CSV strings
- ✅ Backend controls CSV formatting (guaranteed proper quoting)
- ✅ Multi-line fields automatically quoted
- ✅ No risk of CSV parsing errors
- ✅ Easier to validate each field

#### Method 2: Raw CSV (Legacy - Deprecated)

**Request:**
```json
POST /api/backlog
{
  "action": "save",
  "id": "Backlog",
  "rows_csv": "[COMPLETE CSV WITH HEADERS + ALL ROWS]",
  "wireframes": [{"slug": "wf-xxx", "html_content": "..."}],
  "session_meta": {"project_name": "PROJECT_NAME"}
}
```

**Backend Processing:**
1. Validates CSV headers match schema
2. Parses CSV using `csv.reader()`
3. Re-writes CSV using `csv.writer()` with `QUOTE_ALL` (fixes any quoting issues)
4. Validates row count (prevents accidental deletion)
5. Writes CSV file with schema validation

**⚠️ DANGER:** If rows_csv is incomplete, ALL other rows will be DELETED!
**⚠️ DANGER:** Unquoted multi-line fields in rows_csv will cause column misalignment

### POST /api/backlog/update-story (SAFE - Updates one story)

**Purpose:** Update a single story's status and notes

**Request:**
```json
{
  "story_id": "US-006",
  "status": "Done",
  "notes": "User approved"
}
```

**Behavior:**
1. Reads entire CSV
2. Finds story by Story_ID
3. Updates Status field
4. Appends timestamped note to Notes field
5. Updates Last_Updated and Last_Event
6. Writes complete CSV back

**This is the SAFE way to update individual stories!**

---

## Current Issues and Gaps

### Issue 1: Sprint Planning Backlog Updates ✅ IMPLEMENTED
**Status:** RESOLVED - Sprint planning now updates backlog automatically.
**Implementation:** `POST /api/sprints` updates selected stories with `Sprint_ID`, `Status="In Sprint"`, and `Execution_Status="planned"`.

### Issue 2: Sprint Execution Backlog Updates ✅ IMPLEMENTED
**Status:** RESOLVED - Orchestrator DOES update `Backlog.csv` during execution using row-scoped updates.
**Implementation:** `_update_backlog()` method in `sprint_orchestrator.py` (row-scoped update of a single `Story_ID`).
**Updates Made:**
- Story start: Sets `Execution_Status="in_progress"`, `Execution_Started_At`, `Sprint_ID`
- Story complete (all tests pass): Sets `Execution_Status="completed"`, `Execution_Completed_At`
- Story complete with test failures: Sets `Execution_Status="completed_with_failures"`, `Execution_Completed_At`
- All updates include `Last_Event` and `Last_Updated` timestamps. Hard failures are recorded as `story_failed` events in `execution_log_SP-XXX.jsonl` and currently do not set `Execution_Status="failed"`.

### Issue 3: Sarah Can Overwrite Entire Backlog
**Problem:** If Sarah uses "save" action with incomplete rows_csv, she deletes all other rows
**Impact:** DATA LOSS - entire backlog can be wiped out
**Fix Needed:** Sarah should ALWAYS read full backlog from context before saving

### Issue 4: No Backlog Versioning
**Problem:** No backup or version history for backlog CSV
**Impact:** If data is lost, it's gone forever
**Fix Needed:** Add git tracking or automatic backups

---

## Recommended Fixes

### Fix 1: Add Backlog to Git
```bash
cd development/src/static/appdocs/backlog
git add Backlog.csv
git commit -m "Track backlog CSV for version control"
```

---

## Sprint SSE Event Schemas (Runtime Narration)

### Event Shapes Accepted by Frontend

- Primary (orchestrator):
```json
{ "event_type": "alex_implemented", "data": { "story_id": "US-009", "task_id": "US-009-03", "files_written": 4, "file_paths": ["..."] } }
```

- Fallback (generic message):
```json
{ "type": "team_message", "persona": "mike|alex|jordan", "message": "..." }
```

- Completion variants:
```json
{ "event_type": "sprint_completed", "data": { "summary": { "stories_completed": 2 } } }
{ "type": "sprint_complete", "sprint_id": "SP-001" }
```

### Display Policy (Chat)

- Displayed: `sprint_started`, `story_started`, `mike_breakdown`, `alex_implemented`, `jordan_tested`, `story_completed`, `sprint_completed|sprint_complete`
- Hidden (noise): `backlog_updated` (remains in JSONL log)

### Key Fields Referenced by UI

- `story_id` (data.story_id)
- `task_id` (data.task_id; optional; formats vary)
- `files_written` (preferred) or `files_count` (fallback) for Alex lines
- `task_count` for Mike breakdowns (when `summary` absent)

### Streaming Contract

- Endpoint: `GET /api/sprints/stream` (single global stream; events include `sprint_id` for filtering)
- SSE uses default "message" events only (no named `event:`); payload is JSON
- SSE Manager buffers ~200 messages before first listener connects

### Fix 2: Add Validation to Sarah's Save
Before saving, verify rows_csv contains ALL existing stories:
```python
# In save_backlog()
existing_csv = read_current_csv()
existing_story_ids = extract_story_ids(existing_csv)
new_story_ids = extract_story_ids(request.rows_csv)

if len(new_story_ids) < len(existing_story_ids):
    # DANGER: Some stories are missing!
    missing = existing_story_ids - new_story_ids
    raise ValidationError(f"Cannot save: Missing stories {missing}. Must include ALL rows.")
```

---

## Testing Checklist

### Test 1: Requirements Meeting - Add Story
1. Start requirements meeting
2. Ask Sarah to add a new user story US-010
3. Verify: Backlog CSV contains US-010 AND all previous stories

### Test 2: Requirements Meeting - Update Story
1. Start requirements meeting
2. Ask Sarah to update US-006 title
3. Verify: US-006 title changed, all other stories unchanged

### Test 3: Sprint Planning - Select Stories
1. Start sprint planning
2. Mike selects US-006, US-008 for sprint
3. Verify: Backlog CSV shows US-006 and US-008 with Status="In Sprint", Sprint_ID="SP-XXX"

### Test 4: Sprint Execution - Update Status
1. Execute sprint
2. Verify: Backlog CSV shows Execution_Status="in_progress" during execution
3. Verify: Backlog CSV shows Execution_Status="completed" after execution

### Test 5: Sprint Review - Approve Story
1. Start sprint review
2. User approves US-006
3. Verify: Backlog CSV shows US-006 Status="Done", Notes contain approval

### Test 6: Sprint Review - Reject Story
1. Start sprint review
2. User rejects US-008
3. Verify: Backlog CSV shows US-008 Status="Rejected", Notes contain issue details

---

## Emergency Recovery

### If Backlog is Lost/Corrupted

1. **Check Git History** (if tracked):
   ```bash
   git log -- static/appdocs/backlog/Backlog.csv
   git checkout HEAD~1 -- static/appdocs/backlog/Backlog.csv
   ```

2. **Reconstruct from Sprint Plans**:
   - Check `static/appdocs/sprints/SP-*.json` for story IDs
   - Manually recreate stories in backlog

3. **Reconstruct from Vision**:
   - Start requirements meeting
   - Ask Sarah to recreate backlog from vision document

---

## Status Field State Machine

```
Backlog → In Sprint → Done
              ↓
           Rejected → (Requirements Meeting) → Backlog → In Sprint → Done
```

**State Transitions:**
- `Backlog` → `In Sprint`: Sprint Planning (Mike)
- `In Sprint` → `Done`: Sprint Review (Sarah, user approves)
- `In Sprint` → `Rejected`: Sprint Review (Sarah, user finds issues)
- `Rejected` → `Backlog`: Requirements Meeting (Sarah, clarify requirements)

---

## 2) Backlog CSV Schema

_Migrated from: `architect/BACKLOG_CSV_SCHEMA.md`_

This section provides additional detail on schema rules, formatting, and implementation patterns. For the canonical field definitions, see Section 1 above.

---

## Execution_Status Field

### Allowed Values

- **pending** - Story in sprint but execution not started (design/default)
- **planned** - Story assigned to sprint via sprint planning
- **in_progress** - Story currently being executed
- **completed** - Execution finished and all tests passed
- **completed_with_failures** - Execution finished but tests failed or could not run; code is kept for review
- **failed** - Reserved for future use to represent hard failures that abort execution early

**Note:** This is separate from Status. A story can be `Execution_Status: completed` or `completed_with_failures` while `Status: Rejected` if the user does not approve in Sprint Review.

---

## CSV Formatting Rules

### Required Rules

1. **Header Row:** First row MUST be the exact 20-column header
2. **Column Count:** Every data row MUST have exactly 20 columns
3. **Empty Fields:** Use empty string for optional fields, NOT null or missing
4. **Quotes:** Wrap fields in double quotes if they contain commas, newlines, or quotes
5. **Escape Quotes:** Double any quotes inside quoted fields
6. **Line Endings:** Use LF or CRLF, be consistent
7. **Encoding:** UTF-8 only

### List Fields (Semicolon-Separated)

Fields that contain lists use semicolon + space as separator:

```
Requirement 1; Requirement 2; Requirement 3
```

**List Fields:**
- Functional_Requirements
- Non_Functional_Requirements
- Integrations
- Dependencies
- Constraints
- Acceptance_Criteria

### Notes Field (Pipe-Separated Timestamped)

Notes field contains timestamped entries separated by pipe with spaces:

```
[2025-11-01 14:05] User approved | [2025-11-01 15:30] Status changed to Done
```

**Format:** [YYYY-MM-DD HH:MM] Note text | [YYYY-MM-DD HH:MM] Next note

---

## Story ID Prefixes

### Prefix Meanings

- **US-###** - User Story (functional feature)
- **WF-###** - Wireframe (UI design)
- **NFR-###** - Non-Functional Requirement (performance, security, etc.)
- **STYLE-###** - Style Guide (design system rules)

### Numbering Rules

- Start at 001 for each prefix type
- Increment sequentially
- Zero-pad to 3 digits: US-001, US-002, ..., US-099, US-100
- Do NOT reuse deleted IDs

---

## Code Implementation Rules

### Rule 1: Always Read ALL Rows Before Writing

**CORRECT:**
```python
# Read all rows
with open(csv_file, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    headers = reader.fieldnames

# Modify specific rows
for row in rows:
    if row['Story_ID'] == target_id:
        row['Status'] = new_status

# Write ALL rows back
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
```

**WRONG:**
```python
# This will DELETE all other rows!
with open(csv_file, 'w', newline='') as f:
    f.write(partial_csv)
```

### Rule 2: Validate Schema Before Writing

**CORRECT:**
```python
# Validate headers match expected schema
EXPECTED_HEADERS = [
    "Story_ID", "Title", "User_Story", "Functional_Requirements",
    "Non_Functional_Requirements", "Integrations", "Dependencies",
    "Constraints", "Acceptance_Criteria", "Priority", "Status",
    "Vision_Ref", "Wireframe_Ref", "Notes", "Sprint_ID",
    "Execution_Status", "Execution_Started_At", "Execution_Completed_At",
    "Last_Event", "Last_Updated"
]

if headers != EXPECTED_HEADERS:
    raise ValueError(f"Invalid headers: {headers}")
```

### Rule 3: Validate Row Count Before Overwriting

**CORRECT:**
```python
# Count existing rows
existing_count = len(list(csv.DictReader(open(csv_file))))

# Count new rows
new_count = len(new_rows)

# Prevent accidental deletion
if new_count < existing_count * 0.9:  # 10% tolerance
    raise ValueError(
        f"Suspicious save: {existing_count} rows → {new_count} rows. "
        f"This would delete {existing_count - new_count} rows!"
    )
```

### Rule 4: Use Consistent Status Values

**CORRECT:**
```python
VALID_STATUS = ["Backlog", "In Sprint", "Done", "Rejected"]

if status not in VALID_STATUS:
    raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUS}")
```

---

## Persona Instructions

### Requirements PM (Sarah) - Backlog Creation/Updates

**When to use:** Requirements Meeting

**Status values to use:**
- New stories: `Backlog`
- Never use: Draft, Approved, In Progress

**Save procedure:**
1. Read current backlog from injected context
2. Add/modify/delete specific stories
3. Save COMPLETE CSV with ALL rows (modified + unmodified)

### Sprint Planning (Mike) - Story Selection

**When to use:** Sprint Planning Meeting

**Status values to use:**
- Selected stories: Change from `Backlog` to `In Sprint`
- Set `Sprint_ID` field

**Update procedure:**
- Use update-story endpoint for each selected story
- OR read full backlog, modify, save complete CSV

### Sprint Execution (Orchestrator) - Execution Tracking

**When to use:** During sprint execution

**Fields to update:**
- `Execution_Status`: pending → in_progress → completed/failed
- `Execution_Started_At`: ISO timestamp when started
- `Execution_Completed_At`: ISO timestamp when finished
- `Last_Event`: Description of what happened
- `Last_Updated`: Current timestamp

**Update procedure:**
- Read all rows
- Update specific story
- Write all rows back

### Sprint Review (Sarah) - User Acceptance

**When to use:** Sprint Review Meeting

**Status values to use:**
- User approves: Change from `In Sprint` to `Done`
- User rejects: Change from `In Sprint` to `Rejected`

**Update procedure:**
- Use update-story endpoint
- Append timestamped note explaining decision

---

## Validation Checklist

Before any code writes to Backlog.csv, verify:

- [ ] Headers match exact 20-column schema
- [ ] All rows have exactly 20 columns
- [ ] Status values are: Backlog, In Sprint, Done, or Rejected
- [ ] Priority values are: High, Medium, or Low
- [ ] Execution_Status values are: pending, planned, in_progress, completed, completed_with_failures, or failed
- [ ] Story_IDs follow prefix rules: US-###, WF-###, NFR-###, STYLE-###
- [ ] ISO timestamps are valid format
- [ ] Row count is not suspiciously lower than before
- [ ] All existing rows are preserved (unless explicitly deleted)

---

## Emergency Recovery

If backlog is corrupted or accidentally overwritten:

1. Check `architect/` folder for backup copies
2. Reconstruct from sprint plans in `static/appdocs/sprints/SP-*.json`
3. Start fresh from vision document in Requirements Meeting

---

## JSON Records Implementation

**Status:** ✅ IMPLEMENTED AND TESTED

**What Changed:**
- Added `records` field to `BacklogRequest` model (JSON array of objects)
- Backend now accepts JSON records as preferred method over raw CSV
- Added `build_csv_from_records()` function that builds CSV with guaranteed `QUOTE_ALL` quoting
- Fixed bug where CSV wasn't being written when records provided (elif → if logic fix)

**Why This Matters:**
- ✅ Eliminates CSV parsing errors from unquoted multi-line fields
- ✅ Backend controls CSV formatting (no reliance on persona to quote correctly)
- ✅ Structured JSON is easier to validate than raw CSV strings
- ✅ Prevents column misalignment issues that plagued raw CSV approach

**Implementation Details:**
- Location: `/development/src/api/backlog.py` lines 28-85 (build_csv_from_records function)
- Location: `/development/src/api/backlog.py` lines 158-291 (save_backlog with records support)
- Location: `/development/src/api/conventions.py` line 80 (BacklogRequest model)

**Backward Compatibility:**
- ✅ Legacy `rows_csv` field still supported (deprecated)
- ✅ Existing code using rows_csv continues to work
- ✅ New code should use `records` field

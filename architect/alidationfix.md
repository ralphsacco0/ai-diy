# Validation Fix Inventory & Prompt Alignment (US-004 Breakdown)

## Purpose
This document inventories the **validation layers** (and their enforcement strength) in the sprint execution pipeline, and maps those validations to the **Mike (Architect)**, **Alex (Developer)**, and **Jordan (QA)** system prompts.

Primary goal: reduce recurrence of failures like **US-004** on Railway where a persona response (Mike) was **not parseable JSON**, causing downstream validation to fail.

## Scope
- **Orchestrator**: `development/src/services/sprint_orchestrator.py`
- **Orchestrator version observed**: `2.6.0-arch-contract-enforced`
- **Persona prompts**:
  - `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt` (Mike)
  - `system_prompts/SPRINT_EXECUTION_DEVELOPER_system_prompt.txt` (Alex)
  - `system_prompts/SPRINT_EXECUTION_QA_system_prompt.txt` (Jordan)

---

## Executive summary (US-004 failure mode)
- **What happened**: Mike produced a response that was **not valid JSON** (commonly: unescaped characters and/or template literal constructs like ```${...}``` inside JSON string values). 
- **Why it broke**:
  - The orchestrator uses `_extract_json()` to parse Mike’s response.
  - When parsing fails, `_extract_json()` attempts to locate JSON objects via brace-counting and “repair” strategies.
  - In US-004, invalid JSON caused the extractor to either:
    - Fail to parse any candidate JSON object, or
    - Extract a *smaller* valid object (incomplete) that then failed structure validation.
  - `_validate_task_breakdown()` requires a non-empty `tasks` array with minimal required fields; failure leads to “mike_breakdown_failed” behavior (story is skipped/failed).

Net: this is a **contract failure** at the Mike → Orchestrator boundary.

---

## Inventory: validation layers and enforcement strength

### A) Mike (Architect) stage

#### A1) JSON extraction/parsing: `_extract_json(text) -> Optional[Dict]`
**Where**: `sprint_orchestrator.py`

**What it does**:
- Attempts `json.loads(text.strip())`.
- If that fails:
  - Attempts to parse a JSON object from a markdown code fence (```json ... ```).
  - Attempts “brace-counting” extraction of balanced `{ ... }` objects while tracking string/escape state.
  - Tries immediate inline repairs on each candidate object, including:
    - Replacing invalid JSON escape for single quotes: `\\'` → `'`
    - Mitigating template literal `${` sequences: `${` → `$\\u007B`
    - Repairing an HTML-adjacent sequence: `}">` → `}\\">`
  - If multiple valid candidates are found, returns the **largest** by string length.
- If no candidates parse:
  - Attempts “aggressive repair” on substring from first `{` to last `}` with several strategies.

**Enforcement**: Hard gate. If JSON cannot be extracted, Mike’s breakdown cannot proceed.

**US-004 relevance**:
- `${...}` and/or backticks inside JSON string values are high-risk.
- Literal unescaped newlines inside JSON string values are also high-risk.

#### A2) Breakdown structure validation: `_validate_task_breakdown(breakdown, story_id) -> bool`
**Where**: `sprint_orchestrator.py`

**Checks (hard requirements)**:
- `breakdown` is a `dict`.
- `tasks` exists.
- `tasks` is a non-empty list.
- Each task is a `dict`.
- Normalizes:
  - `taskId` or `id` → `task_id`
  - `title` → `description`
- Requires each task has:
  - `task_id`
  - `description`
- Validates story id:
  - If `breakdown['story_id']` exists and differs, orchestrator **corrects it** to the expected `story_id`.
- Pre-flight path validation:
  - Calls `_validate_file_paths(files_to_create)` and logs **warnings** (does not fail).

**Enforcement**: Hard gate. If this returns false, breakdown is considered invalid.

**US-004 relevance**:
- If `_extract_json` returns an incomplete object lacking `tasks` or with empty `tasks`, this function fails.

#### A3) Additional breakdown validation layer in `run()` (task id format + task must do something)
**Where**: `run()` immediately after Mike breakdown is received.

**Checks**:
- Task id prefix format:
  - Must start with `T-{story_id}-`
- Zero-padding:
  - Suffix must be exactly 2 digits (`01`, `02`, …)
- Each task must have at least one of:
  - `files_to_create` non-empty
  - `command_to_run` non-empty

**Enforcement**:
- If errors exist: attempts `_call_mike_retry_validation(...)`.
- If retry fails: logs error and proceeds with original breakdown (“better to have wrong format than fail completely”).

**US-004 relevance**:
- Not the primary failure mode for US-004 (that was JSON parse), but it’s the next gating layer and should align with Mike’s prompt.

#### A4) Incomplete breakdown detection (task_count mismatch)
**Where**: `run()`

**Checks**:
- Compares:
  - `expected_task_count = task_breakdown.get('task_count', len(tasks))`
  - `actual_task_count = len(tasks)`
- If `actual < expected`: attempts `_call_mike_retry_incomplete(...)` and extends tasks if recovered.

**Enforcement**:
- Recover if possible; otherwise degrade gracefully and continue.

**US-004 relevance**:
- If `_extract_json` extracts a partial JSON object that still parses but is missing tasks, this recovery is intended to help.

#### A5) File path validation: `_validate_file_paths(file_paths) -> List[str]`
**Where**: used as a pre-flight warning.

**Hard-invalid conditions**:
- Path traversal: contains `..`
- Absolute path: starts with `/`
- Non-string entries

**Non-blocking conditions**:
- If path doesn’t match an “allowed prefix” list, it logs info but does not mark invalid.

**Enforcement**: Warn-only (pre-flight). Does not block.

---

### B) Alex (Developer) stage

#### B1) Alex output normalization: `_normalize_alex_response(code_result) -> List[Dict]`
**Where**: `sprint_orchestrator.py`

**Purpose**:
- Accepts multiple possible shapes from Alex and extracts file specs as a list of `{path, content}`.
- If it cannot extract files, logs a warning.

**Enforcement**: Gating, but typically followed by retries upstream (Alex retry loop). Exact retry logic is outside this snippet, but the pipeline expects Alex to conform.

#### B2) Syntax + content validation: `_validate_files_syntax(files) -> List[Dict]`
**Where**: `sprint_orchestrator.py`

**Checks**:
- Ensures each file has:
  - a `path`
  - `content`
  - and `content` is a string (non-string content yields an error entry)
- Python syntax validation for `.py` via `ast.parse()` / `compile()`
- SQL checks for files likely to contain schema SQL:
  - file path matches patterns like `db.js`, `db.py`, `model`, `migration`, `schema`
  - reserved words used unquoted
  - missing commas heuristic
  - CHECK constraint syntax heuristic
- Node test pattern checks (if a file looks like a Node test file)

**Enforcement**: Gating, typically triggers Alex retry if errors exist.

#### B3) Architectural contract enforcement: `_enforce_arch_contract(project_root, story_id, contract, story_files_written) -> bool`
**Where**: `sprint_orchestrator.py`

**Contract creation**: `_build_arch_contract(baseline_files, baseline_deps, design, story_id)`
- Allowed files = baseline file surface + any `files_to_create` listed by Mike
- Allowed deps = baseline deps + any deps listed in Mike’s `dependencies` block

**Enforcement checks**:
- Alex must not write files outside allowed surface
- Alex must not introduce npm deps outside allowed deps

**Enforcement strength**: Hard fail for the story if violated (returns False).

**US-004 relevance**:
- If Mike’s breakdown is incomplete or missing `files_to_create`, the allowed surface becomes too small, increasing risk of contract violations.

---

### C) Jordan (QA) stage

#### C1) Expected output schema (Jordan → Orchestrator)
**Where**: orchestrator parses JSON and expects test payload.

**Prompt contract** (Jordan prompt):
- Output ONLY valid JSON:
  - `{ "test_file": "...", "test_content": "...", "test_cases": [...] }`

**Enforcement**: Gating; invalid JSON or missing required fields prevents test file writing.

#### C2) Node test anti-pattern validator: `_validate_test_patterns(content, filepath) -> List[Dict]`
**Where**: `sprint_orchestrator.py` (called from `_validate_files_syntax`)

**Checks** (only for Node test files by filename pattern):
- “db imported at file level before first test()”
- “db imported but never closed” (expects `db.close` usage)

**Enforcement**: Produces validation errors (used to trigger retries / block writing bad test files).

---

## Hard-fail vs retry vs warn-only classification

| Layer | Function / Location | What it validates | Enforcement strength | Typical handling |
|---|---|---|---|---|
| Mike JSON parse | `_extract_json` | Response must be parseable JSON object | Hard gate | If None → breakdown invalid (story fails/skips) |
| Mike breakdown structure | `_validate_task_breakdown` | `tasks` exists and non-empty; each task has `task_id`,`description` | Hard gate | If false → breakdown invalid (story fails/skips) |
| Mike task format | `run()` “VALIDATION LAYER” | `task_id` prefix + zero-padding; task has files or command | Retry (best effort) | Retry Mike with feedback; if still wrong continue |
| Mike incomplete breakdown | `run()` task_count mismatch | Detect missing tasks | Retry (best effort) | Retry Mike for missing tasks; else continue |
| Mike file path safety | `_validate_file_paths` | Blocks traversal/absolute paths; warns on new dirs | Warn-only | Logs warnings; does not block |
| Alex output parse | `_normalize_alex_response` | Extract files array from Alex JSON | Gating | Missing files → warning + likely retry upstream |
| Alex syntax | `_validate_files_syntax` | Python syntax; SQL heuristics; Node test patterns | Retry-gated | Errors → retry Alex / fail task if exhausted |
| Alex arch contract | `_enforce_arch_contract` | No extra files/deps beyond Mike contract | Hard fail | Story fails if violated |
| Jordan output schema | (Orchestrator parse + writer) | `test_file` + `test_content` present | Hard gate | Invalid → tests not written / story fails |
| Jordan test patterns | `_validate_test_patterns` | Node test DB isolation patterns | Retry-gated | Errors → retry Jordan / block tests |

---

## Prompt-to-validator alignment matrix

### Mike (Architect) prompt alignment

| Validator expectation | Where enforced | Mike prompt instruction | Alignment status | Gap / risk |
|---|---|---|---|---|
| Output must be valid JSON only | `_extract_json` | “OUTPUT ONLY VALID JSON. NO markdown. NO prose.” | Aligned | Still fails in practice when JSON strings include illegal characters |
| `story_id`, `architectural_conflict`, `tasks` required | `_validate_task_breakdown` partially; others indirectly | “Top-level JSON MUST include these fields” | Partially aligned | Orchestrator does **not** explicitly validate all top-level fields (beyond `tasks`), but missing fields can break later stages |
| `tasks` must be non-empty for normal stories | `_validate_task_breakdown` | “You MUST produce a NON-EMPTY tasks array” | Aligned | If JSON extraction yields incomplete object, this fails |
| Task id format strict | `run()` validation | “TASK ID FORMAT (STRICT)… zero padded” | Aligned | Orchestrator retries but can proceed even if wrong |
| Each task should specify files/commands | `run()` validation | “files_to_create … or []” and command optional | Aligned | If Mike omits both, orchestrator retries but may continue |
| Avoid template literals / invalid escapes in JSON strings | `_extract_json` repair attempts | Mike prompt includes “NO TEMPLATE LITERALS… Template literal backticks and ${} cause JSON parse errors.” | Aligned (but buried) | This rule is present but not prominent; failures still occur |

### Alex (Developer) prompt alignment

| Validator expectation | Where enforced | Alex prompt instruction | Alignment status | Gap / risk |
|---|---|---|---|---|
| Alex output must be parseable JSON | `_extract_json` + `_normalize_alex_response` | “Output a single JSON object… valid, parseable JSON” | Aligned | High-risk due to embedding multi-line file content in JSON strings |
| Only generate files in `files_to_create` | `_enforce_arch_contract` + orchestration logic | “Respect files_to_create… MUST NOT generate any file not listed” | Aligned | If Mike breakdown is incomplete, contract surface may be too small, increasing false violations |
| Do not generate tests | Pipeline role separation | “MUST NOT generate test files” | Aligned | None |

### Jordan (QA) prompt alignment

| Validator expectation | Where enforced | Jordan prompt instruction | Alignment status | Gap / risk |
|---|---|---|---|---|
| Output must be valid JSON with required fields | Orchestrator parse + writer | “output only valid JSON of this shape…” | Aligned | Same JSON-string risks as Alex (multi-line test content) |
| Node tests must avoid hanging (`res.resume()`, close server) | Runtime/test behavior + prompt checklist | Jordan prompt explicitly requires `res.resume()` and close patterns | Aligned | Very strong; enforced mostly by behavior not schema |

---

## Key mismatches and “missing reinforcement” items

### 1) Mike: “valid JSON” is stated, but failure cases still occur
Even with a strong instruction, the most common breakpoints are:
- Backticks and template literal patterns (```${...}```)
- Literal unescaped newlines inside JSON string values
- Unescaped double quotes inside JSON string values

**Impact**: `_extract_json` may fail entirely or return a smaller candidate object that passes parsing but fails breakdown validation.

### 2) Orchestrator validates only a subset of Mike’s declared mandatory fields
Mike prompt says each task must include fields like `files_to_create`, `dependencies`, `dependency_reason`.
- `_validate_task_breakdown` only requires `task_id` and `description`.
- The later `run()` validation layer additionally requires “files or command”, but not the full set.

**Impact**:
- The prompt and validator are not fully aligned.
- Missing fields can break the “closed world” contract (e.g., missing `files_to_create` shrinks the allowed file surface).

### 3) Alex/Jordan: valid JSON with multi-line content is intrinsically fragile
Both Alex and Jordan output JSON where `content` fields are long and multi-line.
- JSON strings cannot contain literal newlines; they must be escaped (`\n`).

**Impact**: JSON parse failures are likely without additional repair/retry.

---

## Minimal hardening proposals (proposal-only; do not apply without approval)

### Proposal set A: prompt-only reinforcement (lowest code risk)

#### A1) Mike prompt: elevate “JSON string safety” into the top contract section
Add a short “DO NOT EVER” checklist directly under “OUTPUT ONLY VALID JSON”:
- No backticks (`` ` ``) anywhere in JSON.
- No `${` sequences anywhere in JSON.
- No literal newlines in JSON string values (keep all values single-line).
- Never embed code snippets in JSON values; describe behavior in plain English.

**Why minimal**: Does not change system behavior; only strengthens compliance.

#### A2) Alex/Jordan prompts: explicit reminder about escaping multi-line `content`
Add a single line near “Output must be valid, parseable JSON”:
- “If you include multi-line file content inside JSON, it MUST be JSON-escaped (`\n`, `\t`, `\"`).”


### Proposal set B: orchestrator-only hardening (still minimal, but code changes)

#### B1) Add a Mike JSON repair retry on JSONDecodeError
There is already `_retry_json_extraction(...)` used for JSON repair patterns.
- Extend similar retry behavior to Mike breakdown parsing failures:
  - When `_extract_json` returns None for Mike, retry once with a strict “JSON repair assistant” message containing the truncated original output.

**Why minimal**: Adds resilience without changing Mike’s prompt.

#### B2) Treat “parsed but structurally invalid” as a retry condition
If `_extract_json` returns a dict but `_validate_task_breakdown` fails, treat it equivalently to a parse failure:
- Retry Mike with targeted feedback (“missing tasks array”, “tasks empty”, etc.).

**Why minimal**: Keeps the pipeline’s design but increases self-healing.

#### B3) Optional: JSON Schema validation for Mike breakdown
Introduce a JSON Schema for Mike’s output and validate before proceeding.
- This is more invasive than B1/B2 but would provide a single authoritative contract.

---

## Recommended next step
- Decide whether we prefer:
  - **Prompt-only** reinforcement first (A1/A2), or
  - A small orchestrator resilience patch (B1/B2), or
  - Both.

Once you choose, I can propose exact diff(s) for the prompt(s) and/or orchestrator, but I will not apply any changes without explicit approval.

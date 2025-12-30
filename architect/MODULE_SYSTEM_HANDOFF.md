# Module System Consistency - Handoff Document

## Purpose
This document describes the flow of technical decisions from architecture through code generation and testing, identifies sensitive interdependencies, documents recent changes and problems, and defines the work needed for a holistic consistency review.

---

## 1. The Decision Flow: Tech Stack to Testing

### Source of Truth
```
architecture.json (locked at SP-001)
├── conventions.module_system: "commonjs"
├── conventions.export_import_patterns: "Use require() for imports; module.exports = {...}"
└── tech_stack.backend: "nodejs_express"
```

### Decision Flow Chain
```
architecture.json
    ↓
Mike (Architect) - SPRINT_EXECUTION_ARCHITECT_system_prompt.txt
    │   Reads architecture, creates task breakdowns
    │   Should specify: "Use CommonJS (require/module.exports)"
    ↓
Alex (Developer) - SPRINT_EXECUTION_DEVELOPER_system_prompt.txt
    │   Reads Mike's tasks + architecture
    │   Generates: package.json, server.js, routes, etc.
    │   CRITICAL: Must NOT add "type": "module" for CommonJS projects
    ↓
Jordan (QA) - SPRINT_EXECUTION_QA_system_prompt.txt
    │   Reads generated code + architecture
    │   Generates: test files (*.test.js)
    │   CRITICAL: Must match module system of generated code
    ↓
Node.js Test Runner
    │   Runs: node --test tests/
    │   Behavior determined by package.json "type" field
    ↓
Pass/Fail
```

### How Node.js Determines Module System
- If package.json has `"type": "module"` → ALL .js files are ES modules (import/export)
- If package.json has NO "type" field → ALL .js files are CommonJS (require/module.exports)
- This is ALL OR NOTHING - you cannot mix within a project

---

## 2. The Sensitive Interdependencies

### Critical Chain Reactions
```
IF Alex adds "type": "module" to package.json
THEN Jordan sees it and writes ES module tests (import/export)
THEN Node runs tests as ES modules
THEN tests try to import CommonJS app code
THEN FAILURE: "require is not defined in ES module scope"
```

### Files That Must Be Consistent

| File | Must Match | Why |
|------|-----------|-----|
| package.json | architecture.module_system | Determines how Node interprets ALL .js files |
| src/*.js | package.json type field | App code syntax must match |
| tests/*.test.js | package.json type field | Test code syntax must match |

### Prompt Files That Influence This

| Prompt | Role | Influence |
|--------|------|-----------|
| SPRINT_EXECUTION_ARCHITECT_system_prompt.txt | Mike | Sets task descriptions, may specify module system |
| SPRINT_EXECUTION_DEVELOPER_system_prompt.txt | Alex | Contains package.json EXAMPLES that may mislead |
| SPRINT_EXECUTION_QA_system_prompt.txt | Jordan | Has rules to check package.json for "type": "module" |

---

## 3. What I Changed and Why

### Change 1: Removed "type": "module" from Alex's Examples (commit 34c0eff)

**File:** `system_prompts/SPRINT_EXECUTION_DEVELOPER_system_prompt.txt`

**What I removed:**
```json
// BEFORE (lines 900-903 and 943-946):
{
  "name": "business-app",
  "version": "1.0.0",
  "type": "module",  // <-- REMOVED THIS
  ...
}
```

**Why:** The examples showed ES module config but architecture says CommonJS. Alex was copying the examples.

**Problem:** This was in the prompt since INITIAL COMMIT (Dec 21). It was always inconsistent with architecture.json.

### Change 2: Added Hybrid Case Guidance (commit 960acbd)

**Files:** All three execution prompts (Mike, Alex, Jordan)

**What I added:**
```
API RESPONSES WITH REDIRECT URLS (HYBRID CASE):
When an API returns a redirect path in JSON that client JS will use:
- The redirect value must be RELATIVE (no leading /) because it flows to client-side JS

✅ res.json({ success: true, redirect: 'dashboard' })
❌ res.json({ success: true, redirect: '/dashboard' })
```

**Why:** Login was working on localhost but failing on Railway. The redirect path in JSON responses was using absolute paths which broke behind the Caddy proxy.

### Change 3: Rollback Fixes (sprint_orchestrator.py)

**What I changed:**
1. Hardwired project_root to "yourapp" instead of using metadata.get("project_name")
2. Added clearing of mike_breakdowns directory during rollback

**Why:** Rollback was pointing to wrong folder and not clearing task breakdowns, causing sprints to resume from middle.

---

## 4. Problems Encountered

### Problem 1: NFR-001 First Pass Failures
- **Symptom:** Tests fail with "require is not defined in ES module scope"
- **Root cause:** Alex adds "type": "module" to package.json, Jordan writes ES module tests, but app code uses CommonJS
- **Recovery:** System retries and sometimes succeeds on 2nd/3rd attempt
- **Status:** Partially addressed by removing examples, but still occurring

### Problem 2: Inconsistent Behavior
- **Symptom:** Same sprint sometimes passes, sometimes fails first pass
- **Observation:** Backup from Dec 29/30 shows correct CommonJS package.json
- **Hypothesis:** LLM (Grok-4) interprets prompts differently on different runs
- **Status:** Not fully understood

### Problem 3: Prompt Sensitivity
- **Symptom:** Small changes to prompts cause cascade failures
- **Observation:** Examples in prompts have strong influence on LLM output
- **Lesson:** Changes to execution prompts need full flow testing

---

## 5. Work That Needs To Be Done

### Required: Holistic Consistency Review

An LLM needs to examine ALL of the following for consistency:

#### A. Architecture Source of Truth
- `development/src/static/appdocs/architecture.json`
  - What does it say about module_system?
  - What does it say about export_import_patterns?

#### B. Mike's Prompt (Architect)
- `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt`
  - Does it tell Mike to specify module system in task descriptions?
  - Are there examples that conflict with CommonJS?
  - Does it reference architecture.json conventions?

#### C. Alex's Prompt (Developer)
- `system_prompts/SPRINT_EXECUTION_DEVELOPER_system_prompt.txt`
  - Are ALL package.json examples consistent with CommonJS (NO "type": "module")?
  - Are ALL code examples using require/module.exports (NOT import/export)?
  - Is there a CLEAR DEFAULT rule: "If unsure, use CommonJS"?
  - Does it tell Alex to CHECK architecture.json before writing package.json?

#### D. Jordan's Prompt (QA)
- `system_prompts/SPRINT_EXECUTION_QA_system_prompt.txt`
  - Does it tell Jordan to match the module system of the app code?
  - Are test examples using require/module.exports?
  - Does it tell Jordan to check architecture.json, not just package.json?

#### E. Cross-Prompt Consistency
- Do all three prompts give CONSISTENT instructions about module system?
- Are there any CONFLICTS between prompts?
- Is the decision hierarchy clear? (architecture.json > Mike's task > Alex's code > Jordan's tests)

### Specific Questions to Answer

1. **Are there any remaining ES module examples in any prompt?**
   - Search for: `import `, `export `, `"type": "module"`

2. **Is there a clear DEFAULT rule in Alex's prompt?**
   - Should say: "If module_system is not specified, assume CommonJS"
   - Should say: "NEVER add 'type': 'module' unless explicitly required"

3. **Does Jordan check architecture.json or just package.json?**
   - Current behavior: Jordan checks package.json for "type": "module"
   - If Alex mistakenly adds it, Jordan follows the mistake
   - Should Jordan check architecture.json as source of truth instead?

4. **Is the server/client path guidance consistent across all prompts?**
   - I added hybrid case guidance to all three prompts
   - Need to verify they don't conflict

### Recommended Fix Approach

1. **Add explicit DEFAULT rules to Alex's prompt:**
   ```
   CRITICAL FOR NODE.JS 18+ PROJECTS:
   - ALWAYS check architecture.json conventions.module_system BEFORE writing package.json
   - If module_system = "commonjs" → Do NOT add "type": "module"
   - DEFAULT: If unclear, assume CommonJS - NEVER add "type": "module" unless explicitly required
   ```

2. **Make Jordan check architecture.json, not just package.json:**
   ```
   MODULE SYSTEM: Check architecture.json conventions.module_system, NOT package.json
   - This is the source of truth
   - If Alex made a mistake in package.json, don't propagate it
   ```

3. **Full search for ES module patterns in all prompts:**
   ```bash
   grep -r "import " system_prompts/
   grep -r "export " system_prompts/
   grep -r '"type": "module"' system_prompts/
   ```

---

## 6. Files to Review

| File | Purpose | Check For |
|------|---------|-----------|
| `architecture.json` | Source of truth | module_system value |
| `SPRINT_EXECUTION_ARCHITECT_system_prompt.txt` | Mike | Module system guidance, examples |
| `SPRINT_EXECUTION_DEVELOPER_system_prompt.txt` | Alex | package.json examples, code examples, default rules |
| `SPRINT_EXECUTION_QA_system_prompt.txt` | Jordan | Test examples, module system detection logic |
| `SPRINT_REVIEW_ALEX_system_prompt.txt` | Debug Alex | May also have examples |
| `sprint_orchestrator.py` | Execution engine | How prompts are assembled, what context is passed |

---

## 7. Summary

**The Core Issue:** The architecture specifies CommonJS, but prompts had (and may still have) ES module examples and patterns that confuse the LLMs.

**Why It Matters:** If Alex adds "type": "module" to package.json, the ENTIRE project breaks because Node.js treats all .js files as ES modules, but the app code uses CommonJS require() syntax.

**What's Needed:** A complete review of all prompts to ensure:
1. All examples match CommonJS (require/module.exports)
2. Clear default rules exist ("when in doubt, use CommonJS")
3. Alex checks architecture.json before making decisions
4. Jordan checks architecture.json as source of truth, not potentially-wrong package.json

---

*Document created: 2025-12-30*
*Author: Claude (handoff for consistency review)*

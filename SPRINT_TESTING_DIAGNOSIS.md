# Sprint Execution Testing Diagnosis & Fixes
**Date**: 2025-12-08  
**Issue**: Sprint execution testing failures despite correct code implementation

---

## Problems Identified

### Problem 1: HTTP Test Timeouts (120 seconds)
**Symptom**: Jordan's tests hang for 120 seconds then timeout  
**Log Evidence**: `execution_log_SP-001.jsonl` line 21
```json
{"event_type": "jordan_tested", "data": {"test_count": 0, "passed": 0, "failed": 0, "output": "Test execution timeout (>120s)"}}
```

**Root Cause**: Missing `res.resume()` in HTTP test pattern

**Technical Explanation**:
- Jordan's test creates an HTTP request and listens for `res.on('end')` event
- Without consuming the response stream, the 'end' event never fires
- Test waits indefinitely until 120s timeout kills it

**The Bug** (in generated test):
```javascript
const req = http.request({...}, (res) => {
  assert(res.statusCode < 500);
  // Missing: res.resume()
  res.on('end', () => {
    server.close(() => resolve());
  });
});
```

**The Fix**:
```javascript
const req = http.request({...}, (res) => {
  assert(res.statusCode < 500);
  res.resume(); // ← CRITICAL: Consume the stream
  res.on('end', () => {
    server.close(() => resolve());
  });
});
```

---

### Problem 2: Wrong Test Framework (pytest for Node.js)
**Symptom**: pytest tries to run `.test.js` files  
**Log Evidence**: `execution_log_SP-001 2.jsonl` lines 24, 42, 60
```json
{"output": "ERROR: file or directory not found: execution-sandbox/.../tests/test_US-009.test.js"}
```

**Root Cause**: NFR-001 (Tech Stack NFR) failed, so tech stack was never extracted

**Chain of Failure**:
1. Line 3: `{"event_type": "story_failed", "data": {"story_id": "NFR-001", "reason": "mike_breakdown_failed"}}`
2. Tech stack not extracted from Mike's breakdown
3. Orchestrator's `_run_tests()` checks `vision.get('tech_stack_details', {})`
4. Returns empty dict → defaults to pytest
5. pytest tries to run Node.js tests → fails

**Code Location**: `sprint_orchestrator.py` lines 1186-1201
```python
tech_stack_details = self.vision.get('tech_stack_details', {})
backend = tech_stack_details.get('backend', '').lower()

if 'nodejs' in backend or 'express' in backend:
    test_cmd = ["node", "--test", rel_path]
else:
    test_cmd = ["pytest", str(test_path), "-v", "--tb=short"]  # ← Defaults here
```

**The Real Problem**: When NFR-001 fails, the entire sprint is broken because:
- No tech stack extracted
- Wrong test framework used
- All subsequent tests fail

---

## Fixes Applied

### Fix 1: Updated Jordan's Prompt
**File**: `system_prompts/SPRINT_EXECUTION_QA_system_prompt.txt`

**Added Section** (lines 165-181):
```
1) HTTP SERVER SMOKE TEST (Node.js/Express example pattern)

- Import the server entry point module as defined in Mike's conventions.
- Start the `app` on a random port.
- Make ONE request to the main endpoint for this story.
- Assert that the response status is **not 5xx**.
- **CRITICAL**: Call `res.resume()` to consume the response stream, otherwise the 'end' event will never fire and the test will timeout.
- Close the server in `finally`.

Example pattern (Node.js):
```javascript
const req = http.request({ hostname: 'localhost', port: port, path: '/', method: 'GET' }, (res) => {
  try {
    assert(res.statusCode < 500, 'Response status is 5xx or higher');
    res.resume(); // ← CRITICAL: Consume the stream so 'end' event fires
    res.on('end', () => {
      server.close(() => resolve());
    });
  } catch (err) {
    server.close(() => reject(err));
  }
});
```
```

**Impact**: Jordan will now generate correct HTTP tests that don't timeout

---

### Fix 2: Updated Onboarding Document
**File**: `architect/LLM_ONBOARDING.md`

**Added to Sprint Execution Anti-Patterns** (line 96):
```markdown
- ❌ **DON'T** let Jordan forget `res.resume()` in HTTP tests (causes 120s timeout)
```

**Added to Common Gotchas** (line 214):
```markdown
8. **HTTP tests need res.resume()** - Without it, 'end' event never fires and test times out after 120s
```

**Added Persona Specialization Section** (lines 239-255):
```markdown
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
```

**Impact**: LLMs will understand the persona system better and know about the HTTP test gotcha

---

## NFR-001 JSON Parsing Error - FIXED ✅

### Root Cause Identified (2025-12-08)
**Console log showed**:
```
ERROR - JSON parse error at position 624: Expecting ',' delimiter
ERROR - Failed JSON substring: ...ev-secret-fallback'",
        "cookie_maxAge": 30 * 60 * 1000,
        "resave": false,
```

**The Problem**:
- Mike returned **JavaScript expression** `30 * 60 * 1000` instead of JSON value `1800000`
- JSON parser failed because expressions aren't valid JSON
- Only extracted `['backend', 'frontend', 'database', 'backend_port', 'frontend_port']`
- **Missing `tasks` field** → validation failed → NFR-001 failed

**Why It Happened**:
- Line 363 of Mike's prompt had **contradictory example**:
  ```json
  "cookie_maxAge": "30 * 60 * 1000 (30 minutes)"
  ```
- This contradicted the JSON OUTPUT RULES (lines 466-468) which say:
  ```
  ❌ WRONG: "maxAge": 30 * 60 * 1000
  ✅ CORRECT: "maxAge": 1800000
  ```
- Mike copied the bad example from conventions section instead of following the rules

**The Fix**:
Changed the example to:
```json
"cookie_maxAge": 1800000,
"cookie_maxAge_description": "30 minutes"
```

**Impact**:
- NFR-001 will now parse correctly
- Tech stack will be extracted
- Correct test framework (node --test) will be used
- Sprint execution will work properly

**Files Changed**:
- `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt` (line 363)

---

## Testing the Fixes

### To verify Fix 1 (res.resume()):
1. Run a sprint with NFR-001 (tech stack setup)
2. Check `execution_log_SP-XXX.jsonl` for Jordan's test results
3. Should see: `"test_count": 2, "passed": 2, "failed": 0` (not timeout)

### To verify Fix 2 (onboarding):
1. Start a new LLM session
2. Point them to `architect/LLM_ONBOARDING.md`
3. Ask them to explain base personas vs specialized versions
4. They should mention config files and different prompts per meeting

---

## Summary

**Two distinct problems**:
1. ✅ **FIXED**: Jordan generates HTTP tests without `res.resume()` → 120s timeout
2. ⚠️ **SYMPTOM**: Wrong test framework used when NFR-001 fails → need to fix NFR-001

**Files changed**:
- `system_prompts/SPRINT_EXECUTION_QA_system_prompt.txt` - Added res.resume() pattern
- `architect/LLM_ONBOARDING.md` - Added gotcha + persona specialization explanation

**Next steps**:
1. Test the res.resume() fix in next sprint execution
2. Investigate why NFR-001 is failing (Mike's breakdown)
3. Consider adding validation that NFR-001 must succeed before continuing sprint

---

**End of Diagnosis**

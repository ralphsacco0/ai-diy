# Sprint Execution Improvements - Retry Analysis

**Date:** December 26, 2025  
**Analysis:** Test retry patterns and root causes

---

## Summary

**NFR-001:** 2 attempts (1 retry)  
**US-001:** 3 attempts (2 retries)

---

## Critical Discovery

**Tests are passing on retry WITHOUT any code changes.**

### The Timeline (US-001):

1. **Attempt 1:** Alex implements all 7 tasks → Jordan tests → **ECONNREFUSED** (server not starting)
2. **Attempt 2:** Alex **re-implements ALL 7 tasks from scratch** → Jordan tests → **TypeError: app.address is not a function**
3. **Attempt 3:** Alex **re-implements ALL 7 tasks from scratch again** → Jordan tests → **SUCCESS** ✅

### Key Observation:

- `retry_count=0` for all implementations (not fixes, fresh implementations)
- Same code fails twice, then passes on 3rd attempt
- No code changes between attempts

---

## Root Causes of Retries

### 1. Orchestrator Re-runs Entire Story (Not Targeted Fixes)

**Current behavior:**
- Test fails → Orchestrator discards all work
- Alex re-implements ALL tasks from scratch
- Jordan tests again

**Problem:**
- Wasteful: Re-implementing working code
- Time-consuming: 7 tasks × 3 attempts = 21 implementations
- Doesn't fix actual issues

**Better approach:**
- Test fails → Jordan analyzes failure
- Jordan fixes ONLY the broken file(s)
- Jordan tests again

---

### 2. Timing/Race Condition Issues

**Evidence:**
- ECONNREFUSED: Server not starting in time for tests
- TypeError: `app.address is not a function` (accessing before ready)
- Same code passes on retry (no changes)

**Likely causes:**
- Tests start before server fully initialized
- Database initialization race condition
- Port binding timing issue

---

## Proposed Improvements

### Option 1: Add Test Delays/Retries (Quick Fix)

Add retry logic to Jordan's tests:

```javascript
// Wait for server to be ready
await new Promise(resolve => setTimeout(resolve, 2000));

// Retry failed requests
for (let i = 0; i < 3; i++) {
  try {
    const response = await fetch('http://localhost:3000');
    break; // Success
  } catch (err) {
    if (i === 2) throw err; // Final attempt failed
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}
```

**Pros:** Simple, reduces flaky test failures  
**Cons:** Masks timing issues, slower tests

---

### Option 2: Improve Server Startup Signal (Better Fix)

Have Alex generate code that signals when server is ready:

```javascript
// In server.js
app.listen(port, () => {
  console.log(`Server on port ${port}`);
  console.log('READY'); // Signal for tests
});

// In tests
await waitForOutput(serverProcess, 'READY', 5000);
```

**Pros:** Tests wait for actual readiness  
**Cons:** Requires changes to Mike/Alex prompts

---

### Option 3: Implement Targeted Fixes (Best Long-term)

Change orchestrator to:

1. Test fails → Capture error details
2. Jordan analyzes which file(s) caused failure
3. Jordan fixes ONLY broken files
4. Jordan tests again
5. If still fails after 2 targeted fixes → Re-run entire story

**Pros:** Efficient, fixes actual issues, faster  
**Cons:** More complex orchestrator logic

---

## Recommendation

**Immediate:** Option 1 (add test delays) - reduces flaky failures quickly  
**Long-term:** Option 3 (targeted fixes) - more efficient, better debugging

---

## Implementation Status

- [ ] Option 1: Add test delays/retries to Jordan's test generation
- [ ] Option 2: Add server readiness signals to Mike/Alex prompts
- [ ] Option 3: Implement targeted fix logic in orchestrator

---

## Related Issues Fixed Today

1. ✅ Backend redirect paths (relative vs absolute)
2. ✅ Mike's file visibility (context gap - couldn't see HTML/CSS files)
3. ✅ Invalid file path construction (ForbiddenError from string concatenation)
4. ✅ Wrong path depth calculation (ENOENT from incorrect '..' count)

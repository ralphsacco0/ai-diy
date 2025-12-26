# Proxy-Helper Fix: Comprehensive Analysis

**Date:** December 26, 2025  
**Status:** Partially Implemented - Issues Remain

---

## Table of Contents
1. [Problem Statement](#problem-statement)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Solution Design](#solution-design)
4. [Implementation History](#implementation-history)
5. [Current Status](#current-status)
6. [Known Issues](#known-issues)
7. [Recommendations](#recommendations)
8. [Testing & Reset Information](#testing--reset-information)

---

## Problem Statement

### The Core Issue
Generated applications run behind a reverse proxy at `/yourapp/` on Railway, but the code generation system (Mike and Alex) was producing code with inconsistent path handling, causing:

1. **Redirect failures:** Login redirects to `/dashboard` instead of `/yourapp/dashboard` → 404 Not Found
2. **File serving errors:** `ForbiddenError` and `ENOENT` errors from incorrect path depth calculations
3. **Authentication bugs:** Routes creating separate database instances, causing "Invalid credentials" errors
4. **Development complexity:** Developers (Mike/Alex) had to understand and manually handle proxy path rewriting

### The Deployment Architecture
```
User Request: https://ai-diy-dev-production.up.railway.app/yourapp/login
    ↓
AI-DIY Proxy (FastAPI on port 8000)
    ↓ Rewrites to: http://localhost:3000/login
Generated App (Express on port 3000)
    ↓ Responds with redirect: Location: /dashboard
Proxy Should Rewrite: Location: /yourapp/dashboard
    ↓
User Browser: Redirects to /yourapp/dashboard
```

**The Problem:** Generated apps were writing code that didn't account for the `/yourapp/` prefix, and the proxy wasn't consistently rewriting responses.

---

## Root Cause Analysis

### 1. Inconsistent Path Guidance in Prompts

**Mike's Original Prompt Issues:**
- Instructed "relative paths only" for cross-platform compatibility
- Mixed guidance: absolute paths for backend redirects, relative for frontend
- No clear pattern for file serving path depth calculation
- No guidance on database instance sharing

**Result:** Mike generated inconsistent task descriptions, Alex implemented them inconsistently.

### 2. Proxy Implementation Gaps

**In `main.py` (AI-DIY proxy):**
```python
# Original code - BROKEN
if 'location' in resp_headers:  # Case-sensitive check
    loc = resp_headers['location']
    if loc.startswith('/'):
        resp_headers['location'] = f"/yourapp{loc}"
```

**Issue:** Express sends `Location` header with capital L, but code only checked for lowercase `'location'`. Proxy failed to rewrite redirects.

### 3. Database Instance Anti-Pattern

**Generated Code Pattern (WRONG):**
```javascript
// auth.js
router.post('/login', async (req, res) => {
  let db;
  try {
    db = createDb();      // Creates NEW db instance
    await initDb(db);     // Initializes EMPTY database
    const user = await db.get(...);  // Queries empty db
  } finally {
    if (db) db.close();   // Closes db after each request
  }
});
```

**Result:** Admin user seeded in `server.js` db instance, but `auth.js` queries a different empty db instance → "Invalid credentials" always.

### 4. Path Depth Calculation Errors

**Generated Code Pattern (WRONG):**
```javascript
// From src/routes/auth.js
res.sendFile(__dirname + '/../public/login.html');  // String concatenation
res.sendFile(path.join(__dirname, '..', 'public', 'login.html'));  // Wrong depth
```

**Issues:**
- String concatenation with `..` triggers Express security check → `ForbiddenError`
- Hardcoded `..` depth assumes file location, breaks when file moves
- No automatic calculation based on actual directory depth

---

## Solution Design

### The Proxy-Helper Module Approach

**Core Concept:** Abstract ALL proxy complexity into a single module that developers never need to think about.

**Design Principles:**
1. **Standard Paths Everywhere:** Developers write standard absolute paths (`/dashboard`, `/api/auth/login`)
2. **Transparent Abstraction:** Proxy-helper handles path translations automatically
3. **Single Source of Truth:** One module for all path/redirect logic
4. **Zero Developer Overhead:** Mike and Alex don't need to understand proxy mechanics

### Module Design

**Backend Functions:**
```javascript
// proxy-helper.js
function redirect(res, targetPath) {
  const absolutePath = targetPath.startsWith('/') ? targetPath : `/${targetPath}`;
  res.redirect(absolutePath);  // Proxy rewrites this
}

function sendFile(res, filePath) {
  // Auto-calculates depth from __dirname to project root
  const currentDir = __dirname;
  const projectRoot = process.cwd();
  const currentParts = currentDir.split(path.sep).filter(p => p);
  const rootParts = projectRoot.split(path.sep).filter(p => p);
  const depth = currentParts.length - rootParts.length;
  const upDirs = depth > 0 ? Array(depth).fill('..') : [];
  const fullPath = path.join(__dirname, ...upDirs, filePath);
  res.sendFile(fullPath);
}
```

**Usage Pattern:**
```javascript
// In routes
const { redirect, sendFile } = require('../utils/proxy-helper');

router.post('/login', (req, res) => {
  redirect(res, '/dashboard');  // Standard absolute path
});

router.get('/login', (req, res) => {
  sendFile(res, 'public/login.html');  // Relative to project root
});
```

**Why This Works:**
- Developers write standard code with absolute paths
- `redirect()` ensures paths start with `/`
- Proxy rewrites `Location: /dashboard` to `Location: /yourapp/dashboard`
- `sendFile()` calculates correct depth automatically
- No manual path calculations needed

---

## Implementation History

### Phase 1: Proxy Location Header Fix (Deployed)

**File:** `development/src/main.py`  
**Change:** Made Location header detection case-insensitive

```python
# Before
if 'location' in resp_headers:  # Fails for 'Location'

# After
location_key = None
for key in resp_headers:
    if key.lower() == 'location':
        location_key = key
        break
if location_key:
    loc = resp_headers[location_key]
    if loc.startswith('/'):
        resp_headers[location_key] = f"/yourapp{loc}"
```

**Status:** ✅ Deployed to Railway  
**Commit:** `3dd5360` - "Fix proxy Location header rewriting to be case-insensitive"

### Phase 2: Proxy-Helper Module Template (Deployed)

**File:** `templates/proxy-helper.js`  
**Purpose:** Template for Mike to include in NFR-001 Task 1

**Status:** ✅ Created and committed  
**Commit:** `c4047d2` - Initial proxy-helper implementation

### Phase 3: Mike's Prompt Updates (Deployed)

**File:** `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt`

**Changes Made:**

1. **Section 2: PROXY-HELPER MODULE (lines 103-126)**
   - Mandates proxy-helper.js creation in Task 1
   - Specifies ALL paths use standard absolute format
   - Provides usage examples for redirect() and sendFile()
   - Includes full proxy-helper.js template at end of prompt

2. **Section 5: FILE SERVING (lines 210-226)**
   - Mandates use of proxy-helper sendFile()
   - Prohibits direct res.sendFile() usage
   - Explains why: auto-calculates path depth

3. **Section 7: DATABASE INSTANCE SHARING (lines 168-205)**
   - Mandates single db instance via app.locals.db
   - Prohibits routes from creating separate db instances
   - Explains the "Invalid credentials" bug this prevents

**Status:** ✅ Deployed to Railway  
**Commits:**
- `c4047d2` - Initial proxy-helper guidance
- `ba8cbde` - Database instance sharing pattern

### Phase 4: Alex's Prompt Updates (Deployed)

**File:** `system_prompts/SPRINT_EXECUTION_DEVELOPER_system_prompt.txt`

**Changes Made:**
- Lines 97-124: Proxy-helper usage instructions
- Mandates use of redirect() and sendFile() functions
- Provides examples of correct vs incorrect patterns

**Status:** ✅ Deployed to Railway  
**Commit:** `c4047d2`

### Phase 5: PM Prompt Updates (Deployed)

**File:** `system_prompts/REQUIREMENTS_PM_system_prompt.txt`

**Changes Made:**
- Line 33: Removed "relative paths only" from NFR-001 guidance
- Line 51: Updated EXAMPLE to remove "relative paths only"

**Reason:** Conflicted with proxy-helper's absolute path approach

**Status:** ✅ Deployed to Railway  
**Commits:**
- `c4047d2` - Line 33 fix
- `c539b85` - Line 51 EXAMPLE fix

---

## Current Status

### What's Working ✅

1. **Proxy Location Header Rewriting**
   - Case-insensitive header detection
   - Correctly rewrites `Location: /path` to `Location: /yourapp/path`

2. **Prompt Updates Deployed**
   - Mike knows to create proxy-helper.js
   - Mike knows to use app.locals.db for database sharing
   - Alex knows to use proxy-helper functions
   - PM no longer specifies "relative paths only"

3. **Database Instance Sharing Pattern**
   - Mike's prompt includes correct pattern
   - Should prevent "Invalid credentials" bug in future sprints

### What's Broken ❌

1. **Generated Code Not Using Proxy-Helper**
   - `auth.js` uses `res.redirect()` directly instead of `redirect()`
   - Missing `const { redirect } = require('../utils/proxy-helper');`
   - Result: Redirects fail with 404 Not Found

2. **Mike's Guidance Not Strong Enough**
   - Prompt shows the pattern but doesn't ENFORCE it
   - Alex generates code without importing proxy-helper
   - No validation that proxy-helper is actually used

---

## Known Issues

### Issue 1: auth.js Not Using Proxy-Helper Redirect

**Current Generated Code:**
```javascript
// src/routes/auth.js
const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');

router.post('/login', async (req, res) => {
  // ... auth logic ...
  res.redirect('/dashboard');  // ❌ Direct res.redirect
});
```

**Should Be:**
```javascript
const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const { redirect } = require('../utils/proxy-helper');  // ✅ Import helper

router.post('/login', async (req, res) => {
  // ... auth logic ...
  redirect(res, '/dashboard');  // ✅ Use helper
});
```

**Impact:** Login form submission redirects to `/dashboard` which becomes `/yourapp/dashboard` after proxy rewrite, but subsequent requests fail because routes aren't properly mounted.

### Issue 2: Redundant npm install

**Current Behavior:**
- NFR-001 Task 2: `npm install` (after creating package.json)
- US-001 Task 2: `npm install` (after modifying package.json with SAME dependencies)

**Root Cause:** Mike's prompt doesn't specify to only run npm install when NEW dependencies are added.

**Impact:** Wastes ~10-15 seconds per sprint, slows down execution.

**Status:** Fix attempted but rejected by user - needs different approach.

### Issue 3: Mike's Prompt Enforcement Gap

**Current State:**
- Prompt SHOWS the proxy-helper pattern
- Prompt EXPLAINS why to use it
- Prompt DOESN'T ENFORCE that it must be used

**Result:** Alex generates valid code that doesn't use the helper, causing runtime failures.

**Possible Solutions:**
1. Stronger language: "MUST import proxy-helper" instead of "Use proxy-helper"
2. Add to task description template: "Import proxy-helper: const { redirect } = require('../utils/proxy-helper');"
3. Add validation step that checks if proxy-helper is imported

---

## Recommendations

### Immediate Actions Needed

1. **Strengthen Mike's Prompt Enforcement**
   - Change "USE PROXY-HELPER FUNCTIONS" to "MANDATORY: IMPORT AND USE PROXY-HELPER"
   - Add explicit import statement to task description template
   - Example: "Create src/routes/auth.js: MUST import proxy-helper at top: const { redirect } = require('../utils/proxy-helper');"

2. **Add Validation to Sprint Orchestrator**
   - After Alex generates code, check if files with redirects import proxy-helper
   - Fail the task if proxy-helper not imported when needed
   - Similar to how architectural contract validates file operations

3. **Update Mike's Task Description Pattern**
   - For any route file with redirects, task description MUST include:
     ```
     Import proxy-helper: const { redirect } = require('../utils/proxy-helper');
     Use redirect(res, '/path') for all redirects, NOT res.redirect()
     ```

### Long-term Improvements

1. **Proxy-Helper Validation**
   - Add linting/validation that checks generated code
   - Ensure all `res.redirect()` calls are replaced with `redirect()`
   - Ensure all `res.sendFile()` calls are replaced with `sendFile()`

2. **Better Error Messages**
   - When 404 occurs, check if it's a missing `/yourapp/` prefix
   - Provide actionable error message pointing to proxy-helper issue

3. **Documentation for Mike/Alex**
   - Create a "Common Patterns" section in prompts
   - Include full working examples of routes with redirects
   - Show complete file with all imports and usage

4. **npm install Optimization**
   - Add guidance: "Only run npm install when NEW dependencies added"
   - Check Current Project State for existing dependencies
   - Skip npm install if dependencies unchanged

---

## Testing Checklist

Before considering this fix complete, verify:

- [ ] proxy-helper.js created in NFR-001 Task 1
- [ ] All route files with redirects import proxy-helper
- [ ] All redirects use `redirect(res, '/path')` not `res.redirect()`
- [ ] All file serving uses `sendFile(res, 'path')` not `res.sendFile()`
- [ ] Database instance shared via `app.locals.db`
- [ ] Routes access db via `req.app.locals.db`
- [ ] Login flow works: /yourapp/login → /yourapp/api/auth/login → /yourapp/dashboard
- [ ] No 404 errors on redirects
- [ ] No ForbiddenError or ENOENT on file serving
- [ ] No "Invalid credentials" with correct password
- [ ] npm install runs only once (or when new deps added)

---

## Conclusion

The proxy-helper solution is **architecturally sound** but **incompletely implemented**. The core design is correct:

✅ **Good Design:**
- Single abstraction module for all proxy complexity
- Standard absolute paths everywhere
- Automatic path depth calculation
- Database instance sharing pattern

❌ **Implementation Gap:**
- Mike's prompt guidance not strong enough
- Alex not consistently importing/using proxy-helper
- No validation that the pattern is followed

**Next Steps:**
1. Strengthen Mike's prompt with MANDATORY language
2. Add explicit import statements to task descriptions
3. Consider validation/linting step in sprint orchestrator
4. Re-run sprint and verify all checklist items pass

The solution is **90% there** - just needs stronger enforcement in the prompt system to ensure Mike specifies and Alex implements the proxy-helper pattern consistently.

---

## Testing & Reset Information

### Backlog Backup for Testing

**Location:** `/app/development/src/static/appdocs/backlog/backups/Backlog_20251226_011658_proxy_helper.csv`

**Purpose:** Clean backlog with proxy-helper compatible NFR-001 (no "relative paths only" references)

**Created:** December 26, 2025 at 01:16:58 UTC

**Contents:**
- NFR-001: Development Environment Setup (with proxy-helper requirements)
- STYLE-001: UI Style Guide
- US-001: User Authentication
- US-999: Application Shell and Navigation
- Additional user stories for HR system

**How to Restore:**
```bash
# On Railway
railway ssh "cp /app/development/src/static/appdocs/backlog/backups/Backlog_20251226_011658_proxy_helper.csv /app/development/src/static/appdocs/backlog/Backlog.csv"
```

**When to Use:**
- Before re-running sprints to test proxy-helper fixes
- After failed sprint runs that corrupt the backlog
- When resetting to known-good state for debugging

**Verification After Restore:**
```bash
# Verify no "relative paths" references
railway ssh "grep -i 'relative' /app/development/src/static/appdocs/backlog/Backlog.csv"
# Should return exit code 1 (no matches)

# Count stories
railway ssh "grep -c '^\"' /app/development/src/static/appdocs/backlog/Backlog.csv"
# Should return 8 (header + 7 stories)
```

### Sprint Reset Procedure

**When to Reset:**
- After identifying prompt issues that need fixing
- Before testing updated prompts
- When generated code has critical bugs

**Reset Steps:**
1. Stop generated app: `POST /api/control-app {"action": "stop"}`
2. Restore backlog from backup (see above)
3. Verify prompt updates are deployed to Railway
4. Clear execution-sandbox if needed
5. Re-run sprint with updated prompts

### Testing Workflow

**Recommended Testing Sequence:**
1. Make prompt changes locally
2. Commit and push to GitHub
3. Deploy to Railway (`railway up`)
4. Restore clean backlog from backup
5. Run sprint
6. Verify generated code uses proxy-helper
7. Test login flow end-to-end
8. Check for issues in this document's checklist

**Key Files to Inspect After Sprint:**
- `/app/development/src/static/appdocs/execution-sandbox/client-projects/BrightHR_Lite_Vision/src/routes/auth.js`
- `/app/development/src/static/appdocs/execution-sandbox/client-projects/BrightHR_Lite_Vision/src/server.js`
- `/app/development/src/static/appdocs/execution-sandbox/client-projects/BrightHR_Lite_Vision/src/utils/proxy-helper.js`

**What to Look For:**
- `auth.js` imports proxy-helper: `const { redirect } = require('../utils/proxy-helper');`
- `auth.js` uses `redirect(res, '/path')` not `res.redirect('/path')`
- `server.js` has `app.locals.db = db;` before routes are mounted
- `proxy-helper.js` exists and matches template

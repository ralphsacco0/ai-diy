# Prompt Hardcoding Analysis & Fixes

**Date:** 2025-11-25  
**Issue:** Module system conflicts due to hardcoding in prompts

---

## Summary of Findings:

### ✅ Python Code: CLEAN
- No hardcoded module systems
- No hardcoded package.json templates
- Architecture flows correctly: Mike outputs → Orchestrator saves → Alex reads

### ✅ Mike's Prompt (Architect): MOSTLY GOOD
- **Good:** Mike has freedom to choose module system
- **Problem:** Too prescriptive about WHICH technologies to use
- **Fixed:** Removed specific tech recommendations, made guidance generic

### ❌ Alex's Prompt (Developer): HARDCODED
- **Problem:** Forces ES6 modules regardless of Mike's decision
- **Needs Fix:** Remove hardcoding, follow Mike's conventions

### ✅ Recovery Prompts: CLEAN
- Used only for syntax error fixes
- No hardcoding found

---

## Changes Made:

### 1. Mike's Prompt - Created Clean Version

**File:** `/system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt_CLEAN.txt`

**Changes:**
- ❌ Removed: "Use express-session if..." (lines 78-82, 279-283)
- ❌ Removed: "bcrypt is recommended" (line 283)
- ❌ Removed: Prescriptive auth guidance
- ✅ Added: Generic guidance to analyze requirements and choose appropriate tech
- ✅ Added: Emphasis on documenting complete decisions in conventions

**Key Addition:**
```
4. AUTHENTICATION METHOD:
   ✓ For NFR-001: Read ALL sprint stories first to understand auth requirements
   ✓ Determine what the auth system needs to do:
     - Does it need to track server-side state? (sessions, timeouts, logout clearing)
     - Can it be stateless? (tokens only)
     - What are the security requirements?
   ✓ Choose an auth approach that satisfies ALL requirements
   ✓ Choose appropriate password hashing library for your stack
   ✓ Document your complete auth pattern in conventions
```

---

## Next Steps - Alex's Prompt Needs Fixing:

### Current Problem in Alex's Prompt:

**Line 37:**
```
ALL Node.js projects use ES modules ("type": "module" in package.json).
```

**Lines 474, 492, 516:** Examples showing `"type": "module"`

**This OVERRIDES Mike's decision!**

---

### Proposed Fix for Alex's Prompt:

**Replace Line 37-95 (ES Modules section) with:**

```
🚨 CRITICAL: FOLLOW MIKE'S ARCHITECTURAL DECISIONS

Mike (the architect) has defined the module system in his conventions.
You MUST follow his decision EXACTLY.

CHECK MIKE'S CONVENTIONS:
Look for "module_system" in the conventions you receive.

IF Mike specifies "module_system": "ES6" or "es6":
- Use import/export syntax throughout
- Add "type": "module" to package.json
- For __dirname, use this pattern:
  ```javascript
  import path from 'path';
  import { fileURLToPath } from 'url';
  import { dirname } from 'path';
  
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);
  ```

IF Mike specifies "module_system": "CommonJS" or "commonjs":
- Use require/module.exports syntax throughout
- Do NOT add "type": "module" to package.json
- __dirname is available natively (no imports needed)
- Example:
  ```javascript
  const express = require('express');
  const db = require('./db');
  
  module.exports = { app };
  ```

CRITICAL: Never mix module systems. Follow Mike's choice consistently across ALL files.
```

**Replace Lines 470-527 (package.json examples) with:**

```
Example package.json structure (adapt based on Mike's module_system choice):

// If Mike chose ES6 modules:
{
  "name": "app",
  "version": "1.0.0",
  "type": "module",  // ← ONLY if ES6
  "dependencies": { ... },
  "scripts": {
    "start": "node src/server.js",
    "test": "NODE_ENV=test node --test"
  }
}

// If Mike chose CommonJS:
{
  "name": "app",
  "version": "1.0.0",
  // NO "type" field for CommonJS
  "dependencies": { ... },
  "scripts": {
    "start": "node src/server.js",
    "test": "NODE_ENV=test node --test"
  }
}
```

---

## Testing Plan:

1. ✅ Replace Mike's prompt with clean version
2. ⏳ Fix Alex's prompt to follow Mike's decisions
3. ⏳ Update NFR-001 or keep as-is (decision pending)
4. ⏳ Re-run Sprint 1
5. ⏳ Verify:
   - Mike chooses module system based on requirements
   - Alex follows Mike's choice
   - No module system conflicts
   - Tests pass

---

## Architecture Flow (Correct):

```
Vision Statement
    ↓
Requirements (NFR-001)
    ↓
Mike reads requirements
    ↓
Mike chooses complete tech stack
    ↓
Mike outputs conventions JSON
    ↓
Orchestrator saves to architecture.json
    ↓
Alex reads conventions
    ↓
Alex implements following conventions
    ↓
Tests run successfully
```

**No hardcoded files needed!**
**No prescriptive tech choices!**
**Everything flows from requirements!**

---

## Current NFR-001 Requirements:

```
"Database: SQLite via sqlite3 npm package (v5.1+)"
"Use sqlite3 package (NOT better-sqlite3)"
"Callback-based API: db.run(), db.get(), db.all() with callback functions"
"Pattern: Wrap all database callbacks in Promises for async/await compatibility"
```

**This is valid!** Mike can work with this.

Mike will likely choose:
- Module system: CommonJS (natural fit for callbacks)
- Database package: sqlite3 (as specified)
- Import pattern: require/module.exports

**As long as Alex follows Mike's decision, it will work!**

---

**Status:** Mike's prompt cleaned ✅  
**Next:** Fix Alex's prompt to remove hardcoding

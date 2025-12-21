# Module System Conflict - Root Cause Analysis

**Date:** 2025-11-25  
**Sprint:** Sprint 1 (Re-run), Story NFR-001  
**Error:** `ReferenceError: require is not defined in ES module scope`

---

## 🎯 Root Cause Found

**Mike (Architect) is choosing CommonJS, but the system requires ES modules.**

---

## The Conflict Chain

### 1. **APPROVED_TECH_STACK.json** (Line 29, 182)
```json
{
  "package_json_template": {
    "type": "module",  // ← REQUIRES ES modules
  },
  "validation_rules": {
    "package_json_must_have": [
      "type: module (for ES6 imports)"  // ← EXPLICIT requirement
    ]
  }
}
```

**Says:** Use ES modules (`import/export`)

---

### 2. **Mike's System Prompt** (Line 260-261)
```
2. MODULE SYSTEM CONSISTENCY:
   ✓ Choose ES6 modules OR CommonJS (pick one, not both)
```

**Says:** Mike has the FREEDOM to choose either

---

### 3. **Mike's Decision** (Execution Log)
```json
{
  "technical_notes": "Initial project setup follows requirements: CommonJS modules, ..."
}
```

**Mike chose:** CommonJS (`require/module.exports`)

---

### 4. **Alex's System Prompt** (Line 34-37)
```
🚨 CRITICAL: ES MODULES + MANDATORY IMPORTS (READ THIS FIRST!)

ALL Node.js projects use ES modules ("type": "module" in package.json).

✅ MANDATORY IMPORTS FOR EVERY FILE THAT NEEDS FILE PATHS:
```javascript
import path from 'path';
import { fileURLToPath } from 'url';
```

**Says:** ALWAYS use ES modules

---

### 5. **Alex's Implementation**
```javascript
// src/db.js
const sqlite3 = require('sqlite3');  // ← CommonJS (following Mike)
const bcrypt = require('bcrypt');
```

**Alex used:** CommonJS (following Mike's breakdown)

---

### 6. **package.json Generated**
```json
{
  "type": "module"  // ← ES modules (from APPROVED_TECH_STACK template)
}
```

**Result:** ES module mode enabled

---

### 7. **Runtime Error**
```
ReferenceError: require is not defined in ES module scope
```

**Why:** `package.json` says ES modules, but code uses CommonJS

---

## Why This Happened

### Mike's Perspective:
1. Mike reads his system prompt: "Choose ES6 modules OR CommonJS"
2. Mike has FREEDOM to choose
3. Mike chooses CommonJS (perhaps because requirements mention sqlite3 which is callback-based?)
4. Mike tells Alex: "Use CommonJS modules"

### Alex's Perspective:
1. Alex reads his system prompt: "ALL Node.js projects use ES modules"
2. Alex reads Mike's breakdown: "CommonJS modules"
3. **CONFLICT:** System prompt says ES, Mike says CommonJS
4. Alex follows Mike (the architect) → Uses CommonJS syntax
5. But `package.json` template from APPROVED_TECH_STACK has `"type": "module"`
6. **CRASH:** CommonJS code in ES module mode

---

## The Disconnect

**There are THREE sources of truth:**

1. **APPROVED_TECH_STACK.json** → Says: ES modules (line 29, 182)
2. **Mike's system prompt** → Says: Choose either (line 260-261)
3. **Alex's system prompt** → Says: Always ES modules (line 34-37)

**Mike doesn't know about #1 and #3!**

---

## Why Mike Chose CommonJS

Looking at the requirements for NFR-001:
```
Database: SQLite via sqlite3 npm package (v5.1+)
Callback-based API: db.run(), db.get(), db.all() with callback functions
Pattern: Wrap all database callbacks in Promises for async/await compatibility
```

**Hypothesis:** Mike saw "sqlite3" and "callback-based API" and thought CommonJS was more appropriate for callback-style code.

**But:** The APPROVED_TECH_STACK actually says to use `better-sqlite3` (line 110-119), not `sqlite3`!

---

## Additional Issues Found

### Issue 1: sqlite3 vs better-sqlite3
**Requirements say:** `sqlite3` package (callback-based)  
**APPROVED_TECH_STACK says:** `better-sqlite3` (synchronous, ES module friendly)  
**APPROVED_TECH_STACK also says:** `sqlite3` is DEPRECATED (line 131-136)

```json
{
  "name": "sqlite3",
  "status": "DEPRECATED - Use better-sqlite3 instead",
  "rationale": "better-sqlite3 is faster and has synchronous API"
}
```

### Issue 2: bcrypt not installed
**Generated code uses:** `bcrypt`  
**Actually installed:** `bcryptjs` (from previous run)  
**Should use:** `bcrypt@^5.1.1` per APPROVED_TECH_STACK (line 122-129)

---

## The Fix

### Option 1: Make Mike Aware of ES Module Requirement (RECOMMENDED)

**Update Mike's system prompt to:**
1. Reference APPROVED_TECH_STACK.json
2. Make ES modules the DEFAULT for Node.js projects
3. Only allow CommonJS if explicitly required by user

**Changes needed:**
```
CRITICAL: For Node.js projects, ALWAYS use ES modules unless user explicitly requires CommonJS.

Check APPROVED_TECH_STACK.json for the correct package.json template.
The template includes "type": "module" - this is MANDATORY for all Node.js projects.

Module system choice:
- Node.js projects: ES modules (import/export) - LOCKED, not negotiable
- Python projects: Native imports (no choice needed)

If you output CommonJS syntax (require/module.exports) for a Node.js project,
Alex will generate code that crashes at runtime.
```

---

### Option 2: Remove Mike's Freedom to Choose

**Update Mike's system prompt line 260-261:**

**Before:**
```
2. MODULE SYSTEM CONSISTENCY:
   ✓ Choose ES6 modules OR CommonJS (pick one, not both)
```

**After:**
```
2. MODULE SYSTEM CONSISTENCY (LOCKED FOR NODE.JS):
   ✓ Node.js projects: ALWAYS use ES6 modules (import/export)
   ✓ Python projects: Use native imports
   ✓ This is NOT negotiable - package.json template has "type": "module"
   ✓ If you specify CommonJS, Alex's code will crash at runtime
```

---

### Option 3: Pass APPROVED_TECH_STACK to Mike

**Update `_call_mike()` in sprint_orchestrator.py:**

Add APPROVED_TECH_STACK.json to Mike's context so he knows the constraints:

```python
# Load approved tech stack
tech_stack_file = Path(__file__).parent.parent.parent / "system_prompts" / "APPROVED_TECH_STACK.json"
approved_tech_stack = json.loads(tech_stack_file.read_text())

user_message = f"""
{context_header}

APPROVED TECH STACK (YOUR CONSTRAINTS):
{json.dumps(approved_tech_stack, indent=2)}

CRITICAL: Follow the package.json template EXACTLY.
If it has "type": "module", you MUST specify ES6 modules in your conventions.
...
"""
```

---

## Recommended Solution

**Combine all three options:**

1. ✅ **Update Mike's system prompt** to make ES modules mandatory for Node.js
2. ✅ **Pass APPROVED_TECH_STACK** to Mike so he sees the constraints
3. ✅ **Add validation** in orchestrator to check if Mike's module choice matches package.json template

---

## Additional Fixes Needed

### Fix 1: Update NFR-001 Requirements
**Current:** "SQLite via sqlite3 npm package (v5.1+)"  
**Should be:** "SQLite via better-sqlite3 npm package (v11.0+)"

**Rationale:** APPROVED_TECH_STACK marks sqlite3 as deprecated

### Fix 2: Ensure bcrypt is installed
**Current:** Only bcryptjs is installed  
**Should be:** bcrypt@^5.1.1 per APPROVED_TECH_STACK

---

## Impact Assessment

### Stories Affected:
- ✅ **NFR-001:** Will be fixed by this change
- ✅ **US-009:** Will work correctly (no more module conflicts)
- ✅ **Sprint 2:** Will avoid the bcrypt/bcryptjs confusion

### Token Impact:
- Adding APPROVED_TECH_STACK to Mike's context: ~2K tokens
- Worth it to prevent runtime errors

### Breaking Changes:
- None - this enforces what was already intended

---

## Testing Plan

1. Update Mike's system prompt with ES module requirement
2. Add APPROVED_TECH_STACK to Mike's context
3. Re-run Sprint 1 NFR-001
4. Verify Mike outputs: `"module_system": "ES6"` in conventions
5. Verify Alex generates: `import` statements (not `require`)
6. Verify package.json has: `"type": "module"`
7. Verify tests pass without module errors

---

**Status:** Root cause identified, solution designed, ready to implement  
**Next Step:** Update Mike's system prompt and orchestrator context

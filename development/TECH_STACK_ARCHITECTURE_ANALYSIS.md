# Tech Stack Architecture - Proper Flow Analysis

**Date:** 2025-11-25  
**Issue:** APPROVED_TECH_STACK.json is unused, Mike choosing CommonJS conflicts with reality

---

## ✅ The CORRECT Architecture (As Designed)

### Flow:
```
Vision Statement
    ↓
Requirements (NFR-001)
    ↓
Mike reads NFR-001 requirements
    ↓
Mike infers tech stack from requirements
    ↓
Mike defines conventions (including module system)
    ↓
Alex implements following Mike's conventions
```

### Key Quote from Mike's System Prompt (Line 349):
```
"Infer tech stack from acceptance criteria (don't assume)"
```

**This is the RIGHT approach** - no hardcoded tech stack file!

---

## ❌ The Problem: APPROVED_TECH_STACK.json

### Status: **UNUSED / HALF-BAKED**

**Evidence:**
```bash
$ grep -r "APPROVED_TECH_STACK" --include="*.py" .
# NO RESULTS - Nobody loads or reads this file!
```

**Conclusion:** This file was created as a shortcut but never wired up. It's dead code.

---

## 🔍 What Actually Happened

### NFR-001 Requirements Say:
```
"Backend framework and version: Node.js v18+ with Express"
"Database: SQLite via sqlite3 npm package (v5.1+)"
"Callback-based API: db.run(), db.get(), db.all() with callback functions"
"Pattern: Wrap all database callbacks in Promises for async/await compatibility"
```

### Mike's Interpretation:
1. Saw "sqlite3" (callback-based)
2. Saw "callback functions" mentioned explicitly
3. Thought: "Callbacks = CommonJS is more natural"
4. Decided: `"module_system": "CommonJS"`

### The Missing Guidance:
**NFR-001 requirements DON'T specify:**
- ❌ Module system (ES6 vs CommonJS)
- ❌ Import/export pattern
- ❌ `"type": "module"` in package.json

**Mike had to guess!**

---

## 🎯 Root Cause

### The Real Problem:
**NFR-001 requirements are incomplete** - they don't specify the module system.

### Why Mike Chose Wrong:
1. Requirements mention "callback-based API"
2. Requirements mention "sqlite3" (old package)
3. No explicit guidance on module system
4. Mike inferred: CommonJS (reasonable guess given callbacks)

### Why It Failed:
1. Alex's system prompt says: "ALL Node.js projects use ES modules"
2. Alex follows Mike's CommonJS decision (architect overrides)
3. But Alex also generates `"type": "module"` in package.json (from his prompt)
4. **CONFLICT:** CommonJS code in ES module mode

---

## 🔧 The Proper Fix

### Option 1: Update NFR-001 Requirements (RECOMMENDED)

**Add to NFR-001 requirements:**
```
"Module System: ES6 modules (import/export syntax)"
"Package.json must include: \"type\": \"module\""
"All files use import/export, not require/module.exports"
```

**Why this is correct:**
- Follows the designed architecture (requirements → Mike → conventions)
- No hardcoded tech stack file needed
- Mike reads requirements and follows them
- Clear, explicit guidance

---

### Option 2: Add Module System Guidance to Mike's Prompt

**Add to Mike's system prompt (after line 331):**
```
11. MODULE SYSTEM (Node.js projects):
   - For Node.js projects, ALWAYS use ES6 modules unless requirements explicitly say CommonJS
   - Default: "module_system": "ES6", package.json includes "type": "module"
   - Use import/export syntax, not require/module.exports
   - Only use CommonJS if requirements explicitly require it (rare)
   - Rationale: ES6 modules are the modern standard, better tooling support
```

**Why this works:**
- Gives Mike a default when requirements are silent
- Still allows requirements to override if needed
- No hardcoded file needed

---

### Option 3: Update Vision Statement

**Add to Vision technical constraints:**
```
"All Node.js code must use ES6 modules (import/export)"
"Package.json must include \"type\": \"module\""
```

**Why this works:**
- Vision is the source of truth
- Mike reads vision and follows it
- Consistent across all sprints

---

## 📋 Additional Fixes Needed

### Fix 1: sqlite3 → better-sqlite3

**Current NFR-001:**
```
"Database: SQLite via sqlite3 npm package (v5.1+)"
"Callback-based API: db.run(), db.get(), db.all() with callback functions"
```

**Should be:**
```
"Database: SQLite via better-sqlite3 npm package (v11.0+)"
"Synchronous API: db.prepare().run(), get(), all()"
"No callbacks needed - synchronous operations"
```

**Why:**
- `better-sqlite3` is faster, more modern
- Synchronous API is simpler (no Promise wrapping needed)
- Works perfectly with ES6 modules
- `sqlite3` is callback-based (feels like CommonJS era)

---

### Fix 2: Clarify Alex's System Prompt

**Current (Line 34-37):**
```
🚨 CRITICAL: ES MODULES + MANDATORY IMPORTS (READ THIS FIRST!)

ALL Node.js projects use ES modules ("type": "module" in package.json).
```

**Problem:** This is too absolute - what if Mike's conventions say CommonJS?

**Should be:**
```
🚨 CRITICAL: FOLLOW MIKE'S MODULE SYSTEM DECISION

Mike's conventions will specify the module system (ES6 or CommonJS).
FOLLOW HIS DECISION EXACTLY.

If Mike specifies ES6 modules:
- Use import/export syntax
- Package.json must have "type": "module"
- Use the __dirname pattern shown below

If Mike specifies CommonJS:
- Use require/module.exports syntax
- Package.json must NOT have "type": "module"
- __dirname is available natively
```

**Why:** Removes conflict between Mike and Alex

---

## 🎯 Recommended Solution

**Implement all three options:**

1. ✅ **Update NFR-001 requirements** to specify ES6 modules explicitly
2. ✅ **Add default to Mike's prompt** (ES6 unless requirements say otherwise)
3. ✅ **Update Alex's prompt** to follow Mike's decision (not override it)

**Also:**
4. ✅ **Change sqlite3 → better-sqlite3** in requirements
5. ✅ **Delete APPROVED_TECH_STACK.json** (unused, confusing)

---

## 📝 What APPROVED_TECH_STACK.json Should Have Been

If we were to use a tech stack file (we shouldn't), it should be:

**Purpose:** Validation only, not decision-making
**Usage:** Check Mike's decisions against known-good patterns
**Example:**
```python
# After Mike makes decisions, validate them:
if mike_tech_stack["database"] == "sqlite3":
    logger.warning("sqlite3 is deprecated, suggest better-sqlite3")
    
if mike_tech_stack["module_system"] == "CommonJS" and mike_tech_stack["backend"] == "nodejs":
    logger.warning("CommonJS is legacy, suggest ES6 modules")
```

**But even this is wrong** - requirements should be the source of truth, not a validation file.

---

## ✅ Proper Architecture Summary

### Source of Truth Hierarchy:
1. **Vision Statement** - High-level technical direction
2. **Requirements (NFR-001)** - Specific tech stack decisions
3. **Mike's Conventions** - Detailed implementation patterns
4. **Alex's Code** - Follows Mike's conventions exactly

### No Hardcoded Files Needed:
- ❌ APPROVED_TECH_STACK.json
- ❌ Tech stack templates
- ❌ Validation files

### Everything Flows From:
- ✅ Vision
- ✅ Requirements
- ✅ Mike's analysis

---

## 🔄 Implementation Steps

1. **Update NFR-001 requirements** (add module system specification)
2. **Update Mike's system prompt** (add ES6 default guidance)
3. **Update Alex's system prompt** (follow Mike, don't override)
4. **Delete APPROVED_TECH_STACK.json** (unused, confusing)
5. **Update Vision** (add ES6 module constraint if desired)
6. **Re-run Sprint 1** (verify Mike chooses ES6 correctly)

---

**Status:** Architecture properly understood, fixes identified  
**Next:** Update requirements and prompts, remove dead code

# Sonnet Turnover Document

**Date**: November 26, 2025  
**Issue**: Sprint Review Alex generating HTML-encoded content and hallucinating routes  
**Status**: Cascade made changes that may be out of scope - needs review

---

## THE PROBLEM

### What Happened
During Sprint 2 review, user reported that Sprint Review Alex (SPRINT_REVIEW_ALEX) generated `admin.html` with:
1. **HTML-encoded content** - `&lt;html&gt;` instead of `<html>`
2. **Hallucinated routes** - Links to `/search-employees`, `/add-employee`, `/approve-leaves`, `/documents` that don't exist
3. **Missing actual functionality** - Only showed logout button

### Root Cause Analysis (What We Found)

**Sprint Execution Alex (SPRINT_EXECUTION_DEVELOPER) writes HTML correctly because:**
- Gets wireframe HTML files from `/static/appdocs/backlog/wireframes/`
- Gets project context (existing files, routes, patterns)
- Gets architecture conventions
- Gets Mike's task breakdown
- NO hardcoded examples in prompt
- Context-driven approach

**Sprint Review Alex (SPRINT_REVIEW_ALEX) writes HTML incorrectly because:**
- NO wireframes
- NO project state (existing files, routes)
- Hardcoded examples in prompt (lines 55-56): "Login issue → read_file('ProjectName/src/routes/auth.js')"
- Instruction-driven approach (tells Alex HOW to do his job)
- Conflicting instructions

**Key Files Reviewed:**
- `/system_prompts/SPRINT_REVIEW_ALEX_system_prompt.txt` - Has hardcoded examples
- `/system_prompts/personas_config.json` - SPRINT_REVIEW_ALEX gets: vision, backlog, architecture (NO wireframes)
- `/development/src/services/sprint_orchestrator.py` lines 2437-2640 - Shows Sprint Execution Alex gets wireframes + project context
- `/development/src/services/ai_gateway.py` lines 618-715 - Bounded loop for Sprint Review (Investigation + Execution modes)
- `/development/src/streaming.py` lines 468-498 - Context injection for personas

---

## THE AGREED FIX

### What Should Be Done

**Make Sprint Review Alex context-driven like Sprint Execution Alex:**

1. **Add context injection** (similar to Sprint Execution)
   - Project state (existing files in execution sandbox)
   - Routes (extracted from server.js)
   - Wireframes (from wireframes folder)
   - File summaries (what code exists)

2. **Simplify the prompt** (remove hardcoded examples)
   - Remove lines 55-56 hardcoded file paths
   - Remove conflicting instructions
   - Trust Alex to use tools (list_directory, read_file)
   - Trust architecture context to guide him

3. **Update documentation**
   - Document the pattern in PATTERNS_AND_METHODS.md
   - Note that Sprint Review Alex gets same context as Sprint Execution Alex

---

## WHAT CASCADE DID (NEEDS REVIEW)

### Changes Made to `/development/src/services/ai_gateway.py`

**Lines 618-715 (Investigation Mode):**
- Added project name extraction from architecture context
- Added file scanning (all .js, .html, .css, .json files)
- Added route extraction from server.js
- Added wireframe loading (up to 3 wireframes)
- Injected all this as "PROJECT STATE" before investigation instructions
- Updated investigation instructions to reference PROJECT STATE

**Execution Mode:**
- Started to make changes but user canceled
- NO changes applied to execution mode

### Concerns About These Changes

**User stopped Cascade because:**
1. **Scope question**: Should context be injected in `streaming.py` (persona-level) or `ai_gateway.py` bounded loop (investigation-level)?
2. **Performance**: Scanning files and loading wireframes on EVERY investigation (even unrelated issues)
3. **Context bloat**: Potentially thousands of tokens added every time
4. **Wrong approach?**: Force-feeding context vs. letting Alex use tools to get what he needs

---

## QUESTIONS FOR NEXT LLM

### Critical Decisions Needed

1. **WHERE should context be injected?**
   - Option A: `/development/src/streaming.py` (persona-level, like vision/backlog/architecture)
   - Option B: `/development/src/services/ai_gateway.py` bounded loop (investigation-level, what Cascade did)

2. **WHAT context should be injected?**
   - Project state (files, routes)?
   - Wireframes?
   - Or should Alex just use his tools (list_directory, read_file) to get this?

3. **HOW to prevent HTML encoding?**
   - Is this a prompt issue?
   - Is this an LLM behavior issue?
   - Does providing wireframes solve it (gives Alex HTML template to copy)?

4. **Should we revert Cascade's changes?**
   - Are they correct but in wrong place?
   - Are they fundamentally wrong approach?
   - Should we start over?

---

## REFERENCE INFORMATION

### Sprint Execution Context Injection (Working Example)

**File**: `/development/src/services/sprint_orchestrator.py`

**Lines 2437-2443**: Loads wireframe
```python
wireframe_html = ""
wireframe_ref = story.get("Wireframe_Ref", "")
if wireframe_ref:
    wireframe_path = WIREFRAME_DIR / f"{wireframe_ref}.html"
    if wireframe_path.exists():
        wireframe_html = wireframe_path.read_text(encoding="utf-8")
```

**Lines 2456-2491**: Gets project context
- Calls `_get_project_context(project_name)` 
- Calls `_get_file_summaries()` for existing code
- Calls `_get_existing_patterns()` for established patterns

**Lines 2617-2640**: Passes to Alex
```python
user_message = f"""{context_header}

{retry_history_prompt}{backlog_context}

PROJECT CONTEXT:
{project_context}

EXISTING FILES YOU CAN IMPORT FROM:
{file_summaries}

ESTABLISHED CODE PATTERNS:
{existing_patterns}
{architect_design}
IMPLEMENT THIS TASK:
...
Wireframe:
{wireframe_html if wireframe_html else 'No wireframe'}
```

### Current Sprint Review Context Injection

**File**: `/development/src/streaming.py` lines 468-498

Currently injects for SPRINT_REVIEW_ALEX:
- Vision
- Backlog  
- Architecture (tech stack + conventions)

Does NOT inject:
- Wireframes
- Project state
- File summaries
- Existing patterns

---

## FILES TO REVIEW

1. `/development/src/services/ai_gateway.py` lines 618-715 - Cascade's changes (may need revert)
2. `/system_prompts/SPRINT_REVIEW_ALEX_system_prompt.txt` - Needs hardcoded examples removed
3. `/development/src/streaming.py` lines 468-498 - Possible location for context injection
4. `/development/src/services/sprint_orchestrator.py` lines 2426-2660 - Reference for how Sprint Execution does it
5. `/architect/PATTERNS_AND_METHODS.md` - Needs documentation update

---

## USER CONSTRAINTS

1. **ONLY update files in DOCUMENTATION_INDEX.md** - Don't create new docs
2. **Context over instructions** - Give Alex context, not step-by-step instructions
3. **No hardcoding** - Removed hardcoding from sprint execution, don't add it back
4. **Follow existing patterns** - Sprint Review should work like Sprint Execution
5. **Explain changes in plain English** - User is not technical, needs clear explanations

---

## NEXT STEPS

1. **Decide**: Revert Cascade's changes or fix them?
2. **Decide**: Where to inject context (streaming.py vs ai_gateway.py)?
3. **Decide**: What context to inject (wireframes? project state? both? neither?)?
4. **Execute**: Make changes based on decisions
5. **Document**: Update PATTERNS_AND_METHODS.md

---

## CONTACT

User: ralph  
Project: AI-DIY (ai-diy-scrum-app)  
Location: `/Users/ralph/Documents/NoHub/ai-diy/`

**Good luck. Don't make it worse.**

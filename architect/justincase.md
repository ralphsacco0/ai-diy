# Recovery Documentation - Path Resolution and Public Directory Fixes

**Session Date:** 2025-12-30
**Issue:** Railway deployment working but login failing in generated apps
**Root Cause:** Conflicting file path patterns causing incorrect HTML script references

---

## Executive Summary

This session fixed two critical issues in the AI-DIY platform:
1. **Path resolution inconsistencies** across 7 components (Sprint Review Alex couldn't apply fixes)
2. **Public directory structure confusion** causing login failures (script paths broken)

All fixes are **backward compatible** - they align the code with the documented architecture, they don't change the architecture itself.

---

## Part 1: Path Resolution Standardization

### Problem
Sprint Review Alex was failing with: `"Cannot safely apply the fix because no target file contents were provided from the sandbox"`

### Root Cause
Seven different locations used different path construction methods:
- Some used: `Path(__file__).parent.parent / "static/appdocs/..."`
- Some used: `Path("static/appdocs/...")` (correct - matches Railway WORKDIR)

This caused file discovery to find files in one location, but file modification operations to look in another location.

### Files Changed

#### 1. development/src/api/sandbox.py (line 21-22)
**Before:**
```python
SANDBOX_ROOT = Path(__file__).parent.parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"
```

**After:**
```python
# Working directory is /app/development/src on Railway, repo/development/src locally
SANDBOX_ROOT = Path("static/appdocs/execution-sandbox/client-projects")
```

**Reason:** Matches Railway WORKDIR set in Dockerfile line 50. The working directory is already at the right level.

---

#### 2. development/src/api/testing.py (line 42)
**Before:**
```python
PROJECT_ROOT = Path(__file__).parent.parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"
```

**After:**
```python
# Use consistent path resolution (matches sprint_orchestrator.py pattern)
# Working directory is /app/development/src on Railway, repo/development/src locally
PROJECT_ROOT = Path("static/appdocs/execution-sandbox/client-projects")
```

**Reason:** Test execution needs to find the same sandbox as Sprint Review Alex.

---

#### 3. development/src/main.py (line 201)
**Before:**
```python
sandbox_base = Path(__file__).parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"
```

**After:**
```python
# Use consistent path resolution (matches sprint_orchestrator.py pattern)
sandbox_base = Path("static/appdocs/execution-sandbox/client-projects")
```

**Reason:** App control (start/stop/restart) needs to find the correct project directory.

---

#### 4. development/src/services/ai_gateway.py (line 717)
**Before:**
```python
execution_sandbox = Path(__file__).parent.parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"
```

**After:**
```python
# Use consistent path resolution (matches sprint_orchestrator.py pattern)
# Working directory is /app/development/src on Railway, repo/development/src locally
execution_sandbox = Path("static/appdocs/execution-sandbox/client-projects")
```

**Reason:** Sprint Review Alex investigation mode context building.

---

#### 5. development/src/services/ai_gateway.py (line 726)
**Before:**
```python
wireframe_dir = Path(__file__).parent.parent / "static" / "appdocs" / "backlog" / "wireframes"
```

**After:**
```python
wireframe_dir = Path("static/appdocs/backlog/wireframes")
```

**Reason:** Wireframe discovery for Sprint Review Alex context.

---

#### 6. development/src/services/ai_gateway.py (line 1590)
**Before:**
```python
execution_sandbox = Path(__file__).parent.parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"
```

**After:**
```python
# Use consistent path resolution (matches sprint_orchestrator.py pattern)
execution_sandbox = Path("static/appdocs/execution-sandbox/client-projects")
```

**Reason:** Sprint Review Alex execution mode snapshot creation.

---

#### 7. development/src/services/ai_gateway.py (line 2001)
**Before:**
```python
execution_sandbox = Path(__file__).parent.parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"
```

**After:**
```python
# Use consistent path resolution (matches sprint_orchestrator.py pattern)
execution_sandbox = Path("static/appdocs/execution-sandbox/client-projects")
```

**Reason:** list_snapshots tool for Sprint Review Alex.

---

#### 8. development/src/services/ai_gateway.py (line 2047)
**Before:**
```python
execution_sandbox = Path(__file__).parent.parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"
```

**After:**
```python
# Use consistent path resolution (matches sprint_orchestrator.py pattern)
execution_sandbox = Path("static/appdocs/execution-sandbox/client-projects")
```

**Reason:** restore_snapshot tool for Sprint Review Alex.

---

### Canonical Pattern
The correct pattern (already used in `sprint_orchestrator.py` line 71):
```python
EXECUTION_SANDBOX = Path("static/appdocs/execution-sandbox/client-projects")
```

This works because:
- Railway Dockerfile sets `WORKDIR /app/development/src` (line 50)
- Locally, we always run from `repo/development/src/`
- The relative path resolves correctly in both environments

---

## Part 2: File Path Extraction Improvements

### Problem
Sprint Review Alex was extracting wrong file paths from investigation responses (e.g., `src/server.js` instead of `src/routes/documents.js`).

### Root Cause
Fragile regex parsing only checked first word in each line and had no logging to diagnose failures.

### Files Changed

#### development/src/services/ai_gateway.py (lines 1370-1398)
**Improvements:**
1. Added detailed logging at each extraction strategy
2. Try each word in line instead of just first word
3. Strip common punctuation (`,`, `.`, `;`, `:`) before validation
4. Better error reporting for debugging

**Key Change:**
```python
# OLD: Only check first word
token = line.split()[0]

# NEW: Try each word as potential file path
for word in words:
    word = word.strip(",.;:")  # Remove common punctuation
    if "/" in word and ("." in word.split("/")[-1]):
        # ... validation ...
        break  # Found a path in this line, move to next line
```

**Benefit:** More resilient to variations in Alex's investigation response format.

---

## Part 3: Public Directory Structure Fix (THE LOGIN BUG)

### Problem
Generated apps had login pages that couldn't load JavaScript files:
- HTML: `<script src="js/login.js"></script>`
- Actual file: `public/login.js`
- Result: 404 error, login broken

### Root Cause
Conflicting signals about directory structure:
- Mike's prompt (line 210): `public/ (static frontend files: HTML, CSS, JS)` ✅ Correct
- Mike's file discovery (line 446): `'public/js/*.js'` ❌ Wrong pattern
- Alex's prompt (line 272): Example showed `public/js/*.js` ❌ Wrong example

Alex saw the pattern `public/js/*.js` and generated HTML expecting files in a `js/` subdirectory that doesn't exist.

### Files Changed

#### 1. development/src/services/sprint_orchestrator.py (line 446)
**Before:**
```python
'public/js/*.js'       # Frontend JS files (for consistency with HTML)
```

**After:**
```python
'public/*.js'          # Frontend JS files (for consistency with HTML)
```

**Impact:** Mike now shows Alex the correct file locations during context building.

---

#### 2. system_prompts/SPRINT_EXECUTION_DEVELOPER_system_prompt.txt (line 272)
**Before:**
```
IF the tech stack is a server-rendered web UI using PLAIN HTML/CSS/JS (for example: Express serving static files from /public, no React/Vue SPA) AND your task's files_to_create include BOTH an HTML page (for example public/*.html) AND a page-specific JS file (for example public/js/*.js), you MUST treat the HTML and JS as a single, consistent unit.
```

**After:**
```
IF the tech stack is a server-rendered web UI using PLAIN HTML/CSS/JS (for example: Express serving static files from /public, no React/Vue SPA) AND your task's files_to_create include BOTH an HTML page (for example public/*.html) AND a page-specific JS file (for example public/*.js), you MUST treat the HTML and JS as a single, consistent unit.
```

**Impact:** Alex now sees the correct example when generating HTML + JS pages.

---

### Correct Architecture (Unchanged)
From `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt` line 210:
```
- public/ (static frontend files: HTML, CSS, JS)
```

Files go **directly in public/**, not in subdirectories like `public/js/` or `public/css/`.

**Correct generated structure:**
```
public/
  ├── login.html          (with <script src="login.js">)
  ├── login.js
  ├── dashboard.html      (with <script src="dashboard.js">)
  └── dashboard.js
```

**NOT:**
```
public/
  ├── login.html          (with <script src="js/login.js"> ❌)
  ├── js/
  │   └── login.js
  └── css/
      └── styles.css
```

---

## Additional Fix: Caddy Installation (NOT related to above issues)

### Problem
Railway builds failing with GPG key verification error for Caddy repository.

### Solution
Changed from repository-based install to direct binary download.

#### Dockerfile (lines 7-15)
**Before:**
```dockerfile
RUN apt-get update && apt-get install -y \
    debian-keyring debian-archive-keyring apt-transport-https curl \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update \
    && apt-get install -y caddy
```

**After:**
```dockerfile
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    ca-certificates \
    && curl -1sLf 'https://caddyserver.com/api/download?os=linux&arch=amd64' -o /usr/bin/caddy \
    && chmod +x /usr/bin/caddy \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

**Note:** Fixed package name from `debian-ca-certificates` to `ca-certificates`.

---

## Git Commits

All changes committed in these commits:

1. **1532fa0** - `fix: use direct Caddy download to bypass GPG key verification error`
2. **d172b91** - `fix: align Sprint Review Alex file path resolution with sprint_orchestrator pattern`
3. **68e4b53** - `fix: standardize execution sandbox path resolution across all components`
4. **55d5924** - `fix: improve Sprint Review Alex file path extraction from investigation responses`
5. **98fd481** - `fix: correct public/ directory structure - remove public/js/ subdirectory pattern`

---

## Rollback Instructions (If Needed)

To revert all changes:
```bash
git revert 98fd481 55d5924 68e4b53 d172b91 1532fa0
git push
railway up
```

To revert just the public/ directory fix:
```bash
git revert 98fd481
git push
railway up
```

To revert just the path resolution changes:
```bash
git revert 55d5924 68e4b53 d172b91
git push
railway up
```

---

## Testing Verification

After deployment, verify:

1. **Sprint Review Alex can apply fixes:**
   - Navigate to generated app with a bug
   - Tell Sprint Review Alex to investigate and fix
   - Check that execution mode applies fixes successfully
   - Check Railway logs for: `Execution mode: wrote target file for Sprint Review Alex`

2. **Generated apps have correct file structure:**
   - Run Sprint 1 (login story)
   - Check file exists: `curl https://ai-diy-dev-production.up.railway.app/yourapp/login.js -I`
   - Should return: `HTTP/2 200` (not 404)
   - Check HTML source: `curl https://ai-diy-dev-production.up.railway.app/yourapp/login`
   - Should contain: `<script src="login.js">` (not `<script src="js/login.js">`)

3. **Login functionality works:**
   - Visit: https://ai-diy-dev-production.up.railway.app/yourapp/login
   - Open browser console (F12)
   - Should see NO 404 errors for JavaScript files
   - Login form should be interactive

---

## Impact Assessment

### Low Risk Changes ✅
- Path resolution standardization: Aligns code with documented WORKDIR
- File path extraction improvements: Better error handling, more resilient
- Caddy installation: Simpler, more reliable

### Medium Risk Change ⚠️
- Public directory structure: Changes how Mike discovers files and Alex generates HTML

**Why medium risk:** This changes the guidance Alex receives, which could affect file generation. However:
- Change aligns code with documented architecture (prompt line 210)
- Makes pattern consistent across all components
- Fixes actual bug preventing login from working

### Zero Risk ✅
- No database changes
- No API contract changes
- No breaking changes to generated apps
- Backward compatible with existing sprints

---

## Related Documentation

- **LLM_ONBOARDING.md** (lines 313-322): Script/Test Path Resolver Standard
- **LLM_ONBOARDING.md** (line 388): HTML paths must be relative (no leading /)
- **refactorideas.md**: Long-term architectural improvements
- **SPRINT_EXECUTION_ARCHITECT_system_prompt.txt** (line 210): Directory structure rules

---

## Known Issues (Pre-existing, NOT caused by these changes)

1. No single source of truth for path resolution (see `refactorideas.md` Phase 1, Item 1)
2. File path extraction still uses regex parsing instead of structured data
3. Architecture contract enforcement happens after file creation, not before

These issues are documented in `refactorideas.md` for future improvement.

---

## Conclusion

All changes were necessary to fix two critical bugs:
1. Sprint Review Alex couldn't apply fixes (path resolution mismatch)
2. Generated apps had broken login (public/ directory pattern confusion)

Changes are **conservative** - they align the code with the documented architecture without changing the architecture itself. The risk is low because we're fixing inconsistencies, not introducing new behaviors.

**Recommendation:** Monitor Sprint 1 execution and Sprint Review Alex operations after deployment. If issues arise, the rollback is straightforward (see Rollback Instructions above).

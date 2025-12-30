# AI-DIY Refactoring Ideas

**Date:** 2025-12-30
**Context:** Identified during Sprint Review Alex debugging session
**Goal:** Make AI-DIY easier to maintain and reduce "dribs and drabs" fixes

---

## Core Architectural Issues

### 1. **Scattered Path Resolution Logic**

**Problem:** We just fixed 6+ locations with inconsistent path patterns across the codebase:
- `api/testing.py:42` - `PROJECT_ROOT`
- `api/sandbox.py:24` - `SANDBOX_ROOT`
- `services/ai_gateway.py:1587, 1998, 2042` - execution context, snapshot tools
- `main.py:201` - app control

Each location used different patterns like `Path(__file__).parent.parent / "static/appdocs/..."` which caused path resolution failures.

**Why it's hard:**
- No single source of truth for sandbox paths
- Changes require hunting through entire codebase
- Easy to miss locations, causing runtime failures
- Different patterns work differently on Railway vs Mac

**Proposed Fix:**
```python
# Create: development/src/core/paths.py
from pathlib import Path
from typing import Optional

class SandboxPaths:
    """Single source of truth for all sandbox paths.

    Works on both Railway (/app/development/src working dir)
    and Mac (development/src working dir).
    """

    @staticmethod
    def execution_sandbox() -> Path:
        """Returns execution sandbox root - works on Railway and Mac"""
        return Path("static/appdocs/execution-sandbox/client-projects")

    @staticmethod
    def project_dir(project_name: str = "yourapp") -> Path:
        """Returns specific project directory in execution sandbox"""
        return SandboxPaths.execution_sandbox() / project_name

    @staticmethod
    def appdocs() -> Path:
        """Returns appdocs root directory"""
        return Path("static/appdocs")

    @staticmethod
    def sprints() -> Path:
        """Returns sprints directory"""
        return SandboxPaths.appdocs() / "sprints"

    @staticmethod
    def visions() -> Path:
        """Returns visions directory"""
        return SandboxPaths.appdocs() / "visions"

    @staticmethod
    def backlog() -> Path:
        """Returns backlog directory"""
        return SandboxPaths.appdocs() / "backlog"

    @staticmethod
    def wireframes() -> Path:
        """Returns wireframes directory"""
        return SandboxPaths.backlog() / "wireframes"
```

**Usage:**
```python
# Before (scattered across 6+ files):
execution_sandbox = Path(__file__).parent.parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"

# After (everywhere):
from core.paths import SandboxPaths
execution_sandbox = SandboxPaths.execution_sandbox()
project_path = SandboxPaths.project_dir("yourapp")
```

**Benefits:**
- One change fixes all path issues
- Type-safe and IDE-friendly
- Self-documenting
- Easy to extend (e.g., add Railway-specific overrides if needed)

---

### 2. **Monolithic ai_gateway.py (2000+ lines)**

**Problem:** Sprint Review Alex logic is buried in a giant file:
- Investigation mode (lines 650-800)
- Execution mode (lines 1300-1700)
- Tool execution (lines 1750-2100)
- All intermingled in one massive `call_openrouter_api()` function

**Why it's hard:**
- Can't test components independently
- Changes ripple unpredictably across 2000 lines
- Hard to understand control flow
- Difficult to onboard new developers
- Git conflicts when multiple changes happen

**Proposed Fix:** Break into focused modules:

```
services/
  sprint_review/
    __init__.py           # Public interface
    investigation.py      # Investigation loop logic
    execution.py          # Execution mode logic
    file_extraction.py    # Path extraction strategies (the regex mess)
    tools.py              # Tool definitions (read_file, write_text, etc.)
    context_builder.py    # Build context for Alex (file structure, etc.)
```

**Example refactor:**
```python
# services/sprint_review/investigation.py
class InvestigationMode:
    def __init__(self, project_name: str, session_id: str):
        self.project_name = project_name
        self.session_id = session_id

    def build_context(self) -> str:
        """Build CURRENT FILE STRUCTURE context"""
        # Logic from lines 706-754

    def run(self, messages: List[Dict], model: str) -> AsyncGenerator:
        """Execute investigation loop with bounded passes"""
        # Logic from lines 650-800

# services/sprint_review/execution.py
class ExecutionMode:
    def __init__(self, approved_plan: str, files_to_modify: str):
        self.approved_plan = approved_plan
        self.files_to_modify = files_to_modify

    def extract_file_paths(self) -> List[str]:
        """Extract target files from approved plan"""
        # Logic from lines 1368-1425

    def read_file_contents(self, file_paths: List[str]) -> List[Dict]:
        """Read current file contents from sandbox"""
        # Logic from lines 1420-1455

    def apply_fixes(self, execution_response: str) -> None:
        """Parse JSON and write files to sandbox"""
        # Logic from lines 1540-1680

# Main handler becomes simple orchestration:
def handle_sprint_review_alex(messages, persona_key, model):
    if is_approval_message(messages[-1]):
        execution = ExecutionMode(
            approved_plan=extract_plan(messages),
            files_to_modify=extract_files(messages)
        )
        return execution.run(messages, model)
    else:
        investigation = InvestigationMode(
            project_name=get_project_name_safe(),
            session_id=get_session_id(messages)
        )
        return investigation.run(messages, model)
```

**Benefits:**
- Each module has single responsibility
- Easy to test in isolation
- Clear separation of concerns
- Easier to understand and modify
- Better code organization

---

### 3. **String-Based File Path Extraction (Regex Hell)**

**Problem:** Lines 1370-1420 use fragile regex patterns to parse Alex's text responses:
```python
files_match = re.search(r'Files to modify[:\s]+(.+?)(?:\n|$)', alex_last_response, re.IGNORECASE)
# ... then parse the string with more regex
# ... then split words and check prefixes
# ... then hope it works
```

**Why it's hard:**
- Breaks when Alex changes response format slightly
- Impossible to validate until runtime
- Requires manual regex tuning for each failure case
- Three fallback strategies needed (Strategy 1, 2, 3)
- Still fails (we saw it extract `src/server.js` instead of `src/routes/documents.js`)

**Root cause:** We're asking an LLM to write text, then parsing that text with regex. This is backwards.

**Proposed Fix:** Use OpenRouter's function calling for structured output:

```python
# Define a tool for Alex to declare his plan
declare_fix_plan_tool = {
    "type": "function",
    "function": {
        "name": "declare_fix_plan",
        "description": "Declare the specific files you need to modify and the fix you propose",
        "parameters": {
            "type": "object",
            "properties": {
                "files_to_modify": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to modify (e.g., ['src/routes/documents.js'])"
                },
                "fix_description": {
                    "type": "string",
                    "description": "Plain English description of what you'll change"
                },
                "verification_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "How to verify the fix works (e.g., ['npm start should succeed'])"
                }
            },
            "required": ["files_to_modify", "fix_description"]
        }
    }
}

# Alex's investigation mode includes this tool
# When ready to propose fix, Alex calls the function:
{
    "files_to_modify": ["src/routes/documents.js"],
    "fix_description": "Add missing closing parenthesis on line 67 in resolve() call",
    "verification_steps": ["npm start", "curl /api/documents should return 200"]
}

# Python receives structured data - no parsing needed!
```

**Benefits:**
- No regex parsing needed
- Guaranteed structure
- Type-safe extraction
- Alex can't accidentally format it wrong
- Easy to validate
- Clear contract between investigation and execution modes

---

### 4. **Investigation vs Execution Mode Coupling**

**Problem:** Both modes live in the same 2000-line function with complex branching:
```python
if persona_key == "SPRINT_REVIEW_ALEX":
    if is_approval_message():
        # Execution mode (400 lines)
    else:
        # Investigation mode (300 lines)
```

Different concerns mixed together makes it hard to reason about either mode.

**Why it's hard:**
- Can't test investigation without execution logic present
- Shared state causes unexpected interactions
- Hard to understand what each mode needs
- Changes to one mode can break the other

**Proposed Fix:** Separate handlers with clear interface:

```python
# services/sprint_review/sprint_review_alex.py
from typing import Protocol

class SprintReviewMode(Protocol):
    """Interface that all Sprint Review modes must implement"""
    async def run(self, messages: List[Dict], model: str) -> AsyncGenerator:
        ...

class InvestigationMode:
    """Handles Sprint Review investigation loop"""

    def __init__(self, project_name: str, context: Dict):
        self.project_name = project_name
        self.context = context

    async def run(self, messages, model):
        # Investigation logic only
        # Build file structure context
        # Execute bounded loop with tools
        # Return diagnosis and proposed fix

class ExecutionMode:
    """Handles applying approved fixes"""

    def __init__(self, approved_plan: Dict, project_name: str):
        self.approved_plan = approved_plan
        self.project_name = project_name

    async def run(self, messages, model):
        # Execution logic only
        # Extract file paths from plan
        # Read current file contents
        # Send to Alex for JSON generation
        # Write fixed files to sandbox

class SprintReviewAlex:
    """Routes between investigation and execution modes"""

    def route(self, messages: List[Dict]) -> SprintReviewMode:
        """Determine which mode to use based on conversation state"""
        if self._is_approval(messages[-1]):
            approved_plan = self._extract_plan(messages)
            return ExecutionMode(approved_plan, self.project_name)
        else:
            return InvestigationMode(self.project_name, self.context)

    async def handle(self, messages, model):
        mode = self.route(messages)
        return await mode.run(messages, model)
```

**Benefits:**
- Clear separation of concerns
- Each mode is independently testable
- Easy to understand what each mode does
- Can evolve modes separately
- Type-safe routing

---

### 5. **No Type Safety**

**Problem:** Dictionaries everywhere with `Dict[str, Any]`:
```python
def extract_file_paths(alex_response: str) -> List[str]:  # Which fields? Who knows!
def build_execution_context(plan: Dict) -> str:  # What keys exist? No idea!
```

**Why it's hard:**
- No IDE autocomplete
- Runtime errors from typos (`approved_change_spec["fils"]` instead of `"files"`)
- Can't validate structure until runtime
- Hard to refactor (no type checker to catch breaks)

**Proposed Fix:** Use Pydantic models throughout:

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional, List

class FileFix(BaseModel):
    """A single file modification"""
    file_path: str = Field(..., description="Path relative to project root")
    action: Literal["overwrite", "none"] = Field(..., description="Action to take")
    new_content: Optional[str] = Field(None, description="Complete new file content")
    explanation: Optional[str] = Field(None, description="Why this change is needed")

    class Config:
        frozen = True  # Immutable

class ExecutionPlan(BaseModel):
    """Alex's execution plan with fixes"""
    files: List[FileFix] = Field(..., description="Files to modify")
    explanation: str = Field(..., description="Plain English summary of changes")

    def get_file_paths(self) -> List[str]:
        """Get list of all file paths in plan"""
        return [f.file_path for f in self.files]

    def to_approved_spec(self) -> Dict:
        """Convert to APPROVED_CHANGE_SPEC format"""
        return {
            "files": [{"file_path": f.file_path} for f in self.files],
            "description": self.explanation
        }

class FileSnapshot(BaseModel):
    """Current state of a file from sandbox"""
    file_path: str
    content: str
    bytes: int = Field(..., description="Content length in bytes")

class InvestigationContext(BaseModel):
    """Context for investigation mode"""
    project_name: str
    session_id: str
    file_structure: str
    api_endpoints: str
    wireframes: Optional[str] = None

# Usage with type safety:
def build_execution_plan(alex_response: str) -> ExecutionPlan:
    """Parse Alex's JSON response into validated ExecutionPlan"""
    data = json.loads(alex_response)
    return ExecutionPlan.model_validate(data)  # Pydantic validates structure

def apply_fixes(plan: ExecutionPlan, project_name: str) -> None:
    """Apply fixes from execution plan"""
    for file_fix in plan.files:  # IDE knows file_fix is FileFix!
        if file_fix.action == "overwrite":  # Autocomplete works!
            write_file(project_name, file_fix.file_path, file_fix.new_content)
```

**Benefits:**
- IDE autocomplete everywhere
- Type checker catches errors at development time
- Self-documenting (Field descriptions)
- Runtime validation (Pydantic ensures structure)
- Easy refactoring (type checker finds all usages)
- Better error messages when structure is wrong

---

### 6. **Logging is Inconsistent**

**Problem:** Inconsistent logging makes debugging hard:
- Some functions log entry/exit, some don't
- Some log parameters, some don't
- Hard to trace execution flow
- We had to add logging manually to diagnose file extraction bug

**Why it's hard:**
- Can't trace what happened without adding more logging
- Logs are scattered and unstructured
- Hard to filter for specific operations
- No correlation IDs across operations

**Proposed Fix:** Structured logging with decorators:

```python
# core/logging.py
import functools
import logging
from typing import Callable, Any
import time

def log_execution_mode(func: Callable) -> Callable:
    """Decorator to log execution mode operations with timing"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger = logging.getLogger(func.__module__)

        # Log entry with parameters
        logger.info(
            f"⚡ {func_name} started",
            extra={
                "function": func_name,
                "args_count": len(args),
                "kwargs": list(kwargs.keys())
            }
        )

        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time

            # Log success with timing
            logger.info(
                f"✅ {func_name} completed",
                extra={
                    "function": func_name,
                    "duration_ms": int(duration * 1000),
                    "result_type": type(result).__name__
                }
            )
            return result

        except Exception as e:
            duration = time.time() - start_time

            # Log failure with error details
            logger.error(
                f"❌ {func_name} failed",
                extra={
                    "function": func_name,
                    "duration_ms": int(duration * 1000),
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise

    return wrapper

# Usage:
@log_execution_mode
async def extract_file_paths(alex_response: str, persona_key: str) -> List[str]:
    """Extract file paths from Alex's investigation response"""
    # Decorator logs entry/exit automatically
    # No manual logging needed!

    # Function logic...
    return file_paths

# Logs automatically show:
# ⚡ extract_file_paths started (args_count=2, kwargs=['persona_key'])
# ✅ extract_file_paths completed (duration_ms=45, result_type=list)
```

**Benefits:**
- Consistent logging across all operations
- Automatic timing for performance analysis
- Structured logs (easy to filter/search)
- Less boilerplate (decorator handles it)
- Clear operation boundaries (start/end)

---

## Recommended Refactoring Priority

### Phase 1: Quick Wins (1-2 days)
**Goal:** Eliminate immediate pain points with minimal risk

1. **Create `core/paths.py`** - Single source of truth for all paths
   - Impact: Eliminates 90% of path-related bugs
   - Risk: Low (just replacing inline paths)
   - Files affected: 6-10 files

2. **Add structured logging to file extraction**
   - Impact: Makes debugging Sprint Review much easier
   - Risk: Low (additive change)
   - Files affected: `services/ai_gateway.py`

3. **Add type hints to critical functions**
   - Impact: Catches bugs during development
   - Risk: Low (additive, doesn't change behavior)
   - Files affected: `services/ai_gateway.py`, `services/sprint_orchestrator.py`

**Deliverables:**
- `core/paths.py` module
- All path references updated to use it
- Type hints on top 10 most-called functions
- Logging decorator for execution mode

---

### Phase 2: Structural (3-5 days)
**Goal:** Make the codebase easier to understand and modify

4. **Break `ai_gateway.py` into modules**
   - Create `services/sprint_review/` package
   - Move investigation mode to `investigation.py`
   - Move execution mode to `execution.py`
   - Move file extraction to `file_extraction.py`
   - Impact: Much easier to understand and test
   - Risk: Medium (refactoring large file)

5. **Create Pydantic models for all data structures**
   - `ExecutionPlan`, `FileFix`, `FileSnapshot`
   - `InvestigationContext`, `ApprovedChangeSpec`
   - Impact: Type safety, better error messages
   - Risk: Medium (changes interfaces)

6. **Separate investigation/execution handlers**
   - Clear interface between modes
   - Independent testing
   - Impact: Easier to reason about each mode
   - Risk: Medium (refactoring control flow)

**Deliverables:**
- `services/sprint_review/` package structure
- Pydantic models for all key data structures
- Separate handlers for investigation and execution
- Unit tests for each module

---

### Phase 3: Architecture (1 week)
**Goal:** Eliminate fragile parsing and improve reliability

7. **Replace regex extraction with structured tools**
   - Add `declare_fix_plan` function calling tool
   - Remove all regex parsing logic
   - Impact: Eliminates entire class of bugs
   - Risk: High (changes Alex's interface)

8. **Add unit tests for each module**
   - Test file path extraction in isolation
   - Test execution plan building
   - Test context building
   - Impact: Catches regressions early
   - Risk: Low (tests don't affect runtime)

9. **Create integration tests for Sprint Review flow**
   - End-to-end test: investigation → approval → execution
   - Mock OpenRouter API for deterministic testing
   - Impact: Confidence in changes
   - Risk: Low (tests don't affect runtime)

**Deliverables:**
- Function calling tools for structured output
- 80%+ unit test coverage on sprint_review package
- Integration test suite for full Sprint Review flow
- Documentation of new architecture

---

## Immediate Action Recommendation

**Start with Phase 1, Item 1:** Create `core/paths.py` module

**Why:**
- Small change (1 new file + updates to 6-10 existing files)
- Huge impact (eliminates path-related bugs permanently)
- Low risk (just consolidating existing patterns)
- Foundation for other improvements
- Can be done in < 1 hour
- Can be tested immediately

**Next steps after that:**
1. Add logging decorator (Phase 1, Item 2)
2. Add type hints (Phase 1, Item 3)
3. Then reassess and plan Phase 2

**Don't start with:** Phase 3 (too big, too risky without Phase 1 and 2 foundation)

---

## Notes

- All proposed changes maintain backward compatibility with existing generated apps
- Changes focused on AI-DIY internal architecture, not output
- Refactoring can be done incrementally without breaking production
- Each phase builds on previous phase
- Can pause between phases to validate improvements

---

**Created:** 2025-12-30
**Author:** Claude Sonnet 4.5 (via Claude Code)
**Context:** Debugging Sprint Review Alex path resolution and file extraction issues

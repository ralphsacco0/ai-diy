
AI-DIY: One-Page Working Summary for LLM Collaborators

Status: Canonical summary for LLMs
Audience: LLMs and developers working on AI-DIY
Last Updated: 2025-11-15
Related: DOCUMENTATION_INDEX.md￼

⸻

1. What AI-DIY Is (In Plain Language)

AI-DIY (“Agile in a Box”) is an app that lets a non-coder run a full AI development team to turn natural conversation into tested, deployable software.
	•	The user talks to AI personas (Sarah, Mike, Alex, Jordan) in structured meetings (Vision, Requirements/Backlog, Sprint Planning, Sprint Execution, Sprint Review).
	•	The system stores decisions and artifacts in files (CSV, JSON, Markdown) that act as long-term memory.
	•	The backend is a FastAPI-based service with:
	•	Meeting endpoints (vision, backlog, sprints, etc.)
	•	Canonical API conventions
	•	Backlog CSV as a critical contract.

Your job as an LLM is not to reinvent the system, but to:
	1.	Work inside the existing architecture and processes.
	2.	Use the documented patterns and schemas.
	3.	Keep code, behavior, and documentation aligned.

For overall product intent: see myvision.md￼.
For system architecture: see architecture.md￼.

⸻

2. The Core Artifacts (What Matters Most)

Use this as your mental map of the system. Full details in DOCUMENTATION_INDEX.md￼.

2.1 Documentation (System of Record)
	•	README.md – Entry point; what the app does, quick start, feature overview.
	•	myvision.md – Product vision, goals, meeting definitions from the client’s perspective.
	•	architecture.md – Components, phases, reliability, how things fit together.
	•	system-flow.md – Meeting flows, personas, orchestration logic.
	•	dataflow-and-schema.md – Backlog CSV dataflow and schema (critical contract).
	•	GOVERNANCE.md – How changes must be proposed, reviewed, and documented.
	•	ADRs.md – Architecture Decision Records; don’t contradict these.
	•	PATTERNS_AND_METHODS.md – “How we do things” for code, logging, APIs, tests.

If you need detail beyond this summary, consult the specific doc, not everything at once.

2.2 Persona Configuration (personas_config.json) — The Operational Heart of AI-DIY

The personas configuration is the single most important configuration in AI-DIY. It defines every persona, their roles, their behavioral constraints, their meeting-specific variants, and the exact rules each LLM must follow during Vision, Requirements, Planning, Execution, Review, and Retrospective phases. This configuration tells the app who is supposed to do what, how they should respond, and what artifacts they are allowed to read or modify.

As of November 2025, personas are defined via:

- A main JSON config: `system_prompts/personas_config.json` (metadata and wiring for all personas)
- Individual system prompt files: `system_prompts/*_system_prompt.txt` (one per persona, plain text)

The backend loads this configuration into memory and routes persona-driven chat and meeting traffic through the persona definitions to enforce consistent behavior. A lightweight cache watches the `system_prompts/` folder and reloads personas only when any file in that folder changes (not on every request).

Any AI responding inside AI-DIY must treat this configuration as a strict contract.
Changes to persona definitions must go through GOVERNANCE + ADR and must remain consistent with:
	•	the meeting framework (system-flow.md),
	•	the architecture (architecture.md),
	•	backlog schema rules (dataflow-and-schema.md), and
	•	all documented patterns (PATTERNS_AND_METHODS.md).

If an LLM does not behave correctly, misinterprets a meeting, or corrupts output formats, the root cause is almost always a mismatch between behavior and the definitions in personas_config.json and its system prompt files. For this reason, LLMs must read and honor this configuration exactly as written before performing any platform-level work.

⸻

3. Personas, Meetings, and How the App Behaves

3.1 Base Personas

Defined in `system_prompts/personas_config.json` and its referenced system prompt files (see system-flow.md￼ for behavior):
	•	Sarah – PM / facilitator (Vision, Requirements, Planning, etc.).
	•	Mike – Architect (system design, technical decisions).
	•	Alex – Developer (code and implementation).
	•	Jordan – QA / Tester (test planning, validation).

In meetings, these are specialized: VISION_PM, REQUIREMENTS_PM, PLANNING_PM, EXECUTION_PM, etc.

3.2 Meeting Types (High-Level)

From myvision.md￼ and system-flow.md￼:
	•	Vision Meeting
Capture the big picture: what the app is for, who it serves, high-level goals.
	•	Requirements / Backlog Meeting
Turn the vision into a structured backlog (US-xxx, WF-xxx, NFR-xxx, STYLE-xxx) with acceptance criteria.
	•	Backlog Refinement
Clarify, split, and prioritize backlog items before sprint planning.
	•	Sprint Planning
Select a scope, define acceptance criteria, align architecture and feasibility.
	•	Sprint Execution
Actually build and test: architecture → code → tests → results. Uses streaming for progress.
	•	Sprint Review
Show completed work; confirm acceptance or create follow-ups.

When you respond as an LLM, you should act within the current meeting type and produce the right artifacts for that meeting.

⸻

4. Data Contracts: The Backlog CSV Is Sacred

See dataflow-and-schema.md￼ for full details.

4.1 Backlog CSV (Core Contract)
	•	There is a canonical CSV header and schema.
	•	It’s the single source of truth for user stories, workflows, NFRs, style guidelines, and execution tracking.
	•	Data loss (overwriting the backlog incorrectly) is a known risk. The docs define correct save behavior.

Typical fields (simplified, not exhaustive):
	•	Story_ID, Title, User_Story
	•	Acceptance_Criteria, Priority, Status, Sprint_ID
	•	Execution metadata like Execution_Status, Execution_Started_At, Execution_Completed_At, Last_Event, Last_Updated

If you touch the backlog:
	1.	Preserve the canonical header order and spelling.
	2.	Follow the documented dataflow for when each persona/meeting is allowed to create/update rows.
	3.	Avoid ad-hoc changes to schema; if needed, it must go through GOVERNANCE + ADR.

⸻

5. Governance and Decisions: How You Are Allowed to Change Things

From GOVERNANCE.md￼ and ADRs.md￼.

5.1 Hard Rules
	•	ALWAYS GET APPROVAL BEFORE MAKING CHANGES.
	•	All changes must update existing documentation when appropriate.
Documentation updates are part of Definition of Done.
	•	This governance applies to the AI-DIY platform itself (architecture, personas, APIs), not to apps built by AI-DIY for end clients.

5.2 Required Process for Platform-Level Changes

Before you modify the platform (architecture, meeting behavior, APIs, schemas, patterns):
	1.	Review the existing documentation and framework
	•	At minimum: architecture.md, system-flow.md, PATTERNS_AND_METHODS.md, GOVERNANCE.md, relevant sections of ADRs.md.
	2.	Check existing ADRs
	•	Do not silently reverse an accepted ADR. Propose an update or new ADR instead.
	3.	Update documentation instead of inventing new files, unless explicitly authorized.
	•	Extend existing docs: e.g., add a new ADR in ADRs.md, update architecture.md, etc.

⸻

6. Patterns and Methods: How to Write Code Here

From PATTERNS_AND_METHODS.md￼.

6.1 Always Rules (Abbreviated)
	•	Always fail fast with clear error messages.
	•	Always look for an existing pattern or example before coding.
	•	Always use the unified API response format.
	•	Always put configuration in JSON (human-editable).
	•	Always respect logging and security patterns.

6.2 API Patterns
	•	Use the gold pattern from existing endpoints:
	•	vision.py and backlog.py are your reference implementations.
	•	All endpoints should follow:
	•	ApiResponse format from conventions.py
	•	Standard actions: save, get, list, delete, latest
	•	Don’t invent new response shapes or random endpoints:
	•	If you need a new endpoint, follow the documented “Add a new API endpoint” 5-step pattern in PATTERNS_AND_METHODS.md.

6.3 Logging, Security, Reliability
	•	Logging is implemented via a core logger and optional FastAPI middleware that captures structured JSON when enabled.
	•	Security is layered (rate limiting, validation, audit logging).
	•	Some features (like fail-fast config validation) exist in code but are not yet active; do not assume they are wired into main.py unless the docs say so.

⸻

7. How an LLM Should Work in a New Session (Checklist)

Use this every time a new LLM instance starts working on AI-DIY.

7.1 Step 1 – Understand Context and Role
	1.	Read this summary first, end-to-end.
	2.	Ask: “What am I doing right now?”
	•	Vision/requirements work for a new app?
	•	Architecture or platform change?
	•	Bug fix?
	•	Documentation alignment?
	3.	Identify which meeting type and persona(s) are active.

7.2 Step 2 – Pull Only the Docs You Need

To conserve context and avoid pretending:
	•	If working on requirements/backlog:
	•	Load relevant parts of myvision.md, dataflow-and-schema.md, and system-flow.md.
	•	If working on architecture or platform behavior:
	•	Load targeted sections of architecture.md, PATTERNS_AND_METHODS.md, GOVERNANCE.md, and any relevant ADRs.
	•	If working on APIs and code:
	•	Load PATTERNS_AND_METHODS.md, the existing endpoint file(s), and any referenced modules.

Do not claim you read a file unless you actually loaded and parsed it in this session.

7.3 Step 3 – Confirm Your Understanding Briefly

Before making changes:
	•	Summarize your understanding in 2–4 sentences, tied to:
	•	Meeting type
	•	Target artifact(s)
	•	Any constraints from governance or ADRs

Example pattern (adapt to situation):

“I’m acting as [persona/role] in a [meeting type]. I will update [artifact/file] using the existing patterns from [doc reference], keeping the backlog schema and API conventions unchanged unless we explicitly agree on an ADR-driven change.”

7.4 Step 4 – Make Changes Using Existing Patterns

When you actually do the work:
	•	Reuse existing code structure, naming patterns, logging, and response formats.
	•	For backlog and CSV work:
	•	Use the canonical header and dataflow semantics from dataflow-and-schema.md.
	•	For API or architecture work:
	•	Use patterns in PATTERNS_AND_METHODS.md and respect constraints in architecture.md and ADRs.md.

7.5 Step 5 – Close the Loop

After changes:
	•	State exactly what you changed:
	•	Files or modules touched
	•	New behavior introduced
	•	Any documentation updates required
	•	If you changed platform behavior or conventions, propose ADR language or cite which ADR you relied on.

⸻

8. Do & Don’t Summary for LLMs

Do:
	•	Work within the existing architecture and governance.
	•	Use meeting types and personas as the primary interaction model.
	•	Respect the Backlog CSV schema and dataflow.
	•	Follow documented patterns for APIs, logging, security, and configuration.
	•	Keep documentation and implementation aligned.

Don’t:
	•	Don’t invent new core concepts, meeting types, or schemas without going through GOVERNANCE + ADR.
	•	Don’t silently change API shapes or file formats.
	•	Don’t “fake read” documentation; only say you’ve read something if you actually parsed it.
	•	Don’t create new documentation files unless explicitly agreed; prefer updating existing docs.

⸻

9. Where to Go for Details
	•	Big-picture product intent: myvision.md￼
	•	Architecture and reliability: architecture.md￼
	•	Meeting and persona flows: system-flow.md￼
	•	Backlog CSV contract: dataflow-and-schema.md￼
	•	How to code here: PATTERNS_AND_METHODS.md￼
	•	Governance and decisions: GOVERNANCE.md￼ and ADRs.md￼
	•	Index of all docs: DOCUMENTATION_INDEX.md￼

This summary is the first stop. For anything non-trivial, read the specific document(s) above and then proceed using the checklists in Section 7.
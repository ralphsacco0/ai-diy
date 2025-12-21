# AI-DIY: AI-Powered Agile Development Platform

## What Is This?

AI-DIY (aka "Agile in a Box") is a web application that lets a non-coder work with an AI Scrum team through a single chat interface. You interact with virtual rolesProject Manager, Architect, Developer, QA, and a hidden Scribe personaas they run structured meetings and produce working, testable software artifacts.

The app is currently an MVP focused on a meeting-driven workflow (Vision  Backlog  Sprints) and a clear extension model for developers.

## Who Is This For?

- **Non-technical users**  
  Run the app locally and use the meeting framework to guide the AI team. You never need to touch code.

- **Developers / maintainers**  
  Extend or change the AI-DIY platform itself (personas, APIs, sprint engine, security). If thats you, read the architect docs listed below before making changes.

## Current Capabilities (MVP)

- **Meeting framework**  
  Vision, Backlog Refinement, Sprint Planning, Sprint Execution, and Sprint Review. Meetings are driven by specialized personas (for example `VISION_PM`, `REQUIREMENTS_PM`, `SPRINT_EXECUTION_PM`).

- **Multi-persona collaboration**  
  PM, Architect, Developer, QA, and Scribe personas with configuration-driven behavior.
  Concurrent responses and meeting-specific persona variants.

- **Vision & backlog management**  
  Versioned vision documents stored under `static/appdocs/visions/`.  
  Backlog stored as a single CSV + metadata under `static/appdocs/backlog/` with schema validation and overwrite-on-save behavior.

- **Sprint execution pipeline**  
  Orchestrated flow (Mike  Alex  Jordan) that generates code, tests, and execution logs under `static/appdocs/sprints/` and `execution-sandbox/client-projects/`.  
  Live narration of sprint execution in the main chat via Server-Sent Events (SSE).

- **Scribe & transcripts**  
  Structured meeting notes and persona transcripts stored under `static/appdocs/scribe/`.

- **Health & status**  
  Basic health and environment status endpoints (for example `/health`, `/api/env`) exposed by the running app.

Details about enhanced configuration, logging, and security modules (and which ones are active in the default entrypoint) are documented in `architect/architecture.md`.

## Quick Start

### Prerequisites

- Python 3.11+
- Git

### Setup and Run

```bash
# Clone and enter the project
git clone <repository-url>
cd ai-diy

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r development/requirements.txt

# Create .env from example and configure API key
cp development/.env.example .env
# Edit .env and set OPENROUTER_API_KEY

# Start the application
cd development
./start.command
```

### Access the Application

- Web UI: http://localhost:8000  
- Health check: http://localhost:8000/health  
- API docs: available at the application root while the server is running.

## Project Layout (High Level)

- `architect/`  Architecture, patterns, governance, and ADR documentation.
- `development/`  Application implementation (FastAPI app, APIs, services, tests, scripts).
- `static/appdocs/`  Runtime application data (visions, backlog, sprints, scribe, sessions).
- `system_prompts/`  Persona configuration (`personas_config.json`) and system prompt files.
- `docs/`  Process documentation (Vision, Requirements, UI/status behavior, etc.).

## Where to Read More

Use `architect/DOCUMENTATION_INDEX.md` as the source of truth for documentation. Key entry points:

- `architect/architecture.md`  Overall system architecture and current implementation/activation status.
- `architect/PATTERNS_AND_METHODS.md`  Canonical  how we do things for developers (APIs, personas, storage, context patterns).
- `architect/GOVERNANCE.md`  How Ralph, ChatGPT, and Cascade collaborate on platform changes.
- `architect/ADRs.md`  Architecture Decision Records (rationale and enforcement for major decisions).
- `architect/dataflow-and-schema.md`  Backlog CSV schema, dataflow, and persona instructions.
- `docs/vision_process.md`  How Vision meetings work and how vision documents are produced.
- `docs/requirements_process.md`  How Requirements meetings work and how the backlog is managed.
- `development/DEPLOYMENT.md`  Deployment options and production setup details.
- `development/OPERATIONS.md`  Operations runbook, monitoring, and troubleshooting.

## For Developers (Short Version)

Before changing code in this repo:

- **Copy existing patterns instead of inventing new ones.**  
  For new APIs, start from `development/src/api/vision.py` or `development/src/api/backlog.py`.

- **Keep personas in config, not code.**  
  Persona wiring lives in `system_prompts/personas_config.json` and individual `system_prompts/*_system_prompt.txt` files.

- **Store data under `static/appdocs/` only.**  
  Do not invent new storage locations; reuse the existing directory layout.

- **Use the unified API response format.**  
  Reuse helpers from `development/src/api/conventions.py` instead of hand-rolling JSON structures.

- **Follow governance.**  
  Propose  discuss  get approval  implement, and update the relevant architect docs as part of your change. See `architect/GOVERNANCE.md`.

Full, detailed guidance lives in `architect/PATTERNS_AND_METHODS.md` and the rest of the architect docs.

## License

[Your License Here]

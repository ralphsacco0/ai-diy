# code2prompt Usage Guide for AI-DIY

## Overview

Two scripts generate comprehensive exports of the AI-DIY project for sharing with other AIs:

1. **`code2prompt-codebase.command`** - Application code & architecture
2. **`code2prompt-samples.command`** - Working samples & outputs

Both output to the `dist/` directory with timestamps.

---

## Script 1: Codebase Export

### Purpose
Exports the **application's source code, architecture, and technical documentation**.

### What It Includes
- ✅ `myvision.md` - Product vision
- ✅ `README.md` - System overview
- ✅ `architect/*.md` - Architecture docs, ADRs, governance
- ✅ `config_personas.json` - All AI persona definitions
- ✅ `development/src/*.py` - Core application code
- ✅ `development/src/api/*.py` - API endpoints
- ✅ `development/src/static/index.html` - Web UI
- ✅ `docs/*.md` - Process documentation

### What It Excludes
- ❌ Runtime data (logs, conversations)
- ❌ Working samples (vision docs, backlogs)
- ❌ Execution sandbox contents
- ❌ Environment variables (.env)
- ❌ Python cache, git files

### Usage
```bash
./code2prompt-codebase.command
```

### Output
```
dist/ai-diy-codebase-YYYYMMDD-HHMMSS.txt
```

### Use This For
- Technical architecture review
- Code quality assessment
- API design feedback
- Persona system evaluation
- Sprint orchestration architecture questions

---

## Script 2: Samples Export

### Purpose
Exports **working examples of what the application produces** during its workflow.

### What It Includes
- ✅ Vision documents (JSON + Markdown)
- ✅ Backlog CSV files
- ✅ HTML wireframes
- ✅ Scribe meeting notes
- ✅ Generated code in execution-sandbox
- ✅ Project templates

### What It Excludes
- ❌ Application source code
- ❌ Architecture documentation
- ❌ Persona definitions

### Usage
```bash
./code2prompt-samples.command
```

### Output
```
dist/ai-diy-samples-YYYYMMDD-HHMMSS.txt
```

### Use This For
- Artifact quality assessment
- Workflow output evaluation
- Wireframe-to-code feasibility
- Backlog structure review
- Generated code quality check

---

## Typical Workflow

### Step 1: Generate Both Exports
```bash
cd /Users/ralph/Documents/NoHub/ai-diy

# Generate codebase export
./code2prompt-codebase.command

# Generate samples export
./code2prompt-samples.command

# Check outputs
ls -lh dist/ai-diy-*
```

### Step 2: Share with Other AIs

**For Architecture Questions:**
```
Upload: dist/ai-diy-codebase-{timestamp}.txt

Ask: "I'm building AI-DIY, a system where non-coders guide AI to build 
working software. Please review the architecture and provide feedback on:

1. Sprint Orchestration: How should I bridge requirements → working code?
2. API Choice: Windsurf Cascade API vs VS Code Extension vs hybrid?
3. Workflow Design: Mike (architect) → Alex (dev) → Jordan (QA) orchestration?
4. Framework Detection: How should Mike choose React vs Python?
5. Red Flags: Any concerns with the current approach?"
```

**For Workflow/Output Questions:**
```
Upload: dist/ai-diy-samples-{timestamp}.txt

Ask: "These are real examples of what AI-DIY produces. Please review and 
provide feedback on:

1. Artifact Quality: Are vision docs, backlogs, wireframes sufficient?
2. Wireframe Fidelity: Can these be reliably converted to working apps?
3. Backlog Structure: Is the CSV format appropriate for sprint planning?
4. Code Generation: Do execution-sandbox samples show viable output?
5. Missing Pieces: What additional artifacts would help?"
```

---

## File Sizes (Approximate)

- **Codebase export**: ~500KB - 2MB (depends on code size)
- **Samples export**: ~100KB - 1MB (depends on number of projects)

Both are well within token limits for most LLMs (Claude, GPT-4, etc.)

---

## Customization

### To Add More Files to Codebase Export
Edit `code2prompt-codebase.command`, find the `--include` section:
```bash
--include "myvision.md,README.md,YOUR_NEW_FILE.md,..."
```

### To Add More Files to Samples Export
Edit `code2prompt-samples.command`, find the `--include` section:
```bash
--include "development/src/static/appdocs/YOUR_NEW_DIR/*.json,..."
```

### To Exclude Additional Patterns
Edit either script, find the `--exclude` section:
```bash
--exclude "**/__pycache__/**,YOUR_NEW_PATTERN/**,..."
```

---

## Troubleshooting

### "code2prompt: command not found"
Install code2prompt:
```bash
brew install code2prompt
```

### Empty or Small Output Files
- Check if included paths exist
- Verify glob patterns match your files
- Run with `set -x` for debugging:
  ```bash
  bash -x ./code2prompt-codebase.command
  ```

### Output Too Large
- Add more exclusion patterns
- Split into smaller focused exports
- Use `--exclude` to filter out large files

---

## Integration with Existing Workflow

These scripts complement your existing `zip_for_architect.command`:

| Script | Purpose | Output Format | Use Case |
|--------|---------|---------------|----------|
| `zip_for_architect.command` | Full backup | ZIP archive | Backup, version control |
| `code2prompt-codebase.command` | Code review | Plain text | AI architecture review |
| `code2prompt-samples.command` | Output review | Plain text | AI workflow review |

---

## Next Steps

1. ✅ Run both scripts to generate initial exports
2. ✅ Review outputs in `dist/` directory
3. ✅ Share with other AIs (Claude, ChatGPT, Gemini)
4. ✅ Collect architectural feedback
5. ✅ Document decisions in `architect/ADRs.md`

---

Generated: 2025-10-25

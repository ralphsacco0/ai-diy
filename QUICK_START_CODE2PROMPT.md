# Quick Start: code2prompt for AI-DIY

## TL;DR - Just Run These

```bash
cd /Users/ralph/Documents/NoHub/ai-diy

# Generate codebase export (architecture + code)
./code2prompt-codebase.command

# Generate samples export (what the app produces)
./code2prompt-samples.command

# Check outputs
ls -lh dist/ai-diy-*
```

## What You Get

### File 1: `dist/ai-diy-codebase-{timestamp}.txt`
**Contains**: Application code, architecture docs, persona definitions
**Use for**: Technical architecture review, API design feedback
**Share with AIs to ask**: "How should I build the Sprint Orchestration layer?"

### File 2: `dist/ai-diy-samples-{timestamp}.txt`
**Contains**: Vision docs, backlogs, wireframes, generated code
**Use for**: Workflow quality review, artifact assessment
**Share with AIs to ask**: "Are these artifacts good enough for code generation?"

## Key Questions to Ask Other AIs

### Using Codebase Export
1. How should I architect Sprint Orchestration (requirements → code)?
2. Windsurf Cascade API vs VS Code Extension - which approach?
3. How to orchestrate Mike → Alex → Jordan workflow?
4. Framework detection strategy (React vs Python)?
5. Any red flags in current architecture?

### Using Samples Export
1. Are vision docs sufficient for requirements gathering?
2. Can wireframes be reliably converted to working apps?
3. Is CSV backlog format appropriate for sprint planning?
4. Quality of generated code in execution-sandbox?
5. What artifacts are missing from the workflow?

## Files Created

✅ `code2prompt-codebase.command` - Exports application code
✅ `code2prompt-samples.command` - Exports working samples
✅ `CODE2PROMPT_USAGE.md` - Detailed documentation
✅ `QUICK_START_CODE2PROMPT.md` - This file

## Output Location

All exports go to: `dist/ai-diy-{type}-{timestamp}.txt`

Same directory as your existing `zip_for_architect.command` outputs.

---

**Ready to use!** Just run the commands above.

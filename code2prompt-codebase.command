#!/bin/bash
# Generate code2prompt output for AI-DIY codebase (architecture + code)
# Output: dist/ai-diy-codebase-{timestamp}.txt
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
OUT_DIR="$BASE_DIR/dist"
OUTPUT_FILE="$OUT_DIR/ai-diy-codebase-$TIMESTAMP.txt"

mkdir -p "$OUT_DIR"

echo "🔍 Generating code2prompt for AI-DIY codebase..."

# Generate prompt with core codebase files
code2prompt \
  "$BASE_DIR" \
  --output-file "$OUTPUT_FILE" \
  --line-numbers \
  --tokens format \
  --include "myvision.md" \
  --include "README.md" \
  --include "architect/*.md" \
  --include "models_config.json" \
  --include "development/src/*.py" \
  --include "development/src/api/*.py" \
  --include "development/src/core/*.py" \
  --include "development/src/static/index.html" \
  --include "development/requirements.txt" \
  --include "development/.env.example" \
  --include "system_prompts/**" \
  --exclude "**/__pycache__/**" \
  --exclude "**/.venv/**" \
  --exclude "**/.git/**" \
  --exclude "**/.pytest_cache/**" \
  --exclude "**/logs/**" \
  --exclude "**/dist/**" \
  --exclude "**/stable/**" \
  --exclude "**/archive/**" \
  --exclude "**/.DS_Store" \
  --exclude "**/*.pyc" \
  --exclude "**/.env" \
  --exclude "**/static/appdocs/scribe/**" \
  --exclude "**/static/appdocs/visions/**" \
  --exclude "**/execution-sandbox/**"

# Add header context to the file
TEMP_FILE=$(mktemp)
cat > "$TEMP_FILE" << 'EOF'
# AI-DIY Codebase Review - Architecture & Implementation

## Context
This is the **CODEBASE** export for AI-DIY (Agile in a Box) - showing the application's architecture, code, and technical documentation.

## What This Contains
- **Vision & Architecture**: myvision.md, architecture.md, governance docs
- **Core Application**: FastAPI backend, streaming chat, persona system
- **API Endpoints**: Vision, Backlog, Scribe, Change Requests, Testing
- **Integration Layer**: Windsurf/Cascade integration, Builder executor
- **Persona Definitions**: config_personas.json (all AI team members)
- **Frontend**: index.html (complete web UI)
- **Documentation**: Process docs, persona guides

## What This Does NOT Contain
- Runtime data (logs, scribe notes, conversation history)
- Working examples of what the app produces (see separate "samples" export)
- Execution sandbox contents
- Environment variables (.env)

## Review Questions
1. **Sprint Orchestration**: How should I bridge requirements → working code?
2. **API Choice**: Windsurf Cascade API vs VS Code Extension vs hybrid?
3. **Workflow Design**: Mike (architect) → Alex (dev) → Jordan (QA) orchestration?
4. **Framework Detection**: How should Mike choose React vs Python vs other?
5. **Architecture Concerns**: Any red flags in current approach?

---

EOF

cat "$OUTPUT_FILE" >> "$TEMP_FILE"
mv "$TEMP_FILE" "$OUTPUT_FILE"

echo ""
echo "✅ Codebase export complete!"
echo "📄 Output: $OUTPUT_FILE"
echo "📊 File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "This file contains the APPLICATION CODE and ARCHITECTURE."
echo "Use this to get feedback on technical implementation and design."

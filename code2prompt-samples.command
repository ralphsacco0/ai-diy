#!/bin/bash
# Generate code2prompt output for AI-DIY working samples
# Output: dist/ai-diy-samples-{timestamp}.txt
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
OUT_DIR="$BASE_DIR/dist"
OUTPUT_FILE="$OUT_DIR/ai-diy-samples-$TIMESTAMP.txt"

mkdir -p "$OUT_DIR"

echo "📋 Generating code2prompt for AI-DIY working samples..."

# Check if sample directories exist
STATIC_DOCS="$BASE_DIR/development/src/static/appdocs"
if [ ! -d "$STATIC_DOCS" ]; then
  echo "⚠️  Warning: No appdocs directory found at $STATIC_DOCS"
  echo "Creating sample output anyway..."
fi

# Generate prompt with working samples
code2prompt \
  "$BASE_DIR" \
  --output-file "$OUTPUT_FILE" \
  --line-numbers \
  --tokens format \
  --include "development/src/static/appdocs/visions/*.json" \
  --include "development/src/static/appdocs/visions/*.md" \
  --include "development/src/static/appdocs/backlog/*.csv" \
  --include "development/src/static/appdocs/backlog/*.json" \
  --include "development/src/static/appdocs/backlog/wireframes/*.html" \
  --include "development/src/static/appdocs/scribe/*.json" \
  --include "development/src/static/appdocs/*.md" \
  --include "execution-sandbox/client-projects/**/*.py" \
  --include "execution-sandbox/client-projects/**/*.js" \
  --include "execution-sandbox/client-projects/**/*.html" \
  --include "execution-sandbox/client-projects/**/*.css" \
  --include "execution-sandbox/templates/**/*" \
  --exclude "**/__pycache__/**" \
  --exclude "**/.git/**" \
  --exclude "**/.DS_Store" \
  --exclude "**/node_modules/**" \
  --exclude "**/*.pyc"

# Add header context to the file
TEMP_FILE=$(mktemp)
cat > "$TEMP_FILE" << 'EOF'
# AI-DIY Working Samples - Output Examples

## Context
This is the **SAMPLES** export for AI-DIY (Agile in a Box) - showing real examples of what the application produces during its workflow.

## What This Contains
- **Vision Documents**: Approved vision docs created during Vision Meetings
- **Backlog Files**: CSV backlogs with user stories and acceptance criteria
- **Wireframes**: HTML wireframes generated during Requirements Meetings
- **Scribe Notes**: Meeting transcripts, decisions, and sign-offs
- **Client Projects**: Code generated in execution-sandbox
- **Templates**: Scaffolding templates used for new projects

## What This Does NOT Contain
- Application source code (see separate "codebase" export)
- Architecture documentation
- Persona definitions

## Why This Matters
These samples show:
1. **Input Quality**: What the app receives from users during meetings
2. **Output Quality**: What the app produces (vision docs, backlogs, wireframes)
3. **Generated Code**: What Alex (Developer) creates in execution-sandbox
4. **Meeting Records**: What Scribe captures for AI memory

## Review Questions
1. **Artifact Quality**: Are the vision docs, backlogs, and wireframes sufficient for code generation?
2. **Wireframe Fidelity**: Can these HTML wireframes be reliably converted to working apps?
3. **Backlog Structure**: Is the CSV format appropriate for sprint planning?
4. **Code Generation**: Do the execution-sandbox samples show viable output?
5. **Missing Artifacts**: What additional documents/artifacts would help the workflow?

---

EOF

cat "$OUTPUT_FILE" >> "$TEMP_FILE"
mv "$TEMP_FILE" "$OUTPUT_FILE"

echo ""
echo "✅ Samples export complete!"
echo "📄 Output: $OUTPUT_FILE"
echo "📊 File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "This file contains WORKING SAMPLES of what the app produces."
echo "Use this to get feedback on artifact quality and workflow outputs."

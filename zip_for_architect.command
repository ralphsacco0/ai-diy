#!/bin/bash
# Package the AI-DIY project into a clean zip for architect review (macOS)
# Updated for new development/src structure and enhanced architecture
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
OUT_DIR="$BASE_DIR/dist"
ZIP_NAME="ai-diy-architect-$TIMESTAMP.zip"
MANIFEST="$OUT_DIR/ai-diy-manifest-$TIMESTAMP.txt"

mkdir -p "$OUT_DIR"

echo "Preparing AI-DIY file list..."
# Build list of included files using find, pruning unwanted paths
INCLUDE_LIST=$(mktemp)
find "$BASE_DIR" -type d \( \
  -name ".git" -o -name ".venv" -o -name "__pycache__" -o -name ".pytest_cache" -o -name "logs" -o -name "archive" \
  -o -name ".history" -o -name ".DS_Store" -o -name ".mypy_cache" -o -name "dist" -o -name "scribe" -o -name "stable" \
\) -prune -false -o -type f ! -name ".DS_Store" \
  | sed "s|$BASE_DIR/||" \
  | grep -v '^dist/' \
  | grep -v '^stable/' \
  | grep -v '^development/src/logs/' \
  | grep -v '^development/src/static/appdocs/scribe/' \
  | grep -Ev '(\.db$|\.pid$|\.env$|conversations_.*\.json$|meeting_notes\.json$|decisions\.json$|agreements\.json$)' \
  > "$INCLUDE_LIST"

echo "Writing manifest: $MANIFEST"
{
  echo "AI-DIY Backup Package Manifest"
  echo "Generated: $(date)"
  echo ""
  echo "Included files:"
  cat "$INCLUDE_LIST"
  echo ""
  echo "Excluded patterns:"
  echo "  .git/, .venv/, __pycache__/, .pytest_cache/, .DS_Store"
  echo "  logs/, archive/, dist/, stable/ (production duplicate)"
  echo "  development/src/logs/ (runtime logs)"
  echo "  development/src/static/appdocs/scribe/ (runtime conversation data)"
  echo "  *.db, *.pid, .env, conversations_*.json, meeting_notes.json"
  echo ""
  echo "AI-DIY Architecture Overview:"
  echo ""
  echo "ARCHITECTURE DOCUMENTATION:"
  echo "  architect/ - Architecture documentation and governance"
  echo "    architecture.md - Technical architecture and contracts"
  echo "    adr.jsonl - Architecture Decision Records (ADR log)"
  echo "    governance_process.md - Development governance process"
  echo ""
  echo "  myvision.md - Product vision and meeting framework (VITAL)"
  echo "  README.md - Operational guide and critical design rules (VITAL)"
  echo "  config_personas.json - AI persona definitions (canonical source)"
  echo ""
  echo "DEVELOPMENT ENVIRONMENT:"
  echo "  development/src/ - Main application source code"
  echo "    main.py - FastAPI app entry point"
  echo "    streaming.py - Real-time streaming chat with AI personas"
  echo "    windsurf_integration.py - Enhanced Windsurf IDE integration"
  echo "    builder.py - Code execution and testing framework"
  echo ""
  echo "  development/src/api/ - API endpoint modules"
  echo "    scribe.py - Meeting recorder and AI memory system"
  echo "    change_requests.py - Code change request handling"
  echo "    testing.py - Automated testing framework"
  echo "    vision.py - Project vision and requirements management"
  echo "    chat.py - Chat API for persona interactions"
  echo "    models.py - Data models and schemas"
  echo ""
  echo "  development/src/core/ - Core system components"
  echo "    models_config.py - AI model configuration management"
  echo ""
  echo "  development/src/static/ - Web interface and documentation"
  echo "    index.html - Main web UI (comprehensive interface)"
  echo "    appdocs/ - Project documentation and artifacts"
  echo "      visions/ - Vision document storage (client-specific, optional)"
  echo "      Backlog.md, Sprint.md, Scribe.md - Project management docs"
  echo ""
  echo "EXECUTION ENVIRONMENT:"
  echo "  execution-sandbox/ - Isolated code execution environment"
  echo "    client-projects/ - Client code execution workspace"
  echo "    templates/ - Code templates and scaffolding"
  echo ""
  echo "KEY ARCHITECTURAL FEATURES:"
  echo "  - Multi-persona AI team (PM, Architect, Developer, QA, Scribe)"
  echo "  - Meeting-driven development workflow (Vision, Backlog, Planning, Review, Retro)"
  echo "  - Real-time streaming chat interface"
  echo "  - Automated code generation and testing via Builder"
  echo "  - Scribe memory system for conversation tracking"
  echo "  - Vision-driven development with document persistence"
  echo "  - Isolated execution sandbox for safety"
  echo "  - Local timezone handling for all timestamps"
  echo "  - Architecture governance process (see architect/governance_process.md)"
} > "$MANIFEST"

echo "Creating zip: $OUT_DIR/$ZIP_NAME"
(
  cd "$BASE_DIR"
  # Use zip with -r and a file list to control inclusion precisely
  zip -q -r "$OUT_DIR/$ZIP_NAME" $(cat "$INCLUDE_LIST") "$MANIFEST"
)

rm -f "$INCLUDE_LIST"

echo "Done."
echo "Package: $OUT_DIR/$ZIP_NAME"
echo "Manifest: $MANIFEST"
echo ""
echo "🎯 AI-DIY package ready for architect review"
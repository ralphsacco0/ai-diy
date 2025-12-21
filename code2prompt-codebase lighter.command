#!/bin/bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
OUT_DIR="$BASE_DIR/dist"
OUTPUT_FILE="$OUT_DIR/ai-diy-codebase-light-$TIMESTAMP.txt"

mkdir -p "$OUT_DIR"

echo "🔍 Generating LIGHT code2prompt export..."
code2prompt \
  "$BASE_DIR" \
  --output-file "$OUTPUT_FILE" \
  --line-numbers \
  --tokens format \
  --include "README.md" \
  --include "myvision.md" \
  --include "architect/**/*.md" \
  --include "docs/**/*.md" \
  --include "models_config.json" \
  --include "development/requirements.txt" \
  --include "development/.env.example" \
  --include "system_prompts/**" \
  --include "development/src/**/*.py" \
  --include "development/src/static/**/*.{html,css,js}" \
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
  --exclude "development/src/static/appdocs/**" \
  --exclude "development/src/static/appdocs*/**" \
  --exclude "development/src/static/**/backups/**" \
  --exclude "development/src/static/**/backup/**" \
  --exclude "**/execution-sandbox/**"

echo ""
echo "✅ Light export complete: $OUTPUT_FILE"
echo "📊 Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
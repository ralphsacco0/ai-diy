#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

fail() { echo -e "${RED}VALIDATION FAILED:${NC} $1"; exit 1; }
ok() { echo -e "${GREEN}$1${NC}"; }
warn() { echo -e "${YELLOW}WARNING:${NC} $1"; }

# Python available?
if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 not found. Install Python 3 to run validations."
fi

# Scanners
python3 tools/scanners/scan_persona_in_code.py || fail "Persona/instruction text detected in code."
python3 tools/scanners/scan_hardcoded_models.py || warn "Hard-coded model names found in code."
python3 tools/scanners/scan_stubs.py || warn "Unapproved TODO/STUB/WORKAROUND found."
python3 tools/scanners/validate_models_config.py || warn "models_config.json missing or invalid."

# Optional: run pytest if present
if command -v pytest >/dev/null 2>&1; then
  echo "Running tests (pytest -q)..."
  if ! pytest -q; then
    fail "Tests failed."
  fi
else
  echo "pytest not found; skipping tests."
fi

ok "Validation passed."

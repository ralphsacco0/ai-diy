#!/bin/bash
set -euo pipefail
cd "$(cd "$(dirname "$0")" && pwd)/.."
exec ./scripts/ai-commit.sh "$@"

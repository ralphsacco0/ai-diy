#!/bin/bash
# Auto-commit script for AI changes
# This script automatically commits and pushes changes made during AI conversations

set -euo pipefail

# Get the repository root
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

# Check if there are any changes to commit
if git diff --quiet && git diff --cached --quiet; then
    echo "No changes to commit."
    exit 0
fi

# Generate a commit message based on the changes
echo "Auto-committing AI changes..."

# Use the existing AI commit script
exec ./scripts/ai-commit.command "AI: Auto-commit changes from conversation"

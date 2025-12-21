#!/bin/bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

msg="${*:-AI commit}"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Initializing git repo..."
  git init
fi

echo "Staging changes..."
git add -A

echo "Running validation..."
./tools/validate.sh

echo "Creating commit..."
if git diff --cached --quiet; then
  echo "No staged changes to commit."
else
  git commit -m "$msg"
fi

# Push if a remote exists
if git remote >/dev/null 2>&1; then
  remotes=$(git remote | wc -l | tr -d ' ')
  if [ "$remotes" -gt 0 ]; then
    current_branch="$(git rev-parse --abbrev-ref HEAD)"
    echo "Pushing to upstream (branch: $current_branch)..."
    git push -u origin "$current_branch" || true
  else
    echo "No git remote set; skipping push."
  fi
else
  echo "No git remote set; skipping push."
fi

echo "Done."

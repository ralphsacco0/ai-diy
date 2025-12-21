#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {".git", "tools/scanners", "node_modules", "build", "dist", ".venv", "venv", "__pycache__", "tests", "development/tests", "development/src/tests", "stable", ".history"}
CODE_EXTS = {".py"}

patterns = [
    (re.compile(r"(?i)\byou are\b"), 40),  # likely instruction opener
    (re.compile(r"(?i)\bsystem prompt\b"), 0),
    (re.compile(r"(?i)\bpersona\b"), 160),  # long lines with 'persona'
]

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    return any(d in parts for d in IGNORE_DIRS)

violations = []
repo = Path(__file__).resolve().parents[2]
for root, dirs, files in os.walk(repo):
    # prune ignored dirs
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
    for f in files:
        p = Path(root) / f
        if p.suffix not in CODE_EXTS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if len(stripped) < 10:
                continue
            for rx, min_len in patterns:
                if len(stripped) >= min_len and rx.search(stripped):
                    # Heuristic: allow purely code-like lines without spaces
                    if len(stripped.split()) <= 3:
                        continue
                    violations.append(f"{p}:{i}: persona-like instruction text: {stripped[:120]}")
                    break

if violations:
    print("Persona/instruction text found in code (keep personas in data/docs, not .py):", file=sys.stderr)
    for v in violations[:50]:
        print(" -", v, file=sys.stderr)
    if len(violations) > 50:
        print(f" ... and {len(violations)-50} more", file=sys.stderr)
    sys.exit(1)

sys.exit(0)

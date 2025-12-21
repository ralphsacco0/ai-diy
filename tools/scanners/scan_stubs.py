#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {".git", "tools/scanners", "node_modules", "build", "dist", ".venv", "venv", "__pycache__"}
SCAN_EXTS = {".py", ".ts", ".js", ".md", ".sh", ".json", ".yaml", ".yml"}

tokens = [r"TODO", r"FIXME", r"WORKAROUND", r"STUB"]
rx = re.compile("|".join(tokens), re.IGNORECASE)
adr_rx = re.compile(r"ADR[- :]?\d+", re.IGNORECASE)

repo = Path(__file__).resolve().parents[2]
violations = []

for root, dirs, files in os.walk(repo):
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
    for f in files:
        p = Path(root) / f
        if p.suffix.lower() not in SCAN_EXTS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if rx.search(line):
                # Allow if ADR reference present on the same line
                if not adr_rx.search(line):
                    violations.append(f"{p}:{i}: {line.strip()[:120]}")

if violations:
    print("Found TODO/FIXME/STUB/WORKAROUND without ADR reference (add e.g., 'ADR-001' on the same line):", file=sys.stderr)
    for v in violations[:100]:
        print(" -", v, file=sys.stderr)
    if len(violations) > 100:
        print(f" ... and {len(violations)-100} more", file=sys.stderr)
    sys.exit(1)

sys.exit(0)

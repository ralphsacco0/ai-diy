#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {".git", "tools/scanners", "node_modules", "build", "dist", ".venv", "venv", "__pycache__"}
IGNORE_FILES = {"models_config.json"}
SCAN_EXTS = {".py", ".ts", ".js", ".json", ".yaml", ".yml"}

model_tokens = [
    r"gpt-",
    r"claude-",
    r"llama",
    r"mixtral",
    r"mistral",
    r"sonnet",
    r"haiku",
    r"command-",
]
rx = re.compile("|".join(model_tokens), re.IGNORECASE)

repo = Path(__file__).resolve().parents[2]
violations = []

for root, dirs, files in os.walk(repo):
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
    for f in files:
        p = Path(root) / f
        if p.name in IGNORE_FILES:
            continue
        if p.suffix.lower() not in SCAN_EXTS:
            continue
        # Allow listing in docs or README, but block in code/config outside models_config.json
        is_doc = any(seg.lower() in {"readme.md", "docs", "architect", "architecture.md"} for seg in p.parts)
        if is_doc:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if rx.search(text):
            violations.append(str(p))

if violations:
    print("Hard-coded model names found outside models_config.json:", file=sys.stderr)
    for v in sorted(set(violations)):
        print(" -", v, file=sys.stderr)
    sys.exit(1)

sys.exit(0)

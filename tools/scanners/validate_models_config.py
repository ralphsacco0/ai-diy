#!/usr/bin/env python3
import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[2]

candidates = [repo / "models_config.json", repo / "config" / "models_config.json"]
config_path = None
for c in candidates:
    if c.exists():
        config_path = c
        break

if not config_path:
    print("models_config.json not found at repo root or config/. Create it with at least {\"default_model\": \"...\"}.", file=sys.stderr)
    sys.exit(1)

try:
    data = json.loads(config_path.read_text(encoding="utf-8"))
except Exception as e:
    print(f"Failed to parse {config_path}: {e}", file=sys.stderr)
    sys.exit(1)

if not isinstance(data, dict):
    print("models_config.json must be a JSON object.", file=sys.stderr)
    sys.exit(1)

default_model = data.get("default_model")
if not isinstance(default_model, str) or not default_model.strip():
    print("models_config.json must contain a non-empty string key 'default_model'.", file=sys.stderr)
    sys.exit(1)

# Optional: validate providers/models maps if present
for key in ("models", "providers"):
    if key in data and not isinstance(data[key], dict):
        print(f"If present, '{key}' must be an object (map).", file=sys.stderr)
        sys.exit(1)

sys.exit(0)

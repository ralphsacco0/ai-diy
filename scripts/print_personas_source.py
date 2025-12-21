#!/usr/bin/env python3
import sys, json
from pathlib import Path

def main():
    try:
        # Adjust import path if your package layout differs
        sys.path.insert(0, str(Path.cwd() / "development" / "src"))
        from services.ai_gateway import resolve_personas_path, load_personas
    except Exception as e:
        print(f"[personas] unable to import loader: {e}")
        sys.exit(0)

    try:
        path = resolve_personas_path()
    except Exception as e:
        print(f"[personas] resolve_personas_path failed: {e}")
        sys.exit(0)

    src = str(path)
    ext = Path(src).suffix.lower()
    try:
        personas = load_personas()
        count = len(personas) if isinstance(personas, dict) else 0
    except Exception as e:
        print(f"[personas] load_personas failed from {src}: {e}")
        sys.exit(0)

    print(json.dumps({
        "personas_source_ext": ext,
        "personas_path": src,
        "personas_count": count
    }))

if __name__ == "__main__":
    main()

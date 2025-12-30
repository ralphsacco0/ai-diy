#!/usr/bin/env python3
"""
Test script to show exactly what CURRENT FILE STRUCTURE Alex sees.
Now uses the shared project_context module (Stage 1 implementation).
"""
import sys
from pathlib import Path

# Add development/src to path so we can import the shared module
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / "development" / "src"))

from services.project_context import extract_file_structure, extract_api_endpoints

def build_snapshot(project_name: str) -> str:
    """Build CURRENT FILE STRUCTURE snapshot using shared extraction utilities."""
    
    # Same path resolution as ai_gateway.py
    execution_sandbox = script_dir / "development" / "src" / "static" / "appdocs" / "execution-sandbox" / "client-projects"
    project_path = execution_sandbox / project_name
    
    print(f"Project path: {project_path}")
    print(f"Exists: {project_path.exists()}\n")
    
    if not project_path.exists():
        return f"ERROR: Project path does not exist: {project_path}"
    
    # Use shared extraction utilities (same as ai_gateway.py now uses)
    file_structure = extract_file_structure(project_path)
    routes_info = "\n\n" + extract_api_endpoints(project_path)
    
    project_context = f"""
═══════════════════════════════════════════════════════════════════
CURRENT FILE STRUCTURE (ACTUAL project on disk):
═══════════════════════════════════════════════════════════════════
{file_structure}
{routes_info}

CRITICAL: Use the exact paths shown above when calling read_file.
Examples:
- To read authController.js: read_file(project_name="{project_name}", file_path="src/controllers/authController.js")
- To read login.html: read_file(project_name="{project_name}", file_path="public/login.html")
- To read auth.js route: read_file(project_name="{project_name}", file_path="src/routes/auth.js")
"""
    
    return project_context


if __name__ == "__main__":
    print("=" * 80)
    print("TESTING CURRENT FILE STRUCTURE SNAPSHOT BUILDER")
    print("=" * 80)
    print()
    
    snapshot = build_snapshot("yourapp")
    
    print("\n" + "=" * 80)
    print("WHAT ALEX SEES:")
    print("=" * 80)
    print(snapshot)
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Snapshot length: {len(snapshot)} characters")
    print("\nKey improvements (Stage 1):")
    print("- ✅ Now using shared project_context.py module")
    print("- ✅ Files categorized by type (controllers, routes, public, etc.)")
    print("- ✅ Shows exported functions/classes from each file")
    print("- ✅ Full paths shown (no ambiguity: 'src/controllers/authController.js')")
    print("- ✅ Examples show exact read_file() call syntax")
    print("- ✅ node_modules still filtered out")
    print("- ✅ Sprint execution can use same module later (Stage 2)")

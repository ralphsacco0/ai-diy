#!/usr/bin/env python3
from pathlib import Path

def resolve_project_root() -> Path:
    railway = Path("/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp")
    if railway.exists():
        return railway
    script_dir = Path(__file__).parent
    local = script_dir / "development" / "src" / "static" / "appdocs" / "execution-sandbox" / "client-projects" / "yourapp"
    return local

PROJECT_ROOT = resolve_project_root()
AUTH_CONTROLLER = PROJECT_ROOT / "src" / "controllers" / "authController.js"

print("Fixing authController.js redirects...")
content = AUTH_CONTROLLER.read_text()

# From /api/auth/login, we need to go up 2 levels to reach /dashboard
content = content.replace("res.redirect('dashboard')", "res.redirect('../../dashboard')")
content = content.replace("res.redirect('login?error=missing')", "res.redirect('../../login?error=missing')")
content = content.replace("res.redirect('login?error=invalid')", "res.redirect('../../login?error=invalid')")
content = content.replace("res.redirect('login')", "res.redirect('../../login')")

AUTH_CONTROLLER.write_text(content)
print("✓ Fixed redirects to use ../../ to go up from /api/auth/")

#!/usr/bin/env python3
"""
Fix absolute paths to relative paths in Railway generated app.
Run this on Railway to fix the deployed app.
"""
from pathlib import Path

# Railway paths
PROJECT_ROOT = Path("/app/development/src/static/appdocs/execution-sandbox/client-projects/BrightHR_Lite_Vision")
LOGIN_HTML = PROJECT_ROOT / "public" / "login.html"
AUTH_CONTROLLER = PROJECT_ROOT / "src" / "controllers" / "authController.js"

def fix_login_html():
    """Fix form action in login.html"""
    print(f"Fixing {LOGIN_HTML}")
    content = LOGIN_HTML.read_text()
    
    # Fix form action from absolute to relative
    content = content.replace('action="/api/auth/login"', 'action="api/auth/login"')
    
    LOGIN_HTML.write_text(content)
    print("✓ Fixed login.html form action")

def fix_auth_controller():
    """Fix redirects in authController.js"""
    print(f"Fixing {AUTH_CONTROLLER}")
    content = AUTH_CONTROLLER.read_text()
    
    # Fix redirects from absolute to relative
    content = content.replace("res.redirect('/login?error=missing')", "res.redirect('login?error=missing')")
    content = content.replace("res.redirect('/login?error=invalid')", "res.redirect('login?error=invalid')")
    content = content.replace("res.redirect('/dashboard')", "res.redirect('dashboard')")
    content = content.replace("res.redirect('/login')", "res.redirect('login')")
    
    AUTH_CONTROLLER.write_text(content)
    print("✓ Fixed authController.js redirects")

if __name__ == "__main__":
    print("Fixing Railway deployed app paths...")
    fix_login_html()
    fix_auth_controller()
    print("\n✓ All fixes applied. Restart the app to pick up changes.")

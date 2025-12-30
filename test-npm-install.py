#!/usr/bin/env python3
"""
Standalone script to test npm install in Railway environment
Run this manually to see what happens with npm install
"""

import subprocess
import os
import sys
from pathlib import Path

def resolve_project_dir() -> Path:
    """Resolve project directory for Railway or Mac.
    Tries Railway absolute path first, then local repo-relative path.
    """
    railway = Path("/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp")
    if railway.exists():
        return railway
    script_dir = Path(__file__).parent
    local = script_dir / "development" / "src" / "static" / "appdocs" / "execution-sandbox" / "client-projects" / "yourapp"
    return local

def test_npm_install():
    print("=== NPM INSTALL TEST ===")
    
    # Get the project directory (same logic as main app)
    project_dir = resolve_project_dir()
    
    print(f"Project directory: {project_dir}")
    print(f"Project exists: {project_dir.exists()}")
    
    if not project_dir.exists():
        print("ERROR: Project directory not found")
        return False
    
    try:
        # Test 1: Check if npm exists
        print("\n1. Testing npm availability...")
        npm_test = subprocess.run(["which", "npm"], capture_output=True, text=True)
        print(f"   npm location: {npm_test.stdout.strip()}")
        print(f"   which npm exit code: {npm_test.returncode}")
        
        # Test 2: Check npm version
        print("\n2. Testing npm version...")
        version_test = subprocess.run(["npm", "--version"], capture_output=True, text=True)
        print(f"   npm version: {version_test.stdout.strip()}")
        print(f"   npm version stderr: {version_test.stderr}")
        print(f"   npm version exit code: {version_test.returncode}")
        
        # Test 3: Check directory contents
        print("\n3. Checking project directory contents...")
        ls_result = subprocess.run(["ls", "-la"], cwd=str(project_dir), capture_output=True, text=True)
        print(f"   Directory contents:\n{ls_result.stdout}")
        
        # Test 4: Try npm install
        print("\n4. Running npm install...")
        print("   This may take a few minutes...")
        
        install_result = subprocess.run(
            ["npm", "install", "--verbose"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )
        
        print(f"\n=== NPM INSTALL RESULTS ===")
        print(f"Exit code: {install_result.returncode}")
        print(f"STDOUT:\n{install_result.stdout}")
        print(f"STDERR:\n{install_result.stderr}")
        
        # Check if node_modules was created
        node_modules_exists = (project_dir / "node_modules").exists()
        print(f"node_modules created: {node_modules_exists}")
        
        if install_result.returncode == 0 and node_modules_exists:
            print("\n✅ SUCCESS: npm install completed successfully!")
            return True
        else:
            print(f"\n❌ FAILED: npm install failed with exit code {install_result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ TIMEOUT: npm install timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_npm_install()
    sys.exit(0 if success else 1)

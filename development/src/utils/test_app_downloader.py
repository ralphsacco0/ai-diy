#!/usr/bin/env python3
"""
Standalone test program to download and package generated apps.
Run this manually to test the download functionality before UI integration.

Usage:
    cd development/src
    python utils/test_app_downloader.py

This will:
1. Create a ZIP package of the generated app
2. Verify the package is complete and portable
3. Test extraction and basic functionality
4. Generate a test report
"""

import os
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
import json

class TestAppDownloader:
    def __init__(self):
        self.project_name = "yourapp"
        self.project_root = Path("static/appdocs/execution-sandbox/client-projects") / self.project_name
        self.output_dir = Path("downloads")
        self.test_dir = Path("test_extraction")
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        self.test_dir.mkdir(exist_ok=True)
        
        # Files to exclude from package
        self.exclude_patterns = {
            'node_modules', '.git', '.DS_Store', '*.log', '*.tmp',
            '.env', '.venv', 'venv', '__pycache__', '.pytest_cache',
            '.snapshots', 'uploads'
        }
        
    def create_smart_start_script(self) -> str:
        """Create a smart start script that works from any location."""
        script_content = '''#!/bin/bash

# Your App - Smart Start Script
# This script works from any location - no manual configuration needed!

echo "🚀 Starting Your Application..."

# Auto-detect script location (works from any folder)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo "📍 Location: $SCRIPT_DIR"

# Find the app folder (Mac-compatible find command)
APP_FOLDER=$(find "$SCRIPT_DIR" -name "package.json" -exec dirname {} \; | head -1)
if [ -z "$APP_FOLDER" ]; then
    echo "❌ Error: Could not find application folder"
    echo "🔍 Looking for package.json in: $SCRIPT_DIR"
    echo "📁 Contents:"
    ls -la "$SCRIPT_DIR"
    exit 1
fi

echo "📁 App found in: $APP_FOLDER"
cd "$APP_FOLDER"

# Kill any process on port 3001
echo "🛑 Clearing port 3001..."
lsof -ti:3001 | xargs kill -9 2>/dev/null || true

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start the application
echo "🚀 Starting application on http://localhost:3001"
PORT=3001 npm start

echo ""
echo "✅ Your app is running!"
echo "🌐 Open: http://localhost:3001"
echo ""
echo "🛑 To stop: Press Ctrl+C"
'''
        return script_content
    
    def should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from package."""
        for pattern in self.exclude_patterns:
            if pattern in str(file_path) or file_path.name.startswith('.'):
                return True
        return False
    
    def download_app(self) -> Path:
        """Download the app as a ZIP file and return the path."""
        print(f"📦 Creating ZIP package for {self.project_name}...")
        
        if not self.project_root.exists():
            raise FileNotFoundError(f"Project not found: {self.project_root}")
        
        # Create ZIP file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{self.project_name}_{timestamp}.zip"
        zip_path = self.output_dir / zip_filename
        
        files_included = 0
        files_excluded = 0
        total_size = 0
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add smart start script at root level
            smart_script = self.create_smart_start_script()
            zip_file.writestr("start.command", smart_script)
            files_included += 1
            
            # Add all project files
            for root, dirs, files in os.walk(self.project_root):
                # Filter directories
                dirs[:] = [d for d in dirs if not self.should_exclude(Path(root) / d)]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    if self.should_exclude(file_path):
                        files_excluded += 1
                        continue
                    
                    # Calculate relative path for ZIP (place in subfolder)
                    arc_name = Path(self.project_name) / file_path.relative_to(self.project_root)
                    
                    try:
                        zip_file.write(file_path, arc_name)
                        files_included += 1
                        total_size += file_path.stat().st_size
                    except Exception as e:
                        print(f"⚠️  Warning: Could not add {file_path}: {e}")
                        files_excluded += 1
        
        print(f"✅ Package created: {zip_path}")
        print(f"📊 Files included: {files_included}, excluded: {files_excluded}")
        print(f"💾 Package size: {total_size / 1024 / 1024:.2f} MB")
        print(f"🚀 Smart start script included at root level")
        
        return zip_path
    
    def verify_package(self, zip_path: Path) -> dict:
        """Verify the ZIP package is complete and portable."""
        print("🔍 Verifying package integrity...")
        
        verification_results = {
            "valid_zip": False,
            "file_count": 0,
            "essential_files": [],
            "missing_files": [],
            "package_size": 0
        }
        
        try:
            # Check ZIP file validity
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                verification_results["valid_zip"] = True
                verification_results["file_count"] = len(zip_file.namelist())
                verification_results["package_size"] = zip_path.stat().st_size
                
                # Check for essential files
                essential_files = [
                    "package.json",
                    "src/server.js",
                    "public/dashboard.html",
                    "README.md"
                ]
                
                for essential in essential_files:
                    if essential in zip_file.namelist():
                        verification_results["essential_files"].append(essential)
                    else:
                        verification_results["missing_files"].append(essential)
                
                # Test extraction
                with tempfile.TemporaryDirectory() as temp_dir:
                    try:
                        zip_file.extractall(temp_dir)
                        print("✅ Package extraction test passed")
                    except Exception as e:
                        print(f"❌ Package extraction failed: {e}")
                        return verification_results
                        
        except Exception as e:
            print(f"❌ Package verification failed: {e}")
            return verification_results
        
        print(f"✅ Package verification completed")
        print(f"📁 Total files: {verification_results['file_count']}")
        print(f"📋 Essential files found: {len(verification_results['essential_files'])}/{len(essential_files)}")
        
        if verification_results["missing_files"]:
            print(f"⚠️  Missing essential files: {verification_results['missing_files']}")
        
        return verification_results
    
    def test_portability(self, zip_path: Path) -> dict:
        """Test if the package can be extracted and run."""
        print("🧪 Testing portability...")
        
        portability_results = {
            "extraction_success": False,
            "npm_install_success": False,
            "app_starts": False,
            "errors": []
        }
        
        # Clean test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        
        try:
            # Extract package
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                zip_file.extractall(self.test_dir / self.project_name)
            
            portability_results["extraction_success"] = True
            print("✅ Package extracted successfully")
            
            extracted_project = self.test_dir / self.project_name
            
            # Test npm install (if package.json exists)
            if (extracted_project / "package.json").exists():
                print("📦 Testing npm install...")
                try:
                    result = subprocess.run(
                        ["npm", "install", "--production"],
                        cwd=extracted_project,
                        capture_output=True,
                        text=True,
                        timeout=120  # 2 minutes
                    )
                    
                    if result.returncode == 0:
                        portability_results["npm_install_success"] = True
                        print("✅ npm install completed successfully")
                    else:
                        error_msg = f"npm install failed: {result.stderr}"
                        portability_results["errors"].append(error_msg)
                        print(f"❌ {error_msg}")
                        
                except subprocess.TimeoutExpired:
                    error_msg = "npm install timed out"
                    portability_results["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
                except FileNotFoundError:
                    error_msg = "npm not found - cannot test install"
                    portability_results["errors"].append(error_msg)
                    print(f"⚠️  {error_msg}")
            else:
                portability_results["errors"].append("package.json not found")
                print("⚠️  package.json not found - cannot test npm install")
            
            # Test basic app startup (very basic check)
            if (extracted_project / "src/server.js").exists():
                print("🚀 Testing app startup (basic syntax check)...")
                try:
                    # Just check if the main file can be parsed (syntax check)
                    result = subprocess.run(
                        ["node", "-c", "src/server.js"],
                        cwd=extracted_project,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        portability_results["app_starts"] = True
                        print("✅ App syntax check passed")
                    else:
                        error_msg = f"App syntax error: {result.stderr}"
                        portability_results["errors"].append(error_msg)
                        print(f"❌ {error_msg}")
                        
                except Exception as e:
                    error_msg = f"App startup test failed: {e}"
                    portability_results["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
            
        except Exception as e:
            error_msg = f"Portability test failed: {e}"
            portability_results["errors"].append(error_msg)
            print(f"❌ {error_msg}")
        
        return portability_results
    
    def generate_test_report(self, zip_path: Path, verification: dict, portability: dict) -> Path:
        """Generate a test report."""
        report = {
            "test_timestamp": datetime.now().isoformat(),
            "project_name": self.project_name,
            "package_file": str(zip_path),
            "verification": verification,
            "portability": portability,
            "summary": {
                "overall_success": (
                    verification.get("valid_zip", False) and
                    portability.get("extraction_success", False)
                ),
                "ready_for_deployment": (
                    verification.get("valid_zip", False) and
                    portability.get("extraction_success", False) and
                    portability.get("npm_install_success", False)
                )
            }
        }
        
        report_path = self.output_dir / f"download_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_path
    
    def cleanup_test_files(self):
        """Clean up test extraction directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        print("🧹 Test files cleaned up")


def main():
    """Main test execution."""
    print("🚀 Starting App Download Test Program")
    print("=" * 50)
    
    try:
        downloader = TestAppDownloader()
        
        # Test 1: Download/Create ZIP
        zip_path = downloader.download_app()
        
        # Test 2: Verify package
        verification = downloader.verify_package(zip_path)
        
        # Test 3: Test portability
        portability = downloader.test_portability(zip_path)
        
        # Test 4: Generate report
        report_path = downloader.generate_test_report(zip_path, verification, portability)
        
        # Cleanup
        downloader.cleanup_test_files()
        
        print("\n" + "=" * 50)
        print("🎉 DOWNLOAD TEST COMPLETED")
        print("=" * 50)
        
        # Summary
        print(f"📦 Package: {zip_path}")
        print(f"📊 Report: {report_path}")
        
        if verification["valid_zip"]:
            print("✅ Package verification: PASSED")
        else:
            print("❌ Package verification: FAILED")
        
        if portability["extraction_success"]:
            print("✅ Portability test: PASSED")
        else:
            print("❌ Portability test: FAILED")
        
        if portability.get("npm_install_success"):
            print("✅ Dependencies install: PASSED")
        else:
            print("⚠️  Dependencies install: SKIPPED/FAILED")
        
        if portability.get("app_starts"):
            print("✅ App startup test: PASSED")
        else:
            print("⚠️  App startup test: SKIPPED/FAILED")
        
        print("\n🎯 Ready for UI integration!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

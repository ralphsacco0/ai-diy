#!/bin/bash

# Cleanup script for BrightHR Lite Vision
# Removes .bak files, duplicate folders, and Mac-generated duplicates

PROJECT_DIR="/Users/ralph/Documents/NoHub/ai-diy/development/src/execution-sandbox/client-projects/BrightHR_Lite_Vision"

echo "🧹 Cleaning up $PROJECT_DIR..."
echo ""

cd "$PROJECT_DIR" || exit 1

# Remove .bak files
echo "Removing .bak files..."
find . -name "*.bak" -type f -delete
echo "✅ Removed .bak files"

# Remove " 2" duplicates (Mac creates these)
echo "Removing duplicate files (with ' 2' suffix)..."
find . -name "* 2.*" -type f -delete
find . -name "* 2" -type d -exec rm -rf {} + 2>/dev/null
echo "✅ Removed duplicate files"

# Remove old duplicate folders (from early sprint runs)
echo "Removing duplicate folder structures..."
[ -d "backend" ] && rm -rf "backend" && echo "  - Removed backend/"
[ -d "frontend" ] && rm -rf "frontend" && echo "  - Removed frontend/"
[ -d "client" ] && rm -rf "client" && echo "  - Removed client/"
[ -d "server" ] && rm -rf "server" && echo "  - Removed server/"
[ -d "tests 2" ] && rm -rf "tests 2" && echo "  - Removed tests 2/"
[ -d "src 2" ] && rm -rf "src 2" && echo "  - Removed src 2/"
[ -d "public" ] && rm -rf "public" && echo "  - Removed duplicate public/"

# Remove old test files (from when Jordan generated .py instead of .js)
echo "Removing old Python test files..."
find tests -name "*.py" -type f -delete 2>/dev/null
echo "✅ Removed old test files"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Remaining structure:"
ls -la | head -20

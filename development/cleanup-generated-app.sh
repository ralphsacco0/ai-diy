#!/bin/bash
# Cleanup/Unlock Generated App Script
# Unlocks files in the execution sandbox so you can copy/zip the generated app

set -e

PROJECT_NAME=${1:-"BrightHR_Lite_Vision"}
SANDBOX_PATH="src/execution-sandbox/client-projects/$PROJECT_NAME"

echo "🧹 Cleaning up generated app: $PROJECT_NAME"
echo "================================================"

# Step 1: Kill any running Node.js server from this project
echo "1️⃣ Stopping any running Node.js processes..."
pkill -f "$SANDBOX_PATH" 2>/dev/null || echo "   No running processes found (OK)"

# Step 2: Wait a moment for processes to fully terminate
sleep 1

# Step 3: Remove SQLite lock files
echo "2️⃣ Removing SQLite lock files..."
if [ -d "$SANDBOX_PATH" ]; then
    find "$SANDBOX_PATH" -name "*.sqlite-shm" -delete 2>/dev/null || true
    find "$SANDBOX_PATH" -name "*.sqlite-wal" -delete 2>/dev/null || true
    echo "   ✅ Lock files removed"
else
    echo "   ⚠️ Project path not found: $SANDBOX_PATH"
    exit 1
fi

# Step 4: Remove .DS_Store files (macOS metadata)
echo "3️⃣ Removing .DS_Store files..."
find "$SANDBOX_PATH" -name ".DS_Store" -delete 2>/dev/null || true
echo "   ✅ Metadata files removed"

# Step 5: Optional - Remove node_modules (makes folder much smaller and copyable)
read -p "4️⃣ Remove node_modules? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   Removing node_modules..."
    rm -rf "$SANDBOX_PATH/node_modules"
    echo "   ✅ node_modules removed (run 'npm install' to restore)"
else
    echo "   ⏭️ Skipping node_modules removal"
fi

echo ""
echo "✅ Cleanup complete! You can now:"
echo "   - Copy the folder: $SANDBOX_PATH"
echo "   - Zip it: cd src/execution-sandbox/client-projects && zip -r $PROJECT_NAME.zip $PROJECT_NAME"
echo ""

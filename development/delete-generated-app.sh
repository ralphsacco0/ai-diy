#!/bin/bash
# Delete Generated App Script
# Completely removes a generated app from the execution sandbox
# Use this to start fresh with a new sprint execution

set -e

PROJECT_NAME=${1:-"BrightHR_Lite_Vision"}
SANDBOX_PATH="src/execution-sandbox/client-projects/$PROJECT_NAME"

echo "🗑️  Delete Generated App: $PROJECT_NAME"
echo "================================================"
echo "⚠️  WARNING: This will PERMANENTLY delete:"
echo "   $SANDBOX_PATH"
echo ""
read -p "Are you sure? Type 'DELETE' to confirm: " -r
echo

if [ "$REPLY" != "DELETE" ]; then
    echo "❌ Cancelled - nothing was deleted"
    exit 0
fi

# Step 1: Kill any running processes
echo "1️⃣ Stopping any running processes..."
pkill -f "$SANDBOX_PATH" 2>/dev/null || echo "   No running processes found"
sleep 1

# Step 2: Delete the project directory
echo "2️⃣ Deleting project directory..."
if [ -d "$SANDBOX_PATH" ]; then
    rm -rf "$SANDBOX_PATH"
    echo "   ✅ Deleted: $SANDBOX_PATH"
else
    echo "   ℹ️  Directory doesn't exist: $SANDBOX_PATH"
fi

echo ""
echo "✅ Project deleted successfully!"
echo ""
echo "To create a fresh version:"
echo "   1. Open the app: http://localhost:8000"
echo "   2. Start sprint execution meeting"
echo "   3. Select Sprint SP-001"
echo "   4. Confirm execution"
echo ""

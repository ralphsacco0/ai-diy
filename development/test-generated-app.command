#!/bin/bash

# Test Generated App Script
# Runs the most recently generated app in execution-sandbox

cd "$(dirname "$0")"

echo "🔍 Finding most recent generated app..."

# Find the most recent project directory
SANDBOX_DIR="src/execution-sandbox/client-projects"
if [ ! -d "$SANDBOX_DIR" ]; then
    echo "❌ No execution-sandbox found. Generate an app first!"
    exit 1
fi

# Get the most recent project (by modification time)
LATEST_PROJECT=$(ls -t "$SANDBOX_DIR" | head -1)

if [ -z "$LATEST_PROJECT" ]; then
    echo "❌ No generated projects found in $SANDBOX_DIR"
    exit 1
fi

PROJECT_PATH="$SANDBOX_DIR/$LATEST_PROJECT"
echo "📂 Testing: $LATEST_PROJECT"
echo "📍 Path: $PROJECT_PATH"

# Check if app.py exists
if [ ! -f "$PROJECT_PATH/app.py" ]; then
    echo "❌ No app.py found in $PROJECT_PATH"
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "$PROJECT_PATH/requirements.txt" ]; then
    echo "⚠️  No requirements.txt found - skipping dependency install"
else
    echo "📦 Installing dependencies..."
    pip3 install -q -r "$PROJECT_PATH/requirements.txt"
fi

# Find an available port (start at 5000)
PORT=5000
while lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do
    echo "⚠️  Port $PORT is busy, trying next..."
    PORT=$((PORT + 1))
done

echo "🌐 Starting app on http://localhost:$PORT"
echo "📝 Project: $LATEST_PROJECT"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Save PID for stop script
echo $$ > /tmp/ai-diy-test-app.pid
echo "$PROJECT_PATH" > /tmp/ai-diy-test-app-path.txt

# Run the app
cd "$PROJECT_PATH"
python3 -c "
import sys
sys.path.insert(0, '.')
from app import app
app.run(host='0.0.0.0', port=$PORT, debug=True)
"

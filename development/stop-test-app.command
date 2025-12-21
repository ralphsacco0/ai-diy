#!/bin/bash

# Stop Test Generated App Script

cd "$(dirname "$0")"

echo "🛑 Stopping test app server..."

# Find Flask processes running from execution-sandbox
pkill -f "execution-sandbox/client-projects.*app.py"

# Also check for the specific PID if saved
if [ -f /tmp/ai-diy-test-app.pid ]; then
    PID=$(cat /tmp/ai-diy-test-app.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID 2>/dev/null
        echo "✅ Stopped test app (PID: $PID)"
    fi
    rm /tmp/ai-diy-test-app.pid
fi

# Clean up path file
if [ -f /tmp/ai-diy-test-app-path.txt ]; then
    PROJECT_PATH=$(cat /tmp/ai-diy-test-app-path.txt)
    echo "📂 Was testing: $(basename "$PROJECT_PATH")"
    rm /tmp/ai-diy-test-app-path.txt
fi

# Check if anything is still running on common test ports
for PORT in 5000 5001 5002 5003; do
    PID=$(lsof -ti:$PORT 2>/dev/null)
    if [ ! -z "$PID" ]; then
        echo "⚠️  Port $PORT still in use by PID $PID"
        echo "   Run: kill $PID"
    fi
done

echo "✅ Test app stopped"

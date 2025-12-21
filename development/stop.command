#!/bin/bash

set -e

# --- Stop any existing server first ---
echo "🛑 Stopping any existing AI-DIY Scrum App server..."
PORT=8000
PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
if [ -z "$PIDS" ]; then
    echo "✅ No server found running on port $PORT."
else
    echo "🔍 Found server processes on port $PORT: $PIDS"
    kill $PIDS
    sleep 1
    echo "✅ Server stopped."
fi

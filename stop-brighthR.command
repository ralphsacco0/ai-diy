#!/bin/bash

# Stop script for BrightHR Lite Vision project
# This script stops the Express server running on port 3000
# Double-click this file to run!
# Note: This script doesn't need a path - it just kills processes on port 3000

echo "🛑 Stopping BrightHR Lite Vision..."
echo ""

# Kill processes on port 3000 (Express server)
echo "Stopping server (port 3000)..."
lsof -ti:3000 | xargs kill -9 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Server stopped"
else
    echo "ℹ️  No process running on port 3000"
fi

echo ""
echo "✅ Done"

#!/bin/bash

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

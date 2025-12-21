#!/bin/bash

# Start script for BrightHR Lite Vision project
# This script starts the Express server (backend + static frontend on port 3000)
# Double-click this file to run!

# Use dynamic path relative to this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/development/src/execution-sandbox/client-projects/BrightHR_Lite_Vision"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Project directory not found at $PROJECT_DIR"
    echo "Please ensure SP-001 has been run and generated the project files."
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

cd "$PROJECT_DIR"

echo "🚀 Starting BrightHR Lite Vision..."
echo ""

# Check Node.js version against package.json requirements
CURRENT_NODE=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
echo "📌 Node.js version: $(node --version)"

# Read required Node version from package.json (if jq is available)
if command -v jq &> /dev/null; then
    REQUIRED_NODE=$(cat package.json 2>/dev/null | jq -r '.engines.node // "^18.0.0"' | sed 's/[^0-9]//g' | cut -c1-2)
    
    if [ "$CURRENT_NODE" -lt "$REQUIRED_NODE" ]; then
        echo ""
        echo "⚠️  WARNING: Node.js $CURRENT_NODE detected, but package.json requires Node.js $REQUIRED_NODE+"
        echo "    Continuing anyway, but installation may fail..."
    fi
    
    # Check for problematic dependencies
    HAS_BETTER_SQLITE=$(cat package.json 2>/dev/null | jq -r '.dependencies["better-sqlite3"] // empty')
    if [ -n "$HAS_BETTER_SQLITE" ] && [ "$CURRENT_NODE" -ge 23 ]; then
        echo ""
        echo "⚠️  WARNING: better-sqlite3 detected - may be incompatible with Node.js 23+"
        echo "    Continuing anyway, but compilation may fail..."
    fi
else
    # Fallback if jq not available - just check minimum
    if [ "$CURRENT_NODE" -lt 18 ]; then
        echo ""
        echo "⚠️  WARNING: Node.js $CURRENT_NODE detected (minimum recommended: 18+)"
        echo "    Continuing anyway..."
    fi
fi

# Kill any existing Node processes that might block port 3000
echo ""
echo "🔍 Checking for processes on port 3000..."
PORT_PIDS=$(lsof -ti:3000 2>/dev/null)
if [ -n "$PORT_PIDS" ]; then
    echo "   Found processes: $PORT_PIDS"
    echo "   Killing processes on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null
    sleep 1
    echo "   ✅ Port 3000 cleared"
else
    echo "   ✅ Port 3000 is free"
fi

# Clean up any failed previous installs
if [ -d "node_modules" ] && [ ! -f "node_modules/.package-lock.json" ]; then
    echo ""
    echo "⚠️  Detected incomplete node_modules (previous install may have failed)"
    echo "   Cleaning up..."
    rm -rf node_modules package-lock.json
fi

echo ""
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ npm install failed"
    echo ""
    exit 1
fi

echo "✅ Dependencies installed"
echo ""
echo "🎯 Starting server..."
echo "   Server: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

npm start

echo ""
echo "✅ Server stopped"

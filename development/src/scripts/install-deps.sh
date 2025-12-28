#!/bin/bash

# Shell script to install npm dependencies for generated app
# This bypasses Python subprocess environment issues

set -e  # Exit on any error

echo "=== NPM INSTALL SCRIPT ==="
echo "Working directory: $(pwd)"

# Find the generated app directory (fixed folder name - single pipeline)
APP_DIR="/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp"

if [ ! -d "$APP_DIR" ]; then
    echo "ERROR: App directory not found: $APP_DIR"
    exit 1
fi

echo "Changing to app directory: $APP_DIR"
cd "$APP_DIR"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "ERROR: package.json not found in $APP_DIR"
    exit 1
fi

# Check if node_modules already exists
if [ -d "node_modules" ]; then
    echo "Dependencies already installed (node_modules exists)"
    exit 0
fi

echo "Installing npm dependencies..."
echo "Node version: $(node --version)"
echo "NPM version: $(npm --version)"

# Run npm install with verbose output
npm install --verbose

echo "=== NPM INSTALL COMPLETED ==="
echo "node_modules created: $([ -d "node_modules" ] && echo "YES" || echo "NO")"

if [ -d "node_modules" ]; then
    echo "SUCCESS: Dependencies installed successfully"
    exit 0
else
    echo "ERROR: node_modules not created after npm install"
    exit 1
fi

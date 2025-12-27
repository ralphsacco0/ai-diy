#!/bin/bash

# BrightHR Lite Start Script
# This script starts the BrightHR application on port 3001

echo "🚀 Starting BrightHR Lite Application..."
echo "📍 Location: /Users/ralph/AI-DIY/ai-diy/delme/BrightHR_Lite_Vision_railway"
echo "🌐 URL: http://localhost:3001"
echo ""

# Kill any process running on port 3001
echo "🛑 Killing any existing process on port 3001..."
lsof -ti:3001 | xargs kill -9 2>/dev/null || true

# Change to the app directory using absolute path
cd /Users/ralph/AI-DIY/ai-diy/delme/BrightHR_Lite_Vision_railway

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Set port and start the application
PORT=3001 npm start

echo ""
echo "✅ BrightHR Lite is running!"
echo "🌐 Open your browser and go to: http://localhost:3001"
echo ""
echo "📝 Login Credentials:"
echo "   Admin: admin@test.com / Password123!"
echo "   Employee: john@company.com / Password123!"
echo ""
echo "🛑 To stop: Press Ctrl+C or run: pkill -f 'node src/server.js'"

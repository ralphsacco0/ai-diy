#!/bin/bash

# AI-DIY Scrum App Startup Script
# Runs from within ai-diy directory for standalone repo

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

# --- Clear Python bytecode cache ---
echo "🧹 Clearing Python bytecode cache..."
rm -rf "$(dirname "${BASH_SOURCE[0]}")/src"/**/__pycache__ 2>/dev/null || true
rm -f "$(dirname "${BASH_SOURCE[0]}")/src"/**/*.pyc 2>/dev/null || true
echo "✅ Cache cleared."

# ensure sandbox workspace exists
mkdir -p "${SANDBOX_DIR:-sandbox}"
echo "Sandbox at: ${SANDBOX_DIR:-sandbox}"

# Get the absolute path to the script's directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# --- Environment Detection ---
ENV_TYPE="development"

# If the current directory is 'stable', switch to production mode.
if [[ "$(basename "$DIR")" == "stable" ]]; then
    ENV_TYPE="stable/production"
    # Project root is one level up from the 'stable' directory
    PROJECT_ROOT="$(cd "$DIR/.." && pwd)"
else
    # We are in development - project root is one level up
    PROJECT_ROOT="$(cd "$DIR/.." && pwd)"
fi

VENV_PATH="$PROJECT_ROOT/.venv"
ENV_FILE_PATH="$PROJECT_ROOT/.env"

echo "🚀 Starting AI-DIY Scrum App ($ENV_TYPE)..."
echo "Directory: $DIR"

# --- Virtual Environment ---
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "Please run the main setup script from the project root."
    exit 1
fi
source "$VENV_PATH/bin/activate"

# --- Dependencies ---
echo "📦 Installing/updating requirements..."
pip install -r requirements.txt > /dev/null

# --- .env File ---
if [ ! -f "$ENV_FILE_PATH" ]; then
    echo "⚠️ No .env file found at $ENV_FILE_PATH"
    echo "Please create one from .env.example and add your API key."
    exit 1
fi

# --- PYTHONPATH & APP_ENV ---
if [[ "$ENV_TYPE" == "development" ]]; then
    export PYTHONPATH="$DIR/src:${PYTHONPATH:-}"
    export APP_ENV="DEV"
else
    export PYTHONPATH="$DIR:${PYTHONPATH:-}"
    export APP_ENV="STABLE"
fi

# --- VERBOSE LOGGING (for debugging) ---
# CURRENT SETTINGS (to restore when done):
export OPENROUTER_LOG_PAYLOADS="false"
export OPENROUTER_LOG_SAMPLE="0.0"
export USER_LOG_ENABLED="false"
export USER_LOG_LEVEL="INFO"
#
# ENABLED FOR DEBUGGING:
#export OPENROUTER_LOG_PAYLOADS="true"
#export OPENROUTER_LOG_SAMPLE="1.0"
#export USER_LOG_ENABLED="true"
#export USER_LOG_LEVEL="DEBUG"

# --- Start Server ---
echo "🌐 Starting server on http://localhost:8000"
echo "Press Ctrl+C to stop the server"

# Change to src directory where main.py is located (both dev and stable)
cd "$DIR/src"

# Dynamically build and execute the uvicorn command
UVICORN_CMD="uvicorn main:app --host 0.0.0.0 --port 8000"

if [ "$ENV_TYPE" == "development" ]; then
    # No auto-reload to prevent interruptions during bounded loop execution
    UVICORN_CMD+=""
else
    # For stable, load the .env file from the parent directory
    UVICORN_CMD+=" --env-file '$ENV_FILE_PATH'"
fi

eval $UVICORN_CMD

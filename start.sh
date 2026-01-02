#!/usr/bin/env bash
set -euo pipefail

echo "Starting AI-DIY with Caddy reverse proxy..."

# FastAPI runs on internal port 8001 (not exposed externally)
# Caddy handles external PORT (Railway sets this to 8000)
FASTAPI_PORT=8001

# Start FastAPI app in background on internal port
echo "Starting FastAPI on 127.0.0.1:${FASTAPI_PORT}..."
uvicorn main:app --host 127.0.0.1 --port ${FASTAPI_PORT} &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
echo "Waiting for FastAPI to start..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:${FASTAPI_PORT}/health > /dev/null 2>&1; then
        echo "FastAPI is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: FastAPI failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Start generated Node.js app on port 3000 (if it exists)
GENERATED_APP_PATH="/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp"
if [ -f "${GENERATED_APP_PATH}/src/server.js" ]; then
    echo "Starting generated Node.js app on 127.0.0.1:3000..."
    cd "${GENERATED_APP_PATH}"
    PORT=3000 node src/server.js > /tmp/yourapp.log 2>&1 &
    NODEJS_PID=$!
    echo "Generated app started with PID ${NODEJS_PID}"
    cd /app/development/src
else
    echo "No generated app found at ${GENERATED_APP_PATH}, skipping..."
fi

# Start Caddy in foreground (handles Railway PORT, typically 8000)
echo "Starting Caddy on port ${PORT:-8000}..."
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile

#!/usr/bin/env bash
set -euo pipefail

echo "Starting AI-DIY with Caddy reverse proxy..."

# Start FastAPI app in background on internal port
echo "Starting FastAPI on 127.0.0.1:8000..."
uvicorn main:app --host 127.0.0.1 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
echo "Waiting for FastAPI to start..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "FastAPI is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: FastAPI failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Start Caddy in foreground (handles Railway PORT)
echo "Starting Caddy on port ${PORT:-8080}..."
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile

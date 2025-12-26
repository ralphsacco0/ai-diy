# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Caddy
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && echo 'deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x for sprint execution (npm install, node --test)
# Required for executing Node.js/Express sprints on Railway
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify Node.js, npm, and Caddy are installed
RUN node --version && npm --version && caddy version

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Copy Caddyfile
COPY Caddyfile /etc/caddy/Caddyfile

# Set Python path to include development/src
ENV PYTHONPATH=/app/development/src

# Change working directory to where main.py is located
WORKDIR /app/development/src

# Create startup script
RUN echo '#!/bin/bash\n\
# Start FastAPI app in background on internal port only\n\
uvicorn main:app --host 127.0.0.1 --port 8000 &\n\
# Wait a moment for FastAPI to start\n\
sleep 3\n\
# Start Caddy in foreground\n\
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile' > /app/start.sh && \
chmod +x /app/start.sh

# Expose port (Railway sets this via PORT env var)
EXPOSE 8000

# Start Caddy (which will proxy to FastAPI)
CMD ["/app/start.sh"]

# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Caddy using the official install script
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    ca-certificates \
    && curl -1sLf 'https://caddyserver.com/api/download?os=linux&arch=amd64' -o /usr/bin/caddy \
    && chmod +x /usr/bin/caddy \
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

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Start Caddy (which will proxy to FastAPI)
CMD ["/app/start.sh"]

# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Node.js 20.x for sprint execution (npm install, node --test)
# Required for executing Node.js/Express sprints on Railway
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify Node.js and npm are installed
RUN node --version && npm --version

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Set Python path to include development/src
ENV PYTHONPATH=/app/development/src

# Change working directory to where main.py is located
WORKDIR /app/development/src

# Expose port
EXPOSE 8000

# Start the application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

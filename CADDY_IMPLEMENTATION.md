# Caddy Reverse Proxy Implementation

## Overview

This document describes the Caddy reverse proxy implementation that replaces the custom Python-based proxy in AI-DIY.

## Architecture

```
Internet → Caddy (Port 80) → FastAPI (Port 8000) → Generated Apps (Port 3000)
```

### Traffic Flow

1. **Main Application** (`/`, `/api/*`, `/static/*`) → Caddy → FastAPI (Port 8000)
2. **Generated Apps** (`/yourapp/*`) → Caddy → Generated App (Port 3000)
3. **Health Checks** (`/health`) → Caddy → FastAPI (Port 8000)

## Configuration Files

### Caddyfile
- Location: `/etc/caddy/Caddyfile` (in container)
- Handles reverse proxy routing
- Manages health checks for both FastAPI and generated apps
- Serves static files directly

### Dockerfile Changes
- Installs Caddy from official repository
- Creates startup script that runs FastAPI in background, Caddy in foreground
- Exposes port 80 instead of 8000

### railway.json Changes
- Sets deployment port to 80 (Caddy's port)

## Benefits

1. **Performance**: Caddy is written in Go and handles concurrent connections efficiently
2. **Reliability**: Purpose-built reverse proxy with robust error handling
3. **Security**: Automatic HTTPS handling (when enabled)
4. **Simplified Code**: Removed complex Python proxy logic
5. **Health Checks**: Built-in health monitoring for backend services

## Migration Notes

### Removed from main.py
- Custom proxy endpoints (`/yourapp/{path:path}`)
- HTML rewriting functions (`rewrite_html_paths`)
- HTTP client proxy logic
- Import of `httpx` for proxy functionality

### Preserved Functionality
- App control API (`/api/control-app`) still works
- Generated apps still start on port 3000
- All existing API endpoints unchanged
- Static file serving unchanged

## Testing

To test the Caddy configuration locally:

```bash
# Build and run with Docker
docker build -t ai-diy-caddy .
docker run -p 80:80 ai-diy-caddy

# Test main application
curl http://localhost/health

# Start a generated app
curl -X POST http://localhost/api/control-app \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'

# Test generated app proxy
curl http://localhost/yourapp/
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure nothing else is using port 80
2. **Health Checks**: Verify FastAPI is responding on port 8000
3. **Generated Apps**: Ensure they start on port 3000

### Logs

- Caddy logs: `/var/log/caddy.log`
- FastAPI logs: stdout/stderr
- Generated app logs: via sprint execution logs

### Debug Commands

```bash
# Check Caddy configuration
caddy validate --config /etc/caddy/Caddyfile

# Test Caddy dry run
caddy run --config /etc/caddy/Caddyfile --dry-run

# Check listening ports
netstat -tlnp | grep -E ':(80|8000|3000)'
```

## Future Enhancements

1. **HTTPS**: Enable automatic HTTPS with `auto_https on`
2. **Rate Limiting**: Add rate limiting for API endpoints
3. **Caching**: Configure static file caching
4. **Load Balancing**: Add multiple FastAPI instances behind Caddy

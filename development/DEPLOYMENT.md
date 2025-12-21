# AI-DIY Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the AI-DIY application in development and production environments. The deployment process follows the fail-fast configuration principles and includes all security enhancements.

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Git
- Required environment variables set
- Models configuration file

### One-Line Setup

```bash
# Clone repository
git clone <repository-url>
cd ai-diy

# Setup development environment
python development/setup_config.py --environment development

# Validate configuration
python development/validate_config.py

# Start application
python development/src/main_integrated.py
```

## Environment Configuration

### Required Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `LOG_LEVEL` | Logging level | Yes | `INFO` |
| `DATA_ROOT` | Data directory path | Yes | `static/appdocs` |
| `MODELS_CONFIG_PATH` | Models configuration file | No | `models_config.json` |

### Optional Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PORT` | Server port | `8000` | `8080` |
| `HOST` | Server host | `127.0.0.1` | `0.0.0.0` |
| `PRODUCTION` | Production mode | `false` | `true` |

## Development Deployment

### Local Development Setup

1. **Set Environment Variables**
   ```bash
   export LOG_LEVEL=DEBUG
   export DATA_ROOT=static/appdocs
   export PRODUCTION=false
   ```

2. **Configure Models**
   ```bash
   # Edit models_config.json with your preferred models
   {
     "favorites": ["deepseek/deepseek-chat-v3-0324"],
     "default": null,
     "meta": {},
     "last_used": null,
     "last_session_name": ""
   }
   ```

3. **Start Application**
   ```bash
   python development/src/main_integrated.py
   ```

4. **Access Application**
   - Open http://localhost:8000 in your browser
   - API available at http://localhost:8000/api/*

### Development Features

- **Hot reload** for code changes
- **Debug logging** for troubleshooting
- **Relaxed CORS** for frontend development
- **File system storage** for easy data inspection

## Production Deployment

### Production Requirements

1. **Security Configuration**
   ```bash
   export LOG_LEVEL=INFO
   export DATA_ROOT=/var/lib/ai-diy/data
   export PRODUCTION=true
   export PORT=8000
   export HOST=0.0.0.0
   ```

2. **Secure Models Configuration**
   ```bash
   # Place in secure location (e.g., /etc/ai-diy/models_config.json)
   {
     "favorites": ["your-production-models"],
     "default": null,
     "meta": {},
     "last_used": null,
     "last_session_name": ""
   }
   ```

3. **Directory Setup**
   ```bash
   # Create secure data directory
   sudo mkdir -p /var/lib/ai-diy/data
   sudo chown your-user:your-group /var/lib/ai-diy/data
   chmod 750 /var/lib/ai-diy/data
   ```

### Production Features

- **Security headers** (CSP, HSTS, X-Frame-Options)
- **Rate limiting** (100 requests/minute)
- **Input validation** and sanitization
- **Structured logging** for monitoring
- **Path traversal protection**
- **File type restrictions**

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd --create-home --shell /bin/bash ai-diy
USER ai-diy

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "development/src/main_secure.py"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  ai-diy:
    build: .
    environment:
      - LOG_LEVEL=INFO
      - DATA_ROOT=/app/data
      - PRODUCTION=true
    volumes:
      - ./data:/app/data
      - ./models_config.json:/app/models_config.json
    ports:
      - "8000:8000"
    restart: unless-stopped
```

### Docker Commands

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f ai-diy

# Stop application
docker-compose down
```

## Configuration Management

### Using Setup Script

```bash
# Setup development environment
python development/setup_config.py --environment development

# Setup production environment
python development/setup_config.py --environment production

# Validate current configuration
python development/setup_config.py --validate

# Show current configuration
python development/setup_config.py --show
```

### Manual Configuration

1. **Copy Environment Template**
   ```bash
   cp development/.env.example .env
   # Edit .env with your settings
   ```

2. **Validate Configuration**
   ```bash
   python development/validate_config.py
   ```

3. **Test Configuration**
   ```bash
   python development/tests/test_integration.py
   ```

## Operational Procedures

### Health Monitoring

#### Health Check Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# Environment status
curl http://localhost:8000/api/env

# Security status
curl http://localhost:8000/api/security/status

# Data management status
curl http://localhost:8000/api/data/status
```

#### Log Monitoring

```bash
# View application logs
tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl

# Monitor security events
tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq 'select(.logger=="ai_diy.security")'

# Check for errors
tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq 'select(.level>="ERROR")'
```

### Backup Procedures

#### Data Backup

```bash
# Backup data directory
tar -czf ai-diy-backup-$(date +%Y%m%d).tar.gz static/appdocs/

# Backup configuration
tar -czf ai-diy-config-backup-$(date +%Y%m%d).tar.gz models_config.json .env

# Copy to remote storage
scp ai-diy-backup-*.tar.gz user@backup-server:/backups/
```

#### Database Backup (if applicable)

```bash
# Export application data
python development/src/export_data.py > ai-diy-export-$(date +%Y%m%d).json

# Compress and store
gzip ai-diy-export-$(date +%Y%m%d).json
```

### Troubleshooting

#### Common Issues

1. **Configuration Errors**
   ```bash
   # Validate configuration
   python development/validate_config.py

   # Check environment variables
   env | grep -E "(LOG_LEVEL|DATA_ROOT|MODELS)"

   # Verify models config exists and is valid
   python -c "import json; print(json.load(open('models_config.json')))"
   ```

2. **Permission Errors**
   ```bash
   # Check file permissions
   ls -la static/appdocs/
   ls -la models_config.json

   # Fix permissions (development)
   chmod 644 models_config.json
   chmod 755 static/appdocs/
   ```

3. **Port Conflicts**
   ```bash
   # Check what's using the port
   lsof -i :8000

   # Use different port
   export PORT=8080
   python development/src/main_integrated.py
   ```

4. **Import Errors**
   ```bash
   # Check Python path
   python -c "import sys; print('\n'.join(sys.path))"

   # Verify all dependencies installed
   pip list | grep -E "(fastapi|uvicorn|pydantic)"
   ```

#### Log Analysis

```bash
# Search for specific errors
grep "ERROR" logs/ai_diy_api_$(date +%Y%m%d).jsonl

# Find slow requests
grep "duration_ms" logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq 'select(.duration_ms > 1000)'

# Analyze request patterns
grep "API_CALL" logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq '.route' | sort | uniq -c | sort -nr
```

## Security Considerations

### Production Security Checklist

- [ ] Set `PRODUCTION=true`
- [ ] Configure secure `DATA_ROOT` path
- [ ] Set appropriate `LOG_LEVEL` (INFO or WARNING)
- [ ] Configure proper CORS origins
- [ ] Set up log rotation and monitoring
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS certificates
- [ ] Configure backup strategy
- [ ] Set up monitoring and alerting

### Security Monitoring

```bash
# Monitor rate limiting
grep "rate_limit_exceeded" logs/ai_diy_api_$(date +%Y%m%d).jsonl

# Check for suspicious activities
grep "path_traversal_attempt" logs/ai_diy_api_$(date +%Y%m%d).jsonl

# Monitor resource usage
grep "resource_usage" logs/ai_diy_api_$(date +%Y%m%d).jsonl
```

## Performance Tuning

### Memory Optimization

```bash
# Monitor memory usage
python development/src/main_integrated.py &
PID=$!
watch -n 5 "ps -o pid,ppid,pcpu,pmem,rsz,vsz,comm $PID"
```

### Request Optimization

```bash
# Monitor request performance
tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq '.duration_ms' | awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'
```

### Scaling Considerations

- **Vertical Scaling**: Increase server resources for higher throughput
- **Horizontal Scaling**: Deploy multiple instances behind load balancer
- **Database**: Consider database for high-volume deployments
- **Caching**: Implement Redis for session and data caching

## Support and Maintenance

### Regular Maintenance Tasks

1. **Daily**: Review logs for errors and security events
2. **Weekly**: Validate configuration and run test suites
3. **Monthly**: Update dependencies and security patches
4. **Quarterly**: Review and update documentation

### Getting Help

1. **Check Documentation**: Review this deployment guide
2. **Run Validation**: Use `python development/validate_config.py`
3. **Check Logs**: Review application and security logs
4. **Test Suite**: Run `python development/tests/test_integration.py`
5. **Community**: Check project repository for updates

### Update Procedures

```bash
# Backup current installation
cp -r . ../ai-diy-backup-$(date +%Y%m%d)

# Pull latest changes
git pull origin main

# Validate new configuration
python development/validate_config.py

# Run tests
python development/tests/test_integration.py

# Restart application
systemctl restart ai-diy  # If using systemd
# OR
kill $(cat ai-diy.pid) && python development/src/main_secure.py &
```

## Appendix

### File Structure

```
ai-diy/
├── architect/              # Architecture documentation
│   ├── architecture.md     # Complete system architecture
│   ├── governance_process.md # Governance and process docs
│   └── ADRs.md            # Architecture Decision Records
├── development/           # Implementation directory
│   ├── src/              # Source code
│   │   ├── api/          # API endpoints
│   │   ├── config_manager.py # Configuration management
│   │   ├── data_manager.py  # Data management
│   │   ├── logging_middleware.py # Logging system
│   │   ├── security_middleware.py # Security system
│   │   └── main_secure.py   # Main application
│   ├── tests/            # Test suites
│   ├── setup_config.py   # Configuration setup
│   ├── validate_config.py # Configuration validation
│   └── .env.example      # Configuration template
├── static/               # Static files and data
│   └── appdocs/          # Application data
├── models_config.json    # Models configuration
└── README.md            # Project overview
```

### API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application interface |
| `/health` | GET | Comprehensive health check |
| `/api/env` | GET | Environment and configuration status |
| `/api/vision` | POST | Vision document management |
| `/api/backlog` | POST | Backlog CSV management |
| `/api/security/status` | GET | Security system status |

### Configuration Files

- **`.env.example`**: Complete configuration template
- **`models_config.json`**: AI model configuration
- **`config_personas.json`**: Persona definitions (repository root)

### Test Coverage

- **Unit Tests**: Individual component validation
- **Integration Tests**: Cross-component functionality
- **Security Tests**: Comprehensive security validation
- **End-to-End Tests**: Complete workflow validation

Run all tests:
```bash
python development/tests/test_end_to_end.py
```
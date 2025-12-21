# AI-DIY Operational Runbook

## Overview

This runbook provides operational procedures for running, monitoring, and maintaining the AI-DIY application in production. Use this document for day-to-day operations and incident response.

## Daily Operations

### Application Startup

#### Normal Startup
```bash
# 1. Validate configuration
python development/validate_config.py

# 2. Start application
python development/src/main_secure.py

# 3. Verify health
curl http://localhost:8000/health
```

#### Startup with Logging
```bash
# Start with detailed logging
LOG_LEVEL=DEBUG python development/src/main_secure.py 2>&1 | tee ai-diy-startup.log

# Monitor startup process
tail -f ai-diy-startup.log | grep -E "(INFO|ERROR|✅|❌)"
```

### Health Monitoring

#### Automated Health Checks
```bash
#!/bin/bash
# daily-health-check.sh

HEALTH_URL="http://localhost:8000/health"
SECURITY_URL="http://localhost:8000/api/security/status"

echo "=== AI-DIY Daily Health Check ==="

# Basic health check
if curl -f -s $HEALTH_URL > /dev/null; then
    echo "✅ Application is healthy"
else
    echo "❌ Application health check failed"
    exit 1
fi

# Security status
SECURITY_STATUS=$(curl -s $SECURITY_URL | jq -r '.security_status')
if [ "$SECURITY_STATUS" = "active" ]; then
    echo "✅ Security systems active"
else
    echo "❌ Security systems not active"
    exit 1
fi

echo "=== Health check complete ==="
```

#### Log Monitoring
```bash
# Monitor application logs
tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl

# Monitor security events
tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq 'select(.logger=="ai_diy.security")'

# Check for errors in last hour
find logs/ -name "*.jsonl" -mtime -1 -exec grep -l "ERROR" {} \;
```

## Incident Response

### Incident Response Process

1. **Detection**: Monitor logs and health checks for anomalies
2. **Assessment**: Determine severity and impact
3. **Containment**: Isolate affected components
4. **Recovery**: Restore normal operations
5. **Review**: Document lessons learned

### Common Incidents

#### High Error Rate

**Symptoms**:
- Increased error responses in logs
- Health check failures
- User reports of application issues

**Response**:
```bash
# 1. Check current status
curl http://localhost:8000/health

# 2. Review recent errors
tail -n 50 logs/ai_diy_api_$(date +%Y%m%d).jsonl | grep '"status":"error"'

# 3. Check resource usage
curl http://localhost:8000/api/security/status | jq '.report.resource_usage'

# 4. If resource exhaustion, restart application
systemctl restart ai-diy
```

#### Security Incidents

**Symptoms**:
- Rate limit violations
- Path traversal attempts
- Suspicious input patterns

**Response**:
```bash
# 1. Review security logs
tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq 'select(.logger=="ai_diy.security")'

# 2. Check security status
curl http://localhost:8000/api/security/status

# 3. Identify attack source
grep "path_traversal_attempt" logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq '.details.client_ip'

# 4. If attack detected, consider IP blocking
# Add to firewall rules or rate limiting configuration
```

#### Performance Issues

**Symptoms**:
- Slow response times
- High resource usage
- Timeout errors

**Response**:
```bash
# 1. Check performance metrics
tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq '.duration_ms' | awk '{sum+=$1; count++} END {print "Avg response time:", sum/count, "ms"}'

# 2. Monitor resource usage
top -p $(pgrep -f "main_secure.py")

# 3. Check for resource-intensive operations
grep "duration_ms" logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq 'select(.duration_ms > 5000)'

# 4. If needed, optimize or scale resources
```

## Maintenance Procedures

### Log Rotation

#### Automated Log Rotation
```bash
#!/bin/bash
# log-rotate.sh

LOG_DIR="logs"
DAYS_TO_KEEP=30

# Rotate logs older than threshold
find $LOG_DIR -name "*.jsonl" -type f -mtime +$DAYS_TO_KEEP -delete

# Compress old logs (optional)
find $LOG_DIR -name "*.jsonl" -type f -mtime +7 -exec gzip {} \;

echo "Log rotation completed"
```

#### Manual Log Management
```bash
# View current log files
ls -la logs/

# Compress specific log file
gzip logs/ai_diy_api_20250107.jsonl

# Archive logs to external storage
tar -czf ai-diy-logs-$(date +%Y%m%d).tar.gz logs/
scp ai-diy-logs-$(date +%Y%m%d).tar.gz backup-server:/archives/
```

### Configuration Updates

#### Safe Configuration Updates
```bash
# 1. Backup current configuration
cp models_config.json models_config.json.backup
cp .env .env.backup

# 2. Validate new configuration
python development/validate_config.py

# 3. Test new configuration
python development/tests/test_integration.py

# 4. Apply new configuration
# Edit configuration files

# 5. Restart application
systemctl restart ai-diy

# 6. Verify functionality
curl http://localhost:8000/health
```

#### Rollback Procedure
```bash
# 1. Restore backup configuration
cp models_config.json.backup models_config.json
cp .env.backup .env

# 2. Restart application
systemctl restart ai-diy

# 3. Verify rollback successful
curl http://localhost:8000/health
```

### Database Maintenance (if applicable)

```bash
# Backup application data
python development/src/export_data.py > backup/ai-diy-data-$(date +%Y%m%d).json

# Verify backup integrity
python development/src/validate_backup.py backup/ai-diy-data-$(date +%Y%m%d).json

# Clean old backups
find backup/ -name "ai-diy-data-*.json" -mtime +30 -delete
```

## Monitoring and Alerting

### Key Metrics to Monitor

#### Application Metrics
- **Response Time**: Average API response time < 1000ms
- **Error Rate**: Error responses < 1% of total requests
- **Uptime**: Application availability > 99.9%
- **Resource Usage**: Memory and CPU usage within limits

#### Security Metrics
- **Rate Limit Violations**: Track blocked requests
- **Security Events**: Monitor for suspicious activities
- **Authentication Failures**: Track failed login attempts (if applicable)
- **Data Validation Errors**: Monitor input validation failures

### Alerting Rules

#### Critical Alerts
```bash
# Application down
curl -f http://localhost:8000/health || alert "AI-DIY application is down"

# High error rate (>5%)
ERROR_RATE=$(grep '"status":"error"' logs/ai_diy_api_$(date +%Y%m%d).jsonl | wc -l)
TOTAL_REQUESTS=$(grep '"status":' logs/ai_diy_api_$(date +%Y%m%d).jsonl | wc -l)
if [ $TOTAL_REQUESTS -gt 0 ]; then
    ERROR_PERCENT=$((ERROR_RATE * 100 / TOTAL_REQUESTS))
    if [ $ERROR_PERCENT -gt 5 ]; then
        alert "High error rate: $ERROR_PERCENT%"
    fi
fi
```

#### Warning Alerts
```bash
# High response time (>2000ms average)
AVG_RESPONSE=$(tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq '.duration_ms' | awk '{sum+=$1; count++} END {print sum/count}')
if [ $(echo "$AVG_RESPONSE > 2000" | bc -l) -eq 1 ]; then
    alert "High average response time: $AVG_RESPONSE ms"
fi

# Security events detected
SECURITY_EVENTS=$(grep "SECURITY_AUDIT" logs/ai_diy_api_$(date +%Y%m%d).jsonl | wc -l)
if [ $SECURITY_EVENTS -gt 10 ]; then
    alert "Unusual security event frequency: $SECURITY_EVENTS events"
fi
```

## Troubleshooting Guides

### Application Won't Start

**Symptoms**: Application fails to start or exits immediately

**Troubleshooting Steps**:

1. **Check Configuration**
   ```bash
   python development/validate_config.py
   # Fix any configuration errors reported
   ```

2. **Check Logs**
   ```bash
   # Look for startup errors
   tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl | head -20
   ```

3. **Verify Dependencies**
   ```bash
   python -c "import fastapi, uvicorn, pydantic; print('Dependencies OK')"
   ```

4. **Check File Permissions**
   ```bash
   ls -la models_config.json
   ls -la static/appdocs/
   ```

### High Memory Usage

**Symptoms**: Application using excessive memory

**Troubleshooting Steps**:

1. **Check Resource Usage**
   ```bash
   curl http://localhost:8000/api/security/status | jq '.report.resource_usage'
   ```

2. **Monitor Memory Growth**
   ```bash
   watch -n 5 'ps aux | grep main_secure.py'
   ```

3. **Check for Memory Leaks**
   ```bash
   # Look for accumulating requests or large data structures
   grep "memory_mb" logs/ai_diy_api_$(date +%Y%m%d).jsonl | tail -10
   ```

4. **Restart if Necessary**
   ```bash
   systemctl restart ai-diy
   ```

### Slow Response Times

**Symptoms**: API requests taking longer than expected

**Troubleshooting Steps**:

1. **Check Performance Metrics**
   ```bash
   tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq '.duration_ms' | awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'
   ```

2. **Identify Slow Operations**
   ```bash
   grep "duration_ms" logs/ai_diy_api_$(date +%Y%m%d).jsonl | jq 'select(.duration_ms > 1000)' | head -5
   ```

3. **Check Resource Usage**
   ```bash
   top -p $(pgrep -f "main_secure.py") | head -5
   ```

4. **Optimize or Scale**
   ```bash
   # If consistently slow, consider optimization or scaling
   ```

## Emergency Procedures

### Application Emergency Restart

```bash
#!/bin/bash
# emergency-restart.sh

echo "=== Emergency Application Restart ==="

# 1. Backup current state
cp logs/ai_diy_api_$(date +%Y%m%d).jsonl logs/ai_diy_api_$(date +%Y%m%d)_pre_restart.jsonl

# 2. Stop application
systemctl stop ai-diy || killall python

# 3. Wait for cleanup
sleep 5

# 4. Start application
systemctl start ai-diy

# 5. Verify startup
sleep 10
if curl -f http://localhost:8000/health > /dev/null; then
    echo "✅ Application restarted successfully"
else
    echo "❌ Application restart failed"
    exit 1
fi

echo "=== Emergency restart complete ==="
```

### Data Recovery

#### From Backup
```bash
# 1. Stop application
systemctl stop ai-diy

# 2. Restore data from backup
tar -xzf ai-diy-backup-20250107.tar.gz

# 3. Verify data integrity
python development/src/validate_data.py

# 4. Restart application
systemctl start ai-diy

# 5. Verify functionality
curl http://localhost:8000/health
```

#### From Export
```bash
# 1. Import data from export file
python development/src/import_data.py ai-diy-export-20250107.json

# 2. Verify import success
python development/src/validate_data.py

# 3. Restart application
systemctl restart ai-diy
```

## Compliance and Audit

### Log Retention

- **Application Logs**: 30 days
- **Security Logs**: 90 days
- **Audit Logs**: 1 year
- **Backup Logs**: 7 days compressed

### Compliance Checks

#### GDPR Compliance (if applicable)
```bash
# Check for personal data in logs
grep -r "email\|phone\|address" logs/ || echo "No personal data found"

# Verify data encryption (if applicable)
# Check that sensitive data is properly encrypted
```

#### Security Compliance
```bash
# Verify security headers
curl -I http://localhost:8000/ | grep -E "(X-Frame-Options|X-Content-Type-Options|Strict-Transport-Security)"

# Check rate limiting
for i in {1..110}; do
    curl -s http://localhost:8000/api/env > /dev/null
done

# Should see rate limiting in effect after ~100 requests
```

## Support Contacts

### Development Team
- **Primary Contact**: [Your Name/Team]
- **Email**: [your-email@company.com]
- **Slack/Teams**: [#ai-diy-support]
- **On-call**: [on-call-schedule-link]

### Escalation Procedures

1. **Level 1**: Check this runbook and logs
2. **Level 2**: Contact development team
3. **Level 3**: Escalate to infrastructure team
4. **Level 4**: Contact vendor support (if applicable)

## Document Maintenance

### Review Schedule

- **Monthly**: Review and update operational procedures
- **Quarterly**: Update with new features and improvements
- **Annually**: Complete review and testing of all procedures

### Change Management

- **Documentation Changes**: Review by operations team before publishing
- **Procedure Changes**: Test in staging environment before production
- **Emergency Changes**: Document after implementation for future reference

---

## Quick Reference

### Essential Commands

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/api/security/status

# Log monitoring
tail -f logs/ai_diy_api_$(date +%Y%m%d).jsonl

# Application control
systemctl status ai-diy    # Status
systemctl restart ai-diy   # Restart
systemctl stop ai-diy      # Stop

# Configuration validation
python development/validate_config.py

# Run tests
python development/tests/test_integration.py
```

### Emergency Contacts

- **Primary**: [Phone/Email]
- **Backup**: [Phone/Email]
- **Infrastructure**: [Phone/Email]

### Critical Metrics Thresholds

- **Response Time**: > 2000ms (warning), > 5000ms (critical)
- **Error Rate**: > 1% (warning), > 5% (critical)
- **Memory Usage**: > 80% (warning), > 95% (critical)
- **Rate Limit Violations**: > 10/hour (warning), > 50/hour (critical)
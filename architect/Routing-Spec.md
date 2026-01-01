# AI-DIY Routing Architecture Specification

## Overview

This document defines the complete routing architecture for AI-DIY generated applications, covering local development, Railway deployment, Caddy proxy configuration, and sprint-by-sprint implementation guidelines.

## Problem Statement

The AI-DIY system generates applications that must work in two distinct environments:
1. **Local Development**: Direct access to `localhost:3000`
2. **Railway Deployment**: Behind Caddy proxy at `/yourapp/` prefix

Each environment requires different URL patterns, creating a routing complexity that must be handled systematically.

## Core Architecture

### Environment Detection

Applications must automatically detect their environment and adjust routing accordingly:

```javascript
// Environment Detection Logic
const isRailway = process.env.RAILWAY_ENVIRONMENT === 'production' || 
                 process.env.RAILWAY_PID !== undefined;
const apiPrefix = isRailway ? '/yourapp' : '';
const basePath = isRailway ? '/yourapp' : '';
```

### URL Pattern Rules

| Component | Local Development | Railway Deployment | Implementation |
|-----------|-------------------|-------------------|----------------|
| **API Endpoints** | `/api/auth/login` | `/yourapp/api/auth/login` | `fetch(\`\${apiPrefix}/api/auth/login\`)` |
| **Navigation Links** | `dashboard` | `dashboard` | `href="dashboard"` (relative) |
| **Form Actions** | `api/auth/login` | `api/auth/login` | `action="api/auth/login"` (relative) |
| **Server Redirects** | `/dashboard` | `/dashboard` | `res.redirect('/dashboard')` (absolute) |
| **Static Assets** | `css/styles.css` | `css/styles.css` | `href="css/styles.css"` (relative) |
| **Client Redirects** | `dashboard` | `dashboard` | `window.location.href = 'dashboard'` |

## Implementation Strategy

### 1. Server-Side Configuration

#### Express.js Setup
```javascript
// server.js
const express = require('express');
const path = require('path');

const app = express();

// Environment detection
const isRailway = process.env.RAILWAY_ENVIRONMENT === 'production' || 
                 process.env.RAILWAY_PID !== undefined;
const apiPrefix = isRailway ? '/yourapp' : '';

// Middleware to inject API prefix into templates
app.use((req, res, next) => {
  res.locals.apiPrefix = apiPrefix;
  res.locals.isRailway = isRailway;
  next();
});

// Static file serving
app.use(express.static('public'));

// API routes
app.use('/api/auth', require('./routes/auth'));
app.use('/api/employees', require('./routes/employees'));
app.use('/api/leaves', require('./routes/leaves'));

// Page routes
app.get('/login', (req, res) => res.sendFile(path.join(__dirname, 'public', 'login.html')));
app.get('/dashboard', (req, res) => res.sendFile(path.join(__dirname, 'public', 'dashboard.html')));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Environment: ${isRailway ? 'Railway' : 'Local'}`);
  console.log(`API Prefix: ${apiPrefix}`);
});
```

#### Session Configuration
```javascript
// Session middleware
app.use(session({
  secret: process.env.SESSION_SECRET || 'keyboard cat',
  resave: false,
  saveUninitialized: false,
  cookie: {
    maxAge: 1800000, // 30 minutes
    secure: isRailway, // HTTPS on Railway
    sameSite: 'lax'
  }
}));
```

### 2. Frontend JavaScript Template

#### Template Injection Pattern
```html
<!-- In HTML templates -->
<script>
  // Injected by server
  const API_PREFIX = '{{apiPrefix}}';
  const IS_RAILWAY = {{isRailway}};
  
  // API helper function
  function apiCall(endpoint, options = {}) {
    return fetch(`${API_PREFIX}${endpoint}`, {
      ...options,
      credentials: 'include'
    });
  }
  
  // Usage examples
  async function login(email, password) {
    const response = await apiCall('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    return response.json();
  }
  
  async function checkSession() {
    const response = await apiCall('/api/auth/check-session');
    const data = await response.json();
    if (!data.success) {
      window.location.href = 'login';
    }
  }
</script>
```

#### Navigation Pattern
```javascript
// Navigation remains relative
function navigateTo(page) {
  window.location.href = page; // e.g., 'dashboard', 'employees', 'leaves'
}

// Form submissions use relative actions
// <form action="api/auth/login" method="POST">
```

### 3. Caddy Proxy Configuration

#### Railway Caddyfile
```caddyfile
# Railway Caddy Configuration
ai-diy-dev-production.up.railway.app {
    # Handle API routes with proxy
    handle /yourapp/api/* {
        reverse_proxy localhost:3000
    }
    
    # Handle static files and pages
    handle /yourapp/* {
        reverse_proxy localhost:3000
    }
    
    # Root redirect to app
    handle /* {
        redir /yourapp/ 302
    }
    
    # Security headers
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        X-XSS-Protection "1; mode=block"
        Referrer-Policy strict-origin-when-cross-origin
    }
    
    # Session cookie handling
    header Set-Cookie {
        "Path=/yourapp; SameSite=lax; Secure; HttpOnly"
    }
}
```

#### Local Development (No Caddy)
```bash
# Local development runs directly on localhost:3000
# No proxy, no URL rewriting
npm start
# Access: http://localhost:3000
```

## Sprint-by-Sprint Implementation

### Sprint 1: Foundation
**Stories**: NFR-001, US-001, US-999

**Implementation Requirements**:
1. **NFR-001 (Local Setup)**:
   - Basic Express server with environment detection
   - Database seeding with admin user
   - Static file serving
   - Session middleware

2. **US-001 (Authentication)**:
   - Login/logout endpoints
   - Session management
   - API prefix injection in login.html

3. **US-999 (Dashboard)**:
   - Dashboard with navigation
   - Session check with API prefix
   - Relative navigation links

**Code Generation Rules**:
- All API calls use `apiCall()` helper with prefix
- Navigation uses relative paths
- Form actions use relative paths
- Server redirects use absolute paths

### Sprint 2: Core Features
**Stories**: US-002, US-003, US-004

**Implementation Requirements**:
1. **Employee Directory (US-002)**:
   - Employee listing with search
   - API calls use `apiCall()` helper
   - Navigation links remain relative

2. **Add/Edit Employees (US-003)**:
   - Forms use relative actions
   - API calls use `apiCall()` helper
   - Redirects use server-side absolute paths

3. **Leave Management (US-004)**:
   - Leave request forms
   - API endpoints with proper prefix handling
   - Dashboard integration

**Code Generation Rules**:
- New API endpoints automatically get prefix support
- All new forms follow relative action pattern
- Navigation updates maintain relative structure

### Sprint 3: Advanced Features
**Stories**: US-005, US-006, US-007

**Implementation Requirements**:
1. **Document Management (US-005)**:
   - File upload/download with proper routing
   - API calls with prefix support
   - Static file serving considerations

2. **Calendar Integration (US-006)**:
   - Calendar API endpoints
   - Client-side routing for calendar views
   - Session-aware access control

3. **Reporting (US-007)**:
   - Report generation endpoints
   - Data export with proper routing
   - Authentication integration

## System Prompt Updates

### Architect (Mike) Prompt Updates

```text
ROUTING ARCHITECTURE (ENVIRONMENT-AWARE):

The application must work in TWO environments:
1. Local Development: localhost:3000 (no prefix)
2. Railway Deployment: /yourapp/ prefix via Caddy proxy

IMPLEMENTATION PATTERN:
- Server detects environment: process.env.RAILWAY_ENVIRONMENT
- API calls use server-injected prefix: {{apiPrefix}}
- Navigation uses relative paths: href="dashboard"
- Forms use relative actions: action="api/auth/login"
- Server redirects use absolute paths: res.redirect('/dashboard')

CODE GENERATION RULES:
✅ All API calls MUST use apiCall() helper with prefix injection
✅ Navigation links MUST be relative (no leading /)
✅ Form actions MUST be relative (no leading /)
✅ Server redirects MUST be absolute (with leading /)
✅ Static assets MUST be relative (no leading /)

ENVIRONMENT DETECTION:
const isRailway = process.env.RAILWAY_ENVIRONMENT === 'production';
const apiPrefix = isRailway ? '/yourapp' : '';

TEMPLATE INJECTION:
app.use((req, res, next) => {
  res.locals.apiPrefix = isRailway ? '/yourapp' : '';
  next();
});

FRONTEND PATTERN:
<script>
const API_PREFIX = '{{apiPrefix}}';
function apiCall(endpoint, options) {
  return fetch(`${API_PREFIX}${endpoint}`, options);
}
</script>
```

### Developer (Alex) Prompt Updates

```text
ROUTING IMPLEMENTATION (ENVIRONMENT-AWARE):

ENVIRONMENTS:
- Local: localhost:3000 → API calls use ''
- Railway: /yourapp/ → API calls use '/yourapp'

IMPLEMENTATION REQUIREMENTS:
1. Server MUST detect environment and inject apiPrefix
2. All API calls MUST use apiCall() helper with prefix
3. Navigation MUST use relative paths
4. Forms MUST use relative actions
5. Server redirects MUST use absolute paths

CODE PATTERNS:
✅ apiCall('/api/auth/login') → fetch('/yourapp/api/auth/login') on Railway
✅ href="dashboard" → /yourapp/dashboard on Railway
✅ action="api/auth/login" → /yourapp/api/auth/login on Railway
✅ res.redirect('/dashboard') → /yourapp/dashboard on Railway

❌ NEVER hardcode '/yourapp/' in frontend code
❌ NEVER use absolute paths for navigation
❌ NEVER use relative paths for server redirects

TESTING REQUIREMENTS:
- Test locally: localhost:3000
- Test on Railway: /yourapp/ prefix
- Verify API calls work in both environments
- Verify navigation works in both environments
```

### PM (Sarah) Prompt Updates

```text
ROUTING ACCEPTANCE CRITERIA:

ENVIRONMENT COMPATIBILITY:
✅ Application works on localhost:3000
✅ Application works on Railway with /yourapp/ prefix
✅ All API calls function in both environments
✅ All navigation functions in both environments
✅ Session management works in both environments

TESTING SCENARIOS:
1. Local Development:
   - Access: http://localhost:3000
   - Login: POST to /api/auth/login
   - Navigate: href="dashboard" → /dashboard
   
2. Railway Deployment:
   - Access: https://app.railway.app/yourapp/
   - Login: POST to /yourapp/api/auth/login
   - Navigate: href="dashboard" → /yourapp/dashboard

DEFECT CRITERIA:
❌ API calls fail on Railway (404 errors)
❌ Navigation breaks on Railway (wrong URLs)
❌ Sessions don't persist on Railway
❌ Static assets don't load on Railway
❌ Login redirects are incorrect
```

## Testing Strategy

### 1. Environment Testing

#### Local Tests
```bash
# Start local server
npm start

# Test endpoints
curl http://localhost:3000/api/auth/login
curl http://localhost:3000/dashboard
```

#### Railway Tests
```bash
# Test Railway deployment
curl https://app.railway.app/yourapp/api/auth/login
curl https://app.railway.app/yourapp/dashboard
```

### 2. Automated Testing

#### Test Suite Structure
```javascript
// tests/routing.test.js
describe('Environment-Aware Routing', () => {
  describe('Local Development', () => {
    test('API calls work without prefix', async () => {
      const response = await fetch('http://localhost:3000/api/auth/login');
      expect(response.ok).toBe(true);
    });
  });
  
  describe('Railway Deployment', () => {
    test('API calls work with prefix', async () => {
      const response = await fetch('https://app.railway.app/yourapp/api/auth/login');
      expect(response.ok).toBe(true);
    });
  });
});
```

### 3. Manual Testing Checklist

#### Pre-Deployment Checklist
- [ ] Application starts locally on port 3000
- [ ] Login works locally
- [ ] Navigation works locally
- [ ] Sessions persist locally
- [ ] API calls work locally

#### Post-Deployment Checklist
- [ ] Application accessible on Railway
- [ ] Login works on Railway
- [ ] Navigation works on Railway
- [ ] Sessions persist on Railway
- [ ] API calls work on Railway
- [ ] No 404 errors on Railway
- [ ] No redirect loops on Railway

## Deployment Guidelines

### 1. Railway Deployment

#### Environment Variables
```bash
RAILWAY_ENVIRONMENT=production
SESSION_SECRET=your-secret-key
NODE_ENV=production
PORT=3000
```

#### Build Process
```bash
# Install dependencies
npm install

# Start application
npm start
```

#### Health Checks
```javascript
// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    environment: process.env.RAILWAY_ENVIRONMENT || 'local',
    apiPrefix: res.locals.apiPrefix 
  });
});
```

### 2. Local Development

#### Setup Commands
```bash
# Clone repository
git clone <repo>
cd <project>

# Install dependencies
npm install

# Start development server
npm start

# Access application
open http://localhost:3000
```

#### Development Workflow
```bash
# Run tests
npm test

# Start with debug mode
DEBUG=* npm start

# Reset database
rm data.sqlite && npm start
```

## Troubleshooting Guide

### Common Issues

#### 1. API Calls Fail on Railway
**Symptoms**: 404 errors, login failures
**Causes**: Missing `/yourapp/` prefix in API calls
**Solution**: Ensure `apiCall()` helper is used with proper prefix injection

#### 2. Navigation Breaks on Railway
**Symptoms**: Wrong page redirects, broken links
**Causes**: Absolute paths in navigation
**Solution**: Use relative paths for all navigation

#### 3. Sessions Don't Persist
**Symptoms**: Constant login redirects
**Causes**: Cookie path issues, session configuration
**Solution**: Configure proper cookie path and session settings

#### 4. Static Assets Don't Load
**Symptoms**: Broken CSS/JS, missing images
**Causes**: Incorrect asset paths
**Solution**: Use relative paths for static assets

### Debugging Tools

#### Environment Detection
```javascript
console.log('Environment:', process.env.RAILWAY_ENVIRONMENT);
console.log('API Prefix:', res.locals.apiPrefix);
console.log('Request URL:', req.url);
```

#### Network Monitoring
```bash
# Monitor API calls
curl -v https://app.railway.app/yourapp/api/auth/login

# Check headers
curl -I https://app.railway.app/yourapp/dashboard
```

## Future Considerations

### 1. Multi-Environment Support
- Staging environment configuration
- Development vs production settings
- Environment-specific database connections

### 2. Advanced Routing
- Route guards and middleware
- Dynamic route generation
- API versioning support

### 3. Performance Optimization
- Route caching strategies
- Static asset optimization
- API response caching

### 4. Security Enhancements
- CSRF protection
- Rate limiting
- API authentication tokens

## Conclusion

This routing architecture provides a robust foundation for AI-DIY generated applications that work seamlessly across local development and Railway deployment environments. By following the environment-aware patterns and systematic implementation guidelines, we ensure consistent behavior and maintainable code across all sprint iterations.

The key success factors are:
1. **Environment detection** for automatic adaptation
2. **Consistent patterns** for predictable behavior
3. **Comprehensive testing** across environments
4. **Clear documentation** for team alignment
5. **Systematic implementation** in sprint execution

This specification serves as the definitive guide for all routing-related decisions in the AI-DIY system.

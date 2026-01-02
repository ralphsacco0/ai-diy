# AI-DIY Routing Architecture Implementation Guide

## Overview

This document provides complete specifications for implementing consistent routing patterns in AI-DIY generated applications that work seamlessly across both local Mac development and Railway deployment environments.

## Problem Statement

Generated applications must work in two distinct environments:
- **Local Mac**: Direct access at `http://localhost:3000`
- **Railway**: Behind Caddy proxy at `https://app.railway.app/yourapp/`

Each environment requires different URL resolution patterns, creating routing complexity that must be handled systematically through consistent coding patterns.

## Architecture Overview

```
Internet → Caddy (Railway) → Node.js App (Port 3000)
```

### Traffic Flow

1. **Main Application** (`/`, `/api/*`, `/static/*`) → FastAPI (Port 8001)
2. **Generated Apps** (`/yourapp/*`) → Caddy → Node.js App (Port 3000)
3. **Caddy strips `/yourapp/` prefix** before forwarding to Node.js

## Core Routing Principles

### The Golden Rule

**Client-side calls use RELATIVE paths, Server-side routes use ABSOLUTE paths**

This single principle ensures compatibility across both environments without environment detection or conditional code.

### Why This Works

**Caddy Proxy Behavior:**
- Browser requests: `fetch('login')` from `/yourapp/login` → `/yourapp/login` → Caddy strips `/yourapp/` → Node.js receives `/login` ✅
- Node.js responds: `res.redirect('/dashboard')` → Caddy rewrites to `/yourapp/dashboard` → Browser receives `/yourapp/dashboard`

**CRITICAL: API calls MUST be relative to go through Caddy proxy**
- `fetch('login')` → Through Caddy → Node.js ✅  
- `fetch('/api/auth/login')` → Bypasses Caddy → FastAPI → 404 ❌

## Complete Routing Specifications

### 1. API Calls (Client-side JavaScript)

**✅ CORRECT Pattern:**
```javascript
// Relative paths - go through Caddy proxy to Node.js
fetch('login')                     // For authentication
fetch('logout')                    // For logout  
fetch('check-session')             // For session validation
fetch('employees')                 // For data retrieval
fetch('employees/123')             // For specific resource
```

**❌ WRONG Patterns:**
```javascript
// Absolute paths - bypass Caddy and hit FastAPI (404 errors)
fetch('/api/auth/login')           // Goes to FastAPI → 404
fetch('/api/employees')            // Goes to FastAPI → 404
fetch('/api/auth/logout')          // Goes to FastAPI → 404
```

**Implementation Requirements:**
- Always include `credentials: 'include'` for authentication-related API calls
- Use `Content-Type: application/json` for JSON data
- Use `JSON.stringify()` for request bodies

**Example:**
```javascript
const response = await fetch('login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    credentials: 'include',
    body: JSON.stringify({ email, password })
});
```

### 2. Navigation Links (Client-side HTML)

**✅ CORRECT Pattern:**
```html
<!-- Relative paths - resolve relative to current URL -->
<a href="dashboard">Dashboard</a>
<a href="employees">Employee Directory</a>
<a href="leaves">Leave Requests</a>
<a href="documents">Documents</a>
<a href="login">Login</a>
```

**❌ WRONG Patterns:**
```html
<!-- Absolute paths - break on Railway -->
<a href="/dashboard">Dashboard</a>         <!-- Goes to wrong domain -->
<a href="/employees">Employees</a>        <!-- 404 on Railway -->
```

**Why Relative Works:**
- **Mac**: At `/employees` → `href="dashboard"` → `/dashboard` ✅
- **Railway**: At `/yourapp/employees` → `href="dashboard"` → `/yourapp/dashboard` ✅

### 3. Form Actions (Client-side HTML)

**✅ CORRECT Patterns:**

**Self-submitting forms (submit to same URL):**
```html
<form action="#" method="POST">     <!-- or action="." -->
    <input name="email" type="email">
    <input name="password" type="password">
    <button type="submit">Login</button>
</form>
```

**Forms submitting to authentication endpoints:**
```html
<!-- Forms submitting to authentication endpoints -->
<form action="login" method="POST">
    <input name="email" type="email">
    <input name="password" type="password">
    <button type="submit">Login</button>
</form>
```

**Forms submitting to API endpoints:**
```html
<form action="employees" method="POST">
    <input name="name" type="text">
    <input name="email" type="email">
    <button type="submit">Add Employee</button>
</form>
```

**WRONG Patterns:**
```html
<!-- Absolute paths bypass Caddy -->
<form action="/api/auth/login" method="POST">     <!-- Goes to FastAPI → 404 -->
<form action="/login" method="POST">              <!-- Goes to wrong domain -->
```

### 4. Form Data Encoding (Client-side JavaScript)

**CORRECT for Simple Forms (login, text fields):**
```javascript
const formData = new FormData(form);
await fetch('login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(Object.fromEntries(formData))
});
```

**✅ CORRECT for File Uploads:**
```javascript
const formData = new FormData(form);
await fetch('upload', {
    method: 'POST',
    credentials: 'include',
    body: formData  // multipart/form-data
});
```

**❌ WRONG for Simple Forms:**
```javascript
// Absolute paths bypass Caddy and hit FastAPI
await fetch('/api/login', {
    method: 'POST',
    body: formData  // WRONG - causes 404 on FastAPI
});
```

### 5. Server-side Routes (Node.js/Express)

**✅ CORRECT Pattern:**
```javascript
// Absolute paths - server-side routes
app.get('/login', (req, res) => { ... });
app.get('/dashboard', isAuthenticated, (req, res) => { ... });
app.get('/employees', isAuthenticated, (req, res) => { ... });

// Router mounting at ROOT (critical for API endpoints)
const authRouter = require('./routes/auth');
app.use('/', authRouter);  // Routes in auth.js become /login, /logout, /check-session
```

**Router Export Pattern:**
```javascript
// routes/auth.js
const express = require('express');
const router = express.Router();

router.post('/login', (req, res) => { ... });  // Becomes /login when mounted at root
router.post('/logout', (req, res) => { ... });  // Becomes /logout when mounted at root
router.get('/check-session', (req, res) => { ... });  // Becomes /check-session

module.exports = router;
```

### 6. Server-side Redirects (Node.js/Express)

** CORRECT Pattern:**
```javascript
// Absolute paths - Caddy handles rewriting
res.redirect('/dashboard');           // Becomes /yourapp/dashboard on Railway
res.redirect('/login');               // Becomes /yourapp/login on Railway
res.redirect('/employees');           // Becomes /yourapp/employees on Railway
```

** WRONG Patterns:**
```javascript
// Relative paths - break server-side routing
res.redirect('dashboard');            // Server-side confusion
res.redirect('../dashboard');         // Unpredictable behavior
```

### 7. Client-side Redirects (JavaScript)

** CORRECT Pattern:**
```javascript
// Relative paths - client-side navigation
window.location.href = 'dashboard';   // Resolves relative to current URL
window.location.href = 'login';       // Works in both environments
```

**❌ WRONG Patterns:**
```javascript
// Absolute paths - break on Railway
window.location.href = '/dashboard';  // Goes to wrong domain on Railway
```

### 8. Session Management

**✅ CRITICAL Configuration for Railway:**
```javascript
app.use(session({
    secret: process.env.SESSION_SECRET || 'dev-secret',
    resave: false,
    saveUninitialized: false,
    cookie: {
        maxAge: 30 * 60 * 1000,      // 30 minutes
        secure: false,                // REQUIRED for Railway proxy
        sameSite: 'lax'               // REQUIRED for Railway redirects
    }
}));
```

**Why These Settings:**
- `secure: false` - Backend is HTTP behind HTTPS proxy
- `sameSite: 'lax'` - Prevents cookies being blocked in redirects
- Without these settings, sessions don't persist on Railway

## Implementation Guide for AI-DIY

### 1. System Prompt Updates

**Add to SPRINT_EXECUTION_ARCHITECT_system_prompt.txt:**

```markdown
## ROUTING PATTERNS (CRITICAL FOR RAILWAY COMPATIBILITY)

### Client-side vs Server-side Path Rules

**CLIENT-SIDE (HTML/JavaScript) - Use RELATIVE paths:**
- Navigation links: <a href="dashboard">Dashboard</a>
- Form actions: <form action="api/auth/login" method="POST">
- API calls: fetch('/api/employees') (ABSOLUTE for API calls)
- Client redirects: window.location.href = 'dashboard'

**SERVER-SIDE (Express) - Use ABSOLUTE paths:**
- Routes: app.get('/dashboard', ...)
- Redirects: res.redirect('/dashboard')
- Router mounting: app.use('/api', apiRouter)

### Form Data Encoding Rules

**SIMPLE FORMS (login, text fields):**
- Specify: JSON.stringify(Object.fromEntries(formData)) with application/json
- Backend: express.json() and express.urlencoded({ extended: true })

**FILE UPLOADS:**
- Specify: body: formData (multipart/form-data)
- Backend: Requires multer middleware

### Session Configuration (MANDATORY)
- secure: false and sameSite: 'lax' required for Railway proxy compatibility
```

**Add to SPRINT_EXECUTION_DEVELOPER_system_prompt.txt:**

```markdown
## RAILWAY ROUTING IMPLEMENTATION

### Path Handling Rules
- API calls: Use absolute paths fetch('/api/employees')
- Navigation: Use relative paths href="dashboard"
- Forms: Use relative paths action="api/auth/login"
- Server redirects: Use absolute paths res.redirect('/dashboard')

### Session Configuration
app.use(session({
    secret: process.env.SESSION_SECRET || 'dev-secret',
    resave: false,
    saveUninitialized: false,
    cookie: {
        maxAge: 1800000,
        secure: false,        // REQUIRED for Railway
        sameSite: 'lax'       // REQUIRED for Railway
    }
}));

### Form Submission Pattern
const formData = new FormData(form);
await fetch('/api/endpoint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(Object.fromEntries(formData))
});
```

### 2. Code Generation Templates

**Login Form Template:**
```html
<form action="#" method="POST" id="login-form">
    <input name="email" type="email" required>
    <input name="password" type="password" required>
    <button type="submit">Login</button>
</form>

<script>
document.querySelector('form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(Object.fromEntries(formData))
        });
        
        const data = await response.json();
        if (data.success) {
            window.location.href = data.redirect || 'dashboard';
        } else {
            // Show error
        }
    } catch (err) {
        // Show error
    }
});
</script>
```

**Navigation Template:**
```html
<nav>
    <a href="dashboard">Dashboard</a>
    <a href="employees">Employees</a>
    <a href="leaves">Leaves</a>
    <a href="documents">Documents</a>
    <form action="/api/auth/logout" method="POST" style="display: inline;">
        <button type="submit">Logout</button>
    </form>
</nav>
```

**Session Check Template:**
```javascript
window.addEventListener('load', async () => {
    try {
        const response = await fetch('/api/auth/check-session', {
            credentials: 'include'
        });
        const data = await response.json();
        if (!data.authenticated) {
            window.location.href = 'login';
        }
    } catch (err) {
        window.location.href = 'login';
    }
});
```

### 3. Validation Rules

**Add to sprint validation:**

```python
def validate_routing_patterns(generated_code):
    """Validate that generated code follows routing patterns."""
    
    # Check HTML files for correct patterns
    html_files = find_files('*.html')
    for file in html_files:
        content = read_file(file)
        
        # Should have relative navigation links
        assert 'href="/' not in content, "Absolute href found - should be relative"
        
        # Should have correct form actions
        assert 'action="/login' not in content, "Absolute form action found"
        
        # Should have correct API calls
        if 'fetch(' in content:
            assert "fetch('" in content and not "fetch('/" in content, "API calls should be relative"
            
        # Should have credentials in auth calls
        if 'fetch(\'login' in content or 'fetch(\'logout' in content:
            assert 'credentials: \'include\'' in content, "Auth calls need credentials"
    
    # Check server files for correct patterns
    server_files = find_files('server.js', 'routes/*.js')
    for file in server_files:
        content = read_file(file)
        
        # Should have absolute routes
        assert 'app.get(\'/' in content or 'router.' in content, "Routes should be absolute"
        
        # Should have absolute redirects
        assert 'res.redirect(\'/' in content, "Redirects should be absolute"
        
        # Should have correct session config
        if 'session(' in content:
            assert 'secure: false' in content, "Session needs secure: false for Railway"
            assert 'sameSite: \'lax\'' in content, "Session needs sameSite: 'lax'"
```

### 4. Testing Strategy

**Unit Tests for Routing:**
```javascript
// Test API calls work from different page depths
test('API call from nested page', async () => {
    // Simulate being at /yourapp/employees/departments
    const response = await fetch('employees');
    assert(response.ok);
});

// Test navigation links work correctly
test('Navigation link resolution', () => {
    // At /yourapp/employees, href="dashboard" should go to /yourapp/dashboard
    const currentPath = '/yourapp/employees';
    const linkHref = 'dashboard';
    const resolved = new URL(linkHref, currentPath).href;
    assert(resolved.endsWith('/yourapp/dashboard'));
});
```

**Integration Tests:**
```javascript
// Test complete login flow
test('Complete login flow', async () => {
    // 1. Get login page
    const loginPage = await app.request('/login');
    assert(loginPage.ok);
    
    // 2. Submit login form
    const response = await app.request('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@test.com', password: 'test' })
    });
    assert(response.ok);
    
    // 3. Follow redirect to dashboard
    const dashboard = await app.request('/dashboard');
    assert(dashboard.ok);
});
```

## Deployment Considerations

### 1. Caddy Configuration

**Required Caddyfile:**
```caddy
{
    email your-email@example.com
}

# Handle generated app requests
handle /yourapp/* {
    reverse_proxy localhost:3000
    
    # Critical: Rewrite Location headers to prevent double-prefixing
    header_down Location "^/((?!yourapp/).*)" "/yourapp/$1"
}

# Handle main AI-DIY application
reverse_proxy localhost:8001
```

### 2. Environment Variables

**Railway Environment:**
- `PORT=3000` (for generated app)
- `SESSION_SECRET` (for session encryption)
- `NODE_ENV=production` (optional)

### 3. File Structure

**Required structure for Railway:**
```
/app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp/
├── src/
│   ├── server.js
│   ├── db.js
│   └── routes/
│       └── auth.js
├── public/
│   ├── login.html
│   ├── dashboard.html
│   ├── employees.html
│   ├── leaves.html
│   └── documents.html
├── package.json
└── .env
```

## Troubleshooting Guide

### Common Issues and Solutions

1. **"Invalid credentials" despite correct login**
   - Check form data encoding (should be JSON, not FormData)
   - Verify credentials: 'include' in fetch calls
   - Check session configuration (secure: false, sameSite: 'lax')

2. **404 errors on API calls**
   - Check if API calls use relative paths: `fetch('login')` not `fetch('/api/auth/login')`
   - Verify auth router is mounted at root: `app.use('/', authRouter)`
   - Check if generated app is running on port 3000

3. **Redirect loops**
   - Check session cookie settings
   - Verify Caddy Location header rewriting
   - Check for conflicting middleware

4. **Navigation links go to wrong pages**
   - Ensure links use relative paths: `href="dashboard"`
   - Check for absolute paths in HTML

5. **Pages load then redirect to 404**
   - Check session check API calls use relative paths: `fetch('check-session')`
   - Verify session check includes credentials: 'include'

### Debug Commands

**Railway Debugging:**
```bash
# Check if app is running
railway ssh "netstat -tlnp | grep :3000"

# Check generated files
railway ssh "ls -la /app/development/src/static/appdocs/execution-sandbox/client-projects/yourapp/"

# Test API endpoints
curl -X POST https://app.railway.app/yourapp/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@test.com", "password": "test"}'

# Check session
curl -b cookies.txt https://app.railway.app/yourapp/check-session
```

## Migration Guide

### Converting Existing Code

1. **HTML Files:**
   - Replace `href="/page"` with `href="page"`
   - Replace `action="/endpoint"` with `action="#"` or `action="endpoint"`
   - Add `credentials: 'include'` to auth fetch calls

2. **JavaScript Files:**
   - Replace `fetch('/api/auth/login')` with `fetch('login')` (use relative for API)
   - Replace `fetch('/api/auth/check-session')` with `fetch('check-session')`
   - Replace `window.location.href = '/page'` with `window.location.href = 'page'`

3. **Server Files:**
   - Mount auth router at root: `app.use('/', authRouter)` not `app.use('/api/auth', authRouter)`
   - Add session configuration with `secure: false, sameSite: 'lax'`
   - Ensure all routes use absolute paths

## Summary

This routing architecture provides:
- **Consistent behavior** across Mac and Railway environments
- **No environment detection** needed in generated code
- **Simple patterns** that are easy to follow and implement
- **Full compatibility** with Caddy proxy configuration
- **Maintainable code** that works without conditional logic

The key insight is that **client-side uses relative paths, server-side uses absolute paths**, and Caddy handles the translation between environments automatically.

By implementing these patterns consistently in AI-DIY generated applications, we ensure seamless deployment and operation across both development and production environments.

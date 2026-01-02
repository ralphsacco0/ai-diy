# AI-DIY Routing Architecture - PROVEN Implementation Guide

## Overview

AI-DIY generates "small web apps" that work in two environments **without any environment detection**:

- **Local**: `http://localhost:3000`
- **Railway**: `https://<railway-host>/yourapp/` (behind Caddy prefix proxy)

This document defines the routing patterns that are **PROVEN TO WORK** based on the working POC (`aayourapp_gold_sample_readonly`).

---

## Architecture Overview

### Traffic Flow

- **Main AI-DIY platform**
  - Root (`/`, `/api/*`, etc.) → **FastAPI** (port 8001)
- **Generated app**
  - `/yourapp/*` → **Caddy** → **Node/Express** (internal port 3000)
  - Caddy **strips `/yourapp`** before forwarding to Node
  - Caddy may rewrite **Location** response headers to re-add `/yourapp`

**Key consequence:** any browser request that does **NOT** include `/yourapp/...` will be handled by the main platform (FastAPI), not the generated app.

---

## PROVEN Rules (Based on Working POC)

### Rule 0: No environment detection
Generated app code must NOT attempt to detect Railway vs local.
No `apiPrefix`, no `BASE_PATH`, no `window.location.pathname` prefix hacks, no templated prefix injection.

### Rule 1: Never use `<base>` tags
No `<base href=...>` anywhere.

### Rule 2: Server-side vs Client-side path styles (PROVEN PATTERN)

**Server-side (Express routes + redirects):**
- Always **absolute** paths starting with `/`
- Example: `res.redirect('/dashboard')`

**Client-side (HTML and browser JS):**
- Always **relative** paths with **NO leading `/`**
- Examples: `href="dashboard"`, `fetch('login')`

### Rule 3: Simple auth endpoints (PROVEN WORKING)

**Authentication endpoints work WITHOUT `/api/` namespace:**
- **Server**: `router.post('/login')` (mounted at `/`) → Final route: `/login`
- **Client**: `fetch('login')` (relative) → Works correctly

**Data endpoints SHOULD use `/api/` namespace:**
- **Server**: `router.get('/api/employees')` (mounted at `/api`) → Final route: `/api/employees`
- **Client**: `fetch('api/employees')` (relative) → Prevents collisions with page routes

### Rule 4: Flat pages only (no nested GET pages)
Generated app **pages** must be single-segment routes only:

✅ `/login`, `/dashboard`, `/employees`  
❌ `/employees/123`, `/employees/123/edit`, `/dashboard/settings`

If you need "details", do it as:
- query string (`/employees?id=123`), and/or
- POST action → server redirect back to a flat page, and/or
- data fetched from `api/...`

### Rule 5: No trailing slashes on pages
Canonical page URLs must not end with `/` (except root if you ever use it).
This avoids browser-relative resolution changing based on trailing slash.

✅ `/employees`  
❌ `/employees/`

---

## PROVEN Endpoint Map (Generated App)

### Pages (HTML)
- `GET /login` → login page
- `GET /dashboard` → dashboard page
- `GET /employees` → employees page

### Authentication (Simple Pattern - PROVEN)
- `POST /login` ✅ (NOT `/api/auth/login`)
- `POST /logout` ✅ (NOT `/api/auth/logout`)
- `GET  /check-session` ✅ (NOT `/api/auth/check-session`)

### Data APIs (Namespaced Pattern)
- `GET  /api/employees`
- `POST /api/employees`
- (etc — all DATA endpoints stay under `/api/...`)

---

## PROVEN Client-Side Patterns (Browser)

### Navigation (HTML)
Always relative, no leading slash:

```html
<a href="dashboard">Dashboard</a>
<a href="employees">Employees</a>
<a href="login">Login</a>
```

### Static assets (HTML)
Always relative:

```html
<link rel="stylesheet" href="css/styles.css">
<script src="login.js"></script>
```

### Fetch (browser JS)

**Authentication endpoints (PROVEN PATTERN):**

```javascript
await fetch('login', { credentials: 'include' });        // ✅ PROVEN
await fetch('logout', { method: 'POST', credentials: 'include' });  // ✅ PROVEN
await fetch('check-session', { credentials: 'include' }); // ✅ PROVEN
```

**Data endpoints (Namespaced):**

```javascript
await fetch('api/employees', { credentials: 'include' });  // ✅ Namespaced
```

**Never do this (bypasses /yourapp and hits FastAPI):**

```javascript
fetch('/login')           // ❌ Absolute - breaks proxy
fetch('/api/employees')   // ❌ Absolute - breaks proxy
```

### Form actions

**Self-submitting forms (PROVEN):**

```html
<form id="loginForm" action="#" method="post">
  ...
</form>
```

**JavaScript handling (PROVEN):**

```javascript
const formData = new FormData(form);
const data = Object.fromEntries(formData);
await fetch('login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify(data)
});
```

---

## PROVEN Server-Side Patterns (Express)

### Route definitions

**Authentication routes (PROVEN PATTERN):**

```javascript
// In server.js - mount auth router at root
app.use('/', authRouter);

// In routes/auth.js - simple routes
router.post('/login', ...);        // Final route: /login
router.post('/logout', ...);       // Final route: /logout
router.get('/check-session', ...); // Final route: /check-session
```

**Data routes (Namespaced):**

```javascript
// In server.js - mount data router at /api
app.use('/api', dataRouter);

// In routes/data.js - namespaced routes
router.get('/employees', ...);     // Final route: /api/employees
router.post('/employees', ...);    // Final route: /api/employees
```

### Absolute redirects (mandatory)

Always redirect with a leading /:

```javascript
return res.redirect('/dashboard'); // ✅ PROVEN
```

Never:

```javascript
res.redirect('dashboard'); // ❌ Wrong
```

---

## PROVEN Patterns from Working POC

### 1. Package.json (CommonJS)

```json
{
  "dependencies": {
    "express": "*",
    "sqlite3": "*",
    "bcryptjs": "*",
    "express-session": "*"
  }
}
```

**NO**: `"type": "module"` - Use CommonJS only

### 2. Server.js structure

```javascript
const express = require('express');
const session = require('express-session');
const path = require('path');
const { createDb, initDb } = require('./db');
const authRouter = require('./routes/auth');

const app = express();

// Middleware order matters
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
  secret: process.env.SESSION_SECRET || 'secret-key',
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 1800000, secure: false, sameSite: 'lax' }
}));
app.use(express.static(path.join(__dirname, '..', 'public')));

// Route mounting
app.use("/", authRouter);  // Auth at root
app.use("/api", apiRouter); // Data at /api

// Page routes
app.get('/login', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'login.html'));
});

// Database sharing
async function startServer() {
  const db = createDb();
  await initDb(db);
  app.locals.db = db;  // Share with all routes
  const port = process.env.PORT || 3000;
  app.listen(port, () => console.log(`Server on port ${port}`));
}
```

### 3. Authentication routes (PROVEN)

```javascript
// routes/auth.js
const express = require('express');
const router = express.Router();

router.post('/login', async (req, res) => {
  const db = req.app.locals.db;  // Use shared DB
  const { email, password } = req.body;
  
  // Validation logic...
  req.session.userId = user.id;
  res.json({ success: true, redirect: 'dashboard' });  // Relative redirect
});

router.post('/logout', (req, res) => {
  req.session.destroy((err) => {
    res.clearCookie('connect.sid');
    res.json({ success: true, redirect: 'login' });  // Relative redirect
  });
});

router.get('/check-session', (req, res) => {
  res.json({ 
    authenticated: !!(req.session && req.session.userId),
    user: req.session && req.session.user 
  });
});
```

---

## Hybrid Approach: Why It Works

**Authentication endpoints don't need `/api/` namespace because:**
- They're simple, universal operations
- No risk of collision with page routes
- Simpler client code: `fetch('login')` vs `fetch('api/auth/login')`
- Proven to work in production

**Data endpoints benefit from `/api/` namespace because:**
- Prevents collisions: `/employees` (page) vs `/api/employees` (data)
- Clear separation of concerns
- Easier to understand and maintain

---

## Caddy Configuration (Railway Prefix Proxy)

### Caddy Goals
1. Route `/yourapp/*` to the generated app (Node)
2. Strip `/yourapp` before forwarding upstream
3. Rewrite `Location: /login` → `Location: /yourapp/login`
4. Prevent double-prefix loops (`/yourapp/yourapp/...`)

### Canonical Caddy Snippet (Guarded Location Rewrite)

```caddy
:{$PORT} {

  handle_path /yourapp/* {
    reverse_proxy 127.0.0.1:3000

    # Rewrite absolute Location headers (/login) into prefixed ones (/yourapp/login)
    # but DO NOT rewrite if it is already /yourapp/...
    header_down Location "^/(?!yourapp/)(.*)$" "/yourapp/$1"
  }

  # everything else continues to the main platform (FastAPI, etc.)
  handle {
    reverse_proxy 127.0.0.1:8001
  }
}
```

### Critical Rule for Node Redirects

Node/Express must **NEVER** emit redirects containing `/yourapp`.
Node should only emit: `/login`, `/dashboard`, etc.
Caddy is responsible for prefixing on Railway.

---

## Environment Variables (Railway + Local)

### Ports
- **Caddy** listens on Railway-provided `$PORT` (public)
- **Node/Express** listens on 3000 (internal)
- **FastAPI** listens on 8001 (internal)

**Important**: Do not set `PORT=3000` for the generated app; reserve `$PORT` for Caddy.
If you want configurability, use `APP_PORT=3000` for Node, not `PORT`.

### Required
- `SESSION_SECRET` (recommended for non-toy apps)

---

## Troubleshooting (Based on Real Issues)

### Symptom: "works on localhost, 404 on Railway"

Check these in order:
1. **Absolute fetch calls**: Any `fetch('/something')` will hit FastAPI, not your app
2. **Missing credentials**: `credentials: 'include'` required for sessions
3. **Form encoding**: Use `JSON.stringify(Object.fromEntries(formData))`, not `formData`
4. **Session config**: Must have `secure: false, sameSite: 'lax'` for proxy

### Quick checks
```bash
# In browser devtools Network:
# All requests must start with /yourapp/... when deployed

# Grep generated app:
grep -r "href=/" public/     # ❌ Should find none
grep -r "fetch('/" public/   # ❌ Should find none
grep -r "action=/" public/   # ❌ Should find none
```

### Curl smoke tests (Railway)
```bash
# Page:
curl -I https://<host>/yourapp/login

# API:
curl -I https://<host>/yourapp/check-session
```

---

## Migration Guide (If Coming from Old Spec)

**If you have code using `/api/auth/login`:**
1. Change server routes: Move from `/api/auth` router to `/` router
2. Change client calls: `fetch('api/auth/login')` → `fetch('login')`
3. Update documentation to reflect hybrid approach

**Benefits:**
- Simpler authentication code
- Proven to work in production
- Less verbose client-side JavaScript
- Maintains data namespace separation

---

This spec is **PROVEN** by the working POC and should be treated as the canonical implementation guide.

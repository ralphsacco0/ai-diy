# AI-DIY Routing Architecture Implementation Guide (Canonical)

## Overview

AI-DIY generates “small web apps” that must work in two environments **without any environment detection**:

- **Local**: `http://localhost:3000`
- **Railway**: `https://<railway-host>/yourapp/` (behind Caddy prefix proxy)

This document defines the only allowed routing/pathing patterns for generated apps.

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

## Non-Negotiable Rules

### Rule 0: No environment detection
Generated app code must NOT attempt to detect Railway vs local.
No `apiPrefix`, no `BASE_PATH`, no `window.location.pathname` prefix hacks, no templated prefix injection.

### Rule 1: Never use `<base>` tags
No `<base href=...>` anywhere.

### Rule 2: Server-side vs Client-side path styles

**Server-side (Express routes):**
- Always **absolute** paths starting with `/`
- Example: `app.get('/dashboard', ...)`, `app.post('/api/auth/login', ...)`

**Server-side (redirects in HTML responses):**
- Always **absolute** paths starting with `/`
- Example: `res.redirect('/dashboard')`

**Server-side (redirects in JSON responses):**
- Always **relative** paths with **NO leading `/`**
- Example: `res.json({ success: true, redirect: 'dashboard' })`
- Client uses: `window.location.href = result.redirect`

**Client-side (HTML links and forms):**
- Always **relative** paths with **NO leading `/`**
- Examples: `href="dashboard"`, `action="#"`

**Client-side (JavaScript fetch):**
- Always **relative** paths with **NO leading `/`**
- Examples: `fetch('api/employees')`, `fetch('api/auth/login')`
- **NEVER** use absolute paths like `fetch('/api/employees')` - this bypasses `/yourapp/` on Railway

### Rule 3: API namespace is mandatory
All JSON/data endpoints in the generated app must live under:

- **`/api/*`** (server-side absolute)
- **`api/*`** (client-side relative)

This prevents collisions with page routes (e.g., `/employees` page vs employees data).

### Rule 4: Flat pages only (no nested GET pages)
Generated app **pages** must be single-segment routes only:

✅ `/login`, `/dashboard`, `/employees`  
❌ `/employees/123`, `/employees/123/edit`, `/dashboard/settings`

If you need “details”, do it as:
- query string (`/employees?id=123`), and/or
- POST action → server redirect back to a flat page, and/or
- data fetched from `api/...`

### Rule 5: No trailing slashes on pages
Canonical page URLs must not end with `/` (except root if you ever use it).
This avoids browser-relative resolution changing based on trailing slash.

✅ `/employees`  
❌ `/employees/`

---

## Canonical Endpoint Map (Generated App)

### Pages (HTML)
- `GET /login` → login page
- `GET /dashboard` → dashboard page
- `GET /employees` → employees page

### API (JSON)
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET  /api/auth/check-session`

- `GET  /api/employees`
- `POST /api/employees`
- (etc — all data endpoints stay under `/api/...`)

---

## Client-Side Patterns (Browser)

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
Always relative and namespaced under `api/...`:

```javascript
await fetch('api/employees', { credentials: 'include' });

await fetch('api/auth/check-session', { credentials: 'include' });

await fetch('api/auth/logout', {
  method: 'POST',
  credentials: 'include',
});
```

**CRITICAL - Never do this (bypasses /yourapp and hits FastAPI):**

```javascript
// ❌ WRONG - absolute paths
fetch('/api/employees')
fetch('/api/auth/login')
```

### Form Handling Pattern (MANDATORY)

**All forms MUST use JavaScript fetch, not standard HTML form submission.**

Pattern:

```html
<form action="#" method="POST">
  <input name="email" type="email" required>
  <input name="password" type="password" required>
  <button type="submit">Submit</button>
</form>

<script>
  document.querySelector('form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);
    
    try {
      const response = await fetch('api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(data)
      });
      const result = await response.json();
      
      if (result.success) {
        window.location.href = result.redirect;  // relative path from server
      } else {
        // Show error message
      }
    } catch (err) {
      // Handle error
    }
  });
</script>
```

**Why this pattern:**
- `action="#"` prevents standard form submission
- `e.preventDefault()` stops page reload
- Fetch uses **relative path** `api/auth/login` (no leading `/`)
- Server returns JSON with **relative redirect**: `{ success: true, redirect: 'dashboard' }`
- Works identically on localhost and Railway


---

## Server-Side Patterns (Express)

### Route Definitions
Always use absolute paths starting with `/`:

```javascript
// Pages (serve HTML)
app.get('/login', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'login.html'));
});

app.get('/dashboard', isAuthenticated, (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'dashboard.html'));
});

// API endpoints (return JSON)
app.post('/api/auth/login', async (req, res) => { ... });
app.post('/api/auth/logout', (req, res) => { ... });
app.get('/api/auth/check-session', (req, res) => { ... });
app.get('/api/employees', isAuthenticated, async (req, res) => { ... });
```

### JSON Response Format (for API endpoints)

**Login endpoint:**

```javascript
router.post('/api/auth/login', async (req, res) => {
  const { email, password } = req.body;
  const user = await validateUser(email, password);
  
  if (!user) {
    return res.status(401).json({ 
      success: false, 
      error: 'Invalid credentials' 
    });
  }
  
  req.session.userId = user.id;
  req.session.user = { id: user.id, role: user.role };
  
  // Return RELATIVE redirect path
  res.json({ success: true, redirect: 'dashboard' });
});
```

**Logout endpoint:**

```javascript
router.post('/api/auth/logout', (req, res) => {
  req.session.destroy((err) => {
    if (err) {
      return res.status(500).json({ success: false, error: 'Logout failed' });
    }
    res.clearCookie('connect.sid');
    res.json({ success: true, redirect: 'login' });
  });
});
```

**Check session endpoint:**

```javascript
router.get('/api/auth/check-session', (req, res) => {
  res.json({ 
    authenticated: !!(req.session && req.session.userId),
    user: req.session?.user || null
  });
});
```

### HTML Redirects (for non-API routes)

When serving HTML pages that need to redirect, use **absolute** paths:

```javascript
// ✅ Correct - absolute path for HTML redirect
return res.redirect('/dashboard');

// ❌ Wrong - relative path
res.redirect('dashboard');
```

**Why:** Caddy rewrites `Location: /dashboard` to `Location: /yourapp/dashboard` on Railway.

Canonical “no trailing slash” middleware (recommended)

This prevents browser-relative resolution bugs caused by /employees/:

app.use((req, res, next) => {
  if (req.path.length > 1 && req.path.endsWith('/')) {
    const q = req.url.slice(req.path.length); // keep query string
    return res.redirect(301, req.path.slice(0, -1) + q);
  }
  next();
});

Sessions (dev-safe, works local + behind proxy)

Because local dev is HTTP, cookie secure must remain false in this canonical spec.

app.use(session({
  secret: process.env.SESSION_SECRET || 'dev-secret',
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: false,
    sameSite: 'lax',
  },
}));

---

## Caddy Configuration (Railway prefix proxy)

### Caddy Goals
1. Route `/yourapp/*` to the generated app (Node)
2. Strip `/yourapp` before forwarding upstream
3. Rewrite `Location: /login` → `Location: /yourapp/login`
4. Prevent double-prefix loops (`/yourapp/yourapp/...`)

### Canonical Caddy Configuration

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

- ✅ Node emits: `Location: /login`
- ✅ Caddy rewrites to: `Location: /yourapp/login`
- ❌ Node emits: `Location: /yourapp/login` (causes double-prefix)

---

## Environment Variables (Railway + Local)

### Ports
- **Caddy:** Listens on Railway-provided `$PORT` (public)
- **Node/Express:** Listens on `3000` (internal)
- **FastAPI:** Listens on `8001` (internal)

**IMPORTANT:** Do not set `PORT=3000` for the generated app; reserve `$PORT` for Caddy.

### Required Variables
- `SESSION_SECRET` (recommended for production apps)

### Server Startup Pattern

```javascript
const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
```

---

## Troubleshooting

### Symptom: "Works on localhost, 404 on Railway"

Almost always caused by:
- ✅ Client used an **absolute path** (`/api/...`, `/dashboard`, `/css/...`)
- ✅ Page URL ended with **trailing slash** (`/employees/`) causing wrong relative resolution
- ✅ Node emitted `Location: /yourapp/...` and Caddy double-prefixed

### Quick Checks

**Browser DevTools Network tab (Railway):**
- All requests must start with `/yourapp/...`
- If you see requests to `/api/...` or `/dashboard` → client is using absolute paths

**Grep the generated app for violations:**

```bash
# Find absolute paths in HTML/JS (should return nothing)
grep -r 'href="/' public/
grep -r 'src="/' public/
grep -r "fetch('/" public/
grep -r 'action="/' public/
```

### Curl Smoke Tests (Railway)

**Test page route:**
```bash
curl -I https://<railway-host>/yourapp/login
# Should return 200 OK
```

**Test API route:**
```bash
curl -I https://<railway-host>/yourapp/api/auth/check-session
# Should return 200 OK (or 401 if not authenticated)
```

### Common Mistakes

| Mistake | Fix |
|---------|-----|
| `fetch('/api/employees')` | `fetch('api/employees')` |
| `href="/dashboard"` | `href="dashboard"` |
| `action="/api/auth/login"` | `action="#"` + JS handler |
| `res.json({ redirect: '/dashboard' })` | `res.json({ redirect: 'dashboard' })` |
| Environment detection code | Remove all `isRailway`, `apiPrefix` variables |
| `cookie: { secure: true }` | `cookie: { secure: false }` |

---

## File Serving Pattern (Standardized)

**Decision Date:** January 4, 2026

Generated apps must use the standard Express static file serving pattern:

### Pattern (REQUIRED)
```javascript
// In server.js (setup once)
app.use(express.static('public'));

// In route handlers
router.get('/login', (req, res) => {
  res.redirect('/login.html');
});

router.get('/dashboard', (req, res) => {
  res.redirect('/dashboard.html');
});
```

### Rationale
- **Simplicity:** No path calculations needed (`__dirname`, `..`, `path.join()`)
- **Error prevention:** Eliminates common mistakes with wrong number of `..` in paths
- **Standard Express pattern:** Follows Express.js best practices
- **Already present:** `express.static('public')` is standard in all generated apps
- **Flexibility maintained:** Works for all file serving scenarios

### Forbidden Pattern
❌ Do NOT use `res.sendFile()` with manual path calculations:
```javascript
// WRONG - error-prone path calculations
res.sendFile(path.join(__dirname, '..', '..', 'public', 'login.html'));
```

This pattern is error-prone because:
- Files in `src/routes/` need TWO `..` to reach project root
- Files in `src/server.js` need ONE `..` to reach project root
- Easy to get wrong, causes file not found errors

---

## Complete Working Example

See `architect/aayourapp_gold_sample_readonly/yourapp/` for a fully working reference implementation.
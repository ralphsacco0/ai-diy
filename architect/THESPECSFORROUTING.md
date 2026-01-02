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

**Server-side (Express routes + redirects):**
- Always **absolute** paths starting with `/`
- Example: `res.redirect('/dashboard')`

**Client-side (HTML and browser JS):**
- Always **relative** paths with **NO leading `/`**
- Examples: `href="dashboard"`, `fetch('api/employees')`

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

Static assets (HTML)

Always relative:

<link rel="stylesheet" href="css/styles.css">
<script src="login.js"></script>

Fetch (browser JS)

Always relative and namespaced under api/...:

await fetch('api/employees', { credentials: 'include' });

await fetch('api/auth/check-session', { credentials: 'include' });

await fetch('api/auth/logout', {
  method: 'POST',
  credentials: 'include',
});

Never do this (bypasses /yourapp and hits FastAPI):

fetch('/api/employees')
fetch('/api/auth/login')

Form actions

Prefer JS-handled forms + action="#" (self-submit), OR a relative API action.

Recommended (self-submit + JS handler):

<form id="loginForm" action="#" method="post">
  ...
</form>

Allowed (direct to API route):

<form action="api/auth/login" method="post">
  ...
</form>


⸻

Server-Side Patterns (Express)

Absolute route definitions

Always start with /:

app.get('/login', ...);
app.get('/dashboard', ...);
app.get('/employees', ...);

app.post('/api/auth/login', ...);
app.post('/api/auth/logout', ...);
app.get('/api/auth/check-session', ...);

app.get('/api/employees', ...);

Absolute redirects (mandatory)

Always redirect with a leading /:

return res.redirect('/dashboard'); // correct

Never:

res.redirect('dashboard'); // wrong

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


⸻

Caddy Configuration (Railway prefix proxy)

Caddy goals
	1.	Route /yourapp/* to the generated app (Node)
	2.	Strip /yourapp before forwarding upstream
	3.	Rewrite Location: /login → Location: /yourapp/login
	4.	Prevent double-prefix loops (/yourapp/yourapp/...)

Canonical Caddy snippet (guarded Location rewrite)

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

Critical rule for Node redirects

Node/Express must NEVER emit redirects containing /yourapp.
Node should only emit: /login, /dashboard, etc.
Caddy is responsible for prefixing on Railway.

⸻

Environment Variables (Railway + Local)

Ports
	•	Caddy listens on Railway-provided $PORT (public)
	•	Node/Express listens on 3000 (internal)
	•	FastAPI listens on 8001 (internal)

Do not set PORT=3000 for the generated app; reserve $PORT for Caddy.
If you want configurability, use APP_PORT=3000 for Node, not PORT.

Required
	•	SESSION_SECRET (recommended for non-toy apps)

⸻

Troubleshooting (Dev)

Symptom: “works on localhost, 404 on Railway”

Almost always one of:
	•	client used an absolute path (/api/..., /dashboard, /css/...)
	•	a page URL ended with trailing slash (/employees/) and links resolved under it
	•	Node emitted Location: /yourapp/... and Caddy double-prefixed

Quick checks
	•	In browser devtools Network:
	•	all requests must start with /yourapp/... when deployed
	•	Grep generated app:
	•	no href="/
	•	no src="/
	•	no fetch('/
	•	no action="/

Curl smoke tests (Railway)
	•	Page:
	•	curl -I https://<host>/yourapp/login
	•	API:
	•	curl -I https://<host>/yourapp/api/auth/check-session

If you want, I can also give you the **exact “prompt insert” text** for:
- Sprint Execution Architect
- Sprint Execution Developer
- Sprint Review Alex  
so they **must** follow this canonical spec (and stop reintroducing `/api/...` absolute fetches, non-namespaced data calls, or nested pages).
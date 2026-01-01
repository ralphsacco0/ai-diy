# What We Know About Paths and Routing

## Executive Summary

**Status**: IMPLEMENTED - Option A (Pure Caddy Rewriting)
**Date**: January 1, 2026

After extensive testing and debugging, we've implemented a simple routing solution: **Caddy handles ALL path rewriting**. Generated apps use standard paths with NO environment detection, NO template injection, and NO special variables.

## The Core Problem

Generated apps need to work in two different environments:
- **Local Mac**: Direct access at `http://localhost:3000/`
- **Railway**: Proxied access at `https://app.railway.app/yourapp/`

## The Solution: Pure Caddy Rewriting

**Key Insight**: Caddy's `handle_path /yourapp/*` directive strips the `/yourapp/` prefix BEFORE forwarding to Express. This means:
- Express app NEVER sees `/yourapp/` in any request
- Same paths work in both environments
- No code changes needed between environments

## Implementation: Option A (Pure Caddy Rewriting)

### What We Removed

**From system prompts:**
- ❌ Environment detection code (`process.env.RAILWAY_ENVIRONMENT`)
- ❌ Template injection middleware (`res.locals.apiPrefix`)
- ❌ API prefix variables (`apiPrefix`, `API_PREFIX`)
- ❌ Template helper functions (`apiCall()`)

**Why**: These added complexity without benefit. Caddy strips the prefix automatically.

### The Final Pattern (Simple)

**API calls**: Use absolute paths (`fetch('/api/employees')`)
- Works from any page depth
- Railway: Browser sends `/yourapp/api/employees` → Caddy strips `/yourapp/` → Express receives `/api/employees`
- Local: Browser sends `/api/employees` → Express receives `/api/employees`

**Navigation**: Use relative paths (`href="dashboard"`)
- Resolves relative to current URL
- Railway: At `/yourapp/employees`, clicking `href="dashboard"` → `/yourapp/dashboard`
- Local: At `/employees`, clicking `href="dashboard"` → `/dashboard`

**Forms**: Use relative paths (`action="api/auth/login"`)
- Submits relative to current page
- Works consistently in both environments

**Server redirects**: Use absolute paths (`res.redirect('/dashboard')`)
- Railway: Caddy rewrites Location header from `/dashboard` to `/yourapp/dashboard`
- Local: Browser receives `/dashboard` directly

## The Technical Reason This Works

### API Calls (Absolute)
```javascript
fetch('/api/employees')  // Works from ANY page depth
```
- Resolves to domain root: `/yourapp/api/employees` on Railway, `/api/employees` locally
- Independent of current page URL
- Caddy rewrites Location headers but not fetch URLs

### Navigation (Relative)
```html
<a href="dashboard">Dashboard</a>
```
- Resolves relative to current URL
- Railway: `/yourapp/employees` + `href="dashboard"` → `/yourapp/dashboard` ✅
- Local: `/employees` + `href="dashboard"` → `/dashboard` ✅

### Forms (Relative)
```html
<form action="api/auth/login" method="POST">
```
- Submits relative to current page
- Works consistently in both environments

## Changes Made (January 1, 2026)

### 1. Updated System Prompts

**Files changed**:
- `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt`
  - Removed environment detection requirements
  - Removed template injection patterns
  - Added clear "DO NOT" statements
  - Emphasized: API calls use absolute paths, navigation uses relative paths

- `system_prompts/SPRINT_EXECUTION_DEVELOPER_system_prompt.txt`
  - Removed apiPrefix variable usage
  - Removed environment detection code
  - Simplified to: fetch('/api/user') for API calls, href="dashboard" for navigation

- `architect/LLM_ONBOARDING.md`
  - Added explicit statement that Caddy strips prefix before forwarding
  - Added "DO NOT add" section listing what NOT to generate
  - Clarified that Express never sees /yourapp/ in requests

### 2. Caddy Configuration (Already Correct)

The Caddyfile at `/Users/ralph/AI-DIY/ai-diy/Caddyfile` uses:
```caddy
handle_path /yourapp/* {
    reverse_proxy 127.0.0.1:3000
}
```

The `handle_path` directive automatically strips `/yourapp/` before forwarding. No changes needed.

## Testing Checklist

When testing routing in generated apps:

### ✅ Verify These Work

1. **Login flow**: `/yourapp/login` → successful login → dashboard
2. **API calls from any page**:
   - From `/yourapp/dashboard`: `fetch('/api/employees')` works
   - From `/yourapp/employees`: `fetch('/api/employees')` works
3. **Navigation between pages**:
   - `href="dashboard"` from any page works
   - `href="employees"` from any page works
4. **Form submissions**:
   - Login form submits correctly
   - Search/filter forms work

### ❌ Watch Out For These

1. **Empty data tables**: Often indicates API calls failing (check browser dev tools)
2. **404 errors on API calls**: Usually relative path issue from nested pages
3. **Redirect loops**: Check Caddy Location header rewrite rules
4. **Navigation going to wrong URLs**: Absolute paths in navigation breaking proxy

## Debugging Steps When Things Don't Work

### 1. Check API Calls
```bash
# Check if API endpoints are accessible
curl https://your-app.railway.app/api/employees
```

### 2. Check Browser Network Tab
- Look for 404 errors on fetch requests
- Verify URLs are resolving correctly
- Check if relative paths are being appended incorrectly

### 3. Test Both Environments
- Local: `http://localhost:3000/login`
- Railway: `https://app.railway.app/yourapp/login`
- If one works and other doesn't, it's a path resolution issue

### 4. Check Generated Code
```javascript
// Should see this pattern:
fetch('/api/employees')  // Absolute - correct

// NOT this pattern:
fetch('api/employees')   // Relative - wrong for API calls
```

## Future Considerations

### 1. Automated Testing
- Add tests that verify API calls from different page depths
- Test navigation flows in both environments

### 2. Code Generation Validation
- Lint generated code for path patterns
- Validate fetch calls use absolute paths
- Validate navigation uses relative paths

### 3. Documentation Updates
- Keep examples in sync with actual working patterns
- Add more debugging guidance to onboarding docs

## Key Takeaways

1. **Caddy does the heavy lifting** - `handle_path` strips prefix automatically
2. **No environment detection needed** - same code works everywhere
3. **API calls need absolute paths** - they must work from any page depth
4. **Navigation needs relative paths** - to maintain proxy compatibility
5. **Keep it simple** - no variables, no template injection, no complexity

## Quick Reference

| Context | Pattern | Example | Why |
|---------|---------|---------|-----|
| API calls | Absolute | `fetch('/api/user')` | Works from any page depth |
| Navigation links | Relative | `href="dashboard"` | Resolves relative to current URL |
| Form actions | Relative | `action="api/auth/login"` | Submits relative to current page |
| Server redirects | Absolute | `res.redirect('/dashboard')` | Caddy rewrites Location header |
| Client redirects | Relative | `window.location.href = 'login'` | Resolves relative to current URL |

**DO NOT add to generated code:**
- ❌ `const isRailway = process.env.RAILWAY_ENVIRONMENT === 'production'`
- ❌ `const apiPrefix = isRailway ? '/yourapp' : ''`
- ❌ `res.locals.apiPrefix = apiPrefix`
- ❌ `const API_PREFIX = '{{apiPrefix}}'`
- ❌ `fetch(\`\${apiPrefix}/api/user\`)`

**DO use in generated code:**
- ✅ `fetch('/api/user')` - simple absolute path
- ✅ `href="dashboard"` - simple relative path
- ✅ `res.redirect('/dashboard')` - simple absolute path

# Routing Solution Implementation - January 1, 2026

## Problem Statement

The AI-DIY platform generates Express applications that must work in two environments:
1. **Local Development**: Direct access at `http://localhost:3000/`
2. **Railway Production**: Proxied access at `https://ai-diy-dev-production.up.railway.app/yourapp/`

Multiple routing approaches were attempted, causing confusion and failures:
- **Routing-Spec.md**: Template injection with `{{apiPrefix}}` variables
- **LLM_ONBOARDING.md**: Hybrid absolute/relative approach
- **System prompts**: Mixed guidance with environment detection

**Result**: Generated apps had environment detection code, template injection middleware, and `{{apiPrefix}}` variables in HTML files that didn't work because static HTML files can't use template variables without a template engine.

## Solution: Option A - Pure Caddy Rewriting

**Core Principle**: Let Caddy handle ALL path rewriting. Generate simple, standard Express code with NO environment detection.

### How It Works

**Caddy's `handle_path` directive** in `/Users/ralph/AI-DIY/ai-diy/Caddyfile`:
```caddy
handle_path /yourapp/* {
    reverse_proxy 127.0.0.1:3000
}
```

This **strips the `/yourapp/` prefix BEFORE forwarding** to Express:
- Browser requests: `/yourapp/login`
- Caddy strips prefix and forwards: `/login`
- Express receives: `/login`

**Result**: Express sees identical paths in both environments.

### The Pattern

| Component | Pattern | Example | Why |
|-----------|---------|---------|-----|
| **API calls** | Absolute | `fetch('/api/user')` | Works from any page depth |
| **Navigation** | Relative | `href="dashboard"` | Resolves relative to current URL |
| **Forms** | Relative | `action="api/auth/login"` | Submits relative to current page |
| **Server redirects** | Absolute | `res.redirect('/dashboard')` | Caddy rewrites Location header |

### What We Removed

**From generated applications:**
- ❌ Environment detection: `const isRailway = process.env.RAILWAY_ENVIRONMENT === 'production'`
- ❌ API prefix variables: `const apiPrefix = isRailway ? '/yourapp' : ''`
- ❌ Template injection middleware: `res.locals.apiPrefix = apiPrefix`
- ❌ Template variables in HTML: `const API_PREFIX = '{{apiPrefix}}'`
- ❌ Helper functions: `function apiCall(endpoint) { return fetch(\`\${apiPrefix}\${endpoint}\`) }`

**Why**: These added complexity without benefit. Caddy strips the prefix automatically.

## Files Changed

### 1. System Prompts

**`system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt`**
- Lines 129-166: Replaced "ENVIRONMENT-AWARE ROUTING ARCHITECTURE" section
- Removed: Environment detection requirements, template injection patterns
- Added: Clear statement that Caddy strips prefix before forwarding
- Added: "DO NOT add environment detection code" warnings
- Emphasized: API calls use absolute paths, navigation uses relative paths

**`system_prompts/SPRINT_EXECUTION_DEVELOPER_system_prompt.txt`**
- Lines 108-155: Replaced "ENVIRONMENT-AWARE ROUTING IMPLEMENTATION" section
- Removed: apiPrefix variable usage, template injection requirements
- Added: "DO NOT use apiPrefix or API_PREFIX variables"
- Simplified: `fetch('/api/user')` for API calls, `href="dashboard"` for navigation

### 2. Documentation

**`architect/LLM_ONBOARDING.md`**
- Lines 531-550: Updated "Reverse Proxy Path Handling" section
- Added: Explicit statement that Caddy strips prefix before forwarding
- Added: "DO NOT add" section listing what NOT to generate
- Added: Clear explanation that Express never sees `/yourapp/` in requests
- Clarified: Path rules for API calls (absolute) vs navigation (relative)

**`architect/whatweknowaboutpathsandrouting.md`**
- Updated entire document to reflect Option A implementation
- Added status: "IMPLEMENTED - Option A (Pure Caddy Rewriting)"
- Added "What We Removed" section
- Added "DO NOT add to generated code" reference table
- Documented all changes made on January 1, 2026

### 3. Files NOT Changed

**`architect/Routing-Spec.md`**
- **Status**: KEPT for reference until solution is proven
- Contains the template injection approach that we're replacing
- Will be deleted or archived once Option A is verified working

**`Caddyfile`**
- **Status**: Already correct, no changes needed
- Uses `handle_path /yourapp/*` which strips prefix automatically

## Testing Plan

### Before Running Sprint

1. **Verify system prompts are deployed** to Railway
2. **Check that Mike and Alex will NOT generate**:
   - Environment detection code
   - Template injection middleware
   - apiPrefix variables
   - Template helper functions

### After Running Sprint

1. **Check generated code** in `/Users/ralph/AI-DIY/ai-diy/development/src/static/appdocs/execution-sandbox/client-projects/yourapp/`:
   - `src/server.js` should NOT have environment detection
   - `public/*.html` should NOT have `{{apiPrefix}}` variables
   - `public/*.html` should use `fetch('/api/user')` for API calls
   - `public/*.html` should use `href="dashboard"` for navigation

2. **Test on Railway**:
   - Login at `/yourapp/login` should work
   - API calls from dashboard should work
   - Navigation between pages should work
   - No 404 errors, no redirect loops

3. **Test locally** (if possible):
   - Same tests at `http://localhost:3000/`
   - Should work identically without code changes

## Expected Outcomes

### Success Criteria

✅ Generated `server.js` has NO environment detection code
✅ Generated HTML files have NO `{{apiPrefix}}` template variables
✅ API calls use absolute paths: `fetch('/api/user')`
✅ Navigation uses relative paths: `href="dashboard"`
✅ Login flow works on Railway: `/yourapp/login` → `/yourapp/dashboard`
✅ API calls work from any page depth
✅ No 404 errors, no redirect loops

### If It Fails

**Possible causes:**
1. System prompts not deployed to Railway
2. Mike/Alex still generating old patterns (check prompt content)
3. Caddy configuration issue (verify `handle_path` is working)
4. Browser caching old code (hard refresh)

**Debugging steps:**
1. Check generated code matches expected patterns
2. Test direct to port 3000: `curl http://127.0.0.1:3000/login`
3. Test through proxy: `curl https://railway-url/yourapp/login`
4. Check browser network tab for actual URLs being requested

## Next Steps

1. **Deploy changes** to Railway (commit and push)
2. **Run a sprint** to generate a fresh application
3. **Verify generated code** matches expected patterns
4. **Test on Railway** - login flow, API calls, navigation
5. **If successful**: Archive or delete `Routing-Spec.md`
6. **If unsuccessful**: Review generated code, check what Mike/Alex actually produced

## Summary

We've simplified routing by removing all environment detection and template injection complexity. Caddy's `handle_path` directive does the heavy lifting automatically. Generated apps now use standard Express patterns that work in both environments without modification.

**Key insight**: The app never needs to know it's behind a proxy. Caddy strips the prefix before forwarding, so Express sees the same paths everywhere.

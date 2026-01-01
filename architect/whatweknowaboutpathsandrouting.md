# What We Know About Paths and Routing

## Executive Summary

After extensive testing and debugging of the AI-DIY platform's routing system, we've identified the correct patterns for generating applications that work in both local development (Mac) and production (Railway) environments.

## The Core Problem

Generated apps need to work in two different environments:
- **Local Mac**: Direct access at `http://localhost:3000/`
- **Railway**: Proxied access at `https://app.railway.app/yourapp/`

The challenge is making the same code work in both contexts without modification.

## What We Discovered

### 1. The "All Relative" Approach Was Wrong

**Initial hypothesis**: All client-side paths should be relative (no leading `/`)

**What broke**: API calls from nested pages
- From `/dashboard`: `fetch('api/employees')` → `/api/employees` ✅ works
- From `/employees`: `fetch('api/employees')` → `/employees/api/employees` ❌ 404 error

**Root cause**: Relative paths resolve relative to the current URL, not the app root.

### 2. The "All Absolute" Approach Was Wrong

**Initial hypothesis**: All paths should use leading `/`

**What broke**: Proxy routing on Railway
- Caddy proxy at `/yourapp/` expects relative navigation
- Absolute paths like `href="/dashboard"` bypass the `/yourapp/` prefix
- Result: 404 errors on Railway

### 3. The Hybrid Solution Works

**Final working pattern**:
- **API calls**: Use absolute paths (`fetch('/api/employees')`)
- **Navigation**: Use relative paths (`href="dashboard"`)
- **Forms**: Use relative paths (`action="api/auth/login"`)
- **Server-side redirects**: Use absolute paths (`res.redirect('/dashboard')`)

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

## What We Fixed

### 1. Updated System Prompts

**Files changed**:
- `system_prompts/SPRINT_EXECUTION_ARCHITECT_system_prompt.txt`
- `system_prompts/SPRINT_EXECUTION_DEVELOPER_system_prompt.txt`
- `architect/LLM_ONBOARDING.md`

**Key changes**:
- Clarified that API calls must use absolute paths
- Maintained that navigation stays relative
- Fixed contradictory examples in form submission code

### 2. Caddy Configuration

**Issue**: Redirect loop from `/yourapp/login` → `/yourapp/login`

**Root cause**: Overly broad Location header rewrite rule

**Fix**: Updated Caddyfile to use negative lookahead pattern
```caddy
header_down Location "^/((?!yourapp/).*)" "/yourapp/$1"
```

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

1. **Hybrid approach is necessary** - no single path strategy works for both environments
2. **API calls need absolute paths** - they must work from any page depth
3. **Navigation needs relative paths** - to maintain proxy compatibility
4. **Test both environments** - what works locally might break on Railway
5. **Browser dev tools are essential** - network tab reveals most routing issues

## Quick Reference

| Context | Pattern | Example |
|---------|---------|---------|
| API calls | Absolute | `fetch('/api/user')` |
| Navigation links | Relative | `href="dashboard"` |
| Form actions | Relative | `action="api/auth/login"` |
| Server redirects | Absolute | `res.redirect('/dashboard')` |
| Client redirects | Relative | `window.location.href = 'login'` |

Follow this pattern and your generated apps will work consistently in both development and production environments.

# Single-branch workflow (direct commits)

- Default branch: main (direct commits allowed)
- No feature branches or PRs required
- CI runs tests on every push to main
- CODEOWNERS provides visibility for critical paths

## Operational steps
1. Work directly on main branch
2. Commit and push changes directly
3. CI automatically runs tests and diagnostics
4. Tag releases as needed

## Setup
- Default branch: main
- No branch protection required
- CI runs on push to main

## Benefits
- Simple, fast workflow
- No PR overhead for solo development
- Still maintains CI testing and diagnostics

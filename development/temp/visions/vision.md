# BrightHR Lite Vision

**Status:** Approved
**Updated:** 2025-12-06T10:12:45.301775
**Client Approval:** Yes

---

PROJECT: BrightHR Lite Vision (Draft)

PROJECT: BrightHR Lite Vision

**PROJECT:** BrightHR Lite

**PROBLEM & VALUE:**  
Small businesses with 10–50 employees often rely on spreadsheets and email threads to handle employee data, leave requests, and compliance documents. This leads to frequent errors, lost information, and hours of wasted admin time. BrightHR Lite solves this by providing a simple, centralized platform that streamlines HR tasks, reduces mistakes, and frees up time for what matters—growing the business and supporting the team.

**TARGET USERS:**  
- **Small business owners (10–50 staff)**: Busy leaders who want to offload routine HR admin without complexity.  
- **HR managers / office admins**: Hands-on folks needing an intuitive way to track employee details, policies, and workflows.  
- **Employees**: Everyday staff seeking self-service options for things like requesting leave or updating personal info, with minimal tech hurdles (assuming basic computer literacy).

**KEY FEATURES:**  
**MVP Must-Haves:**  
- Employee directory (basic profiles with contact info, searchable and updatable)  
- Leave / absence management (request submission, approval workflows, and calendar views for oversight)  
- Document storage (secure upload and access for contracts, policies, and compliance docs)  

**Nice-to-Haves:**  
- Onboarding checklist for new hires (step-by-step guides and task tracking)  
- Simple performance review tracking (basic templates and reminders)  
- Email notifications for leave approvals and key updates  

**SUCCESS CRITERIA:**  
- 80% of employees using self-service for leave requests within the first 3 months  
- 50% reduction in HR admin time spent on leave tracking (measured via pre/post-pilot surveys)  
- 100% completeness of digital employee records (no more scattered spreadsheets)  
- Average user satisfaction score of ≥4/5 from pilot team feedback  

**CONSTRAINTS & TECHNICAL FOUNDATION:**  
- Web-only access in Phase 1 (no native mobile app)  
- Lightweight and low-cost: Total pilot budget under $5K, focusing on local development to avoid hosting fees initially  
- GDPR compliance essentials (easy data export, deletion options, and basic privacy controls)  
- **Deployment**: Local run on a Mac laptop for Phase 1 (targeting macOS Ventura or later). The architecture is designed for portability: use cross-platform libraries and configs (e.g., avoid OS-specific file paths; stick to relative paths) so the codebase can easily migrate to Windows/Linux or cloud (e.g., Vercel/Supabase) later—no major rewrites needed.

**TECHNICAL STACK:**  
- **Platform**: Mac local (Ventura+), web-based (localhost access only in MVP).  
- **Backend**: Node.js v18+ with Express (this is the ONLY supported backend; handles API endpoints and serves static frontend files).  
- **Frontend**: Plain HTML/CSS/JS served by Express from /public (NO React/Vue for MVP—keeps it lightweight and fast to develop).  
- **Database**: SQLite (file-based DB stored in the project directory, e.g., ./data.sqlite—no server setup required).  
- **Server Port**: Single port 3000 (backend and static frontend both served from http://localhost:3000 for simplicity).  
- **Development**: npm scripts in package.json:  
  * "start": starts the Express server (backend + static files).  
  * "test": runs Node.js native tests via `node --test`.  
  - Full setup: `npm install` for dependencies (Node.js via Homebrew or nvm); use .env for config (e.g., PORT=3000, DB_PATH=./data.sqlite).  
- **Seeding**: On first run, seed test data via backend script: 1 admin user (admin@test.com / Password123!), 5 sample employee records.  
- **Mac-Specific Notes**: Install Node.js (v18+) via Homebrew (`brew install node`). Ensure DB file writable; test on M1/M2 (arm64 compatible). Allow localhost:3000 in firewall if prompted. README.md with steps: "1. Install Node. 2. Clone repo. 3. npm install. 4. npm start. Access: http://localhost:3000."  
- **Testing**: Smoke tests via Node.js native test runner (npm test executes `node --test`—no external frameworks like Jest for MVP).  
- **Portability & Gotchas**: Relative paths only; minimal native modules for cross-platform ease. Gitignore .env and DB file for security.

**COMPETITIVE LANDSCAPE:**  
- **Existing assets**: Importable spreadsheets with current employee data and leave history to kickstart the system.  
- **Inspiration**: Drawing from BambooHR's clean, user-friendly interface and CharlieHR's focus on small-team simplicity—aiming for that same ease without the bloat.
# Instance & Subscription Roadmap

## 1. Purpose

This roadmap describes how to evolve AI-DIY from a single-user, laptop-hosted app into a system where:

- Each **app** runs in its own isolated instance (“appliance” model).
- Users can **self-subscribe**, create instances, and use them without my manual involvement.
- Usage can be **limited and billed simply** (e.g., time-based), without complex per-token accounting.
- The core AI-DIY app remains **single-tenant** internally (one vision/backlog/sprint pipeline per instance).

This is an outer layer around the existing app, not a rewrite of the core internals.

---

## 2. High-Level Concept

- **One instance = one app**  
  - One live vision, one backlog, one sandbox repo, one set of sprints.
- **Users may own multiple instances**  
  - If a user wants to build multiple apps, they create multiple instances.
- **The core app is unaware of other instances**  
  - It behaves as it does today, assuming it is the only project in the world.
- **A separate “Portal” handles users, subscriptions, and instance lifecycle.**

---

## 3. Components

### 3.1. Core AI-DIY App (unchanged in spirit)

- Runs as a **single-tenant appliance**:
  - One vision → backlog → sprints → code pipeline.
  - Uses local filesystem for:
    - `execution-sandbox/`
    - `static/appdocs/`
- Can be packaged as:
  - A Docker image **or**
  - A deployable folder that a hosting provider runs as a service.

### 3.2. Instance Hosting Layer

- A hosting provider capable of running many copies of the same app:
  - Example categories: container platforms (Fly.io, Railway, Render) or simple VPS with Docker.
- Responsibilities:
  - Run N independent instances of the AI-DIY image.
  - Each instance has its own:
    - Filesystem / sandbox
    - Logs
    - URL or subdomain
  - Expose an API or control mechanism to:
    - **Create** a new instance from a base image/template.
    - **Start / Stop** instances.
    - Optionally **destroy** instances.

### 3.3. Subscription & Instance Portal (new component)

A small, separate web app that:

- Manages **users**:
  - Sign up / log in.
- Manages **billing**:
  - Integrates with a payment processor (e.g., Stripe).
  - Handles subscriptions (e.g., monthly plans or pay-per-hour).
- Manages **instances**:
  - Create a new instance for a user via the hosting layer.
  - Track instance URL, owner, and status (Running/Stopped).
  - Start/stop instances on user request.
  - Log **active time** per instance for billing and governance.

The Portal does not run AI-DIY logic. It only orchestrates instances and billing.

---

## 4. Instance Lifecycle

Each instance (app) has a clear lifecycle:

1. **Created**
   - Triggered by the Portal (“Create new app”).
   - Hosting provider clones from a **base image/template**.
   - Initial state: `Stopped` or `Running` depending on design.

2. **Running**
   - User can access the AI-DIY UI and drive sprints.
   - The instance uses AI APIs and consumes compute.
   - Portal records:
     - `started_at` timestamp.
     - Optional usage counters (e.g., number of sprints executed).

3. **Stopped**
   - Instance is not accessible to the user.
   - No compute or AI usage is incurred.
   - Portal records:
     - `stopped_at` and **duration** (`stopped_at - started_at`).

4. **Destroyed (optional)**
   - Instance (and its data) is permanently removed.
   - Possibly used when:
     - Trial expires.
     - User explicitly deletes the app.
     - Long-idle instances are cleaned up (if policy requires).

---

## 5. Billing Model (Simple)

Initial design favors **simple billing**, not token-level precision:

- **Baseline assumption**:
  - AI + infrastructure cost is modest enough to cover with a time-based model (e.g., ~$5/hour of active use).
- **Primary metric**:
  - **Active instance hours**:
    - When an instance is in `Running` state, it accrues billable time.
- **Examples**:
  - Time-based:
    - Charge `$5/hour` of active time across all instances owned by the user.
  - Or plan-based:
    - Basic: includes `N` hours per month.
    - Additional hours billed at a fixed rate.

**Governors**:

- Max consecutive runtime per instance (e.g., 4 hours).
- Optional request-level limits:
  - Max sprints per hour.
  - Max calls to certain AI-heavy operations.
- Purpose: protect against runaway cost and abuse.

---

## 6. Data & Isolation Model

- Each instance has **exclusive** use of:
  - Vision document(s)
  - Backlog
  - Sprint definitions and logs
  - Execution sandbox repo
  - Optional project memory store (summaries, embeddings, etc.)
- No cross-instance access:
  - The core app only reads/writes within its own filesystem paths.
  - The Portal is the only layer that “knows” about multiple instances.

This isolation simplifies:

- Future Sprint Execution and Sprint Review redesign.
- Introducing project memory, code search, and repo-aware tools per instance.

---

## 7. Implementation Phases

### Phase 0 – Clarify “Appliance” Model (documentation only)

- Document that current app = **single-tenant appliance**:
  - One vision, one backlog, one sandbox repo.
- Confirm filesystem layout is suitable to be cloned as a base image:
  - No hard-coded machine-specific paths.
  - All instance-specific data lives under a known root (e.g., `/app/data`).

### Phase 1 – Base Image / Template

- Create a **clean template** of the app:
  - App code.
  - Default configuration files.
  - Empty:
    - `execution-sandbox/`
    - `static/appdocs/`
- Package this as:
  - A Docker image **or**
  - A reproducible folder for the hosting provider.

Outcome: one reproducible “golden” instance.

### Phase 2 – Instance Hosting Integration

- Choose a hosting provider capable of:
  - Running many copies of the app.
  - Exposing an API or deployment automation.
- Implement or script:
  - “Create new instance” → deploy a copy of the base image.
  - “Start instance” / “Stop instance”.
- Decide URL scheme:
  - Per-instance subdomain (e.g., `app-123.example.com`) **or**
  - Path-based with a reverse proxy (e.g., `example.com/instances/123`).

Outcome: manual but repeatable instance lifecycle (without the Portal yet).

### Phase 3 – Subscription & Instance Portal

- Build a small **Portal** with:
  - User registration / login.
  - Stripe integration for subscriptions / payments.
  - Instance management UI:
    - List user’s instances.
    - Create instance.
    - Start/stop instance.
- Backend responsibilities:
  - Maintain DB tables:
    - `users`
    - `instances` (owner, URL, status, created_at)
    - `usage_log` (instance_id, started_at, stopped_at)
  - Call hosting provider APIs to:
    - Create / start / stop instances.
- Billing logic:
  - On `start_instance`:
    - Record `started_at`.
  - On `stop_instance`:
    - Record `stopped_at` and compute duration.
    - Send usage to Stripe (or store for end-of-period invoicing).

Outcome: self-service sign-up, instance creation, and basic automated billing.

### Phase 4 – (Later) Sprint & Review Redesign Using Instance Isolation

- For each instance:
  - Introduce **Project Memory** (summaries, decisions, code map).
  - Introduce **repo tools** (list/read/write/search within that instance’s codebase).
- Refactor Sprint Execution and Sprint Review to:
  - Assume full control of a single isolated repo.
  - Use project memory and repo tools instead of huge prompts.
- This phase is **optional** for initial subscription rollout but enabled by this roadmap.

---

## 8. Non-Goals (for this roadmap)

- No multi-tenant data model inside the core AI-DIY app.
- No complex role-based access inside a single instance (each instance is effectively single user or small team).
- No detailed per-token billing; only time-based or coarse usage metrics are in scope initially.

---

## 9. Open Questions / To-Decide

- Which hosting provider to standardize on for instances?
- Exact pricing strategy (hourly vs tiered monthly plans).
- How long idle instances may remain `Running` before auto-stop.
- Retention policy for destroyed instances (backup vs irreversible delete).



FOLLOW UP WITH SERVICES - You’re right, naming concrete services makes this much more useful. I’ll keep it high-level but with actual vendor/product names you can plug into the roadmap.

Below is an updated section you can drop into your doc (or just overlay onto the previous roadmap).

⸻

Recommended Services / Plans (Concrete Examples)

You don’t have to use these exact vendors, but this gives you a realistic stack:

1. Hosting for per-instance app “appliances”
Option 1 – Railway (very simple)
Use Railway to run a Dockerized AI-DIY app:
	•	Service type:
	•	Railway “Service” running from your GitHub repo or Docker image.
	•	What you use it for:
	•	One “base service” definition (your app).
	•	Portal (or scripts) call Railway’s API to create new environments/instances of that service.
	•	Plan to aim at:
	•	Start on their free/trial tier while developing.
	•	Move to a paid team/project plan once you have real users (you’ll see the current plan names in their dashboard; just pick the first paid tier that allows enough RAM + persistent storage).

Option 2 – Fly.io (more control, still reasonable)
	•	Service type:
	•	A Fly.io app built from your Docker image.
	•	What you use it for:
	•	A “golden” Fly app config as your base.
	•	The Portal uses the Fly.io API to clone or create new apps (one per AI-DIY instance) and run them.
	•	Plan to aim at:
	•	Their default pay-as-you-go account (no special plan; you pay for vCPU/RAM/hours).
	•	Use small machines (e.g., 256–512 MB RAM) per instance to keep cost down.

You can pick either Railway or Fly.io and stick with it. Both can be driven by API from your Portal.

⸻

2. Database for the Portal (users, instances, usage log)
You need one small database for the Portal; the AI-DIY instances can stay file-based.

Three easy choices:
	•	Railway Postgres (if you host Portal + instances on Railway)
	•	Fly Postgres (Fly.io managed Postgres add-on)
	•	Cloud Postgres elsewhere:
	•	e.g., Supabase free or starter plan
	•	or Neon free tier

Minimum requirement: a small managed Postgres instance with:
	•	Tables: users, instances, usage_log, maybe billing_events.
	•	No heavy load, so entry-level free/cheap tiers are fine at first.

⸻

3. Payments / Subscriptions
Use Stripe – it already supports everything you need:
	•	Products & Prices
	•	Create a product like “AI-DIY Instance Access”.
	•	Create:
	•	A subscription price (e.g., monthly base fee), and/or
	•	A metered usage price (for “Active Instance Hours”).
	•	Stripe Billing features you’d use:
	•	Stripe Checkout for sign-up (hosted payment page).
	•	Stripe Billing – Subscriptions for monthly access.
	•	Stripe Billing – Metered Billing if you want to bill by hours:
	•	Portal records usage and sends “usage records” to Stripe for that price.

You don’t need anything beyond Stripe Payments + Stripe Billing to start.

⸻

4. Portal Hosting
The Portal itself is tiny and light. Host it wherever is least annoying:
	•	If you use Railway:
	•	Run Portal as another Service in the same Railway project.
	•	If you use Fly.io:
	•	Run Portal as its own Fly app (FastAPI or similar).
	•	If you prefer something even simpler:
	•	Render (Web Service with free/entry tier) for the Portal only.
	•	AI-DIY instances still on Fly.io or Railway.

So, in the doc, you can write something like:

“The Subscription & Instance Portal is a small web service (e.g., FastAPI) hosted on Railway or Fly.io, with a managed Postgres database (Railway Postgres or Fly Postgres). It integrates with Stripe Billing for subscriptions and metered usage, and with the hosting provider’s API (Railway or Fly.io) to create/start/stop per-user AI-DIY instances.”

⸻

5. Very short “bill of materials” you can paste into the roadmap
Add a small section like this at the end of your roadmap:

## 10. Suggested Vendor Stack (Initial)

- **Core AI-DIY Instance Hosting**
  - Option A: Railway
    - Run the AI-DIY app as a Railway Service (Docker or GitHub).
    - Use Railway API to create new environments/instances per user app.
  - Option B: Fly.io
    - Build a Docker image for AI-DIY.
    - Run one Fly.io app per instance, created via Fly.io API.

- **Portal Hosting**
  - Small FastAPI/Django/Flask app hosted as:
    - A separate Railway Service, or
    - A separate Fly.io app, or
    - A small Web Service on Render.

- **Portal Database**
  - Managed Postgres (Railway Postgres, Fly Postgres, Supabase, or Neon).

- **Billing**
  - Stripe:
    - Stripe Checkout for sign-up.
    - Stripe Billing (Subscriptions + optional Metered Billing by “Active Instance Hours”).

If you want, next step we can tighten this into a final INSTANCE_ROADMAP.md snippet with those vendor names baked in exactly where they belong, so you can drop it into your repo as-is.


PRICING - 

## 11. Cost Considerations (Indicative, Late 2025)

This section gives order-of-magnitude costs for the instance + portal model using example vendors. Numbers are approximate and will change over time; they are meant for planning, not as a quote.

### 11.1 Fixed / Platform Costs

**Portal + DB**

- Portal (FastAPI/Django/etc.) on Railway or Fly.io:
  - Railway: free tier for small apps, then a low base (e.g., Hobby plan around $5/month) plus usage. [oai_citation:0‡Railway](https://railway.com/pricing?utm_source=chatgpt.com)  
  - Fly.io: pay-as-you-go; a tiny 256 MB shared-CPU VM is around ~$2/month if you run it 24/7. [oai_citation:1‡Fly](https://fly.io/docs/about/pricing/?utm_source=chatgpt.com)  
- Managed Postgres (for users/instances/usage log):
  - Often included in starter tiers (Railway Postgres / Fly Postgres) or available with free/cheap plans from Supabase/Neon.

**Payment / Billing (Stripe)**

- Stripe Billing has:
  - Card processing around **2.9% + $0.30 per online transaction** (US, typical). [oai_citation:2‡Stripe](https://stripe.com/pricing?utm_source=chatgpt.com)  
  - Stripe Billing fee around **0.7% of recurring billing volume** for usage-based/recurring invoices. [oai_citation:3‡Stripe](https://stripe.com/billing/pricing?utm_source=chatgpt.com)  
- There is generally **no large up-front platform fee** for small volume; fees scale with revenue.

Net: Up-front platform cost can be close to **$0–$10/month** while you are in development or very early beta, assuming low traffic and starter tiers.

---

### 11.2 Per-Instance Infrastructure Cost

Each AI-DIY instance needs a small app server:

- Example: **Fly.io shared-cpu-1x, 256 MB RAM**
  - Roughly $1.9–$2.0/month if it runs 24/7. [oai_citation:4‡Fly](https://fly.io/blog/new-vms-more-ram-extra-cpu-and-a-dollar-menu/?utm_source=chatgpt.com)  
- If instances are **only started on demand** (user clicks “Start” / “Stop”):
  - Actual cost is proportional to active hours:
    - e.g., if an instance is active 20 hours/month:
      - ~20/730 ≈ 0.027 of full-time → ~0.027 × $2 ≈ **$0.05–$0.10 per month** for the VM itself.

Storage and bandwidth for a few repos/backlogs are tiny at this scale and typically sit inside the free/low usage included in starter plans. [oai_citation:5‡srvrlss.io](https://www.srvrlss.io/blog/fly-io-pay-as-you-go/?utm_source=chatgpt.com)  

---

### 11.3 AI API Costs (LLM Usage)

Assume OpenAI-style pricing for planning purposes:

- GPT-4o (flagship, general model):
  - Roughly **$2.50 per 1M input tokens** and **$10 per 1M output tokens** (ballpark based on late-2025 summaries). [oai_citation:6‡Price Per Token](https://pricepertoken.com/pricing-page/model/openai-gpt-4o?utm_source=chatgpt.com)  
- Lower-cost models (e.g., “mini” variants) are significantly cheaper:
  - Example ranges around **$0.60 per 1M input** and **$2.40 per 1M output** for GPT-4o-mini-class models. [oai_citation:7‡Rogue Marketing](https://the-rogue-marketing.github.io/openai-api-pricing-comparison-october-2025/?utm_source=chatgpt.com)  

**Illustrative cost per “heavier” sprint**

- Suppose one full sprint execution (including planning, code generation, tests, and some review) uses:
  - ~100k input tokens and ~50k output tokens with GPT-4o.
- Cost:
  - Input: 0.1M × $2.50 ≈ **$0.25**
  - Output: 0.05M × $10 ≈ **$0.50**
  - Total ≈ **$0.75 per sprint** on a flagship model.

Using a cheaper “mini” model for most steps (and reserving top models for tricky cases) can bring that closer to **$0.15–$0.30 per sprint**, depending on actual token usage. [oai_citation:8‡LaoZhang AI](https://blog.laozhang.ai/ai-tools/openai-gpt4o-pricing-guide/?utm_source=chatgpt.com)  

---

### 11.4 End-to-End Example Scenarios

These are **ballpark** numbers to reason about viability, assuming small-scale usage.

**Scenario A – Solo / Small Internal Use**

- 1 Portal instance (always on) + 1–3 AI-DIY instances used occasionally.
- 10 “serious” sprints/month using a mid/high-end model.
- Rough monthly cost:
  - Infra (Portal + 1–3 small VMs, mostly idle): **$5–$10**
  - AI (10 sprints × ~$0.50–$0.75): **$5–$8**
  - Stripe fees only if you charge others.

Total: roughly **$10–$20/month** to run the whole system for yourself and a couple of trusted testers.

**Scenario B – Early Beta with Paying Users**

- 10 users, each with their own instance used a few hours/month.
- 5 sprints/user/month at ~$0.50 each → ~**$25** AI cost.
- Infra: multiple small VMs, not 24/7 → **$10–$20**.
- Stripe fees: ~3–4% of revenue.

Charging even **$20–$30/month per user** with guardrails (limited active hours per month) should comfortably cover infra + AI and leave margin, given the above order-of-magnitude costs.

---

### 11.5 Design Implications

- The main **cost driver** is **LLM usage**, not hosting.
- You can keep **up-front and fixed costs very low**:
  - Use free/low-tier plans for Portal + DB + hosting while building.
  - Only pay more as instances and usage grow.
- You can control risk by:
  - Capping per-instance active hours per month.
  - Using cheaper models for routine steps and reserving expensive models for complex tasks.
  - Auto-stopping idle instances.

These assumptions are enough to justify a simple, time-based or tiered usage price (e.g., **$5/hour of active instance use**, or a fixed monthly fee with included hours) while still leaving room for a margin.



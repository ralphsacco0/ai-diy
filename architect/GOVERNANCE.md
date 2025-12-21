AI-DIY Governance Process (Collaborative Draft)

Key points:
ALWAYS GET APPROVAL BEFORE MAKING CHANGES.
All changes must update the existing documentation if approprate. Do not create new documents unless explicitly approved. Documentation updates are part of every request and part of the Definition of Done. See DOCUMENTATION_INDEX.md


Defines how Ralph, ChatGPT (Architect), and Cascade collaborate to design, maintain, and evolve the AI-DIY system.
This document governs the builders, not the apps created by AI-DIY.

1. Purpose

This governance framework ensures that all changes to the AI-DIY platform — its architecture, personas, documentation, tooling, and automation — are introduced, reviewed, and approved in a structured and traceable way.

It does not apply to apps or client projects produced by AI-DIY; those follow their own internal processes (Vision → Requirements → Build → Test).

2. Roles & Responsibilities

Role

Description

Decision Authority

Ralph (Owner / Product Director)

Final authority on all platform decisions. Defines strategic direction, approves ADRs, and accepts major releases.

Cascade (Automation / Integrator)


Executes only pre-approved actions

Contributors (Future)

Any additional human or AI collaborators working under Ralph’s direction.

Operate under this governance

3. Scope of Governance

This process applies to:

Architectural changes (structure, personas, runtime, repositories)

Documentation standards (See DOCUMENTATION_INDEX.md)

Governance of AI behaviors (persona prompts, escalation rules)

Release management and version control of the ai-diy app

It explicitly excludes:

The apps Vision, Requirements, Backlog, or other runtime workflows inside client projects. but includes myvision.md

Content, code, or artifacts under /execution-sandbox/client-projects.

4. Decision Process

4.1 Change Initiation

Any platform change begins with a request or proposal (from Ralph) that includes:


4.2 Discussion & Review

Ralph and ChatGPT review proposals in chat.

If the change affects core behavior, it becomes an ADR (Architectural Decision Record).

4.3 Approval & Implementation

Ralph’s explicit approval is required for all ADRs and significant merges.

Cascade executes the technical steps (commits, syncs, deployments).

4.4 Documentation

Every approved decision must be recorded as:

A Markdown or JSONL ADR in /architect/adr.*

Reference in /architect/architecture.md if it changes system structure

4.5 Documentation & Framework Review Requirement

Before implementing any platform-level change — architectural, behavioral, persona-related, schema-related, or structural — the Architect must perform the following steps:
	1.	Review the existing documentation and system framework
Ensure the proposed change aligns with the current architecture, meeting flows, persona structure, and documented patterns.
This prevents accidental drift or contradictions in core system behavior.
	2.	Determine whether documentation requires updates
Compare the proposed change against the authoritative reference documents (see DOCUMENTATION_INDEX.md).
If any section of the documentation will become outdated, unclear, or incomplete as a result of the change, it must be updated.
	3.	Update documentation as part of the change
When updates are required, modify the corresponding documents in the same change set (same commit series).
Documentation updates are not optional — they are part of the Definition of Done (DoD).
	4.	Record documentation impact in the ADR (if one exists)
If the change uses an ADR, note whether documentation was updated or why no updates were necessary.

This rule applies to all modifications to AI-DIY’s architecture, personas, system flows, schemas, runtime behavior, or governance logic.


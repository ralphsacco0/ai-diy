# AI-DIY Scrum Sim - Quick Help Guide

Welcome to **Agile in a Box** - an AI-driven project team that turns natural conversation into tested, deployable software.

---

## System Overview

You work with an AI team of 4 personas:
- **Sarah** - Project Manager (leads meetings, gathers requirements)
- **Mike** - Architect (designs solutions, breaks down work)
- **Alex** - Developer (writes code)
- **Jordan** - QA Tester (writes and runs tests)

Work flows through **7 meeting types**, each with specific keywords to trigger them.

---

## The 7 Meetings

### 1. **Vision Meeting**
**Purpose:** Define what you want to build - the problem, users, features, and success criteria.

**Keywords to start:**
- "start a vision meeting"
- "start vision meeting"

**What happens:**
- Sarah asks 7 questions about your project
- You answer to build a complete vision document
- Vision drives all future work

**End with:** "end meeting"

---

### 2. **Requirements Meeting** (Backlog Refinement)
**Purpose:** Turn vision into a prioritized backlog of user stories and wireframes.

**Keywords to start:**
- "start a requirements meeting"
- "start requirements meeting"
- "start a backlog meeting"
- "start backlog meeting"

**What happens:**
- Sarah creates user stories (US-###) with acceptance criteria
- Wireframes (WF-###) are designed as references
- Stories are prioritized and ready for sprint planning

**End with:** "end meeting"

---

### 3. **Sprint Planning Meeting**
**Purpose:** Select stories for the next sprint and define scope.

**Keywords to start:**
- "start sprint planning"
- "start a sprint planning meeting"
- "start sprint planning meeting"
- "plan a sprint"
- "let's plan a sprint"

**What happens:**
- Mike analyzes the backlog
- Mike proposes 2-5 stories that fit together logically
- You approve the selection
- Stories are marked "In Sprint"

**End with:** "end meeting"

---

### 4. **Sprint Execution Meeting**
**Purpose:** Run the sprint - Mike breaks down stories, Alex codes, Jordan tests.

**Keywords to start:**
- "start sprint execution meeting"
- "start sprint meeting"

**What happens:**
- Sarah starts the meeting and waits for your signal
- **You indicate you're ready** (say it any way: "start", "begin", "let's go", "execute", etc.)
- Sarah calls the orchestrator
- Mike breaks stories into tasks
- Alex generates code for each task
- Jordan writes tests
- All messages stream live to the chat

**End with:** "end meeting"

---

### 5. **Sprint Review Meeting**
**Purpose:** Demo completed work and gather feedback.

**Keywords to start:**
- "start sprint review meeting"
- "start sprint review"
- "review the sprint"
- "demo the work"

**What happens:**
- Sarah demonstrates each completed story
- You test the app: `./test-generated-app.command`
- You approve or request changes
- Stories marked "Done" or "Rejected"

**End with:** "end meeting"

---

### 6. **Sprint Retrospective Meeting**
**Purpose:** Reflect on what went well and what to improve.

**Keywords to start:**
- (Triggered by Sarah when sprint review is complete)

**What happens:**
- Sarah facilitates discussion
- You share feedback
- Improvements are captured for next sprint

**End with:** "end meeting"

---

### 7. **Regular Chat** (No Meeting)
**Purpose:** Ask questions, get advice, discuss with the team.

**How it works:**
- All 4 personas are active
- Each decides independently if they should respond
- Sarah leads, Mike advises on architecture, Alex on code, Jordan on testing

---

## Quick Reference: Keywords by Meeting

| Meeting | Start Keywords |
|---------|----------------|
| Vision | "start vision meeting" |
| Requirements | "start requirements meeting", "start backlog meeting" |
| Sprint Planning | "start sprint planning" |
| Sprint Execution | "start sprint execution meeting" |
| Sprint Review | "start sprint review" |
| Retrospective | (Auto-triggered) |
| Regular Chat | (No keyword needed) |

---

## Common Commands

| Command | What it does |
|---------|------------|
| "end meeting" | Ends the current meeting |
| "help" | Shows this guide |
| "./stop.command" | Stops the server (use if execution runs away) |
| "./test-generated-app.command" | Tests the generated app |

---

## Tips for Success

1. **Be clear about scope** - Vision and Requirements meetings set the foundation
2. **Approve before execution** - Sprint Planning ensures everyone agrees on scope
3. **Let the team work** - During Sprint Execution, watch the live progress
4. **Test thoroughly** - Sprint Review is your chance to validate
5. **Iterate** - Retrospectives improve the process

---

## Troubleshooting

**"Unknown Project" in meeting header?**
- Make sure you completed the Vision meeting first
- Project name comes from your vision

**Execution running away?**
- Run `./stop.command` to stop the server
- The 5-message hard stop is active during debugging

**Need to restart?**
- Run `./stop.command`
- Then start the server again

---

## Need More Help?

Check these files for detailed documentation:
- `myvision.md` - System vision and philosophy
- `architect/` - Architecture decisions and processes
- `docs/` - Detailed documentation
- `config_personas.json` - Persona definitions and system prompts

---

**Built with ❤️ by Ralph Sacco - AI-DIY**

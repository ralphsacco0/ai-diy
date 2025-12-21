# Vision Process

## Purpose
The Vision process defines how AI-DIY captures the initial high-level concept for a new project. 
It sets the foundation for all subsequent requirements, backlog, and development work.

The goal is to clarify *what problem is being solved*, *who it helps*, and *what success looks like* — 
without getting lost in implementation details.

---

## Inputs
- User conversation or prompt describing the app idea or goal.
- Optional reference materials (documents, screenshots, or prior notes).

---

## Outputs

### Versioned Document Pattern
Vision documents use a **timestamped file strategy** where each vision is a separate file:

- **`{ProjectName}-Vision_{timestamp}.json`** — Canonical vision document
  - Timestamped ID: `BrightHR-Lite2-Vision_20251010_132116`
  - Each save creates a new file (never overwrites)
  - Multiple visions can coexist (drafts, approved, different projects)
  - Approval workflow tracks which version is active

- **`{ProjectName}-Vision_{timestamp}.md`** — Human-readable version (same content)

**Content Structure**:
- Project name
- Problem statement
- Target users/personas
- Key features (must/nice-to-have)
- Success criteria (KPIs or goals)
- Constraints (time, tech, budget)
- Approval record (Ralph sign-off)

**Why Separate Files?** Vision documents need version history and approval workflow. Each vision is an independent, immutable document once created. This differs from the Backlog (single living document).

---

## Process Steps

1. **Capture Context**
   - Sarah asks guiding questions to uncover motivation, pain points, and objectives.
   - Responses are summarized and normalized into structured fields.

2. **Define Audience & Goals**
   - Identify who will use the app and what they hope to accomplish.
   - Translate general ideas into measurable outcomes.

3. **Outline Features**
   - Capture must-have and nice-to-have features in simple bullet format.
   - Sarah avoids detailed design — the focus remains on goals, not tasks.

4. **Confirm Success Criteria**
   - Establish how success will be measured (usage, satisfaction, business outcome).

5. **Record Constraints**
   - Document boundaries like timeline, platform, or compliance needs.

6. **Approval**
   - Ralph or the user confirms the vision summary is correct and complete.
   - Once approved, it becomes a frozen reference for Requirements capture.

---

## User Experience & Status Feedback

### Real-Time Progress Display

Vision meetings provide continuous visual feedback through a progressive status system that keeps users informed throughout the entire interaction.

**Initial State** (User sends message)
- Animated thinking dots (• • •) with "Thinking..." text
- Appears immediately in blue status bar (bottom-right corner)
- Indicates LLM is consuming context and processing prompts
- Generic message works for all Vision PM interactions

**Active Generation** (First progress update arrives ~0.5-1s)
- Automatically upgrades to detailed budget display
- Shows real-time metrics:
  - **Time**: Current elapsed / Total budget (e.g., "5s / 30s")
  - **Tokens**: Current usage / Maximum limit (e.g., "2.5K / 10K")
  - **Progress Bar**: Visual indicator of time budget consumption
- Updates every ~1 second during generation
- Animated dots continue to show activity

**Content Streaming**
- Vision document text appears word-by-word in chat area
- Real-time streaming provides immediate feedback
- User can read content as it's being generated
- No waiting for complete response before seeing results

**Completion**
- Final statistics displayed in budget bar
- Progress bar reaches 100%
- Status display automatically hides after 2 seconds
- Complete formatted response remains in chat

### Technical Implementation

**Context Injection**: Vision PM receives on every turn:
- System prompt with Vision PM persona instructions
- Full chat history from current session
- Current user message
- **No** pre-loaded vision documents (creates visions from scratch)

**Budget Tracking**: Each Vision PM interaction monitors:
- Time budget: 30 seconds default
- Token budget: Model-specific maximum (e.g., 10K tokens)
- Real-time progress updates via streaming API
- Automatic warnings if approaching limits

**Why This Design**:
- **Progressive disclosure**: Start simple ("Thinking..."), add detail when available
- **No placeholders**: Budget display only appears with real data
- **Continuous feedback**: Animated dots show activity even during idle periods
- **Transparency**: Users see exactly what resources are being consumed

---

## Example Vision Summary (Markdown)

```markdown
# Project Vision: Field Data Logger

## Problem
Field technicians need a reliable way to record test results without network access.

## Target Users
Environmental engineers, field surveyors, and lab technicians.

## Key Features
- Offline data capture
- GPS tagging
- CSV export

## Success Criteria
- 90% reduction in transcription errors
- 50% faster data reporting cycle

## Constraints
- Must run on Windows and iOS tablets
- Offline-first with sync capability

## Approval
Approved by: Ralph Sacco
Date: 2025-10-04
```

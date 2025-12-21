# Requirements Process

## Purpose
The Requirements process captures detailed functionality for the system defined in Vision.
It translates high-level goals into actionable requirements, user stories, and **interactive HTML wireframes**.

This process ensures that **nothing can be developed** until it is **fully understood and validated**.

---

## Inputs
- Approved `vision.json` (from Vision process)
- User's detailed descriptions of desired features or operations
- Existing backlog CSV (for incremental updates)

---

## Outputs

### Living Document Pattern
The backlog uses a **single file strategy** where all requirements are stored together:

- **`Backlog.csv`** — Single CSV file containing all requirements as rows
  - Fixed ID: `Backlog` (not timestamped)
  - Each requirement has a unique `Story_ID` column (e.g., NEW-002, NEW-003, WF-001)
  - Overwrite-on-save: Entire file updated when requirements change
  - All requirements viewable together in UI

- **`wireframes/`** — Folder containing HTML wireframe files with Tailwind CSS
  - Individual files: `{slug}.html` (e.g., `wf-001-landing-page.html`)
  - Referenced by `Wireframe_Ref` column in CSV

- **`Backlog.json`** — Metadata for the backlog (last updated, wireframe list, session info)

**Why One File?** Unlike Vision documents (which need version history), the backlog is a living document that evolves. All requirements are managed together for easier viewing, updating, and UI display.

---

## Process Steps

1. **Start Requirements Meeting**
   - User triggers: "Start Requirements Meeting" or "Open Backlog Session"
   - Sarah (Requirements PM) loads latest vision and existing backlog
   - Meeting mode activated (other personas silenced for focus)

2. **Feature-by-Feature Development**
   - Sarah works through vision features systematically
   - For each feature, captures:
     - **User Story** (As a..., I want..., so that...)
     - **Functional Requirements** (detailed acceptance criteria)
     - **Non-functional Requirements** (performance, security, etc.)
     - **Priority** (High, Medium, Low)
     - **Wireframe** (HTML with Tailwind CSS)

3. **Wireframe Generation**
   - Sarah generates **interactive HTML wireframes** using Tailwind CSS
   - Wireframes include: forms, buttons, tables, navigation layouts
   - Preview available via **modal dialog** in the web interface
   - Wireframes saved as `req-XXX-feature-name.html` files

4. **Backlog Management**
   - All requirements saved to `Backlog.csv` with columns:
     - ID, Title, User_Story, Acceptance_Criteria, Priority, Status
     - Vision_Ref, Wireframe_Ref, Notes
   - Wireframe_Ref contains clickable links to preview wireframes
   - CSV exportable for external use

5. **Validation & Approval**
   - User reviews requirements and wireframes in real-time
   - Sarah validates completeness before finalizing
   - User approved or requests changes

6. **Definition of Ready**
   - Requirements must have:
     - Complete user story and acceptance criteria
     - Associated wireframe (HTML file)
     - User approval
   - Status progresses: Draft → Review → Approved → Ready

---

## User Experience & Status Feedback

### Real-Time Progress Display

Requirements meetings use the same progressive status system as Vision meetings, providing continuous visual feedback throughout the interaction.

**Initial State** (User sends message)
- Animated thinking dots (• • •) with "Thinking..." text
- Appears immediately in blue status bar (bottom-right corner)
- Generic status works for all Requirements PM interactions
- Indicates LLM is processing context (vision + backlog + prompts)

**Active Generation** (First progress update arrives ~0.5-1s)
- Automatically upgrades to detailed budget display
- Shows real-time metrics:
  - **Time**: Current elapsed / Total budget (e.g., "8s / 30s")
  - **Tokens**: Current usage / Maximum limit (e.g., "3.2K / 10K")
  - **Progress Bar**: Visual indicator of progress
- Updates continuously during generation
- Animated dots show ongoing activity

**Content Streaming**
- Requirements text, user stories, and acceptance criteria stream in real-time
- User sees content as it's being generated
- Immediate feedback on what's being created
- Can interrupt if direction is wrong

**Completion**
- Final statistics displayed in budget bar
- Progress bar reaches 100%
- Status display hides after 2 seconds
- Complete formatted response in chat

### Technical Implementation

**Context Injection**: Requirements PM receives on every turn:
- System prompt with Requirements PM persona instructions
- **Latest approved Vision document** (automatically injected as system context)
- **Current Backlog.csv** (automatically injected as system context)
- Full chat history from current session
- Current user message

This automatic context injection ensures Requirements PM always works with the latest approved vision and current backlog state, maintaining alignment across all requirements work.

**Budget Tracking**: Same as Vision meetings
- Time budget: 30 seconds default
- Token budget: Model-specific maximum
- Real-time progress updates via streaming API
- Transparent resource consumption display

**Why Automatic Context Injection**:
- **Alignment**: Requirements always reference current approved vision
- **Consistency**: Backlog updates build on existing requirements
- **No manual steps**: User doesn't need to provide vision/backlog context
- **Always current**: Fetches latest files on every turn

---

## Wireframe Implementation Details

### HTML Wireframes
```html
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.tailwindcss.com"></script>
  <title>Feature Wireframe</title>
</head>
<body class="bg-gray-50 p-8">
  <div class="max-w-6xl mx-auto bg-white rounded-lg shadow-lg p-6">
    <h1 class="text-2xl font-bold mb-6 text-gray-800">Feature Name</h1>
    <!-- Interactive UI elements -->
  </div>
</body>
</html>
```

### Backlog UI Display
- **Card-Based Layout**: Each requirement displayed as an expandable card
- **Visual Badges**: Priority (High/Medium/Low) and Status (Draft/Approved/In Progress) with color coding
- **Collapsible Sections**: Long text fields (Functional Requirements, Non-Functional Requirements, Acceptance Criteria) are collapsed by default - click to expand
- **Story ID Prominent**: Each card shows the Story_ID at the top for easy reference
- **Responsive Design**: Vertical scrolling, mobile-friendly
- **Quick Overview**: See all requirements at a glance, expand for details

### Preview System
- **Modal Dialog**: Wireframes open in responsive modal overlay
- **Responsive Design**: Works on desktop and mobile
- **Interactive Elements**: Forms, buttons, navigation previews
- **API Served**: Wireframes served via `/api/backlog/wireframe/{slug}`

### CSV Integration
```csv
ID,Title,User_Story,Acceptance_Criteria,Priority,Status,Vision_Ref,Wireframe_Ref,Notes
REQ-001,Manager Approval,As a manager...,Criteria...,High,Draft,Vision,req-001-manager-approval,Wireframe created
```

---

## Example Requirement Record

```json
{
  "id": "REQ-001",
  "title": "Manager approval/rejection of leave requests",
  "user_story": "As a manager, I want to approve or reject employee leave requests, so that leave is authorized and records are up to date.",
  "acceptance_criteria": [
    "Managers can view pending requests for direct reports",
    "Approve/reject with optional comments",
    "Status updates reflected immediately",
    "Audit trail maintained"
  ],
  "priority": "High",
  "status": "Approved",
  "vision_ref": "Leave Management",
  "wireframe_ref": "req-001-manager-approval",
  "wireframe_path": "wireframes/req-001-manager-approval.html",
  "created_date": "2025-10-06",
  "approved_date": "2025-10-06"
}
```

---

## Integration Points

- **Vision Process**: Requirements build on approved vision documents
- **Development Process**: Ready requirements feed into sprint planning
- **Scribe**: Meeting notes and decisions captured for audit trail
- **UI Integration**: Backlog view with clickable wireframe links

---

## Notes
- **Sarah** is the primary persona managing this process
- **Real-time Collaboration**: User sees wireframes and provides feedback immediately
- **Persistent Storage**: All artifacts saved to `/development/src/static/appdocs/backlog/`
- **Version Control**: Backlog snapshots created for each requirements session

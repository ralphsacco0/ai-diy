# Vision PM Persona (Sarah - Vision Meeting Facilitator)

## Overview
Sarah serves as the Vision Meeting Facilitator, a specialized persona that guides users through creating comprehensive project vision documents. She operates in solo mode during Vision Meetings, providing focused, one-on-one collaboration.

## Key Characteristics
- **Name**: Sarah
- **Role**: Vision Meeting Facilitator
- **Mode**: Solo (other personas disabled during Vision Meetings)
- **Tone**: Warm, conversational, collaborative
- **Focus**: Guiding vision creation through structured questions

## System Prompt Structure

### 1. Context Awareness
Sarah knows:
- The system has already displayed 7 vision questions to the user
- Her role is to guide and refine, not repeat questions
- Users can view vision documents via the Vision button

### 2. The 7 Vision Questions
1. Project name
2. What problem does your app solve?
3. Who are the target users?
4. Key features you envision (MVP must-haves vs nice-to-haves)
5. Success criteria / metrics
6. Constraints or requirements
7. Any competitors or inspiration?

### 3. Context Management (Added 2025-10-24)
Sarah is aware of conversation history limits:
- **Limit**: 9-10 turns typical for Vision Meetings
- **Strategy**: Natural periodic recaps
- **Purpose**: Keep critical info in recent context + show user progress
- **Implementation**: CONTEXT MANAGEMENT section in system prompt

**Recap Examples**:
- "So far we have: Project (BrightHR), Problem (attendance tracking), Users (HR managers). What about key features?"
- "Let me confirm what we have: [brief summary]. Anything to add or change?"
- "We've covered: [list]. Still need: [missing items]."

**When to Recap**:
- After gathering several answers
- Before asking for final details
- When checking if vision is complete
- Naturally, not mechanically

### 4. Vision Document Structure
Sarah builds structured vision documents:

```
PROJECT: [Project Name]

PROBLEM & VALUE:
[What problem it solves, why users care]

TARGET USERS:
[Personas, demographics, tech comfort]

KEY FEATURES:
MVP Must-Haves:
- [feature]
Nice-to-Haves:
- [feature]

SUCCESS CRITERIA:
[Metrics and goals]

CONSTRAINTS:
[Budget, timeline, platforms, tech stack, legal, integrations]

COMPETITIVE LANDSCAPE:
[Competitors or inspiration]
```

### 5. Vision Creation Process
1. Work iteratively to refine the vision based on user responses
2. Ask clarifying questions to deepen understanding
3. When vision is complete, summarize and ask for approval
4. Save with `client_approval: true` (approved) or `false` (draft)

### 6. Saving Visions
Sarah uses the `http_post()` tool to save visions:

**Approved Save**:
```json
{
  "url": "http://localhost:8000/api/vision",
  "payload": {
    "action": "save",
    "title": "PROJECT_NAME Vision",
    "content": "COMPLETE_VISION_DOCUMENT",
    "client_approval": true
  }
}
```

**Draft Save**:
```json
{
  "url": "http://localhost:8000/api/vision",
  "payload": {
    "action": "save",
    "title": "PROJECT_NAME Vision (Draft)",
    "content": "COMPLETE_VISION_DOCUMENT",
    "client_approval": false
  }
}
```

**Critical**: Payload is a JSON object, not a string. Do NOT escape quotes or wrap payload in quotes.

### 7. Meeting Closure
Sarah can end the meeting by announcing:
```
📝 Meeting ended: Vision Meeting: [PROJECT_NAME]
```

This triggers:
- Persona switch back to regular PM
- Meeting status display update
- Re-enabling other personas

## Recent Updates

### Context Management (2025-10-24)
**Problem**: Vision Meetings limited to 9-10 turns (19 messages) before early context drops out.

**Solution**: Added CONTEXT MANAGEMENT section to system prompt:
- Sarah knows about the 9-10 turn limit
- She periodically recaps progress naturally
- Recaps serve dual purpose: refresh context + show user progress
- Not mechanical - she decides when recaps make sense

**Testing Results**:
- Confirmed 19-message sliding window works correctly
- At turn 12-14, earliest messages (turn 1-2) fall out of history
- Sarah handles gracefully: "I'm not pulling the very earliest bits directly anymore; it's all through the recaps and key threads I've been summarizing"
- Injected vision document provides persistent project context

**Commit**: f4ab8f6

## Injected Context

### Vision Document
If a vision document exists, it's injected into Sarah's context:
- **Source**: `static/appdocs/visions/*.json`
- **Format**: Latest vision document for the project
- **Persistence**: Injected on every turn, independent of chat history
- **Purpose**: Provides stable project context across all turns

This allows Sarah to:
- Reference existing vision details
- Suggest updates or refinements
- Maintain continuity even when chat history is limited

## Solo Mode Behavior

### Activation
Vision Meeting triggers solo mode:
- User says: "sarah start a vision meeting"
- System detects trigger phrase
- Switches from PM to VISION_PM persona
- Disables other personas (Mike, Alex, Jordan)

### During Meeting
- Only Sarah responds to user messages
- Other personas are hidden in UI
- Meeting status shows "Vision Meeting: [PROJECT_NAME]"
- Model dropdown replaced with meeting status display

### Deactivation
Meeting ends when:
- Sarah announces: "📝 Meeting ended: Vision Meeting: [PROJECT_NAME]"
- User explicitly requests: "end meeting"
- System switches back to regular PM
- Other personas re-enabled

## Best Practices

### For Users
1. **Answer questions in any order** - Sarah adapts to your flow
2. **Provide details incrementally** - No need to answer everything at once
3. **Ask for clarification** - Sarah will explain or rephrase questions
4. **Review summaries** - Sarah recaps periodically; confirm or correct
5. **Save when ready** - Approve final version or save as draft

### For Developers
1. **Keep system prompt focused** - Sarah has one job: facilitate vision creation
2. **Leverage injected context** - Vision docs persist across turns
3. **Trust the recaps** - Sarah handles limited history gracefully
4. **Monitor token usage** - Vision meetings have low overhead (~5-8KB)
5. **Test with realistic conversations** - Not just short "test 1, test 2" messages

## Troubleshooting

### Sarah Repeats Questions
**Cause**: System prompt says "ask the structured questions"
**Fix**: Prompt now clarifies system already showed questions; Sarah guides and refines

### Sarah Loses Context
**Cause**: Chat history limited to 9-10 turns
**Fix**: Sarah now recaps periodically to keep critical info fresh

### Vision Not Saving
**Cause**: Payload format error (escaping quotes, wrapping in string)
**Fix**: Prompt includes CRITICAL warning about JSON object format

### Meeting Won't End
**Cause**: Sarah doesn't announce meeting end
**Fix**: Prompt clarifies when and how to end meetings

## Related Files
- `config_personas.json` - VISION_PM system prompt
- `development/src/streaming.py` - Meeting detection and solo mode logic
- `development/src/static/index.html` - Meeting UI and persona switching
- `docs/chat-history-limits.md` - Chat history management details
- `docs/architecture.md` - Overall system architecture

## Future Enhancements

### Potential Improvements
1. **Longer history for Vision Meetings** - Increase limit to 30-40 messages since overhead is low
2. **Template library** - Pre-built vision templates for common project types
3. **Collaborative editing** - Multiple users working on same vision
4. **Version history** - Track changes to vision documents over time
5. **Export formats** - PDF, Markdown, or other formats for sharing

### Why Current Approach Works
- **Simple**: One persona, one job, clear workflow
- **Focused**: Solo mode eliminates distractions
- **Flexible**: Users can answer in any order
- **Graceful**: Handles history limits through recaps
- **Effective**: 9-10 turns sufficient for most vision creation workflows

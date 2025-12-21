# Chat History Management

## Overview
The application maintains a sliding window of chat history to manage token limits and costs.

## Technical Details

### Frontend (index.html)
- **Storage**: `chatHistory` array stores conversation messages
- **Limit**: 20 messages maximum in array
- **Sent to Backend**: 19 messages (uses `.slice(0, -1)` to exclude current message)
- **Implementation**: Lines 1356-1368, 1400

```javascript
// Chat history storage
let chatHistory = [];

function addToChatHistory(role, content) {
    chatHistory.push({
        role: role,
        content: content
    });
    
    // Keep only last 20 messages to avoid token limits
    if (chatHistory.length > 20) {
        chatHistory = chatHistory.slice(-20);
    }
}

// When sending to backend
chat_history: chatHistory.slice(0, -1) // Send history without current message
```

### Backend (streaming.py)
- **Receives**: Up to 19 messages from frontend
- **Logging**: Added INFO level logging to track history count (line 93)
- **No server-side limit**: Backend uses whatever frontend sends

```python
# Log chat history count at INFO level for easy verification
logger.info(f"📊 Chat history: {len(chat_history)} messages ({len(chat_history)//2} turns)")
```

## Practical Impact by Meeting Type

### Vision Meetings (Solo Mode)
- **Typical capacity**: 9-12 turns
- **Why**: 1 user message + 1 Sarah response per turn = 2 messages/turn
- **Calculation**: 19 messages ÷ 2 = ~9.5 turns
- **Actual range**: Varies based on message length
- **Testing confirmed**: At turn 12-14, earliest messages (turn 1-2) fall out of history

### Full Team Conversations
- **Typical capacity**: 5-6 turns
- **Why**: 1 user message + 4 persona responses per turn = 5 messages/turn
- **Calculation**: 19 messages ÷ 5 = ~3.8 turns
- **Actual range**: Varies based on response patterns and which personas respond

### Requirements Meetings
- **Typical capacity**: 5-7 turns
- **Additional overhead**: Vision doc + Backlog CSV injected as context
- **Token budget**: More constrained due to injected documents
- **Note**: Injected context does NOT count against the 19-message history limit

## Context Management Strategy

### Vision PM Persona
Added explicit context management guidance (commit f4ab8f6):
- **Awareness**: Knows about 9-10 turn conversation limit
- **Strategy**: Periodically summarizes progress naturally
- **Examples**:
  - "So far we have: Project (BrightHR), Problem (attendance tracking), Users (HR managers). What about key features?"
  - "Let me confirm what we have: [brief summary]. Anything to add or change?"
  - "We've covered: [list]. Still need: [missing items]."
- **Purpose**: Dual benefit - refresh context + show user progress
- **Implementation**: CONTEXT MANAGEMENT section in system prompt

### How Personas Handle History Limits

**Graceful Degradation**:
- When early messages fall out of history, personas don't fail
- They use their own recaps and summaries to maintain continuity
- They offer to retrieve specifics if user requests: "If there's something specific from earlier you'd like me to pull up or clarify, just let me know!"

**Injected Context Persistence**:
- Vision documents persist across all turns (injected separately)
- Backlog data persists across all turns (injected separately)
- These provide stable project context independent of chat history

### Best Practices

1. **Keep messages focused**: Shorter exchanges = more turns in history
2. **Leverage recaps**: Personas summarize to maintain continuity
3. **Use injected context**: Vision docs, backlog data persist across turns
4. **Monitor token usage**: Check logs for `tokens_in` to track context size
5. **Don't rely on deep history**: Design conversations to work within 9-10 turn window

## Debugging Chat History

### Viewing History Count
The application logs chat history count at INFO level:
```
📊 Chat history: 19 messages (9 turns)
```

### Log Location
- **Development**: `development/src/logs/app.jsonl`
- **Format**: JSONL (one JSON object per line)
- **Parsing**: Use `jq` or Python's `json` module to parse

### Testing History Limits

To test how many turns are retained:

1. Start a Vision Meeting: `"sarah start a vision meeting"`
2. Send numbered test messages: `"test 1"`, `"test 2"`, etc.
3. Monitor logs for history count:
   ```bash
   tail -f development/src/logs/app.jsonl | grep "Chat history"
   ```
4. At turn 12+, ask Sarah what she can see from early messages:
   ```
   "Sarah, can you still see my first test message directly, or only through your recaps?"
   ```
5. Expected: She should acknowledge she no longer has direct access to earliest messages

### Expected Behavior
- History caps at 19 messages sent to backend (20 in frontend array)
- Sliding window drops oldest messages first
- Personas handle gracefully via recaps and summaries
- Injected context (vision docs, backlog) persists independently

### Example Test Results (2025-10-24)

**Vision Meeting Test**:
- Turn 1: 0 messages
- Turn 2: 2 messages
- Turn 3: 4 messages
- ...
- Turn 12: 19 messages (capped)
- Turn 14: 19 messages (still capped)

**Sarah's Response at Turn 14**:
> "I'm not pulling the very earliest bits directly anymore; it's all through the recaps and key threads I've been summarizing to keep everything fresh and focused as we chat."

**Conclusion**: Working as designed. Sarah gracefully handles missing history by maintaining recaps.

## Future Considerations

### Potential Enhancements
1. **Configurable limits per persona**: Vision meetings could have higher limits (30-40 messages) since they have less overhead
2. **Smart summarization**: Automatically summarize and compress old messages instead of dropping them
3. **Persistent conversation storage**: Store full conversation in database, retrieve relevant portions as needed
4. **User control**: Allow users to adjust history limit in settings

### Why Current Approach Works
- **Simple**: Easy to understand and debug
- **Predictable**: Fixed limit prevents token budget surprises
- **Efficient**: Minimal overhead, no complex summarization logic
- **Sufficient**: 9-10 turns is adequate for most Vision Meeting workflows
- **Graceful**: Personas handle limits naturally through recaps

## Related Files
- `development/src/static/index.html` - Frontend history management (lines 1356-1368, 1400)
- `development/src/streaming.py` - Backend history logging (line 93)
- `config_personas.json` - VISION_PM context management guidance
- `docs/personas/vision-pm.md` - Vision PM persona documentation

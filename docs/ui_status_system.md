# UI Status System - Vision & Requirements Meetings

## Overview

The AI-DIY status system provides real-time visual feedback during Vision and Requirements meetings through a progressive disclosure pattern. Users always know what's happening, from initial processing through content generation to completion.

This document covers the technical implementation of the status display system introduced in v1.2.0.

---

## Status Flow

### 1. Initial State: "Thinking..."

**When**: Immediately when user sends a message to VISION_PM or REQUIREMENTS_PM

**Display**:
- Location: Blue status bar (bottom-right, fixed position)
- Content: Animated dots (• • •) + "Thinking..." text
- Purpose: Indicates LLM is consuming context and processing prompts

**Duration**: ~0.5-1 second (until first progress update arrives)

**Implementation**:
```javascript
showThinkingStatus();  // Called from streamChat()
```

---

### 2. Active Generation: Budget Display

**When**: First progress update arrives from backend (~0.5-1s after start)

**Display**:
- Location: Same blue status bar (seamless transition)
- Content:
  - Animated dots (• • •) - continuous activity indicator
  - Time: `Xs / Ys` (current / budget)
  - Tokens: `X.XK / YK` (current / max)
  - Progress bar (fills based on time percentage)
- Purpose: Shows real-time resource consumption

**Updates**: Every ~1 second during generation

**Implementation**:
```javascript
// Progress handler detects thinking-status and upgrades
if (thinkingStatus && data.progress) {
    showBudgetProgress();  // Replaces thinking status
}
```

---

### 3. Content Streaming

**When**: Concurrent with budget display updates

**Display**:
- Location: Chat messages area
- Content: Text appears word-by-word as LLM generates
- Purpose: Immediate feedback on what's being created

**Implementation**:
```javascript
// content_chunk events create/update streaming div
case 'content_chunk':
    streamingDiv.textContent += data.content;
```

---

### 4. Completion

**When**: LLM finishes generating response

**Display**:
- Budget display shows final statistics
- Progress bar set to 100%
- Status hides after 2 seconds
- Final formatted response remains in chat

**Implementation**:
```javascript
// Final response updates budget, then hides
setTimeout(() => hideLoading(), 2000);
```

---

## Technical Architecture

### Frontend Components

**Status Display Elements**:
- `#loadingOverlay` - Blue status bar container
- `.thinking-status` - Initial thinking state
- `.budget-progress-overlay` - Budget display state
- `.thinking-dots` - Animated activity indicator

**Event Handlers**:
- `showThinkingStatus()` - Initial state
- `showBudgetProgress()` - Upgrade to budget display
- `handleStreamEvent('progress')` - Update budget stats
- `handleStreamEvent('content_chunk')` - Stream content
- `handleStreamEvent('persona_response')` - Final response

### Backend Components

**Progress Events** (`ai_gateway.py`):
```python
yield {
    "type": "progress",
    "elapsed_seconds": round(elapsed, 1),
    "budget_seconds": total_budget,
    "tokens_out": len(content.split()),
    "tokens_max": max_tokens,
    "model": model
}
```

**Content Chunks** (`ai_gateway.py`):
```python
if should_stream_content:  # VISION_PM or REQUIREMENTS_PM
    yield {
        "type": "content_chunk",
        "content": content_chunk
    }
```

**Event Forwarding** (`streaming.py`):
- Forwards progress events only for VISION_PM/REQUIREMENTS_PM
- Forwards content_chunk events only for VISION_PM/REQUIREMENTS_PM
- Regular personas use standard thinking banner

---

## Design Decisions

### Why Progressive Disclosure?

**Problem**: Showing full budget display immediately with placeholder values (`--s / --s`) was confusing and looked broken.

**Solution**: Start with simple "Thinking..." state, upgrade to detailed budget display only when real data arrives.

**Benefits**:
- No confusing placeholders
- Clear progression of states
- Smooth user experience
- Generic messaging works for all interactions

### Why Separate Vision/Requirements Status?

**Problem**: Regular personas (Alex, Jordan, Mike) don't need budget tracking, only Vision/Requirements PM does.

**Solution**: Detect persona type and show appropriate status:
- Vision/Requirements: Progressive status → budget display
- Other personas: Standard "AI is thinking..." or "AI Team is collaborating..."

**Benefits**:
- Budget display only where relevant
- No performance overhead for regular personas
- Cleaner UX for different interaction types

### Why Animated Dots Throughout?

**Problem**: Static displays don't show activity during idle periods (e.g., waiting for first progress update).

**Solution**: Animated dots (• • •) appear in both thinking state and budget display header.

**Benefits**:
- Continuous activity indicator
- User knows system is working even when stats aren't updating
- Consistent visual language across states

---

## CSS Styling

### Thinking Status
```css
.thinking-status {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
}

.thinking-status .thinking-text {
    color: white;
    font-size: 14px;
    font-weight: 500;
}
```

### Budget Display
```css
.budget-progress-overlay {
    display: flex;
    align-items: center;
    gap: 12px;
    color: white;
    font-size: 13px;
}

.budget-progress-bar {
    width: 100px;
    height: 4px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
}

.budget-progress-fill {
    height: 100%;
    background: white;
    transition: width 0.3s ease;
}
```

### Animated Dots
```css
.thinking-dots span {
    width: 8px;
    height: 8px;
    background: white;
    border-radius: 50%;
    animation: thinking-pulse 1.4s infinite ease-in-out;
}

.thinking-dots span:nth-child(1) { animation-delay: -0.32s; }
.thinking-dots span:nth-child(2) { animation-delay: -0.16s; }
.thinking-dots span:nth-child(3) { animation-delay: 0s; }
```

---

## Implementation Files

### Frontend (index.html)

**Status Functions**:
- `showThinkingStatus()` - Lines 1873-1894
- `showBudgetProgress()` - Lines 1896-1918
- `hideLoading()` - Lines 1916-1931

**Event Handlers**:
- `handleStreamEvent('progress')` - Lines 1489-1540
- `handleStreamEvent('content_chunk')` - Lines 1468-1488
- `handleStreamEvent('persona_response')` - Lines 1535-1614

**CSS Styles**:
- `.thinking-status` - Lines 860-871
- `.budget-progress-overlay` - Lines 838-902
- `.thinking-dots` - Lines 446-462

### Backend (ai_gateway.py)

**Progress Generation**:
- Lines 334-346: Yield progress updates every ~1 second
- Lines 269-303: Detect Vision/Requirements and enable streaming

**Content Streaming**:
- Lines 294-303: Yield content_chunk events for word-by-word streaming

### Backend (streaming.py)

**Event Forwarding**:
- Lines 203-219: Forward progress events to frontend
- Lines 221-231: Forward content_chunk events to frontend

---

## Troubleshooting

### Budget Display Not Appearing

**Symptom**: Only "Thinking..." shows, never upgrades to budget display

**Cause**: Progress events not being sent from backend

**Fix**: 
1. Check that persona is VISION_PM or REQUIREMENTS_PM
2. Verify progress events are yielded in ai_gateway.py
3. Check browser console for progress event logs

### Budget Display Persists for Regular Personas

**Symptom**: Budget display appears for Alex, Jordan, Mike

**Cause**: Budget display HTML not cleaned up after Vision/Requirements meeting

**Fix**: `hideLoading()` now restores original bubble-loader HTML (fixed in v1.2.0)

### Content Not Streaming

**Symptom**: Full response drops in at once instead of word-by-word

**Cause**: content_chunk events not being generated or handled

**Fix**: 
1. Verify `should_stream_content` flag in ai_gateway.py
2. Check content_chunk handler in index.html
3. Verify streaming.py forwards content_chunk events

### JavaScript Variable Errors

**Symptom**: "Identifier 'streamingDiv' has already been declared"

**Cause**: Variable declared in multiple case blocks of same switch statement

**Fix**: Use different variable names in each case block (fixed in v1.2.0)

---

## Testing Checklist

When testing Vision/Requirements status display:

- [ ] "Thinking..." appears immediately when message sent
- [ ] Animated dots pulse continuously
- [ ] Budget display appears within 1 second
- [ ] Time counter increments (e.g., 1s → 2s → 3s)
- [ ] Token counter updates (e.g., 0.5K → 1.2K → 2.5K)
- [ ] Progress bar fills from left to right
- [ ] Content streams in word-by-word (not all at once)
- [ ] Budget display shows final stats at completion
- [ ] Status bar disappears after 2 seconds
- [ ] Final response remains in chat
- [ ] Regular personas (Alex, Jordan, Mike) don't show budget display
- [ ] Scribe status message appears and disappears correctly

---

## Future Enhancements

Potential improvements to consider:

1. **Configurable Budgets**: Allow per-meeting-type time/token budgets
2. **Budget Warnings**: Visual indicator when approaching limits (e.g., 80% consumed)
3. **Pause/Resume**: Allow user to pause generation if going off track
4. **Budget History**: Track and display budget usage trends over time
5. **Custom Status Messages**: Allow personas to send custom status updates
6. **Estimated Time Remaining**: Calculate and display ETA based on current rate
7. **Token Efficiency Metrics**: Show tokens per second generation rate

---

## Related Documentation

- [Vision Process](vision_process.md) - How Vision meetings work
- [Requirements Process](requirements_process.md) - How Requirements meetings work
- [Architecture Guide](../architect/architecture.md) - System architecture
- [README](../README.md) - Project overview and quick start

---

## Version History

### v1.2.0 (2025-10-20)
- Initial implementation of progressive status display
- Word-by-word content streaming for Vision/Requirements
- Real-time budget tracking with time/token metrics
- Animated thinking dots for continuous activity feedback
- Bug fixes for variable redeclaration and status persistence

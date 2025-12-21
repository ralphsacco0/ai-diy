# Frontend Persona Lifecycle

## Selector Pattern

Use consistent `data-persona` + `.persona-checkbox` pattern:

```javascript
// Get selected personas
function getSelectedPersonas() {
    const selected = [];
    document.querySelectorAll('.persona-checkbox:checked').forEach(checkbox => {
        const personaItem = checkbox.closest('.persona-item');
        selected.push(personaItem.dataset.persona);
    });
    return selected;
}

// Update persona state
function updatePersonaState(personaName, isChecked) {
    const personaItem = document.querySelector(`[data-persona="${personaName}"]`);
    if (personaItem) {
        const checkbox = personaItem.querySelector('.persona-checkbox');
        if (checkbox) {
            checkbox.checked = isChecked;
            personaItem.classList.toggle('selected', isChecked);
        }
    }
}
```

## Meeting Lifecycle

1. **Detection**: PM detects meeting trigger keywords
2. **Announcement**: PM announces with format `🎯 Starting [TYPE]: [NAME]`
3. **Persona Switch**: JavaScript switches from PM to specialized persona
4. **Meeting Active**: Specialized persona handles conversation
5. **End Detection**: Specialized persona announces `📝 Meeting ended: [TYPE]: [NAME]`
6. **Cleanup**: JavaScript switches back to PM, restores persona states

## Meeting Detection Pattern

```javascript
// In WebSocket message handler
if (data.persona === 'PM' && data.content.includes('🎯 Starting Vision Meeting:')) {
    detectAndHandleMeeting(data.content);
    disableOtherPersonas();
}

if (data.persona === 'VISION_PM' && data.content.includes('📝 Meeting ended:')) {
    endMeeting();
    restorePersonaStates();
}
```

## Change Checklist

When modifying persona functionality:

- [ ] Update HTML structure if needed
- [ ] Update ALL JavaScript functions that handle personas
- [ ] Update persona definitions in personas.md
- [ ] Test meeting start/end cycles
- [ ] Verify persona switching works correctly
- [ ] Check visual state updates (selected class)
- [ ] Ensure consistent selection method throughout

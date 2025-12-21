# Sprint Review Meeting - User Guide

## Overview

Sprint Review is where you test and validate completed work with Sarah (PM) and Alex (Developer). It's a natural, collaborative session - not a rigid checklist.

---

## Starting a Sprint Review

Say any of these:
- "start sprint review meeting"
- "start sprint review"
- "review the sprint"
- "demo the work"

**What happens**:
- Sarah announces the meeting and what was built
- Both Sarah and Alex are available to help
- You have full access to the generated code

---

## Working with Sarah (PM)

Sarah helps you understand what was built and manages the review process.

### What Sarah Can Do:

**Explain the Work**:
- "What did we build in this sprint?"
- "Tell me about US-001"
- "How does the auth system work?"

**Guide Testing**:
- "What should I test first?"
- "Where are the files located?"
- "How do I run the app?"

**Manage Scope**:
- Approves/rejects stories based on your feedback
- Keeps discussion focused on sprint scope
- Suggests adding new features to backlog

**Update Backlog**:
- Marks stories as Done or Rejected
- Records your feedback in notes

### Example Conversations:

```
You: "What did we build?"
Sarah: "We completed US-001 (Employee Directory) and US-006 (Auth). 
        The directory has search and filters. Auth uses JWT tokens with 
        login/logout. Want to start with one of these?"

You: "Let's test auth"
Sarah: "Great. The login page is at /login. Alex generated email/password 
        fields with validation. Try logging in and let me know if you find 
        any issues."
```

---

## Working with Alex (Developer)

Alex built the code and can help you understand, test, and debug it.

### What Alex Can Do:

**Explain Code**:
- "How does the login work?"
- "Show me the auth code"
- "What files did you create?"

**Explore Files**:
- "List the files in the project"
- "Show me the directory structure"
- "What's in the tests folder?"

**Run Commands**:
- "Run the app"
- "Run the tests"
- "Check if Flask is installed"

**Debug Issues**:
- "The login button doesn't work"
- "I'm getting a 404 error"
- "The search isn't returning results"

**Fix Bugs**:
- Investigates the issue
- Explains what's wrong
- Proposes a fix
- Applies the fix (with your approval)
- Verifies it works

### Example Conversations:

```
You: "The login button doesn't work"
Alex: "Let me check. [reads login.html, auth.py] 
       I see the issue - the form action is missing. The button click 
       isn't triggering the POST to /api/auth/login. Should I fix it?"

You: "Yes"
Alex: "Fixed. Added form action='/api/auth/login' to the form element. 
       Try logging in now."

You: "Works! Can you show me the auth code?"
Alex: "Sure. The auth logic is in /app/auth.py. It uses Flask-JWT-Extended 
       for token management. The login endpoint validates credentials against 
       the database and returns a JWT token. Want me to show you the specific 
       function?"
```

---

## Alex's Tools

Alex has powerful tools to work with the generated code:

### 1. Read Files
```
You: "Show me the login code"
Alex: [reads /app/auth.py and explains the implementation]
```

### 2. List Directories
```
You: "What files are in the project?"
Alex: [lists all files and folders]
```

### 3. Run Commands
```
You: "Run the tests"
Alex: [executes: pytest tests/]
      [shows output: 5 passed, 0 failed]
```

### 4. Modify Files
```
You: "Fix the validation error"
Alex: [proposes fix]
You: "Go ahead"
Alex: [applies fix using write_text]
```

---

## Natural Workflow

### 1. Understand What Was Built
```
You: "What's in this sprint?"
Sarah: "US-001 (Employee Directory) and US-006 (Auth)"
```

### 2. Test Each Story
```
You: "Let's test the employee directory"
Sarah: "It has a table view with search and filters. Try searching for an employee."
You: "The search doesn't work"
Alex: "Let me check... [investigates] Found it - the query filter has a typo..."
```

### 3. Fix Issues
```
Alex: "Should I fix the search filter?"
You: "Yes"
Alex: "Fixed. Try searching now."
You: "Works!"
```

### 4. Approve or Reject
```
You: "This looks good"
Sarah: "Great! I'll mark US-001 as Done. [updates backlog]"
```

### 5. Handle New Requests
```
You: "Can we add pagination?"
Sarah: "That's new scope - let's add it to the backlog for next sprint. 
        For this sprint, the directory meets the acceptance criteria."
```

---

## Long Conversations

Sprint Review uses **session management** to maintain context across long conversations.

### How It Works:

Every few turns, the system automatically saves a summary:
- Key points discussed
- Decisions made
- Pending items
- Files modified

This summary is injected into future turns, so Sarah and Alex remember everything even after 20+ turns.

### What This Means for You:

- **No repetition**: They remember what you've already discussed
- **Continuity**: Can debug complex issues over many turns
- **Context**: They know what's been tested, fixed, approved

### Example:

```
Turn 5: "The login works now"
Turn 15: "What did we fix earlier?"
Sarah: "We fixed the login button - it wasn't triggering the POST. 
        Alex added the form action in login.html."
```

---

## Scope Boundaries

### What's In Scope ✅

- **Bug fixes**: Fixing what was promised in the sprint
- **Clarifications**: Explaining how things work
- **Testing**: Verifying acceptance criteria
- **Minor improvements**: Small tweaks that preserve requirements

### What's Out of Scope ❌

- **New features**: Anything not in the sprint stories
- **Requirement changes**: Modifying acceptance criteria
- **Scope expansion**: Adding functionality beyond the sprint

### How It's Handled:

```
You: "Can we add a 'remember me' checkbox?"
Sarah: "That's new scope - let's add it to the backlog for next sprint."

You: "The login should also support Google OAuth"
Sarah: "That's a new feature. I'll add it as a new story in the backlog."
```

---

## Tips for Effective Reviews

### 1. Start Broad, Then Dive Deep
```
✅ "What did we build?" → "Tell me about auth" → "Show me the login code"
❌ "Show me line 45 of auth.py" (too specific too soon)
```

### 2. Test Before Asking for Changes
```
✅ Test the feature → Find issue → Ask Alex to fix
❌ Ask for changes without testing
```

### 3. Be Specific About Issues
```
✅ "The search returns no results when I search for 'John'"
❌ "The search doesn't work"
```

### 4. Let Sarah Handle Scope
```
✅ "Can we add pagination?" → Sarah: "Let's add to backlog"
❌ "Alex, add pagination" (bypasses scope control)
```

### 5. Use Natural Language
```
✅ "The login button doesn't work"
✅ "Show me the auth code"
✅ "Run the tests"
❌ "Execute function test_auth() in tests/test_auth.py"
```

---

## Ending the Meeting

When you're done reviewing all stories:

```
You: "That's everything"
Sarah: "Great! I've updated the backlog. US-001 is Done, US-006 is Done. 
        📝 Meeting ended: Sprint Review"
```

---

## Common Scenarios

### Scenario 1: Everything Works
```
You: "start sprint review"
Sarah: "We built US-001 and US-006. Want to test them?"
You: "Yes, let's test auth first"
[test auth - works]
You: "Looks good. What about the directory?"
[test directory - works]
You: "All good"
Sarah: "Perfect! Both stories approved. 📝 Meeting ended: Sprint Review"
```

### Scenario 2: Found a Bug
```
You: "The search doesn't work"
Alex: "Let me check... [investigates] Found the issue - query filter typo"
Alex: "Should I fix it?"
You: "Yes"
Alex: "Fixed. Try now."
You: "Works!"
Sarah: "Great! US-001 approved with fix."
```

### Scenario 3: Want New Feature
```
You: "Can we add export to CSV?"
Sarah: "That's new scope. I'll add it to the backlog as a new story for next sprint."
You: "Okay, the current features work fine"
Sarah: "Perfect! US-001 approved."
```

### Scenario 4: Long Debugging Session
```
Turn 1: "The login has issues"
Turn 5: [Fixed form action]
Turn 10: [Fixed validation]
Turn 15: [Fixed error handling]
Turn 20: "What have we fixed so far?"
Sarah: "We fixed three issues: form action, validation, and error handling. 
        All in auth.py. Login is now working correctly."
```

---

## Quick Reference

| I Want To... | Say This... |
|--------------|-------------|
| Start review | "start sprint review" |
| See what was built | "What did we build?" |
| Test a feature | "Let's test [feature]" |
| Report a bug | "[Describe the issue]" |
| See code | "Show me [file/function]" |
| Run tests | "Run the tests" |
| Fix a bug | "Can you fix [issue]?" |
| Add new feature | "Can we add [feature]?" |
| Approve story | "This looks good" |
| End meeting | "That's everything" |

---

## Need Help?

During the review, just ask:
- "How does this work?"
- "What should I test?"
- "Can you explain [concept]?"
- "Show me [code/file]"

Sarah and Alex are here to help you understand and validate the work!

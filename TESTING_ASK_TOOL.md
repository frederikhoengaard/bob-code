# Testing the AskUserQuestionTool

This guide shows you how to test the `ask_user_question` tool in Bob Code.

## How It Works

The `ask_user_question` tool allows Bob to pause execution and ask you questions when:
- Your request is ambiguous
- Multiple valid implementation approaches exist
- Bob needs clarification on your preferences

## Test Scenarios

### 1. **Ambiguous Feature Request**
Try asking Bob to add a feature without specifying the approach:

```
Add authentication to the app
```

**Expected behavior**: Bob should use `ask_user_question` to ask which authentication method you prefer (JWT, OAuth, sessions, API keys, etc.)

---

### 2. **Multiple Valid Approaches**
Ask for something that can be done in different ways:

```
Add caching to improve performance
```

**Expected behavior**: Bob should ask where to cache (Redis, in-memory, file-based, database, etc.)

---

### 3. **Missing Technical Details**
Request something without specifying key details:

```
Create a new API endpoint for user data
```

**Expected behavior**: Bob should ask about:
- HTTP method (GET, POST, PUT, DELETE)
- Authentication requirements
- Data format (JSON, XML, etc.)
- What user data to return

---

### 4. **Library/Tool Selection**
Ask Bob to add functionality that requires choosing a library:

```
Add date formatting to the application
```

**Expected behavior**: Bob should ask which library to use (datetime, dateutil, arrow, pendulum, etc.)

---

### 5. **Refactoring Without Direction**
Request a refactor without specifying goals:

```
Refactor the tool system
```

**Expected behavior**: Bob should ask what to optimize for:
- Performance
- Readability
- Modularity
- Maintainability
- Test coverage

---

### 6. **Very Vague Request**
Test with an extremely vague request:

```
Add a new feature
```

**Expected behavior**: Bob should ask what kind of feature you want to add.

---

### 7. **Direct Tool Test**
Explicitly ask Bob to use the tool:

```
Use the ask_user_question tool to ask me which testing framework I prefer for Python
```

**Expected behavior**: Bob should ask about testing frameworks with options like pytest, unittest, nose2, etc.

---

## How to Answer Questions

When Bob asks questions, you'll see:

```
============================================================
❓ Bob has questions for you:
============================================================

[Header Label]
Question text here?

  1. Option One
     Description of option one

  2. Option Two
     Description of option two

  3. Option Three
     Description of option three

(Select number or type custom answer)

Header Label ►
```

### Ways to Answer:

1. **Select by number**: Type `1`, `2`, or `3`
2. **Custom answer**: Type any text you want
3. **Multi-select** (when enabled): Type `1,2` or `1, 3`

The answer will be converted automatically:
- If you type `1`, Bob receives "Option One"
- If you type custom text, Bob receives exactly what you typed

---

## Testing the Full Flow

1. **Start Bob**: Run `make run`
2. **Enable tools**: Type `/enable file_operations` and `/enable shell_commands`
3. **Ask an ambiguous question**: Try one of the test scenarios above
4. **Wait for questions**: Bob will display questions in the conversation area
5. **Answer**: Type your answer (number or custom text) and press Enter
6. **Verify**: Bob should acknowledge your answer and continue with the task

---

## Expected Output Format

After you answer, Bob will show:

```
User's answers:

Header Label: Your Answer Here
```

And then continue with the implementation based on your answers.

---

## Troubleshooting

### Bob doesn't ask questions
- Make sure you're asking something ambiguous
- Try being more vague in your request
- Try the "Direct Tool Test" scenario to confirm the tool works

### Questions don't appear
- Check that tools are enabled (`/enable file_operations`)
- Ensure you're running the latest version with the tool registered

### Can't input answers
- Make sure the working indicator has paused
- Check that you see the `Header ►` prompt
- Try typing your answer and pressing Enter

### Bob makes assumptions instead of asking
- The LLM may sometimes choose to make reasonable assumptions
- Try a more ambiguous request
- Use the direct tool test to verify functionality

---

## Example Session

```
You: Add authentication to the app

Bob: 🔧 ask_user_question(...)

============================================================
❓ Bob has questions for you:
============================================================

[Auth Method]
Which authentication method would you like to use?

  1. JWT (JSON Web Tokens)
     Stateless token-based authentication, good for APIs

  2. OAuth 2.0
     Third-party authentication (Google, GitHub, etc.)

  3. Session-based
     Server-side sessions with cookies

  4. API Keys
     Simple key-based authentication for services

(Select number or type custom answer)

Auth Method ► 1

You: 1

============================================================

Bob: User's answers:

Auth Method: JWT (JSON Web Tokens)

Bob: I'll implement JWT authentication for the app. Let me start by...
[continues with implementation]
```

---

## Notes

- The tool is **not available to subagents** (only the main agent can ask questions)
- You can ask **1-4 questions** at a time
- Each question supports **2-4 options**
- Users can always provide custom text instead of selecting options
- The working indicator automatically pauses during questions

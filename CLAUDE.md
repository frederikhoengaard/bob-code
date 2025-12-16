# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Build & Run:**
```bash
make install      # Set up venv and install dependencies
make run          # Launch the TUI application
make format       # Format code with ruff
make lock         # Recompile requirements.lock from pyproject.toml
make clean        # Remove venv and lockfile
```

**Development:**
```bash
.venv/bin/python -m src.main              # Run directly
.venv/bin/ruff check src                  # Lint without fixing
.venv/bin/ruff format --check src         # Check formatting
```

**Testing Bob:**
- After starting with `make run`, use `/enable file_operations` and `/enable shell_commands` to activate tools
- Use `/model <name>` to switch LLM providers
- Use `/init` command to generate workspace documentation

## Architecture Overview

Bob Code is a TUI-based AI coding assistant with agentic tool-calling capabilities. The architecture is layered:

```
┌─────────────────────────────────────────────────────────────┐
│                    TUI (CodeAgentTUI)                       │
│  src/cli/interface.py - User interaction and display        │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                   Agent (CodeAgent)                          │
│  src/agent/core.py - Agentic loop and orchestration         │
└───┬─────────────────────┬─────────────────────┬─────────────┘
    │                     │                     │
┌───▼─────────┐  ┌────────▼────────┐  ┌────────▼──────────┐
│ Providers   │  │ Tools           │  │ Workspace         │
│ src/        │  │ src/tools/      │  │ src/workspace/    │
│ providers/  │  │                 │  │                   │
└─────────────┘  └─────────────────┘  └───────────────────┘
```

### Core Data Flow

**Agentic Loop** (src/agent/core.py:39-120):
1. User input → Add Message(role="user") to history
2. Build messages with system prompt prepended
3. LLM generates response (potentially with tool_calls)
4. If tool_calls present → ToolExecutor executes → Add tool result messages → Loop back to step 2
5. If no tool_calls → Return final response → Save conversation

**Maximum Iterations:** 10 (prevents infinite loops)

### Key Components

#### 1. CodeAgent (src/agent/core.py)
- Manages conversation as `Message` objects (src/providers/models.py)
- Implements agentic loop with tool execution
- Provides `chat()` (tool-enabled) and `stream_chat()` (streaming only, no tools)
- Callbacks: `on_conversation_update` (save), `on_tool_call` (display)

#### 2. LLM Providers (src/providers/)
All providers implement `LLMProvider` interface:
- `generate(messages, tools)` → Message with content/tool_calls
- `stream(messages)` → AsyncIterator[StreamChunk]
- Unified models: Message, ToolCall, FunctionCall (src/providers/models.py)

**Active providers:**
- OpenAI (src/providers/openai.py) - GPT models
- Azure OpenAI (src/providers/azure.py) - Azure-hosted GPT models

**Stub providers:** Anthropic, DeepSeek (not yet implemented)

#### 3. Tool System (src/tools/)
Permission-based tool execution:
- `BaseTool` (src/tools/base.py) - Abstract interface
- `ToolRegistry` (src/tools/registry.py) - Manages available tools
- `ToolExecutor` (src/tools/executor.py) - Enforces permissions, executes in parallel

**Built-in Tools:**
- `ReadTool` - Read file contents (respects .gitignore via pathspec)
- `WriteTool` - Create/overwrite files
- `EditTool` - Perform exact string replacements in files (requires reading first)
- `BashTool` - Execute shell commands with timeout (default 30s)
- `TaskTool` - Spawn specialized subagents (explore/plan)
- `AskUserQuestionTool` - Ask users questions during execution (1-4 questions with 2-4 options each)
- `SlashCommandTool` - Execute slash commands programmatically (e.g., /help, /model, /permissions)
- `EnterPlanModeTool` - Enter planning mode for complex tasks (requires user approval)
- `ExitPlanModeTool` - Exit planning mode and transition to implementation

#### 4. Subagent System (src/agent/subagent.py)
The `task` tool spawns specialized agents with focused capabilities:

**Explore agent** (read-only, fast):
- Tools: read, bash (ls/find/git only)
- Max iterations: 5
- System prompt: SYSTEM_PROMPT_EXPLORE
- Use for: finding files, understanding code structure, searching patterns

**Plan agent** (full access, thorough):
- Tools: read, write, edit, bash
- Max iterations: 15
- System prompt: SYSTEM_PROMPT_PLAN
- Use for: designing implementations, creating detailed plans, analyzing architecture

**Critical:** Subagents receive ONLY the task_prompt - no conversation history is shared. The parent agent controls what context to provide.

#### 5. System Prompts (src/prompts/system.py)
- `SYSTEM_PROMPT_BASIC` - Main agent (emphasizes using read tool, not bash cat/head/tail)
- `SYSTEM_PROMPT_EXPLORE` - Explore subagent (read-only, fast, parallel tool calls)
- `SYSTEM_PROMPT_PLAN` - Plan subagent (thorough planning, architecture design)

**Key guideline:** Always use `read` tool for file contents, NEVER bash commands (cat/head/tail). The read tool respects .gitignore and prevents token waste on .venv/__pycache__.

#### 6. Workspace Configuration (src/workspace/)
- `.bob/settings.json` - Model selection and tool permissions
- `.bob/conversations/` - Auto-saved conversation history with metadata
- WorkspaceConfig manages initialization and settings persistence

**Permission System:**
```python
class ToolPermissions:
    allow_file_operations: bool  # read/write tools
    allow_shell_commands: bool   # bash tool
    allow_network_access: bool   # future use
```

## Common Development Tasks

### Adding a New Tool

1. **Create tool class** in `src/tools/implementations/`:
```python
from src.tools.base import BaseTool

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "mytool"

    @property
    def description(self) -> str:
        return "Tool description for LLM"

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {...},
            "required": [...]
        }

    @property
    def required_permission(self) -> str | None:
        return "allow_file_operations"  # or None

    async def execute(self, **kwargs) -> str:
        # Implementation
        return "result"
```

2. **Export** in `src/tools/implementations/__init__.py`
3. **Register** in `src/cli/interface.py` (around line 71-78)
4. **Add permission** (if needed) to `ToolPermissions` in `src/workspace/config.py`

### Adding a New LLM Provider

1. **Implement** `LLMProvider` in `src/providers/newprovider.py`:
   - `generate(messages, tools)` - Convert to/from provider format, handle tool_calls
   - `stream(messages)` - Stream responses chunk by chunk
   - `_convert_messages()` - Map Message format to provider's API format

2. **Add models** to `LLM` enum in `src/providers/models.py`
3. **Export** in `src/providers/__init__.py`
4. **Update** `_create_provider()` in `src/cli/interface.py` to route to new provider

**Critical considerations:**
- Different providers have different tool calling formats (OpenAI: `tool_calls`, Anthropic: `tool_use` blocks)
- Some providers don't accept system messages in messages array (extract separately)
- Tool calling typically only works in non-streaming mode

### Adding a Slash Command

1. **Add to commands dict** in `src/cli/interface.py` `__init__()` (line ~91):
```python
self.commands = {
    "/mycommand": "Description of command",
    ...
}
```

2. **Implement handler** in `handle_command()` method (line ~714):
```python
elif cmd == "/mycommand":
    await self.append_output(f"{self.GRAY}Processing...\n")
    result = self._process_mycommand(args)
    await self.append_output(f"{result}\n{self.RESET}\n\n")
```

### Modifying System Prompts

Edit prompts in `src/prompts/system.py`. The main agent uses `SYSTEM_PROMPT_BASIC` by default.

For custom prompts, pass to CodeAgent constructor:
```python
agent = CodeAgent(
    provider,
    system_prompt=SYSTEM_PROMPT_CUSTOM,
    tool_registry=registry,
    tool_permissions=permissions
)
```

## Important Implementation Details

### EditTool and ReadTool Integration
The EditTool requires that files be read before editing:
- ReadTool tracks files that have been read in `_read_files` set
- EditTool receives a reference to ReadTool and calls `read_tool.has_read_file()` before editing
- This prevents editing files without understanding their current state
- Path normalization ensures different path representations (relative/absolute) are handled correctly
- Both tools are instantiated together in src/cli/interface.py:85-89

### AskUserQuestionTool Integration
The AskUserQuestionTool provides interactive questioning during agent execution:
- Receives `on_question_callback` pointing to TUI's `_on_user_question()` method
- When executed, displays questions in the conversation area and pauses agent execution
- Uses asyncio.Event to synchronize: tool waits for user input, `process_input()` detects pending question and sets event
- Supports 1-4 questions with 2-4 options each, users can select by number or provide custom text
- Automatically pauses/resumes working indicator during question flow
- NOT available to subagents (requires TUI callback which subagents don't have)
- System prompt encourages proactive use when requests are ambiguous
- See TESTING_ASK_TOOL.md for detailed testing scenarios

### SlashCommandTool Integration
The SlashCommandTool allows the agent to execute slash commands programmatically:
- Receives `command_handler` callback pointing to TUI's `_on_slash_command()` method
- Callback uses existing `handle_command()` logic and captures output by comparing conversation buffer before/after
- Can execute any registered slash command (e.g., /help, /model, /permissions, /enable, /disable)
- Useful for the agent to check current state or modify settings when needed
- Always available to main agent (no special permissions required)
- NOT available to subagents (requires TUI callback)

### Plan Mode Integration
Plan mode allows the agent to thoroughly explore and plan before implementation:
- **EnterPlanModeTool** requests user approval via `_on_enter_plan_mode()` callback
- User sees a prompt explaining plan mode and can approve/decline (yes/no)
- State tracked in `is_in_plan_mode` boolean flag
- When approved, agent enters planning phase with full tool access for exploration
- **ExitPlanModeTool** transitions out of plan mode via `_on_exit_plan_mode()` callback
  - ONLY for implementation tasks (writing code), NOT research tasks (understanding codebase)
  - Agent should present plan in conversation before calling this tool
  - Should use ask_user_question to clarify ambiguities before exiting
  - Examples: "implement feature X" (use tool) vs "understand component Y" (don't use - just research)
- Both tools use the same `pending_question_event` mechanism as AskUserQuestionTool
- Intended for complex tasks: multiple approaches, architectural decisions, large changes, unclear requirements
- NOT for simple tasks, small bugs, or obvious implementations
- NOT available to subagents (requires TUI callback)

### Tool Execution Flow
1. LLM returns tool_calls in response
2. ToolExecutor.execute_tool_calls() processes in parallel
3. For each call: lookup → check permission → parse args → execute → wrap result
4. ToolResult messages added to conversation history
5. Loop continues with tool results until LLM responds without tool_calls

### Conversation Persistence
- Auto-saves on every conversation update via `on_conversation_update` callback
- Format: JSON with metadata (started_at, last_message_at, message_count, model, title)
- Title extracted from first user message (max 100 chars)
- ConversationPersistence handles loading/saving (src/workspace/persistence.py)

### .gitignore Integration
ReadTool uses `pathspec` to parse .gitignore and automatically exclude files. This prevents wasting tokens reading .venv/, __pycache__/, node_modules/, etc.

Implementation: src/utils/gitignore.py creates PathSpec from .gitignore, used in ReadTool.execute()

### TUI Buffer Management
The conversation display uses a read-only TextArea. To append output:
1. Set `_conversation_read_only = False`
2. Modify buffer text
3. Set `_conversation_read_only = True`

Failure to toggle causes `EditReadOnlyBuffer` exception.

### Provider Selection Logic
In `_create_provider()` (src/cli/interface.py):
- If model starts with "gpt" → check for Azure env vars, else OpenAI
- Add similar checks for other providers based on model prefix

### Subagent Recursion Prevention
TaskTool checks `self.is_subagent` and returns error if true. CodeAgent receives `is_subagent=True` from SubagentFactory, preventing nested task calls.

## Code Style

**Linting:** Ruff (line-length 100, target py311)
**Selected lints:** E (pycodestyle), W (warnings), F (pyflakes), I (isort), B (bugbear), C4 (comprehensions), UP (pyupgrade)
**Format:** Double quotes, space indentation

Always run `make format` before committing.

## Project Structure

```
src/
├── main.py                          # Entry point
├── agent/
│   ├── core.py                      # CodeAgent (agentic loop)
│   └── subagent.py                  # SubagentFactory (explore/plan)
├── cli/
│   └── interface.py                 # CodeAgentTUI (TUI implementation)
├── providers/
│   ├── base.py                      # LLMProvider interface
│   ├── models.py                    # Message, ToolCall, LLM enum
│   ├── openai.py                    # OpenAI provider
│   ├── azure.py                     # Azure OpenAI provider
│   ├── anthropic.py                 # [Stub]
│   └── deepseek.py                  # [Stub]
├── tools/
│   ├── base.py                      # BaseTool interface
│   ├── registry.py                  # ToolRegistry
│   ├── executor.py                  # ToolExecutor
│   └── implementations/
│       ├── read.py                  # ReadTool (respects .gitignore)
│       ├── write.py                 # WriteTool
│       ├── edit.py                  # EditTool (exact string replacement)
│       ├── bash.py                  # BashTool
│       ├── task.py                  # TaskTool (subagent spawning)
│       ├── ask.py                   # AskUserQuestionTool (interactive questions)
│       ├── slash_command.py         # SlashCommandTool (programmatic slash commands)
│       ├── plan_mode.py             # EnterPlanModeTool (enter planning mode)
│       └── exit_plan_mode.py        # ExitPlanModeTool (exit planning mode)
├── workspace/
│   ├── config.py                    # WorkspaceConfig, ToolPermissions
│   └── persistence.py               # ConversationPersistence
├── prompts/
│   └── system.py                    # System prompts
└── utils/
    └── gitignore.py                 # .gitignore parsing for ReadTool
```

## Common Pitfalls

1. **Forgetting to enable permissions:** Tools require explicit permission grants via `/enable` commands
2. **Using bash for file reading:** Always use `read` tool, not `bash cat/head/tail` (prompts enforce this)
3. **Buffer read-only errors:** Toggle `_conversation_read_only` around TUI buffer modifications
4. **Infinite loops:** CodeAgent has max_iterations=10 to prevent runaway tool calling
5. **Subagent recursion:** TaskTool prevents subagents from spawning additional subagents
6. **Missing tool registration:** New tools must be registered in TUI's `__init__` method
7. **Streaming with tools:** Tool calling only works in non-streaming mode (`chat()`, not `stream_chat()`)

# Bob Code

**Bob** is a Terminal User Interface (TUI) AI coding assistant that brings the power of multiple LLM providers directly into your terminal. With agentic tool-calling capabilities, Bob can read, write, and execute commands in your workspace autonomously.


## Features

- 🤖 **Agentic Tool Calling** - LLM autonomously uses tools (read, write, bash) to complete tasks
- 🔄 **Multiple LLM Providers** - OpenAI, Azure OpenAI, Anthropic, DeepSeek support
- 🎨 **Beautiful TUI** - Built with prompt_toolkit for a smooth interactive experience
- 💾 **Conversation Persistence** - Auto-saves conversations with metadata and browsing
- 🔒 **Permission System** - Granular control over file operations, shell commands, and network access
- ⚡ **Streaming Responses** - Character-by-character streaming with natural typing delays
- 📁 **Workspace Awareness** - Operates within workspace boundaries with `.bob/` configuration
- 🔧 **Extensible Architecture** - Easy to add new tools, commands, and providers

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bob-code.git
cd bob-code

# Install dependencies (creates venv and installs packages)
make install
```

### Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Add your API keys to `.env`:
```bash
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
```

### Running Bob

```bash
make run
```

### Basic Usage

Once Bob is running, you can:

- Type messages to chat with the AI
- Use slash commands (type `/` to see suggestions)
- Enable tools with `/enable file_operations` and `/enable shell_commands`
- Switch models with `/model <model_name>`
- Browse previous conversations with `/conversations`

### Essential Commands

```bash
make install     # Create venv, compile dependencies, install packages
make run         # Run the TUI application
make format      # Format code with ruff
make clean       # Remove .venv and requirements.lock
```

## Architecture Overview

Bob is built with a modular architecture separating concerns across several key components:

```
┌─────────────────────────────────────────────────────────────┐
│                        TUI Layer                            │
│                  (CodeAgentTUI)                             │
│  - Input handling  - Display  - Commands  - Streaming      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                     Agent Layer                             │
│                    (CodeAgent)                              │
│  - Conversation state  - Agentic loop  - Tool coordination │
└─────┬──────────────────────────────┬─────────────────────┬──┘
      │                              │                     │
┌─────▼──────────┐        ┌──────────▼─────────┐    ┌─────▼──────┐
│   Providers    │        │    Tool System     │    │ Workspace  │
│  - OpenAI      │        │  - Registry        │    │  - Config  │
│  - Azure       │        │  - Executor        │    │  - Persist │
│  - Anthropic   │        │  - Permissions     │    │  - Settings│
│  - DeepSeek    │        │  - Read/Write/Bash │    │            │
└────────────────┘        └────────────────────┘    └────────────┘
```

### Core Components

#### 1. **CodeAgent** (`src/agent/core.py`)
The main orchestrator that:
- Manages conversation history as `Message` objects
- Implements the agentic loop (max 10 iterations)
- Coordinates between LLM providers and tool execution
- Provides both streaming and non-streaming interfaces

#### 2. **LLM Providers** (`src/providers/`)
Abstract provider system normalizing different LLM APIs:
- **Base Interface**: `LLMProvider` with `generate()` and `stream()` methods
- **Unified Models**: All providers convert to/from `Message` and `StreamChunk`
- **Tool Support**: Providers handle tool call formatting and parsing
- **Implementations**: OpenAI, Azure OpenAI (Anthropic/DeepSeek in progress)

#### 3. **Tool System** (`src/tools/`)
Permission-based tool execution framework:
- **BaseTool**: Abstract base class for all tools
- **ToolRegistry**: Manages available tools
- **ToolExecutor**: Enforces permissions and executes tools in parallel
- **Built-in Tools**: Read (file operations), Write (file creation), Bash (shell commands)

#### 4. **TUI Interface** (`src/cli/interface.py`)
Interactive terminal interface with:
- Conversation display with ANSI color support
- Input field with command suggestions
- Conversation browser with metadata
- Working indicator with pulsating counter
- Keyboard shortcuts (Ctrl+C to exit, Enter to submit)

#### 5. **Workspace Configuration** (`src/workspace/`)
Manages workspace-specific settings:
- `.bob/settings.json` - Model selection and permissions
- `.bob/conversations/` - Auto-saved conversation history
- Security boundaries preventing directory traversal

## Extending Bob

### Adding New Tools

Tools are the primary way Bob interacts with the environment. Here's how to add a new tool:

#### Step 1: Create Tool Implementation

Create a new file in `src/tools/implementations/` (e.g., `mytool.py`):

```python
from src.tools.base import BaseTool

class MyTool(BaseTool):
    """Description of what this tool does"""

    @property
    def name(self) -> str:
        """Tool name used in LLM function calling"""
        return "mytool"

    @property
    def description(self) -> str:
        """Description shown to LLM"""
        return "Does something useful with the provided parameters"

    @property
    def parameters_schema(self) -> dict:
        """JSON Schema for tool parameters"""
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of param1"
                },
                "param2": {
                    "type": "integer",
                    "description": "Description of param2",
                    "default": 10
                }
            },
            "required": ["param1"]
        }

    @property
    def required_permission(self) -> str | None:
        """Permission required to use this tool (or None)"""
        return "allow_custom_operations"  # Or None if no permission needed

    async def execute(self, **kwargs) -> str:
        """
        Execute the tool with validated parameters

        Args:
            **kwargs: Parameters matching the schema

        Returns:
            String result to send back to LLM
        """
        param1 = kwargs.get("param1")
        param2 = kwargs.get("param2", 10)

        # Implement your tool logic here
        result = f"Processed {param1} with {param2}"

        return result
```

#### Step 2: Export the Tool

Add your tool to `src/tools/implementations/__init__.py`:

```python
from .bash import BashTool
from .read import ReadTool
from .write import WriteTool
from .mytool import MyTool  # Add this

__all__ = ["ReadTool", "WriteTool", "BashTool", "MyTool"]
```

#### Step 3: Register the Tool

In `src/cli/interface.py`, register your tool in the `__init__` method (around line 71-78):

```python
# Initialize tool registry
from src.tools.registry import ToolRegistry
from src.tools.implementations import ReadTool, WriteTool, BashTool, MyTool

self.tool_registry = ToolRegistry()
self.tool_registry.register(ReadTool())
self.tool_registry.register(WriteTool())
self.tool_registry.register(BashTool())
self.tool_registry.register(MyTool())  # Add this
```

#### Step 4: (Optional) Add Permission

If your tool requires a new permission:

1. Add to `ToolPermissions` in `src/workspace/config.py`:
```python
class ToolPermissions(BaseModel):
    allow_file_operations: bool = False
    allow_shell_commands: bool = False
    allow_network_access: bool = False
    allow_custom_operations: bool = False  # Add this
```

2. Add enable/disable handlers in `src/cli/interface.py` (around lines 386-456):
```python
PERMISSION_MAP = {
    "file_operations": "allow_file_operations",
    "shell_commands": "allow_shell_commands",
    "network_access": "allow_network_access",
    "custom_operations": "allow_custom_operations",  # Add this
}
```

### Adding Slash Commands

Slash commands provide quick access to functionality without going through the LLM.

#### Step 1: Define Command

In `src/cli/interface.py`, add your command to the `commands` dict in `__init__` (around line 91-103):

```python
self.commands = {
    "/clear": "Clear conversation history",
    "/conversations": "Browse previous conversations",
    "/help": "Show available commands",
    "/exit": "Exit Bob",
    "/quit": "Exit Bob",
    "/model": "Show current model or switch model",
    "/models": "List all available models",
    "/init": "Generate BOB.md workspace documentation",
    "/permissions": "Show current tool permissions",
    "/enable": "Enable a permission (file_operations, shell_commands, network_access)",
    "/disable": "Disable a permission",
    "/mycommand": "Description of my command",  # Add this
}
```

#### Step 2: Implement Handler

Add command handling logic in the `handle_command()` method (around lines 714-845):

```python
async def handle_command(self, cmd_line: str):
    """Handle slash commands"""
    parts = cmd_line.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    # ... existing command handlers ...

    elif cmd == "/mycommand":
        await self.append_output(f"{self.GRAY}Processing mycommand...\n")

        # Your command logic here
        # Can access self.agent, self.workspace_config, etc.
        result = self._process_mycommand(args)

        await self.append_output(f"{result}\n{self.RESET}\n\n")

    else:
        await self.append_output(f"{self.RED}Unknown command: {cmd}{self.RESET}\n\n")
```

#### Step 3: (Optional) Add Helper Method

For complex commands, add a helper method:

```python
def _process_mycommand(self, args: str) -> str:
    """Process mycommand with given arguments"""
    # Implementation
    return "Command result"
```

### Adding LLM Providers

Bob supports multiple LLM providers through a unified interface.

#### Step 1: Create Provider Implementation

Create a new file in `src/providers/` (e.g., `newprovider.py`):

```python
import os
from typing import AsyncIterator
from src.providers.base import LLMProvider
from src.providers.models import Message, StreamChunk, LLM, ToolCall, FunctionCall

class NewProvider(LLMProvider):
    """Provider for New LLM API"""

    def __init__(self, model: LLM, api_key: str | None = None):
        """Initialize provider with API key from environment or parameter"""
        super().__init__(
            model,
            api_key or os.getenv("NEW_API_KEY")
        )

        # Initialize your API client
        from new_sdk import AsyncNewClient
        self.client = AsyncNewClient(api_key=self.api_key)

    async def generate(
        self,
        messages: list[Message],
        tools: list | None = None,
        **kwargs
    ) -> Message:
        """
        Generate a complete response (supports tool calling)

        Args:
            messages: Conversation history (includes system prompt)
            tools: Optional list of ToolDefinition objects
            **kwargs: Additional provider-specific parameters

        Returns:
            Message object with content and/or tool_calls
        """
        # Convert unified Message format to provider's format
        provider_messages = self._convert_messages(messages)

        # Prepare API call parameters
        params = {
            "model": self.model.value,
            "messages": provider_messages,
            **kwargs
        }

        # Add tools if provided
        if tools:
            params["tools"] = [t.model_dump() for t in tools]

        # Call API
        response = await self.client.chat.completions.create(**params)

        # Extract message
        message = response.choices[0].message

        # Convert to unified Message format
        result = Message(
            role="assistant",
            content=message.content
        )

        # Parse tool calls if present
        if hasattr(message, "tool_calls") and message.tool_calls:
            result.tool_calls = [
                ToolCall(
                    id=tc.id,
                    type="function",
                    function=FunctionCall(
                        name=tc.function.name,
                        arguments=tc.function.arguments
                    )
                )
                for tc in message.tool_calls
            ]

        return result

    async def stream(
        self,
        messages: list[Message],
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream response chunk by chunk

        Args:
            messages: Conversation history
            **kwargs: Additional parameters

        Yields:
            StreamChunk objects with content
        """
        provider_messages = self._convert_messages(messages)

        params = {
            "model": self.model.value,
            "messages": provider_messages,
            "stream": True,
            **kwargs
        }

        stream = await self.client.chat.completions.create(**params)

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield StreamChunk(
                    content=chunk.choices[0].delta.content,
                    finish_reason=chunk.choices[0].finish_reason
                )

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert unified Message format to provider's format"""
        result = []

        for msg in messages:
            provider_msg = {"role": msg.role}

            # Handle different message types
            if msg.role == "tool":
                # Tool result message
                provider_msg["tool_call_id"] = msg.tool_call_id
                provider_msg["content"] = msg.content
                provider_msg["name"] = msg.name
            elif msg.tool_calls:
                # Assistant message with tool calls
                provider_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in msg.tool_calls
                ]
                if msg.content:
                    provider_msg["content"] = msg.content
            else:
                # Regular message
                provider_msg["content"] = msg.content

            result.append(provider_msg)

        return result
```

#### Step 2: Add Model Enums

In `src/providers/models.py`, add your models to the `LLM` enum:

```python
class LLM(StrEnum):
    # ... existing models ...

    # New Provider
    NEW_MODEL_1 = "new-model-1"
    NEW_MODEL_2 = "new-model-2"
```

#### Step 3: Export Provider

Add to `src/providers/__init__.py`:

```python
from .azure import AzureOpenAIProvider
from .openai import OpenAIProvider
from .newprovider import NewProvider

__all__ = [
    "LLMProvider",
    "AzureOpenAIProvider",
    "OpenAIProvider",
    "NewProvider",
]
```

#### Step 4: Update TUI to Support Provider

In `src/cli/interface.py`, add logic to select your provider based on model:

```python
def _create_provider(self, model: LLM) -> LLMProvider:
    """Create appropriate provider for the given model"""
    from src.providers import AzureOpenAIProvider, OpenAIProvider, NewProvider

    if model.value.startswith("gpt"):
        # OpenAI or Azure
        if os.getenv("AZURE_OPENAI_API_KEY"):
            return AzureOpenAIProvider(model)
        return OpenAIProvider(model)
    elif model.value.startswith("new-model"):  # Add this
        return NewProvider(model)
    else:
        raise ValueError(f"Unknown model: {model}")
```

#### Key Considerations for Providers

1. **Tool Calling Format**: Different providers have different tool calling formats. OpenAI uses `tool_calls`, Anthropic uses `tool_use` blocks. You'll need to convert to the unified `ToolCall` format.

2. **System Prompt Handling**: Some providers (like Anthropic) don't accept system messages in the messages array. You may need to extract and handle separately.

3. **Streaming vs Non-Streaming**: Tool calls typically only work in non-streaming mode. Plan accordingly.

4. **Error Handling**: Wrap API calls in try/except blocks and return meaningful error messages.

5. **Rate Limiting**: Consider implementing retry logic with exponential backoff.

6. **Token Limits**: Be aware of context window limits for each model.

### Adding Custom Permissions

To add granular control over new functionality:

#### Step 1: Extend ToolPermissions

In `src/workspace/config.py`:

```python
class ToolPermissions(BaseModel):
    allow_file_operations: bool = False
    allow_shell_commands: bool = False
    allow_network_access: bool = False
    allow_database_access: bool = False  # Add custom permission
    allow_api_calls: bool = False  # Add custom permission
```

#### Step 2: Add to Permission Commands

In `src/cli/interface.py`, update the `PERMISSION_MAP` (around line 390):

```python
PERMISSION_MAP = {
    "file_operations": "allow_file_operations",
    "shell_commands": "allow_shell_commands",
    "network_access": "allow_network_access",
    "database_access": "allow_database_access",  # Add
    "api_calls": "allow_api_calls",  # Add
}
```

#### Step 3: Use in Tools

Reference the permission in your tool's `required_permission` property:

```python
class DatabaseTool(BaseTool):
    @property
    def required_permission(self) -> str | None:
        return "allow_database_access"
```

### Customizing System Prompts

System prompts guide the LLM's behavior. Bob supports multiple prompt strategies:

#### Editing Existing Prompts

In `src/prompts/system.py`:

```python
SYSTEM_PROMPT_BASIC = """You are Bob Code, a helpful AI coding assistant...

## Your Capabilities
...

## Custom Instructions
Add your custom instructions here
"""
```

#### Adding New Prompt Variants

```python
SYSTEM_PROMPT_CUSTOM = """You are Bob Code in custom mode...
"""
```

Then use when creating the agent:

```python
from src.prompts import SYSTEM_PROMPT_CUSTOM

self.agent = CodeAgent(
    provider,
    system_prompt=SYSTEM_PROMPT_CUSTOM,
    tool_registry=self.tool_registry,
    tool_permissions=permissions
)
```

## Data Flow

Understanding how data flows through Bob helps with debugging and extending functionality:

### Conversation Flow

```
1. User Input (TUI)
   ↓
2. CodeAgentTUI.process_input()
   - Append "> {user_input}" to display
   ↓
3. CodeAgent.chat(user_input)
   - Add Message(role="user") to history
   - Prepend SYSTEM_PROMPT
   ↓
4. Provider.generate(messages, tools)
   - Convert to provider format
   - Call LLM API
   ↓
5. Check Response
   ├─ Has tool_calls? → Execute tools → Loop back to step 4
   └─ No tool_calls? → Continue to step 6
   ↓
6. Add Message(role="assistant") to history
   ↓
7. on_conversation_update callback
   ↓
8. ConversationPersistence.save_conversation()
   ↓
9. Display in TUI
```

### Tool Execution Flow

```
1. LLM Response contains tool_calls
   ↓
2. ToolExecutor.execute_tool_calls()
   ↓
3. For each tool_call:
   a. Lookup in ToolRegistry
   b. Check ToolPermissions
   c. Parse JSON arguments
   d. Execute Tool.execute(**kwargs)
   e. Wrap result in ToolResult
   ↓
4. Add ToolResult messages to history
   ↓
5. Continue agentic loop
```

## Configuration

### Workspace Structure

```
your-project/
├── .bob/                           # Created on first run
│   ├── settings.json              # Model & permissions
│   └── conversations/             # Auto-saved chats
│       ├── conversation_YYYYMMDD_HHMMSS.json
│       └── conversation_YYYYMMDD_HHMMSS.json
├── .env                           # API keys (gitignored)
└── [your project files]
```

### Settings File Format

`.bob/settings.json`:
```json
{
  "model": "gpt-4o-mini",
  "permissions": {
    "allow_file_operations": true,
    "allow_shell_commands": false,
    "allow_network_access": false
  },
  "created_at": "2025-02-07T15:30:45",
  "last_updated": "2025-02-07T16:45:12"
}
```

### Conversation File Format

`.bob/conversations/conversation_*.json`:
```json
{
  "metadata": {
    "started_at": "2025-02-07T15:30:45",
    "last_message_at": "2025-02-07T15:45:12",
    "message_count": 10,
    "model": "gpt-4o-mini",
    "title": "Help me debug the authentication issue"
  },
  "messages": [
    {
      "role": "user",
      "content": "Help me debug the authentication issue"
    },
    {
      "role": "assistant",
      "content": "I'll help you debug that...",
      "tool_calls": [...]
    },
    {
      "role": "tool",
      "tool_call_id": "call_123",
      "name": "read",
      "content": "File contents..."
    }
  ]
}
```

## Development Workflow

### Code Style

Bob uses Ruff for linting and formatting:

```bash
# Auto-format code
make format

# Check for issues (manual)
.venv/bin/ruff check src
.venv/bin/ruff format --check src
```

**Configuration** (in `pyproject.toml`):
- Line length: 100
- Target: Python 3.11+
- Quote style: Double quotes
- Selected lints: pycodestyle, pyflakes, isort, flake8-bugbear, flake8-comprehensions, pyupgrade

### Testing

```bash
# Run tests (when implemented)
.venv/bin/pytest tests/

# Run specific test
.venv/bin/pytest tests/test_tools.py -v
```

### Debugging

Enable debug logging by modifying `src/main.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or use the Python debugger:

```python
import pdb; pdb.set_trace()
```

### Dependency Management

Bob uses `pip-tools` for deterministic dependency resolution:

```bash
# Add dependency to pyproject.toml, then:
make lock        # Update requirements.lock

# Install updated dependencies
make install
```

## Troubleshooting

### Common Issues

**Issue: `ImportError: cannot import name 'X' from 'Y'`**
- Solution: Check that all `__init__.py` files export the required classes

**Issue: Tools not being called by LLM**
- Solution: Ensure permissions are enabled with `/enable file_operations` and `/enable shell_commands`

**Issue: `EditReadOnlyBuffer` error**
- Solution: This is an internal error - ensure `_conversation_read_only` flag is toggled correctly around buffer writes

**Issue: Cannot copy text from conversation area**
- Solution: This is expected - `mouse_support=False` enables terminal-native selection with Cmd+C

**Issue: API key not found**
- Solution: Check `.env` file exists and contains the correct key variables

## Project Structure

```
bob-code/
├── src/
│   ├── main.py                    # Entry point
│   ├── agent/
│   │   └── core.py               # CodeAgent
│   ├── cli/
│   │   └── interface.py          # TUI implementation
│   ├── providers/
│   │   ├── base.py               # LLMProvider interface
│   │   ├── models.py             # Data models
│   │   ├── openai.py             # OpenAI provider
│   │   ├── azure.py              # Azure OpenAI provider
│   │   ├── anthropic.py          # [Stub]
│   │   └── deepseek.py           # [Stub]
│   ├── tools/
│   │   ├── base.py               # BaseTool
│   │   ├── registry.py           # ToolRegistry
│   │   ├── executor.py           # ToolExecutor
│   │   └── implementations/
│   │       ├── read.py           # ReadTool
│   │       ├── write.py          # WriteTool
│   │       └── bash.py           # BashTool
│   ├── workspace/
│   │   ├── config.py             # WorkspaceConfig
│   │   └── persistence.py        # ConversationPersistence
│   └── prompts/
│       └── system.py             # System prompts
├── Makefile                       # Development commands
├── pyproject.toml                 # Project metadata & dependencies
├── requirements.lock              # Locked dependencies
├── .env.example                   # Environment template
├── CLAUDE.md                      # Development guide for Claude Code
└── README.md                      # This file
```

## Contributing

Contributions are welcome! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make your changes**
4. **Format code**: `make format`
5. **Test your changes**: Run Bob and test manually
6. **Commit**: Use clear commit messages
7. **Push**: `git push origin feature/my-feature`
8. **Create Pull Request**

### Contribution Guidelines

- Follow the existing code style (Ruff formatting)
- Add docstrings to new classes and methods
- Update this README if adding major features
- Test with multiple LLM providers if possible
- Keep tool implementations async
- Add permission checks for tools that modify state

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)
- Inspired by Claude Code and other AI coding assistants

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/bob-code/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/bob-code/discussions)

---

**Bob Code** - Your AI coding companion in the terminal 🤖✨

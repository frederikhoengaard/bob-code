import asyncio

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    FormattedTextControl,
    HSplit,
    Layout,
    Window,
)
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.widgets import RadioList, TextArea

from src.agent import CodeAgent
from src.providers import AzureOpenAIProvider, LLMProvider
from src.providers.models import LLM, Message
from src.workspace.config import WorkspaceConfig, WorkspaceSettings
from src.workspace.persistence import ConversationPersistence


class ANSILexer(Lexer):
    """Lexer that interprets ANSI escape codes for colored output."""

    def lex_document(self, document):
        """Convert each line's ANSI codes to formatted text."""

        def get_line(lineno):
            try:
                line = document.lines[lineno]
                return ANSI(line).__pt_formatted_text__()
            except IndexError:
                return []

        return get_line


class CodeAgentTUI:
    # ANSI color codes for consistent styling
    GRAY = "\x1b[38;2;152;151;151m"  # #989797 for Bob's responses
    RESET = "\x1b[0m"

    def __init__(self, provider: LLMProvider, model: LLM = LLM.GPT_4o_mini):
        # Initialize workspace
        self.workspace_config = WorkspaceConfig()
        self._initialize_workspace_if_needed()

        # Load model from settings (overrides default)
        permissions = None
        try:
            settings = self.workspace_config.load_settings()
            model = LLM(settings.model)
            permissions = settings.permissions
        except (FileNotFoundError, ValueError):
            # Use default model/permissions if settings don't exist or invalid
            from src.workspace.config import ToolPermissions

            permissions = ToolPermissions()  # All disabled by default

        provider = AzureOpenAIProvider(model=model)

        # Setup conversation persistence
        self.persistence = ConversationPersistence(self.workspace_config)
        self.current_conversation_file = self.persistence.start_new_conversation(str(model))

        # Initialize tool registry
        from src.tools.implementations import BashTool, ReadTool, WriteTool
        from src.tools.registry import ToolRegistry

        self.tool_registry = ToolRegistry()
        self.tool_registry.register(ReadTool())
        self.tool_registry.register(WriteTool())
        self.tool_registry.register(BashTool())

        # Create agent with tools and save callback
        self.agent = CodeAgent(
            provider,
            on_conversation_update=self._on_conversation_update,
            tool_registry=self.tool_registry,
            tool_permissions=permissions,
            on_tool_call=self._on_tool_call,
        )
        self.model = model or provider.model

        # Available commands
        self.commands = {
            "/clear": "Clear conversation history",
            "/conversations": "List previous conversations",
            "/help": "Show help message",
            "/exit": "Exit the application",
            "/quit": "Exit the application",
            "/model": "Show current model info",
            "/models": "List available models",
            "/init": "Generate BOB.md documentation for workspace",
            "/permissions": "View current tool permissions",
            "/enable": "Enable a tool permission",
            "/disable": "Disable a tool permission",
        }

        # Conversation area (includes welcome message, then conversations)
        # Use Buffer + Window instead of TextArea to support line prefixes for wrapped lines
        # Use a flag to control read_only state
        self._conversation_read_only = True

        self.conversation_buffer = Buffer(
            document=None,
            read_only=Condition(lambda: self._conversation_read_only),
            multiline=True,
        )
        # Set initial text (temporarily disable read_only)
        self._conversation_read_only = False
        self.conversation_buffer.text = self._welcome_message()
        self._conversation_read_only = True

        self.conversation_area = Window(
            content=BufferControl(
                buffer=self.conversation_buffer,
                lexer=ANSILexer(),
                focusable=True,
            ),
            wrap_lines=True,
            right_margins=[ScrollbarMargin(display_arrows=True)],
            get_line_prefix=lambda line_number, wrap_count: "  ",
        )

        # Input area
        self.input_area = TextArea(
            height=1,
            multiline=False,
            prompt="> ",
            focusable=True,
            wrap_lines=False,
        )

        # Command suggestions area
        self.suggestions_text = ""
        self.suggestions_control = FormattedTextControl(text=lambda: self.suggestions_text)
        self.suggestions_window = Window(
            content=self.suggestions_control,
            height=3,
            dont_extend_height=True,
        )

        # Conversation selector (RadioList) - needs at least one value
        self.conversation_radio_list = RadioList(values=[("", "Loading...")])

        # Info bar at bottom
        self.info_control = FormattedTextControl(text=self._get_info_text)
        self.info_window = Window(
            content=self.info_control,
            height=1,
            dont_extend_height=True,
        )

        # Bind input changes to update suggestions
        self.input_area.buffer.on_text_changed += self._on_input_changed

        # Conversation selector state
        self.showing_selector = False
        self.selector_radio_list = None

        # Create filter conditions
        self._create_conditions()

        self.setup_keybindings()
        self.app = None
        self.is_streaming = False
        self.token_count = 0

        # Working state tracking for pulsating counter
        self.is_working = False
        self.working_counter = 0
        self.base_output_length = 0
        self.tool_call_output = ""

    def _initialize_workspace_if_needed(self):
        """Initialize workspace if .bob/ doesn't exist"""
        try:
            created = self.workspace_config.initialize_workspace()
            if created:
                from datetime import datetime

                default_settings = WorkspaceSettings(
                    model=str(LLM.GPT_4o_mini),
                    created_at=datetime.now().isoformat(),
                    last_updated=datetime.now().isoformat(),
                )
                self.workspace_config.save_settings(default_settings)
        except Exception as e:
            import sys

            print(f"Warning: Could not initialize workspace: {e}", file=sys.stderr)

    def _on_conversation_update(self, messages: list[Message]):
        """Callback when conversation is updated - auto-save"""
        try:
            self.persistence.save_conversation(
                self.current_conversation_file, messages, str(self.model)
            )
        except Exception as e:
            import sys

            print(f"Warning: Could not save conversation: {e}", file=sys.stderr)

    async def _on_tool_call(self, tool_calls, tool_results):
        """Callback when tools are called - accumulate output and update display"""
        if not self.is_working:
            return

        if tool_results is None:
            # Tools are about to be executed
            for tc in tool_calls:
                tool_name = tc.function.name
                # Parse arguments to show them nicely
                import json

                try:
                    args = json.loads(tc.function.arguments)
                    args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
                except Exception:
                    args_str = "..."

                self.tool_call_output += f"{self.GRAY}🔧 {tool_name}({args_str})\n"
        else:
            # Tools have been executed, accumulate results
            for result in tool_results:
                status = "✓" if not result.is_error else "✗"
                # Truncate long results for display
                result_preview = result.content[:100].replace("\n", " ")
                if len(result.content) > 100:
                    result_preview += "..."

                self.tool_call_output += (
                    f"{self.GRAY}{status} {result.tool_name}: {result_preview}{self.RESET}\n\n"
                )

        # Update the display with current state
        self._update_working_display()

    def _update_working_display(self):
        """Update the output area with working indicator and tool output"""
        if not self.is_working:
            return

        # Build display: base output + working indicator + tool output
        base = self.conversation_buffer.text[: self.base_output_length]
        working = f"{self.GRAY}⚡ Bob is working... ({self.working_counter}){self.RESET}\n\n"

        self._conversation_read_only = False
        self.conversation_buffer.text = base + working + self.tool_call_output
        self._conversation_read_only = True
        # Don't auto-scroll during updates - let user control scroll position while waiting

    async def _increment_counter(self):
        """Background task to increment working counter"""
        while self.is_working:
            await asyncio.sleep(1)
            self.working_counter += 1
            self._update_working_display()

    async def _load_conversation(self, filename: str):
        """Load a conversation and restore it to the current session"""
        try:
            conversation = self.persistence.load_conversation(filename)

            # Clear current conversation display
            self._conversation_read_only = False
            self.conversation_buffer.text = self._welcome_message()
            self._conversation_read_only = True

            # Restore messages to agent
            self.agent.conversation_history = conversation.messages.copy()

            # Update current conversation file to the loaded one
            self.current_conversation_file = filename

            # Display loaded conversation
            await self.append_output(
                f"{self.GRAY}✓ Loaded conversation: {conversation.metadata.title or filename}{self.RESET}\n\n"
            )

            # Replay conversation in display
            for msg in conversation.messages:
                if msg.role == "user":
                    await self.append_output(f"> {msg.content}\n\n")
                elif msg.role == "assistant":
                    await self.append_output(f"{self.GRAY}{msg.content}{self.RESET}\n\n")

        except Exception as e:
            await self.append_output(f"{self.RESET}\n\n❌ Error loading conversation: {str(e)}\n")

    async def _show_conversation_selector(self):
        """Show interactive conversation selector at bottom of screen"""
        from datetime import datetime

        conversations = self.persistence.list_conversations()

        if not conversations:
            await self.append_output(f"{self.GRAY}No previous conversations found.{self.RESET}\n\n")
            return

        # Format conversations for RadioList
        radio_values = []
        for filename, metadata in conversations:
            started_at = datetime.fromisoformat(metadata.started_at)
            now = datetime.now()
            delta = now - started_at

            # Format relative time
            if delta.days > 0:
                time_str = f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
            elif delta.seconds >= 3600:
                hours = delta.seconds // 3600
                time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif delta.seconds >= 60:
                minutes = delta.seconds // 60
                time_str = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                time_str = "just now"

            title = metadata.title or "Untitled conversation"
            message_count = metadata.message_count

            label = f"{title}\n   {time_str} · {message_count} messages"
            radio_values.append((filename, label))

        # Update RadioList values
        self.conversation_radio_list.values = radio_values

        # Show selector and focus it
        self.showing_selector = True
        self.app.layout.focus(self.conversation_radio_list)

    async def _handle_init_command(self):
        """Generate BOB.md file with workspace analysis"""
        await self.append_output(f"{self.GRAY}Generating BOB.md workspace documentation...\n\n")

        init_prompt = """Analyze this workspace and create a BOB.md file with comprehensive documentation:

1. **Project Overview**: Summarize the project's purpose and main functionality
2. **Directory Structure**: Map out the key directories and their purposes
3. **Key Files**: Identify important files and explain their roles
4. **Development Setup**: Document how to set up the development environment
5. **Common Tasks**: List frequent workflows and commands

Use the read tool to explore the codebase structure and files.
Use the write tool to create a well-formatted BOB.md file.
Be thorough but concise - focus on what's most useful for developers."""

        try:
            # Use non-streaming chat for tool-based commands
            response = await self.agent.chat(init_prompt)
            await self.append_output(f"{response}\n{self.RESET}\n")
        except Exception as e:
            await self.append_output(f"\n{self.RESET}❌ Error generating BOB.md: {str(e)}\n\n")

    async def _handle_permissions_command(self):
        """Show current tool permissions"""
        try:
            settings = self.workspace_config.load_settings()
            perms = settings.permissions

            await self.append_output(f"{self.GRAY}Tool Permissions:\n\n")
            await self.append_output(
                f"  File Operations:   {'✓ enabled ' if perms.allow_file_operations else '✗ disabled'}\n"
            )
            await self.append_output(
                f"  Shell Commands:    {'✓ enabled ' if perms.allow_shell_commands else '✗ disabled'}\n"
            )
            await self.append_output(
                f"  Network Access:    {'✓ enabled ' if perms.allow_network_access else '✗ disabled'}\n"
            )
            await self.append_output(
                f"\nUse /enable or /disable to modify permissions.{self.RESET}\n\n"
            )
        except Exception as e:
            await self.append_output(
                f"{self.GRAY}Error loading permissions: {str(e)}{self.RESET}\n\n"
            )

    async def _handle_enable_permission(self, permission: str):
        """Enable a specific permission"""
        # Map user-friendly names to field names
        permission_map = {
            "file_operations": "allow_file_operations",
            "shell_commands": "allow_shell_commands",
            "network_access": "allow_network_access",
        }

        if permission not in permission_map:
            await self.append_output(
                f"{self.GRAY}✗ Unknown permission: {permission}\n"
                f"Available permissions: file_operations, shell_commands, network_access{self.RESET}\n\n"
            )
            return

        try:
            settings = self.workspace_config.load_settings()
            field_name = permission_map[permission]

            # Update the permission
            setattr(settings.permissions, field_name, True)
            self.workspace_config.save_settings(settings)

            # Update agent's executor with new permissions
            if self.agent.tool_executor:
                self.agent.tool_executor.permissions = settings.permissions

            await self.append_output(
                f"{self.GRAY}✓ Enabled {permission.replace('_', ' ')}{self.RESET}\n\n"
            )
        except Exception as e:
            await self.append_output(
                f"{self.GRAY}✗ Error enabling permission: {str(e)}{self.RESET}\n\n"
            )

    async def _handle_disable_permission(self, permission: str):
        """Disable a specific permission"""
        # Map user-friendly names to field names
        permission_map = {
            "file_operations": "allow_file_operations",
            "shell_commands": "allow_shell_commands",
            "network_access": "allow_network_access",
        }

        if permission not in permission_map:
            await self.append_output(
                f"{self.GRAY}✗ Unknown permission: {permission}\n"
                f"Available permissions: file_operations, shell_commands, network_access{self.RESET}\n\n"
            )
            return

        try:
            settings = self.workspace_config.load_settings()
            field_name = permission_map[permission]

            # Update the permission
            setattr(settings.permissions, field_name, False)
            self.workspace_config.save_settings(settings)

            # Update agent's executor with new permissions
            if self.agent.tool_executor:
                self.agent.tool_executor.permissions = settings.permissions

            await self.append_output(
                f"{self.GRAY}✓ Disabled {permission.replace('_', ' ')}{self.RESET}\n\n"
            )
        except Exception as e:
            await self.append_output(
                f"{self.GRAY}✗ Error disabling permission: {str(e)}{self.RESET}\n\n"
            )

    def _welcome_message(self) -> str:
        """Generate welcome screen with ASCII art logo and ANSI colors."""
        # ANSI color codes - 256-color palette
        BLUE = "\x1b[38;5;75m"  # Light blue (#6b9bd1 equivalent)
        RESET = "\x1b[0m"
        # Response color constant (defined here for easy access in other methods)
        # GRAY = "\x1b[38;2;152;151;151m"  # #989797 in true color

        return f"""{BLUE}
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║    {BLUE}██████{RESET}╗  {BLUE}██████{RESET}╗ {BLUE}██████{RESET}╗                                           ║
║    {BLUE}██{RESET}╔══{BLUE}██{RESET}╗{BLUE}██{RESET}╔═══{BLUE}██{RESET}╗{BLUE}██{RESET}╔══{BLUE}██{RESET}╗                                          ║
║    {BLUE}██████{RESET}╔╝{BLUE}██{RESET}║   {BLUE}██{RESET}║{BLUE}██████{RESET}╔╝                                          ║
║    {BLUE}██{RESET}╔══{BLUE}██{RESET}╗{BLUE}██{RESET}║   {BLUE}██{RESET}║{BLUE}██{RESET}╔══{BLUE}██{RESET}╗                                          ║
║    {BLUE}██████╔╝╚{BLUE}██████{RESET}╔╝{BLUE}██████{RESET}╔╝                                          ║
║    {RESET}╚═════╝  ╚═════╝ ╚═════╝                                           ║
║                                                                       ║
║    {BLUE}Welcome back Frederik!{RESET}                                             ║
║                                                                       ║
║    {BLUE}Tips for getting started{RESET}                                           ║
║    Run {BLUE}/init{RESET} to create a BOB.md file with instructions for Bob        ║
║                                                                       ║
║    {BLUE}Recent activity{RESET}                                                    ║
║    No recent activity                                                 ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
{RESET}

"""

    def _get_info_text(self):
        """Generate info bar with model name and working directory."""
        import os

        from prompt_toolkit.formatted_text import FormattedText

        # Get working directory
        cwd = os.getcwd()

        # Truncate path if too long (keep last 40 chars)
        if len(cwd) > 40:
            display_path = "..." + cwd[-37:]
        else:
            display_path = cwd

        model_name = str(self.model)

        return FormattedText(
            [
                ("", f"{model_name} · {display_path}"),
            ]
        )

    def _on_input_changed(self, _):
        """Called whenever input text changes"""
        text = self.input_area.text

        if text.startswith("/"):
            # Filter commands based on what user typed
            query = text[1:].lower()  # Remove the / and lowercase
            matching = [
                f"  {cmd:15} {desc}"
                for cmd, desc in self.commands.items()
                if cmd[1:].lower().startswith(query)  # cmd[1:] removes the /
            ]

            if matching:
                self.suggestions_text = "\n".join(matching[:5])  # Show max 5
            else:
                self.suggestions_text = "  No matching commands"
        else:
            self.suggestions_text = ""

    def setup_keybindings(self):
        """Setup keyboard shortcuts"""
        kb = KeyBindings()

        @kb.add("enter")
        def _(event):
            # If selector is showing and focused, load selected conversation
            if self.showing_selector and event.app.layout.has_focus(self.conversation_radio_list):
                selected_filename = self.conversation_radio_list.current_value
                if selected_filename:
                    self.showing_selector = False
                    # Return focus to input
                    event.app.layout.focus(self.input_area)
                    # Load conversation
                    asyncio.create_task(self._load_conversation(selected_filename))
            # Process input when user presses Enter
            elif not self.is_streaming:
                asyncio.create_task(self.process_input())

        @kb.add("c-c")
        def _(event):
            # Exit on Ctrl+C
            event.app.exit()

        @kb.add("escape")
        def _(event):
            # If selector is showing, cancel it
            if self.showing_selector:
                self.showing_selector = False
                # Return focus to input area
                event.app.layout.focus(self.input_area)
            # Clear input on Escape
            self.input_area.text = ""

        self.input_area.control.key_bindings = kb

        # Global key bindings for focus management
        global_kb = KeyBindings()

        @global_kb.add("c-up")
        def _(event):
            # Focus conversation area (for scrolling)
            event.app.layout.focus(self.conversation_area)

        @global_kb.add("c-down")
        def _(event):
            # Focus input area (for typing)
            event.app.layout.focus(self.input_area)

        @global_kb.add("enter", filter=self.show_selector_condition, eager=True)
        def _(event):
            # Load selected conversation when Enter is pressed in selector
            # RadioList stores selection in _selected_index
            if hasattr(self.conversation_radio_list, "_selected_index"):
                selected_idx = self.conversation_radio_list._selected_index

                if selected_idx is not None and 0 <= selected_idx < len(
                    self.conversation_radio_list.values
                ):
                    selected_filename, _ = self.conversation_radio_list.values[selected_idx]

                    if (
                        selected_filename and selected_filename != ""
                    ):  # Ignore the dummy "Loading..." entry
                        self.showing_selector = False
                        # Return focus to input
                        event.app.layout.focus(self.input_area)
                        # Load conversation
                        asyncio.create_task(self._load_conversation(selected_filename))

        @global_kb.add("escape", filter=self.show_selector_condition)
        def _(event):
            # Cancel selector when Escape is pressed
            self.showing_selector = False
            # Return focus to input area
            event.app.layout.focus(self.input_area)

        # Redirect any printable character to input area when conversation is focused
        @global_kb.add("<any>", filter=has_focus(self.conversation_buffer))
        def _(event):
            # When typing in the conversation area, redirect to input area
            if event.data and len(event.data) == 1 and event.data.isprintable():
                # Focus input area
                event.app.layout.focus(self.input_area)
                # Insert the typed character
                self.input_area.buffer.insert_text(event.data)

        self.global_keybindings = global_kb

    async def append_output(self, text: str):
        """Add text to conversation area"""
        self._conversation_read_only = False
        self.conversation_buffer.text += text
        self.conversation_buffer.cursor_position = len(self.conversation_buffer.text)
        self._conversation_read_only = True

    async def process_input(self):
        """Process user input"""
        user_text = self.input_area.text.strip()

        if not user_text:
            return

        # Clear input field immediately
        self.input_area.text = ""

        # Handle special commands
        if user_text.startswith("/"):
            await self.handle_command(user_text)
            return

        # Show user's message
        await self.append_output(f"> {user_text}\n\n")

        # Use non-streaming chat when tools are available
        if self.agent.tool_registry:
            # Set up working state
            self.is_working = True
            self.working_counter = 0
            self.base_output_length = len(self.conversation_buffer.text)
            self.tool_call_output = ""

            # Start counter task
            counter_task = asyncio.create_task(self._increment_counter())

            # Show initial working indicator
            self._update_working_display()

            try:
                response = await self.agent.chat(user_text)

                # Stop working state
                self.is_working = False
                counter_task.cancel()

                # Remove working indicator, keep tool output, add response
                base = self.conversation_buffer.text[: self.base_output_length]
                self._conversation_read_only = False
                self.conversation_buffer.text = base + self.tool_call_output
                self._conversation_read_only = True

                # Response will be indented by get_line_prefix
                await self.append_output(f"{self.GRAY}{response}{self.RESET}\n\n")
            except Exception as e:
                # Stop working state
                self.is_working = False
                counter_task.cancel()

                # Remove working indicator, keep tool output
                base = self.conversation_buffer.text[: self.base_output_length]
                self._conversation_read_only = False
                self.conversation_buffer.text = base + self.tool_call_output
                self._conversation_read_only = True

                await self.append_output(f"{self.RESET}\n\n❌ Error: {str(e)}\n\n")
        else:
            # Stream agent response with gray color (no tools available)
            self.is_streaming = True
            await self.append_output(f"{self.GRAY}")

            try:
                async for chunk in self.agent.stream_chat(user_text):
                    for char in chunk.content:
                        await self.append_output(char)
                        # Variable delay for natural typing feel
                        if char in [".", "!", "?"]:
                            await asyncio.sleep(0.03)
                        elif char in [",", ";", ":"]:
                            await asyncio.sleep(0.02)
                        elif char == "\n":
                            await asyncio.sleep(0.01)
                        else:
                            await asyncio.sleep(0.003)
            except Exception as e:
                await self.append_output(f"{self.RESET}\n\n❌ Error: {str(e)}\n\n")

            await self.append_output(f"{self.RESET}\n\n")
            self.is_streaming = False

        # Update token count (approximate)
        self.token_count = len(self.agent.conversation_history) * 100  # rough estimate

    async def handle_command(self, command: str):
        """Handle special commands"""
        cmd = command.lower().strip()

        if cmd == "/clear":
            self.agent.clear_history()
            self.token_count = 0

            # Start new conversation file
            self.current_conversation_file = self.persistence.start_new_conversation(
                str(self.model)
            )

            await self.append_output(f"{self.GRAY}✓ Conversation history cleared.{self.RESET}\n\n")

        elif cmd == "/conversations":
            await self._show_conversation_selector()

        elif cmd == "/help":
            await self.append_output(self._welcome_message())
            await self.append_output(f"{self.GRAY}Available commands:\n")
            for cmd, desc in self.commands.items():
                await self.append_output(f"{cmd:12} - {desc}\n")
            await self.append_output(f"{self.RESET}\n")

        elif cmd == "/exit" or cmd == "/quit":
            self.app.exit()

        elif cmd.startswith("/model"):
            parts = command.split(maxsplit=1)

            if len(parts) == 1:
                # No args - show current model
                await self.append_output(f"{self.GRAY}Current model: {self.model}{self.RESET}\n\n")
            else:
                # Switch model
                model_name = parts[1].strip()
                try:
                    new_model = LLM(model_name)

                    # Update workspace settings
                    self.workspace_config.update_model(new_model)

                    # Recreate provider and agent (preserve tools and permissions)
                    provider = AzureOpenAIProvider(model=new_model)
                    old_history = self.agent.conversation_history

                    # Load permissions for agent
                    try:
                        settings = self.workspace_config.load_settings()
                        permissions = settings.permissions
                    except (FileNotFoundError, ValueError):
                        from src.workspace.config import ToolPermissions

                        permissions = ToolPermissions()

                    self.agent = CodeAgent(
                        provider,
                        on_conversation_update=self._on_conversation_update,
                        tool_registry=self.tool_registry,
                        tool_permissions=permissions,
                        on_tool_call=self._on_tool_call,
                    )
                    self.agent.conversation_history = old_history

                    self.model = new_model

                    await self.append_output(
                        f"{self.GRAY}✓ Switched to model: {new_model}{self.RESET}\n\n"
                    )
                except ValueError:
                    await self.append_output(
                        f"{self.GRAY}✗ Invalid model: {model_name}\n"
                        f"Use /models to see available models.{self.RESET}\n\n"
                    )

        elif cmd == "/models":
            await self.append_output(f"{self.GRAY}Available models:\n")

            openai_models = [m for m in LLM if "gpt" in m.value.lower()]
            anthropic_models = [m for m in LLM if "claude" in m.value.lower()]
            deepseek_models = [m for m in LLM if "deepseek" in m.value.lower()]

            if openai_models:
                await self.append_output("OpenAI:\n")
                for model in openai_models:
                    marker = "→ " if model == self.model else " "
                    await self.append_output(f"  {marker}{model.value}\n")

            if anthropic_models:
                await self.append_output("Anthropic:\n")
                for model in anthropic_models:
                    marker = "→ " if model == self.model else " "
                    await self.append_output(f"  {marker}{model.value}\n")

            if deepseek_models:
                await self.append_output("DeepSeek:\n")
                for model in deepseek_models:
                    marker = "→ " if model == self.model else " "
                    await self.append_output(f"  {marker}{model.value}\n")

            await self.append_output(f"\nUse /model <model_value> to switch{self.RESET}\n\n")

        elif cmd == "/init":
            await self._handle_init_command()

        elif cmd == "/permissions":
            await self._handle_permissions_command()

        elif cmd.startswith("/enable"):
            parts = command.split(maxsplit=1)
            if len(parts) == 1:
                await self.append_output(
                    f"{self.GRAY}Usage: /enable <permission>\n"
                    f"Available permissions: file_operations, shell_commands, network_access{self.RESET}\n\n"
                )
            else:
                await self._handle_enable_permission(parts[1].strip())

        elif cmd.startswith("/disable"):
            parts = command.split(maxsplit=1)
            if len(parts) == 1:
                await self.append_output(
                    f"{self.GRAY}Usage: /disable <permission>\n"
                    f"Available permissions: file_operations, shell_commands, network_access{self.RESET}\n\n"
                )
            else:
                await self._handle_disable_permission(parts[1].strip())

        else:
            await self.append_output(f"{self.GRAY}Unknown command: {command}\n")
            await self.append_output(f"Type /help for available commands.{self.RESET}\n\n")

    def _create_conditions(self):
        """Create filter conditions"""
        self.show_suggestions_condition = Condition(lambda: bool(self.suggestions_text))
        self.show_selector_condition = Condition(lambda: self.showing_selector)

    def create_layout(self):
        """Create the TUI layout"""
        return Layout(
            HSplit(
                [
                    # Conversation area (scrollable, includes welcome at top)
                    self.conversation_area,
                    # Horizontal line separator
                    Window(height=1, char="─"),
                    # Input area
                    self.input_area,
                    # Horizontal line separator
                    Window(height=1, char="─"),
                    # Command suggestions (only shown when typing / and selector not showing)
                    ConditionalContainer(
                        self.suggestions_window,
                        filter=~self.show_selector_condition,  # Hide when selector is showing
                    ),
                    # Conversation selector (shown when /conversations is active)
                    ConditionalContainer(
                        HSplit(
                            [
                                Window(
                                    FormattedTextControl(text="Resume Session\n"),
                                    height=2,
                                ),
                                self.conversation_radio_list,
                                Window(
                                    FormattedTextControl(text="\nEnter to load · Esc to cancel"),
                                    height=2,
                                ),
                            ]
                        ),
                        filter=self.show_selector_condition,
                    ),
                    # Info bar at bottom
                    self.info_window,
                ]
            )
        )

    async def run(self):
        """Run the TUI application"""
        self.app = Application(
            layout=self.create_layout(),
            key_bindings=self.global_keybindings,
            full_screen=True,
            mouse_support=False,  # Disable to allow terminal-native text selection and copying
        )

        # Focus input area by default
        self.app.layout.focus(self.input_area)

        await self.app.run_async()


async def main(provider: LLMProvider = AzureOpenAIProvider, model: str = LLM.GPT_4o_mini):
    tui = CodeAgentTUI(provider=provider, model=model)
    await tui.run()

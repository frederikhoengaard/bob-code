import asyncio

from prompt_toolkit import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, Window
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.widgets import TextArea

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
        try:
            settings = self.workspace_config.load_settings()
            model = LLM(settings.model)
        except (FileNotFoundError, ValueError):
            # Use default model if settings don't exist or invalid
            pass

        provider = AzureOpenAIProvider(model=model)

        # Setup conversation persistence
        self.persistence = ConversationPersistence(self.workspace_config)
        self.current_conversation_file = self.persistence.start_new_conversation(str(model))

        # Create agent with save callback
        self.agent = CodeAgent(provider, on_conversation_update=self._on_conversation_update)
        self.model = model or provider.model

        # Available commands
        self.commands = {
            "/clear": "Clear conversation history",
            "/help": "Show help message",
            "/exit": "Exit the application",
            "/quit": "Exit the application",
            "/model": "Show current model info",
            "/models": "List available models",
        }

        # Conversation area (includes welcome message, then conversations)
        self.conversation_area = TextArea(
            text=self._welcome_message(),
            multiline=True,
            scrollbar=True,
            focusable=True,
            read_only=True,
            wrap_lines=True,
            lexer=ANSILexer(),
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

        # Info bar at bottom
        self.info_control = FormattedTextControl(text=self._get_info_text)
        self.info_window = Window(
            content=self.info_control,
            height=1,
            dont_extend_height=True,
        )

        # Bind input changes to update suggestions
        self.input_area.buffer.on_text_changed += self._on_input_changed

        self.setup_keybindings()
        self.app = None
        self.is_streaming = False
        self.token_count = 0

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
            # Process input when user presses Enter
            if not self.is_streaming:
                asyncio.create_task(self.process_input())

        @kb.add("c-c")
        def _(event):
            # Exit on Ctrl+C
            event.app.exit()

        @kb.add("escape")
        def _(event):
            # Clear input on Escape and focus input area
            self.input_area.text = ""
            event.app.layout.focus(self.input_area)

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

        self.global_keybindings = global_kb

    async def append_output(self, text: str):
        """Add text to conversation area"""
        self.conversation_area.text += text
        # Auto-scroll to bottom
        self.conversation_area.buffer.cursor_position = len(self.conversation_area.text)

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
        await self.append_output(f"  > {user_text}\n\n  ")

        # Stream agent response with gray color
        self.is_streaming = True
        await self.append_output(self.GRAY)  # Start gray color for Bob's response

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
            await self.append_output(f"{self.RESET}\n\n❌ Error: {str(e)}\n")

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

        elif cmd == "/help":
            await self.append_output(self._welcome_message())
            await self.append_output(f"{self.GRAY}Available commands:\n")
            for cmd, desc in self.commands.items():
                await self.append_output(f"  {cmd:12} - {desc}\n")
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

                    # Recreate provider and agent
                    provider = AzureOpenAIProvider(model=new_model)
                    old_history = self.agent.conversation_history
                    self.agent = CodeAgent(
                        provider, on_conversation_update=self._on_conversation_update
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
                await self.append_output("  OpenAI:\n")
                for model in openai_models:
                    marker = "→ " if model == self.model else "  "
                    await self.append_output(f"    {marker}{model.value}\n")

            if anthropic_models:
                await self.append_output("  Anthropic:\n")
                for model in anthropic_models:
                    marker = "→ " if model == self.model else "  "
                    await self.append_output(f"    {marker}{model.value}\n")

            if deepseek_models:
                await self.append_output("  DeepSeek:\n")
                for model in deepseek_models:
                    marker = "→ " if model == self.model else "  "
                    await self.append_output(f"    {marker}{model.value}\n")

            await self.append_output(f"\nUse /model <model_value> to switch{self.RESET}\n\n")

        else:
            await self.append_output(f"{self.GRAY}Unknown command: {command}\n")
            await self.append_output(f"Type /help for available commands.{self.RESET}\n\n")

    @Condition
    def show_suggestions(self):
        """Condition to show suggestions window"""
        return bool(self.suggestions_text)

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
                    # Command suggestions (only shown when typing /)
                    HSplit(
                        [
                            self.suggestions_window,
                        ],
                        # filter=self.show_suggestions,
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
            mouse_support=True,
        )

        # Focus input area by default
        self.app.layout.focus(self.input_area)

        await self.app.run_async()


async def main(provider: LLMProvider = AzureOpenAIProvider, model: str = LLM.GPT_4o_mini):
    tui = CodeAgentTUI(provider=provider, model=model)
    await tui.run()

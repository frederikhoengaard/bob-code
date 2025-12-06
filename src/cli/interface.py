import asyncio

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import Frame, TextArea

from src.agent import CodeAgent
from src.providers import AzureOpenAIProvider, LLMProvider
from src.providers.models import LLM


class CodeAgentTUI:
    def __init__(self, provider: LLMProvider, model: LLM = LLM.GPT_4o_mini):
        provider = AzureOpenAIProvider(model=model)
        self.agent = CodeAgent(provider)

        # Output area (read-only)
        self.output_area = TextArea(
            text=self._welcome_message(),
            multiline=True,
            scrollbar=True,
            focusable=False,
            read_only=True,
            wrap_lines=True,
        )

        # Input area
        self.input_area = TextArea(
            height=3,
            multiline=False,
            prompt=HTML("<ansiyellow>> </ansiyellow>"),
            focusable=True,
            wrap_lines=True,
        )

        self.setup_keybindings()
        self.app = None
        self.is_streaming = False

    def _welcome_message(self) -> str:
        return """╔══════════════════════════════════════════════════════════╗
║               BOB-CODE - AI Coding Assistant             ║
╚══════════════════════════════════════════════════════════╝

Welcome! I'm here to help you with coding tasks.

Commands:
  • Type your message and press Enter to send
  • Ctrl+C to exit
  • /clear to clear conversation history
  • /help to show this help message

Ready to assist!
════════════════════════════════════════════════════════════

"""

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

        self.input_area.control.key_bindings = kb

    async def append_output(self, text: str):
        """Add text to output area"""
        self.output_area.text += text
        # Auto-scroll to bottom
        self.output_area.buffer.cursor_position = len(self.output_area.text)

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

        # Stream agent response
        self.is_streaming = True

        try:
            async for chunk in self.agent.stream_chat(user_text):
                for char in chunk.content:
                    await self.append_output(char)
                    await asyncio.sleep(0.005)
        except Exception as e:
            await self.append_output(f"\n\n❌ Error: {str(e)}\n")

        await self.append_output("\n\n" + "─" * 60 + "\n\n")
        self.is_streaming = False

    async def handle_command(self, command: str):
        """Handle special commands"""
        cmd = command.lower().strip()

        if cmd == "/clear":
            self.agent.clear_history()
            await self.append_output("✓ Conversation history cleared.\n\n")

        elif cmd == "/help":
            await self.append_output(self._welcome_message())

        elif cmd == "/exit" or cmd == "/quit":
            self.app.exit()

        else:
            await self.append_output(f"Unknown command: {command}\n")
            await self.append_output("Type /help for available commands.\n\n")

    def create_layout(self):
        """Create the TUI layout"""
        return Layout(
            HSplit(
                [
                    Frame(self.output_area, title="Conversation"),
                    Frame(
                        self.input_area,
                        title="Input (Enter to send • Ctrl+C to exit • /help for commands)",
                    ),
                ]
            )
        )

    async def run(self):
        """Run the TUI application"""
        self.app = Application(
            layout=self.create_layout(),
            full_screen=True,
            mouse_support=True,
        )

        await self.app.run_async()


async def main(provider: LLMProvider = AzureOpenAIProvider, model: str = LLM.GPT_4o_mini):
    tui = CodeAgentTUI(provider=provider, model=model)
    await tui.run()

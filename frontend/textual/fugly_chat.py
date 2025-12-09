import argparse

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown

from backend.agents.draw_steel_expert_class import DrawSteelExpert
from backend.utils.agent_models import MODEL_MAP

# Default configuration
DEFAULT_COLLECTION = "AllBooksV1"
DEFAULT_MODEL = "gemini-flash-lite"


class UserMessage(Markdown):
    """User input message."""

    pass


class AssistantMessage(Markdown):
    """Assistant response message."""

    BORDER_TITLE = "Draw Steel Expert"


class SystemMessage(Markdown):
    """System/command output message."""

    pass


class DrawSteelApp(App):
    """Draw Steel Expert chat application."""

    AUTO_FOCUS = "Input"
    CSS_PATH = "css/fugly_chat.tcss"

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        model_name: str = DEFAULT_MODEL,
        expert: DrawSteelExpert | None = None,
    ):
        super().__init__()
        self.collection_name = collection_name
        self.model_name = model_name
        self.expert = expert
        self.session_id: str | None = None
        self._pending_response: AssistantMessage | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="chat-view"):
            yield SystemMessage(self._welcome_message())
        yield Input(placeholder="Ask about Draw Steel...")
        yield Footer()

    def on_mount(self) -> None:
        self.theme = "nord"
        # Create session for pre-initialized expert
        if self.expert is not None and self.session_id is None:
            self.session_id = self.expert.create_session()

    def _init_expert(self) -> None:
        """Reinitialize the expert agent (for model switching)."""
        if self.expert is not None:
            self.expert.close()
        model = MODEL_MAP[self.model_name]
        self.expert = DrawSteelExpert(
            collection_name=self.collection_name,
            model=model,
        )
        # Warm up database and agent outside of async context
        _ = self.expert.database
        _ = self.expert.agent
        self.session_id = self.expert.create_session()

    def _welcome_message(self) -> str:
        return (
            f"**Welcome to Draw Steel Expert!**\n\n"
            f"Collection: `{self.collection_name}`\n"
            f"Model: `{self.model_name}`\n\n"
            f"Commands: `/clear` `/model <name>` `/models` `/help`"
        )

    @on(Input.Submitted)
    async def handle_input(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return

        event.input.clear()
        chat_view = self.query_one("#chat-view", VerticalScroll)

        # Handle commands
        if query.startswith("/"):
            await self._handle_command(query, chat_view)
            return

        # Add user message
        await chat_view.mount(UserMessage(query))

        # Add response placeholder and start query
        self._pending_response = AssistantMessage("*Thinking...*")
        await chat_view.mount(self._pending_response)
        self._pending_response.anchor()

        self._run_query(query)

    @work(exclusive=True)
    async def _run_query(self, query: str) -> None:
        """Run the agent query with streaming, updating UI progressively."""
        if self.expert is None:
            if self._pending_response:
                self._pending_response.update("**Error:** Expert not initialized")
                self._pending_response = None
            return

        try:
            accumulated = ""
            async for chunk in self.expert.run_agent_streamed(
                query, session_id=self.session_id
            ):
                accumulated += chunk
                if self._pending_response:
                    self._pending_response.update(accumulated)
        except Exception as e:
            if self._pending_response:
                self._pending_response.update(f"**Error:** {e}")
        finally:
            self._pending_response = None

    async def _handle_command(self, query: str, chat_view: VerticalScroll) -> None:
        """Handle slash commands."""
        parts = query.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command == "/clear":
            chat_view.remove_children()
            if self.expert:
                self.session_id = self.expert.create_session()
            await chat_view.mount(SystemMessage("Session cleared. Starting fresh!"))

        elif command == "/help":
            await chat_view.mount(
                SystemMessage(
                    f"**Draw Steel Expert Help**\n\n"
                    f"Current Collection: `{self.collection_name}`\n"
                    f"Current Model: `{self.model_name}`\n\n"
                    f"**Commands:**\n"
                    f"- `/clear` - Start new session\n"
                    f"- `/model <name>` - Switch model\n"
                    f"- `/models` - List available models\n"
                    f"- `/help` - Show this message"
                )
            )

        elif command == "/models":
            model_list = "\n".join(f"- `{name}`" for name in sorted(MODEL_MAP.keys()))
            await chat_view.mount(
                SystemMessage(
                    f"**Available Models:**\n\n{model_list}\n\n"
                    f"Current: `{self.model_name}`"
                )
            )

        elif command == "/model":
            if not args:
                await chat_view.mount(
                    SystemMessage(
                        f"Usage: `/model <name>`\n\nCurrent: `{self.model_name}`"
                    )
                )
            elif args in MODEL_MAP:
                self.model_name = args
                self._init_expert()
                await chat_view.mount(
                    SystemMessage(f"Switched to model: `{self.model_name}`")
                )
            else:
                model_list = ", ".join(f"`{n}`" for n in sorted(MODEL_MAP.keys()))
                await chat_view.mount(
                    SystemMessage(f"Unknown model: `{args}`\n\nAvailable: {model_list}")
                )

        else:
            await chat_view.mount(
                SystemMessage(
                    f"Unknown command: `{command}`\n\nType `/help` for available commands."
                )
            )

        chat_view.scroll_end(animate=False)

    def on_unmount(self) -> None:
        """Clean up on exit."""
        if self.expert is not None:
            self.expert.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Draw Steel Expert - Textual chat interface"
    )

    parser.add_argument(
        "--collection-name",
        type=str,
        default=DEFAULT_COLLECTION,
        help=f"Name of the database collection (default: {DEFAULT_COLLECTION})",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        choices=list(MODEL_MAP.keys()),
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )

    args = parser.parse_args()

    # Initialize expert BEFORE starting Textual to avoid multiprocessing conflicts
    # (tqdm/sentence-transformers use multiprocessing locks that conflict with Textual)
    model = MODEL_MAP[args.model]
    expert = DrawSteelExpert(
        collection_name=args.collection_name,
        model=model,
    )
    # Warm up database and agent
    _ = expert.database
    _ = expert.agent

    app = DrawSteelApp(
        collection_name=args.collection_name,
        model_name=args.model,
        expert=expert,
    )
    app.run()


if __name__ == "__main__":
    main()

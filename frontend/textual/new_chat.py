import argparse
from typing import Literal

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Collapsible, Footer, Header, Input, LoadingIndicator, Static
from textual.worker import Worker, WorkerState

from backend.agents.draw_steel_expert_class import DrawSteelExpert
from backend.utils.agent_models import MODEL_MAP

Role = Literal["system", "user", "assistant", "tool", "other"]

# Default configuration
DEFAULT_COLLECTION = "AllBooksV1"
DEFAULT_MODEL = "gemini-flash-lite"


class MessageContainer(Container):
    def __init__(self, message: str, role: Role):
        super().__init__()
        self.message = message
        self.role = role
        self.can_focus = True
        match role:
            case "user":
                self.row_classes = "row user-row"
                self.bubble_classes = "bubble user-bubble"
                self.message_classes = "message user-message"
            case "assistant":
                self.row_classes = "row assistant-row"
                self.bubble_classes = "bubble assistant-bubble"
                self.message_classes = "message assistant-message"
            case "tool":
                self.row_classes = "row tool-row"
                self.bubble_classes = "bubble tool-bubble"
                self.message_classes = "message tool-message"
            case "other":
                self.row_classes = "row other-row"
                self.bubble_classes = "bubble other-bubble"
                self.message_classes = "message other-message"
            case _:
                raise ValueError(f"Invalid role: {self.role}")

    def compose(self) -> ComposeResult:
        with Container(classes=self.row_classes):
            if self.role == "tool":
                self.can_focus = False
                with Collapsible(
                    title="Tool Call",
                    collapsed=True,
                    classes=self.bubble_classes,
                ):
                    yield Static(
                        self.message,
                        classes=self.message_classes,
                    )
            else:
                with Container(classes=self.bubble_classes):
                    yield Static(self.message, classes=self.message_classes)


class ThinkingIndicator(Container):
    """Shows a loading indicator while the agent is thinking."""

    def compose(self) -> ComposeResult:
        with Container(classes="row assistant-row"):
            with Container(classes="bubble assistant-bubble"):
                yield LoadingIndicator()
                yield Static("Thinking...", classes="message assistant-message")


class ChatInput(Input):
    """Input that swallows ESC so the global binding doesn't fire while focused."""

    BINDINGS = [
        Binding(
            key="escape",
            action="noop_escape",
            description="",
            show=False,
        )
    ]

    def action_noop_escape(self) -> None:
        pass


class Chat(Widget):
    """Entire chat widget with history and input."""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat-history")
        yield ChatInput(
            placeholder="Ask about Draw Steel...", type="text", id="chat-input"
        )

    def add_message(self, content: str, role: Role) -> MessageContainer:
        """Add a new message to the chat history."""
        history = self.query_one("#chat-history", VerticalScroll)
        message = MessageContainer(content, role)
        history.mount(message)
        history.scroll_end(animate=False)
        return message

    def show_thinking(self) -> ThinkingIndicator:
        """Show a thinking indicator."""
        history = self.query_one("#chat-history", VerticalScroll)
        indicator = ThinkingIndicator()
        history.mount(indicator)
        history.scroll_end(animate=False)
        return indicator

    def hide_thinking(self, indicator: ThinkingIndicator) -> None:
        """Remove the thinking indicator."""
        indicator.remove()

    def clear_history(self) -> None:
        """Clear all messages from chat history."""
        history = self.query_one("#chat-history", VerticalScroll)
        history.remove_children()


class ChatApp(App):
    CSS_PATH = "css/new_chat.tcss"
    BINDINGS = [
        Binding(key="c", action="copy", description="copy highlighted content"),
        Binding(
            key="escape",
            action="focus_chat_input",
            description="focus chat input",
            id="focus_chat_input",
        ),
    ]

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        model_name: str = DEFAULT_MODEL,
    ):
        super().__init__()
        self.collection_name = collection_name
        self.current_model_name = model_name
        self.expert: DrawSteelExpert | None = None
        self.current_session_id: str | None = None
        self._thinking_indicator: ThinkingIndicator | None = None

    def on_mount(self) -> None:
        """Initialize on mount."""
        self.theme = "nord"
        self._init_expert()
        # Show welcome message
        chat = self.query_one(Chat)
        chat.add_message(
            f"Welcome to Draw Steel Expert!\n\n"
            f"Collection: {self.collection_name}\n"
            f"Model: {self.current_model_name}\n\n"
            f"Commands:\n"
            f"  /clear  - Start new session\n"
            f"  /model <name> - Switch model\n"
            f"  /models - List available models\n"
            f"  /help   - Show this message",
            role="other",
        )

    def _init_expert(self) -> None:
        """Initialize or reinitialize the expert agent."""
        if self.expert is not None:
            self.expert.close()
        model = MODEL_MAP[self.current_model_name]
        self.expert = DrawSteelExpert(
            collection_name=self.collection_name,
            model=model,
        )
        self.current_session_id = self.expert.create_session()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Chat()
        yield Footer(name="footer")

    def action_focus_chat_input(self) -> None:
        """Focus on chat-input widget."""
        chat_input = self.query_one("#chat-input", Input)
        chat_input.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        query = event.value.strip()
        if not query:
            return

        # Clear the input
        event.input.value = ""
        chat = self.query_one(Chat)

        # Handle commands
        if query.startswith("/"):
            await self._handle_command(query, chat)
            return

        # Add user message
        chat.add_message(query, role="user")

        # Show thinking indicator
        self._thinking_indicator = chat.show_thinking()

        # Run the agent asynchronously (worker result handled in on_worker_state_changed)
        _ = self._run_agent_query(query)

    @work(exclusive=True)
    async def _run_agent_query(self, query: str) -> str:
        """Run the agent query in a worker."""
        if self.expert is None:
            return "Error: Expert not initialized"
        result = await self.expert.run_agent(query, session_id=self.current_session_id)
        return result.final_output

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.state == WorkerState.SUCCESS:
            chat = self.query_one(Chat)
            # Hide thinking indicator
            if self._thinking_indicator is not None:
                chat.hide_thinking(self._thinking_indicator)
                self._thinking_indicator = None
            # Add assistant response
            response = event.worker.result
            if response:
                chat.add_message(response, role="assistant")

        elif event.state == WorkerState.ERROR:
            chat = self.query_one(Chat)
            # Hide thinking indicator
            if self._thinking_indicator is not None:
                chat.hide_thinking(self._thinking_indicator)
                self._thinking_indicator = None
            # Show error
            chat.add_message(f"Error: {event.worker.error}", role="other")

    async def _handle_command(self, query: str, chat: Chat) -> None:
        """Handle slash commands."""
        parts = query.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command == "/clear":
            chat.clear_history()
            if self.expert:
                self.current_session_id = self.expert.create_session()
            chat.add_message("Session cleared. Starting fresh!", role="other")

        elif command == "/help":
            chat.add_message(
                f"Draw Steel Expert Help\n\n"
                f"Current Collection: {self.collection_name}\n"
                f"Current Model: {self.current_model_name}\n\n"
                f"Commands:\n"
                f"  /clear  - Start new session\n"
                f"  /model <name> - Switch model\n"
                f"  /models - List available models\n"
                f"  /help   - Show this message",
                role="other",
            )

        elif command == "/models":
            model_list = "\n".join(f"  • {name}" for name in sorted(MODEL_MAP.keys()))
            current = f"Current: {self.current_model_name}"
            chat.add_message(
                f"Available Models:\n\n{model_list}\n\n{current}", role="other"
            )

        elif command == "/model":
            if not args:
                chat.add_message(
                    f"Usage: /model <name>\n\nCurrent model: {self.current_model_name}",
                    role="other",
                )
            elif args in MODEL_MAP:
                self.current_model_name = args
                self._init_expert()
                chat.add_message(
                    f"Switched to model: {self.current_model_name}", role="other"
                )
            else:
                model_list = ", ".join(sorted(MODEL_MAP.keys()))
                chat.add_message(
                    f"Unknown model: {args}\n\nAvailable: {model_list}",
                    role="other",
                )

        else:
            chat.add_message(
                f"Unknown command: {command}\n\nType /help for available commands.",
                role="other",
            )

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

    app = ChatApp(
        collection_name=args.collection_name,
        model_name=args.model,
    )
    app.run()


if __name__ == "__main__":
    main()


"""
this does properly work.
"""

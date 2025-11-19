from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from frontend.textual.sample_data.chat_history import (
    SAMPLE_CHAT_HISTORY_1,
    async_simulate_chat,
)


class ChatInteraction(Static):
    """One rendered chat message."""

    def __init__(self, message: dict[str, Any]) -> None:
        self.message = message
        super().__init__(self._render_message(message))

    def _render_message(self, msg: dict[str, Any]) -> str:
        role = msg.get("role", "?")

        if role == "assistant":
            content = msg.get("content", "") or str(msg.get("function_call", {}))
            return f"[b]Assistant:[/b] {content}"

        if role == "user":
            content = msg.get("content", "")
            return f"[b cyan]You:[/b cyan] {content}"

        if role == "tool":
            # Example: show the first tool chunk text
            chunks = msg.get("content") or []
            text = chunks[0].get("text", "") if chunks else ""
            return f"[dim]Tool:[/dim] {text[:140]}..."

        # Fallback
        return f"[dim]{role}:[/dim] {msg}"


class ChatHistory(VerticalScroll):
    """Container that plays back a chat as 'streaming' messages."""

    @work(exclusive=True)
    async def play_from_user_message(self, user_message: dict[str, Any]) -> None:
        """Replay the conversations that follow this user_message."""
        # Show the user's message immediately
        self.mount(ChatInteraction(user_message))

        # Then stream the rest of the conversation
        async for msg in async_simulate_chat(user_message):
            # Each yielded dict becomes a ChatInteraction widget
            self.mount(ChatInteraction(msg))


class ChatApp(App):
    CSS = """
    ChatHistory {
        border: heavy $primary;
        height: 100%;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield ChatHistory(id="chat-history")

    def on_mount(self) -> None:
        # Kick off the simulation from inside Textual
        history = self.query_one(ChatHistory)
        first_item = SAMPLE_CHAT_HISTORY_1[0]
        history.play_from_user_message(first_item)


if __name__ == "__main__":
    app = ChatApp()
    app.run()

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input

from frontend.textual.sample_data.chat_history import SAMPLE_CHAT_HISTORY

with open("frontend/textual/css/scrollableContainer.tcss", "r") as f:
    SCROLLABLE_CONTAINER_CSS = f.read()

dummy_chat_history = SAMPLE_CHAT_HISTORY


class ChatContent(VerticalScroll):
    """Chat messages and retrieved items"""


class DrawSteelApp(App):
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]
    CSS = SCROLLABLE_CONTAINER_CSS
    INPUT = Input(placeholder="Enter your message here...")

    def __init__(self):
        super().__init__()
        self.chat_content = ChatContent()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with self.chat_content:
            yield from self.chat_content.compose()
        yield self.INPUT

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )


if __name__ == "__main__":
    app = DrawSteelApp()
    app.run()


"""
No agent logic here. Just basic features.
"""

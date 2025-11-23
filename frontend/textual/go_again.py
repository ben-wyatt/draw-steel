from typing import Literal

from lorem.text import TextLorem
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Collapsible, Footer, Header, Input, Static

Role = Literal["system", "user", "assistant", "tool", "other"]


class MessageContainer(Container):
    def __init__(self, message: str, role: Role):
        super().__init__()
        self.message = message
        self.role = role
        self.can_focus = True
        match role:
            case "user":
                self.row_classes = "row user-row"
                self.classes = "user-container"
            case "assistant":
                self.row_classes = "row assistant-row"
                self.classes = "assistant-container"
            case "tool":
                self.row_classes = "row tool-row"
                self.classes = "tool-container"
            case "other":
                self.row_classes = "row other-row"
                self.classes = "other-container"
            case _:
                raise ValueError(f"Invalid role: {self.role}")

    def compose(self) -> ComposeResult:
        if self.role == "tool":
            text = TextLorem(srange=(10, 200)).paragraph()
            self.can_focus = False
            with Collapsible(title="search_text(query='Draw Steel')", collapsed=True):
                yield Static(
                    self.message + "\n\n" + text,
                    classes=self.role + " message-text",
                )
        else:
            yield Static(self.message, classes=self.role + " message-text")


class ChatInput(Input):
    """Input that swallows ESC so the global binding doesn't fire while focused."""

    BINDINGS = [
        Binding(
            key="escape",
            action="noop_escape",
            description="",
            show=False,  # use to override global binding
        )
    ]

    def action_noop_escape(self) -> None:
        pass


class Chat(Widget):
    """entire chat widget"""

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="chat-history"):
            for i in range(10):
                yield MessageContainer(f"Hey I'm user {i}", role="user")
                yield MessageContainer(f"Hey I'm assistant {i}", role="assistant")
                yield MessageContainer("whatever", role="tool")
        yield ChatInput(placeholder="Whatever...", type="text", id="chat-input")


class ChatApp(App):
    CSS_PATH = "css/gpt/go_again.tcss"
    BINDINGS = [
        Binding(key="c", action="copy", description="copy highlighted content"),
        Binding(
            key="escape",
            action="focus_chat_input",
            description="focus chat input",
            id="focus_chat_input",
        ),
    ]

    def on_mount(self) -> None:
        """Set theme on mount"""
        self.theme = "nord"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Chat()
        yield Footer(name="footer")

    def action_focus_chat_input(self) -> None:
        """focus on chat-input widget"""
        chat_input = self.query_one("#chat-input", Input)
        chat_input.focus()


if __name__ == "__main__":
    app = ChatApp()
    app.run()


"""
TODO: check with heavy lorem ipsum
TODO: switch Static to Markdown
TODO: add async chat history rendering
TODO: test with simulated chat
TODO: connect with backend
TODO: landing screen
"""

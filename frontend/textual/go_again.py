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
        with Container(classes=self.row_classes):  # row
            if self.role == "tool":
                text = TextLorem(srange=(10, 200)).paragraph()
                self.can_focus = False
                with Collapsible(
                    title="search_text(query='Draw Steel')",
                    collapsed=True,
                    classes=self.bubble_classes,
                ):
                    yield Static(
                        self.message + "\n\n" + text,
                        classes=self.message_classes,
                    )
            else:
                with Container(classes=self.bubble_classes):
                    yield Static(self.message, classes=self.message_classes)


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
            for i in range(5):
                yield MessageContainer(f"Hey I'm user {i}", role="user")
                yield MessageContainer(f"Hey I'm assistant {i}", role="assistant")
                yield MessageContainer("whatever", role="tool")
        yield ChatInput(placeholder="Whatever...", type="text", id="chat-input")


class ChatApp(App):
    CSS_PATH = "css/gpt/go_again_2.tcss"
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

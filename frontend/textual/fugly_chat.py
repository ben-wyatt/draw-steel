import argparse

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.validation import ValidationResult, Validator
from textual.widgets import Collapsible, Footer, Header, Input, Markdown

from backend.agents.draw_steel_expert_class import DrawSteelExpert, StreamEvent
from backend.utils.agent_models import MODEL_MAP

# Default configuration
DEFAULT_COLLECTION = "AllBooksV1"
DEFAULT_MODEL = "gemini-flash-lite"

# Known commands
KNOWN_COMMANDS = {"/clear", "/help", "/models", "/model"}


class CommandValidator(Validator):
    """Validates that slash commands are recognized."""

    def validate(self, value: str) -> ValidationResult:
        """Check if value starting with / is a known command."""
        if not value.startswith("/"):
            # Not a command, always valid
            return self.success()

        # Extract the command part (before any arguments)
        command = value.split(maxsplit=1)[0].lower()

        if command in KNOWN_COMMANDS:
            return self.success()
        else:
            return self.failure(
                f"Unknown command: {command}. Type /help for available commands."
            )


class UserMessage(Markdown):
    """User input message."""

    pass


class AssistantMessage(Markdown):
    """Assistant response message."""

    BORDER_TITLE = "Draw Steel Expert"


class SystemMessage(Markdown):
    """System/command output message."""

    pass


class ToolMessage(Markdown):
    """Tool call/result message."""

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
        self._thinking_message: SystemMessage | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="chat-view"):
            yield SystemMessage(self._welcome_message())
        yield Input(
            placeholder="Ask about Draw Steel...",
            validators=[CommandValidator()],
            validate_on=["submitted"],
        )
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

        # Don't process if validation failed
        if event.validation_result and not event.validation_result.is_valid:
            return

        event.input.clear()
        chat_view = self.query_one("#chat-view", VerticalScroll)

        # Handle commands
        if query.startswith("/"):
            await self._handle_command(query, chat_view)
            return

        # Add user message
        await chat_view.mount(UserMessage(query))

        # Add a lightweight placeholder first (tool calls will follow, then assistant msg)
        self._pending_response = None
        self._thinking_message = SystemMessage("... thinking.")
        await chat_view.mount(self._thinking_message)
        self._thinking_message.anchor()

        self._run_query(query)

    @work(exclusive=True)
    async def _run_query(self, query: str) -> None:
        """Run the agent query with streaming, updating UI progressively."""
        if self.expert is None:
            if self._thinking_message:
                self._thinking_message.update("**Error:** Expert not initialized")
                self._thinking_message = None
            return

        chat_view = self.query_one("#chat-view", VerticalScroll)
        tool_calls: dict[str, dict] = {}
        tool_call_seq = 0
        last_tool_call_id: str | None = None
        accumulated_text = ""

        try:
            event: StreamEvent
            async for event in self.expert.run_agent_streamed(
                query, session_id=self.session_id
            ):
                if event.type == "tool_call":
                    # Mount a new ToolMessage (or search_text Collapsible) for this tool call
                    tool_query = event.metadata.get("arguments", {}).get("query", "")
                    content = f"**{event.data}**: {tool_query}"

                    tool_call_id = event.metadata.get("tool_call_id")
                    if not tool_call_id:
                        tool_call_seq += 1
                        tool_call_id = f"tool_call_{tool_call_seq}"
                    last_tool_call_id = tool_call_id

                    if event.data == "search_text":
                        # IMPORTANT: mount chunk widgets into an inner container which is a *child*
                        # of Collapsible content. Mounting directly on Collapsible won't collapse them.
                        results_container = Container(classes="search-results")
                        search_collapsible = Collapsible(
                            results_container,
                            title=f"search_text: {tool_query}",
                            collapsed=False,
                            classes="search-collapsible",
                        )
                        tool_calls[tool_call_id] = {
                            "name": event.data,
                            "query": tool_query,
                            "collapsible": search_collapsible,
                            "results_container": results_container,
                        }
                        await chat_view.mount(search_collapsible)
                    else:
                        tool_message = ToolMessage(content)
                        tool_calls[tool_call_id] = {
                            "name": event.data,
                            "message": tool_message,
                            "content": content,
                        }
                        await chat_view.mount(tool_message)
                    chat_view.scroll_end(animate=False)

                elif event.type == "tool_result":
                    # Update the current tool message / collapsible with results
                    tool_call_id = (
                        event.metadata.get("tool_call_id") or last_tool_call_id
                    )
                    state = tool_calls.get(tool_call_id) if tool_call_id else None

                    # If this was a search_text call, render the returned chunks as collapsibles.
                    tool_name = state["name"] if state else None
                    if tool_name == "search_text":
                        if not isinstance(state, dict):
                            continue
                        collapsible = state.get("collapsible")
                        results_container = state.get("results_container")
                        if collapsible is not None:
                            query_str = state.get("query", "")
                            collapsible.title = (
                                f"search_text: {query_str} | {event.data}"
                            )
                        results = event.metadata.get("results", [])
                        if isinstance(results, list) and results:
                            for r in results:
                                if not isinstance(r, dict):
                                    continue
                                source_book = r.get("source_book", "unknown")
                                page = r.get("page", "?")
                                chunk_index = r.get("chunk_index", "?")
                                score = r.get("score", None)
                                score_str = (
                                    f"{float(score):.3f}"
                                    if isinstance(score, (int, float))
                                    else "?"
                                )
                                section = r.get("section", [])
                                section_str = ""
                                if isinstance(section, list) and section:
                                    section_str = " > " + " > ".join(
                                        str(s) for s in section
                                    )
                                title = (
                                    f"[b]{score_str}[/b] - {source_book}:{page}:{chunk_index}"
                                    f"{section_str}"
                                )
                                chunk_text = r.get("text", "")
                                target = (
                                    results_container
                                    if results_container is not None
                                    else chat_view
                                )
                                await target.mount(
                                    Collapsible(
                                        Markdown(chunk_text),
                                        title=title,
                                        collapsed=True,
                                        classes="chunk-collapsible",
                                    )
                                )
                            chat_view.scroll_end(animate=False)
                    else:
                        if state and "message" in state:
                            state["content"] = f"{state['content']} | {event.data}"
                            state["message"].update(state["content"])

                    if tool_call_id and tool_call_id in tool_calls:
                        del tool_calls[tool_call_id]
                    if tool_call_id == last_tool_call_id:
                        last_tool_call_id = None

                elif event.type == "text_delta":
                    # First text -> mount assistant message after tool calls
                    if self._pending_response is None:
                        if self._thinking_message is not None:
                            self._thinking_message.remove()
                            self._thinking_message = None
                        self._pending_response = AssistantMessage("")
                        await chat_view.mount(self._pending_response)
                        self._pending_response.anchor()

                    # Update AssistantMessage with accumulated text
                    accumulated_text += event.data
                    if self._pending_response:
                        self._pending_response.update(accumulated_text)

        except Exception as e:
            if self._pending_response:
                self._pending_response.update(f"**Error:** {e}")
            elif self._thinking_message:
                self._thinking_message.update(f"**Error:** {e}")
        finally:
            # If we never received text, leave tool call logs and clean up placeholder.
            if self._pending_response is None and self._thinking_message is not None:
                self._thinking_message.remove()
                self._thinking_message = None
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

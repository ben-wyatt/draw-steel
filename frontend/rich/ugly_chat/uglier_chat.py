import argparse
import asyncio
import warnings
from datetime import datetime
from typing import List, Tuple

# Globally silence extremely noisy aiohttp + Pydantic warnings for this CLI
_orig_showwarning = warnings.showwarning


def _filtered_showwarning(message, category, filename, lineno, file=None, line=None):
    text = str(message)
    if (
        "enable_cleanup_closed ignored because" in text
        or "Pydantic serializer warnings" in text
        or "PydanticSerializationUnexpectedValue" in text
    ):
        return
    return _orig_showwarning(message, category, filename, lineno, file=file, line=line)


warnings.showwarning = _filtered_showwarning

from agents import Runner  # noqa: E402
from rich.align import Align  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.markdown import Markdown  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.prompt import Prompt  # noqa: E402
from rich.rule import Rule  # noqa: E402
from rich.status import Status  # noqa: E402
from rich.text import Text  # noqa: E402

from backend.agents.draw_steel_expert import create_draw_steel_expert  # noqa: E402
from backend.utils.agent_models import MODEL_MAP  # noqa: E402


class ChatHistory:
    """Manages chat history with formatting."""

    def __init__(self):
        self.messages: List[
            Tuple[str, str, datetime]
        ] = []  # (role, content, timestamp)

    def add(self, role: str, content: str):
        """Add a message to history."""
        self.messages.append((role, content, datetime.now()))

    def clear(self):
        """Clear all messages from history."""
        self.messages = []


def create_header_panel(collection_name: str, model_name: str) -> Panel:
    """Create a styled header panel with collection and model info."""
    header_text = Text(
        f"Draw Steel Expert\nCollection: {collection_name} | Model: {model_name}",
        style="bold white",
    )
    return Panel(
        Align.center(header_text, vertical="middle"),
        border_style="bright_blue",
        title="[bold]🤖 Uglier Chat[/bold]",
        padding=(1, 2),
    )


def create_help_panel() -> Panel:
    """Create a help panel showing available commands."""
    help_text = """
[bold]Available Commands:[/bold]
  • exit, quit, q  - Exit the chat
  • clear          - Clear chat history
  • model <name>   - Switch to a different model
  • models         - List all available models
  • help           - Show this help message
    """
    return Panel(help_text, border_style="blue", title="Help")


def list_models_panel() -> Panel:
    """Create a panel listing all available models."""
    model_list = "\n".join(f"  • {name}" for name in sorted(MODEL_MAP.keys()))
    content = f"[bold]Available Models:[/bold]\n\n{model_list}"
    return Panel(content, border_style="cyan", title="Models")


async def chat(collection_name: str, model_name: str):
    """
    Interactive chat loop using the Draw Steel Expert agent.

    Args:
        collection_name: Name of the database collection to use
        model_name: Name of the model to use
    """
    assert model_name in MODEL_MAP, (
        f"Model '{model_name}' not found. Available models: {', '.join(MODEL_MAP.keys())}"
    )

    # Initialize state
    current_model_name = model_name
    model = MODEL_MAP[current_model_name]
    agent = create_draw_steel_expert(collection_name, model=model)
    console = Console()
    history = ChatHistory()

    # Display header
    console.print(create_header_panel(collection_name, current_model_name))
    console.print(Rule(style="dim"))
    console.print(
        "[dim]Enter your questions. Type 'exit', 'quit', or 'q' to stop. "
        "Type 'clear' to clear history. Type 'help' for commands.[/dim]\n"
    )

    while True:
        try:
            # Use Rich's Prompt for better styling
            query = Prompt.ask("\n[bold cyan]You[/bold cyan]").strip()

            if not query:
                continue

            # Handle exit commands
            if query.lower() in ("exit", "quit", "q"):
                console.print("\n[bold yellow]Exiting...[/bold yellow]")
                break

            # Handle clear command
            if query.lower() == "clear":
                history.clear()
                console.print("[dim]History cleared.[/dim]\n")
                continue

            # Handle help command
            if query.lower() == "help":
                console.print(create_help_panel())
                continue

            # Handle models command
            if query.lower() == "models":
                console.print(list_models_panel())
                continue

            # Handle model switching command
            if query.lower().startswith("model "):
                new_model_name = query[6:].strip()
                if new_model_name in MODEL_MAP:
                    current_model_name = new_model_name
                    model = MODEL_MAP[current_model_name]
                    agent = create_draw_steel_expert(collection_name, model=model)
                    console.print(
                        f"[bold green]✓[/bold green] Switched to model: [bold]{current_model_name}[/bold]"
                    )
                    # Update header display
                    console.print()
                    console.print(
                        create_header_panel(collection_name, current_model_name)
                    )
                    console.print(Rule(style="dim"))
                    console.print()
                else:
                    console.print(
                        Panel(
                            f"[bold red]Error:[/bold red] Model '{new_model_name}' not found.\n\n"
                            f"Available models: {', '.join(sorted(MODEL_MAP.keys()))}",
                            border_style="red",
                            title="Error",
                        )
                    )
                continue

            # Add user query to history
            history.add("user", query)

            # Show thinking status
            with Status(
                "[bold yellow]Thinking...[/bold yellow]",
                console=console,
                spinner="dots",
            ):
                result = await Runner.run(agent, query)

            # Add response to history
            history.add("assistant", result.final_output)

            # Display response in a panel
            console.print()
            console.print(
                Panel(
                    Markdown(result.final_output),
                    border_style="green",
                    title="[bold]Assistant[/bold]",
                    padding=(1, 2),
                )
            )
            console.print()

        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]Exiting...[/bold yellow]")
            break
        except Exception as e:
            error_msg = f"[bold red]Error:[/bold red] {str(e)}"
            console.print()
            console.print(Panel(error_msg, border_style="red", title="Error"))
            import traceback

            console.print("\n[dim]")
            traceback.print_exc()
            console.print("[/dim]\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Draw Steel Expert - Interactive chatbot using agents framework"
    )

    parser.add_argument(
        "--collection-name",
        type=str,
        default="AllBooksV1",
        help="Name of the database collection to use (default: AllBooksV1)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gemini-flash",
        help="Model to use (default: gemini-flash)",
    )

    args = parser.parse_args()

    asyncio.run(chat(args.collection_name, args.model))


if __name__ == "__main__":
    main()

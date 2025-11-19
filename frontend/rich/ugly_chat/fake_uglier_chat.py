from pyfiglet import Figlet
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

## panels


def powered_by_ds():
    """Draw Steel Logo"""
    fig = Figlet(font="ogre").renderText("Draw Steel")
    return Panel(
        Align.center(Text(fig, style="bold white"), vertical="middle"),
        border_style="bright_blue",
        title="[bold]Powered by[/bold]",
        padding=(1, 1),
    )


def config_panel(model_name: str, collection_name: str) -> Panel:
    """Chatbot configuration element"""
    shortcuts_text = Text.from_markup("[bold cyan]![/bold cyan] for shortcuts")
    status_text = Text(
        f"{model_name} | {collection_name}",
        style="dim white",
        justify="right",
    )

    # Create columns with left and right alignment
    content = Columns(
        [shortcuts_text, status_text],
        equal=False,
        expand=True,
    )

    return Panel(
        content,
        border_style="dim",
        height=3,
    )


def main():
    console = Console()
    console.print(Rule(style="dim"))
    console.print(powered_by_ds())
    console.print(config_panel("gemini-flash", "AllBooksV1"))

    console.print("[bold cyan]What is your name?[/] (press enter when ready)")

    # Show elements UNDER the prompt *before* asking for input:
    console.print("[dim]Helpful tips appear down here while waiting…[/]")

    name = console.input("[bold cyan]> [/]")  # behaves like Prompt.ask

    console.print(f"Welcome, {name}!")


if __name__ == "__main__":
    main()


"""
Core elements:
- Powered by Draw Steel
- usage
- Panel for input (claude code like interface)
- custom elements for each type of retrieval


Consider: Textual for the TUI instead of just Rich.

"""

import argparse
import asyncio

from agents import Runner
from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status

from backend.agents.draw_steel_expert import create_draw_steel_expert
from backend.utils.agent_models import MODEL_MAP


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

    model = MODEL_MAP[model_name]
    agent = create_draw_steel_expert(collection_name, model=model)
    console = Console()

    print(f"\nUsing collection: {collection_name}")
    print(f"Using model: {model_name}")
    print("Enter your questions. Type 'exit', 'quit', or 'q' to stop.\n")

    while True:
        try:
            query = input("\nYou: ").strip()

            if not query:
                continue

            if query.lower() in ("exit", "quit", "q"):
                print("\nExiting...")
                break

            with Status("[bold yellow]Thinking...", console=console):
                result = await Runner.run(agent, query)

            console.print()  # New line before markdown
            console.print(Markdown(result.final_output))
            console.print()  # New line after markdown

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback

            traceback.print_exc()


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
        default="gemini-flash-lite",
        help="Model to use (default: gemini-flash-lite). Available: gemini-flash-lite, gemini-flash, gemini-pro, claude-haiku, claude-sonnet, gpt, gpt-mini, gpt-nano",
    )

    args = parser.parse_args()

    asyncio.run(chat(args.collection_name, args.model))


if __name__ == "__main__":
    main()

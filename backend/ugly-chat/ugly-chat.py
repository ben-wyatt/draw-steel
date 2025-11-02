"""
CLI chatbot that uses gpt-5-mini and the database for context-aware responses.

Queries the database first, then sends the full conversation to LLM via OpenRouter.
"""

import argparse
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI
from qdrant_client import QdrantClient
from rich.console import Console
from rich.markdown import Markdown

from backend.database.database import Database
from backend.utils.keys import get_openrouter_api_key

# Set tokenizers parallelism to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# System prompt for the chatbot
SYSTEM_PROMPT = """You are a helpful assistant answering questions about Draw Steel TTRPG rules.
Use the provided context from the rulebook to answer questions accurately.
If the context doesn't contain relevant information, say so."""


def list_collections(db_path: Optional[str] = None) -> list[str]:
    """
    List all available collections in the database.

    Args:
        db_path: Optional path to database directory

    Returns:
        List of collection names
    """
    # Determine db path
    if db_path is None:
        repo_root = Path(__file__).parent.parent.parent
        db_path_obj = repo_root / "backend" / "data" / "db_files"
    else:
        db_path_obj = Path(db_path)

    qdrant_path = db_path_obj / "qdrant"

    # Access Qdrant client directly without creating Database instance
    client = QdrantClient(path=str(qdrant_path))
    try:
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        return collection_names
    finally:
        client.close()


def format_context(results: list[dict]) -> str:
    """
    Format database search results into context string for LLM.

    Args:
        results: List of search result dictionaries

    Returns:
        Formatted context string
    """
    if not results:
        return ""

    context_parts = []
    for i, result in enumerate(results, 1):
        parts = []
        if result.get("page"):
            parts.append(f"Page {result['page']}")
        if result.get("section"):
            section_str = (
                " > ".join(result["section"])
                if isinstance(result["section"], list)
                else str(result["section"])
            )
            parts.append(section_str)

        location = " | ".join(parts) if parts else "Unknown location"
        context_parts.append(f"[{i}] {location}\n{result['text']}")

    return "\n\n".join(context_parts)


def chat(
    collection_name: str,
    limit: int = 5,
    model: str = "google/gemini-2.5-flash-lite",
    db_path: Optional[str] = None,
):
    """
    Interactive chat loop with database context.

    Args:
        collection_name: Name of Qdrant collection to use
        limit: Number of database results to include as context
        model: LLM model to use (default: google/gemini-2.5-flash-lite)
        db_path: Optional path to database directory
    """
    # Check for API key
    api_key = get_openrouter_api_key()
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment or ~/.zshenv")
        sys.exit(1)

    # Initialize OpenAI client for OpenRouter
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    # Initialize Rich console for markdown rendering
    console = Console()

    # Initialize database
    print(f"\nInitializing database with collection: {collection_name}...")
    db_path_obj = Path(db_path) if db_path else None
    db = Database(collection_name=collection_name, db_path=db_path_obj)

    try:
        # Verify collection exists and has data
        info = db.get_collection_info()
        print(f"Collection: {info['name']}")
        print(f"Points: {info['points_count']}")
        print(f"Status: {info['status']}")

        if info["points_count"] == 0:
            print("WARNING: Collection is empty. Chat will work but without context.\n")
        else:
            print()

        print("=" * 80)
        print("Ugly Chat - Interactive Database Chatbot")
        print("=" * 80)
        print(f"Model: {model}")
        print(f"Collection: {collection_name}")
        print(f"Context chunks per query: {limit}")
        print("\nEnter your questions. Type 'exit', 'quit', or 'q' to stop.\n")

        conversation_history = []

        while True:
            try:
                # Get user query
                query = input("\nYou: ").strip()

                if not query:
                    continue

                if query.lower() in ("exit", "quit", "q"):
                    print("\nExiting...")
                    break

                # Search database for context
                print("\n[Searching database...]")
                db_start = time.time()
                db_results = db.search(query=query, limit=limit)
                db_time = time.time() - db_start

                # Format context
                context = format_context(db_results)

                # Build messages
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]

                # Add conversation history
                messages.extend(conversation_history)

                # Add context and current query
                if context:
                    user_message = f"Relevant context from the rulebook:\n\n{context}\n\n---\n\nUser question: {query}"
                else:
                    user_message = query

                messages.append({"role": "user", "content": user_message})

                # Update conversation history (keep last 10 exchanges)
                conversation_history.append({"role": "user", "content": query})
                if len(conversation_history) > 20:  # Keep last 10 user+assistant pairs
                    conversation_history = conversation_history[-20:]

                # Stream response from LLM
                print("\nAssistant: ", end="", flush=True)
                assistant_response = ""

                # Start streaming request
                llm_start = time.time()
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    stream=True,
                )

                # Loading animation while waiting for first token
                loading_stop = threading.Event()

                def loading_animation():
                    """Show '...' animation while waiting for first token."""
                    dots = 0
                    while not loading_stop.is_set():
                        # Show animated dots: ".", "..", "...", then repeat
                        dot_count = (dots % 3) + 1
                        # Clear line and show "Assistant: " with dots
                        print(
                            f"\rAssistant: {'.' * dot_count}{' ' * (3 - dot_count)}",
                            end="",
                            flush=True,
                        )
                        dots += 1
                        time.sleep(0.2)

                loading_thread = threading.Thread(target=loading_animation, daemon=True)
                loading_thread.start()

                # Process stream
                first_token_received = False
                first_token_time = None
                usage = None

                for chunk in stream:
                    # Check for usage information (usually in final chunk)
                    if hasattr(chunk, "usage") and chunk.usage is not None:
                        usage = chunk.usage

                    # Check for content
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content is not None:
                            if not first_token_received:
                                # First token received, stop loading animation
                                first_token_time = time.time() - llm_start
                                loading_stop.set()
                                # Wait a tiny bit for thread to stop
                                time.sleep(0.05)
                                # Clear loading animation and show "Assistant: " again
                                print(
                                    "\r" + " " * 20 + "\rAssistant: ",
                                    end="",
                                    flush=True,
                                )
                                first_token_received = True

                            content = delta.content
                            print(content, end="", flush=True)
                            assistant_response += content

                # Ensure loading animation is stopped
                loading_stop.set()
                time.sleep(0.05)  # Let thread finish

                if not first_token_received:
                    # No tokens received, clear loading animation
                    print("\r" + " " * 20 + "\r", end="", flush=True)

                llm_completion_time = time.time() - llm_start

                print()  # New line after streaming

                # Render markdown if response contains markdown-like content
                if assistant_response.strip():
                    # Check if response looks like markdown (has markdown syntax)
                    has_markdown = any(
                        markdown_pattern in assistant_response
                        for markdown_pattern in ["#", "**", "*", "`", "[", "]", "```"]
                    )
                    if has_markdown:
                        # Render formatted markdown version
                        console.print(Markdown(assistant_response))

                # Print latency breakdown
                print("\n[Latency Breakdown]")
                print(f"  Database retrieval: {db_time * 1000:.1f} ms")
                if first_token_time is not None:
                    print(f"  Time to first token: {first_token_time * 1000:.1f} ms")
                else:
                    print("  Time to first token: N/A (no tokens received)")
                print(f"  Time to completion: {llm_completion_time * 1000:.1f} ms")
                if usage:
                    print(f"  Input tokens: {usage.prompt_tokens}")
                    print(f"  Output tokens: {usage.completion_tokens}")
                else:
                    print("  Token usage: Not available in stream response")
                print()

                # Add assistant response to history
                conversation_history.append(
                    {"role": "assistant", "content": assistant_response}
                )

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                import traceback

                traceback.print_exc()

    finally:
        db.close()


def select_collection_interactive(db_path: Optional[str] = None) -> Optional[str]:
    """
    Interactively select a collection from available collections.

    Args:
        db_path: Optional path to database directory

    Returns:
        Selected collection name or None if cancelled
    """
    collections = list_collections(db_path)

    if not collections:
        print("No collections found in database.")
        return None

    print("\nAvailable collections:")
    for i, name in enumerate(collections, 1):
        print(f"  {i}. {name}")

    while True:
        try:
            choice = input("\nSelect collection (number or name): ").strip()

            if not choice:
                continue

            # Try number first
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(collections):
                    return collections[idx]
                else:
                    print(f"Invalid number. Please enter 1-{len(collections)}")
            except ValueError:
                # Try name match
                if choice in collections:
                    return choice
                else:
                    print(f"Collection '{choice}' not found. Please try again.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ugly Chat - Interactive chatbot with database context"
    )

    parser.add_argument(
        "--collection-name",
        type=str,
        default=None,
        help="Name of Qdrant collection (default: interactive selection)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of database results to include as context (default: 5)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="google/gemini-2.5-flash-lite",
        help="LLM model to use (default: google/gemini-2.5-flash-lite)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to database directory (default: backend/data/db_files)",
    )

    args = parser.parse_args()

    # Select collection if not provided
    collection_name = args.collection_name
    if collection_name is None:
        collection_name = select_collection_interactive(args.db_path)
        if collection_name is None:
            print("No collection selected. Exiting.")
            sys.exit(1)

    # Start chat
    chat(
        collection_name=collection_name,
        limit=args.limit,
        model=args.model,
        db_path=args.db_path,
    )


if __name__ == "__main__":
    main()

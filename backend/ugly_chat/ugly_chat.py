"""
CLI chatbot that uses RAG database for context-aware responses.

Queries the database first, then sends the full conversation to LLM via OpenRouter.
"""

import argparse
import os
import sys
import time
from typing import Optional

from openai import OpenAI
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.status import Status

from backend.database.weaviate_db import WeaviateDatabase, list_collections
from backend.utils.cost import calculate_cost, get_model_pricing
from backend.utils.keys import get_openrouter_api_key

# Set tokenizers parallelism to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# System prompt for the chatbot
SYSTEM_PROMPT = """You are a helpful assistant answering questions about Draw Steel TTRPG rules.
Use the provided context from the rulebook to answer questions accurately.
If the context doesn't contain relevant information, say so.

Respond in markdown formatting, using rich markdown syntax. only use - for lists, not *.

IMPORTANT: Do NOT include citations, page numbers, or reference numbers in your responses.
Do NOT use format like [1], [2], [3] or similar citation markers.
Present information naturally without any citation markers."""


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
    top_k: int = 5,
    model: str = "google/gemini-2.5-flash-lite",
    print_retrieval: bool = False,
):
    """
    Interactive chat loop with database context.

    Args:
        collection_name: Name of Weaviate collection to use
        top_k: Number of database results to include as context
        model: LLM model to use (default: google/gemini-2.5-flash-lite)
        print_retrieval: If True, print the full text of each retrieved chunk
    """
    api_key = get_openrouter_api_key()
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in environment or ~/.zshenv")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    console = Console()

    print(f"\nInitializing database with collection: {collection_name}...")
    db = WeaviateDatabase(collection_name=collection_name)

    try:
        info = db.get_collection_info()
        print(f"Collection: {info['name']}")
        print(f"Vector dimension: {info['vector_dimension']}")
        print(f"Properties: {', '.join(info['properties'])}")
        print(f"Model: {model}")
        print(f"Context chunks per query: {top_k}")
        print()

        print("=" * 8)
        print("uglychat")
        print("=" * 8)

        print("\nEnter your questions. Type 'exit', 'quit', or 'q' to stop.\n")

        conversation_history = []

        while True:
            try:
                # User Query
                query = input("\nYou: ").strip()

                if not query:
                    continue

                if query.lower() in ("exit", "quit", "q"):
                    print("\nExiting...")
                    break

                print("\n[Searching database...]")
                db_start = time.time()
                db_results = db.search(query=query, limit=top_k)
                db_time = time.time() - db_start

                # Print retrieved chunks if requested
                if print_retrieval and db_results:
                    print("\n" + "=" * 70)
                    print(f"Retrieved {len(db_results)} chunks:")
                    print("=" * 70)
                    for i, result in enumerate(db_results, 1):
                        parts = []
                        if result.get("page"):
                            parts.append(f"Page {result['page']}")
                        if result.get("source_book"):
                            parts.append(f"Source: {result['source_book']}")
                        if result.get("section"):
                            section_str = (
                                " > ".join(result["section"])
                                if isinstance(result["section"], list)
                                else str(result["section"])
                            )
                            parts.append(f"Section: {section_str}")
                        if result.get("chunk_index") is not None:
                            parts.append(f"Chunk: {result['chunk_index']}")
                        if result.get("score") is not None:
                            parts.append(f"Score: {result['score']:.4f}")

                        location = " | ".join(parts) if parts else "Unknown location"
                        print(f"\n[{i}] {location}")
                        print("-" * 70)
                        print(result.get("text", ""))
                        print()
                    print("=" * 70 + "\n")

                context = format_context(db_results)
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                messages.extend(conversation_history)

                if context:
                    user_message = f"Relevant context from the rulebook:\n\n{context}\n\n---\n\nUser question: {query}"
                else:
                    user_message = query

                messages.append({"role": "user", "content": user_message})
                conversation_history.append({"role": "user", "content": query})
                if len(conversation_history) > 20:  # Keep last 10 user+assistant pairs
                    conversation_history = conversation_history[-20:]

                assistant_response = ""
                llm_start = time.time()
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    stream=True,
                )

                first_token_received = False
                first_token_time = None
                usage = None

                # Use Rich status spinner while waiting for first token
                with Status("[bold yellow]Thinking...", console=console):
                    for stream_chunk in stream:
                        # Check for usage information (usually in final chunk)
                        if (
                            hasattr(stream_chunk, "usage")
                            and stream_chunk.usage is not None
                        ):
                            usage = stream_chunk.usage

                        # Check for content
                        if stream_chunk.choices and len(stream_chunk.choices) > 0:
                            delta = stream_chunk.choices[0].delta
                            if hasattr(delta, "content") and delta.content is not None:
                                if not first_token_received:
                                    first_token_time = time.time() - llm_start
                                    first_token_received = True
                                    assistant_response = delta.content
                                    break

                if first_token_received:
                    console.print()  # New line before markdown
                    with Live(
                        Markdown(assistant_response),
                        console=console,
                        refresh_per_second=10,
                        vertical_overflow="visible",
                    ) as live:
                        # Process remaining chunks
                        for stream_chunk in stream:
                            # Check for usage information (usually in final chunk)
                            if (
                                hasattr(stream_chunk, "usage")
                                and stream_chunk.usage is not None
                            ):
                                usage = stream_chunk.usage

                            # Check for content
                            if stream_chunk.choices and len(stream_chunk.choices) > 0:
                                delta = stream_chunk.choices[0].delta
                                if (
                                    hasattr(delta, "content")
                                    and delta.content is not None
                                ):
                                    content = delta.content
                                    assistant_response += content
                                    live.update(Markdown(assistant_response))
                else:
                    console.print("\nAssistant: (No response received)")

                llm_completion_time = time.time() - llm_start

                # Latency breakdown
                parts = []
                parts.append(f"db={db_time * 1000:.0f}ms")
                if first_token_time is not None:
                    parts.append(f"TTFT={first_token_time * 1000:.0f}ms")
                else:
                    parts.append("TTFT=N/A")
                parts.append(f"completion={llm_completion_time * 1000:.0f}ms")

                # Calculate cost if we have usage info
                print(f"\n{'|'.join(parts)}")

                if usage:
                    pricing = get_model_pricing(model, api_key)
                    cost = calculate_cost(
                        usage.prompt_tokens, usage.completion_tokens, pricing
                    )
                    if cost is not None:
                        cost_str = f"|${cost:.4f}"
                    else:
                        cost_str = "|$N/A"
                    print(
                        f"token i/o={usage.prompt_tokens}/{usage.completion_tokens}{cost_str}"
                    )
                else:
                    print("tokens in/out = N/A")

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


def select_collection_interactive() -> Optional[str]:
    """
    Interactively select a collection from available collections.

    Returns:
        Selected collection name or None if cancelled
    """
    collections = list_collections()

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

            # Attempt to parse for integer
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
        default="all-books-v1",
        help="Name of Weaviate collection (default: all-books-v1)",
    )
    parser.add_argument(
        "--top-k",
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
        "--print-retrieval",
        action="store_true",
        help="Print the full text of each retrieved chunk",
    )
    args = parser.parse_args()

    collection_name = args.collection_name
    if collection_name is None:
        collection_name = select_collection_interactive()
        if collection_name is None:
            print("No collection selected. Exiting.")
            sys.exit(1)

    chat(
        collection_name=collection_name,
        top_k=args.top_k,
        model=args.model,
        print_retrieval=args.print_retrieval,
    )


if __name__ == "__main__":
    main()

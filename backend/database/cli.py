"""
CLI tool for building and managing the natural language database.

Processes markdown files through chunker and populates Qdrant database.
"""

import argparse
from pathlib import Path
from typing import Optional

from backend.database.chunker import MarkdownChunker
from backend.database.database import Database


def build_database(
    markdown_file: Path,
    collection_name: str = "heroes-full-v1",
    target_tokens: int = 600,
    batch_size: int = 32,
    device: Optional[str] = None,
):
    """
    Build database from markdown file.

    Args:
        markdown_file: Path to markdown file to process
        collection_name: Name of Qdrant collection
        target_tokens: Target chunk size in tokens
        batch_size: Batch size for embedding generation
        device: Device to use for embeddings ('cpu', 'cuda', 'mps', or None for auto-detect)
    """
    if not markdown_file.exists():
        print(f"ERROR: Markdown file not found: {markdown_file}")
        return

    print(f"\nBuilding database from: {markdown_file}")
    print(f"Collection: {collection_name}")
    print(f"Target chunk size: {target_tokens} tokens")
    if device:
        print(f"Device: {device}")
    print()

    # Initialize chunker
    chunker = MarkdownChunker(target_tokens=target_tokens)
    print("Chunking markdown file...")
    chunks = chunker.chunk_file(markdown_file)

    print(f"Created {len(chunks)} chunks")
    if chunks:
        avg_tokens = sum(c.token_count for c in chunks) / len(chunks)
        print(f"Average chunk size: {avg_tokens:.1f} tokens")
        print(
            f"Chunk size range: {min(c.token_count for c in chunks)} - {max(c.token_count for c in chunks)} tokens"
        )

    # Initialize database
    print("\nInitializing database...")
    db = Database(collection_name=collection_name, device=device)
    try:
        # Add chunks to database
        print("\nAdding chunks to database...")
        db.add_chunks(chunks, batch_size=batch_size)

        # Show collection info
        info = db.get_collection_info()
        print("\nDatabase built successfully!")
        print(f"Collection: {info['name']}")
        print(f"Points: {info['points_count']}")
        print(f"Vectors: {info['vectors_count']}")
        print(f"Status: {info['status']}")
    finally:
        db.close()


def test_search(
    collection_name: str = "heroes-full-v1",
    query: str = "surprise round",
    limit: int = 5,
):
    """Test search functionality."""
    print("\nTesting search...")
    print(f"Query: {query}")
    print(f"Limit: {limit}\n")

    db = Database(collection_name=collection_name)
    try:
        results = db.search(query=query, limit=limit)

        print(f"Found {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"Result {i} (score: {result['score']:.4f}):")
            print(f"  Page: {result['page']}")
            print(
                f"  Section: {' > '.join(result['section']) if result['section'] else 'N/A'}"
            )
            print(f"  Tokens: {result['token_count']}")
            print(f"  Text: {result['text']}")
            print()
    finally:
        db.close()


def test_latency(
    collection_name: str = "heroes-full-v1",
    query: str = "surprise round",
    num_runs: int = 10,
):
    """Test search latency."""
    print("\nTesting search latency...")
    print(f"Query: {query}")
    print(f"Runs: {num_runs}\n")

    db = Database(collection_name=collection_name)
    try:
        stats = db.test_latency(query=query, num_runs=num_runs)

        print("Latency Statistics:")
        print(f"  Mean: {stats['mean_ms']:.2f} ms")
        print(f"  Median: {stats['median_ms']:.2f} ms")
        print(f"  Min: {stats['min_ms']:.2f} ms")
        print(f"  Max: {stats['max_ms']:.2f} ms")
        print(f"\nIndividual times (ms): {[f'{t:.2f}' for t in stats['times_ms']]}")
    finally:
        db.close()


def interactive_search(
    collection_name: str = "heroes-full-v1",
    limit: int = 5,
):
    """Interactive search loop."""
    print("\n" + "=" * 80)
    print("Interactive Search Mode")
    print("=" * 80)
    print("Enter queries to search the database. Type 'exit' or 'quit' to stop.\n")

    db = Database(collection_name=collection_name)
    try:
        while True:
            try:
                query = input("\nQuery: ").strip()

                if not query:
                    continue

                if query.lower() in ("exit", "quit", "q"):
                    print("\nExiting...")
                    break

                # Perform search and measure time
                import time

                start = time.time()
                results = db.search(query=query, limit=limit)
                elapsed = (time.time() - start) * 1000  # Convert to ms

                # Display results immediately
                print(f"\n[{elapsed:.1f}ms] Found {len(results)} results:\n")
                for i, result in enumerate(results, 1):
                    print(f"{i}. (score: {result['score']:.4f})")
                    if result["page"]:
                        print(f"   Page {result['page']}", end="")
                    if result["section"]:
                        print(f" > {' > '.join(result['section'])}")
                    else:
                        print()
                    print(f"   {result['text']}")
                    print()

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"\nError: {e}")
    finally:
        db.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build and manage Draw Steel natural language database"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Build command
    build_parser = subparsers.add_parser(
        "build", help="Build database from markdown file"
    )
    build_parser.add_argument(
        "--markdown-file",
        type=Path,
        required=True,
        help="Path to markdown file to process",
    )
    build_parser.add_argument(
        "--collection-name",
        type=str,
        default="heroes-full-v1",
        help="Name of Qdrant collection (default: heroes-full-v1)",
    )
    build_parser.add_argument(
        "--target-tokens",
        type=int,
        default=600,
        help="Target chunk size in tokens (default: 600)",
    )
    build_parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding generation (default: 32)",
    )
    build_parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device to use for embeddings ('cpu', 'cuda', 'mps', or None for auto-detect). "
        "Defaults to 'cpu' to avoid MPS memory issues on macOS.",
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Test search functionality")
    search_parser.add_argument(
        "--collection-name",
        type=str,
        default="heroes-full-v1",
        help="Name of Qdrant collection (default: heroes-full-v1)",
    )
    search_parser.add_argument(
        "--query",
        type=str,
        default="surprise round",
        help="Search query (default: 'surprise round')",
    )
    search_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of results (default: 5)",
    )

    # Latency command
    latency_parser = subparsers.add_parser("latency", help="Test search latency")
    latency_parser.add_argument(
        "--collection-name",
        type=str,
        default="heroes-full-v1",
        help="Name of Qdrant collection (default: heroes-full-v1)",
    )
    latency_parser.add_argument(
        "--query",
        type=str,
        default="surprise round",
        help="Search query (default: 'surprise round')",
    )
    latency_parser.add_argument(
        "--num-runs",
        type=int,
        default=10,
        help="Number of runs for latency test (default: 10)",
    )

    # Interactive search command
    interactive_parser = subparsers.add_parser(
        "interactive", help="Interactive search mode (prompts for queries)"
    )
    interactive_parser.add_argument(
        "--collection-name",
        type=str,
        default="heroes-full-v1",
        help="Name of Qdrant collection (default: heroes-full-v1)",
    )
    interactive_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of results per query (default: 5)",
    )

    args = parser.parse_args()

    if args.command == "build":
        build_database(
            markdown_file=args.markdown_file,
            collection_name=args.collection_name,
            target_tokens=args.target_tokens,
            batch_size=args.batch_size,
            device=args.device,
        )
    elif args.command == "search":
        test_search(
            collection_name=args.collection_name,
            query=args.query,
            limit=args.limit,
        )
    elif args.command == "latency":
        test_latency(
            collection_name=args.collection_name,
            query=args.query,
            num_runs=args.num_runs,
        )
    elif args.command == "interactive":
        interactive_search(
            collection_name=args.collection_name,
            limit=args.limit,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

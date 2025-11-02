"""
CLI tool for building and managing the natural language database.

Processes markdown files through chunker and populates Qdrant database.
"""

import argparse
from pathlib import Path
from typing import Optional

from qdrant_client.models import Distance, PointStruct, VectorParams
from rich.console import Console
from rich.markdown import Markdown
from tqdm import tqdm

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
    console = Console()
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

                # Display results with markdown rendering
                print(f"\n[{elapsed:.1f}ms] Found {len(results)} results:\n")
                for i, result in enumerate(results, 1):
                    # Print metadata
                    metadata_parts = [f"{i}. (score: {result['score']:.4f})"]
                    if result["page"]:
                        metadata_parts.append(f"Page {result['page']}")
                    if result["section"]:
                        section_str = (
                            " > ".join(result["section"])
                            if isinstance(result["section"], list)
                            else str(result["section"])
                        )
                        metadata_parts.append(section_str)
                    print(" | ".join(metadata_parts))

                    # Render text as markdown if it looks like markdown, otherwise as plain text
                    text = result["text"]
                    has_markdown = any(
                        markdown_pattern in text
                        for markdown_pattern in ["#", "**", "*", "`", "[", "]", "```"]
                    )
                    if has_markdown:
                        console.print(Markdown(text))
                    else:
                        print(f"   {text}")
                    print()

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"\nError: {e}")
    finally:
        db.close()


def delete_collection(
    collection_name: str,
    force: bool = False,
):
    """Delete a collection."""
    db = Database(collection_name=collection_name)
    try:
        # Check if collection exists
        collections = db.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if collection_name not in collection_names:
            print(f"ERROR: Collection '{collection_name}' not found")
            return

        # Get collection info
        info = db.client.get_collection(collection_name)
        print(f"\nCollection: {collection_name}")
        print(f"Points: {info.points_count}")
        print(f"Vectors: {info.vectors_count}")
        print(f"Status: {info.status}")

        if not force:
            response = (
                input(
                    f"\nAre you sure you want to delete '{collection_name}'? (yes/no): "
                )
                .strip()
                .lower()
            )
            if response != "yes":
                print("Aborted.")
                return

        print(f"\nDeleting collection '{collection_name}'...")
        db.client.delete_collection(collection_name)
        print(f"Collection '{collection_name}' deleted successfully.")
    finally:
        db.close()


def combine_collections(
    source_collection_1: str,
    source_collection_2: str,
    target_collection: str,
    batch_size: int = 100,
):
    """
    Combine two Qdrant collections into a new collection.

    Args:
        source_collection_1: Name of first source collection
        source_collection_2: Name of second source collection
        target_collection: Name of target collection to create
        batch_size: Batch size for upserting points (default: 100)
    """
    print("\nCombining collections:")
    print(f"  Source 1: {source_collection_1}")
    print(f"  Source 2: {source_collection_2}")
    print(f"  Target: {target_collection}\n")

    # Use a single Database instance to access all collections through the same client
    # This avoids the "already accessed" error with Qdrant's local client
    db = Database(collection_name=source_collection_1)

    try:
        # Check that both source collections exist
        collections = db.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if source_collection_1 not in collection_names:
            print(f"ERROR: Source collection '{source_collection_1}' not found")
            return
        if source_collection_2 not in collection_names:
            print(f"ERROR: Source collection '{source_collection_2}' not found")
            return

        # Check if target collection already exists
        if target_collection in collection_names:
            print(f"WARNING: Target collection '{target_collection}' already exists")
            response = input("Do you want to overwrite it? (yes/no): ").strip().lower()
            if response != "yes":
                print("Aborted.")
                return
            print(f"Deleting existing collection '{target_collection}'...")
            db.client.delete_collection(target_collection)

        # Get collection info to check vector dimensions
        coll1_info = db.client.get_collection(source_collection_1)
        coll2_info = db.client.get_collection(source_collection_2)

        # Access vector dimension (handles both named and unnamed vectors)
        vectors1 = coll1_info.config.params.vectors
        vectors2 = coll2_info.config.params.vectors

        if vectors1 is None or vectors2 is None:
            print("ERROR: Collections must have vector configuration")
            return

        # Handle both dict (named vectors) and VectorParams (unnamed vectors)
        if isinstance(vectors1, dict):
            # Named vectors - get first vector config
            dim1 = next(iter(vectors1.values())).size
        else:
            dim1 = vectors1.size

        if isinstance(vectors2, dict):
            dim2 = next(iter(vectors2.values())).size
        else:
            dim2 = vectors2.size

        if dim1 != dim2:
            print(
                f"ERROR: Collections have incompatible vector dimensions: "
                f"{source_collection_1} has {dim1}, {source_collection_2} has {dim2}"
            )
            return

        print(f"Vector dimension: {dim1}")
        print(f"Points in {source_collection_1}: {coll1_info.points_count}")
        print(f"Points in {source_collection_2}: {coll2_info.points_count}")

        # Create target collection
        print(f"\nCreating target collection '{target_collection}'...")
        db.client.create_collection(
            collection_name=target_collection,
            vectors_config=VectorParams(
                size=dim1,
                distance=Distance.COSINE,
            ),
        )

        # Retrieve all points from both collections
        all_points = []

        print(f"\nRetrieving points from '{source_collection_1}'...")
        offset = None
        while True:
            result, offset = db.client.scroll(
                collection_name=source_collection_1,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            all_points.extend(result)
            if offset is None:
                break
        print(f"Retrieved {len(all_points)} points from '{source_collection_1}'")

        print(f"\nRetrieving points from '{source_collection_2}'...")
        offset = None
        points_from_2 = 0
        while True:
            result, offset = db.client.scroll(
                collection_name=source_collection_2,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            all_points.extend(result)
            points_from_2 += len(result)
            if offset is None:
                break
        print(f"Retrieved {points_from_2} points from '{source_collection_2}'")

        print(f"\nTotal points to add: {len(all_points)}")

        # Convert to PointStruct and upsert in batches
        print(f"\nAdding points to '{target_collection}'...")
        point_structs = [
            PointStruct(
                id=point.id,
                vector=point.vector,
                payload=point.payload,
            )
            for point in all_points
        ]

        # Upsert in batches
        for i in tqdm(
            range(0, len(point_structs), batch_size),
            desc="Upserting points",
            unit="batch",
        ):
            batch = point_structs[i : i + batch_size]
            db.client.upsert(collection_name=target_collection, points=batch)

        # Show final collection info
        target_info = db.client.get_collection(target_collection)
        print("\nCollections combined successfully!")
        print(f"Target collection: {target_collection}")
        print(f"Total points: {target_info.points_count}")
        print(f"Vectors: {target_info.vectors_count}")
        print(f"Status: {target_info.status}")

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

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a collection")
    delete_parser.add_argument(
        "--collection-name",
        type=str,
        required=True,
        help="Name of collection to delete",
    )
    delete_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # Combine command
    combine_parser = subparsers.add_parser(
        "combine", help="Combine two collections into a new one"
    )
    combine_parser.add_argument(
        "--source-collection-1",
        type=str,
        required=True,
        help="Name of first source collection",
    )
    combine_parser.add_argument(
        "--source-collection-2",
        type=str,
        required=True,
        help="Name of second source collection",
    )
    combine_parser.add_argument(
        "--target-collection",
        type=str,
        required=True,
        help="Name of target collection to create",
    )
    combine_parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for upserting points (default: 100)",
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
    elif args.command == "delete":
        delete_collection(
            collection_name=args.collection_name,
            force=args.force,
        )
    elif args.command == "combine":
        combine_collections(
            source_collection_1=args.source_collection_1,
            source_collection_2=args.source_collection_2,
            target_collection=args.target_collection,
            batch_size=args.batch_size,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

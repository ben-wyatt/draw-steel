"""
CLI tool for building and managing the natural language database.

Processes JSON transcription files through chunker and populates Weaviate database.
"""

import argparse
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from tqdm import tqdm

from backend.database.weaviate_db import WeaviateDatabase


def build_from_json(
    json_file: Path,
    collection_name: str = "heroes-full-v1",
    source_book: str = "heroes",
    min_char_len: int = 1000,
    batch_size: int = 32,
    device: Optional[str] = None,
):
    """
    Build database from JSON transcription file.

    Args:
        json_file: Path to JSON file containing page transcriptions
        collection_name: Name of Weaviate collection
        source_book: Source book identifier (e.g., 'heroes', 'monsters')
        min_char_len: Minimum character length for chunks before concatenation
        batch_size: Batch size for embedding generation
        device: Device to use for embeddings ('cpu', 'cuda', 'mps', or None for auto-detect)
    """
    if not json_file.exists():
        print(f"ERROR: JSON file not found: {json_file}")
        return

    print(f"\nBuilding database from: {json_file}")
    print(f"Collection: {collection_name}")
    print(f"Source book: {source_book}")
    print(f"Min chunk length: {min_char_len} characters")
    if device:
        print(f"Device: {device}")
    print()

    # Initialize database
    print("Initializing database...")
    db = WeaviateDatabase(collection_name=collection_name, device=device)
    try:
        # Load JSON, chunk it, and add to database
        db.add_from_json(
            json_path=json_file,
            source_book=source_book,
            min_char_len=min_char_len,
            batch_size=batch_size,
        )

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

    db = WeaviateDatabase(collection_name=collection_name)
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

    db = WeaviateDatabase(collection_name=collection_name)
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

    db = WeaviateDatabase(collection_name=collection_name)
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
    db = WeaviateDatabase(collection_name=collection_name)
    try:
        # Normalize collection name
        normalized_name = db._normalize_collection_name(collection_name)

        # Check if collection exists
        if not db.client.collections.exists(normalized_name):
            print(
                f"ERROR: Collection '{collection_name}' (normalized: '{normalized_name}') not found"
            )
            return

        # Get collection info
        collection = db.client.collections.get(normalized_name)
        aggregate_result = collection.aggregate.over_all(total_count=True)
        points_count = (
            aggregate_result.total_count
            if hasattr(aggregate_result, "total_count")
            else 0
        )

        print(f"\nCollection: {collection_name} (normalized: {normalized_name})")
        print(f"Points: {points_count}")
        print(f"Vectors: {points_count}")

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

        print(f"\nDeleting collection '{normalized_name}'...")
        db.client.collections.delete(normalized_name)
        print(f"Collection '{normalized_name}' deleted successfully.")
    finally:
        db.close()


def combine_collections(
    source_collection_1: str,
    source_collection_2: str,
    target_collection: str,
    batch_size: int = 100,
):
    """
    Combine two Weaviate collections into a new collection.

    Args:
        source_collection_1: Name of first source collection
        source_collection_2: Name of second source collection
        target_collection: Name of target collection to create
        batch_size: Batch size for adding objects (default: 100)
    """
    print("\nCombining collections:")
    print(f"  Source 1: {source_collection_1}")
    print(f"  Source 2: {source_collection_2}")
    print(f"  Target: {target_collection}\n")

    # Use a single WeaviateDatabase instance to access all collections
    db = WeaviateDatabase(collection_name=source_collection_1)

    try:
        # Normalize collection names
        norm_name_1 = db._normalize_collection_name(source_collection_1)
        norm_name_2 = db._normalize_collection_name(source_collection_2)
        norm_target = db._normalize_collection_name(target_collection)

        # Check that both source collections exist
        all_collections = db.client.collections.list_all()

        if norm_name_1 not in all_collections:
            print(
                f"ERROR: Source collection '{source_collection_1}' (normalized: '{norm_name_1}') not found"
            )
            return
        if norm_name_2 not in all_collections:
            print(
                f"ERROR: Source collection '{source_collection_2}' (normalized: '{norm_name_2}') not found"
            )
            return

        # Check if target collection already exists
        if norm_target in all_collections:
            print(
                f"WARNING: Target collection '{target_collection}' (normalized: '{norm_target}') already exists"
            )
            response = input("Do you want to overwrite it? (yes/no): ").strip().lower()
            if response != "yes":
                print("Aborted.")
                return
            print(f"Deleting existing collection '{norm_target}'...")
            db.client.collections.delete(norm_target)

        # Get collection info to check vector dimensions
        coll1 = db.client.collections.get(norm_name_1)
        coll2 = db.client.collections.get(norm_name_2)

        # Get vector dimensions from embedding model (both should use same model)
        dim1 = db.embedding_dim
        dim2 = db.embedding_dim

        if dim1 != dim2:
            print(
                f"ERROR: Collections have incompatible vector dimensions: "
                f"{source_collection_1} has {dim1}, {source_collection_2} has {dim2}"
            )
            return

        # Get point counts
        agg1 = coll1.aggregate.over_all(total_count=True)
        agg2 = coll2.aggregate.over_all(total_count=True)
        count1 = agg1.total_count if hasattr(agg1, "total_count") else 0
        count2 = agg2.total_count if hasattr(agg2, "total_count") else 0

        print(f"Vector dimension: {dim1}")
        print(f"Points in {source_collection_1}: {count1}")
        print(f"Points in {source_collection_2}: {count2}")

        # Create target collection using a temporary database instance
        print(f"\nCreating target collection '{target_collection}'...")
        target_db = WeaviateDatabase(collection_name=target_collection)
        target_db.close()  # Close after creation

        # Fetch all objects with vectors from both collections
        print(f"\nFetching objects with vectors from '{source_collection_1}'...")
        all_data = []
        offset = None
        limit = 1000

        # Fetch from collection 1 with vectors
        while True:
            response = coll1.query.fetch_objects(
                limit=limit,
                offset=offset,
                return_metadata=None,
                include_vector=True,
            )
            if not response.objects:
                break
            for obj in response.objects:
                # Extract vector - Weaviate returns vectors as dict with "default" key for self-provided vectors
                vector = None
                if hasattr(obj, "vector") and obj.vector:
                    if isinstance(obj.vector, dict):
                        vector = obj.vector.get("default")
                    elif isinstance(obj.vector, list):
                        vector = obj.vector
                all_data.append(
                    {
                        "properties": obj.properties,
                        "vector": vector,
                    }
                )
            if len(response.objects) < limit:
                break
            offset = limit if offset is None else offset + limit
        print(f"Retrieved {len(all_data)} objects from '{source_collection_1}'")

        # Fetch from collection 2 with vectors
        print(f"\nFetching objects with vectors from '{source_collection_2}'...")
        offset = None
        objects_from_2 = 0
        while True:
            response = coll2.query.fetch_objects(
                limit=limit,
                offset=offset,
                return_metadata=None,
                include_vector=True,
            )
            if not response.objects:
                break
            for obj in response.objects:
                # Extract vector - Weaviate returns vectors as dict with "default" key for self-provided vectors
                vector = None
                if hasattr(obj, "vector") and obj.vector:
                    if isinstance(obj.vector, dict):
                        vector = obj.vector.get("default")
                    elif isinstance(obj.vector, list):
                        vector = obj.vector
                all_data.append(
                    {
                        "properties": obj.properties,
                        "vector": vector,
                    }
                )
                objects_from_2 += 1
            if len(response.objects) < limit:
                break
            offset = limit if offset is None else offset + limit
        print(f"Retrieved {objects_from_2} objects from '{source_collection_2}'")

        print(f"\nTotal objects to add: {len(all_data)}")

        # Add objects to target collection in batches
        print(f"\nAdding objects to '{target_collection}'...")
        target_db = WeaviateDatabase(collection_name=target_collection)
        try:
            target_collection_obj = target_db.client.collections.get(norm_target)
            with target_collection_obj.batch.dynamic() as batch:
                for i, data in enumerate(
                    tqdm(all_data, desc="Adding objects", unit="obj")
                ):
                    batch.add_object(
                        properties=data["properties"],
                        vector=data["vector"],
                    )
                    # Batch automatically flushes when it reaches internal size limit
                    # or when context manager exits
        finally:
            target_db.close()

        # Show final collection info
        final_db = WeaviateDatabase(collection_name=target_collection)
        try:
            info = final_db.get_collection_info()
            print("\nCollections combined successfully!")
            print(f"Target collection: {target_collection}")
            print(f"Total points: {info['points_count']}")
            print(f"Vectors: {info['vectors_count']}")
            print(f"Status: {info['status']}")
        finally:
            final_db.close()

    finally:
        db.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build and manage Draw Steel natural language database"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Build command (from JSON)
    build_parser = subparsers.add_parser(
        "build", help="Build database from JSON transcription file"
    )
    build_parser.add_argument(
        "--json-file",
        type=Path,
        required=True,
        help="Path to JSON file containing page transcriptions",
    )
    build_parser.add_argument(
        "--collection-name",
        type=str,
        default="all-books-v1",
        help="Name of Weaviate collection (default: all-books-v1)",
    )
    build_parser.add_argument(
        "--source-book",
        type=str,
        default="heroes",
        help="Source book identifier (e.g., 'heroes', 'monsters') (default: heroes)",
    )
    build_parser.add_argument(
        "--min-char-len",
        type=int,
        default=1000,
        help="Minimum character length for chunks before concatenation (default: 1000)",
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
        help="Name of Weaviate collection (default: heroes-full-v1)",
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
        default="all-books-v1",
        help="Name of Weaviate collection (default: all-books-v1)",
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
        default="all-books-v1",
        help="Name of Weaviate collection (default: all-books-v1)",
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
        build_from_json(
            json_file=args.json_file,
            collection_name=args.collection_name,
            source_book=args.source_book,
            min_char_len=args.min_char_len,
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

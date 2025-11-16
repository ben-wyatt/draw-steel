import argparse
import random
import statistics
from pathlib import Path
from typing import List, Optional

from backend.database.chunker import Chunk
from backend.database.weaviate_db import WeaviateDatabase


def analyze_chunks(chunks: List[Chunk]) -> None:
    """
    Summary stats on chunk distribution by character length.
    num chunks, mean chunk size, median, min, max, std
    percentiles
    """
    char_counts = [len(chunk.text) for chunk in chunks]
    sorted_char_counts = sorted(char_counts)
    print(f"Total chunks: {len(chunks)}")
    print(f"Mean chunk size: {statistics.mean(char_counts):.2f}")
    print(f"Median chunk size: {statistics.median(char_counts):.2f}")
    print(f"Min chunk size: {min(char_counts):.2f}")
    print(f"Max chunk size: {max(char_counts):.2f}")
    print(f"Std chunk size: {statistics.stdev(char_counts):.2f}")
    print(f"25th percentile: {sorted_char_counts[len(sorted_char_counts) // 4]:.2f}")
    print(
        f"75th percentile: {sorted_char_counts[3 * len(sorted_char_counts) // 4]:.2f}"
    )
    print(
        f"90th percentile: {sorted_char_counts[9 * len(sorted_char_counts) // 10]:.2f}"
    )
    print(
        f"95th percentile: {sorted_char_counts[19 * len(sorted_char_counts) // 20]:.2f}"
    )
    # other stats
    ability_blocks = [len(chunk.ability_blocks) for chunk in chunks]
    monster_blocks = [len(chunk.monster_blocks) for chunk in chunks]
    item_blocks = [len(chunk.item_blocks) for chunk in chunks]
    other_blocks = [len(chunk.other_blocks) for chunk in chunks]
    print(f"Found {sum(ability_blocks)} ability blocks")
    print(f"Found {sum(monster_blocks)} monster blocks")
    print(f"Found {sum(item_blocks)} item blocks")
    print(f"Found {sum(other_blocks)} other blocks")


def _print_chunk_info(chunk: Chunk, chunk_num: int) -> None:
    """Print metadata and content for a chunk."""
    print(f"\n--- Chunk #{chunk_num} ---")
    if chunk.page is not None:
        print(f"Page: {chunk.page}")
    if chunk.source_book:
        print(f"Source Book: {chunk.source_book}")
    if chunk.section:
        section_str = " > ".join(chunk.section)
        print(f"Section: {section_str}")
    if chunk.chunk_index > 0:
        print(f"Chunk Index: {chunk.chunk_index}")
    print(f"Length: {len(chunk.text)} chars")
    if chunk.token_count > 0:
        print(f"Token Count: {chunk.token_count}")
    if len(chunk.ability_blocks) > 0:
        print(f"Ability Blocks: {chunk.ability_blocks}")
    if len(chunk.monster_blocks) > 0:
        print(f"Monster Blocks: {chunk.monster_blocks}")
    if len(chunk.item_blocks) > 0:
        print(f"Item Blocks: {chunk.item_blocks}")
    if len(chunk.other_blocks) > 0:
        print(f"Other Blocks: {chunk.other_blocks}")
    print("\n--- Content ---")
    print(chunk.text)


def loop_through_sequential_chunks(chunks: List[Chunk]) -> None:
    num_chunks = len(chunks)
    print(
        f"Press Enter to see a chunk (out of {num_chunks}), or 'q' then Enter to quit."
    )
    for i, chunk in enumerate(chunks):
        user_input = input("\n--- Press Enter for another chunk, or 'q' to quit ---")
        if user_input.strip().lower() == "q":
            print("Exiting.")
            break
        _print_chunk_info(chunk, i + 1)


def loop_through_random_chunks(chunks: List[Chunk]) -> None:
    shown_indices = set()
    num_chunks = len(chunks)
    print(
        f"Press Enter to see a random chunk (out of {num_chunks}), or 'q' then Enter to quit."
    )
    while len(shown_indices) < num_chunks:
        user_input = input()
        if user_input.strip().lower() == "q":
            print("Exiting.")
            break
        # Pick an unseen random chunk
        remaining_indices = list(set(range(num_chunks)) - shown_indices)
        idx = random.choice(remaining_indices)
        _print_chunk_info(chunks[idx], idx + 1)
        shown_indices.add(idx)
        if len(shown_indices) < num_chunks:
            print("\n--- Press Enter for another chunk, or 'q' to quit ---")
        else:
            print("\n--- All chunks have been shown! ---")


def load_chunks_from_collection(
    collection_name: str, db_path: Optional[Path] = None
) -> List[Chunk]:
    """
    Load all chunks from a database collection.

    Args:
        collection_name: Name of the Weaviate collection
        db_path: Optional path to database directory (ignored for Weaviate)

    Returns:
        List of Chunk objects
    """
    db = WeaviateDatabase(collection_name=collection_name)
    try:
        chunks = []
        offset = None
        limit = 1000

        print(f"Loading chunks from collection '{collection_name}'...")
        # Use normalized collection name (Weaviate normalizes collection names)
        normalized_name = db._normalize_collection_name(collection_name)
        collection = db.client.collections.get(normalized_name)

        while True:
            # Fetch objects with pagination
            response = collection.query.fetch_objects(
                limit=limit,
                offset=offset,
                return_metadata=None,
            )

            if not response.objects:
                break

            for obj in response.objects:
                props = obj.properties

                # Type-safe property extraction with defaults
                text_val = props.get("text")
                text = str(text_val) if text_val is not None else ""

                page_val = props.get("page")
                page = (
                    int(page_val)
                    if isinstance(page_val, (int, float)) and page_val is not None
                    else None
                )

                source_book_val = props.get("source_book")
                source_book = (
                    str(source_book_val) if source_book_val is not None else ""
                )

                # Handle list properties - blocks are stored as TEXT_ARRAY (List[str]) in Weaviate
                # but Chunk expects List[dict], so we convert strings to dicts
                # If items are already dicts, use them as-is
                def _convert_block_item(item):
                    """Convert block item to dict format."""
                    if isinstance(item, dict):
                        return item
                    elif isinstance(item, (str, int, float, bool)):
                        return {"name": str(item)}
                    else:
                        return {}

                ability_blocks_raw = props.get("ability_blocks")
                if isinstance(ability_blocks_raw, list):
                    ability_blocks = [
                        _convert_block_item(item) for item in ability_blocks_raw
                    ]
                else:
                    ability_blocks = []

                monster_blocks_raw = props.get("monster_blocks")
                if isinstance(monster_blocks_raw, list):
                    monster_blocks = [
                        _convert_block_item(item) for item in monster_blocks_raw
                    ]
                else:
                    monster_blocks = []

                item_blocks_raw = props.get("item_blocks")
                if isinstance(item_blocks_raw, list):
                    item_blocks = [
                        _convert_block_item(item) for item in item_blocks_raw
                    ]
                else:
                    item_blocks = []

                other_blocks_raw = props.get("other_blocks")
                if isinstance(other_blocks_raw, list):
                    other_blocks = [
                        _convert_block_item(item) for item in other_blocks_raw
                    ]
                else:
                    other_blocks = []

                # Handle section - should be List[str] or None
                section_raw = props.get("section")
                if isinstance(section_raw, list):
                    section = [str(s) for s in section_raw if s is not None]
                else:
                    section = None

                # Handle integer properties with proper type checking
                chunk_index_val = props.get("chunk_index")
                if (
                    isinstance(chunk_index_val, (int, float))
                    and chunk_index_val is not None
                ):
                    chunk_index = int(chunk_index_val)
                else:
                    chunk_index = 0

                token_count_val = props.get("token_count")
                if (
                    isinstance(token_count_val, (int, float))
                    and token_count_val is not None
                ):
                    token_count = int(token_count_val)
                else:
                    token_count = 0

                chunk = Chunk(
                    text=text,
                    page=page,
                    source_book=source_book,
                    chunk_id=str(obj.uuid),
                    ability_blocks=ability_blocks,
                    monster_blocks=monster_blocks,
                    item_blocks=item_blocks,
                    other_blocks=other_blocks,
                    section=section,
                    chunk_index=chunk_index,
                    token_count=token_count,
                )
                chunks.append(chunk)

            # Check if we've fetched all objects
            if len(response.objects) < limit:
                break

            # Update offset for next batch
            if offset is None:
                offset = limit
            else:
                offset += limit

        print(f"Loaded {len(chunks)} chunks")
        return chunks
    finally:
        db.close()


def main():
    """CLI entry point for chunk inspector."""
    parser = argparse.ArgumentParser(
        description="Inspect chunks from a database collection"
    )
    parser.add_argument(
        "collection",
        type=str,
        help="Name of the collection to inspect",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["sequential", "random"],
        default="random",
        help="Mode for browsing chunks: sequential or random (default: random)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Optional path to database directory (ignored for Weaviate)",
    )

    args = parser.parse_args()

    # Convert db_path string to Path if provided
    db_path = Path(args.db_path) if args.db_path else None

    # Load chunks from collection
    chunks = load_chunks_from_collection(
        collection_name=args.collection, db_path=db_path
    )

    if not chunks:
        print(f"No chunks found in collection '{args.collection}'")
        return

    # Print summary stats
    print("\n" + "=" * 60)
    analyze_chunks(chunks)
    print("=" * 60 + "\n")

    # Browse chunks based on mode
    if args.mode == "sequential":
        loop_through_sequential_chunks(chunks)
    else:
        loop_through_random_chunks(chunks)


if __name__ == "__main__":
    main()

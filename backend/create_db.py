"""Create Weaviate collection from transcription JSON files.

Loads JSON transcription files, chunks them, and adds to Weaviate collection.
"""

from pathlib import Path

from backend.database.weaviate_db import WeaviateDatabase


def main():
    """Build Weaviate collection from transcription JSON files."""
    # Configuration
    collection_name = "AllBooksV1"
    min_char_len = 1000
    batch_size = 32

    # Paths and source books
    json_paths = [
        ("backend/data/delian_tomb/page_transcription.json", "delian_tomb"),
        ("backend/data/heroes/page_transcription.json", "heroes"),
        ("backend/data/monsters/page_transcription.json", "monsters"),
    ]

    # Check if all JSON files exist
    missing_files = []
    for json_path_str, _ in json_paths:
        json_path = Path(json_path_str)
        if not json_path.exists():
            missing_files.append(json_path_str)

    if missing_files:
        print("ERROR: JSON files not found:")
        for path in missing_files:
            print(f"  - {path}")
        return

    print("\nBuilding Weaviate collection")
    print(f"Collection: {collection_name}")
    print(f"Min chunk length: {min_char_len} characters")
    print(f"Processing {len(json_paths)} source books:")
    for json_path_str, source_book in json_paths:
        print(f"  - {source_book}: {json_path_str}")
    print()

    # Initialize Weaviate database (embedded by default)
    print("Initializing Weaviate database...")
    db = WeaviateDatabase(collection_name=collection_name)
    try:
        # Process each JSON file
        for json_path_str, source_book in json_paths:
            json_path = Path(json_path_str)
            print(f"\n{'=' * 60}")
            print(f"Processing: {source_book}")
            print(f"File: {json_path}")
            print(f"{'=' * 60}")

            # Load JSON, chunk it, and add to database
            db.add_from_json(
                json_path=json_path,
                source_book=source_book,
                min_char_len=min_char_len,
                batch_size=batch_size,
            )

        # Show collection info
        info = db.get_collection_info()
        print("\n" + "=" * 60)
        print("Database built successfully!")
        print(f"Collection: {info['name']}")
        print(f"Vector dimension: {info['vector_dimension']}")
        print(f"Properties: {', '.join(info['properties'])}")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()

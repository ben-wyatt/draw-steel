"""Test retrieval performance for Weaviate search methods.

Benchmarks vector search, text search (BM25), and hybrid search.
"""

import time
from statistics import mean, stdev

from backend.database.weaviate_db import WeaviateDatabase


def benchmark_search(
    db: WeaviateDatabase,
    search_method: str,
    query: str,
    limit: int = 10,
    num_runs: int = 5,
) -> tuple[list[dict], dict]:
    """
    Benchmark a search method and return results with timing stats.

    Args:
        db: WeaviateDatabase instance
        search_method: 'vector', 'text', or 'hybrid'
        query: Search query string
        limit: Number of results to return
        num_runs: Number of runs for averaging

    Returns:
        Tuple of (results, stats_dict) where stats_dict contains timing info
    """
    times = []
    results: list[dict] = []

    for _ in range(num_runs):
        start = time.perf_counter()
        if search_method == "vector":
            results = db.vector_search(query=query, limit=limit)
        elif search_method == "text":
            results = db.text_search(query=query, limit=limit)
        elif search_method == "hybrid":
            results = db.hybrid_search(query=query, limit=limit)
        else:
            raise ValueError(f"Unknown search method: {search_method}")

        elapsed = time.perf_counter() - start
        times.append(elapsed)

    stats = {
        "mean": mean(times),
        "stdev": stdev(times) if len(times) > 1 else 0.0,
        "min": min(times),
        "max": max(times),
        "num_runs": num_runs,
    }

    return results, stats


def format_time(seconds: float) -> str:
    """Format time in seconds to readable string."""
    if seconds < 0.001:
        return f"{seconds * 1_000_000:.2f} μs"
    elif seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.3f} s"


def print_results(results: list[dict], limit: int = 3):
    """Print top search results."""
    print(f"\n  Top {min(limit, len(results))} results:")
    for i, result in enumerate(results[:limit], 1):
        text_preview = result["text"][:100].replace("\n", " ")
        if len(result["text"]) > 100:
            text_preview += "..."
        print(
            f"    {i}. [Page {result['page']}] "
            f"Score: {result['score']:.4f} - {text_preview}"
        )


def main():
    """Run performance benchmarks for all search methods."""
    collection_name = "all-books-v1"
    num_runs = 5
    limit = 10

    # Test queries covering different types
    test_queries = [
        "combat abilities",
        "character creation",
        "magic spells",
        "equipment and weapons",
        "skill checks",
    ]

    print("Testing Weaviate search performance")
    print(f"Collection: {collection_name}")
    print(f"Runs per query: {num_runs}")
    print(f"Results per query: {limit}")
    print("=" * 70)

    # Initialize database
    print("\nInitializing Weaviate database...")
    db = WeaviateDatabase(collection_name=collection_name)

    try:
        # Get collection info
        info = db.get_collection_info()
        print(f"Collection: {info['name']}")
        print(f"Vector dimension: {info['vector_dimension']}")
        print()

        # Test each query
        all_stats = {"vector": [], "text": [], "hybrid": []}

        for query_idx, query in enumerate(test_queries, 1):
            print(f"\n{'=' * 70}")
            print(f"Query {query_idx}/{len(test_queries)}: '{query}'")
            print("=" * 70)

            # Test vector search
            print("\n1. Vector Search (Semantic):")
            results, stats = benchmark_search(
                db, "vector", query, limit=limit, num_runs=num_runs
            )
            all_stats["vector"].append(stats)
            print(f"   Mean: {format_time(stats['mean'])}")
            print(f"   Min:  {format_time(stats['min'])}")
            print(f"   Max:  {format_time(stats['max'])}")
            if stats["stdev"] > 0:
                print(f"   Std:  {format_time(stats['stdev'])}")
            print_results(results, limit=2)

            # Test text search
            print("\n2. Text Search (BM25):")
            results, stats = benchmark_search(
                db, "text", query, limit=limit, num_runs=num_runs
            )
            all_stats["text"].append(stats)
            print(f"   Mean: {format_time(stats['mean'])}")
            print(f"   Min:  {format_time(stats['min'])}")
            print(f"   Max:  {format_time(stats['max'])}")
            if stats["stdev"] > 0:
                print(f"   Std:  {format_time(stats['stdev'])}")
            print_results(results, limit=2)

            # Test hybrid search
            print("\n3. Hybrid Search (Vector + BM25):")
            results, stats = benchmark_search(
                db, "hybrid", query, limit=limit, num_runs=num_runs
            )
            all_stats["hybrid"].append(stats)
            print(f"   Mean: {format_time(stats['mean'])}")
            print(f"   Min:  {format_time(stats['min'])}")
            print(f"   Max:  {format_time(stats['max'])}")
            if stats["stdev"] > 0:
                print(f"   Std:  {format_time(stats['stdev'])}")
            print_results(results, limit=2)

        # Summary statistics
        print(f"\n{'=' * 70}")
        print("SUMMARY STATISTICS (across all queries)")
        print("=" * 70)

        for method_name, method_stats in all_stats.items():
            method_display = {
                "vector": "Vector Search",
                "text": "Text Search (BM25)",
                "hybrid": "Hybrid Search",
            }[method_name]

            avg_mean = mean(s["mean"] for s in method_stats)
            avg_min = mean(s["min"] for s in method_stats)
            avg_max = mean(s["max"] for s in method_stats)

            print(f"\n{method_display}:")
            print(f"  Average mean time: {format_time(avg_mean)}")
            print(f"  Average min time:  {format_time(avg_min)}")
            print(f"  Average max time:  {format_time(avg_max)}")

        # Comparison
        print(f"\n{'=' * 70}")
        print("SPEED COMPARISON (average mean times)")
        print("=" * 70)
        avg_times = {
            "Vector": mean(s["mean"] for s in all_stats["vector"]),
            "Text (BM25)": mean(s["mean"] for s in all_stats["text"]),
            "Hybrid": mean(s["mean"] for s in all_stats["hybrid"]),
        }
        fastest = min(avg_times.items(), key=lambda x: x[1])
        for method, avg_time in sorted(avg_times.items(), key=lambda x: x[1]):
            speedup = avg_time / fastest[1]
            marker = " ⚡ FASTEST" if method == fastest[0] else ""
            print(
                f"  {method:15s}: {format_time(avg_time):>12s} ({speedup:.2f}x){marker}"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()

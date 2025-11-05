"""
Compare all 5 extraction approaches.
Focus on page 266 (Failure section issue) and overall structure.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
# Try both possible paths
RULES_DIR_1 = REPO_ROOT / "backend" / "data" / "heroes" / "rules"
RULES_DIR_2 = Path("/Users/benwyatt/Repos/backend/data/heroes/rules")
RULES_DIR = RULES_DIR_1 if RULES_DIR_1.exists() else RULES_DIR_2


def load_extraction(version: str) -> List[Dict[str, Any]]:
    """Load an extraction result."""
    # Map version numbers to actual filenames
    filename_map = {
        "1": "extracted_rules_v1_column_sort.json",
        "2": "extracted_rules_v2_pdfplumber.json",
        "3": "extracted_rules_v3_markitdown.json",
        "4": "extracted_rules_v4_unstructured.json",
        "5": "extracted_rules_v5_hybrid.json",
    }

    filename = filename_map.get(version, f"extracted_rules_v{version}.json")
    filepath = RULES_DIR / filename

    if not filepath.exists():
        print(f"Warning: File not found: {filepath}")
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Loaded {len(data)} chunks from {filename}")
            return data
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []


def find_chunks_by_page(
    chunks: List[Dict[str, Any]], page_num: int
) -> List[Dict[str, Any]]:
    """Find all chunks for a specific page."""
    return [chunk for chunk in chunks if chunk.get("page") == page_num]


def find_chunks_by_subsection(
    chunks: List[Dict[str, Any]], subsection: str
) -> List[Dict[str, Any]]:
    """Find all chunks for a specific subsection."""
    return [chunk for chunk in chunks if chunk.get("subsection") == subsection]


def analyze_page_266(chunks: List[Dict[str, Any]], version_name: str) -> Dict[str, Any]:
    """Analyze page 266 specifically for the Failure section issue."""
    page_266_chunks = find_chunks_by_page(chunks, 266)

    # Find Failure section
    failure_chunks = []
    in_failure = False

    for chunk in page_266_chunks:
        subsection = chunk.get("subsection")
        text = chunk.get("text", "").lower()

        if subsection and "failure" in subsection.lower():
            in_failure = True
            failure_chunks.append(chunk)
        elif text.startswith("failure"):
            in_failure = True
            failure_chunks.append(chunk)
        elif in_failure:
            # Check if we've moved to next section
            if subsection and subsection.lower() not in [
                "failure",
                "failure with a consequence",
            ]:
                break
            failure_chunks.append(chunk)

    # Also check for "Success With a Reward" mislabeling
    success_reward_chunks = []
    for chunk in page_266_chunks:
        section = chunk.get("section", "")
        subsection = chunk.get("subsection", "")
        text = chunk.get("text", "").lower()

        if (
            "success with a reward" in section.lower()
            or "success with a reward" in subsection.lower()
        ):
            success_reward_chunks.append(chunk)

    return {
        "version": version_name,
        "total_page_266_chunks": len(page_266_chunks),
        "failure_chunks_found": len(failure_chunks),
        "failure_chunks": failure_chunks,
        "success_reward_chunks": success_reward_chunks,
        "failure_section_labeled_correctly": any(
            "failure" in (chunk.get("subsection") or "").lower()
            for chunk in failure_chunks
        ),
    }


def analyze_paragraph_merging(
    chunks: List[Dict[str, Any]], subsection: str
) -> Dict[str, Any]:
    """Analyze how well paragraphs are merged for a subsection."""
    subsection_chunks = find_chunks_by_subsection(chunks, subsection)

    # Count chunks vs expected paragraphs
    total_text_length = sum(len(chunk.get("text", "")) for chunk in subsection_chunks)

    # Check if "Failure" text appears complete
    failure_text = " ".join(
        chunk.get("text", "")
        for chunk in subsection_chunks
        if "failure" in chunk.get("subsection", "").lower()
    )

    expected_keywords = [
        "fail a test without incurring a consequence",
        "director can decide",
        "director can offer to let them succeed",
    ]

    keywords_found = [
        kw for kw in expected_keywords if kw.lower() in failure_text.lower()
    ]

    return {
        "subsection": subsection,
        "chunk_count": len(subsection_chunks),
        "total_text_length": total_text_length,
        "expected_keywords_found": len(keywords_found),
        "expected_keywords": expected_keywords,
        "keywords_found": keywords_found,
    }


def generate_comparison_report() -> str:
    """Generate a comparison report of all 5 approaches."""
    versions = [
        ("1", "Column-Aware Sorting"),
        ("2", "PDFPlumber"),
        ("3", "MarkItDown"),
        ("4", "Unstructured.io"),
        ("5", "Hybrid with Paragraph Merging"),
    ]

    all_chunks = {}
    page_266_analyses = {}

    # Load all extractions
    for version_num, version_name in versions:
        chunks = load_extraction(version_num)
        all_chunks[version_num] = chunks
        page_266_analyses[version_num] = analyze_page_266(chunks, version_name)

    # Build report
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("RULES EXTRACTION COMPARISON REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Overall statistics
    report_lines.append("OVERALL STATISTICS")
    report_lines.append("-" * 80)
    for version_num, version_name in versions:
        chunks = all_chunks[version_num]
        report_lines.append(f"\n{version_name} (V{version_num}):")
        report_lines.append(f"  Total chunks: {len(chunks)}")

        # Count by type
        type_counts = {}
        for chunk in chunks:
            chunk_type = chunk.get("type", "unknown")
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

        report_lines.append("  Chunks by type:")
        for chunk_type, count in sorted(type_counts.items()):
            report_lines.append(f"    {chunk_type}: {count}")

    # Page 266 Analysis
    report_lines.append("\n" + "=" * 80)
    report_lines.append("PAGE 266 ANALYSIS (Failure Section Issue)")
    report_lines.append("=" * 80)

    for version_num, version_name in versions:
        analysis = page_266_analyses[version_num]
        report_lines.append(f"\n{version_name} (V{version_num}):")
        report_lines.append(
            f"  Total chunks on page 266: {analysis['total_page_266_chunks']}"
        )
        report_lines.append(
            f"  Failure chunks found: {analysis['failure_chunks_found']}"
        )
        report_lines.append(
            f"  Failure section labeled correctly: {analysis['failure_section_labeled_correctly']}"
        )

        # Show Failure chunks
        if analysis["failure_chunks"]:
            report_lines.append("\n  Failure section chunks:")
            for i, chunk in enumerate(
                analysis["failure_chunks"][:5], 1
            ):  # Show first 5
                text_preview = chunk.get("text", "")[:150]
                subsection = chunk.get("subsection", "None")
                section = chunk.get("section", "None")
                report_lines.append(f"    {i}. Subsection: {subsection}")
                report_lines.append(f"       Section: {section}")
                report_lines.append(f"       Text: {text_preview}...")

        # Check for mislabeling
        if analysis["success_reward_chunks"]:
            mislabeled = [
                chunk
                for chunk in analysis["success_reward_chunks"]
                if "failure" in chunk.get("text", "").lower()
            ]
            if mislabeled:
                report_lines.append(
                    f"\n  ⚠️  WARNING: Found {len(mislabeled)} chunks mislabeled as 'Success With a Reward' but contain 'Failure' text"
                )
                for chunk in mislabeled[:2]:
                    text_preview = chunk.get("text", "")[:150]
                    report_lines.append(f"      - {text_preview}...")

    # Paragraph Merging Analysis
    report_lines.append("\n" + "=" * 80)
    report_lines.append("PARAGRAPH MERGING ANALYSIS (Failure Section)")
    report_lines.append("=" * 80)

    for version_num, version_name in versions:
        chunks = all_chunks[version_num]
        merging_analysis = analyze_paragraph_merging(chunks, "Failure")

        report_lines.append(f"\n{version_name} (V{version_num}):")
        report_lines.append(
            f"  Chunk count for 'Failure': {merging_analysis['chunk_count']}"
        )
        report_lines.append(
            f"  Total text length: {merging_analysis['total_text_length']} chars"
        )
        report_lines.append(
            f"  Expected keywords found: {merging_analysis['expected_keywords_found']}/{len(merging_analysis['expected_keywords'])}"
        )

        if merging_analysis["keywords_found"]:
            report_lines.append("  ✓ Keywords found:")
            for kw in merging_analysis["keywords_found"]:
                report_lines.append(f"    - {kw}")

        missing = set(merging_analysis["expected_keywords"]) - set(
            merging_analysis["keywords_found"]
        )
        if missing:
            report_lines.append("  ✗ Missing keywords:")
            for kw in missing:
                report_lines.append(f"    - {kw}")

    # Recommendations
    report_lines.append("\n" + "=" * 80)
    report_lines.append("RECOMMENDATIONS")
    report_lines.append("=" * 80)
    report_lines.append("""
1. Column Detection: Check which approach correctly separates left/right columns
2. Section Header Association: Verify headers are correctly associated with content in their column
3. Paragraph Merging: Evaluate which approach best groups multi-paragraph sections
4. Page 266 Specific: Focus on fixing the "Failure" section mislabeling issue

Expected "Failure" section should contain:
- "If you fail a test without incurring a consequence..."
- "On a failed test, the Director can decide..."
- "When a hero rolls a failure without a consequence..."

All should be under subsection "Failure", not "Success With a Reward".
""")

    return "\n".join(report_lines)


def main():
    """Generate comparison report."""
    print("Generating comparison report...")

    report = generate_comparison_report()

    # Save report
    output_file = RULES_DIR / "extraction_comparison_report.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nComparison report saved to: {output_file}")
    print("\n" + "=" * 80)
    print(report)
    print("=" * 80)


if __name__ == "__main__":
    main()

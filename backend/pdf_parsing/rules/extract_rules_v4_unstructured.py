"""
Approach 4: Unstructured.io AI-Powered Parsing
Use unstructured library for intelligent document parsing.
Leverage its AI understanding of document structure.
Extract structured chunks with proper section associations.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from unstructured.chunking.title import chunk_by_title
from unstructured.partition.pdf import partition_pdf

# Try to find PDF - check multiple possible locations
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
HEROES_PDF_ABS = Path(
    "/Users/Ben.Wyatt/Personal/Draw Steel v1/Draw_Steel_Heroes_v1.pdf"
)
HEROES_PDF_REL = REPO_ROOT / "pdf" / "Draw_Steel_Heroes_v1.pdf"
HEROES_PDF_REPOS = Path("/Users/benwyatt/Repos/draw-steel/pdf/Draw_Steel_Heroes_v1.pdf")

HEROES_PDF = None
if HEROES_PDF_REL.exists():
    HEROES_PDF = HEROES_PDF_REL
elif HEROES_PDF_REPOS.exists():
    HEROES_PDF = HEROES_PDF_REPOS
elif HEROES_PDF_ABS.exists():
    HEROES_PDF = HEROES_PDF_ABS
else:
    HEROES_PDF = HEROES_PDF_REL


def clean_text(text: str) -> str:
    """Normalize whitespace and formatting."""
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def get_section_for_page(
    page_num: int, toc: List[Tuple[int, str, int]]
) -> Optional[str]:
    """Get the section name for a page using the table of contents."""
    page_num_1_indexed = page_num + 1
    current_section = None

    for level, title, toc_page in toc:
        if toc_page <= page_num_1_indexed:
            current_section = title
        else:
            break

    return current_section


def is_ability_block(text: str) -> bool:
    """Detect ability blocks by keywords."""
    text_lower = text.lower()
    ability_indicators = [
        "power roll",
        "á",
        "é",
        "í",
        "action type",
        "range:",
        "target:",
    ]
    return any(indicator in text_lower for indicator in ability_indicators)


def extract_rule_text_from_elements(
    elements: List, page_num: int, toc: List[Tuple[int, str, int]]
) -> List[Dict[str, Any]]:
    """Extract rule text from unstructured elements."""
    chunks = []
    current_section = get_section_for_page(page_num, toc)
    current_subsection = None

    for element in elements:
        text = str(element.text) if hasattr(element, "text") else str(element)
        text = clean_text(text)

        if not text or len(text) < 10:
            continue

        # Skip ability blocks
        if is_ability_block(text):
            continue

        # Check if element is a title/header
        category = getattr(element, "category", None)
        if category == "Title" or (
            hasattr(element, "metadata") and element.metadata.get("category") == "Title"
        ):
            # This is a section header
            current_subsection = text
            chunks.append(
                {
                    "page": page_num + 1,
                    "text": text,
                    "section": current_section,
                    "subsection": current_subsection,
                    "type": "section_header",
                }
            )
            continue

        # Regular content
        content_type = "rule"
        text_lower = text.lower()
        if any(word in text_lower for word in ["example", "for example", "e.g."]):
            content_type = "example"
        elif any(word in text_lower for word in ["flavor", "story", "lore", "history"]):
            content_type = "flavor_text"

        chunks.append(
            {
                "page": page_num + 1,
                "text": text,
                "section": current_section,
                "subsection": current_subsection,
                "type": content_type,
            }
        )

    return chunks


def main():
    """Extract rule text from the entire PDF."""
    print(f"\n[V4: Unstructured.io] Extracting from {HEROES_PDF}")

    if not HEROES_PDF.exists():
        print(f"ERROR: PDF file not found at {HEROES_PDF}!")
        return

    # Get TOC using PyMuPDF
    import fitz

    doc = fitz.open(HEROES_PDF)
    toc = doc.get_toc()
    total_pages = doc.page_count
    doc.close()

    print(f"Total pages: {total_pages}")

    # Process PDF with unstructured
    print("Processing PDF with unstructured.io...")
    print("This may take a while...")

    # Partition PDF - use strategy="hi_res" for better layout understanding
    # Note: This requires additional dependencies and may be slower
    elements = partition_pdf(
        filename=str(HEROES_PDF),
        strategy="auto",  # Use auto strategy (faster than hi_res)
        infer_table_structure=False,  # We don't need tables
        extract_images_in_pdf=False,
    )

    print(f"Extracted {len(elements)} elements")

    # Chunk by title to group content under headers
    print("Chunking by title...")
    chunks_by_title = chunk_by_title(elements)

    print(f"Created {len(chunks_by_title)} title-based chunks")

    # Process chunks
    all_chunks = []

    # Estimate page numbers based on element metadata
    for chunk in chunks_by_title:
        # Get page number from metadata if available
        page_num = 0
        if hasattr(chunk, "metadata") and chunk.metadata:
            page_num = chunk.metadata.get("page_number", 0) - 1  # Convert to 0-indexed

        chunks = extract_rule_text_from_elements([chunk], page_num, toc)
        all_chunks.extend(chunks)

    print(f"\nCompleted! Extracted {len(all_chunks)} text chunks.")

    # Save to JSON
    output_dir = REPO_ROOT / "backend" / "data" / "heroes" / "rules"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "extracted_rules_v4_unstructured.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()

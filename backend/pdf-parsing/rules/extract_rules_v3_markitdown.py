"""
Approach 3: MarkItDown Conversion
Convert PDF to markdown using MarkItDown library.
Parse markdown structure to extract sections and paragraphs.
Map markdown headers to section structure.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import markitdown

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
        "í",  # Tier symbols
        "action type",
        "range:",
        "target:",
    ]
    return any(indicator in text_lower for indicator in ability_indicators)


def parse_markdown_to_chunks(
    markdown_text: str, page_num: int, toc: List[Tuple[int, str, int]]
) -> List[Dict[str, Any]]:
    """
    Parse markdown text into structured chunks.
    Groups paragraphs under section headers.
    """
    chunks = []
    current_section = get_section_for_page(page_num, toc)
    current_subsection = None
    current_paragraphs = []

    lines = markdown_text.split("\n")

    for line in lines:
        line = line.strip()

        if not line:
            # Empty line - save current paragraph if exists
            if current_paragraphs:
                paragraph_text = " ".join(current_paragraphs)
                paragraph_text = clean_text(paragraph_text)

                if paragraph_text and len(paragraph_text) > 10:
                    # Skip ability blocks
                    if not is_ability_block(paragraph_text):
                        content_type = "rule"
                        text_lower = paragraph_text.lower()
                        if any(
                            word in text_lower
                            for word in ["example", "for example", "e.g."]
                        ):
                            content_type = "example"
                        elif any(
                            word in text_lower
                            for word in ["flavor", "story", "lore", "history"]
                        ):
                            content_type = "flavor_text"

                        chunks.append(
                            {
                                "page": page_num + 1,
                                "text": paragraph_text,
                                "section": current_section,
                                "subsection": current_subsection,
                                "type": content_type,
                            }
                        )

                current_paragraphs = []
            continue

        # Check for markdown headers (# ## ### etc)
        header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if header_match:
            # Save current paragraph before processing header
            if current_paragraphs:
                paragraph_text = " ".join(current_paragraphs)
                paragraph_text = clean_text(paragraph_text)

                if paragraph_text and len(paragraph_text) > 10:
                    if not is_ability_block(paragraph_text):
                        content_type = "rule"
                        text_lower = paragraph_text.lower()
                        if any(
                            word in text_lower
                            for word in ["example", "for example", "e.g."]
                        ):
                            content_type = "example"
                        elif any(
                            word in text_lower
                            for word in ["flavor", "story", "lore", "history"]
                        ):
                            content_type = "flavor_text"

                        chunks.append(
                            {
                                "page": page_num + 1,
                                "text": paragraph_text,
                                "section": current_section,
                                "subsection": current_subsection,
                                "type": content_type,
                            }
                        )

                current_paragraphs = []

            # Process header
            header_level = len(header_match.group(1))
            header_text = header_match.group(2).strip()
            header_text = clean_text(header_text)

            # Section headers are typically level 2 or 3 (## or ###)
            if 2 <= header_level <= 3 and len(header_text) > 2:
                current_subsection = header_text
                chunks.append(
                    {
                        "page": page_num + 1,
                        "text": header_text,
                        "section": current_section,
                        "subsection": current_subsection,
                        "type": "section_header",
                    }
                )
            continue

        # Regular text line - add to current paragraph
        current_paragraphs.append(line)

    # Save last paragraph if exists
    if current_paragraphs:
        paragraph_text = " ".join(current_paragraphs)
        paragraph_text = clean_text(paragraph_text)

        if paragraph_text and len(paragraph_text) > 10:
            if not is_ability_block(paragraph_text):
                content_type = "rule"
                text_lower = paragraph_text.lower()
                if any(
                    word in text_lower for word in ["example", "for example", "e.g."]
                ):
                    content_type = "example"
                elif any(
                    word in text_lower
                    for word in ["flavor", "story", "lore", "history"]
                ):
                    content_type = "flavor_text"

                chunks.append(
                    {
                        "page": page_num + 1,
                        "text": paragraph_text,
                        "section": current_section,
                        "subsection": current_subsection,
                        "type": content_type,
                    }
                )

    return chunks


def extract_rule_text_from_page(
    markdown_text: str, page_num: int, toc: List[Tuple[int, str, int]]
) -> List[Dict[str, Any]]:
    """Extract rule text from markdown."""
    return parse_markdown_to_chunks(markdown_text, page_num, toc)


def main():
    """Extract rule text from the entire PDF."""
    print(f"\n[V3: MarkItDown] Extracting from {HEROES_PDF}")

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

    # Convert entire PDF to markdown
    print("Converting PDF to markdown...")
    md_file = markitdown.convert(str(HEROES_PDF))

    # Split markdown by page markers if available, or process as whole
    # MarkItDown may not preserve page boundaries, so we'll process page by page
    print("Processing markdown...")

    # For now, process entire document and estimate page boundaries
    # This is a limitation - MarkItDown doesn't preserve page info
    all_chunks = []

    # Process entire markdown as if it's one page (approximation)
    # In a real scenario, we'd need to match content to pages
    chunks = extract_rule_text_from_page(md_file, 0, toc)

    # Since we can't perfectly map to pages, assign chunks evenly
    # This is a limitation of this approach
    for i, chunk in enumerate(chunks):
        # Estimate page number based on position
        estimated_page = (
            min((i * total_pages) // len(chunks) + 1, total_pages) if chunks else 1
        )
        chunk["page"] = estimated_page
        all_chunks.append(chunk)

    print(f"\nCompleted! Extracted {len(all_chunks)} text chunks.")
    print(
        "Note: Page numbers are estimated as MarkItDown doesn't preserve page boundaries."
    )

    # Save to JSON
    output_dir = REPO_ROOT / "backend" / "data" / "heroes" / "rules"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "extracted_rules_v3_markitdown.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()

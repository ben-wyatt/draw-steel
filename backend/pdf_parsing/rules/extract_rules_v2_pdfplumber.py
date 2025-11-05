"""
Approach 2: PDFPlumber Layout-Aware Extraction
Use PDFPlumber's layout-aware text extraction.
Leverage its column detection capabilities.
Parse markdown-like structure from PDFPlumber output.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

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
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
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


def detect_section_header(words: List) -> Optional[str]:
    """
    Detect section headers by font size and style.
    words is a list of word dictionaries from PDFPlumber.
    """
    if not words:
        return None

    # Check font size (headers are larger)
    font_sizes = [word.get("size", 0) for word in words[:10]]  # Sample first 10 words
    avg_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0

    # Section headers are typically 12-16pt
    if 12 <= avg_size <= 16:
        text = " ".join(word["text"] for word in words[:5]).strip()  # First few words
        if len(text) > 2:
            return text

    return None


def is_ability_block(words: List) -> bool:
    """Detect ability blocks by font pattern."""
    if not words:
        return False

    font_sizes = [word.get("size", 0) for word in words[:10]]
    avg_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0

    # Ability titles are Newzald-Bold @ ~10pt
    if 9 <= avg_size <= 11:
        text = " ".join(word["text"] for word in words[:20]).lower()
        if any(
            word in text for word in ["power roll", "á", "é", "í", "action", "range"]
        ):
            return True

    return False


def extract_rule_text_from_page(
    page: "Page", page_num: int, toc: List[Tuple[int, str, int]]
) -> List[Dict[str, Any]]:
    """Extract rule text using PDFPlumber's layout awareness."""
    chunks = []
    current_section = get_section_for_page(page_num, toc)
    current_subsection = None

    # Extract words with layout information
    words = page.extract_words()

    # Group words into blocks based on proximity
    blocks = []
    current_block = []
    current_y = None

    for word in words:
        word_y = word["top"]

        # If Y coordinate changed significantly, start new block
        if current_y is None or abs(word_y - current_y) > 5:
            if current_block:
                blocks.append(current_block)
            current_block = [word]
            current_y = word_y
        else:
            current_block.append(word)

    if current_block:
        blocks.append(current_block)

    # Process blocks
    for block_words in blocks:
        if not block_words:
            continue

        # Skip ability blocks
        if is_ability_block(block_words):
            continue

        # Check for section headers
        section_header = detect_section_header(block_words)
        if section_header:
            current_subsection = section_header
            chunks.append(
                {
                    "page": page_num + 1,
                    "text": clean_text(section_header),
                    "section": current_section,
                    "subsection": current_subsection,
                    "type": "section_header",
                }
            )
            continue

        # Extract text
        text = " ".join(word["text"] for word in block_words)
        text = clean_text(text)

        if not text or len(text) < 10:
            continue

        # Filter headers/footers (top/bottom 10% of page)
        page_height = page.height
        first_word_y = block_words[0]["top"]
        if first_word_y < page_height * 0.1 or first_word_y > page_height * 0.9:
            if len(text) < 100:
                continue

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
    print(f"\n[V2: PDFPlumber] Extracting from {HEROES_PDF}")

    if not HEROES_PDF.exists():
        print(f"ERROR: PDF file not found at {HEROES_PDF}!")
        return

    with pdfplumber.open(HEROES_PDF) as pdf:
        total_pages = len(pdf.pages)

        # Get TOC - PDFPlumber doesn't have direct TOC access, so we'll use PyMuPDF for that
        import fitz

        doc = fitz.open(HEROES_PDF)
        toc = doc.get_toc()
        doc.close()

        print(f"Total pages: {total_pages}")

        all_chunks = []

        print("Processing pages...")
        for page_num in range(total_pages):
            if page_num % 50 == 0:
                print(f"  Processing page {page_num + 1}/{total_pages}...")

            page = pdf.pages[page_num]
            chunks = extract_rule_text_from_page(page, page_num, toc)
            all_chunks.extend(chunks)

        print(f"\nCompleted! Extracted {len(all_chunks)} text chunks.")

        # Save to JSON
        output_dir = REPO_ROOT / "backend" / "data" / "heroes" / "rules"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "extracted_rules_v2_pdfplumber.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()

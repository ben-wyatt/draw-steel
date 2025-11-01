"""
Extract plain text rule descriptions and flavor text from the Draw Steel Heroes PDF.
Filters out ability blocks, stat blocks, headers, and footers for clean rule text.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import fitz  # PyMuPDF
import json
import re


# Try to find PDF - check multiple possible locations
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
HEROES_PDF_ABS = Path("/Users/Ben.Wyatt/Personal/Draw Steel v1/Draw_Steel_Heroes_v1.pdf")
HEROES_PDF_REL = REPO_ROOT / "pdf" / "Draw_Steel_Heroes_v1.pdf"
HEROES_PDF_REPOS = Path("/Users/benwyatt/Repos/draw-steel/pdf/Draw_Steel_Heroes_v1.pdf")

# Determine PDF path - check multiple locations
HEROES_PDF = None
if HEROES_PDF_REL.exists():
    HEROES_PDF = HEROES_PDF_REL
elif HEROES_PDF_REPOS.exists():
    HEROES_PDF = HEROES_PDF_REPOS
elif HEROES_PDF_ABS.exists():
    HEROES_PDF = HEROES_PDF_ABS
else:
    # Default to relative path - will show helpful error if not found
    HEROES_PDF = HEROES_PDF_REL


def extract_text_blocks(page: fitz.Page) -> List[Dict]:
    """Extract text blocks with detailed information."""
    text_dict = page.get_text("dict")
    blocks = []
    
    for block in text_dict.get("blocks", []):
        if "lines" not in block:  # Skip image blocks
            continue
        
        block_info = {
            "bbox": block["bbox"],
            "type": block.get("type", 0),
            "lines": []
        }
        
        for line in block["lines"]:
            line_info = {
                "bbox": line["bbox"],
                "spans": []
            }
            
            for span in line["spans"]:
                span_info = {
                    "text": span.get("text", ""),
                    "font": span.get("font", ""),
                    "size": span.get("size", 0),
                    "color": span.get("color", 0),
                    "flags": span.get("flags", 0),
                    "bbox": span.get("bbox", (0, 0, 0, 0))
                }
                line_info["spans"].append(span_info)
            
            # Combine span texts for line text
            line_info["text"] = "".join(s["text"] for s in line_info["spans"])
            block_info["lines"].append(line_info)
        
        # Combine line texts for block text
        block_info["text"] = "\n".join(l["text"] for l in block_info["lines"])
        blocks.append(block_info)
    
    return blocks


def is_ability_block(block: Dict, block_index: int, all_blocks: List[Dict]) -> bool:
    """
    Detect ability blocks by font pattern.
    Ability titles are in Newzald-Bold @ ~10pt.
    """
    if not block["lines"]:
        return False
    
    first_line = block["lines"][0]
    if not first_line["spans"]:
        return False
    
    first_span = first_line["spans"][0]
    font_size = first_span["size"]
    font_name = first_span["font"]
    text = first_span["text"].strip()
    
    # Ability titles are in Newzald-Bold @ ~10pt
    is_ability_title = (
        "Newzald-Bold" in font_name and 
        9 <= font_size <= 11 and
        len(text) > 3
    )
    
    if is_ability_title:
        return True
    
    # Also check if this block is part of an ability (metadata or effect block)
    # Ability metadata blocks use BerlingskeSlab-Bold @ 7.5pt
    if block_index > 0:
        prev_block = all_blocks[block_index - 1]
        if prev_block["lines"] and prev_block["lines"][0]["spans"]:
            prev_font = prev_block["lines"][0]["spans"][0]["font"]
            prev_size = prev_block["lines"][0]["spans"][0]["size"]
            if "Newzald-Bold" in prev_font and 9 <= prev_size <= 11:
                # Previous block was an ability title
                # Check if this is metadata (BerlingskeSlab-Bold @ 7.5pt)
                if "BerlingskeSlab-Bold" in font_name and 7 <= font_size <= 8:
                    return True
                # Check if this is effect block (has power roll or tier symbols)
                if any(word in text.lower() for word in ["power roll", "á", "é", "í"]):
                    return True
    
    return False


def is_header_or_footer(block: Dict, page_rect: fitz.Rect) -> bool:
    """
    Filter headers and footers by position.
    Headers/footers are typically at the very top or bottom of the page.
    """
    bbox = block["bbox"]
    y0, y1 = bbox[1], bbox[3]
    page_height = page_rect.height
    
    # Headers are typically in top 10% of page
    # Footers are typically in bottom 10% of page
    header_threshold = page_height * 0.1
    footer_threshold = page_height * 0.9
    
    if y0 < header_threshold or y1 > footer_threshold:
        # Additional check: headers/footers are often short lines
        text = block["text"].strip()
        if len(text) < 100:  # Short text likely header/footer
            return True
    
    return False


def is_sidebar(block: Dict, page_rect: fitz.Rect) -> bool:
    """
    Filter sidebars by position (typically narrow columns on sides).
    """
    bbox = block["bbox"]
    x0, x1 = bbox[0], bbox[2]
    page_width = page_rect.width
    
    # Sidebars are typically in outer 15% of page width
    sidebar_threshold = page_width * 0.15
    
    if x0 < sidebar_threshold or x1 > (page_width - sidebar_threshold):
        # Check if it's a narrow column
        block_width = x1 - x0
        if block_width < page_width * 0.25:  # Narrow column
            return True
    
    return False


def clean_text(text: str) -> str:
    """
    Normalize whitespace and formatting.
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    # Fix multiple newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text


def get_section_for_page(page_num: int, toc: List[Tuple[int, str, int]]) -> Optional[str]:
    """
    Get the section name for a page using the table of contents.
    Returns the most specific (deepest) section header for the page.
    """
    page_num_1_indexed = page_num + 1  # TOC uses 1-indexed pages
    current_section = None
    
    for level, title, toc_page in toc:
        if toc_page <= page_num_1_indexed:
            # Update current section if this entry is for this page or earlier
            current_section = title
        else:
            # Once we pass the page, break
            break
    
    return current_section


def detect_section_header(block: Dict) -> Optional[str]:
    """
    Detect section headers by font pattern.
    Main headers: MCDM-Book @ 24pt
    Section headers: Newzald-Bold @ 14pt
    """
    if not block["lines"]:
        return None
    
    first_line = block["lines"][0]
    if not first_line["spans"]:
        return None
    
    first_span = first_line["spans"][0]
    font_size = first_span["size"]
    font_name = first_span["font"]
    text = first_span["text"].strip()
    
    # Main headers: MCDM-Book @ 24pt
    # Section headers: Newzald-Bold @ 14pt
    is_header = (
        ("MCDM-Book" in font_name and 20 <= font_size <= 26) or
        ("Newzald-Bold" in font_name and 12 <= font_size <= 16)
    )
    
    if is_header and len(text) > 2:
        return text
    
    return None


def extract_rule_text_from_page(
    page: fitz.Page,
    page_num: int,
    toc: List[Tuple[int, str, int]],
    ability_block_indices: Set[int]
) -> List[Dict[str, Any]]:
    """
    Extract rule text from a page, filtering out structured content.
    Returns a list of text chunks with metadata.
    """
    page_rect = page.rect
    text_blocks = extract_text_blocks(page)
    
    chunks = []
    current_section = get_section_for_page(page_num, toc)
    current_subsection = None
    
    for i, block in enumerate(text_blocks):
        # Skip if this is an ability block
        if i in ability_block_indices:
            continue
        
        # Skip headers and footers
        if is_header_or_footer(block, page_rect):
            continue
        
        # Skip sidebars
        if is_sidebar(block, page_rect):
            continue
        
        # Check for section headers
        section_header = detect_section_header(block)
        if section_header:
            current_subsection = section_header
            # Section headers can be included as their own chunk
            chunks.append({
                "page": page_num + 1,
                "text": clean_text(section_header),
                "section": current_section,
                "subsection": current_subsection,
                "type": "section_header"
            })
            continue
        
        # Extract clean text
        text = clean_text(block["text"])
        
        # Skip if empty or too short (likely noise)
        if not text or len(text) < 10:
            continue
        
        # Determine content type
        content_type = "rule"
        text_lower = text.lower()
        if any(word in text_lower for word in ["example", "for example", "e.g."]):
            content_type = "example"
        elif any(word in text_lower for word in ["flavor", "story", "lore", "history"]):
            content_type = "flavor_text"
        
        chunks.append({
            "page": page_num + 1,
            "text": text,
            "section": current_section,
            "subsection": current_subsection,
            "type": content_type
        })
    
    return chunks


def detect_all_ability_blocks(text_blocks: List[Dict]) -> Set[int]:
    """
    Detect all ability block indices to exclude from rule extraction.
    """
    ability_indices = set()
    
    for i, block in enumerate(text_blocks):
        if is_ability_block(block, i, text_blocks):
            ability_indices.add(i)
            # Also mark the next 2 blocks as ability-related (metadata + effect)
            if i + 1 < len(text_blocks):
                ability_indices.add(i + 1)
            if i + 2 < len(text_blocks):
                ability_indices.add(i + 2)
    
    return ability_indices


def main():
    """Extract rule text from the entire PDF."""
    print(f"\nExtracting rule text from {HEROES_PDF}")
    
    if not HEROES_PDF.exists():
        print(f"ERROR: PDF file not found at {HEROES_PDF}!")
        print("\nPlease ensure the PDF is available at one of these locations:")
        print(f"  - {HEROES_PDF_REL}")
        print(f"  - {HEROES_PDF_REPOS}")
        print(f"  - {HEROES_PDF_ABS}")
        print("\nOr modify HEROES_PDF in the script to point to your PDF location.")
        return
    
    doc = fitz.open(HEROES_PDF)
    total_pages = doc.page_count
    toc = doc.get_toc()
    
    print(f"Total pages: {total_pages}")
    print(f"TOC entries: {len(toc)}\n")
    
    try:
        all_chunks = []
        
        print("Processing pages...")
        for page_num in range(total_pages):
            if page_num % 50 == 0:
                print(f"  Processing page {page_num + 1}/{total_pages}...")
            
            page = doc[page_num]
            text_blocks = extract_text_blocks(page)
            
            # Detect ability blocks to exclude
            ability_indices = detect_all_ability_blocks(text_blocks)
            
            # Extract rule text
            chunks = extract_rule_text_from_page(page, page_num, toc, ability_indices)
            
            all_chunks.extend(chunks)
        
        print(f"\nCompleted! Extracted {len(all_chunks)} text chunks.\n")
        
        # Print summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total chunks: {len(all_chunks)}")
        
        # Count by type
        type_counts = {}
        for chunk in all_chunks:
            chunk_type = chunk["type"]
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        print("\nChunks by type:")
        for chunk_type, count in sorted(type_counts.items()):
            print(f"  {chunk_type}: {count}")
        
        # Show sample chunks
        print("\n" + "=" * 80)
        print("SAMPLE CHUNKS (first 5)")
        print("=" * 80)
        
        for i, chunk in enumerate(all_chunks[:5], 1):
            print(f"\n[Page {chunk['page']}] Chunk {i} ({chunk['type']})")
            if chunk.get('section'):
                print(f"Section: {chunk['section']}")
            if chunk.get('subsection'):
                print(f"Subsection: {chunk['subsection']}")
            print("-" * 80)
            text_preview = chunk['text'][:200]
            print(text_preview)
            if len(chunk['text']) > 200:
                print("...")
        
        # Save to JSON
        output_dir = REPO_ROOT / "data" / "heroes" / "rules"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "extracted_rules.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        
        print(f"\n\nAll {len(all_chunks)} chunks saved to: {output_file}")
        
        # Also save a summary
        summary_file = output_dir / "extraction_summary.txt"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("DRAW STEEL RULES EXTRACTION SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"PDF: {HEROES_PDF}\n")
            f.write(f"Total Pages: {total_pages}\n")
            f.write(f"Total Chunks: {len(all_chunks)}\n\n")
            f.write("Chunks by Type:\n")
            for chunk_type, count in sorted(type_counts.items()):
                f.write(f"  {chunk_type}: {count}\n")
            f.write("\n" + "=" * 80 + "\n")
        
        print(f"Summary saved to: {summary_file}")
        
    finally:
        doc.close()


if __name__ == "__main__":
    main()


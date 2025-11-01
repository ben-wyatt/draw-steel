"""
Approach 5: Hybrid PyMuPDF + Paragraph Merging
Use PyMuPDF with improved column detection.
Implement paragraph merging logic that groups content until next section header.
Add section header validation to ensure headers only apply to their column.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import fitz  # PyMuPDF
import json
import re


# Try to find PDF - check multiple possible locations
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
HEROES_PDF_ABS = Path("/Users/Ben.Wyatt/Personal/Draw Steel v1/Draw_Steel_Heroes_v1.pdf")
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


def extract_text_blocks(page: fitz.Page) -> List[Dict]:
    """Extract text blocks with detailed information."""
    text_dict = page.get_text("dict")
    blocks = []
    
    for block in text_dict.get("blocks", []):
        if "lines" not in block:
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
            
            line_info["text"] = "".join(s["text"] for s in line_info["spans"])
            block_info["lines"].append(line_info)
        
        block_info["text"] = "\n".join(l["text"] for l in block_info["lines"])
        blocks.append(block_info)
    
    return blocks


def detect_columns(blocks: List[Dict], page_width: float) -> Tuple[float, float]:
    """Detect column boundaries by clustering X-coordinates."""
    x_positions = []
    for block in blocks:
        bbox = block["bbox"]
        x_center = (bbox[0] + bbox[2]) / 2
        x_positions.append(x_center)
    
    if not x_positions:
        return (page_width / 2, page_width / 2)
    
    x_positions.sort()
    gaps = []
    for i in range(len(x_positions) - 1):
        gap = x_positions[i + 1] - x_positions[i]
        gaps.append((gap, x_positions[i], x_positions[i + 1]))
    
    if not gaps:
        return (page_width / 2, page_width / 2)
    
    largest_gap = max(gaps, key=lambda x: x[0])
    
    if largest_gap[0] > page_width * 0.1:
        return (largest_gap[1], largest_gap[2])
    
    return (page_width / 2, page_width / 2)


def get_column_for_block(block: Dict, left_boundary: float, right_boundary: float) -> int:
    """Return 0 for left column, 1 for right column."""
    bbox = block["bbox"]
    x_center = (bbox[0] + bbox[2]) / 2
    if x_center < (left_boundary + right_boundary) / 2:
        return 0
    return 1


def sort_blocks_column_aware(blocks: List[Dict], left_boundary: float, right_boundary: float) -> List[Dict]:
    """Sort blocks: first by Y (top to bottom), then by X (left to right)."""
    Y_TOLERANCE = 10
    
    def sort_key(block: Dict) -> Tuple[float, int, float]:
        bbox = block["bbox"]
        y_top = bbox[1]
        x_center = (bbox[0] + bbox[2]) / 2
        column = get_column_for_block(block, left_boundary, right_boundary)
        y_rounded = round(y_top / Y_TOLERANCE) * Y_TOLERANCE
        return (y_rounded, column, x_center)
    
    return sorted(blocks, key=sort_key)


def is_ability_block(block: Dict, block_index: int, all_blocks: List[Dict]) -> bool:
    """Detect ability blocks by font pattern."""
    if not block["lines"]:
        return False
    
    first_line = block["lines"][0]
    if not first_line["spans"]:
        return False
    
    first_span = first_line["spans"][0]
    font_size = first_span["size"]
    font_name = first_span["font"]
    text = first_span["text"].strip()
    
    is_ability_title = (
        "Newzald-Bold" in font_name and 
        9 <= font_size <= 11 and
        len(text) > 3
    )
    
    if is_ability_title:
        return True
    
    if block_index > 0:
        prev_block = all_blocks[block_index - 1]
        if prev_block["lines"] and prev_block["lines"][0]["spans"]:
            prev_font = prev_block["lines"][0]["spans"][0]["font"]
            prev_size = prev_block["lines"][0]["spans"][0]["size"]
            if "Newzald-Bold" in prev_font and 9 <= prev_size <= 11:
                if "BerlingskeSlab-Bold" in font_name and 7 <= font_size <= 8:
                    return True
                if any(word in text.lower() for word in ["power roll", "á", "é", "í"]):
                    return True
    
    return False


def is_header_or_footer(block: Dict, page_rect: fitz.Rect) -> bool:
    """Filter headers and footers by position."""
    bbox = block["bbox"]
    y0, y1 = bbox[1], bbox[3]
    page_height = page_rect.height
    
    header_threshold = page_height * 0.1
    footer_threshold = page_height * 0.9
    
    if y0 < header_threshold or y1 > footer_threshold:
        text = block["text"].strip()
        if len(text) < 100:
            return True
    
    return False


def is_sidebar(block: Dict, page_rect: fitz.Rect) -> bool:
    """Filter sidebars by position."""
    bbox = block["bbox"]
    x0, x1 = bbox[0], bbox[2]
    page_width = page_rect.width
    
    sidebar_threshold = page_width * 0.15
    
    if x0 < sidebar_threshold or x1 > (page_width - sidebar_threshold):
        block_width = x1 - x0
        if block_width < page_width * 0.25:
            return True
    
    return False


def clean_text(text: str) -> str:
    """Normalize whitespace and formatting."""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text


def get_section_for_page(page_num: int, toc: List[Tuple[int, str, int]]) -> Optional[str]:
    """Get the section name for a page using the table of contents."""
    page_num_1_indexed = page_num + 1
    current_section = None
    
    for level, title, toc_page in toc:
        if toc_page <= page_num_1_indexed:
            current_section = title
        else:
            break
    
    return current_section


def detect_section_header(block: Dict) -> Optional[str]:
    """Detect section headers by font pattern."""
    if not block["lines"]:
        return None
    
    first_line = block["lines"][0]
    if not first_line["spans"]:
        return None
    
    first_span = first_line["spans"][0]
    font_size = first_span["size"]
    font_name = first_span["font"]
    text = first_span["text"].strip()
    
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
    Extract rule text with column-aware sorting and paragraph merging.
    Groups paragraphs under section headers until next header is found.
    """
    page_rect = page.rect
    text_blocks = extract_text_blocks(page)
    
    # Detect column boundaries
    left_boundary, right_boundary = detect_columns(text_blocks, page_rect.width)
    
    # Sort blocks column-aware
    sorted_blocks = sort_blocks_column_aware(text_blocks, left_boundary, right_boundary)
    
    chunks = []
    current_section = get_section_for_page(page_num, toc)
    current_subsection = None
    current_column = None
    current_paragraphs = []  # Accumulate paragraphs for merging
    
    for i, block in enumerate(sorted_blocks):
        original_index = text_blocks.index(block) if block in text_blocks else i
        
        if original_index in ability_block_indices:
            continue
        
        if is_header_or_footer(block, page_rect):
            continue
        
        if is_sidebar(block, page_rect):
            continue
        
        block_column = get_column_for_block(block, left_boundary, right_boundary)
        
        # Check for section headers
        section_header = detect_section_header(block)
        if section_header:
            # Save accumulated paragraphs before processing new header
            if current_paragraphs:
                merged_text = ' '.join(current_paragraphs)
                merged_text = clean_text(merged_text)
                
                if merged_text and len(merged_text) > 10:
                    content_type = "rule"
                    text_lower = merged_text.lower()
                    if any(word in text_lower for word in ["example", "for example", "e.g."]):
                        content_type = "example"
                    elif any(word in text_lower for word in ["flavor", "story", "lore", "history"]):
                        content_type = "flavor_text"
                    
                    chunks.append({
                        "page": page_num + 1,
                        "text": merged_text,
                        "section": current_section,
                        "subsection": current_subsection,
                        "type": content_type
                    })
                
                current_paragraphs = []
            
            # Only update subsection if we're in the same column or starting a new column
            if current_column is None or current_column == block_column:
                current_subsection = section_header
                current_column = block_column
                chunks.append({
                    "page": page_num + 1,
                    "text": clean_text(section_header),
                    "section": current_section,
                    "subsection": current_subsection,
                    "type": "section_header"
                })
            continue
        
        # Handle column switching
        if current_column is not None and current_column != block_column:
            # Save accumulated paragraphs before switching columns
            if current_paragraphs:
                merged_text = ' '.join(current_paragraphs)
                merged_text = clean_text(merged_text)
                
                if merged_text and len(merged_text) > 10:
                    content_type = "rule"
                    text_lower = merged_text.lower()
                    if any(word in text_lower for word in ["example", "for example", "e.g."]):
                        content_type = "example"
                    elif any(word in text_lower for word in ["flavor", "story", "lore", "history"]):
                        content_type = "flavor_text"
                    
                    chunks.append({
                        "page": page_num + 1,
                        "text": merged_text,
                        "section": current_section,
                        "subsection": current_subsection,
                        "type": content_type
                    })
                
                current_paragraphs = []
            
            current_subsection = None  # Reset subsection when switching columns
        
        current_column = block_column
        
        text = clean_text(block["text"])
        if not text or len(text) < 10:
            continue
        
        # Accumulate paragraphs instead of creating immediate chunks
        current_paragraphs.append(text)
    
    # Save remaining paragraphs
    if current_paragraphs:
        merged_text = ' '.join(current_paragraphs)
        merged_text = clean_text(merged_text)
        
        if merged_text and len(merged_text) > 10:
            content_type = "rule"
            text_lower = merged_text.lower()
            if any(word in text_lower for word in ["example", "for example", "e.g."]):
                content_type = "example"
            elif any(word in text_lower for word in ["flavor", "story", "lore", "history"]):
                content_type = "flavor_text"
            
            chunks.append({
                "page": page_num + 1,
                "text": merged_text,
                "section": current_section,
                "subsection": current_subsection,
                "type": content_type
            })
    
    return chunks


def detect_all_ability_blocks(text_blocks: List[Dict]) -> Set[int]:
    """Detect all ability block indices."""
    ability_indices = set()
    
    for i, block in enumerate(text_blocks):
        if is_ability_block(block, i, text_blocks):
            ability_indices.add(i)
            if i + 1 < len(text_blocks):
                ability_indices.add(i + 1)
            if i + 2 < len(text_blocks):
                ability_indices.add(i + 2)
    
    return ability_indices


def main():
    """Extract rule text from the entire PDF."""
    print(f"\n[V5: Hybrid with Paragraph Merging] Extracting from {HEROES_PDF}")
    
    if not HEROES_PDF.exists():
        print(f"ERROR: PDF file not found at {HEROES_PDF}!")
        return
    
    doc = fitz.open(HEROES_PDF)
    total_pages = doc.page_count
    toc = doc.get_toc()
    
    print(f"Total pages: {total_pages}")
    
    try:
        all_chunks = []
        
        print("Processing pages...")
        for page_num in range(total_pages):
            if page_num % 50 == 0:
                print(f"  Processing page {page_num + 1}/{total_pages}...")
            
            page = doc[page_num]
            text_blocks = extract_text_blocks(page)
            ability_indices = detect_all_ability_blocks(text_blocks)
            chunks = extract_rule_text_from_page(page, page_num, toc, ability_indices)
            all_chunks.extend(chunks)
        
        print(f"\nCompleted! Extracted {len(all_chunks)} text chunks.")
        
        # Save to JSON
        output_dir = REPO_ROOT / "backend" / "data" / "heroes" / "rules"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "extracted_rules_v5_hybrid.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        
        print(f"Saved to: {output_file}")
        
    finally:
        doc.close()


if __name__ == "__main__":
    main()


"""
Extract and analyze ability blocks from the Draw Steel Heroes PDF.
Starting with page 32 (Melee/Ranged Weapon Free Strike abilities).
"""

from pathlib import Path
from typing import Dict, List

import fitz  # PyMuPDF

HEROES_PDF = Path("/Users/Ben.Wyatt/Personal/Draw Steel v1/Draw_Steel_Heroes_v1.pdf")


def print_section(title: str, level: int = 1):
    """Print a formatted section header."""
    if level == 1:
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)
    elif level == 2:
        print(f"\n{'-' * 60}")
        print(f"  {title}")
        print("-" * 60)
    else:
        print(f"\n{'  ' * (level - 2)}• {title}")


def extract_drawing_objects(page: fitz.Page) -> Dict[str, List]:
    """Extract lines and rectangles from the page."""
    drawings = page.get_drawings()

    horizontal_lines = []
    vertical_lines = []
    rectangles = []

    for drawing in drawings:
        items = drawing.get("items", [])

        for item in items:
            if item[0] == "l":  # line
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 1:  # horizontal
                    horizontal_lines.append(
                        {
                            "y": p1.y,
                            "x1": min(p1.x, p2.x),
                            "x2": max(p1.x, p2.x),
                            "length": abs(p2.x - p1.x),
                        }
                    )
                elif abs(p1.x - p2.x) < 1:  # vertical
                    vertical_lines.append(
                        {
                            "x": p1.x,
                            "y1": min(p1.y, p2.y),
                            "y2": max(p1.y, p2.y),
                            "length": abs(p2.y - p1.y),
                        }
                    )
            elif item[0] == "re":  # rectangle
                rect = item[1]
                rectangles.append(
                    {
                        "x0": rect.x0,
                        "y0": rect.y0,
                        "x1": rect.x1,
                        "y1": rect.y1,
                        "width": rect.width,
                        "height": rect.height,
                    }
                )

    return {
        "horizontal_lines": horizontal_lines,
        "vertical_lines": vertical_lines,
        "rectangles": rectangles,
    }


def extract_text_blocks(page: fitz.Page) -> List[Dict]:
    """Extract text blocks with detailed information."""
    text_dict = page.get_text("dict")
    blocks = []

    for block in text_dict.get("blocks", []):
        if "lines" not in block:  # Skip image blocks
            continue

        block_info = {"bbox": block["bbox"], "type": block.get("type", 0), "lines": []}

        for line in block["lines"]:
            line_info = {
                "bbox": line["bbox"],
                "wmode": line.get("wmode", 0),
                "dir": line.get("dir", (1, 0)),
                "spans": [],
            }

            for span in line["spans"]:
                span_info = {
                    "text": span.get("text", ""),
                    "font": span.get("font", ""),
                    "size": span.get("size", 0),
                    "color": span.get("color", 0),
                    "flags": span.get("flags", 0),
                    "bbox": span.get("bbox", (0, 0, 0, 0)),
                }
                line_info["spans"].append(span_info)

            # Combine span texts for line text
            line_info["text"] = "".join(s["text"] for s in line_info["spans"])
            block_info["lines"].append(line_info)

        # Combine line texts for block text
        block_info["text"] = "\n".join(l["text"] for l in block_info["lines"])
        blocks.append(block_info)

    return blocks


def extract_words_with_details(page: fitz.Page) -> List[Dict]:
    """Extract words with position and formatting details."""
    words_raw = page.get_text("words") or []
    words = []

    for w in words_raw:
        word_info = {
            "text": w[4] if len(w) > 4 else "",
            "x0": w[0],
            "y0": w[1],
            "x1": w[2],
            "y1": w[3],
            "block_no": w[5] if len(w) > 5 else -1,
            "line_no": w[6] if len(w) > 6 else -1,
            "word_no": w[7] if len(w) > 7 else -1,
        }
        words.append(word_info)

    return words


def identify_table_cells(
    horizontal_lines: List[Dict],
    vertical_lines: List[Dict],
    page_rect: fitz.Rect,
    min_line_length: float = 20,
) -> List[Dict]:
    """Identify table cells from line intersections."""
    # Filter meaningful lines (not decorative short ones)
    h_lines = [l for l in horizontal_lines if l["length"] >= min_line_length]
    v_lines = [l for l in vertical_lines if l["length"] >= min_line_length]

    if not h_lines or not v_lines:
        return []

    # Sort lines
    h_lines.sort(key=lambda l: l["y"])
    v_lines.sort(key=lambda l: l["x"])

    print(f"\n  Found {len(h_lines)} significant horizontal lines")
    print(f"  Found {len(v_lines)} significant vertical lines")

    # Build potential cells from line grid
    cells = []
    for i in range(len(h_lines) - 1):
        for j in range(len(v_lines) - 1):
            cell = {
                "row": i,
                "col": j,
                "x0": v_lines[j]["x"],
                "y0": h_lines[i]["y"],
                "x1": v_lines[j + 1]["x"],
                "y1": h_lines[i + 1]["y"],
            }
            cell["width"] = cell["x1"] - cell["x0"]
            cell["height"] = cell["y1"] - cell["y0"]
            cells.append(cell)

    return cells


def map_text_to_cells(text_blocks: List[Dict], cells: List[Dict]) -> List[Dict]:
    """Map text blocks to table cells."""
    for cell in cells:
        cell["text_blocks"] = []
        cell["text"] = ""

    for block in text_blocks:
        bx0, by0, bx1, by1 = block["bbox"]
        b_center_x = (bx0 + bx1) / 2
        b_center_y = (by0 + by1) / 2

        # Find which cell contains this block's center
        for cell in cells:
            if (
                cell["x0"] <= b_center_x <= cell["x1"]
                and cell["y0"] <= b_center_y <= cell["y1"]
            ):
                cell["text_blocks"].append(block)
                if cell["text"]:
                    cell["text"] += "\n" + block["text"]
                else:
                    cell["text"] = block["text"]
                break

    return cells


def detect_ability_blocks(text_blocks: List[Dict], page_rect: fitz.Rect) -> List[Dict]:
    """Detect ability block structures using font patterns and layout."""
    ability_blocks = []

    for i, block in enumerate(text_blocks):
        if not block["lines"]:
            continue

        # Check first line for ability name pattern
        first_line = block["lines"][0]
        if not first_line["spans"]:
            continue

        first_span = first_line["spans"][0]
        font_size = first_span["size"]
        font_name = first_span["font"]
        text = first_span["text"].strip()

        # Ability names are in Newzald-Bold @ ~10pt
        # They often contain keywords like "Strike", "Attack", "Maneuver", etc.
        is_ability_title = (
            "Newzald-Bold" in font_name
            and 9 <= font_size <= 11
            and len(text) > 0
            and
            # Exclude single-character or very short lines
            len(text) > 3
        )

        if is_ability_title:
            # Try to gather the complete ability (title + next 2-3 blocks)
            ability_data = {
                "title_block_index": i,
                "name": text,
                "bbox": block["bbox"],
                "font": font_name,
                "size": font_size,
                "title_block": block,
                "metadata_block": None,
                "effect_block": None,
            }

            # Next block is usually metadata (keywords, action type, range, target)
            if i + 1 < len(text_blocks):
                ability_data["metadata_block"] = text_blocks[i + 1]

            # Block after that is usually the effect/power roll
            if i + 2 < len(text_blocks):
                ability_data["effect_block"] = text_blocks[i + 2]

            ability_blocks.append(ability_data)

    return ability_blocks


def analyze_page(doc: fitz.Document, page_num: int):
    """Analyze a specific page for ability blocks."""
    page = doc[page_num]
    page_rect = page.rect

    print_section(f"PAGE {page_num + 1} ANALYSIS", 1)
    print(f"  Page dimensions: {page_rect.width:.2f} x {page_rect.height:.2f} pts")

    # Extract drawing objects
    print_section("Drawing Objects", 2)
    drawings = extract_drawing_objects(page)
    print(f"  Horizontal lines: {len(drawings['horizontal_lines'])}")
    print(f"  Vertical lines: {len(drawings['vertical_lines'])}")
    print(f"  Rectangles: {len(drawings['rectangles'])}")

    # Show significant lines only
    sig_h_lines = [l for l in drawings["horizontal_lines"] if l["length"] >= 30]
    sig_v_lines = [l for l in drawings["vertical_lines"] if l["length"] >= 30]

    print(f"  Significant horizontal lines (length >= 30): {len(sig_h_lines)}")
    print(f"  Significant vertical lines (length >= 30): {len(sig_v_lines)}")

    if sig_h_lines:
        print("\n  Significant horizontal lines:")
        for i, line in enumerate(sig_h_lines[:10]):
            print(
                f"    {i + 1}. y={line['y']:.2f}, x={line['x1']:.2f} to {line['x2']:.2f}, length={line['length']:.2f}"
            )

    if sig_v_lines:
        print("\n  Significant vertical lines:")
        for i, line in enumerate(sig_v_lines[:10]):
            print(
                f"    {i + 1}. x={line['x']:.2f}, y={line['y1']:.2f} to {line['y2']:.2f}, length={line['length']:.2f}"
            )

    # Extract text blocks
    print_section("Text Blocks", 2)
    text_blocks = extract_text_blocks(page)
    print(f"  Total text blocks: {len(text_blocks)}")

    # Show all text blocks with their details
    print("\n  All Text Blocks (detailed):")
    for i, block in enumerate(text_blocks):
        print(f"\n    Block {i}:")
        print(f"      BBox: {block['bbox']}")
        print(f"      Lines: {len(block['lines'])}")

        # Show first line details
        if block["lines"]:
            first_line = block["lines"][0]
            if first_line["spans"]:
                first_span = first_line["spans"][0]
                print(
                    f"      First span font: {first_span['font']} @ {first_span['size']:.1f}pt"
                )

        # Show text (truncated)
        text = block["text"]
        if len(text) > 200:
            print(f"      Text: {text[:200]}...")
        else:
            print(f"      Text: {text}")

    # Detect ability blocks
    print_section("Ability Block Detection", 2)
    ability_blocks = detect_ability_blocks(text_blocks, page_rect)
    print(f"  Found {len(ability_blocks)} ability blocks:")

    for i, ability in enumerate(ability_blocks):
        print(f"\n  {'=' * 70}")
        print(f"  ABILITY {i + 1}: {ability['name']}")
        print(f"  {'=' * 70}")

        print(f"\n    Title Block (Index {ability['title_block_index']}):")
        print(f"      Font: {ability['font']} @ {ability['size']:.1f}pt")
        print(f"      BBox: {ability['bbox']}")
        print(f"      Text: {ability['title_block']['text']}")

        if ability["metadata_block"]:
            print("\n    Metadata Block:")
            print("      Text:")
            for line in ability["metadata_block"]["text"].split("\n"):
                print(f"        {line}")

            # Parse metadata structure
            print("\n      Parsed Lines:")
            for j, line in enumerate(ability["metadata_block"]["lines"]):
                print(f"        Line {j + 1}: '{line['text']}'")

        if ability["effect_block"]:
            print("\n    Effect Block:")
            print("      Text:")
            for line in ability["effect_block"]["text"].split("\n"):
                print(f"        {line}")

            # Show font details for effects
            print("\n      Font Details:")
            for j, line in enumerate(ability["effect_block"]["lines"]):
                if line["spans"]:
                    first_span = line["spans"][0]
                    print(
                        f"        Line {j + 1} ({first_span['font']} @ {first_span['size']:.1f}pt): '{line['text']}'"
                    )

    # Try to identify table cells
    print_section("Table Cell Detection", 2)
    cells = identify_table_cells(
        drawings["horizontal_lines"],
        drawings["vertical_lines"],
        page_rect,
        min_line_length=30,
    )

    if cells:
        print(f"  Detected {len(cells)} potential table cells")
        cells_with_text = map_text_to_cells(text_blocks, cells)

        # Show cells with content
        cells_with_content = [c for c in cells_with_text if c["text"]]
        print(f"  Cells with text: {len(cells_with_content)}")

        # Show first few cells
        for i, cell in enumerate(cells_with_content[:10]):
            print(f"\n    Cell [{cell['row']}, {cell['col']}]:")
            print(
                f"      Position: ({cell['x0']:.1f}, {cell['y0']:.1f}) to ({cell['x1']:.1f}, {cell['y1']:.1f})"
            )
            print(f"      Size: {cell['width']:.1f} x {cell['height']:.1f}")
            print(f"      Text: {cell['text'][:100]}")
            if len(cell["text"]) > 100:
                print(f"        ... ({len(cell['text']) - 100} more chars)")
    else:
        print("  No table grid detected (not enough significant lines)")

    # Extract all words for detailed analysis
    print_section("Word-Level Analysis", 2)
    words = extract_words_with_details(page)
    print(f"  Total words: {len(words)}")

    # Find words related to abilities
    ability_keywords = [
        "Free Strike",
        "Melee",
        "Ranged",
        "Weapon",
        "Strike",
        "Action",
        "Trigger",
        "Effect",
    ]
    relevant_words = [
        w
        for w in words
        if any(kw.lower() in w["text"].lower() for kw in ability_keywords)
    ]

    print(f"  Words related to abilities: {len(relevant_words)}")
    for i, word in enumerate(relevant_words[:20]):
        print(f"    {i + 1}. '{word['text']}' @ ({word['x0']:.1f}, {word['y0']:.1f})")


def main():
    """Main extraction function."""
    print("\n" + "=" * 80)
    print("  ABILITY BLOCK EXTRACTION")
    print("  Starting with Page 32: Melee/Ranged Weapon Free Strike")
    print("=" * 80)
    print(f"\n  Target PDF: {HEROES_PDF}")
    print(f"  Exists: {HEROES_PDF.exists()}")

    if not HEROES_PDF.exists():
        print("\n  ERROR: PDF file not found!")
        return

    doc = fitz.open(HEROES_PDF)

    try:
        # Analyze page 32 (index 31)
        analyze_page(doc, 31)

        print("\n" + "=" * 80)
        print("  EXTRACTION COMPLETE")
        print("=" * 80 + "\n")

    finally:
        doc.close()


if __name__ == "__main__":
    main()

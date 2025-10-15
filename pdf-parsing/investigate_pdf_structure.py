"""
PDF Metadata and Structure Explorer
Focuses on extracting all available metadata with special attention to table structures.
"""
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF
import json


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


def explore_document_metadata(doc: fitz.Document):
    """Extract and display basic document metadata."""
    print_section("1. DOCUMENT METADATA", 1)
    
    metadata = doc.metadata
    if metadata:
        for key, value in metadata.items():
            print(f"  {key:20s}: {value}")
    else:
        print("  No metadata found")
    
    try:
        print(f"\n  PDF Version         : {doc.pdf_version() if hasattr(doc, 'pdf_version') else 'N/A'}")
    except:
        print(f"\n  PDF Version         : N/A")
    print(f"  Is PDF              : {doc.is_pdf}")
    print(f"  Is Encrypted        : {doc.is_encrypted}")
    print(f"  Page Count          : {doc.page_count}")
    print(f"  Has TOC/Outline     : {len(doc.get_toc()) > 0}")


def explore_toc(doc: fitz.Document):
    """Extract and display table of contents/outline."""
    print_section("2. TABLE OF CONTENTS / OUTLINE", 1)
    
    toc = doc.get_toc()
    if not toc:
        print("  No TOC/outline found")
        return
    
    print(f"  Total entries: {len(toc)}")
    print("\n  Structure (first 50 entries):")
    for i, (level, title, page) in enumerate(toc[:50]):
        indent = "  " * level
        print(f"  {indent}[Lvl{level}] {title} → Page {page}")
        if i >= 49 and len(toc) > 50:
            print(f"  ... and {len(toc) - 50} more entries")


def explore_page_structure(doc: fitz.Document):
    """Analyze page dimensions and structure."""
    print_section("3. PAGE STRUCTURE", 1)
    
    # Sample first 5 pages
    print(f"  Analyzing first 5 pages (of {doc.page_count} total):\n")
    for i in range(min(5, doc.page_count)):
        page = doc[i]
        rect = page.rect
        print(f"  Page {i+1}:")
        print(f"    MediaBox     : {rect}")
        print(f"    Dimensions   : {rect.width:.2f} x {rect.height:.2f} pts")
        print(f"    Rotation     : {page.rotation}°")
        print(f"    CropBox      : {page.cropbox}")


def explore_text_structure(doc: fitz.Document):
    """Analyze text layer structure and fonts."""
    print_section("4. TEXT LAYER STRUCTURE", 1)
    
    # Collect fonts from first 10 pages
    fonts_found = set()
    for i in range(min(10, doc.page_count)):
        page = doc[i]
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_name = span.get("font", "")
                        font_size = span.get("size", 0)
                        fonts_found.add((font_name, font_size))
    
    print(f"  Unique fonts found (first 10 pages): {len(fonts_found)}")
    print("\n  Font details:")
    for font, size in sorted(fonts_found, key=lambda x: (-x[1], x[0]))[:20]:
        print(f"    {font:40s} @ {size:.1f}pt")
    
    if len(fonts_found) > 20:
        print(f"    ... and {len(fonts_found) - 20} more font/size combinations")


def explore_page_objects(doc: fitz.Document, page_num: int = 0):
    """Deep dive into page objects structure."""
    print_section(f"5. PAGE OBJECT DETAILS (Page {page_num + 1})", 1)
    
    page = doc[page_num]
    text_dict = page.get_text("dict")
    
    print(f"  Total blocks on page: {len(text_dict.get('blocks', []))}")
    
    for block_idx, block in enumerate(text_dict.get("blocks", [])[:5]):  # First 5 blocks
        print(f"\n  Block {block_idx}:")
        print(f"    Type     : {block.get('type', 'unknown')}")  # 0=text, 1=image
        print(f"    BBox     : {block.get('bbox', 'N/A')}")
        
        if "lines" in block:
            print(f"    Lines    : {len(block['lines'])}")
            for line_idx, line in enumerate(block["lines"][:3]):  # First 3 lines
                print(f"      Line {line_idx}: bbox={line.get('bbox')}")
                for span_idx, span in enumerate(line["spans"][:2]):  # First 2 spans
                    print(f"        Span {span_idx}:")
                    print(f"          Text  : {repr(span.get('text', '')[:50])}")
                    print(f"          Font  : {span.get('font')}")
                    print(f"          Size  : {span.get('size')}pt")
                    print(f"          Color : {span.get('color')}")
                    print(f"          Flags : {span.get('flags')}")


def analyze_table_structure(doc: fitz.Document, sample_pages: List[int] = None):
    """
    PRIMARY FOCUS: Analyze table structure and representation.
    Examines how tables are encoded (lines, rectangles, text positioning).
    """
    print_section("6. TABLE STRUCTURE ANALYSIS (PRIMARY FOCUS)", 1)
    
    if sample_pages is None:
        # Sample pages that likely contain tables/ability blocks
        sample_pages = [10, 50, 100, 200, 300, 400]  # Diverse sampling
    
    for page_num in sample_pages:
        if page_num >= doc.page_count:
            continue
            
        page = doc[page_num]
        print_section(f"Page {page_num + 1}", 2)
        
        # 1. Check for drawing objects (lines, rectangles)
        print("\n  A. DRAWING OBJECTS (Lines & Rectangles):")
        drawings = page.get_drawings()
        print(f"     Total drawing objects: {len(drawings)}")
        
        # Analyze line types
        horizontal_lines = []
        vertical_lines = []
        rectangles = []
        
        for drawing in drawings:
            rect_info = drawing.get("rect")
            items = drawing.get("items", [])
            
            for item in items:
                if item[0] == "l":  # line
                    p1, p2 = item[1], item[2]
                    if abs(p1.y - p2.y) < 1:  # horizontal
                        horizontal_lines.append((p1, p2))
                    elif abs(p1.x - p2.x) < 1:  # vertical
                        vertical_lines.append((p1, p2))
                elif item[0] == "re":  # rectangle
                    rectangles.append(item[1])
        
        print(f"     Horizontal lines : {len(horizontal_lines)}")
        print(f"     Vertical lines   : {len(vertical_lines)}")
        print(f"     Rectangles       : {len(rectangles)}")
        
        # Show sample lines
        if horizontal_lines:
            print(f"\n     Sample horizontal lines (first 5):")
            for i, (p1, p2) in enumerate(horizontal_lines[:5]):
                print(f"       Line {i+1}: y={p1.y:.2f}, x={p1.x:.2f} to {p2.x:.2f}, length={abs(p2.x-p1.x):.2f}")
        
        if vertical_lines:
            print(f"\n     Sample vertical lines (first 5):")
            for i, (p1, p2) in enumerate(vertical_lines[:5]):
                print(f"       Line {i+1}: x={p1.x:.2f}, y={p1.y:.2f} to {p2.y:.2f}, length={abs(p2.y-p1.y):.2f}")
        
        if rectangles:
            print(f"\n     Sample rectangles (first 5):")
            for i, rect in enumerate(rectangles[:5]):
                print(f"       Rect {i+1}: {rect}")
        
        # 2. Text positioning analysis for table detection
        print("\n  B. TEXT POSITIONING (for cell detection):")
        words = page.get_text("words")
        if words:
            print(f"     Total words: {len(words)}")
            
            # Analyze Y-coordinates to find rows
            y_coords = sorted(set(w[1] for w in words))
            y_clusters = []
            current_cluster = [y_coords[0]]
            
            for y in y_coords[1:]:
                if y - current_cluster[-1] < 3:  # Within 3pts = same row
                    current_cluster.append(y)
                else:
                    y_clusters.append(sum(current_cluster) / len(current_cluster))
                    current_cluster = [y]
            if current_cluster:
                y_clusters.append(sum(current_cluster) / len(current_cluster))
            
            print(f"     Detected text rows: {len(y_clusters)}")
            
            # Analyze X-coordinates to find columns
            x_coords = sorted(set(w[0] for w in words))
            x_clusters = []
            current_cluster = [x_coords[0]]
            
            for x in x_coords[1:]:
                if x - current_cluster[-1] < 5:  # Within 5pts = same column
                    current_cluster.append(x)
                else:
                    x_clusters.append(sum(current_cluster) / len(current_cluster))
                    current_cluster = [x]
            if current_cluster:
                x_clusters.append(sum(current_cluster) / len(current_cluster))
            
            print(f"     Detected text columns: {len(x_clusters)}")
            
            # Show sample words with positions
            print(f"\n     Sample word positions (first 10):")
            for i, word in enumerate(words[:10]):
                x0, y0, x1, y1, text = word[:5]
                print(f"       '{text}' @ ({x0:.1f}, {y0:.1f}) to ({x1:.1f}, {y1:.1f})")
        
        # 3. Block structure analysis
        print("\n  C. BLOCK STRUCTURE:")
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])
        print(f"     Total blocks: {len(blocks)}")
        
        # Look for blocks that might be tables (multiple lines, similar spacing)
        table_candidates = []
        for block_idx, block in enumerate(blocks):
            if "lines" not in block:
                continue
            lines = block["lines"]
            if len(lines) < 3:
                continue
            
            # Check if lines are evenly spaced (table-like)
            y_positions = [line["bbox"][1] for line in lines]
            if len(y_positions) > 1:
                gaps = [y_positions[i+1] - y_positions[i] for i in range(len(y_positions)-1)]
                avg_gap = sum(gaps) / len(gaps)
                gap_variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
                
                if gap_variance < 10:  # Low variance = regular spacing
                    table_candidates.append({
                        "block_idx": block_idx,
                        "bbox": block["bbox"],
                        "lines": len(lines),
                        "avg_gap": avg_gap,
                        "variance": gap_variance
                    })
        
        print(f"     Table-like blocks (regular line spacing): {len(table_candidates)}")
        for i, candidate in enumerate(table_candidates[:3]):
            print(f"       Candidate {i+1}:")
            print(f"         Block index : {candidate['block_idx']}")
            print(f"         BBox        : {candidate['bbox']}")
            print(f"         Lines       : {candidate['lines']}")
            print(f"         Avg gap     : {candidate['avg_gap']:.2f}pt")
        
        # 4. Check for structured table data
        print("\n  D. STRUCTURED TABLE DATA:")
        try:
            tables = page.find_tables()
            if tables and hasattr(tables, 'tables'):
                print(f"     Found {len(tables.tables)} structured tables")
                for i, table in enumerate(tables.tables[:3]):
                    print(f"\n       Table {i+1}:")
                    print(f"         BBox     : {table.bbox}")
                    print(f"         Rows     : {table.row_count}")
                    print(f"         Columns  : {table.col_count}")
                    # Try to extract some data
                    try:
                        data = table.extract()
                        print(f"         Sample data (first 3 rows):")
                        for row_idx, row in enumerate(data[:3]):
                            print(f"           Row {row_idx}: {row}")
                    except:
                        print(f"         Could not extract data")
            else:
                print("     No structured tables found (page.find_tables() returned nothing)")
        except Exception as e:
            print(f"     Table extraction not available: {e}")


def explore_links_and_destinations(doc: fitz.Document, sample_pages: List[int] = None):
    """Analyze links and named destinations."""
    print_section("7. LINKS & DESTINATIONS", 1)
    
    if sample_pages is None:
        sample_pages = list(range(min(5, doc.page_count)))
    
    total_links = 0
    link_types = {}
    
    for page_num in sample_pages:
        if page_num >= doc.page_count:
            continue
        page = doc[page_num]
        links = page.get_links()
        total_links += len(links)
        
        for link in links:
            link_type = link.get("kind", "unknown")
            link_types[link_type] = link_types.get(link_type, 0) + 1
    
    print(f"  Total links on sampled pages: {total_links}")
    print(f"  Link types:")
    for link_type, count in link_types.items():
        print(f"    {str(link_type):15s}: {count}")


def explore_annotations(doc: fitz.Document, sample_pages: List[int] = None):
    """Check for annotations."""
    print_section("8. ANNOTATIONS", 1)
    
    if sample_pages is None:
        sample_pages = list(range(min(10, doc.page_count)))
    
    total_annots = 0
    annot_types = {}
    
    for page_num in sample_pages:
        if page_num >= doc.page_count:
            continue
        page = doc[page_num]
        annots = page.annots()
        
        if annots:
            for annot in annots:
                total_annots += 1
                annot_type = annot.type[1] if hasattr(annot, 'type') else "unknown"
                annot_types[annot_type] = annot_types.get(annot_type, 0) + 1
    
    if total_annots == 0:
        print("  No annotations found")
    else:
        print(f"  Total annotations on sampled pages: {total_annots}")
        print(f"  Annotation types:")
        for annot_type, count in annot_types.items():
            print(f"    {str(annot_type):15s}: {count}")


def explore_embedded_resources(doc: fitz.Document):
    """Analyze embedded resources."""
    print_section("9. EMBEDDED RESOURCES", 1)
    
    # Images
    image_count = 0
    for page_num in range(min(10, doc.page_count)):
        page = doc[page_num]
        images = page.get_images()
        image_count += len(images)
    
    print(f"  Images on first 10 pages: {image_count}")
    
    # Fonts
    try:
        font_list = []
        for page_num in range(min(10, doc.page_count)):
            page = doc[page_num]
            fonts = page.get_fonts()
            font_list.extend(fonts)
        
        unique_fonts = set(f[3] for f in font_list if len(f) > 3)  # font name is at index 3
        print(f"  Unique fonts on first 10 pages: {len(unique_fonts)}")
        for font in sorted(unique_fonts)[:15]:
            print(f"    - {font}")
        if len(unique_fonts) > 15:
            print(f"    ... and {len(unique_fonts) - 15} more")
    except Exception as e:
        print(f"  Could not extract font list: {e}")
    
    # Embedded files
    try:
        embedded = doc.embfile_names()
        if embedded:
            print(f"\n  Embedded files: {len(embedded)}")
            for name in embedded:
                print(f"    - {name}")
        else:
            print(f"\n  No embedded files")
    except:
        print(f"\n  Could not check for embedded files")


def explore_structure_tags(doc: fitz.Document):
    """Check for PDF structure tags."""
    print_section("10. DOCUMENT STRUCTURE TAGS", 1)
    
    # Check if PDF is tagged
    try:
        # Try to access structure information
        if hasattr(doc, 'pdf_catalog'):
            catalog = doc.pdf_catalog()
            if catalog:
                print(f"  PDF Catalog accessible: Yes")
                # Note: Full structure tree analysis requires lower-level access
                print(f"  Note: Full structure tree analysis requires additional tools")
            else:
                print(f"  PDF Catalog accessible: No")
        else:
            print(f"  PDF Catalog method not available in this PyMuPDF version")
    except Exception as e:
        print(f"  Could not access structure information: {e}")


def explore_custom_properties(doc: fitz.Document):
    """Extract custom/XMP metadata."""
    print_section("11. CUSTOM PROPERTIES", 1)
    
    try:
        xmp = doc.get_xml_metadata()
        if xmp:
            print(f"  XMP Metadata found: {len(xmp)} bytes")
            print(f"\n  XMP content (first 1000 chars):")
            print("  " + xmp[:1000].replace("\n", "\n  "))
            if len(xmp) > 1000:
                print(f"\n  ... and {len(xmp) - 1000} more characters")
        else:
            print("  No XMP metadata found")
    except Exception as e:
        print(f"  Could not extract XMP metadata: {e}")


def main():
    """Main exploration function."""
    print("\n" + "=" * 80)
    print("  PDF METADATA AND STRUCTURE EXPLORER")
    print("  Focus: Table Structure for Ability Blocks and Monster Stats")
    print("=" * 80)
    print(f"\n  Target PDF: {HEROES_PDF}")
    print(f"  Exists: {HEROES_PDF.exists()}")
    
    if not HEROES_PDF.exists():
        print("\n  ERROR: PDF file not found!")
        return
    
    # Open the PDF
    doc = fitz.open(HEROES_PDF)
    
    try:
        # Run all exploration functions
        explore_document_metadata(doc)
        explore_toc(doc)
        explore_page_structure(doc)
        explore_text_structure(doc)
        explore_page_objects(doc, page_num=10)  # Look at page 11
        
        # TABLE ANALYSIS - the main focus
        # Sample diverse pages likely to contain tables
        analyze_table_structure(doc, sample_pages=[10, 50, 100, 150, 200, 300])
        
        explore_links_and_destinations(doc)
        explore_annotations(doc)
        explore_embedded_resources(doc)
        explore_structure_tags(doc)
        explore_custom_properties(doc)
        
        print("\n" + "=" * 80)
        print("  EXPLORATION COMPLETE")
        print("=" * 80 + "\n")
        
    finally:
        doc.close()


if __name__ == "__main__":
    main()


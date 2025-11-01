"""
Convert PDF pages to images using PyMuPDF.

Supports converting individual pages, page ranges, or all pages to PNG images.
Includes utility function for base64 encoding images for vision model APIs.
"""

import argparse
import base64
from pathlib import Path

import fitz  # PyMuPDF

# Use PDF from local pdf directory (relative to repo root)
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
HEROES_PDF = REPO_ROOT / "pdf" / "Draw_Steel_Heroes_v1.pdf"
MONSTERS_PDF = REPO_ROOT / "pdf" / "Draw_Steel_Monsters_v1.pdf"


def dpi_to_zoom(dpi: int) -> float:
    """Convert DPI to PyMuPDF zoom factor."""
    # PyMuPDF uses a zoom factor where 1.0 = 72 DPI
    # So for 150 DPI: 150/72 = 2.083...
    return dpi / 72.0


def convert_page_to_image(
    doc: fitz.Document, page_num: int, output_path: Path, dpi: int = 150
) -> Path:
    """
    Convert a single PDF page to an image.

    Args:
        doc: PyMuPDF document object
        page_num: Page number (0-indexed)
        output_path: Full path including filename for output image
        dpi: Resolution in DPI (default: 150)

    Returns:
        Path to the saved image file
    """
    page = doc[page_num]

    # Create a transformation matrix for the desired DPI
    zoom = dpi_to_zoom(dpi)
    matrix = fitz.Matrix(zoom, zoom)

    # Render page to pixmap
    pixmap = page.get_pixmap(matrix=matrix)  # type: ignore[attr-defined]

    # Save as PNG
    pixmap.save(output_path)

    # Clean up
    pixmap = None

    return output_path


def encode_image(image_path: Path) -> str:
    """
    Encode a local image file to a Base64 string.

    Useful for vision model API calls (matching pattern from parse_image.py).

    Args:
        image_path: Path to the image file

    Returns:
        Base64 encoded string of the image
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def main():
    """Main function to convert PDF pages to images."""
    parser = argparse.ArgumentParser(
        description="Convert PDF pages to images using PyMuPDF"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default=str(HEROES_PDF),
        help=f"Path to PDF file (default: {HEROES_PDF})",
    )
    parser.add_argument(
        "--page", type=int, help="Single page number to convert (1-indexed)"
    )
    parser.add_argument(
        "--start-page",
        type=int,
        help="Start page number for range conversion (1-indexed, inclusive)",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        help="End page number for range conversion (1-indexed, inclusive)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for images (default: backend/data/images relative to repo root)",
    )
    parser.add_argument(
        "--dpi", type=int, default=150, help="Resolution in DPI (default: 150)"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="png",
        choices=["png"],
        help="Output image format (default: png, currently only PNG supported)",
    )

    args = parser.parse_args()

    # Resolve PDF path
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        return

    # Set up output directory (default to backend/data/images relative to repo root)
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = REPO_ROOT / "backend" / "data" / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Open PDF
    print(f"\nOpening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    print(f"Total pages: {total_pages}\n")

    try:
        # Determine which pages to convert
        if args.page:
            # Single page specified
            page_num = args.page - 1  # Convert to 0-indexed
            if page_num < 0 or page_num >= total_pages:
                print(f"ERROR: Page {args.page} is out of range (1-{total_pages})")
                return
            pages_to_convert = [page_num]
        elif args.start_page is not None or args.end_page is not None:
            # Page range specified
            start = (args.start_page or 1) - 1  # Convert to 0-indexed
            end = (args.end_page or total_pages) - 1  # Convert to 0-indexed

            if start < 0:
                start = 0
            if end >= total_pages:
                end = total_pages - 1

            if start > end:
                print(
                    f"ERROR: Start page ({args.start_page or 1}) must be <= end page ({args.end_page or total_pages})"
                )
                return

            pages_to_convert = list(range(start, end + 1))
        else:
            # Convert all pages
            pages_to_convert = list(range(total_pages))

        print(f"Converting {len(pages_to_convert)} page(s) at {args.dpi} DPI...")
        print(f"Output directory: {output_dir}\n")

        # Convert each page
        for i, page_num in enumerate(pages_to_convert):
            # Generate output filename (1-indexed for display)
            output_filename = f"page_{page_num + 1:04d}.png"
            output_path = output_dir / output_filename

            # Convert page
            convert_page_to_image(doc, page_num, output_path, args.dpi)

            # Progress update
            if (i + 1) % 10 == 0 or (i + 1) == len(pages_to_convert):
                print(
                    f"  Converted page {page_num + 1}/{total_pages} -> {output_filename}"
                )

        print(f"\nCompleted! Converted {len(pages_to_convert)} page(s) to {output_dir}")

    finally:
        doc.close()


if __name__ == "__main__":
    main()

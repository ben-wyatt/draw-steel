"""
Page Transcription Tool

Uses GPT-5 Nano to extract text from PDF pages via vision models.
Converts PDF pages to images on-the-fly and processes them asynchronously
to produce a single markdown file with all transcriptions.
"""

import argparse
import asyncio
import base64
from pathlib import Path

import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm

from backend.utils.keys import get_openrouter_api_key

load_dotenv()


def dpi_to_zoom(dpi: int) -> float:
    """Convert DPI to PyMuPDF zoom factor."""
    # PyMuPDF uses a zoom factor where 1.0 = 72 DPI
    # So for 150 DPI: 150/72 = 2.083...
    return dpi / 72.0


def convert_page_to_base64(doc: fitz.Document, page_num: int, dpi: int = 150) -> str:
    """
    Convert a PDF page to a base64-encoded image in memory.

    Args:
        doc: PyMuPDF document object
        page_num: Page number (0-indexed)
        dpi: Resolution in DPI (default: 150)

    Returns:
        Base64-encoded string of the PNG image
    """
    page = doc[page_num]

    # Create a transformation matrix for the desired DPI
    zoom = dpi_to_zoom(dpi)
    matrix = fitz.Matrix(zoom, zoom)

    # Render page to pixmap
    pixmap = page.get_pixmap(matrix=matrix)  # type: ignore[attr-defined]

    # Convert pixmap to PNG bytes in memory
    img_bytes = pixmap.tobytes("png")  # type: ignore[attr-defined]

    # Clean up
    pixmap = None

    # Encode to base64
    return base64.b64encode(img_bytes).decode("utf-8")


TRANSCRIPTION_SYSTEM_PROMPT = """Extract all text from this TTRPG book page image and transcribe it to markdown format.

Formatting requirements:
- Use markdown headers (# for main headings, ## for subheadings, ### for sub-subheadings)
- Convert tables to markdown table syntax with proper alignment (| column | column |)
- Use markdown lists (- or *) for bulleted items
- Use markdown bold (**text**) and italic (*text*) where appropriate
- Preserve paragraph structure with blank lines between paragraphs

Content extraction:
- Extract all readable text from the page
- Convert headings to appropriate markdown header levels
- Convert tables to markdown table format with proper column alignment
- Preserve the logical structure and hierarchy of content

What to SKIP (do NOT transcribe in full):
- Ability blocks: Skip entire ability blocks that contain structured statistics tables. These typically include:
  * An ability name (often with special formatting or icons)
  * A quote or flavor text line (e.g., "Move or die, folks.")
  * A table with columns like "Type", "Range", "Main action", "Maneuver", "Effect", "Special", "Damage", etc.
  * Numerical values like "Range 10", "Main action", resource costs, etc.
- Monster stat blocks: Skip complete monster stat blocks with extensive structured data
- Item blocks: Skip treasure rewards and mechanical item descriptions
- Power roll tables: Skip tables showing dice mechanics and power roll outcomes
- Complex structured mechanics: Skip any content that combines ability/power names with detailed statistical tables

When skipping structured content, insert a structured note in the format: [[Name|type]]
- Replace "Name" with the actual name of the ability, monster, or item
- Replace "type" with one of: "ability", "monster_block", "item" or "other
- Examples: [[Issue Order|ability]], [[Goblin Warrior|monster_block]], [[Sword of Truth|item]]

What to KEEP (DO transcribe):
- Narrative descriptions and flavor text
- Benefit and Drawback sections (these are narrative descriptions, not structured stats)
- Simple rule explanations and descriptions
- Headings and subheadings for narrative content
- Lists containing descriptive content
- Simple tables that are NOT ability/stat block tables (e.g., skill lists, general reference tables)

Guidance: If you see content like "Benefit: [description]" or "Drawback: [description]", transcribe it. But if you see an ability name followed by a quote and then a table with columns like "Range", "Main action", etc., replace that entire ability block with [[AbilityName|ability]]. Do the same for monster stat blocks ([[MonsterName|monster_block]]) and item blocks ([[ItemName|item]]).
"""


async def transcribe_page(
    client: AsyncOpenAI,
    doc: fitz.Document,
    page_num: int,
    semaphore: asyncio.Semaphore,
    model: str = "openai/gpt-5-nano",
    dpi: int = 150,
):
    """
    Transcribe a single page image using vision model.

    Args:
        client: AsyncOpenAI client configured for OpenRouter
        doc: PyMuPDF document object
        page_num: Page number (0-indexed)
        semaphore: Semaphore to limit concurrent requests
        model: Model to use (default: gpt-5-nano)
        dpi: DPI for image conversion (default: 150)

    Returns:
        Tuple of (page_number (1-indexed), transcription_text)
    """
    page_number = page_num + 1  # Convert to 1-indexed for display

    async with semaphore:
        try:
            # Convert page to base64 image
            base64_image = convert_page_to_base64(doc, page_num, dpi)

            # Build prompt
            prompt = TRANSCRIPTION_SYSTEM_PROMPT

            # Call vision model
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
            )

            transcription = response.choices[0].message.content
            if transcription is None:
                raise ValueError("Empty transcription returned from model")

            return (page_number, transcription)

        except Exception as e:
            print(f"  Error transcribing page {page_number}: {e}")
            return (
                page_number,
                f"Error during transcription: {str(e)}\n",
            )


async def main():
    """Main function to transcribe pages and write markdown output."""
    parser = argparse.ArgumentParser(
        description="Transcribe PDF pages to markdown using vision models"
    )
    parser.add_argument(
        "--pdf-path",
        type=str,
        required=True,
        help="Path to PDF file",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        required=True,
        help="Path to output markdown file",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Start page number (1-indexed, default: 1)",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        default=None,
        help="End page number (1-indexed, default: all pages)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-5-nano",
        help="Model to use (default: openai/gpt-5-nano)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=32,
        help="Maximum number of concurrent requests (default: 32)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI for image conversion (default: 150)",
    )

    args = parser.parse_args()

    # Validate PDF path
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        return

    # Validate output path
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Open PDF
    print(f"\nOpening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    print(f"Total pages: {total_pages}\n")

    try:
        # Determine page range
        start_idx = max(0, args.start_page - 1)  # Convert to 0-indexed
        if args.end_page:
            end_idx = min(args.end_page - 1, total_pages - 1)  # Convert to 0-indexed
        else:
            end_idx = total_pages - 1  # Convert to 0-indexed (last page)

        # Validate range
        if start_idx > end_idx:
            print(
                f"ERROR: Invalid page range: start ({args.start_page}) > end ({args.end_page or total_pages})"
            )
            return

        # Range is inclusive, so use end_idx + 1
        pages_to_process = list(range(start_idx, end_idx + 1))
        end_page_display = (end_idx + 1) if args.end_page is None else args.end_page
        print(
            f"Processing {len(pages_to_process)} page(s) (pages {args.start_page} to {end_page_display})"
        )
        print(f"Output: {output_path}")
        print(f"Model: {args.model}")
        print(f"DPI: {args.dpi}")
        print(f"Max concurrent requests: {args.max_concurrent}\n")

        # Initialize OpenRouter client
        api_key = get_openrouter_api_key()
        if not api_key:
            print("ERROR: OPENROUTER_API_KEY not found in environment or ~/.zshenv")
            return

        client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(args.max_concurrent)

        # Process pages concurrently with progress bar
        print(f"Starting concurrent processing of {len(pages_to_process)} pages...\n")
        tasks = [
            transcribe_page(
                client,
                doc,
                page_num,
                semaphore,
                args.model,
                args.dpi,
            )
            for page_num in pages_to_process
        ]

        # Use tqdm to show progress
        transcription_results = await tqdm.gather(
            *tasks, desc="Transcribing pages", total=len(tasks)
        )

        # Sort results by page number (in case async processing reordered them)
        transcription_results.sort(key=lambda x: x[0])

        # Combine all transcriptions into single markdown file
        print("\nCombining transcriptions into markdown file...")
        with open(output_path, "w", encoding="utf-8") as f:
            for page_number, transcription in transcription_results:
                # Add deterministic page header in post-processing
                f.write(f"[[Begin Page {page_number}]]\n\n")
                f.write(transcription)
                # Add spacing between pages if not already present
                if not transcription.endswith("\n\n"):
                    f.write("\n\n")

        print(f"\nCompleted! Transcribed {len(pages_to_process)} page(s)")
        print(f"Saved transcriptions to {output_path}")

        # Close the client
        await client.close()

    finally:
        doc.close()


if __name__ == "__main__":
    asyncio.run(main())

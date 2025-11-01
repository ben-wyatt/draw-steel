"""
Data Types Catalog Builder

Uses GPT-5 Nano to analyze PDF page images and catalog what data structure types
are present on each page (monster stat blocks, abilities, equipment, etc.).
Auto-detects PDF source (heroes/monsters) and saves to appropriate location.
"""

import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm

load_dotenv()


def get_openrouter_api_key() -> Optional[str]:
    """Get OPENROUTER_API_KEY from environment or ~/.zshenv file."""
    # First check environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    # Try loading from ~/.zshenv
    zshenv_path = Path.home() / ".zshenv"
    if zshenv_path.exists():
        try:
            with open(zshenv_path, "r") as f:
                for line in f:
                    line = line.strip()
                    # Handle both "export OPENROUTER_API_KEY=" and "OPENROUTER_API_KEY="
                    if line.startswith("export OPENROUTER_API_KEY="):
                        value = line.split("=", 1)[1].strip()
                    elif line.startswith("OPENROUTER_API_KEY="):
                        value = line.split("=", 1)[1].strip()
                    else:
                        continue

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    return value
        except Exception:
            pass

    return None


# Use images from whole-image-parsing directory
SCRIPT_DIR = Path(__file__).parent
IMAGES_DIR = SCRIPT_DIR / "whole-image-parsing" / "images"


class PageClassification(BaseModel):
    """Classification result for a single page."""

    page_number: int
    pdf_source: str = Field(
        default="unknown",
        description="Source PDF: 'heroes' or 'monsters'",
    )
    data_types_found: List[str] = Field(
        default_factory=list,
        description="List of data types found on this page (e.g., 'monster_stat_block', 'character_ability', 'equipment')",
    )
    confidence: str = Field(
        default="medium",
        description="Confidence level: 'low', 'medium', or 'high'",
    )
    notes: Optional[str] = Field(
        default=None, description="Additional notes about the page content"
    )


def encode_image(image_path: Path) -> str:
    """Encode a local image file to a Base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def detect_pdf_source(
    images_dir: Path, pdf_source_override: Optional[str] = None
) -> str:
    """
    Detect PDF source from images directory path or use override.

    Args:
        images_dir: Path to images directory
        pdf_source_override: Optional explicit PDF source override

    Returns:
        PDF source: 'heroes' or 'monsters'
    """
    if pdf_source_override:
        return pdf_source_override.lower()

    # Check images directory path
    path_str = str(images_dir).lower()
    if "heroes" in path_str:
        return "heroes"
    elif "monsters" in path_str:
        return "monsters"

    # Check parent directories
    current = images_dir
    for _ in range(5):  # Check up to 5 levels up
        current = current.parent
        path_str = str(current).lower()
        if "heroes" in path_str:
            return "heroes"
        elif "monsters" in path_str:
            return "monsters"

    # Default to heroes if can't detect
    return "heroes"


async def classify_page(
    client: AsyncOpenAI,
    image_path: Path,
    page_number: int,
    semaphore: asyncio.Semaphore,
    pdf_source: str,
    model: str = "openai/gpt-5-nano",
    data_types_list: Optional[List[str]] = None,
) -> PageClassification:
    """
    Classify a single page image to identify what data types are present.

    Args:
        client: AsyncOpenAI client configured for OpenRouter
        image_path: Path to the page image
        page_number: Page number for tracking
        semaphore: Semaphore to limit concurrent requests
        model: Model to use (default: gpt-5-nano)
        data_types_list: Optional list of data types to look for

    Returns:
        PageClassification object with results
    """
    async with semaphore:
        # Encode image
        base64_image = encode_image(image_path)

        # Build classification prompt
        if data_types_list:
            types_prompt = (
                f"\n\nLook for these specific data types: {', '.join(data_types_list)}"
            )
        else:
            types_prompt = (
                "\n\nCommon data types to look for include: "
                "monster_stat_block, character_ability, equipment, "
                "game_mechanics, rules_text, table, flavor_text, etc."
            )

        prompt = f"""Analyze this PDF page image and identify what types of structured data or content are present.

Classify the page into data types such as:
- monster_stat_block: Monster/NPC stat blocks with stats, abilities, traits
- character_ability: Player character abilities with power rolls and effects
- equipment: Weapons, armor, items
- game_mechanics: Rules explanations, mechanics
- table: Data tables
- flavor_text: Narrative text, descriptions
- other: Any other structured content{types_prompt}

Return a classification with:
- The data types found (list of strings)
- Confidence level (low/medium/high)
- Brief notes about what's on the page

Page number: {page_number}
"""

        try:
            response = await client.beta.chat.completions.parse(
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
                response_format=PageClassification,
            )

            classification = response.choices[0].message.parsed
            if classification is None:
                raise ValueError("Failed to parse classification from response")

            return classification

        except Exception as e:
            print(f"  Error classifying page {page_number}: {e}")
            # Return a default classification with error note
            return PageClassification(
                page_number=page_number,
                pdf_source=pdf_source,
                data_types_found=[],
                confidence="low",
                notes=f"Error during classification: {str(e)}",
            )


async def main():
    """Main function to classify pages and build catalog."""
    parser = argparse.ArgumentParser(
        description="Classify PDF pages to catalog data structure types"
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Start page number (default: 1)",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        default=None,
        help="End page number (default: all available pages)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: auto-detected based on PDF source)",
    )
    parser.add_argument(
        "--pdf-source",
        type=str,
        choices=["heroes", "monsters"],
        default=None,
        help="Explicitly specify PDF source: 'heroes' or 'monsters' (default: auto-detect from images directory)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-5-nano",
        help="Model to use (default: openai/gpt-5-nano)",
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default=None,
        help="Directory containing page images (default: whole-image-parsing/images/)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum number of concurrent requests (default: 10)",
    )

    args = parser.parse_args()

    # Set up images directory
    if args.images_dir:
        images_dir = Path(args.images_dir)
    else:
        images_dir = IMAGES_DIR

    if not images_dir.exists():
        print(f"ERROR: Images directory not found: {images_dir}")
        return

    # Detect PDF source
    pdf_source = detect_pdf_source(images_dir, args.pdf_source)
    print(f"Detected PDF source: {pdf_source}")

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Auto-generate output path based on PDF source
        repo_root = Path(__file__).parent.parent.parent
        output_path = repo_root / "data" / pdf_source / "page-classifications.json"
        print(f"Auto-detected output path: {output_path}")

    # Load existing classifications if output file exists
    existing_classifications = {}
    if output_path.exists():
        try:
            with open(output_path, "r") as f:
                existing_data = json.load(f)
                # Convert list to dict keyed by page_number for efficient lookup
                existing_classifications = {
                    item["page_number"]: item for item in existing_data
                }
            print(
                f"Loaded {len(existing_classifications)} existing classifications from {output_path}"
            )
        except Exception as e:
            print(f"Warning: Could not load existing classifications: {e}")
            existing_classifications = {}

    # Find all page images
    page_images = sorted(images_dir.glob("page_*.png"))
    if not page_images:
        print(f"ERROR: No page images found in {images_dir}")
        return

    # Determine page range
    start_idx = args.start_page - 1  # Convert to 0-indexed
    if args.end_page:
        end_idx = args.end_page
    else:
        end_idx = len(page_images)

    # Filter to requested range
    page_images = page_images[start_idx:end_idx]

    print(f"\nFound {len(page_images)} page images")
    print(
        f"Processing pages {args.start_page} to {args.start_page + len(page_images) - 1}"
    )
    print(f"Output: {args.output}")
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
    print(f"Starting concurrent processing of {len(page_images)} pages...\n")
    tasks = [
        classify_page(
            client,
            image_path,
            args.start_page + i,
            semaphore,
            pdf_source,
            args.model,
        )
        for i, image_path in enumerate(page_images)
    ]

    # Use tqdm to show progress
    classifications = await tqdm.gather(
        *tasks, desc="Processing pages", total=len(tasks)
    )

    # Convert new classifications to dict format, ensuring pdf_source is set
    new_classifications_dict = {}
    for cls in classifications:
        cls_dict = cls.model_dump()
        # Ensure pdf_source is set even if it wasn't in the model response
        if "pdf_source" not in cls_dict or cls_dict["pdf_source"] == "unknown":
            cls_dict["pdf_source"] = pdf_source
        new_classifications_dict[cls.page_number] = cls_dict

    # Merge with existing classifications (new ones override existing)
    merged_classifications = {**existing_classifications, **new_classifications_dict}

    # Convert back to sorted list
    classifications_list = sorted(
        merged_classifications.values(), key=lambda x: x["page_number"]
    )

    # Save merged results
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(classifications_list, f, indent=2)

    new_count = len(new_classifications_dict)
    updated_count = sum(
        1
        for page_num in new_classifications_dict
        if page_num in existing_classifications
    )
    added_count = new_count - updated_count

    print(
        f"\nCompleted! Processed {new_count} pages ({added_count} new, {updated_count} updated)"
    )
    print(f"Saved {len(classifications_list)} total classifications to {output_path}")

    # Print summary statistics
    all_types = set()
    for cls in classifications_list:
        all_types.update(cls["data_types_found"])

    print("\nSummary:")
    print(f"  Total pages in catalog: {len(classifications_list)}")
    print(f"  Unique data types found: {len(all_types)}")
    print(f"  Data types: {', '.join(sorted(all_types))}")

    # Close the client
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())

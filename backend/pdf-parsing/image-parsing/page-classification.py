"""
Page Classification Catalog Builder

Uses GPT-5 Nano to analyze PDF page images and catalog what data structure types
are present on each page. Supports both Heroes and Monsters books.

Auto-detects PDF source from images directory path or accepts explicit specification.
"""

import argparse
import asyncio
import base64
import json
import re
from pathlib import Path
from typing import List, Optional, Type, Union

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm

from backend.utils.keys import get_openrouter_api_key

load_dotenv()


SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent


class HeroesPageClassification(BaseModel):
    """Classification result for a single page from the Heroes book."""

    data_types_found: List[str] = Field(
        default_factory=list,
        description="List of data types found on this page (e.g., 'character_ability', 'ancestry', 'class', 'equipment')",
    )
    summary: str = Field(
        description="A 2-3 sentence summary describing the main content and purpose of this page"
    )


class MonstersPageClassification(BaseModel):
    """Classification result for a single page from the Monsters book."""

    data_types_found: List[str] = Field(
        default_factory=list,
        description="List of data types found on this page (e.g., 'monster_stat_block', 'monster_ability', 'monster_trait')",
    )
    summary: str = Field(
        description="A 2-3 sentence summary describing the main content and purpose of this page"
    )
    names_of_monster_stat_block: Optional[List[str]] = Field(
        default=None,
        description="List of monster names found in stat blocks on this page (e.g., ['Goblin Warrior', 'Goblin Shaman'])",
    )


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


def get_classification_model(
    pdf_source: str,
) -> Type[Union[HeroesPageClassification, MonstersPageClassification]]:
    """
    Get the appropriate Pydantic model for classification based on PDF source.

    Args:
        pdf_source: PDF source ('heroes' or 'monsters')

    Returns:
        The appropriate Pydantic model class
    """
    if pdf_source.lower() == "heroes":
        return HeroesPageClassification
    else:
        return MonstersPageClassification


def parse_page_number(image_path: Path) -> int:
    """
    Parse page number from image filename.

    Expected format: page_0266.png -> 266

    Args:
        image_path: Path to the image file

    Returns:
        Page number as integer
    """
    filename = image_path.stem  # Gets filename without extension (e.g., "page_0266")
    match = re.search(r"page_(\d+)", filename)
    if match:
        return int(match.group(1))
    raise ValueError(f"Could not parse page number from filename: {image_path.name}")


def encode_image(image_path: Path) -> str:
    """Encode a local image file to a Base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def build_classification_prompt(
    pdf_source: str,
    page_number: int,
    data_types_list: Optional[List[str]] = None,
) -> str:
    """
    Build the classification prompt based on PDF source.

    Args:
        pdf_source: PDF source ('heroes' or 'monsters')
        page_number: Page number for tracking
        data_types_list: Optional list of specific data types to look for

    Returns:
        Classification prompt string
    """
    # Build types prompt
    if data_types_list:
        types_prompt = (
            f"\n\nLook for these specific data types: {', '.join(data_types_list)}"
        )
    else:
        types_prompt = ""

    if pdf_source.lower() == "heroes":
        prompt = f"""Analyze this PDF page image from the Heroes book and identify what types of structured data or content are present.

Identify the existence of the following data types on the page:
- ancestry: flavor text or mechanics related to player character ancestries
- background: flavor text or mechanics related to player character backgrounds
- class: flavor text or mechanics related to player character classes
- kit: specific additional game mechanic related to equipment loadouts
- perks: outside-combat character benefits (described specifically as perks in the text)
- complications: optional PC roleplaying benefits and drawbacks that influence gameplay (described specifically as complications in the text)
- negotiation: mechanics related to negotiation with NPCs (explicitly described as negotiation in the text)
- downtime_projects: mechanics related to downtime projects (explicitly described as downtime projects in the text)
- treasures: supernatural items for PCs
- certain rewards like: titles, renown, wealth. specifically described as such in the text
- game_mechanics: Rules explanations, abilities, anything to do with *playing the game* and not just flavor text
- table: roll charts and data tables
- flavor_text: Narrative text, descriptions
- one of the classes: censor, conduit, elementalist, fury, null, shadow, tactician, talent, troubadour

Return a classification with:
- The data types found (list of strings)
- A 2-3 sentence summary describing the main content and purpose of this page

Page number: {page_number}
"""
    else:
        prompt = f"""Analyze this PDF page image from the Monsters book and identify what types of structured data or content are present.

Identify the existence of the following data types on the page:
- flavor_text: Narrative text, descriptions
- general_game_mechanics: Rules explanations, abilities, anything to do with *playing the game* and not just flavor text
- monster_stat_block: contains many, one, or a part of a monster stat block, including abilities, traits, and characteristics
- table: roll charts and data tables
- creature organization: if there is a stat block, call out the creature organization. one of: minion, horde, platoon, elite, leader, solo,
- creature role: if there is a stat block, call out the creature role. one of: ambusher, artillery, brute, controller, defender, harrier, hexer, mount, support


Return a classification with:
- The data types found (list of strings)
- A 2-3 sentence summary describing the main content and purpose of this page
- names_of_monster_stat_block: If monster_stat_block is in data_types_found, provide a list of all monster names found in stat blocks on this page (e.g., ['Goblin Warrior', 'Goblin Shaman']). If no monster stat blocks are present, this field should be None or omitted.

Page number: {page_number}
"""

    return prompt


async def classify_page(
    client: AsyncOpenAI,
    image_path: Path,
    semaphore: asyncio.Semaphore,
    pdf_source: str,
    model: str = "openai/gpt-5-nano",
    data_types_list: Optional[List[str]] = None,
):
    """
    Classify a single page image to identify what data types are present.

    Args:
        client: AsyncOpenAI client configured for OpenRouter
        image_path: Path to the page image
        semaphore: Semaphore to limit concurrent requests
        pdf_source: PDF source ('heroes' or 'monsters')
        model: Model to use (default: gpt-5-nano)
        data_types_list: Optional list of data types to look for

    Returns:
        Tuple of (page_number, HeroesPageClassification or MonstersPageClassification object)
    """
    # Parse page number from filename
    page_number = parse_page_number(image_path)

    async with semaphore:
        # Encode image
        base64_image = encode_image(image_path)

        # Get the appropriate classification model
        ClassificationModel = get_classification_model(pdf_source)

        # Build classification prompt based on PDF source
        prompt = build_classification_prompt(pdf_source, page_number, data_types_list)

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
                response_format=ClassificationModel,
            )

            classification = response.choices[0].message.parsed
            if classification is None:
                raise ValueError("Failed to parse classification from response")

            return (page_number, classification)

        except Exception as e:
            print(f"  Error classifying page {page_number}: {e}")
            # Return a default classification with error note using the appropriate model
            ClassificationModel = get_classification_model(pdf_source)
            return (
                page_number,
                ClassificationModel(
                    data_types_found=[],
                    summary=f"Error during classification: {str(e)}",
                ),
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
        help="Directory containing page images (default: backend/data/heroes/images relative to repo root)",
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
        # Default to heroes images directory
        images_dir = REPO_ROOT / "backend" / "data" / "heroes" / "images"

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
        output_path = (
            REPO_ROOT / "backend" / "data" / pdf_source / "page-classifications.json"
        )
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
    print(f"Output: {output_path}")
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
            semaphore,
            pdf_source,
            args.model,
        )
        for image_path in page_images
    ]

    # Use tqdm to show progress
    classification_results = await tqdm.gather(
        *tasks, desc="Processing pages", total=len(tasks)
    )

    # Convert new classifications to dict format, ensuring pdf_source and page_number are set
    new_classifications_dict = {}
    for page_number, cls in classification_results:
        cls_dict = cls.model_dump()
        # Ensure pdf_source is set programmatically (not from LLM)
        cls_dict["pdf_source"] = pdf_source
        # Add page_number parsed from filename
        cls_dict["page_number"] = page_number
        new_classifications_dict[page_number] = cls_dict

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

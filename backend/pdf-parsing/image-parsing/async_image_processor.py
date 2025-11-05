"""
Async LLM Batch Processor

Provides a reusable async function for batch processing page images with LLM vision models.
Supports heroes and monsters books with flexible filtering options.
"""

import asyncio
import base64
import json
import re
from pathlib import Path
from typing import List, Optional, Tuple, Type

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_core._pydantic_core import ValidationError
from tqdm.asyncio import tqdm

from backend.models.primitives import MonstersPageClassification
from backend.utils.keys import get_openrouter_api_key

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent


def encode_image(image_path: Path) -> str:
    """Encode a local image file to a Base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def parse_page_number(image_path: Path) -> int:
    filename = image_path.stem  # Gets filename without extension (e.g., "page_0266")
    match = re.search(r"page_(\d+)", filename)
    if match:
        return int(match.group(1))
    raise ValueError(f"Could not parse page number from filename: {image_path.name}")


async def _process_single_image(
    client: AsyncOpenAI,
    image_path: Path,
    semaphore: asyncio.Semaphore,
    model: str,
    system_prompt: str,
    response_model: Type[BaseModel],
    max_retries: int,
) -> Tuple[int, BaseModel]:
    page_number = parse_page_number(image_path)

    async with semaphore:
        # Encode image once (outside retry loop)
        base64_image = encode_image(image_path)
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                ],
            },
        ]

        # Retry loop for ValidationError
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # Call LLM with structured output
                response = await client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_model,
                )

                parsed_result = response.choices[0].message.parsed
                if parsed_result is None:
                    raise ValueError("Failed to parse response from model")

                return (page_number, parsed_result)

            except ValidationError as e:
                last_error = e
                if attempt < max_retries:
                    print(
                        f"  ValidationError on page {page_number}, attempt {attempt + 1}/{max_retries + 1}, retrying..."
                    )
                    continue
                else:
                    # All retries exhausted, fall through to error handling
                    print(
                        f"  ValidationError on page {page_number} after {max_retries + 1} attempts, creating error result"
                    )
                    break
            except Exception as e:
                # Non-ValidationError exceptions go directly to error handling
                last_error = e
                break

        # Error handling (for ValidationError after retries or other exceptions)
        # last_error should always be set here since we only reach this point via exception paths
        if last_error is None:
            last_error = ValueError("Unknown error occurred during processing")

        print(f"  Error processing page {page_number}: {last_error}")
        # Create an error result using the response model
        # Try to create a minimal valid instance with error information
        error_dict = {}
        for field_name, field_info in response_model.model_fields.items():
            if field_info.is_required() and field_info.default is None:
                # For required fields without defaults, provide sensible defaults
                field_type_str = str(field_info.annotation).lower()
                if "list" in field_type_str or "List" in str(field_info.annotation):
                    error_dict[field_name] = []
                elif "str" in field_type_str or "string" in field_type_str:
                    error_dict[field_name] = (
                        f"Error during processing: {str(last_error)}"
                    )
                elif "int" in field_type_str or "float" in field_type_str:
                    error_dict[field_name] = 0
                elif "bool" in field_type_str:
                    error_dict[field_name] = False
                else:
                    # For other types, try to use default or None
                    error_dict[field_name] = (
                        field_info.default
                        if field_info.default is not None
                        else f"Error: {str(last_error)}"
                    )
            elif field_info.default is not None:
                error_dict[field_name] = field_info.default

        try:
            error_result = response_model(**error_dict)
        except Exception as create_error:
            # If we still can't create the model, try with minimal fields
            # This is a fallback - some models might still fail
            print(
                f"  Warning: Could not create error instance for page {page_number}: {create_error}"
            )
            # Re-raise the original error since we can't create a valid result
            raise last_error

        return (page_number, error_result)


async def process_images_async(
    book: str,
    model: str,
    system_prompt: str,
    response_model: Type[BaseModel],
    images_dir: Optional[Path] = None,
    max_concurrent: int = 10,
    max_retries: int = 3,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    page_filter: Optional[List[bool]] = None,
    page_names: Optional[List[str]] = None,
) -> List[Tuple[int, BaseModel]]:
    """
    Process page images asynchronously using LLM vision models with structured output.

    Args:
        book: Book type - "heroes" or "monsters"
        model: LLM model identifier (e.g., "openai/gpt-5-nano", "google/gemini-2.5-flash-lite")
        system_prompt: System prompt to pass to the LLM
        response_model: Pydantic model class for structured output
        images_dir: Optional explicit images directory path. If None, auto-detects from book.
        max_concurrent: Maximum number of concurrent requests (default: 10)
        max_retries: Maximum number of retries for ValidationError (default: 3)
        start_page: Optional start page number for range filtering (inclusive)
        end_page: Optional end page number for range filtering (inclusive)
        page_filter: Optional boolean list of length num_pages to filter pages by index
        page_names: Optional list of page filenames to process (e.g., ["page_0266.png"])

    Returns:
        List of tuples (page_number, parsed_model) for each processed page

    Raises:
        ValueError: If page_filter length doesn't match number of pages, or if no images found
    """
    # Determine images directory
    if images_dir is None:
        images_dir = REPO_ROOT / "backend" / "data" / book.lower() / "page_images"
    else:
        images_dir = Path(images_dir)

    if not images_dir.exists():
        raise ValueError(f"Images directory not found: {images_dir}")

    # Find all page images
    all_page_images = sorted(images_dir.glob("page_*.png"))
    if not all_page_images:
        raise ValueError(f"No page images found in {images_dir}")

    # Apply filtering
    # Note: page_filter must be applied first since it references indices in all_page_images
    filtered_images = all_page_images.copy()

    # Filter by boolean list (applied first since it references original list indices)
    if page_filter is not None:
        if len(page_filter) != len(all_page_images):
            raise ValueError(
                f"page_filter length ({len(page_filter)}) must match number of found pages ({len(all_page_images)})"
            )
        # Filter based on boolean list indices
        filtered_images = [
            img for i, img in enumerate(all_page_images) if page_filter[i]
        ]

    # Filter by page range
    if start_page is not None or end_page is not None:
        filtered_images = [
            img
            for img in filtered_images
            if (start_page is None or parse_page_number(img) >= start_page)
            and (end_page is None or parse_page_number(img) <= end_page)
        ]

    # Filter by page names
    if page_names is not None:
        # Normalize page_names - support both full filenames and just page numbers
        normalized_names = set()
        for name in page_names:
            # If it's a full filename, use as-is (case-insensitive)
            # If it's just a number or "page_XXXX", normalize it
            name_lower = name.lower()
            if name_lower.endswith(".png"):
                normalized_names.add(name_lower)
            elif name_lower.startswith("page_"):
                normalized_names.add(f"{name_lower}.png")
            else:
                # Assume it's a page number, try to match
                try:
                    page_num = int(name)
                    normalized_names.add(f"page_{page_num:04d}.png")
                except ValueError:
                    # Not a number, try as-is
                    normalized_names.add(f"{name_lower}.png")

        filtered_images = [
            img for img in filtered_images if img.name.lower() in normalized_names
        ]

    if not filtered_images:
        raise ValueError("No images match the specified filters")

    # Initialize OpenRouter client
    api_key = get_openrouter_api_key()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment or ~/.zshenv")

    client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    try:
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)

        # Process images concurrently with progress bar
        tasks = [
            _process_single_image(
                client,
                image_path,
                semaphore,
                model,
                system_prompt,
                response_model,
                max_retries,
            )
            for image_path in filtered_images
        ]

        # Use tqdm to show progress
        results = await tqdm.gather(
            *tasks, desc=f"Processing {book} pages", total=len(tasks)
        )

        return results

    finally:
        # Close the client
        await client.close()


if __name__ == "__main__":
    results = asyncio.run(
        process_images_async(
            book="monsters",
            # model="google/gemini-2.5-flash-lite",
            model="google/gemini-2.5-flash-preview-09-2025",
            system_prompt="""The following is a single page from the Monsters book. Count illustrations panels as contiguous artwork regions only. Analyze the page and extract the following information:
            1. Detailed descriptions of the image or images on the book page. do not include banners or section headers as they are not images. Pages contain two rows of text, but are still one page. Do NOT split a single panel into multiple images just because the subject spans across columns.
            2. Number of monster stat blocks present on the page. a monster stat block always starts with the name of the monster.
            3. names of monster stat blocks present on the page. if there are no monster stat blocks, this should be None.
            3. Whether there are partial monster stat blocks present on the page. this does not include malice features. 
            4. Whether the page includes "Malice Features", as specifically described at the top of the description.
            5. Whether the page includes multiple paragraphs of flavor text descriptions of monster lore.
            7. Whether the page includes a table
            8. whether the page includes a "Villain Action" section.
            8. Whether the page is only an image, with no other text or information.
            """,
            response_model=MonstersPageClassification,
            images_dir=Path("backend/data/monsters/page_images"),
            max_concurrent=25,
            max_retries=3,
            start_page=50,
            end_page=75,
        )
    )
    # Convert results to JSON-serializable format
    serializable_results = [
        {"page_number": page_num, "data": model.model_dump()}
        for page_num, model in results
    ]
    with open("monsters_page_classification.json", "w") as f:
        json.dump(serializable_results, f, indent=2)

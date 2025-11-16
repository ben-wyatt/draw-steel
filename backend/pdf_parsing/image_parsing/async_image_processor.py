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
from typing import List, Optional, Tuple, Type, Union

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel
from tqdm.asyncio import tqdm

from backend.utils.keys import get_openrouter_api_key

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent


class ModelError(BaseModel):
    """Error result when parsing fails after all retries."""

    page_number: int
    error_message: str


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
    response_model: Optional[Type[BaseModel]],
    max_retries: int,
) -> Tuple[int, Union[BaseModel, ModelError, str]]:
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

        # Retry loop
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if response_model is not None:
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
                else:
                    # Call LLM with plain text output
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                    )

                    text_content = response.choices[0].message.content
                    if text_content is None:
                        raise ValueError("Failed to get text content from model")

                    return (page_number, text_content)

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    print(
                        f"  Error on page {page_number}, attempt {attempt + 1}/{max_retries + 1}, retrying..."
                    )
                    continue
                else:
                    # All retries exhausted
                    print(
                        f"  Error on page {page_number} after {max_retries + 1} attempts: {last_error}"
                    )
                    break

        # Return ModelError if all retries failed
        return (
            page_number,
            ModelError(
                page_number=page_number,
                error_message=str(last_error) if last_error else "Unknown error",
            ),
        )


async def _process_image_best_of_n(
    client: AsyncOpenAI,
    image_path: Path,
    semaphore: asyncio.Semaphore,
    model: str,
    system_prompt: str,
    response_model: Optional[Type[BaseModel]],
    max_retries: int,
    best_of_n: int,
) -> Tuple[int, List[Union[BaseModel, ModelError, str]]]:
    """
    Process a single image n times concurrently and return all results.

    Args:
        client: AsyncOpenAI client instance
        image_path: Path to the image file
        semaphore: Semaphore to limit concurrent requests
        model: LLM model identifier
        system_prompt: System prompt to pass to the LLM
        response_model: Optional Pydantic model class for structured output. If None, returns plain text.
        max_retries: Maximum number of retries per call
        best_of_n: Number of times to process the image

    Returns:
        Tuple of (page_number, list of n results)
    """
    page_number = parse_page_number(image_path)

    # Create n concurrent tasks for the same image
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
        for _ in range(best_of_n)
    ]

    # Wait for all n calls to complete
    results = await asyncio.gather(*tasks)

    # Extract just the results (all should have same page_number)
    page_number, _ = results[0]  # Get page_number from first result
    models = [model for _, model in results]

    return (page_number, models)


async def process_images_async(
    book: str,
    model: str,
    system_prompt: str,
    response_model: Optional[Type[BaseModel]] = None,
    images_dir: Optional[Path] = None,
    max_concurrent: int = 10,
    max_retries: int = 3,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    page_filter: Optional[List[bool]] = None,
    page_names: Optional[List[str]] = None,
    best_of_n: int = 1,
) -> Union[
    List[Tuple[int, Union[BaseModel, ModelError, str]]],
    List[Tuple[int, List[Union[BaseModel, ModelError, str]]]],
]:
    """
    Process page images asynchronously using LLM vision models with structured or plain text output.

    Args:
        book: Book type - "heroes" or "monsters" or "delian_tomb"
        model: LLM model identifier (e.g., "google/gemini-2.5-flash-preview-09-2025" for solid and dependable, "google/gemini-2.5-flash-lite" for cheaper and higher volume)
        system_prompt: System prompt to pass to the LLM
        response_model: Optional Pydantic model class for structured output. If None, returns plain text strings.
        images_dir: Optional explicit images directory path. If None, auto-detects from book.
        max_concurrent: Maximum number of concurrent requests (default: 10)
        max_retries: Maximum number of retries for parsing errors per LLM call (default: 3)
        start_page: Optional start page number for range filtering (inclusive)
        end_page: Optional end page number for range filtering (inclusive)
        page_filter: Optional boolean list of length num_pages to filter pages by index
        page_names: Optional list of page filenames to process (e.g., ["page_0266.png"])
        best_of_n: Number of times to process each page (default: 1). When > 1, each page is
                   processed n times concurrently and all results are returned.

    Returns:
        When best_of_n == 1: List of tuples (page_number, parsed_model/plain_text or ModelError) for each processed page.
        When best_of_n > 1: List of tuples (page_number, list of n parsed_models/plain_text or ModelErrors) for each processed page.

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
        if best_of_n > 1:
            # Use best-of-n wrapper for each image
            tasks = [
                _process_image_best_of_n(
                    client,
                    image_path,
                    semaphore,
                    model,
                    system_prompt,
                    response_model,
                    max_retries,
                    best_of_n,
                )
                for image_path in filtered_images
            ]
        else:
            # Use direct single-image processing (backward compatible)
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
        # Note: tqdm.gather tracks high-level task completion (pages), not individual LLM calls
        # When best_of_n > 1, each task internally makes best_of_n LLM calls
        results = await tqdm.gather(
            *tasks, desc=f"Processing {book} pages", total=len(tasks)
        )

        return results

    finally:
        # Close the client
        await client.close()


def json_dump(
    results: Union[
        List[Tuple[int, Union[BaseModel, ModelError, str]]],
        List[Tuple[int, List[Union[BaseModel, ModelError, str]]]],
    ],
    file_path: Union[str, Path],
) -> None:
    """
    Serialize and save the results from process_images_async to a JSON file.

    Args:
        results: Results from process_images_async (handles both best_of_n==1 and best_of_n>1)
        file_path: Full path (str or Path) to the output JSON file, including filename
    """
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def serialize_item(item: Union[BaseModel, ModelError, str]) -> Union[dict, str]:
        """Serialize a single result item."""
        if isinstance(item, str):
            return item
        elif isinstance(item, (BaseModel, ModelError)):
            return item.model_dump()
        else:
            # Fallback for unexpected types
            return str(item)

    serializable_results = []
    for page_num, result in results:
        if isinstance(result, list):
            # best_of_n > 1: result is List[Union[BaseModel, ModelError, str]]
            serializable_results.append(
                {
                    "page_number": page_num,
                    "data": [serialize_item(item) for item in result],
                }
            )
        else:
            # best_of_n == 1: result is Union[BaseModel, ModelError, str]
            serializable_results.append(
                {"page_number": page_num, "data": serialize_item(result)}
            )

    with open(output_path, "w") as f:
        json.dump(serializable_results, f, indent=2)

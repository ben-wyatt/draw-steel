"""
Monster Image Classification Script

Analyzes monster page images and extracts:
- Number of monster stat blocks
- Presence of "Malice Features"
- Image descriptions
- Presence of paragraphs of flavor text
"""

import base64
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from backend.utils.keys import get_openrouter_api_key

load_dotenv()

client = OpenAI(
    api_key=get_openrouter_api_key(), base_url="https://openrouter.ai/api/v1"
)


class MonsterClassification(BaseModel):
    """Classification result for a monster page image."""

    number_of_monster_stat_blocks: int = Field(
        description="The number of monster stat blocks present on this page"
    )
    has_malice_features: bool = Field(
        description="Whether this page contains 'Malice Features' section"
    )
    image_descriptions: list[str] = Field(
        default_factory=list,
        description="Descriptions of any images, illustrations, or artwork present on the page",
    )
    has_flavor_text: bool = Field(
        description="Whether this page contains paragraphs of flavor text (narrative descriptions, lore, etc.)"
    )


def encode_image(image_path: Path) -> str:
    """Encode a local image file to a Base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def classify_monster_page(
    image_path: Path, model: str = "google/gemini-2.5-flash-lite"
) -> MonsterClassification:
    """
    Classify a monster page image and extract structured information.

    Args:
        image_path: Path to the image file
        model: Model to use for classification (default: google/gemini-2.5-flash-lite)

    Returns:
        MonsterClassification object with extracted information
    """
    image = encode_image(image_path)
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analyze this monster page image and extract the following information:
1. Count the number of monster stat blocks present on the page
2. Determine if there is a "Malice Features" section present
3. Describe any images, illustrations, or artwork visible on the page
4. Determine if there are paragraphs of flavor text (narrative descriptions, lore, setting information, etc.)

Be precise and only report what you can actually see in the image.""",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image}"},
                    },
                ],
            }
        ],
        response_format=MonsterClassification,
    )
    if response.choices[0].message.parsed:
        return response.choices[0].message.parsed
    else:
        raise ValueError("Failed to parse classification from image")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Classify monster page images and extract structured information"
    )
    parser.add_argument(
        "image_path",
        type=Path,
        help="Path to the image file to classify",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="google/gemini-2.5-flash-lite",
        help="Model to use for classification (default: google/gemini-2.5-flash-lite)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path (default: prints to stdout)",
    )

    args = parser.parse_args()

    result = classify_monster_page(args.image_path, model=args.model)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
        print(f"Classification saved to {args.output}")
    else:
        print(json.dumps(result.model_dump(), indent=2))

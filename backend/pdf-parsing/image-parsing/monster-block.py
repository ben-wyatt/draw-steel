import base64
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from backend.models.npcs import Monster
from backend.utils.keys import get_openrouter_api_key

load_dotenv()

client = OpenAI(
    api_key=get_openrouter_api_key(), base_url="https://openrouter.ai/api/v1"
)


def encode_image(image_path: Path) -> str:
    """Encode a local image file to a Base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def parse_monster_block(image_path: Path) -> Monster:
    image = encode_image(image_path)
    response = client.beta.chat.completions.parse(
        model="google/gemini-2.5-flash-lite",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Parse the monster block from the image."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image}"},
                    },
                ],
            }
        ],
        response_format=Monster,
    )
    if response.choices[0].message.parsed:
        return response.choices[0].message.parsed
    else:
        raise ValueError("Failed to parse monster block from image")


if __name__ == "__main__":
    image_path = Path("backend/data/monsters/abilities/other_images/predator_A.png")
    result = parse_monster_block(image_path)
    print(result)

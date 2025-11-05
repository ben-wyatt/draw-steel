import asyncio

from backend.models.npcs import Monster
from backend.pdf_parsing.image_parsing.async_image_processor import (
    json_dump,
    process_images_async,
)

if __name__ == "__main__":
    results = asyncio.run(
        process_images_async(
            book="monsters",
            model="google/gemini-2.5-flash-lite",
            system_prompt="Parse the monster block from the image. Never infer information that is not explicitly stated in the page.",
            response_model=Monster,
            start_page=100,
            end_page=100,
            best_of_n=2,
        )
    )
    json_dump(results, "single_monster_block_results.json")

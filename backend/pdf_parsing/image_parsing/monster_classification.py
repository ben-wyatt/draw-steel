import asyncio
from typing import Optional

from pydantic import BaseModel

from backend.pdf_parsing.image_parsing.async_image_processor import (
    json_dump,
    process_images_async,
)

SYSTEM_PROMPT = """The following is a single page from the Monsters book. Analyze the page and extract the following information:
1. Detailed descriptions of the artwork on the book page. do not include banners or section headers as they are not art. Pages contain two rows of text, but are still one page.
2. Number of monster stat blocks present on the page. a monster stat block always starts with the name of the monster.
3. names of monster stat blocks present on the page. if there are no monster stat blocks, this should be None.
3. Whether there are partial monster stat blocks present on the page. this does not include malice features. 
4. Whether the page includes "Malice Features", as specifically described at the top of the description.
5. Whether the page includes multiple paragraphs of flavor text descriptions of monster lore.
7. Whether the page includes a table.
8. whether the page includes a "Villain Action" section.
8. Whether the page is only a large piece of artwork.
"""


class MonstersPageClassification(BaseModel):
    detailed_image_descriptions: list[str]
    number_of_monster_stat_blocks: int
    names_of_monster_stat_blocks: Optional[list[str]]
    has_partial_monster_stat_blocks: bool
    includes_malice_features: bool
    includes_flavor_text: bool
    includes_table: bool
    includes_villain_action: bool
    page_is_only_image: bool


if __name__ == "__main__":
    results = asyncio.run(
        process_images_async(
            book="monsters",
            model="google/gemini-2.5-flash-preview-09-2025",
            system_prompt=SYSTEM_PROMPT,
            response_model=MonstersPageClassification,
            start_page=100,
            end_page=101,
            best_of_n=2,
        )
    )
    json_dump(results, "monster_classification_results.json")

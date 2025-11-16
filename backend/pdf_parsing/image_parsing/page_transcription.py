import asyncio

from backend.pdf_parsing.image_parsing.async_image_processor import (
    json_dump,
    process_images_async,
)

TRANSCRIPTION_SYSTEM_PROMPT = """Extract all text from this TTRPG book page image and transcribe it to markdown format.

Formatting requirements:
- Use markdown headers
- Convert tables to markdown table syntax with proper alignment
- Use - for bulleted lists
- Use **bold** and *italic* where appropriate
- Preserve paragraph structure with blank lines between paragraphs

Content extraction:
- Extract all main body text from the page
- Convert headings to appropriate markdown header levels
- Convert tables to markdown table format with proper column alignment
- Preserve the logical structure and hierarchy of content
- Ignore footers and vertical chapter tabs

What to SKIP (do NOT transcribe in full):
- Ability blocks: Skip entire ability blocks that contain abilities. These typically include:
  * An ability name like "Pillar of Holy Fire"
  * A quote or flavor text line (e.g., "Move or die, folks.")
  * Keywords like "Charge, Melee, Strike, Weapon"
  * Range and target information like "Melee 1" and "One creature or object"
- Monster stat blocks. These include:
  * A monster name like "Lich"
  * statistics like Stamina and Speed
  * a series of monster named monster abilities like "Corpse Rot" and "Necrotic Aura"
- Item blocks: Skip treasure reward descriptions.
- Power roll tables: a small table within an ability that shows outcomes for <=11, 12-16, and 17+
- Ignore descriptions of images. If the page contains only an image, respond with "!!Image only!!".

When skipping structured content, insert a structured note in the format: [[Name|type]]
- Replace "Name" with the actual name of the ability, monster, or item
- Replace "type" with one of: "ability", "monster_block", "item" or "other"
- Examples: [[Issue Order|ability]], [[Goblin Warrior|monster_block]], [[Sword of Truth|item]]

What to KEEP (DO transcribe):
- Narrative descriptions and flavor text
- Benefit and Drawback sections (these are narrative descriptions, not structured stats)
- Simple rule explanations and descriptions
- Headings and subheadings for narrative content
- Lists containing descriptive content
- Tables that are NOT ability/stat block tables (e.g., skill lists, general reference tables)
"""

if __name__ == "__main__":
    results = asyncio.run(
        process_images_async(
            book="delian_tomb",
            model="google/gemini-2.5-flash-preview-09-2025",
            system_prompt=TRANSCRIPTION_SYSTEM_PROMPT,
            best_of_n=1,
            # start_page=110,
            # end_page=130,
        )
    )
    json_dump(results, "backend/data/delian_tomb/page_transcription.json")

import json
from pathlib import Path

from agents import Agent, function_tool

from backend.database import Database
from backend.utils.agent_models import GEMINI_FLASH_LITE_MODEL

DRAW_STEEL_OVERVIEW = Path("backend/agents/prompts/overview_prompt.md").read_text()

DRAW_STEEL_EXPERT_PROMPT = Path(
    "backend/agents/prompts/draw_steel_expert_prompt.md"
).read_text()

DATABASE = Database(collection_name="DelianTombV1")


@function_tool
async def search_text(query: str) -> str:
    """Use combination of semantic and keyword search to find relevant information about the game and adventure.
    Args:
        query: The query to search for.
    Returns:
        A list of results from the database.
    """
    results = DATABASE.search(query)
    return str(json.dumps(results))


draw_steel_expert = Agent(
    name="Draw Steel Expert",
    instructions=DRAW_STEEL_EXPERT_PROMPT,
    tools=[search_text],
    model=GEMINI_FLASH_LITE_MODEL,
)

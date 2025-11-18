import json
from pathlib import Path

from agents import Agent, function_tool
from agents.extensions.models.litellm_model import LitellmModel

from backend.database import Database
from backend.utils.agent_models import GEMINI_FLASH_LITE_MODEL

DRAW_STEEL_OVERVIEW = Path("backend/agents/prompts/overview_prompt.md").read_text()

DRAW_STEEL_EXPERT_PROMPT = Path(
    "backend/agents/prompts/draw_steel_expert_prompt.md"
).read_text()


def create_draw_steel_expert(
    collection_name: str, model: LitellmModel = GEMINI_FLASH_LITE_MODEL
) -> Agent:
    """
    Create a Draw Steel Expert agent with a specific collection.

    Args:
        collection_name: Name of the database collection to use
        model: The model to use for the agent (default: GEMINI_FLASH_LITE_MODEL)

    Returns:
        Configured Agent instance
    """
    database = Database(collection_name=collection_name)

    @function_tool
    async def search_text(query: str) -> str:
        """Use combination of semantic and keyword search to find relevant information about the game and adventure.
        Args:
            query: The query to search for.
        Returns:
            A list of results from the database.
        """
        results = database.search(query, limit=5)
        return str(json.dumps(results))

    return Agent(
        name="Draw Steel Expert",
        instructions=DRAW_STEEL_EXPERT_PROMPT,
        tools=[search_text],
        model=model,
    )

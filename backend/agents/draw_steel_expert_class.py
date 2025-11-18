import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agents import Agent, Runner, RunResult, function_tool
from agents.extensions.models.litellm_model import LitellmModel

from backend.database import Database
from backend.utils.agent_models import GEMINI_FLASH_LITE_MODEL

DRAW_STEEL_EXPERT_PROMPT = Path(
    "backend/agents/prompts/draw_steel_expert_prompt.md"
).read_text()


@dataclass
class RetrievalConfig:
    collection_name: str
    model: LitellmModel = GEMINI_FLASH_LITE_MODEL
    top_k: int = 5
    hybrid_alpha: float = 0.5
    # surrounding_chunks: int = 0
    max_calls_per_query: int = 10


class DrawSteelExpert:
    def __init__(self, retrieval_config: RetrievalConfig):
        self.retrieval_config = retrieval_config

        # lazy init
        self._agent: Optional[Agent] = None
        self._database: Optional[Database] = None

    @property
    def database(self) -> Database:
        if self._database is None:
            self._database = Database(
                collection_name=self.retrieval_config.collection_name
            )
        return self._database

    def _create_agent(self) -> Agent:
        @function_tool
        async def search_text(query: str) -> str:
            """Search for relevant information about the game and adventure.
            Args:
                query: The query to search for.
            Returns:
                A list of results from the database.
            """
            results = self.database.search(
                query,
                limit=self.retrieval_config.top_k,
                alpha=self.retrieval_config.hybrid_alpha,
            )
            return str(json.dumps(results))

        agent = Agent(
            name="Draw Steel Expert",
            instructions=DRAW_STEEL_EXPERT_PROMPT,
            tools=[search_text],
            model=self.retrieval_config.model,
        )
        return agent

    @property
    def agent(self) -> Agent:
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    async def run_agent(self, query: str) -> RunResult:
        return await Runner.run(self.agent, query)

    def close(self):
        if self._database is not None:
            self._database.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


"""
TODO: don't repeat the same chunk in a chat history.
 - unique chunk id: `source_book:page:chunk_index`
 - each chat history should have set of chunks and ids that are excluded from retrieval
 - make object-oriented

should use agents sdk primitives: tool, agent, session, handoff


Functionality organized:
- RetrievalConfig: agent parameters for search
- initialization: create agent, create tool
- chat
- update retrieval configs
- session management
- streaming_chat

"""

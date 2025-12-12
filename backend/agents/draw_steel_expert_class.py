import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, cast
from uuid import uuid4

from agents import Agent, Runner, RunResult, Session, SQLiteSession, function_tool
from agents.extensions.models.litellm_model import LitellmModel
from openai.types.responses import ResponseFunctionToolCall

from backend.database import Database
from backend.utils.agent_models import GEMINI_FLASH_LITE_MODEL

DRAW_STEEL_EXPERT_PROMPT = Path(
    "backend/agents/prompts/draw_steel_expert_prompt.md"
).read_text()


@dataclass
class StreamEvent:
    """Event yielded during streaming agent execution."""

    type: Literal["text_delta", "tool_call", "tool_result"]
    data: str  # text content, tool name, or result summary
    metadata: dict = field(default_factory=dict)  # tool args, chunk ids, etc.


@dataclass
class RetrievalConfig:
    collection_name: str
    model: LitellmModel
    top_k: int = 5
    hybrid_alpha: float = 0.5
    # surrounding_chunks: int = 0
    max_calls_per_query: int = 10


class DrawSteelExpert:
    def __init__(
        self,
        collection_name: str,
        session_id: Optional[str] = None,
        model: LitellmModel = GEMINI_FLASH_LITE_MODEL,
    ):
        self.retrieval_config = RetrievalConfig(
            collection_name=collection_name, model=model
        )

        self._agent: Optional[Agent] = None
        self._database: Optional[Database] = None

        self.sessions: Dict[str, Session] = {}

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

    async def run_agent(
        self, query: str, session_id: Optional[str] = None
    ) -> RunResult:
        if session_id:
            if session_id not in self.sessions:
                self.create_session(session_id)
            session = self.sessions[session_id]
        else:
            session_id = self.create_session()
            session = self.sessions[session_id]
        print(f"Using session id: {session_id}")
        return await Runner.run(self.agent, query, session=session)

    async def run_agent_streamed(
        self, query: str, session_id: Optional[str] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """Run the agent with streaming, yielding StreamEvent objects."""
        if session_id:
            if session_id not in self.sessions:
                self.create_session(session_id)
            session = self.sessions[session_id]
        else:
            session_id = self.create_session()
            session = self.sessions[session_id]

        result = Runner.run_streamed(self.agent, query, session=session)

        async for event in result.stream_events():
            if event.type == "raw_response_event":
                if event.data.type == "response.output_text.delta":
                    yield StreamEvent(type="text_delta", data=event.data.delta)

            elif event.type == "run_item_stream_event":
                item = event.item

                if item.type == "tool_call_item":
                    raw_item = item.raw_item
                    if isinstance(raw_item, ResponseFunctionToolCall):
                        args = json.loads(raw_item.arguments)
                        tool_call_id = (
                            getattr(raw_item, "call_id", None)
                            or getattr(raw_item, "id", None)
                            or None
                        )
                        yield StreamEvent(
                            type="tool_call",
                            data=raw_item.name,
                            metadata={
                                "arguments": args,
                                "tool_call_id": tool_call_id,
                            },
                        )

                elif item.type == "tool_call_output_item":
                    raw_item = item.raw_item
                    output = raw_item.get("output", "")
                    if isinstance(output, str):
                        tool_call_id = None
                        if isinstance(raw_item, dict):
                            raw_item_dict = cast(dict[str, Any], raw_item)
                            tool_call_id = (
                                raw_item_dict.get("tool_call_id")
                                or raw_item_dict.get("call_id")
                                or raw_item_dict.get("id")
                            )
                        try:
                            output_json = json.loads(output)
                            chunk_ids = [
                                f"{c['source_book']}:{c['page']}:{c['chunk_index']}"
                                for c in output_json
                            ]
                            yield StreamEvent(
                                type="tool_result",
                                data=f"Retrieved {len(chunk_ids)} chunks",
                                metadata={
                                    "tool_call_id": tool_call_id,
                                    "chunk_ids": chunk_ids,
                                    "results": output_json,
                                },
                            )
                        except (json.JSONDecodeError, KeyError):
                            yield StreamEvent(
                                type="tool_result",
                                data="Retrieved results",
                                metadata={"tool_call_id": tool_call_id},
                            )

    def update_retrieval_config(self, retrieval_config: RetrievalConfig):
        self.retrieval_config = retrieval_config
        if self._agent is not None:
            self._agent = self._create_agent()
        if self._database is not None:
            self._database = Database(
                collection_name=self.retrieval_config.collection_name
            )

    def create_session(self, session_id: Optional[str] = None) -> str:
        if session_id is None:
            session_id = str(uuid4())
        if session_id in self.sessions:
            raise ValueError(f"Session with id {session_id} already exists")
        self.sessions[session_id] = SQLiteSession(session_id=session_id)
        return session_id

    def list_sessions(self) -> List[str]:
        return list(self.sessions.keys())

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
- RetrievalConfig: agent parameters for search X
- initialization: create agent, create tool X
- chat X
- update retrieval configs X
- session management X
- streaming_chat
- adjacent chunks

TODO: does it make sense to return the Session object instead of the session id?
"""

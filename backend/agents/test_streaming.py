import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import List

from agents import Agent, Runner
from openai.types.responses import ResponseFunctionToolCall

from backend.agents.draw_steel_expert import create_draw_steel_expert


@dataclass
class StreamStats:
    """Track statistics during streaming."""

    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    # Token streaming stats
    delta_count: int = 0
    total_chars: int = 0

    # Tool call stats
    tool_calls: List[dict] = field(default_factory=list)
    retrieved_chunks: List[str] = field(default_factory=list)

    # Event counts
    event_counts: dict = field(default_factory=dict)

    def record_event(self, event_type: str):
        """Record an event occurrence."""
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

    def record_delta(self, text: str):
        """Record a text delta."""
        self.delta_count += 1
        self.total_chars += len(text)

    def record_tool_call(self, name: str, arguments: str):
        """Record a tool call."""
        self.tool_calls.append({"name": name, "arguments": arguments})

    def record_chunks(self, chunk_ids: List[str]):
        """Record retrieved chunks."""
        self.retrieved_chunks.extend(chunk_ids)

    def finalize(self):
        """Mark the stream as complete."""
        self.end_time = time.time()

    @property
    def duration(self) -> float:
        """Get total duration in seconds."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def chars_per_second(self) -> float:
        """Calculate characters per second."""
        duration = self.duration
        return self.total_chars / duration if duration > 0 else 0

    def print_summary(self):
        """Print a formatted summary of statistics."""
        print("\n" + "=" * 70)
        print("STREAM STATISTICS")
        print("=" * 70)

        print(f"\n⏱️  Duration: {self.duration:.2f}s")
        print(f"📊 Text Updates: {self.delta_count}")
        print(f"📝 Total Characters: {self.total_chars}")
        print(f"⚡ Speed: {self.chars_per_second:.1f} chars/sec")

        if self.tool_calls:
            print(f"\n🔧 Tool Calls: {len(self.tool_calls)}")
            for i, tool_call in enumerate(self.tool_calls, 1):
                print(f"   {i}. {tool_call['name']}")
                args = json.loads(tool_call["arguments"])
                for key, value in args.items():
                    print(f"      {key}: {value}")

        if self.retrieved_chunks:
            print(f"\n📚 Retrieved Chunks: {len(self.retrieved_chunks)}")
            for chunk_id in self.retrieved_chunks:
                print(f"   • {chunk_id}")

        if self.event_counts:
            print("\n📡 Event Counts:")
            for event_type, count in sorted(self.event_counts.items()):
                print(f"   {event_type}: {count}")

        print("=" * 70 + "\n")


def get_chunk_ids_from_search_text_output(output: str) -> List[str]:
    """Extract chunk IDs from search_text tool output."""
    output_json = json.loads(output)
    chunk_ids = [
        f"{item['source_book']}:{item['page']}:{item['chunk_index']}"
        for item in output_json
    ]
    return chunk_ids


async def main():
    """Run a streaming query and display clean output with statistics."""
    agent: Agent = create_draw_steel_expert("DelianTombV1")
    user_query = "Where is Violet being kept?"

    # Initialize statistics tracker
    stats = StreamStats()

    # Display query header
    print("\n" + "=" * 70)
    print("DRAW STEEL EXPERT - STREAMING TEST")
    print("=" * 70)
    print(f"\n❓ Query: {user_query}\n")
    print("🔄 Starting stream...\n")

    # Run streamed query
    result = Runner.run_streamed(agent, input=user_query)
    streaming_response = False

    async for event in result.stream_events():
        stats.record_event(event.type)

        if event.type == "raw_response_event":
            if event.data.type == "response.content_part.added":
                # Start of response streaming
                streaming_response = True
                print("💬 Response: ", end="", flush=True)

            elif event.data.type == "response.output_text.delta":
                # Stream each text delta
                delta_text = event.data.delta
                stats.record_delta(delta_text)
                print(delta_text, end="", flush=True)

        elif event.type == "run_item_stream_event":
            item = event.item

            if item.type == "tool_call_item":
                raw_item = item.raw_item
                if isinstance(raw_item, ResponseFunctionToolCall):
                    print(f"\n🔧 Calling tool: {raw_item.name}")
                    args = json.loads(raw_item.arguments)
                    print(f'   └─ query: "{args.get("query", "N/A")}"')
                    stats.record_tool_call(raw_item.name, raw_item.arguments)

            elif item.type == "tool_call_output_item":
                raw_item = item.raw_item
                output = raw_item["output"]

                if isinstance(output, str):
                    chunk_ids = get_chunk_ids_from_search_text_output(output)
                    print(f"   └─ Retrieved {len(chunk_ids)} chunks")
                    stats.record_chunks(chunk_ids)

    # Ensure we end the line after streaming
    if streaming_response:
        print("\n")

    # Finalize and print statistics
    stats.finalize()
    stats.print_summary()


if __name__ == "__main__":
    asyncio.run(main())

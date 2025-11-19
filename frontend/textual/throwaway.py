import asyncio
from typing import Any, AsyncIterator, Dict, List

Message = Dict[str, Any]


async def stream_from_history(
    history: List[Message],
    delay: float = 0.03,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Simulate OpenAI-style streaming over the *last* assistant message
    in a chat history of JSON objects.

    history: [
      {"role": "user", "content": "Hi"},
      {"role": "assistant", "content": "Hello there!"}
    ]
    """
    # Grab the last assistant message (or just the last message)
    last = history[-1]
    role = last.get("role", "assistant")
    text = last.get("content", "")

    # Split into tiny "chunks" (characters, words, tokens… your choice)
    for char in text:
        await asyncio.sleep(delay)

        # Shape the event however you like; this roughly mimics a "delta"
        yield {
            "type": "response.delta",
            "delta": {
                "role": role,
                "content": char,
            },
        }

    # Final "done" event, similar to response.completed
    yield {
        "type": "response.completed",
        "response": {
            "role": role,
            "content": text,
        },
    }


# Example of consuming it
async def main():
    chat_history = [
        {"role": "user", "content": "Tell me a joke."},
        {
            "role": "assistant",
            "content": "Why did the chicken join a band?  Because it had drumsticks!",
        },
    ]

    async for event in stream_from_history(chat_history):
        if event["type"] == "response.delta":
            print(event["delta"]["content"], end="", flush=True)
        elif event["type"] == "response.completed":
            print("\n\n[stream completed]")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from typing import Any, AsyncIterator

SAMPLE_CHAT_HISTORY_1 = [
    {"role": "user", "content": "What is Draw Steel?"},
    {
        "role": "assistant",
        "function_call": {"name": "search_text", "arguments": {"query": "Draw Steel"}},
    },
    {
        "role": "tool",
        "content": [
            {
                "source_book": "Heroes",
                "page": 1,
                "chunk_index": 0,
                "text": """This is a game about 'ghting monsters. About larger-than-life, extraordinary heroes plunging into battle against terrifying,monstrous enemies. That covers a lot! So let’s get specific and talk about what this game is,and what it is not.)This game will absolutely feature dungeons. Ancient undergroundcomplexes filled with ravenous undead or creeping oozes. But it isn’ta dungeon crawler. It’s not about “clearing rooms.” It’s not a survivalhorror game where you must track light and food and the weight ofevery object you carry.)You can 'ght monsters in a dungeon, but the game is not aboutdungeons. Lots of games focus on that gameplay and do it really well!Like Shadowdark.)TacticalIt’s not a wilderness exploration game, aka a hex crawl. It’s not aboutsurviving in extreme weather, getting lost, or trying to navigate yourway back to safety.)""",
            }
        ],
    },
    {
        "role": "assistant",
        "content": "Draw Steel is a Tactical, Heroic, Cinematic, Fantasy Tabletop Roleplaying Game.",
    },
]

SAMPLE_CHAT_HISTORIES_LIST = [SAMPLE_CHAT_HISTORY_1]


async def async_simulate_chat(
    user_message: dict[str, Any],
    delay: float = 1.0,
) -> AsyncIterator[dict[str, Any]]:
    for chat_history in SAMPLE_CHAT_HISTORIES_LIST:
        if (
            chat_history[0]["role"] == "user"
            and chat_history[0]["content"] == user_message["content"]
        ):
            for item in chat_history[1:]:
                await asyncio.sleep(delay)
                yield item
            break
    else:
        raise ValueError(f"User message not found in chat history: {user_message}")


if __name__ == "__main__":
    """
    Test the async_get_chat_history function.
    """

    async def main():
        first_item = SAMPLE_CHAT_HISTORY_1[0]
        print(first_item)
        async for item in async_simulate_chat(first_item):
            print(item)

    asyncio.run(main())

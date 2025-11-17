import asyncio

from agents import Runner

from backend.agents.draw_steel_expert import draw_steel_expert


async def main():
    result = await Runner.run(draw_steel_expert, "Where is Violet?")
    print(result)


def chat():
    pass


if __name__ == "__main__":
    asyncio.run(main())


"""
TODO: clean up the print statements
TODO: figure out tracing
TODO: test agent with a few other questions
TODO: make into proper chat
TODO: add in cli support like ugly_chat.py
"""

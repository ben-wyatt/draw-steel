import asyncio
import json
from typing import List

from agents import Agent, Runner
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputText

from backend.agents.draw_steel_expert import create_draw_steel_expert


def get_chunk_ids_from_search_text_output(output: str) -> List[str]:
    """should be list[dict] with keys: text, page, source_book, section, chunk_index, score"""
    output_json = json.loads(output)
    chunk_ids = [
        f"{item['source_book']}:{item['page']}:{item['chunk_index']}"
        for item in output_json
    ]
    return chunk_ids


async def main():
    agent: Agent = create_draw_steel_expert("DelianTombV1")
    user_query = "Where is Violet being kept?"
    print("\n\n--Starting stream--\n\n")
    print(f"User query: {user_query}\n")
    result = Runner.run_streamed(agent, input=user_query)
    async for event in result.stream_events():
        if event.type == "raw_response_event":
            # continue unless type='response.content_part.added'
            if event.data.type == "response.content_part.added":
                part_added_event = event.data
                print("response.content_part.added message stream started")
                if isinstance(part_added_event.part, ResponseOutputText):
                    print(f"  text: {part_added_event.part.text}")
                else:
                    print(f"  unknown part type: {type(part_added_event.part)}")
                print()

            elif event.data.type == "response.output_text.delta":
                delta_event = event.data
                print(f"  delta sequence_number: {delta_event.sequence_number}")
                print(f"  delta text: {delta_event.delta}\n")

            else:
                continue

        elif event.type == "run_item_stream_event":
            item = event.item
            if item.type == "tool_call_item":
                # print details on tool call
                raw_item = item.raw_item
                # can't figure out better way to type this than isinstance
                if isinstance(raw_item, ResponseFunctionToolCall):
                    print(f"tool call name: {raw_item.name}")
                    print(f"tool call arguments: {raw_item.arguments}")
                else:
                    print(f"unidentified tool call item type: {type(raw_item)}")
            elif item.type == "tool_call_output_item":
                # print details on retrieval item
                raw_item = item.raw_item
                # should be a dictionary
                output = raw_item["output"]
                if isinstance(output, str):
                    chunk_ids = get_chunk_ids_from_search_text_output(output)
                    print("chunk ids:")
                    for chunk_id in chunk_ids:
                        print(f"  {chunk_id}")
                else:
                    print(f"unidentified tool call output type: {type(output)}")
            else:
                print(f"unknown item type: {item.type}")
        else:
            print(f"should be agent_updated_stream_event: {event.type}")

    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())


"""
Reading the streamed events:
first: agent_updated_stream_event
 - defines a new agent, with tools, instructions, model gen details
then: raw_response_event
 - pydanticserializationunexpectedvalue error: two, one for message, one for streamingchoices
then: raw_response_event
 - beginning of the tool call generation
then: raw_response_event
 - end of the tool call generation
then: tool_call_item
 - with specified tool_use_behavior 'run_llm_again' to handle what happens after tool call
then: raw_response_event
 - whatever
then: run_item_stream_event
 - the output of the tool call
then: more raw_response_events
then: message_output_item
 - the full message


conclusion:
 - if you want to do token streaming then you need to handle the raw_response_events
 - if you're fine with just the final message then you can ignore the raw_response_events
what if we wanted to handle token streaming *only when its a final message*?
 - within the raw_response_event, we can check type='response.content_part.added' to begin token stream
 - then parse each subsequent raw_response_event type='repsonse.output_text.delta'

"""

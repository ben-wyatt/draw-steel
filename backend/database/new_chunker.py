"""
Use my own brain to figure out the chunking.

first, figure out chunk size distribution if we just split by page.
"""

import json
import uuid
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Chunk:
    """Represents a chunk of text with metadata."""

    text: str
    page: Optional[int]
    source_book: str
    chunk_id: str


#######
# chunking using JSON dump
def chunk_json_dump(
    json_dump: List[dict], source_book: str, min_char_len: int = 1000
) -> List[Chunk]:
    """
    Converts OCR'ed page transcriptions into chunks.
    1. Remove pages that are full images.
    2. Split by header
    3. Concatenate smaller chunks until char_len > min_char_len
    """
    # check if chunk is just !!Image only!!, if so remove it
    json_dump = [page for page in json_dump if page["data"] != "!!Image only!!"]

    # split by header
    filtered_dump = []
    current_chunk = ""
    current_page = json_dump[0]["page_number"]
    for page_transcription in json_dump:
        lines = page_transcription["data"].split("\n")
        for line in lines:
            if line.startswith("#"):
                filtered_dump.append(
                    {"page_number": current_page, "data": current_chunk}
                )
                current_chunk = ""
                current_page = page_transcription["page_number"]
            current_chunk += line + "\n"
        filtered_dump.append({"page_number": current_page, "data": current_chunk})

    # concatenate smaller chunks
    i = 0
    while i < len(filtered_dump) - 1:
        if len(filtered_dump[i]["data"]) < min_char_len:
            filtered_dump[i]["data"] += filtered_dump[i + 1]["data"]
            filtered_dump.pop(i + 1)
        else:
            i += 1

    # convert to Chunk objects
    chunks = [
        Chunk(
            text=page["data"],
            page=page["page_number"],
            source_book=source_book,
            chunk_id=str(uuid.uuid4()),
        )
        for i, page in enumerate(filtered_dump)
    ]

    return chunks


if __name__ == "__main__":
    # new gemini flash preview transcription
    data_dump = json.load(
        open(
            "backend/data/heroes/natural_language/heroes_transcription_flash_preview.json"
        )
    )
    # chunks = [page["data"] for page in data_dump]
    # print("Chunking by header...")
    # chunks = header_aggregate(chunks)
    # analyze_chunks(chunks)
    # loop_through_sequential_chunks(chunks)
    chunks = chunk_json_dump(data_dump, source_book="heroes")
    print(chunks[0])


"""
TODO:
 - extract ability metadata: [[Name|type]] regex match, page number
 - remove !!Image only!! chunks

"""

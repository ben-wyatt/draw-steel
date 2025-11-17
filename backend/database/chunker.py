"""
Use my own brain to figure out the chunking.

"""

import json
import re
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
    ability_blocks: List[str]
    monster_blocks: List[str]
    item_blocks: List[str]
    other_blocks: List[str]
    section: Optional[List[str]] = None
    chunk_index: int = 0
    token_count: int = 0  # estimated at 4 char/tok


def construct_chunk(
    text: str,
    page: int,
    source_book: str,
    section: Optional[List[str]] = None,
    chunk_index: int = 0,
) -> Chunk:
    """
    Construct a Chunk from text with metadata.

    Args:
        text: The chunk text content
        page: Page number
        source_book: Source book identifier
        section: Optional list of section headers (hierarchy)
        chunk_index: Index of chunk within page
    """
    matches = re.findall(r"\[\[([^|\]]+)\|([^\]]+)\]\]", text)
    ability_blocks = [match[0] for match in matches if match[1].lower() == "ability"]
    monster_blocks = [
        match[0] for match in matches if match[1].lower() == "monster_block"
    ]
    item_blocks = [match[0] for match in matches if match[1].lower() == "item"]
    other_blocks = [
        match[0]
        for match in matches
        if match[1].lower() != "ability"
        and match[1].lower() != "monster_block"
        and match[1].lower() != "item"
    ]

    # Estimate token count: roughly 4 characters per token
    token_count = len(text) // 4

    # Extract section headers from markdown headers in text
    if section is None:
        section = []
        lines = text.split("\n")
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("#"):
                # Count # to determine header level and extract text
                level = 0
                for char in line_stripped:
                    if char == "#":
                        level += 1
                    else:
                        break
                header_text = line_stripped[level:].strip()
                if header_text:
                    # Update section to reflect current level
                    section = section[: level - 1] + [header_text]

    chunk_id = str(uuid.uuid4())
    chunk = Chunk(
        text=text,
        page=page,
        source_book=source_book,
        chunk_id=chunk_id,
        ability_blocks=ability_blocks,
        monster_blocks=monster_blocks,
        item_blocks=item_blocks,
        other_blocks=other_blocks,
        section=section,
        chunk_index=chunk_index,
        token_count=token_count,
    )
    return chunk


def chunk_json_dump(
    json_dump: List[dict], source_book: str, min_char_len: int = 1000
) -> List[Chunk]:
    """
    Converts JSON dump of page transcriptions into chunks.
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
    chunks = []
    chunk_indices_by_page = {}
    for page_data in filtered_dump:
        page_num = page_data["page_number"]
        if page_num not in chunk_indices_by_page:
            chunk_indices_by_page[page_num] = 0
        else:
            chunk_indices_by_page[page_num] += 1

        chunk = construct_chunk(
            text=page_data["data"],
            page=page_num,
            source_book=source_book,
            chunk_index=chunk_indices_by_page[page_num],
        )
        chunks.append(chunk)

    return chunks


if __name__ == "__main__":
    data_dump = json.load(
        open(
            "backend/data/heroes/natural_language/heroes_transcription_flash_preview.json"
        )
    )
    chunks = chunk_json_dump(data_dump, source_book="heroes", min_char_len=2000)
    from backend.database.chunk_inspector import analyze_chunks

    analyze_chunks(chunks)


"""
TODO:
 - extract ability metadata: [[Name|type]] regex match, page number

"""

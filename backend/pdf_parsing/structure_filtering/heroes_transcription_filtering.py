"""
looks through a best-of-n transcription and chooses the transcript that is shortest.
"""

import json


def filter_transcription_by_shortest(json_data):
    """
    keeping only the shortest transcript for each page.
    """
    filtered = []

    for page in json_data:
        transcripts: list[str] = page["data"]
        shortest: str = min(transcripts, key=len)

        filtered_page = {
            "page_number": page["page_number"],
            "data": [shortest],  # Keep as list to maintain structure
        }
        filtered.append(filtered_page)

    return filtered


if __name__ == "__main__":
    data_dump = json.load(
        open(
            "backend/data/heroes/natural_language/heroes_transcription_best_of_n_3.json"
        )
    )
    filtered_data_dump = filter_transcription_by_shortest(data_dump)
    with open(
        "backend/data/heroes/natural_language/heroes_transcription_best_of_n_3_filtered.json",
        "w",
    ) as f:
        json.dump(filtered_data_dump, f, indent=2)

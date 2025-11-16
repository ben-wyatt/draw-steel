# Image Parsing

This directory contains tools for parsing the PDFs images using vision models.

The core LLM logic is abstracted into `async_image_processor.py`. Specify book, model, prompt, response format:

```python
results = asyncio.run(process_images_async(
    book="heroes",
    model="google/gemini-2.5-flash-lite",
    system_prompt="Transcribe the page image to markdown format. Never infer information that is not explicitly stated in the page.",
    response_model=PydanticBaseModel,
    best_of_n=2,
    start_page=110,
    end_page=115,
))
json_dump(results, "transcription_test.json")
```

Dump the results using the supplied `json_dump` file. Entries look like:

```json
[
  {
    "page_number": 1,
    "data": "TACTICAL HEROIC CINEMATIC FANTASY\n\n# DRAW STEEL\nBOOK ONE\n\n# HEROES\n\nMCDM"
  },
  // and for structured output:
  {   
    "page_number": 100,
    "data": [
        { // parsed structured formats
        "detailed_image_descriptions": [
            "A stylized, ornate diamond shape with decorative flourishes is centered below the ",
            "The top of the page features a vertical dark grey bar with the word DRAGONS written in white capital letters, running from top to bottom along the right edge.",
        ],
        "number_of_monster_stat_blocks": 0,
        "names_of_monster_stat_blocks": null,
        "has_partial_monster_stat_blocks": false,
        "includes_malice_features": false,
        },
    ]
  }
]
```

LLMs are good at extracting something *when it is there*, but they also have lots of false positives.

For that reason, I've also implemented `best_of_n` here, which will run each page image `n` times. From there you should be able to use some parsing heuristics to get better overall performance.

## monster_classification

identify what is on each page of Monsters PDF.  So that we can do more targeted best-of-n analysis individually later.

## page_transcription

transcribe pages 

## heroes_classification

not implemented



## random idea

ok so I have this core tool that I can do stuff with: `async_image_generator`. I specify:
- book to extract from
- model to use (flash-preview is great default, flash-lite for cheap tests)
- pages to act on (start/end, page_filter, page_names)
- natural language system prompt to dictate what to look for
- optional pydantic model to enforce specific format
- best_of_n if you need multiple indepedent analyses of each page

And then I specify configurations using the other files in this directory

That gets pretty busy after a while. and unclear

what if there is a better generic interface here?

like I have to make a code change just to 

the core idea is that I want an easy way to save and edit specific extraction operations like transcription, image analysis, ability extraction.


I will often have a pattern of using one config to classify stuff on the page and then another config that extracts stuff conditional on that classification.

"extract all monster stat blocks from Monsters PDF. filter on pages with `monster_block`>1 in @classification_artifact.json"


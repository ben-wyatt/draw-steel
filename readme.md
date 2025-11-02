I want to make a playable version of Draw Steel, the new MCDM TTRPG, with LLMs.
There should be a few different parts to this. I can start with building a rules retrieval system, which I will call Rules Lawyer. 



# Rules Lawyer
- data mine the PDF
- Construct knowledge base that allows for efficient retrieval of game rules
- assemble metaprompt that gives a good overview of the basics of the game
- should be low latency
- allows for image retrieval. like monster statblocks and things like that. maybe not?
- requires lots of structured formatting for things like statblocks and class features and stuff
- balance between tool availability and 

## Mining the PDF

We have two PDFs: Heroes and Monsters

They both contain structured content, like monster stat blocks, character abilities, tables, etc.  And they also contain lore text and general natural language rules.

For the retrieval system I want to be able to gracefully handle all of these on retrieval.  So if I search for "Ajax the Invincible" I should both get his stat block and a bunch of lore where he is mentioned from across the book.

I think what that means is that we have a hybrid keyword-semantic natural language search mechanism a la chroma or whatever.  And also return the JSON object that represents his stat block. 

Ideally the retrieval gives well-formatted paragraphs (so no lazy chunking). 

At first I was thinking that we should use pydantic data models to represent the structured formatting.  This would allow for me to take advantage of LLMs for the extraction: convert pdf to image, then send image to LLM and force structured output of the monster stat block.

the other way would be to get really into the weeds with the PDF extraction. In `pdf-parsing/abilities` I was able to vibe-code a proper pdf metadata-to-ability structured output.

monsters is mostly monster stat blocks and lore, 300 pages worth. it also has about 20 pages of rules on how to run monsters, 20 pages on dynamic terrain, and a few more pages on retainers (PC sidekicks).

heroes contains the basics of the rules, how to make characters, combat mechanics, rules for negotiations and montages. 


Stack-rank of PDF ingestion:
- rules: requires chunking strategy thoughts, should be able to return things like condition definitions, combat rules, or triggered actions. goal is super low latency retrieval 
- monster stats
- class traits and abilities

### basic retrieval

With PDF-to-image, image-transcribe, and the qdrant database implementation, I can do mechanic search very quickly: query for "surprise round" to get all the rules on surprise in combat. Right now timings are very good: database query time = 57ms, TTFT = 480ms, completion = 584ms. that is for gemini flash 2.5 lite with token in/out = 622/43.

Run:
```bash
uv run backend/ugly-chat/ugly-chat.py --model google/gemini-2.5-flash-lite --collection-name heroes-delian-full-v1
```

# Future Ideas

Knowledge Graphs constructed via proper noun relationships like Obsidian. run retrieval on that.

Live Play feature that uses LLM to simulate a DM. It rolls dice, has dynamic in-context gamestate, can run combat through a custom game engine.

session scribe: record session transcript (needs powerful model probably), then writes summaries for players, DM, and prep notes for DM, checked against database.


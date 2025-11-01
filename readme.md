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

the front-end that I end up writing for retrieval should be able to link back to the right page of the PDF really easily.

Stack-rank of PDF ingestion:
- rules: requires chunking strategy thoughts, should be able to return things like condition definitions, combat rules, or triggered actions. goal is super low latency retrieval 
- monster stats
- class traits and abilities

### basic retrieval

The most basic functionality that I want is to be able to do mechanic search very quickly: query for "surprise round" to get all the rules on surprise in combat. "shifting" to find out what shifting is. different conditions. basic lookup.

Let's grind out the very basics of something like that first. goal is *incredibly fast retrieval* and an easy way to open up PDF from response.

LLMs can mostly do what I want them to already. Just using image processing.


## Lore Master
- data mine the adventure and setting
- maybe obsidian cross-functionality? allows for both human readability and efficient LLM retrieval?



## Live Play

This is a long shot.

- rolls dice (or UI elements to make player do it)
- has a sense of gamestate: character and monster stamina, positioning,
- can run combat: this would be quite complicated. 
- memory: can read/write for session persistence. How would this effect context over time?



what would make this a lot easier... some type of "system explorer" that is effectively DSPy but e2e automated. building up prompts on how to use tools over time.


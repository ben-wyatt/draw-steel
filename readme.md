I want to make a playable version of Draw Steel, the new MCDM TTRPG, with LLMs.
There should be a few different parts to this. I can start with building a rules retrieval system, which I will call Rules Lawyer.  Then I can try to do something similar for Lore Master.

There should be structured parts and unstructured parts.  


## Rules Lawyer
- data mine the PDF
- Construct knowledge base that allows for efficient retrieval of game rules
- assemble metaprompt that gives a good overview of the basics of the game
- should be low latency
- allows for image retrieval. like monster statblocks and things like that. maybe not?
- requires lots of structured formatting for things like statblocks and class features and stuff
- balance between tool availability and 


### Structured data

ill have a bunch of pydantic data models that I use as structured data. First thing im going to try is converting PDF to markdown (which looks phenomenal) then try to do a bunch of regex matches to grab monster stat blocks.

### derived from PDFs

there are two PDFs: heroes and monsters.  monsters is mostly monster stat blocks and lore, 300 pages worth. it also has about 20 pages of rules on how to run monsters, 20 pages on dynamic terrain, and a few more pages on retainers (PC sidekicks).

heroes contains the basics of the rules, how to make characters, combat mechanics, rules for negotiations and montages. 

lets create a 



## Lore Master
- data mine the adventure and setting
- maybe obsidian cross-functionality? allows for both human readability and efficient LLM retrieval?



## Live Play

- rolls dice (or UI elements to make player do it)
- has a sense of gamestate: character and monster stamina, positioning,
- can run combat: this would be quite complicated. 
- memory: can read/write for session persistence. How would this effect context over time?



what would make this a lot easier... some type of "system explorer" that is effectively DSPy but e2e automated. building up prompts on how to use tools over time.


## Notes along the way

holy crap the markdown you get from the PDF using `markitdown` is insanely good.  I think I can just do some regex parsing and might be able to get all the way through it.

## Quests

- regex parse for malice abilities
- make an eval based on the markdown files.



# Rules Lawyer

## Structured Data
There are primitives, which are core game mechanics
- Power Rolls
- Characteristics
- Abilities
- etc

There are creatures. All creatures have
- characteristics
- abilities


# Some Assumptions
- pages refer to the page number as described at the bottom of the page in the PDF, not the actual PDF page number. "Page 1" is actually Page 14 in the PDF


# Grand Plan

Fast retrieval is the first goal. I want <200ms retrieval on the index, which should include (in order of importance):
- rule word lookup (verbatim excerpts): conditions, rules for grappling, etc
- abilities
- monster stat blocks

chatbot?

UI in line with the PDF?



# Retrieval

which one should I use?
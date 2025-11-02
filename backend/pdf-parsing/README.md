# PDF-PARSING

each folder is an attempt at parsing structred data out of the book PDFs.

the eventual goal is to be able to immediately ingest new PDFs as they come out for the game: adventures, rulebooks, monster books, etc etc.



## abilities

Extracts game abilities from Heroes using font-based pattern matching to identify ability titles, metadata (keywords, action types, ranges), and tier effects. The extraction pipeline processes all 417 pages and filters out false positives like headers and sidebars through validation criteria. Successfully extracted 423 valid abilities from the full PDF, saving structured JSON output with ability names, power rolls, and tier results.

## image-parsing

Parses monster stat block images from the PDFs using vision models (GPT-5 via OpenRouter) to extract structured Monster data including stats, defenses, abilities, and traits. The pipeline encodes images as base64 and uses structured output parsing to convert visual stat blocks into Pydantic Monster models. Contains design notes and examples for modeling stat blocks with discriminated unions for effects, potency gates, and tiered power rolls.

Honestly this is super powerful. GPT-5-mini can perfectly OCR the text of the PDF.

That makes me think that what we should be doing is going off of the classifiers: if a page has a specific class then it should be OCRed with a specific prompt for extraction.

first thing required for this is to have really good classification done already.

### page-transcription

get well formatted paragraph text chunks out of the PDFs.  ONLY extract plain text. output is one big markdown file.



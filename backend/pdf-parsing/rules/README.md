# Rules Extraction

Extracts plain text rule descriptions and flavor text from the Draw Steel Heroes PDF, filtering out structured content like ability blocks and stat blocks.

## Usage

```bash
uv run python pdf-parsing/rules/extract_rules.py
```

## Output

The script generates:
- `data/heroes/rules/extracted_rules.json` - JSON file with all extracted text chunks
- `data/heroes/rules/extraction_summary.txt` - Summary of extraction results

## JSON Structure

Each chunk in the output JSON contains:
- `page`: Page number (1-indexed)
- `text`: Clean paragraph text
- `section`: Major section name (from TOC)
- `subsection`: Subsection header if detected
- `type`: Content type (`rule`, `flavor_text`, `example`, or `section_header`)

## Filtering

The extraction filters out:
- **Ability blocks**: Detected by `Newzald-Bold @ 10pt` font pattern (ability titles)
- **Headers/Footers**: Content in top/bottom 10% of page
- **Sidebars**: Narrow columns in outer 15% of page width
- **Stat blocks**: (Future enhancement)

## Features

- Preserves paragraph boundaries and section structure
- Uses TOC to identify major sections
- Detects subsection headers by font patterns
- Cleans and normalizes whitespace
- Classifies content types (rules, examples, flavor text)


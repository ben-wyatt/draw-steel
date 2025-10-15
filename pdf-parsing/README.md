# Ben's Commentary

This works ok. haven't seen any false positives. but coverage is not perfect. high precision. imperfect recall.

# PDF Structure Analysis and Ability Extraction

## Overview

This directory contains scripts for analyzing and extracting structured data from the Draw Steel Heroes PDF.

## Key Findings

### PDF Metadata

- **Creator**: Adobe InDesign 20.3 (Macintosh)
- **Format**: PDF 1.7
- **Pages**: 417
- **Table of Contents**: 2,192 hierarchical entries (4 levels deep)

### Table Structure

The PDF **does NOT use structured PDF tables**. Instead, tables and ability blocks are created using:

1. **Drawing Objects**: Horizontal and vertical lines that form visual grids
2. **Absolute Text Positioning**: Text is placed at specific coordinates
3. **Font-based Semantics**: Different fonts/sizes indicate different content types

### Ability Block Structure

Ability blocks follow a consistent 3-block pattern:

#### Block 1: Title
- Font: `Newzald-Bold @ 10pt`
- Content: Ability name (e.g., "Melee Weapon Free Strike")

#### Block 2: Metadata
- Font: `BerlingskeSlab-Bold @ 7.5pt`
- 4 lines:
  1. **Keywords**: Comma-separated (e.g., "Charge, Melee, Strike, Weapon")
  2. **Action Type**: (e.g., "Main action", "Maneuver", "Reaction")
  3. **Range**: Prefixed with `e` symbol (e.g., "e Melee 1", "e Ranged 5")
  4. **Target**: Prefixed with `x` symbol (e.g., "x One creature or object")

#### Block 3: Effect
- Font: Mixed (`BerlingskeSlab-DBd @ 7.5pt` for header, `MCDM-Book @ 12pt` for tiers)
- Content:
  - Power roll description (e.g., "Power Roll + Might or Agility:")
  - Tier results with special characters:
    - `á` = Tier 1 (11 or lower)
    - `é` = Tier 2 (12-16)
    - `í` = Tier 3 (17+)

### Font Patterns

| Font | Size | Usage |
|------|------|-------|
| `MCDM-Book` | 24pt | Main headers |
| `Newzald-Bold` | 14pt | Section headers |
| `Newzald-Bold` | 10pt | **Ability titles** ⭐ |
| `BerlingskeSlab-Bold` | 7.5pt | **Ability metadata** ⭐ |
| `BerlingskeSlab-DBd` | 7.5pt | Power roll header |
| `MCDM-Book` | 12pt | **Tier results** ⭐ |
| `BerlingskeSlab-Regular` | 7.5pt | Body text |

## Directory Structure

```
pdf_parsing/
├── README.md                           # This file
├── investigate_pdf_structure.py        # PDF metadata explorer
└── abilities/                          # Ability extraction scripts
    ├── README.md                       # Detailed ability extraction docs
    ├── parse_abilities.py              # Main extraction script
    ├── filter_abilities.py             # Filter false positives
    └── extract_ability_blocks.py       # Detailed analyzer
```

## Scripts

### 1. `investigate_pdf_structure.py`

Comprehensive PDF metadata explorer that analyzes:
- Document metadata
- Table of contents (TOC)
- Page structure
- Text layers and fonts
- Drawing objects (lines, rectangles)
- Table detection
- Links and annotations
- Embedded resources

**Usage:**
```bash
uv run python pdf_parsing/investigate_pdf_structure.py > pdf_structure_report.txt
```

### 2. Ability Extraction Scripts (`abilities/`)

A suite of scripts for extracting game abilities from the PDF.

**Quick Start:**
```bash
# Extract all abilities (generates raw JSON)
uv run python pdf_parsing/abilities/parse_abilities.py

# Filter to valid abilities only
uv run python pdf_parsing/abilities/filter_abilities.py

# Detailed analysis of specific pages
uv run python pdf_parsing/abilities/extract_ability_blocks.py
```

**See `abilities/README.md` for detailed documentation.**

**Results**: Successfully extracted **423 valid abilities** from 417 pages.

**Output files** saved to `pdf_parsing/abilities/`:
- `filtered_abilities_all_pages.json` - Clean abilities (423)
- `extracted_abilities_all_pages.json` - Raw extraction (849)
- Summary text files

**Example output:**
```json
{
  "name": "Melee Weapon Free Strike",
  "page": 32,
  "metadata": {
    "keywords": ["Charge", "Melee", "Strike", "Weapon"],
    "action_type": "Main action",
    "range": "Melee 1",
    "target": "One creature or object"
  },
  "effect": {
    "power_roll": "Power Roll + Might or Agility",
    "tiers": {
      "tier1": "2 + M or A damage",
      "tier2": "5 + M or A damage",
      "tier3": "7 + M or A damage"
    }
  }
}
```

## Extraction Strategy

### 1. Font-Based Detection

The most reliable approach is detecting ability blocks by font:
- Look for `Newzald-Bold @ 10pt` for titles
- Next 2 blocks are metadata and effects

### 2. Table of Contents Navigation

The extensive TOC (2,192 entries) can be used to:
- Jump directly to specific abilities by name
- Understand document structure
- Build a complete index of abilities

### 3. Line-Based Table Detection

For more complex tables (monster stats):
- Extract horizontal/vertical lines using `page.get_drawings()`
- Find line intersections to determine cell boundaries
- Map text blocks to cells by position

## Next Steps

To extract more abilities or monster stats:

1. **Use the TOC**: Find page numbers for specific content
2. **Apply font patterns**: Adjust detection if layout differs
3. **Handle variations**: Some abilities may have additional fields (triggers, costs, etc.)
4. **Batch processing**: Loop through page ranges to extract multiple abilities

## Example: Finding More Abilities

```python
# Search TOC for abilities
doc = fitz.open(HEROES_PDF)
toc = doc.get_toc()

for level, title, page in toc:
    if "Strike" in title or "Attack" in title:
        print(f"{title} → Page {page}")
        # Extract from page-1 (0-indexed)
        abilities = extract_abilities_from_page(doc, page-1)
```

## Known Limitations

1. **Special Characters**: The tier symbols (`á`, `é`, `í`) may need special handling
2. **Multi-line Effects**: Some abilities have more complex effects that span multiple paragraphs
3. **Tables Without Lines**: Some visual tables may not have explicit line drawings
4. **Nested Content**: Sidebars and callout boxes may interrupt ability block sequences

## Dependencies

- `PyMuPDF` (fitz): PDF parsing and text extraction
- Python 3.12+

Install via:
```bash
uv sync
```


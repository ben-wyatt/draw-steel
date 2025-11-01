# Ability Extraction Scripts

This directory contains scripts for extracting and parsing game abilities from the Draw Steel Heroes PDF.

## Scripts

### 1. `parse_abilities.py` ⭐ Main Script

**Purpose**: Extract all abilities from the PDF and save as structured JSON.

**Usage**:
```bash
cd /Users/Ben.Wyatt/Repos/personal/draw-steel-4
uv run python pdf_parsing/abilities/parse_abilities.py
```

**Output** (saved in `pdf_parsing/abilities/`):
- `extracted_abilities_all_pages.json` - Raw extraction (849 entries)
- `abilities_summary_all_pages.txt` - Summary by page

**What it extracts**:
- Ability name
- Page number
- Keywords (Melee, Strike, Magic, etc.)
- Action type (Main action, Maneuver, etc.)
- Range (Melee 1, Ranged 10, etc.)
- Target specification
- Power roll formula
- Tier effects (tier1, tier2, tier3)

---

### 2. `filter_abilities.py` 🔍 Filter Script

**Purpose**: Filter raw extractions to remove false positives (sidebars, headers, etc.).

**Usage**:
```bash
cd /Users/Ben.Wyatt/Repos/personal/draw-steel-4
uv run python pdf_parsing/abilities/filter_abilities.py
```

**Input**: `extracted_abilities_all_pages.json` (in same folder)

**Output** (saved in `pdf_parsing/abilities/`):
- `filtered_abilities_all_pages.json` - Clean, validated abilities (423 entries)
- `filtered_abilities_summary_all_pages.txt` - Filtered summary

**Filtering Criteria**:
- Must have at least 2 keywords
- Must have action type
- Must have range and target
- Must have power roll or effect description
- Keywords must be short game terms (not sentences)

---

### 3. `extract_ability_blocks.py` 🔬 Detailed Analyzer

**Purpose**: Deep analysis of ability block structure for development and debugging.

**Usage**:
```bash
cd /Users/Ben.Wyatt/Repos/personal/draw-steel-4
uv run python pdf_parsing/abilities/extract_ability_blocks.py
```

**Features**:
- Shows all text blocks with font details
- Analyzes drawing objects (lines, rectangles)
- Detects table cells
- Word-level positioning analysis
- Useful for understanding PDF structure and refining detection

---

## Workflow

1. **Extract**: Run `parse_abilities.py` to extract all potential abilities
2. **Filter**: Run `filter_abilities.py` to clean the data
3. **Analyze**: Use `extract_ability_blocks.py` for detailed inspection of specific pages

## Detection Method

Abilities are detected using font-based pattern matching:

1. **Title Block**: `Newzald-Bold @ 10pt`
   - Contains ability name
   
2. **Metadata Block**: `BerlingskeSlab-Bold @ 7.5pt`
   - Line 1: Keywords (comma-separated)
   - Line 2: Action type
   - Line 3: Range (prefixed with `e` symbol)
   - Line 4: Target (prefixed with `x` symbol)

3. **Effect Block**: Mixed fonts
   - Power roll header: `BerlingskeSlab-DBd @ 7.5pt`
   - Tier results: `MCDM-Book @ 12pt` with special characters (`á`, `é`, `í`)

## Example Extracted Ability

```json
{
  "name": "Concussive Slam",
  "page": 65,
  "metadata": {
    "keywords": ["Psionic", "Ranged", "Strike"],
    "action_type": "Main action",
    "range": "Ranged 10",
    "target": "One creature or object",
    "raw_lines": [
      "Psionic, Ranged, Strike",
      "Main action",
      "e Ranged 10",
      "x One creature or object"
    ]
  },
  "effect": {
    "power_roll": "Power Roll + Reason, Intuition, or Presence",
    "tiers": {
      "tier1": "2 + R, I, or P damage;",
      "tier2": "5 + R, I, or P damage; push 1",
      "tier3": "7 + R, I, or P damage; push 2; m<s, prone"
    },
    "raw_lines": [
      "Power Roll + Reason, Intuition, or Presence:",
      "á\t 2 + R, I, or P damage;",
      "é\t 5 + R, I, or P damage; push 1",
      "í\t 7 + R, I, or P damage; push 2; m<s, prone"
    ]
  }
}
```

## Results

From the full Heroes PDF (417 pages):
- **849 raw extractions**
- **423 valid abilities** after filtering
- **9 classes** identified
- **123 pages** contain abilities

See `../../extraction_report.md` for complete analysis.


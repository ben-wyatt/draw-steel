# PDF Parsing - Quick Start Guide

## 🎯 What's Available

This directory contains tools for extracting structured data from the Draw Steel Heroes PDF.

## 📁 Structure

```
pdf_parsing/
├── investigate_pdf_structure.py    # Explore PDF metadata & structure
└── abilities/                      # Extract game abilities
    ├── parse_abilities.py          # Main extraction
    ├── filter_abilities.py         # Clean/filter results
    └── extract_ability_blocks.py   # Detailed analysis
```

## 🚀 Common Tasks

### Explore PDF Structure
```bash
cd /Users/Ben.Wyatt/Repos/personal/draw-steel-4
uv run python pdf_parsing/investigate_pdf_structure.py > report.txt
```

### Extract All Abilities
```bash
cd /Users/Ben.Wyatt/Repos/personal/draw-steel-4

# Step 1: Extract (raw)
uv run python pdf_parsing/abilities/parse_abilities.py

# Step 2: Filter (clean)
uv run python pdf_parsing/abilities/filter_abilities.py
```

**Output**: `pdf_parsing/abilities/filtered_abilities_all_pages.json` (423 abilities)

### Analyze Specific Pages
```bash
# Edit the script to specify pages, then:
uv run python pdf_parsing/abilities/extract_ability_blocks.py
```

## 📊 Current Results

- **423 valid abilities** extracted from 417 pages
- **9 classes** identified
- **JSON format** ready for import

## 📚 More Information

- **`README.md`** - Full documentation
- **`abilities/README.md`** - Ability extraction details
- **`../extraction_report.md`** - Complete analysis

## 💡 Tips

1. All scripts work from the repo root directory
2. Output files are saved to `pdf_parsing/abilities/`
3. Scripts use `uv run` to ensure dependencies are available
4. PyMuPDF (fitz) is the main dependency

## 🔗 Related Files

Output files in `pdf_parsing/abilities/`:
- `filtered_abilities_all_pages.json` - Clean abilities (423)
- `extracted_abilities_all_pages.json` - Raw extraction (849)
- `filtered_abilities_summary_all_pages.txt` - Summary
- Various other summary files

Analysis reports in repo root:
- `extraction_report.md` - Complete analysis report
- `pdf_structure_report.txt` - PDF metadata (if generated)


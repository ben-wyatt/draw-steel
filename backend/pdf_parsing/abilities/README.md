# Ability Extraction Scripts

Vibe-coded pattern-matching PDF extraction.

It doesn't work perfectly.  Lots of post-processing artifacts, and the extraction will not pick up on really long effects within the ability blocks.

I think there is some hope here. But will need a deep-dive for it to fully work.


## Usage

```bash
cd /Users/Ben.Wyatt/Repos/personal/draw-steel-4
uv run python pdf_parsing/abilities/parse_abilities.py
uv run python pdf_parsing/abilities/filter_abilities.py
uv run python pdf_parsing/abilities/extract_ability_blocks.py

```


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


## Results

From the full Heroes PDF (417 pages):
- **849 raw extractions**
- **423 valid abilities** after filtering
- **9 classes** identified
- **123 pages** contain abilities

See `../../extraction_report.md` for complete analysis.


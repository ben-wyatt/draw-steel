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

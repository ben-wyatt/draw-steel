"""
Parse ability blocks from Draw Steel PDF into structured data.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
import json
import re


HEROES_PDF = Path("/Users/Ben.Wyatt/Personal/Draw Steel v1/Draw_Steel_Heroes_v1.pdf")


def extract_text_blocks(page: fitz.Page) -> List[Dict]:
    """Extract text blocks with detailed information."""
    text_dict = page.get_text("dict")
    blocks = []
    
    for block in text_dict.get("blocks", []):
        if "lines" not in block:  # Skip image blocks
            continue
        
        block_info = {
            "bbox": block["bbox"],
            "type": block.get("type", 0),
            "lines": []
        }
        
        for line in block["lines"]:
            line_info = {
                "bbox": line["bbox"],
                "spans": []
            }
            
            for span in line["spans"]:
                span_info = {
                    "text": span.get("text", ""),
                    "font": span.get("font", ""),
                    "size": span.get("size", 0),
                    "color": span.get("color", 0),
                    "flags": span.get("flags", 0),
                    "bbox": span.get("bbox", (0, 0, 0, 0))
                }
                line_info["spans"].append(span_info)
            
            # Combine span texts for line text
            line_info["text"] = "".join(s["text"] for s in line_info["spans"])
            block_info["lines"].append(line_info)
        
        # Combine line texts for block text
        block_info["text"] = "\n".join(l["text"] for l in block_info["lines"])
        blocks.append(block_info)
    
    return blocks


def detect_ability_blocks(text_blocks: List[Dict]) -> List[Dict]:
    """Detect ability block structures using font patterns."""
    ability_blocks = []
    
    for i, block in enumerate(text_blocks):
        if not block["lines"]:
            continue
        
        first_line = block["lines"][0]
        if not first_line["spans"]:
            continue
        
        first_span = first_line["spans"][0]
        font_size = first_span["size"]
        font_name = first_span["font"]
        text = first_span["text"].strip()
        
        # Ability titles are in Newzald-Bold @ ~10pt
        is_ability_title = (
            "Newzald-Bold" in font_name and 
            9 <= font_size <= 11 and
            len(text) > 3
        )
        
        if is_ability_title:
            ability_data = {
                "title_block_index": i,
                "name": text,
                "title_block": block,
                "metadata_block": text_blocks[i + 1] if i + 1 < len(text_blocks) else None,
                "effect_block": text_blocks[i + 2] if i + 2 < len(text_blocks) else None
            }
            ability_blocks.append(ability_data)
    
    return ability_blocks


def parse_metadata_block(metadata_block: Dict) -> Dict[str, Any]:
    """Parse the metadata block into structured fields."""
    metadata = {
        "keywords": [],
        "action_type": None,
        "range": None,
        "target": None,
        "trigger": None,
        "cost": None,
        "raw_lines": []
    }
    
    if not metadata_block:
        return metadata
    
    for line in metadata_block["lines"]:
        text = line["text"].strip()
        metadata["raw_lines"].append(text)
        
        # First line is usually keywords (comma-separated)
        if not metadata["keywords"] and "," in text:
            # Remove trailing tab/whitespace
            keywords_text = text.rstrip("\t ")
            metadata["keywords"] = [k.strip() for k in keywords_text.split(",") if k.strip()]
        
        # Action type (e.g., "Main action", "Maneuver", "Reaction")
        elif "action" in text.lower() or text.lower() in ["maneuver", "reaction", "free maneuver"]:
            metadata["action_type"] = text
        
        # Range (starts with special char or "Melee" / "Ranged")
        elif text.startswith("e ") or "melee" in text.lower() or "ranged" in text.lower():
            metadata["range"] = text.lstrip("e ").strip()
        
        # Target (starts with special char or "One", "Each", "All", etc.)
        elif text.startswith("x ") or any(word in text.lower() for word in ["creature", "object", "ally", "enemy"]):
            metadata["target"] = text.lstrip("x ").strip()
        
        # Trigger (for reactions)
        elif "trigger" in text.lower():
            metadata["trigger"] = text
        
        # Cost (for abilities with costs)
        elif "cost" in text.lower() or any(word in text.lower() for word in ["hero token", "victory"]):
            metadata["cost"] = text
    
    return metadata


def parse_effect_block(effect_block: Dict) -> Dict[str, Any]:
    """Parse the effect block into structured power roll tiers."""
    effect = {
        "description": None,
        "power_roll": None,
        "tiers": {},
        "raw_lines": []
    }
    
    if not effect_block:
        return effect
    
    for line in effect_block["lines"]:
        text = line["text"].strip()
        effect["raw_lines"].append(text)
        
        # Power roll line (e.g., "Power Roll + Might or Agility:")
        if "power roll" in text.lower():
            effect["power_roll"] = text.rstrip(":").strip()
        
        # Tier results (using special characters á, é, í or symbols)
        elif text.startswith("á\t") or "tier 1" in text.lower():
            effect["tiers"]["tier1"] = text.lstrip("á\t ").strip()
        elif text.startswith("é\t") or "tier 2" in text.lower():
            effect["tiers"]["tier2"] = text.lstrip("é\t ").strip()
        elif text.startswith("í\t") or "tier 3" in text.lower():
            effect["tiers"]["tier3"] = text.lstrip("í\t ").strip()
        
        # Description (any other text)
        elif not effect["description"] and text and "power roll" not in text.lower():
            effect["description"] = text
    
    return effect


def parse_ability(ability_raw: Dict) -> Dict[str, Any]:
    """Parse a complete ability into structured data."""
    ability = {
        "name": ability_raw["name"],
        "metadata": parse_metadata_block(ability_raw["metadata_block"]),
        "effect": parse_effect_block(ability_raw["effect_block"])
    }
    
    return ability


def extract_abilities_from_page(doc: fitz.Document, page_num: int) -> List[Dict[str, Any]]:
    """Extract and parse all abilities from a specific page."""
    page = doc[page_num]
    text_blocks = extract_text_blocks(page)
    raw_abilities = detect_ability_blocks(text_blocks)
    
    abilities = []
    for raw_ability in raw_abilities:
        parsed = parse_ability(raw_ability)
        abilities.append(parsed)
    
    return abilities


def main():
    """Extract abilities from the entire PDF."""
    print(f"\nExtracting abilities from {HEROES_PDF}")
    
    if not HEROES_PDF.exists():
        print("ERROR: PDF file not found!")
        return
    
    doc = fitz.open(HEROES_PDF)
    total_pages = doc.page_count
    print(f"Total pages: {total_pages}\n")
    
    try:
        all_abilities = []
        page_summary = {}
        
        print("Processing pages...")
        for page_num in range(total_pages):  # All pages
            if page_num % 10 == 0:
                print(f"  Processing page {page_num + 1}...")
            
            abilities = extract_abilities_from_page(doc, page_num)
            
            if abilities:
                page_summary[page_num + 1] = [a['name'] for a in abilities]
                
                # Add page number to each ability
                for ability in abilities:
                    ability['page'] = page_num + 1
                    all_abilities.append(ability)
        
        print(f"\nCompleted! Found {len(all_abilities)} abilities across {len(page_summary)} pages.\n")
        print("=" * 80)
        print("SUMMARY BY PAGE")
        print("=" * 80)
        
        for page_num in sorted(page_summary.keys()):
            ability_names = page_summary[page_num]
            print(f"\nPage {page_num}: {len(ability_names)} abilities")
            for name in ability_names:
                print(f"  - {name}")
        
        print("\n" + "=" * 80)
        print("SAMPLE ABILITIES (first 5)")
        print("=" * 80)
        
        for i, ability in enumerate(all_abilities[:5], 1):
            print(f"\n[Page {ability['page']}] ABILITY {i}: {ability['name']}")
            print("-" * 80)
            
            # Metadata
            print("\nMETADATA:")
            if ability['metadata']['keywords']:
                print(f"  Keywords: {', '.join(ability['metadata']['keywords'])}")
            if ability['metadata']['action_type']:
                print(f"  Action Type: {ability['metadata']['action_type']}")
            if ability['metadata']['range']:
                print(f"  Range: {ability['metadata']['range']}")
            if ability['metadata']['target']:
                print(f"  Target: {ability['metadata']['target']}")
            if ability['metadata']['trigger']:
                print(f"  Trigger: {ability['metadata']['trigger']}")
            if ability['metadata']['cost']:
                print(f"  Cost: {ability['metadata']['cost']}")
            
            # Effect
            print("\nEFFECT:")
            if ability['effect']['description']:
                print(f"  Description: {ability['effect']['description']}")
            if ability['effect']['power_roll']:
                print(f"  Power Roll: {ability['effect']['power_roll']}")
            
            if ability['effect']['tiers']:
                print("  Tiers:")
                for tier, effect in ability['effect']['tiers'].items():
                    print(f"    {tier}: {effect}")
        
        if len(all_abilities) > 5:
            print(f"\n... and {len(all_abilities) - 5} more abilities")
        
        print("\n" + "=" * 80)
        
        # Save to JSON
        output_dir = Path(__file__).parent
        output_file = output_dir / "extracted_abilities_all_pages.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_abilities, f, indent=2, ensure_ascii=False)
        
        print(f"\nAll {len(all_abilities)} abilities saved to: {output_file}")
        
        # Also save summary
        summary_file = output_dir / "abilities_summary_all_pages.txt"
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("DRAW STEEL ABILITIES EXTRACTION SUMMARY\n")
            f.write(f"All Pages (1-{total_pages})\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total Abilities: {len(all_abilities)}\n")
            f.write(f"Pages with Abilities: {len(page_summary)}\n\n")
            f.write("=" * 80 + "\n")
            f.write("BY PAGE\n")
            f.write("=" * 80 + "\n\n")
            
            for page_num in sorted(page_summary.keys()):
                ability_names = page_summary[page_num]
                f.write(f"Page {page_num}: {len(ability_names)} abilities\n")
                for name in ability_names:
                    f.write(f"  - {name}\n")
                f.write("\n")
        
        print(f"Summary saved to: {summary_file}")
        
    finally:
        doc.close()


if __name__ == "__main__":
    main()


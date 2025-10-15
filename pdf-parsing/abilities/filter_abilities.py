"""
Filter extracted abilities to only include real game abilities.
"""
import json
from pathlib import Path


def is_valid_ability(ability: dict) -> bool:
    """
    Check if an extracted entry is a real game ability.
    
    Real abilities have:
    - At least 2 keywords (game terms like "Strike", "Melee", "Ranged", etc.)
    - An action type (Main action, Maneuver, Reaction, etc.)
    - A range
    - A target
    - Either power roll tiers OR an effect description
    """
    metadata = ability.get('metadata', {})
    effect = ability.get('effect', {})
    
    # Must have keywords (at least 2)
    keywords = metadata.get('keywords', [])
    if len(keywords) < 2:
        return False
    
    # Keywords should be short game terms, not full sentences
    for keyword in keywords:
        if len(keyword) > 30:  # Too long to be a keyword
            return False
    
    # Must have action type
    if not metadata.get('action_type'):
        return False
    
    # Must have range
    if not metadata.get('range'):
        return False
    
    # Must have target
    if not metadata.get('target'):
        return False
    
    # Must have either power roll with tiers OR an effect description
    has_power_roll = effect.get('power_roll') and effect.get('tiers')
    has_effect = effect.get('description') or effect.get('raw_lines')
    
    if not (has_power_roll or has_effect):
        return False
    
    return True


def main():
    script_dir = Path(__file__).parent
    input_file = script_dir / "extracted_abilities_all_pages.json"
    output_file = script_dir / "filtered_abilities_all_pages.json"
    summary_file = script_dir / "filtered_abilities_summary_all_pages.txt"
    
    if not input_file.exists():
        print(f"Error: {input_file} not found!")
        return
    
    # Load all abilities
    with open(input_file, 'r', encoding='utf-8') as f:
        all_abilities = json.load(f)
    
    print(f"Loaded {len(all_abilities)} entries from {input_file}")
    
    # Filter to only valid abilities
    valid_abilities = [a for a in all_abilities if is_valid_ability(a)]
    
    print(f"Found {len(valid_abilities)} valid game abilities")
    print(f"Filtered out {len(all_abilities) - len(valid_abilities)} false positives")
    
    # Save filtered abilities
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(valid_abilities, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {output_file}")
    
    # Create summary by page
    page_summary = {}
    for ability in valid_abilities:
        page = ability['page']
        if page not in page_summary:
            page_summary[page] = []
        page_summary[page].append(ability['name'])
    
    # Save summary
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("DRAW STEEL ABILITIES - FILTERED RESULTS\n")
        f.write("Pages 1-75\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total Valid Abilities: {len(valid_abilities)}\n")
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
    
    # Print sample
    print("\n" + "=" * 80)
    print("SAMPLE ABILITIES (first 10)")
    print("=" * 80)
    
    for i, ability in enumerate(valid_abilities[:10], 1):
        print(f"\n{i}. [{ability['page']}] {ability['name']}")
        print(f"   Keywords: {', '.join(ability['metadata']['keywords'])}")
        print(f"   {ability['metadata']['action_type']} | {ability['metadata']['range']} | {ability['metadata']['target']}")


if __name__ == "__main__":
    main()


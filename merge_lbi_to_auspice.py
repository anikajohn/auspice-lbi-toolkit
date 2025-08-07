#!/usr/bin/env python3
"""
Merge LBI values from Augur output into Auspice JSON format tree.
This script takes an Auspice format tree and adds/updates LBI values from lbi.json.
"""
import json
import argparse
import sys
from pathlib import Path

def clean_name_for_matching(name):
    """Clean node name for matching - same cleaning as used in tree conversion."""
    if name is None:
        return ""
    return str(name).replace(":", "_").replace("(", "_").replace(")", "_").replace(",", "_").replace(";", "_")

def load_lbi_data(lbi_file):
    """Load LBI values from Augur output JSON."""
    try:
        with open(lbi_file, 'r', encoding='utf-8') as f:
            lbi_data = json.load(f)
        
        # Extract LBI values - Augur stores them in nodes section
        lbi_values = {}
        if "nodes" in lbi_data:
            for node_name, node_data in lbi_data["nodes"].items():
                if "lbi" in node_data:
                    lbi_values[node_name] = node_data["lbi"]
        
        print(f"✓ Loaded {len(lbi_values)} LBI values from {lbi_file}")
        return lbi_values
    
    except FileNotFoundError:
        print(f"Error: LBI file '{lbi_file}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{lbi_file}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading LBI file: {e}", file=sys.stderr)
        sys.exit(1)

def update_node_with_lbi(node, lbi_values, node_counter=[0], updated_count=[0]):
    """Recursively update nodes with LBI values."""
    # Get node name or generate the same name as in tree conversion
    node_name = node.get('name', node.get('strain'))
    if not node_name:
        if 'children' in node and node['children']:
            # Internal node - assign same name as conversion script
            node_name = f"NODE_{node_counter[0]:07d}"
            node_counter[0] += 1
        else:
            # Terminal node without name
            node_name = f"LEAF_{node_counter[0]:07d}"
            node_counter[0] += 1
    
    # Clean the name for matching
    clean_node_name = clean_name_for_matching(node_name)
    
    # Check if we have LBI data for this node
    if clean_node_name in lbi_values:
        lbi_value = lbi_values[clean_node_name]
        
        # Ensure node_attrs exists
        if "node_attrs" not in node:
            node["node_attrs"] = {}
        
        # Add/update LBI value
        node["node_attrs"]["lbi"] = {
            "value": lbi_value
        }
        updated_count[0] += 1
        
        # Optional: also store in older 'attr' format for compatibility
        if "attr" not in node:
            node["attr"] = {}
        node["attr"]["lbi"] = lbi_value
    
    # Process children recursively
    if 'children' in node and node['children']:
        for child in node['children']:
            update_node_with_lbi(child, lbi_values, node_counter, updated_count)

def merge_lbi_to_auspice(auspice_file, lbi_file, output_file, backup=True):
    """Main function to merge LBI values into Auspice tree."""
    # Load LBI data
    lbi_values = load_lbi_data(lbi_file)
    
    # Load Auspice tree
    try:
        with open(auspice_file, 'r', encoding='utf-8') as f:
            auspice_data = json.load(f)
        print(f"✓ Loaded Auspice tree from {auspice_file}")
    except FileNotFoundError:
        print(f"Error: Auspice file '{auspice_file}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{auspice_file}': {e}", file=sys.stderr)
        sys.exit(1)
    
    # Create backup if requested
    if backup:
        backup_file = f"{auspice_file}.backup"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(auspice_data, f, indent=2)
        print(f"✓ Created backup at {backup_file}")
    
    # Find the tree root
    root = None
    if 'tree' in auspice_data:
        # Auspice v2 format
        root = auspice_data['tree']
    elif 'nodes' in auspice_data:
        # Some variants store tree in 'nodes'
        root = auspice_data['nodes']
    else:
        # Assume entire JSON is the tree
        root = auspice_data
    
    if not root:
        print("Error: Could not find tree data in Auspice JSON file", file=sys.stderr)
        sys.exit(1)
    
    # Update tree with LBI values
    node_counter = [0]  # Reset counter to match conversion script naming
    updated_count = [0]
    update_node_with_lbi(root, lbi_values, node_counter, updated_count)
    
    # Update metadata to reflect LBI addition
    if "meta" not in auspice_data:
        auspice_data["meta"] = {}
    
    # Add LBI to colorings if it doesn't exist
    if "colorings" not in auspice_data["meta"]:
        auspice_data["meta"]["colorings"] = []
    
    # Check if LBI coloring already exists
    lbi_coloring_exists = any(coloring.get("key") == "lbi" for coloring in auspice_data["meta"]["colorings"])
    
    if not lbi_coloring_exists:
        # Add LBI coloring configuration
        lbi_coloring = {
            "key": "lbi",
            "title": "Local Branching Index (LBI)",
            "type": "continuous",
            "scale": [
                [0.0, "#4575b4"],
                [0.5, "#fee90d"],
                [1.0, "#d73027"]
            ]
        }
        auspice_data["meta"]["colorings"].append(lbi_coloring)
        print("✓ Added LBI coloring configuration")
    else:
        print("✓ LBI coloring configuration already exists")
    
    # Update generation info
    if "updated" not in auspice_data["meta"]:
        auspice_data["meta"]["updated"] = "unknown"
    
    # Write updated tree
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(auspice_data, f, indent=2)
    
    print(f"✓ Updated {updated_count[0]} nodes with LBI values")
    print(f"✓ Updated Auspice tree written to: {output_file}")
    
    # Summary statistics
    if lbi_values:
        lbi_vals = list(lbi_values.values())
        print(f"✓ LBI value range: {min(lbi_vals):.4f} - {max(lbi_vals):.4f}")
        print(f"✓ Average LBI: {sum(lbi_vals)/len(lbi_vals):.4f}")

def main():
    parser = argparse.ArgumentParser(
        description="Merge LBI values from Augur output into Auspice JSON format tree",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - merge LBI into existing tree
  python merge_lbi_to_auspice.py -t tree.json -l lbi.json -o tree_with_lbi.json
  
  # Update tree in place (overwrites original)
  python merge_lbi_to_auspice.py -t tree.json -l lbi.json -o tree.json
  
  # Don't create backup
  python merge_lbi_to_auspice.py -t tree.json -l lbi.json -o tree_with_lbi.json --no-backup

This script:
- Loads LBI values from Augur's lbi.json output
- Merges them into the Auspice tree format
- Replaces existing LBI values if present
- Adds LBI coloring configuration for visualization
- Creates a backup of the original file (unless --no-backup is used)
        """
    )
    parser.add_argument("-t", "--tree", required=True, 
                       help="Input Auspice JSON tree file")
    parser.add_argument("-l", "--lbi", required=True, 
                       help="Input LBI JSON file from Augur")
    parser.add_argument("-o", "--output", required=True, 
                       help="Output Auspice JSON file with LBI values")
    parser.add_argument("--no-backup", action="store_true", 
                       help="Don't create backup of original tree file")
    
    args = parser.parse_args()
    
    # Validate input files exist
    if not Path(args.tree).exists():
        print(f"Error: Tree file '{args.tree}' not found", file=sys.stderr)
        sys.exit(1)
    
    if not Path(args.lbi).exists():
        print(f"Error: LBI file '{args.lbi}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Run the merge
    try:
        merge_lbi_to_auspice(
            auspice_file=args.tree,
            lbi_file=args.lbi,
            output_file=args.output,
            backup=not args.no_backup
        )
        print("✅ Successfully merged LBI values into Auspice tree!")
        
    except Exception as e:
        print(f"Error during merge: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
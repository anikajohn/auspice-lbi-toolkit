#!/usr/bin/env python3
"""
Convert Auspice JSON format to Newick format + branch_lengths.json.
Outputs both tree.nwk and branch_lengths.json in Augur-compatible format.
Handles missing dates by interpolation to ensure Augur LBI compatibility.
"""
import json
import argparse
import sys
from pathlib import Path

def clean_name(name):
    """Clean node name for Newick format."""
    if name is None:
        return ""
    # Replace problematic characters in Newick format
    return str(name).replace(":", "_").replace("(", "_").replace(")", "_").replace(",", "_").replace(";", "_")

def get_branch_length(node, parent_div=None):
    """Extract branch length from Auspice JSON node."""
    branch_length = 0.0
    
    # Try different ways branch lengths/divergence are stored
    current_div = None
    
    # Check node_attrs.div (most common)
    if "node_attrs" in node and isinstance(node["node_attrs"], dict) and "div" in node["node_attrs"]:
        current_div = node["node_attrs"]["div"]
    # Check attr.div (older format)
    elif "attr" in node and isinstance(node["attr"], dict) and "div" in node["attr"]:
        current_div = node["attr"]["div"]
    # Direct branch_length
    elif "branch_length" in node:
        return node["branch_length"]
    
    # Calculate branch length from divergence
    if current_div is not None and parent_div is not None:
        branch_length = current_div - parent_div
    elif current_div is not None:
        branch_length = current_div
    
    return max(0.0, branch_length)  # Ensure non-negative

def get_divergence(node):
    """Get divergence value for calculating branch lengths."""
    if "node_attrs" in node and isinstance(node["node_attrs"], dict) and "div" in node["node_attrs"]:
        return node["node_attrs"]["div"]
    elif "attr" in node and isinstance(node["attr"], dict) and "div" in node["attr"]:
        return node["attr"]["div"]
    return None

def get_node_date(node):
    """Extract node date from Auspice JSON."""
    # Try different ways dates are stored
    if "node_attrs" in node and isinstance(node["node_attrs"], dict):
        node_attrs = node["node_attrs"]
        # Numeric date
        if "num_date" in node_attrs:
            if isinstance(node_attrs["num_date"], (int, float)):
                return float(node_attrs["num_date"])
            elif isinstance(node_attrs["num_date"], dict) and "value" in node_attrs["num_date"]:
                return float(node_attrs["num_date"]["value"])
        # Date confidence interval (use midpoint)
        elif "num_date" in node_attrs and isinstance(node_attrs["num_date"], dict):
            if "confidence" in node_attrs["num_date"]:
                conf = node_attrs["num_date"]["confidence"]
                if isinstance(conf, list) and len(conf) == 2:
                    return float((conf[0] + conf[1]) / 2.0)
    
    # Check older attr format
    if "attr" in node and isinstance(node["attr"], dict):
        attr = node["attr"]
        if "num_date" in attr:
            if isinstance(attr["num_date"], (int, float)):
                return float(attr["num_date"])
            elif isinstance(attr["num_date"], dict) and "value" in attr["num_date"]:
                return float(attr["num_date"]["value"])
    
    return None

def collect_all_dates(node, dates=None):
    """Collect all available dates from the tree for interpolation."""
    if dates is None:
        dates = []
    
    date = get_node_date(node)
    if date is not None:
        dates.append(date)
    
    # Process children recursively
    if 'children' in node and node['children']:
        for child in node['children']:
            collect_all_dates(child, dates)
    
    return dates

def estimate_missing_date(node, parent_date=None, child_dates=None, global_date_range=None):
    """Estimate missing date based on tree structure and available dates."""
    # If we have a parent date and child dates, interpolate
    if parent_date is not None and child_dates and len(child_dates) > 0:
        # Use average of children or midpoint between parent and average child
        avg_child_date = sum(child_dates) / len(child_dates)
        return (parent_date + avg_child_date) / 2.0
    
    # If we only have parent date, use it
    if parent_date is not None:
        return parent_date
    
    # If we have global date range, use midpoint
    if global_date_range and len(global_date_range) >= 2:
        return (min(global_date_range) + max(global_date_range)) / 2.0
    
    # Last resort: use year 2023 (reasonable default for recent data)
    return 2023.0

def assign_dates_recursively(node, parent_date=None, global_date_range=None):
    """Recursively assign dates to all nodes, estimating missing ones."""
    # Get current node date
    current_date = get_node_date(node)
    
    # Collect child dates if we need to estimate
    child_dates = []
    if 'children' in node and node['children']:
        for child in node['children']:
            child_date = get_node_date(child)
            if child_date is not None:
                child_dates.append(child_date)
    
    # If current node has no date, estimate it
    if current_date is None:
        current_date = estimate_missing_date(node, parent_date, child_dates, global_date_range)
    
    # Store the date in the node (we'll use this later)
    if not hasattr(node, '_computed_date'):
        node['_computed_date'] = current_date
    
    # Process children recursively
    if 'children' in node and node['children']:
        for child in node['children']:
            assign_dates_recursively(child, current_date, global_date_range)
    
    return current_date

def extract_node_data(node, node_data, parent_div=None, node_counter=[0], global_date_range=None):
    """Recursively extract node data for branch_lengths.json format."""
    # Get node name or assign one
    node_name = node.get('name', node.get('strain'))
    if not node_name:
        if 'children' in node and node['children']:
            # Internal node - assign a name
            node_name = f"NODE_{node_counter[0]:07d}"
            node_counter[0] += 1
        else:
            # Terminal node without name - this is unusual
            node_name = f"LEAF_{node_counter[0]:07d}"
            node_counter[0] += 1
    
    # Clean the name
    clean_node_name = clean_name(node_name)
    
    # Get branch length and divergence
    branch_length = get_branch_length(node, parent_div)
    current_div = get_divergence(node)
    
    # Get date - use computed date if original is missing
    node_date = get_node_date(node)
    if node_date is None and '_computed_date' in node:
        node_date = node['_computed_date']
    
    # Create node data entry (matching Augur format)
    node_entry = {}
    
    # Add branch length
    if branch_length > 0:
        node_entry["branch_length"] = branch_length
    
    # Add divergence (cumulative branch length)
    if current_div is not None:
        node_entry["div"] = current_div
    
    # CRITICAL: Always add numdate - Augur LBI requires this for ALL nodes
    if node_date is not None:
        node_entry["numdate"] = float(node_date)
    else:
        # Fallback - this should not happen after date assignment, but just in case
        if global_date_range and len(global_date_range) >= 2:
            fallback_date = (min(global_date_range) + max(global_date_range)) / 2.0
        else:
            fallback_date = 2023.0
        node_entry["numdate"] = fallback_date
        print(f"Warning: Using fallback date {fallback_date} for node {clean_node_name}")
    
    # Add any other node attributes that might be useful
    if "node_attrs" in node and isinstance(node["node_attrs"], dict):
        for key, value in node["node_attrs"].items():
            if key not in ["div", "num_date"]:  # Don't duplicate, and skip num_date since we handle it specially
                if isinstance(value, (str, int, float, bool)):
                    node_entry[key] = value
                elif isinstance(value, dict) and "value" in value:
                    node_entry[key] = value["value"]
    
    # Store the data for this node
    node_data["nodes"][clean_node_name] = node_entry
    
    # Process children recursively
    if 'children' in node and node['children']:
        for child in node['children']:
            extract_node_data(child, node_data, current_div, node_counter, global_date_range)
    
    return clean_node_name

def json_to_newick(node, parent_div=None, node_counter=[0]):
    """Convert Auspice JSON node to Newick string recursively."""
    # Get node name or assign one
    node_name = node.get('name', node.get('strain'))
    if not node_name:
        if 'children' in node and node['children']:
            # Internal node - assign a name
            node_name = f"NODE_{node_counter[0]:07d}"
            node_counter[0] += 1
        else:
            # Terminal node without name
            node_name = f"LEAF_{node_counter[0]:07d}"
            node_counter[0] += 1
    
    # Clean the name
    clean_node_name = clean_name(node_name)
    
    # Get branch length and current divergence
    branch_length = get_branch_length(node, parent_div)
    current_div = get_divergence(node)
    
    # Format branch length (only if > 0)
    branch_str = f":{branch_length:.6f}" if branch_length > 0 else ""
    
    # Process children
    if 'children' in node and node['children']:
        children_newick = []
        for child in node['children']:
            children_newick.append(json_to_newick(child, current_div, node_counter))
        children_str = ','.join(children_newick)
        return f'({children_str}){clean_node_name}{branch_str}'
    else:
        # Terminal node
        return f'{clean_node_name}{branch_str}'

def create_branch_lengths_json(root_node):
    """Create branch_lengths.json in Augur format."""
    # First pass: collect all available dates
    all_dates = collect_all_dates(root_node)
    print(f"✓ Found {len(all_dates)} nodes with existing dates")
    
    if all_dates:
        print(f"✓ Date range: {min(all_dates):.2f} - {max(all_dates):.2f}")
    else:
        print("⚠ No dates found in tree - will use default dates")
        all_dates = [2023.0]  # Fallback
    
    # Second pass: assign dates to all nodes (including estimation for missing ones)
    assign_dates_recursively(root_node, None, all_dates)
    
    # Third pass: create the node data structure
    node_data = {
        "nodes": {},
        "generated_by": {
            "program": "auspice_to_newick.py",
            "version": "1.0.2"
        }
    }
    
    # Reset counter for consistent naming
    node_counter = [0]
    extract_node_data(root_node, node_data, None, node_counter, all_dates)
    
    return node_data

def main():
    parser = argparse.ArgumentParser(
        description="Convert Auspice JSON (from Nextclade) to Newick format + branch_lengths.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python auspice_to_newick.py -i nextclade_output.json -o tree.nwk
  python auspice_to_newick.py -i nextclade_output.json -o results/tree.nwk -b results/branch_lengths.json
  
Output files:
  - Newick tree file (.nwk)
  - Branch lengths JSON file (Augur-compatible format)
  
This version ensures ALL nodes have dates required by Augur LBI command.
        """
    )
    parser.add_argument("-i", "--input", required=True, help="Input Auspice JSON file")
    parser.add_argument("-o", "--output", required=True, help="Output Newick file")
    parser.add_argument("-b", "--branch-lengths", help="Output branch lengths JSON file (default: same directory as output with '_branch_lengths.json' suffix)")
    parser.add_argument("--pretty-json", action="store_true", help="Pretty print the JSON output (default: minified)")
    
    args = parser.parse_args()
    
    # Determine branch lengths output path
    if args.branch_lengths:
        branch_lengths_path = args.branch_lengths
    else:
        output_path = Path(args.output)
        branch_lengths_path = output_path.parent / f"{output_path.stem}_branch_lengths.json"
    
    try:
        # Load JSON file
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different Auspice JSON structures
        root = None
        if 'tree' in data:
            # Auspice v2 format
            root = data['tree']
        elif 'nodes' in data:
            # Some variants store tree in 'nodes'
            root = data['nodes']
        else:
            # Assume entire JSON is the tree
            root = data
        
        if not root:
            raise ValueError("Could not find tree data in JSON file")
        
        # Reset node counter for consistent naming between tree and JSON
        node_counter = [0]
        
        # Convert to Newick
        newick_str = json_to_newick(root, None, [0]) + ';'
        
        # Create branch lengths JSON with enhanced date handling
        branch_lengths_data = create_branch_lengths_json(root)
        
        # Write Newick output
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(newick_str)
        
        # Write branch lengths JSON
        json_indent = 2 if args.pretty_json else None
        with open(branch_lengths_path, 'w', encoding='utf-8') as f:
            json.dump(branch_lengths_data, f, indent=json_indent)
        
        print(f"✓ Successfully converted {args.input}")
        print(f"✓ Newick tree written to: {args.output}")
        print(f"✓ Branch lengths JSON written to: {branch_lengths_path}")
        print(f"✓ Found {len(branch_lengths_data['nodes'])} nodes in tree")
        
        # Verify all nodes have numdate
        nodes_with_dates = sum(1 for node_data in branch_lengths_data['nodes'].values() if 'numdate' in node_data)
        print(f"✓ All {nodes_with_dates} nodes have 'numdate' attribute (required for Augur LBI)")
        
        # Show a sample of the branch lengths data
        if branch_lengths_data['nodes']:
            sample_node = next(iter(branch_lengths_data['nodes'].keys()))
            sample_data = branch_lengths_data['nodes'][sample_node]
            print(f"✓ Sample node data: {sample_node} -> {sample_data}")
        
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{args.input}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
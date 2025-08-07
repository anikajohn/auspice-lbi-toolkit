#!/bin/bash

# LBI Integration Workflow for Auspice Trees
# This script automates the complete workflow for computing and integrating
# Local Branching Index (LBI) values into Auspice phylogenetic trees.

set -e  # Exit on any error

# Default parameters
TAU=0.5
WINDOW=0.5
PRETTY_JSON=false
NO_BACKUP=false
CLEANUP_TEMP=true

# Help function
show_help() {
    cat << EOF
LBI Integration Workflow for Auspice Trees

USAGE:
    $0 [OPTIONS] -i INPUT_TREE -o OUTPUT_TREE

DESCRIPTION:
    This script automates the complete workflow for computing Local Branching Index (LBI)
    values using Augur and integrating them back into Auspice JSON format trees.

    Workflow steps:
    1. Convert Auspice JSON to Newick format + branch_lengths.json
    2. Run Augur LBI computation
    3. Merge LBI values back into the original Auspice tree
    4. Clean up temporary files (optional)

OPTIONS:
    -i, --input FILE        Input Auspice JSON tree file (required)
    -o, --output FILE       Output Auspice JSON tree file with LBI values (required)
    
    LBI Parameters:
    --tau FLOAT            Tau parameter for LBI calculation (default: 0.5)
    --window FLOAT         Window parameter for LBI calculation (default: 0.5)
    
    Output Options:
    --pretty-json          Pretty print JSON output files
    --no-backup           Don't create backup of original tree file
    --keep-temp           Keep temporary files (newick, branch_lengths, lbi.json)
    
    General Options:
    -h, --help            Show this help message
    -v, --verbose         Verbose output
    --dry-run             Show commands that would be executed without running them

EXAMPLES:
    # Basic usage
    $0 -i tree.json -o tree_with_lbi.json
    
    # Custom LBI parameters
    $0 -i tree.json -o tree_with_lbi.json --tau 0.3 --window 0.7
    
    # Keep temporary files and use pretty JSON
    $0 -i tree.json -o tree_with_lbi.json --keep-temp --pretty-json
    
    # Dry run to see what commands would be executed
    $0 -i tree.json -o tree_with_lbi.json --dry-run

REQUIREMENTS:
    - Python 3.6+
    - Augur (nextstrain/augur)
    - auspice_to_newick.py (included in this toolkit)
    - merge_lbi_to_auspice.py (included in this toolkit)

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)
            INPUT_TREE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_TREE="$2"
            shift 2
            ;;
        --tau)
            TAU="$2"
            shift 2
            ;;
        --window)
            WINDOW="$2"
            shift 2
            ;;
        --pretty-json)
            PRETTY_JSON=true
            shift
            ;;
        --no-backup)
            NO_BACKUP=true
            shift
            ;;
        --keep-temp)
            CLEANUP_TEMP=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check required arguments
if [[ -z "$INPUT_TREE" ]]; then
    echo "Error: Input tree file is required (-i/--input)"
    show_help
    exit 1
fi

if [[ -z "$OUTPUT_TREE" ]]; then
    echo "Error: Output tree file is required (-o/--output)"
    show_help
    exit 1
fi

# Check if input file exists
if [[ ! -f "$INPUT_TREE" ]]; then
    echo "Error: Input file '$INPUT_TREE' not found"
    exit 1
fi

# Check if required scripts exist
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
AUSPICE_TO_NEWICK="$SCRIPT_DIR/auspice_to_newick.py"
MERGE_LBI="$SCRIPT_DIR/merge_lbi_to_auspice.py"

if [[ ! -f "$AUSPICE_TO_NEWICK" ]]; then
    echo "Error: auspice_to_newick.py not found in $SCRIPT_DIR"
    exit 1
fi

if [[ ! -f "$MERGE_LBI" ]]; then
    echo "Error: merge_lbi_to_auspice.py not found in $SCRIPT_DIR"
    exit 1
fi

# Check if augur is available
if ! command -v augur &> /dev/null; then
    echo "Error: augur command not found. Please install Augur (nextstrain/augur)"
    exit 1
fi

# Generate temporary file names based on input
BASE_NAME=$(basename "$INPUT_TREE" .json)
TEMP_DIR=$(dirname "$INPUT_TREE")
NEWICK_FILE="$TEMP_DIR/${BASE_NAME}_temp.nwk"
BRANCH_LENGTHS_FILE="$TEMP_DIR/${BASE_NAME}_temp_branch_lengths.json"
LBI_FILE="$TEMP_DIR/${BASE_NAME}_temp_lbi.json"

# Function to run commands
run_cmd() {
    if [[ "$VERBOSE" == true ]]; then
        echo "→ $*"
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        return 0
    fi
    
    "$@"
}

# Function to cleanup temporary files
cleanup() {
    if [[ "$CLEANUP_TEMP" == true && "$DRY_RUN" != true ]]; then
        [[ -f "$NEWICK_FILE" ]] && rm -f "$NEWICK_FILE"
        [[ -f "$BRANCH_LENGTHS_FILE" ]] && rm -f "$BRANCH_LENGTHS_FILE"
        [[ -f "$LBI_FILE" ]] && rm -f "$LBI_FILE"
        if [[ "$VERBOSE" == true ]]; then
            echo "✓ Cleaned up temporary files"
        fi
    fi
}

# Set trap for cleanup on exit
trap cleanup EXIT

echo "🧬 Starting LBI Integration Workflow"
echo "   Input:  $INPUT_TREE"
echo "   Output: $OUTPUT_TREE"
echo "   LBI Parameters: tau=$TAU, window=$WINDOW"
echo

# Step 1: Convert Auspice to Newick + branch_lengths
echo "📁 Step 1: Converting Auspice JSON to Newick format..."
CONVERT_ARGS=(-i "$INPUT_TREE" -o "$NEWICK_FILE" -b "$BRANCH_LENGTHS_FILE")
if [[ "$PRETTY_JSON" == true ]]; then
    CONVERT_ARGS+=(--pretty-json)
fi

run_cmd python3 "$AUSPICE_TO_NEWICK" "${CONVERT_ARGS[@]}"

# Step 2: Run Augur LBI
echo "🧮 Step 2: Computing LBI values with Augur..."
run_cmd augur lbi \
    --tree "$NEWICK_FILE" \
    --branch-lengths "$BRANCH_LENGTHS_FILE" \
    --output "$LBI_FILE" \
    --attribute-names "lbi" \
    --tau "$TAU" \
    --window "$WINDOW"

# Step 3: Merge LBI back into Auspice tree
echo "🔄 Step 3: Merging LBI values back into Auspice tree..."
MERGE_ARGS=(-t "$INPUT_TREE" -l "$LBI_FILE" -o "$OUTPUT_TREE")
if [[ "$NO_BACKUP" == true ]]; then
    MERGE_ARGS+=(--no-backup)
fi

run_cmd python3 "$MERGE_LBI" "${MERGE_ARGS[@]}"

if [[ "$DRY_RUN" != true ]]; then
    echo
    echo "✅ LBI integration workflow completed successfully!"
    echo "   Output file: $OUTPUT_TREE"
    
    if [[ "$CLEANUP_TEMP" == false ]]; then
        echo "   Temporary files preserved:"
        echo "     Newick tree: $NEWICK_FILE"
        echo "     Branch lengths: $BRANCH_LENGTHS_FILE"
        echo "     LBI values: $LBI_FILE"
    fi
else
    echo
    echo "🔍 Dry run completed. No files were modified."
fi
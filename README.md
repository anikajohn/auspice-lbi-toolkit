# Auspice LBI Toolkit

Tools for computing and integrating Local Branching Index (LBI) values with Auspice phylogenetic trees.

## Overview

The Local Branching Index (LBI) is a phylogenetic metric that quantifies the "fitness" or evolutionary success of nodes in a phylogenetic tree. This toolkit provides a complete workflow for:

1. Converting Auspice JSON trees to Newick format + outputting branchlength.jason compatible with Augur
2. Computing LBI values using Augur's LBI implementation
3. Merging computed LBI values back into the original Auspice tree format

## Features

- 🔄 **Complete workflow automation** - Single command to go from Auspice tree to LBI-enhanced tree
- 🛠️ **Format conversion** - Robust conversion between Auspice JSON and Newick formats
- 📊 **Missing data handling** - Intelligent interpolation of missing dates required for LBI calculation
- 🎨 **Visualization ready** - Automatically adds LBI coloring configuration for Auspice
- 🔒 **Safe operations** - Creates backups and handles errors gracefully

## Installation

### Prerequisites

- Python 3.6+
- [Augur](https://docs.nextstrain.org/projects/augur/en/stable/installation/installation.html) (nextstrain/augur)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/anikajohn/auspice-lbi-toolkit.git
cd auspice-lbi-toolkit
```

2. Make scripts executable:
```bash
chmod +x lbi_workflow.sh
```

3. Verify Augur installation:
```bash
augur --version
```

## Quick Start

### Simple Usage

```bash
# Compute and integrate LBI values into your Auspice tree
./lbi_workflow.sh -i your_tree.json -o tree_with_lbi.json
```

### Custom Parameters

```bash
# Use custom LBI parameters
./lbi_workflow.sh -i tree.json -o tree_with_lbi.json --tau 0.3 --window 0.7

# Keep temporary files for inspection
./lbi_workflow.sh -i tree.json -o tree_with_lbi.json --keep-temp --verbose
```

## Manual Workflow

If you prefer to run each step manually:

### Step 1: Convert Auspice to Newick

```bash
python3 auspice_to_newick.py -i tree.json -o tree.nwk -b branch_lengths.json
```

### Step 2: Compute LBI with Augur

```bash
augur lbi \
  --tree tree.nwk \
  --branch-lengths branch_lengths.json \
  --output lbi.json \
  --attribute-names "lbi" \
  --tau 0.5 \
  --window 0.5
```

### Step 3: Merge LBI back to Auspice

```bash
python3 merge_lbi_to_auspice.py -t tree.json -l lbi.json -o tree_with_lbi.json
```

## Scripts Description

### `lbi_workflow.sh`
Main workflow script that orchestrates the entire LBI integration process.

**Options:**
- `-i, --input`: Input Auspice JSON tree file (required)
- `-o, --output`: Output Auspice JSON tree file with LBI values (required)
- `--tau`: Tau parameter for LBI calculation (default: 0.5)
- `--window`: Window parameter for LBI calculation (default: 0.5)
- `--pretty-json`: Pretty print JSON output files
- `--no-backup`: Don't create backup of original tree file
- `--keep-temp`: Keep temporary files
- `--verbose`: Verbose output
- `--dry-run`: Show commands without executing

### `auspice_to_newick.py`
Converts Auspice JSON format to Newick tree and Augur-compatible branch_lengths.json.

**Features:**
- Handles missing node dates through intelligent interpolation
- Preserves all node attributes
- Ensures Augur LBI compatibility
- Generates both tree.nwk and branch_lengths.json files

### `merge_lbi_to_auspice.py`
Merges computed LBI values back into the original Auspice tree format.

**Features:**
- Updates existing LBI values or adds new ones
- Maintains tree structure and existing attributes
- Adds LBI coloring configuration for visualization
- Creates backups of original files

## LBI Parameters

- **tau (τ)**: Controls the time window for LBI calculation. Lower values focus on more recent evolution.
- **window**: Sets the sliding window size for LBI computation. Affects temporal resolution.

Common parameter combinations:
- `--tau 0.5 --window 0.5`: Balanced recent/historical weighting
- `--tau 0.3 --window 0.3`: Focus on recent evolution
- `--tau 0.7 --window 0.7`: Include more historical signal

## Troubleshooting

### Common Issues

1. **"KeyError: 'numdate'"**: Some nodes lack date information
   - Solution: The toolkit automatically handles this through date interpolation

2. **"Command 'augur' not found"**: Augur is not installed
   - Solution: Install Augur following [official instructions](https://docs.nextstrain.org/projects/augur/en/stable/installation/installation.html)

3. **"Could not find tree data"**: Unexpected Auspice JSON structure
   - Solution: Ensure your JSON follows standard Auspice v2 format

### Getting Help

```bash
# Show detailed help
./lbi_workflow.sh --help

# Run in dry-run mode to see what would be executed
./lbi_workflow.sh -i tree.json -o output.json --dry-run --verbose
```

## Examples

See the `examples/` directory for:
- Sample input trees
- Expected output formats
- Parameter tuning examples

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this toolkit in your research, please cite:

- **Augur**: Hadfield et al. (2018) Nextstrain: real-time tracking of pathogen evolution. Bioinformatics.
- **LBI method**: Neher et al. (2014) Predicting evolution from the shape of genealogical trees. eLife.

## Related Projects

- [Nextstrain](https://nextstrain.org/) - Real-time tracking of pathogen evolution
- [Augur](https://github.com/nextstrain/augur) - Phylogenetic analyses for Nextstrain
- [Auspice](https://github.com/nextstrain/auspice) - Web-based visualization of phylogenomic data

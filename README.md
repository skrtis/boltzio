# BoltzIO

A Python client and toolkit for [NVIDIA Boltz-2](https://build.nvidia.com/mit/boltz2) protein structure prediction API, with utilities for protein-ligand complex modeling and structure post-processing.

## Features

- **Boltz-2 API Client**: Simple Python interface to the NVIDIA Boltz-2 structure prediction service
- **YAML-based Configuration**: Define protein sequences, ligands, and prediction parameters in human-readable YAML files
- **Multiple Diffusion Samples**: Automatically extracts and saves all diffusion samples as separate numbered mmCIF files
- **Automatic Output Parsing**: Automatically splits API responses into organized structure files (mmCIF, JSON, confidence scores, PAE matrices)
- **Affinity Prediction**: Automatic ligand binding affinity estimation when ligands are present
- **Residue Renumbering**: Post-processing tool to restore biological residue numbering (Boltz-2 always starts from 1)
- **Batch Processing**: Run multiple predictions from a directory of YAML inputs

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/boltzio.git
cd boltzio

# Install in development mode
pip install -e ".[dev]"
```

## Configuration

### API Key Setup

Set your NVIDIA API key as an environment variable or in a `.env` file:

```bash
# Option 1: Environment variable
export BOLTZ2_API_KEY="nvapi-xxxxx"

# Option 2: Create .env file in project root
echo 'BOLTZ2_API_KEY="nvapi-xxxxx"' > .env
```

### YAML Input Format

Create a YAML configuration file for your prediction. See `examples/protein_ligand_template.yaml` for a full template.

```yaml
meta:
  name: "my_prediction"
  author: "Your Name"
  notes: "Description of this run"

sequences:
  - protein:
      id: A
      sequence: "MKTAYIAKQRQISFVKSHFSRQLE..."
  
  - ligand:
      id: L1
      smiles: "CCO"  # or use ccd: "ATP" for PDB ligands

# Prediction parameters
recycling_steps: 3
sampling_steps: 50
diffusion_samples: 5  # Number of structure samples to generate

# Affinity prediction (automatic when ligand present)
sampling_steps_affinity: 200
diffusion_samples_affinity: 5
```

## Command Line Usage

### Generate Structure Prediction

```bash
# Basic usage - automatically extracts all diffusion samples and splits artifacts
boltz2-generate inputs/my_protein.yaml

# Specify output directory and name
boltz2-generate inputs/my_protein.yaml -o structures -n my_output

# Disable automatic splitting of artifacts
boltz2-generate inputs/my_protein.yaml --no-split

# Override API key
boltz2-generate inputs/my_protein.yaml --api-key nvapi-xxxxx

# Set custom timeout (default: 600s)
boltz2-generate inputs/my_protein.yaml --timeout 1200
```

**Options:**
- `-o, --output-dir`: Output directory (default: `structures`)
- `-n, --name`: Custom name for output files (default: YAML filename)
- `--no-split`: Disable automatic splitting into artifact files
- `--api-key`: Override API key from environment
- `--timeout`: Request timeout in seconds (default: 600)

### Split Existing Output

Split a previously generated Boltz-2 output file into separate artifacts:

```bash
boltz2-split structures/my_prediction/my_prediction_1.mmcif
```

This generates:
- `*_protein.mmcif`: Protein-only structure (HETATM records removed)
- `*_confidence.json`: Per-residue pLDDT scores
- `*_matrices.json`: PAE (Predicted Aligned Error) matrices
- `*_affinity.json`: Binding affinity predictions (if available)

### Batch Processing

Run predictions for all YAML files in a directory:

```bash
# Basic batch run (automatically extracts all samples and splits artifacts)
boltz2-batch --inputs inputs --output structures

# Disable artifact splitting
boltz2-batch --inputs inputs --output structures --no-split
```

### Renumber Residues

Boltz-2 always numbers residues starting from 1, regardless of which protein segment was modeled. Use `renumber.py` to restore biological numbering:

```bash
# Renumber mmCIF file (residue 1 becomes 671)
python scripts/renumber.py structure.mmcif --start 671

# Renumber PDB file
python scripts/renumber.py structure.pdb --start 671

# Specify output file
python scripts/renumber.py structure.mmcif --start 671 --output renumbered.mmcif

# Renumber only a specific chain
python scripts/renumber.py structure.mmcif --start 671 --chain A
```

**What gets renumbered:**
- ATOM records (`label_seq_id`, `auth_seq_id`)
- QA metrics (`_ma_qa_metric_local.label_seq_id`) - ensures pLDDT coloring works in viewers
- Polymer sequence scheme tables
- Entity poly sequence tables

**What is preserved:**
- HETATM records (ligands, waters) - these keep their original numbering
- Original whitespace/column formatting

## Output Structure

When running with `diffusion_samples: 5`, the output directory will contain:

```
structures/
└── my_prediction/
    ├── my_prediction_1.mmcif         # Diffusion sample 1 (full structure)
    ├── my_prediction_2.mmcif         # Diffusion sample 2
    ├── my_prediction_3.mmcif         # Diffusion sample 3
    ├── my_prediction_4.mmcif         # Diffusion sample 4
    ├── my_prediction_5.mmcif         # Diffusion sample 5
    ├── my_prediction.json            # Raw API response metadata
    ├── my_prediction_1_protein.mmcif # Sample 1 protein-only structure
    ├── my_prediction_1_confidence.json
    ├── my_prediction_1_matrices.json
    ├── my_prediction_2_protein.mmcif # Sample 2 protein-only structure
    ├── my_prediction_2_confidence.json
    ├── my_prediction_2_matrices.json
    └── ...                           # Artifacts for remaining samples
```

For single diffusion sample runs (`diffusion_samples: 1`):

```
structures/
└── my_prediction/
    ├── my_prediction.mmcif           # Full structure (protein + ligand)
    ├── my_prediction.json            # Raw API response metadata
    ├── my_prediction_protein.mmcif   # Protein-only structure
    ├── my_prediction_confidence.json # pLDDT scores per residue
    ├── my_prediction_matrices.json   # PAE matrices
    └── my_prediction_affinity.json   # Binding affinity (if ligand present)
```

## Python API

```python
from boltz2 import Boltz2Client
from boltz2.payload import load_payload_from_yaml

# Initialize client
client = Boltz2Client()

# Load configuration from YAML
payload = load_payload_from_yaml("inputs/my_protein.yaml")

# Generate structure (automatically extracts all samples and splits)
result = client.generate_from_payload(
    payload=payload,
    output_dir="structures",
    output_name="my_prediction",
    split_outputs=True  # Default is True
)

# Access all generated mmCIF files
print(f"Generated {len(result['mmcifs'])} structures:")
for path in result['mmcifs']:
    print(f"  - {path}")

# Access first structure (for backwards compatibility)
print(f"First structure: {result['mmcif']}")

# Access split artifacts
if 'artifacts' in result:
    print(f"Artifacts: {result['artifacts']}")
```

## Project Structure

```
boltzio/
├── src/boltz2/           # Main package
│   ├── cli.py            # Command-line interfaces
│   ├── client.py         # Boltz-2 API client
│   ├── config.py         # Configuration and API key management
│   ├── payload.py        # YAML to API payload conversion
│   ├── parser.py         # Output file parsing and splitting
│   ├── renumber.py       # Residue renumbering utilities
│   ├── io.py             # File I/O utilities
│   ├── utils.py          # General utility functions
│   └── logging_config.py # Logging configuration
├── scripts/
│   ├── renumber.py       # Residue renumbering CLI
│   ├── batch_run.py      # Batch processing utilities
│   └── generate.py       # Generation helpers
├── examples/
│   └── protein_ligand_template.yaml  # Example YAML template
├── inputs/               # Your YAML input files
├── structures/           # Generated structure outputs
└── tests/                # Unit tests
```

## Requirements

- Python ≥ 3.9
- requests ≥ 2.28.0
- python-dotenv ≥ 1.0.0
- pyyaml ≥ 6.0.0

## Credits

This project is a Python client for **Boltz-2**, developed by the MIT Jameel Clinic in collaboration with NVIDIA. See [CREDITS.md](CREDITS.md) for full acknowledgments.

## License

MIT - See [LICENSE](LICENSE) for details.

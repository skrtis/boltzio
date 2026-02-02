#!/usr/bin/env python3
"""CLI script for generating protein+ligand structures with Boltz-2.

This script provides a command-line interface for protein-ligand structure
prediction using the Boltz-2 API. For most use cases, prefer using the
installed CLI: `boltz2 generate`.

Example:
    python generate.py "MKTAY..." "CCO" -o output -n my_structure
"""

import argparse
import sys
from pathlib import Path

from boltz2 import Boltz2Client
from boltz2.logging_config import get_logger, setup_logging

logger = get_logger("generate")


def main():
    parser = argparse.ArgumentParser(
        description="Generate protein+ligand structure prediction using Boltz-2 API"
    )
    parser.add_argument(
        "sequence",
        help="Protein amino acid sequence",
    )
    parser.add_argument(
        "ligand_smiles",
        help="Ligand SMILES string",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="structures",
        help="Output directory (default: structures)",
    )
    parser.add_argument(
        "-n", "--name",
        help="Friendly name for output files (optional)",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Split outputs into separate artifact files",
    )
    parser.add_argument(
        "--api-key",
        help="API key (overrides .env file)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Request timeout in seconds (default: 600)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        setup_logging(level="DEBUG")

    # Initialize client
    try:
        client = Boltz2Client(api_key=args.api_key, timeout=args.timeout)
    except (RuntimeError, ValueError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

    # Generate structure
    logger.info("Generating protein+ligand structure...")
    logger.info(f"  Sequence: {args.sequence[:50]}{'...' if len(args.sequence) > 50 else ''}")
    logger.info(f"  Ligand: {args.ligand_smiles}")

    try:
        result = client.generate_protein_ligand(
            sequence=args.sequence,
            ligand_smiles=args.ligand_smiles,
            output_dir=Path(args.output_dir),
            output_name=args.name,
            split_outputs=args.split,
        )
    except (RuntimeError, ValueError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

    logger.info("Generation complete!")
    logger.info(f"  Output directory: {result['dir']}")
    logger.info(f"  mmCIF: {result['mmcif']}")
    logger.info(f"  JSON: {result['json']}")

    if args.split and "artifacts" in result:
        logger.info("Artifacts:")
        for key, path in result["artifacts"].items():
            logger.info(f"  {key}: {path}")


if __name__ == "__main__":
    main()

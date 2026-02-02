#!/usr/bin/env python3
"""CLI script for renumbering residues in Boltz-2 structure files.

This script renumbers residue numbers in mmCIF and PDB files to match the
original protein sequence numbering, since Boltz-2 always starts numbering
from 1 regardless of which segment of the protein was modeled.

For most use cases, you can also use the programmatic API:
    >>> from boltz2 import renumber_structure
    >>> renumber_structure(Path("input.mmcif"), start_residue=672)

Example:
    python renumber.py input.mmcif --start 672 --output output.mmcif
    python renumber.py input.pdb --start 672 --output output.pdb
    python renumber.py input.mmcif --start 672 --chain A --output output.mmcif
"""

import argparse
import sys
from pathlib import Path

from boltz2.logging_config import get_logger, setup_logging
from boltz2.renumber import (
    detect_file_format,
    renumber_mmcif,
    renumber_pdb,
)

logger = get_logger("renumber_cli")


def main():
    """Main entry point for the renumber CLI."""
    parser = argparse.ArgumentParser(
        description="Renumber residues in Boltz-2 output structure files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Renumber mmCIF starting from residue 672
  python renumber.py structure.mmcif --start 672

  # Renumber only chain A in a PDB file
  python renumber.py structure.pdb --start 100 --chain A

  # Specify output file
  python renumber.py input.mmcif --start 672 --output renumbered.mmcif
        """,
    )
    parser.add_argument("input", type=Path, help="Input structure file (mmCIF or PDB)")
    parser.add_argument(
        "--start",
        "-s",
        type=int,
        required=True,
        help="Starting residue number (the number that residue 1 should become)",
    )
    parser.add_argument(
        "--chain",
        "-c",
        type=str,
        default=None,
        help="Chain ID to renumber (default: all chains)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output file path (default: input_renumbered.ext)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["mmcif", "pdb", "auto"],
        default="auto",
        help="File format (default: auto-detect)",
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

    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1

    # Detect format
    if args.format == "auto":
        file_format = detect_file_format(args.input)
        logger.debug(f"Auto-detected format: {file_format}")
    else:
        file_format = args.format

    # Set output path
    if args.output is None:
        stem = args.input.stem
        suffix = args.input.suffix
        args.output = args.input.parent / f"{stem}_renumbered{suffix}"

    # Perform renumbering
    logger.info(f"Renumbering {args.input} starting from residue {args.start}")
    if args.chain:
        logger.info(f"  Chain filter: {args.chain}")

    if file_format == "mmcif":
        renumber_mmcif(args.input, args.start, args.output, args.chain)
    else:
        renumber_pdb(args.input, args.start, args.output, args.chain)

    return 0


if __name__ == "__main__":
    sys.exit(main())

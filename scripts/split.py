#!/usr/bin/env python3
"""CLI script for splitting Boltz-2 output files into separate artifacts."""

import argparse
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from boltz2 import split_structure_file


def main():
    parser = argparse.ArgumentParser(
        description="Split Boltz-2 output file into separate artifacts"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to mmCIF or JSON file from Boltz-2 API",
    )

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Splitting: {args.input_file}")

    try:
        artifacts = split_structure_file(args.input_file)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nArtifacts generated:")
    for key, path in artifacts.items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    main()

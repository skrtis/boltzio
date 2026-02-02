#!/usr/bin/env python3
"""Batch-run Boltz-2 predictions for all YAML files under inputs/.

This script will find all `*.yaml` files in the `inputs/` directory (recursively),
load each one, and run a prediction using the package CLI programmatic API.

Usage:
  python scripts/batch_run.py [--inputs inputs] [--output structures] [--split]

Notes:
- Requires that your environment has BOLTZ2_API_KEY set (in .env or environment).
- Runs sequentially; consider parallelizing if needed.
"""

import argparse
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from boltz2 import load_payload_from_yaml, Boltz2Client


def find_yaml_files(inputs_dir: Path):
    return sorted(inputs_dir.rglob("*.yaml"))


def run_yaml(client: Boltz2Client, yaml_path: Path, output_dir: Path, split: bool):
    print(f"\nRunning: {yaml_path}")
    payload = load_payload_from_yaml(yaml_path)
    output_name = yaml_path.stem
    result = client.generate_from_payload(payload, output_dir=output_dir, output_name=output_name, split_outputs=split)
    print(f"Finished: {yaml_path} -> {result['dir']}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Batch-run Boltz-2 YAML inputs")
    parser.add_argument("--inputs", type=Path, default=Path("inputs"), help="Inputs root directory (default: inputs)")
    parser.add_argument("--output", type=Path, default=Path("structures"), help="Output root directory (default: structures)")
    parser.add_argument("--split", action="store_true", help="Split outputs into artifacts")
    parser.add_argument("--api-key", help="API key (overrides .env file)")
    parser.add_argument("--timeout", type=int, default=600, help="Request timeout in seconds")

    args = parser.parse_args()

    inputs_dir = args.inputs
    if not inputs_dir.exists():
        print(f"No inputs directory found: {inputs_dir}", file=sys.stderr)
        sys.exit(1)

    yaml_files = find_yaml_files(inputs_dir)
    if not yaml_files:
        print(f"No YAML files found under {inputs_dir}")
        sys.exit(0)

    # Initialize client
    try:
        client = Boltz2Client(api_key=args.api_key, timeout=args.timeout)
    except RuntimeError as e:
        print(f"Error initializing client: {e}", file=sys.stderr)
        sys.exit(1)

    for yf in yaml_files:
        try:
            run_yaml(client, yf, args.output, args.split)
        except Exception as e:
            print(f"Error running {yf}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()

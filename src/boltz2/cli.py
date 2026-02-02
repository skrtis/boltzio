"""CLI entry points for Boltz-2 package.

This module provides command-line interfaces for the Boltz-2 package:
    - boltz2-generate: Generate structure predictions from YAML config
    - boltz2-split: Split output files into separate artifacts
    - boltz2-batch: Batch process multiple YAML inputs

Example:
    $ boltz2-generate inputs/my_protein.yaml -o structures
    $ boltz2-split structures/my_prediction/my_prediction.mmcif
    $ boltz2-batch --inputs inputs --output structures
"""

import argparse
import logging
import sys
from pathlib import Path

from boltz2 import Boltz2Client, split_structure_file
from boltz2.logging_config import get_logger, setup_logging
from boltz2.payload import extract_metadata_name, load_payload_from_yaml

logger = get_logger("cli")


def generate_main():
    """CLI entry point for generating protein+ligand structures.

    This function is the main entry point for the boltz2-generate command.
    It parses command-line arguments, loads the YAML configuration, and
    submits a prediction request to the Boltz-2 API.
    """
    parser = argparse.ArgumentParser(
        description="Generate structure prediction using Boltz-2 API"
    )
    parser.add_argument(
        "input_yaml",
        type=Path,
        help="Path to YAML file containing Boltz-2 input configuration",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="structures",
        help="Output directory (default: structures)",
    )
    parser.add_argument(
        "-n", "--name",
        help="Friendly name for output files (optional, defaults to YAML filename)",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Disable automatic splitting of outputs into separate artifact files",
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
        help="Enable verbose (debug) logging",
    )

    args = parser.parse_args()

    # Configure logging based on verbosity
    if args.verbose:
        setup_logging(level="DEBUG")

    # Validate input file
    if not args.input_yaml.exists():
        logger.error("Input file not found: %s", args.input_yaml)
        sys.exit(1)

    # Initialize client
    try:
        client = Boltz2Client(api_key=args.api_key, timeout=args.timeout)
    except (ValueError, RuntimeError) as e:
        logger.error("Failed to initialize client: %s", e)
        sys.exit(1)

    # Load payload from YAML
    try:
        payload = load_payload_from_yaml(args.input_yaml)
    except Exception as e:
        logger.error("Error loading YAML: %s", e)
        sys.exit(1)

    # Determine output name priority:
    # 1. Command-line --name argument
    # 2. meta.name from YAML file
    # 3. YAML filename (without extension)
    if args.name:
        output_name = args.name
    else:
        meta_name = extract_metadata_name(args.input_yaml)
        output_name = meta_name or args.input_yaml.stem
        if meta_name:
            logger.debug("Using metadata name from YAML: %s", meta_name)

    # Generate structure
    logger.info("Generating structure from: %s", args.input_yaml)
    logger.info("  Polymers: %d", len(payload.get('polymers', [])))
    logger.info("  Ligands: %d", len(payload.get('ligands', [])))

    try:
        result = client.generate_from_payload(
            payload=payload,
            output_dir=Path(args.output_dir),
            output_name=output_name,
            split_outputs=not args.no_split,
        )
    except RuntimeError as e:
        logger.error("Generation failed: %s", e)
        sys.exit(1)

    logger.info("Generation complete!")
    logger.info("  Output directory: %s", result['dir'])
    mmcif_paths = result.get('mmcifs', [result['mmcif']])
    logger.info("  mmCIF files: %d", len(mmcif_paths))
    for p in mmcif_paths:
        logger.info("    - %s", p)
    logger.info("  JSON: %s", result['json'])

    if not args.no_split and "artifacts" in result:
        logger.info("Artifacts:")
        for key, value in result["artifacts"].items():
            if isinstance(value, dict):
                # Multiple samples
                logger.info("  %s:", key)
                for artifact_key, path in value.items():
                    logger.info("    %s: %s", artifact_key, path)
            else:
                logger.info("  %s: %s", key, value)


def split_main():
    """CLI entry point for splitting Boltz-2 output files.

    This function is the main entry point for the boltz2-split command.
    It splits a Boltz-2 output file into separate artifact files.
    """
    parser = argparse.ArgumentParser(
        description="Split Boltz-2 output file into separate artifacts"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to mmCIF or JSON file from Boltz-2 API",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )

    args = parser.parse_args()

    # Configure logging based on verbosity
    if args.verbose:
        setup_logging(level="DEBUG")

    if not args.input_file.exists():
        logger.error("File not found: %s", args.input_file)
        sys.exit(1)

    logger.info("Splitting: %s", args.input_file)

    try:
        artifacts = split_structure_file(args.input_file)
    except RuntimeError as e:
        logger.error("Split failed: %s", e)
        sys.exit(1)

    logger.info("Artifacts generated:")
    for key, path in artifacts.items():
        logger.info("  %s: %s", key, path)


def batch_main():
    """CLI entry point to batch-run all YAML inputs under a directory.

    This function is the main entry point for the boltz2-batch command.
    It processes all YAML files in a directory and submits predictions
    for each one.

    Usage:
        boltz2-batch --inputs inputs --output structures [--no-split] [--api-key KEY]
    """
    parser = argparse.ArgumentParser(description="Batch-run Boltz-2 YAML inputs")
    parser.add_argument("--inputs", type=Path, default=Path("inputs"), help="Inputs root directory (default: inputs)")
    parser.add_argument("--output", type=Path, default=Path("structures"), help="Output root directory (default: structures)")
    parser.add_argument("--no-split", action="store_true", help="Disable automatic splitting of outputs into artifacts")
    parser.add_argument("--api-key", help="API key (overrides .env file)")
    parser.add_argument("--timeout", type=int, default=600, help="Request timeout in seconds")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose (debug) logging")

    args = parser.parse_args()

    # Configure logging based on verbosity
    if args.verbose:
        setup_logging(level="DEBUG")

    inputs_dir = args.inputs
    if not inputs_dir.exists():
        logger.error("No inputs directory found: %s", inputs_dir)
        sys.exit(1)

    yaml_files = sorted(inputs_dir.rglob("*.yaml"))
    if not yaml_files:
        logger.warning("No YAML files found under %s", inputs_dir)
        sys.exit(0)

    # Initialize client
    try:
        client = Boltz2Client(api_key=args.api_key, timeout=args.timeout)
    except (ValueError, RuntimeError) as e:
        logger.error("Error initializing client: %s", e)
        sys.exit(1)

    for yf in yaml_files:
        try:
            logger.info("Running: %s", yf)

            payload = load_payload_from_yaml(yf)
            # Use metadata name from YAML if available, otherwise use filename
            meta_name = extract_metadata_name(yf)
            output_name = meta_name or yf.stem
            if meta_name:
                logger.debug("Using metadata name from YAML: %s", meta_name)
            result = client.generate_from_payload(payload, output_dir=args.output, output_name=output_name, split_outputs=not args.no_split)
            logger.info("Finished: %s -> %s", yf, result['dir'])
        except Exception as e:
            logger.error("Error running %s: %s", yf, e)

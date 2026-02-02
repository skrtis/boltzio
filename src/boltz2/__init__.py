"""Boltz-2 protein structure prediction client library.

This package provides a Python interface to the NVIDIA Boltz-2 API for
protein structure prediction, along with utilities for building payloads,
parsing responses, and post-processing structure files.

Example:
    >>> from boltz2 import Boltz2Client
    >>> client = Boltz2Client()
    >>> result = client.generate_protein_ligand("MKTAY...", "CCO")
"""

from boltz2.client import Boltz2Client
from boltz2.io import create_run_directory, save_json, save_mmcif
from boltz2.logging_config import get_logger, setup_logging
from boltz2.parser import extract_all_mmcifs, split_structure_file
from boltz2.payload import (
    build_payload,
    build_protein_only_payload,
    extract_metadata_name,
    load_payload_from_yaml,
)
from boltz2.renumber import (
    detect_file_format,
    renumber_mmcif,
    renumber_pdb,
    renumber_structure,
)

__version__ = "0.1.0"

__all__ = [
    # Client
    "Boltz2Client",
    # Parsing
    "extract_all_mmcifs",
    "split_structure_file",
    # Payload building
    "build_payload",
    "build_protein_only_payload",
    "extract_metadata_name",
    "load_payload_from_yaml",
    # I/O
    "create_run_directory",
    "save_mmcif",
    "save_json",
    # Renumbering
    "renumber_structure",
    "renumber_mmcif",
    "renumber_pdb",
    "detect_file_format",
    # Logging
    "setup_logging",
    "get_logger",
]

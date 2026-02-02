"""File I/O utilities for Boltz-2 package.

This module provides functions for file operations including creating
run directories, saving and loading structure and metadata files.

Example:
    >>> from boltz2.io import create_run_directory, save_mmcif
    >>> run_dir, run_name = create_run_directory(Path("output"))
    >>> save_mmcif(mmcif_content, run_dir / "structure.mmcif")
"""

import json
from pathlib import Path
from typing import Any, Optional

from boltz2.utils import generate_run_name


def create_run_directory(
    base_dir: Path,
    output_name: Optional[str] = None,
    prefix: str = "boltz2",
) -> tuple:
    """Create a run-specific output directory.

    Args:
        base_dir: Base directory for all runs (e.g., 'structures/').
        output_name: Optional user-provided name for the run.
        prefix: Default prefix if no output_name provided. Defaults to "boltz2".

    Returns:
        Tuple of (run_directory_path, run_name) where run_directory_path
        is a Path object to the created directory.

    Example:
        >>> run_dir, name = create_run_directory(Path("output"), "my_run")
        >>> name
        'my_run'
    """
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    run_name = generate_run_name(prefix=prefix, output_name=output_name)
    run_dir = base_dir / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    return run_dir, run_name


def save_mmcif(content: str, path: Path) -> Path:
    """Save mmCIF content to a file.

    Args:
        content: mmCIF structure text.
        path: Output file path.

    Returns:
        Path to the saved file.

    Example:
        >>> path = save_mmcif("data_structure\\n...", Path("out.mmcif"))
    """
    path = Path(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def save_json(data: Any, path: Path, indent: int = 2) -> Path:
    """Save data as JSON to a file.

    Args:
        data: Data to serialize (must be JSON-serializable).
        path: Output file path.
        indent: JSON indentation level. Defaults to 2.

    Returns:
        Path to the saved file.

    Example:
        >>> save_json({"score": 0.95}, Path("confidence.json"))
    """
    path = Path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
    return path


def load_json(path: Path) -> Any:
    """Load JSON data from a file.

    Args:
        path: Input file path.

    Returns:
        Parsed JSON data.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.

    Example:
        >>> data = load_json(Path("confidence.json"))
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_text(path: Path) -> str:
    """Read text content from a file.

    Args:
        path: Input file path.

    Returns:
        File contents as string.

    Raises:
        FileNotFoundError: If the file doesn't exist.

    Example:
        >>> content = read_text(Path("structure.mmcif"))
    """
    path = Path(path)
    return path.read_text(encoding="utf-8")

"""Utility functions for Boltz-2 package.

This module provides general-purpose utility functions for filename
sanitization and timestamp generation.

Example:
    >>> from boltz2.utils import sanitize_name, generate_run_name
    >>> safe_name = sanitize_name("My Protein (v2)")
    >>> run_name = generate_run_name(output_name="my_experiment")
"""

from datetime import datetime
from typing import Optional


def sanitize_name(name: str) -> str:
    """Sanitize a name for use as a filename.

    Keeps alphanumerics, dashes, underscores, and dots.
    Replaces spaces with underscores.

    Args:
        name: Raw name string to sanitize.

    Returns:
        Sanitized string safe for use as a filename.

    Example:
        >>> sanitize_name("My Protein (v2)")
        'My_Protein_v2'
    """
    safe = str(name).strip().replace(" ", "_")
    safe = "".join(ch for ch in safe if (ch.isalnum() or ch in "-_."))
    return safe


def generate_timestamp() -> str:
    """Generate a UTC timestamp string for filenames.

    Returns:
        Timestamp in ISO-like format: YYYYMMDDTHHMMSSZ.

    Example:
        >>> ts = generate_timestamp()
        >>> len(ts)
        16
    """
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def generate_run_name(prefix: str = "boltz2", output_name: Optional[str] = None) -> str:
    """Generate a run name, optionally using a user-provided name.

    If output_name is provided and non-empty after sanitization, it is used
    directly. Otherwise, a timestamped name with the given prefix is generated.

    Args:
        prefix: Default prefix if no output_name provided. Defaults to "boltz2".
        output_name: Optional user-provided name (will be sanitized).

    Returns:
        Final run name string, safe for use as a directory name.

    Example:
        >>> generate_run_name(output_name="my_experiment")
        'my_experiment'
        >>> generate_run_name()  # Returns something like 'boltz2_20240101T120000Z'
        'boltz2_...'
    """
    if output_name:
        sanitized = sanitize_name(output_name)
        if sanitized:
            return sanitized
    return f"{prefix}_{generate_timestamp()}"

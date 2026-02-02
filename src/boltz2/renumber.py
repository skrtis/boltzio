"""Residue renumbering utilities for Boltz-2 structure files.

This module provides functions for renumbering residues in mmCIF and PDB
structure files. Boltz-2 always starts residue numbering from 1, but the
biological numbering may differ (e.g., when modeling a domain starting at
residue 672).

Example:
    >>> from boltz2.renumber import renumber_mmcif, renumber_pdb
    >>> renumber_mmcif(Path("input.mmcif"), 672, Path("output.mmcif"))
    >>> renumber_pdb(Path("input.pdb"), 100, Path("output.pdb"), chain_id="A")
"""

from pathlib import Path
from typing import List, Optional, Tuple

from boltz2.logging_config import get_logger

logger = get_logger("renumber")


def find_field_positions(line: str) -> List[Tuple[int, int, str]]:
    """Find the start position, end position, and value of each whitespace-separated field.

    Handles quoted strings in mmCIF format.

    Args:
        line: A line of text from an mmCIF file.

    Returns:
        List of tuples containing (start_pos, end_pos, value) for each field.

    Example:
        >>> fields = find_field_positions("ATOM 1 CA ALA A 1")
        >>> fields[0]
        (0, 4, 'ATOM')
    """
    fields = []
    i = 0
    while i < len(line):
        # Skip whitespace
        while i < len(line) and line[i] in " \t":
            i += 1
        if i >= len(line):
            break

        # Found start of field
        start = i

        # Handle quoted strings
        if line[i] in "\"'":
            quote_char = line[i]
            i += 1
            while i < len(line) and line[i] != quote_char:
                i += 1
            if i < len(line):
                i += 1  # Include closing quote
        else:
            # Regular field - find end
            while i < len(line) and line[i] not in " \t":
                i += 1

        end = i
        value = line[start:end]
        fields.append((start, end, value))

    return fields


def replace_field_preserve_format(line: str, field_idx: int, new_value: str) -> str:
    """Replace a field in a line while preserving surrounding whitespace.

    Args:
        line: Original line of text.
        field_idx: 0-based index of the field to replace.
        new_value: New value to insert.

    Returns:
        Modified line with field replaced.

    Example:
        >>> replace_field_preserve_format("ATOM 1 CA", 1, "100")
        'ATOM 100 CA'
    """
    fields = find_field_positions(line)
    if field_idx >= len(fields):
        return line

    start, end, old_value = fields[field_idx]

    # Build new line: everything before the field + new value + everything after
    return line[:start] + new_value + line[end:]


def renumber_mmcif(
    input_path: Path,
    start_residue: int,
    output_path: Path,
    chain_id: Optional[str] = None,
) -> None:
    """Renumber residues in an mmCIF file.

    Updates residue numbers in multiple mmCIF sections:
    - _atom_site (atomic coordinates)
    - _pdbx_poly_seq_scheme (sequence mapping)
    - _entity_poly_seq (polymer sequence)
    - _ma_qa_metric_local (pLDDT/confidence scores)

    Only ATOM records are renumbered; HETATM records (ligands, waters)
    are preserved with their original numbering.

    Args:
        input_path: Path to input mmCIF file.
        start_residue: Starting residue number (the number that residue 1
            should become).
        output_path: Path to output mmCIF file.
        chain_id: Optional chain ID to renumber. If None, all chains are
            renumbered.

    Example:
        >>> renumber_mmcif(
        ...     Path("structure.mmcif"),
        ...     start_residue=672,
        ...     output_path=Path("renumbered.mmcif"),
        ...     chain_id="A"
        ... )
    """
    text = input_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    output_lines = []

    # Track which section we're in
    in_atom_site = False
    in_poly_seq_scheme = False
    in_entity_poly_seq = False
    in_ma_qa_metric_local = False
    atom_site_columns: List[str] = []
    poly_seq_scheme_columns: List[str] = []
    entity_poly_seq_columns: List[str] = []
    ma_qa_metric_local_columns: List[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect start of _atom_site loop
        if line.strip().startswith("_atom_site."):
            atom_site_columns = []
            while i < len(lines) and lines[i].strip().startswith("_atom_site."):
                col_name = lines[i].strip().split(".")[1]
                atom_site_columns.append(col_name)
                output_lines.append(lines[i])
                i += 1
            in_atom_site = True
            continue

        # Detect start of _pdbx_poly_seq_scheme loop
        if line.strip().startswith("_pdbx_poly_seq_scheme."):
            poly_seq_scheme_columns = []
            while i < len(lines) and lines[i].strip().startswith(
                "_pdbx_poly_seq_scheme."
            ):
                col_name = lines[i].strip().split(".")[1]
                poly_seq_scheme_columns.append(col_name)
                output_lines.append(lines[i])
                i += 1
            in_poly_seq_scheme = True
            continue

        # Detect start of _entity_poly_seq loop
        if line.strip().startswith("_entity_poly_seq."):
            entity_poly_seq_columns = []
            while i < len(lines) and lines[i].strip().startswith("_entity_poly_seq."):
                col_name = lines[i].strip().split(".")[1]
                entity_poly_seq_columns.append(col_name)
                output_lines.append(lines[i])
                i += 1
            in_entity_poly_seq = True
            continue

        # Detect start of _ma_qa_metric_local loop (QA/pLDDT scores)
        if line.strip().startswith("_ma_qa_metric_local."):
            ma_qa_metric_local_columns = []
            while i < len(lines) and lines[i].strip().startswith(
                "_ma_qa_metric_local."
            ):
                col_name = lines[i].strip().split(".")[1]
                ma_qa_metric_local_columns.append(col_name)
                output_lines.append(lines[i])
                i += 1
            in_ma_qa_metric_local = True
            continue

        # End of any loop section
        if line.strip() == "#" or line.strip().startswith("loop_"):
            in_atom_site = False
            in_poly_seq_scheme = False
            in_entity_poly_seq = False
            in_ma_qa_metric_local = False
            output_lines.append(line)
            i += 1
            continue

        # Process atom_site data
        if in_atom_site and line.strip() and not line.strip().startswith("_"):
            fields = find_field_positions(line)
            parts = [f[2] for f in fields]
            if len(parts) >= len(atom_site_columns):
                try:
                    group_pdb_idx = (
                        atom_site_columns.index("group_PDB")
                        if "group_PDB" in atom_site_columns
                        else None
                    )
                    label_seq_idx = (
                        atom_site_columns.index("label_seq_id")
                        if "label_seq_id" in atom_site_columns
                        else None
                    )
                    auth_seq_idx = (
                        atom_site_columns.index("auth_seq_id")
                        if "auth_seq_id" in atom_site_columns
                        else None
                    )
                    label_asym_idx = (
                        atom_site_columns.index("label_asym_id")
                        if "label_asym_id" in atom_site_columns
                        else None
                    )

                    # Skip HETATM records
                    record_type = (
                        parts[group_pdb_idx] if group_pdb_idx is not None else None
                    )
                    if record_type == "HETATM":
                        output_lines.append(line)
                        i += 1
                        continue

                    # Check chain filter
                    current_chain = (
                        parts[label_asym_idx] if label_asym_idx is not None else None
                    )
                    if chain_id is None or current_chain == chain_id:
                        if label_seq_idx is not None and parts[label_seq_idx] != ".":
                            old_num = int(parts[label_seq_idx])
                            new_num = old_num + start_residue - 1
                            line = replace_field_preserve_format(
                                line, label_seq_idx, str(new_num)
                            )
                            fields = find_field_positions(line)
                            parts = [f[2] for f in fields]

                        if auth_seq_idx is not None and parts[auth_seq_idx] != "?":
                            old_num = int(parts[auth_seq_idx])
                            new_num = old_num + start_residue - 1
                            line = replace_field_preserve_format(
                                line, auth_seq_idx, str(new_num)
                            )

                except (ValueError, IndexError):
                    pass

        # Process pdbx_poly_seq_scheme data
        if in_poly_seq_scheme and line.strip() and not line.strip().startswith("_"):
            fields = find_field_positions(line)
            parts = [f[2] for f in fields]
            if len(parts) >= len(poly_seq_scheme_columns):
                try:
                    asym_idx = (
                        poly_seq_scheme_columns.index("asym_id")
                        if "asym_id" in poly_seq_scheme_columns
                        else None
                    )
                    seq_id_idx = (
                        poly_seq_scheme_columns.index("seq_id")
                        if "seq_id" in poly_seq_scheme_columns
                        else None
                    )
                    pdb_seq_num_idx = (
                        poly_seq_scheme_columns.index("pdb_seq_num")
                        if "pdb_seq_num" in poly_seq_scheme_columns
                        else None
                    )
                    auth_seq_num_idx = (
                        poly_seq_scheme_columns.index("auth_seq_num")
                        if "auth_seq_num" in poly_seq_scheme_columns
                        else None
                    )

                    current_chain = parts[asym_idx] if asym_idx is not None else None
                    if chain_id is None or current_chain == chain_id:
                        indices_to_update = []
                        for idx in [seq_id_idx, pdb_seq_num_idx, auth_seq_num_idx]:
                            if idx is not None and parts[idx] not in (".", "?"):
                                old_num = int(parts[idx])
                                new_num = old_num + start_residue - 1
                                indices_to_update.append((idx, str(new_num)))

                        for idx, new_val in sorted(
                            indices_to_update, key=lambda x: x[0], reverse=True
                        ):
                            line = replace_field_preserve_format(line, idx, new_val)

                except (ValueError, IndexError):
                    pass

        # Process entity_poly_seq data
        if in_entity_poly_seq and line.strip() and not line.strip().startswith("_"):
            fields = find_field_positions(line)
            parts = [f[2] for f in fields]
            if len(parts) >= len(entity_poly_seq_columns):
                try:
                    num_idx = (
                        entity_poly_seq_columns.index("num")
                        if "num" in entity_poly_seq_columns
                        else None
                    )
                    if num_idx is not None and parts[num_idx] not in (".", "?"):
                        old_num = int(parts[num_idx])
                        new_num = old_num + start_residue - 1
                        line = replace_field_preserve_format(line, num_idx, str(new_num))

                except (ValueError, IndexError):
                    pass

        # Process ma_qa_metric_local data
        if (
            in_ma_qa_metric_local
            and line.strip()
            and not line.strip().startswith("_")
        ):
            fields = find_field_positions(line)
            parts = [f[2] for f in fields]
            if len(parts) >= len(ma_qa_metric_local_columns):
                try:
                    label_asym_idx = (
                        ma_qa_metric_local_columns.index("label_asym_id")
                        if "label_asym_id" in ma_qa_metric_local_columns
                        else None
                    )
                    label_seq_idx = (
                        ma_qa_metric_local_columns.index("label_seq_id")
                        if "label_seq_id" in ma_qa_metric_local_columns
                        else None
                    )

                    current_chain = (
                        parts[label_asym_idx] if label_asym_idx is not None else None
                    )
                    if chain_id is None or current_chain == chain_id:
                        if (
                            label_seq_idx is not None
                            and parts[label_seq_idx] not in (".", "?")
                        ):
                            old_num = int(parts[label_seq_idx])
                            new_num = old_num + start_residue - 1
                            line = replace_field_preserve_format(
                                line, label_seq_idx, str(new_num)
                            )

                except (ValueError, IndexError):
                    pass

        output_lines.append(line)
        i += 1

    output_path.write_text("\n".join(output_lines), encoding="utf-8")
    logger.info(f"Renumbered mmCIF saved to: {output_path}")


def renumber_pdb(
    input_path: Path,
    start_residue: int,
    output_path: Path,
    chain_id: Optional[str] = None,
) -> None:
    """Renumber residues in a PDB file.

    Updates residue sequence numbers in ATOM, TER, and ANISOU records.
    HETATM records are not modified.

    Args:
        input_path: Path to input PDB file.
        start_residue: Starting residue number (the number that residue 1
            should become).
        output_path: Path to output PDB file.
        chain_id: Optional chain ID to renumber. If None, all chains are
            renumbered.

    Example:
        >>> renumber_pdb(
        ...     Path("structure.pdb"),
        ...     start_residue=100,
        ...     output_path=Path("renumbered.pdb"),
        ...     chain_id="A"
        ... )
    """
    text = input_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    output_lines = []

    for line in lines:
        if line.startswith(("ATOM", "TER", "ANISOU")):
            try:
                current_chain = line[21] if len(line) > 21 else None

                if (
                    chain_id is None
                    or current_chain == chain_id
                    or current_chain == " "
                ):
                    if len(line) >= 26:
                        old_resnum_str = line[22:26]
                        old_resnum = int(old_resnum_str)
                        new_resnum = old_resnum + start_residue - 1
                        new_resnum_str = f"{new_resnum:4d}"
                        line = line[:22] + new_resnum_str + line[26:]
            except (ValueError, IndexError):
                pass

        output_lines.append(line)

    output_path.write_text("\n".join(output_lines), encoding="utf-8")
    logger.info(f"Renumbered PDB saved to: {output_path}")


def detect_file_format(path: Path) -> str:
    """Detect whether a file is mmCIF or PDB format.

    Uses content-based detection first, then falls back to file extension.

    Args:
        path: Path to structure file.

    Returns:
        Format string: either 'mmcif' or 'pdb'.

    Example:
        >>> detect_file_format(Path("structure.cif"))
        'mmcif'
    """
    text = path.read_text(encoding="utf-8")
    if "data_" in text or "_atom_site." in text:
        return "mmcif"
    elif text.strip().startswith(
        ("ATOM", "HETATM", "HEADER", "TITLE", "REMARK", "CRYST")
    ):
        return "pdb"
    else:
        suffix = path.suffix.lower()
        if suffix in (".cif", ".mmcif"):
            return "mmcif"
        return "pdb"


def renumber_structure(
    input_path: Path,
    start_residue: int,
    output_path: Optional[Path] = None,
    chain_id: Optional[str] = None,
    file_format: str = "auto",
) -> Path:
    """Renumber residues in a structure file (mmCIF or PDB).

    This is a convenience function that auto-detects the file format
    and calls the appropriate renumbering function.

    Args:
        input_path: Path to input structure file.
        start_residue: Starting residue number (the number that residue 1
            should become).
        output_path: Path to output file. If None, appends "_renumbered"
            to the input filename.
        chain_id: Optional chain ID to renumber. If None, all chains are
            renumbered.
        file_format: File format, one of "mmcif", "pdb", or "auto".
            Defaults to "auto" (auto-detect).

    Returns:
        Path to the output file.

    Raises:
        FileNotFoundError: If the input file doesn't exist.

    Example:
        >>> output = renumber_structure(
        ...     Path("structure.mmcif"),
        ...     start_residue=672
        ... )
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Detect format
    if file_format == "auto":
        file_format = detect_file_format(input_path)

    # Set output path
    if output_path is None:
        stem = input_path.stem
        suffix = input_path.suffix
        output_path = input_path.parent / f"{stem}_renumbered{suffix}"
    else:
        output_path = Path(output_path)

    # Perform renumbering
    if file_format == "mmcif":
        renumber_mmcif(input_path, start_residue, output_path, chain_id)
    else:
        renumber_pdb(input_path, start_residue, output_path, chain_id)

    return output_path

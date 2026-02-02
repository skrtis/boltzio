"""Parsing utilities for Boltz-2 API responses.

This module provides functions for extracting and processing data from
Boltz-2 API responses, including structure data, confidence scores,
affinity predictions, and matrix data.

Example:
    >>> from boltz2.parser import extract_all_mmcifs, split_structure_file
    >>> mmcifs = extract_all_mmcifs(api_response)
    >>> artifacts = split_structure_file(Path("output.mmcif"))
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from boltz2.logging_config import get_logger

logger = get_logger("parser")


def extract_all_mmcifs(response_data: Any) -> List[str]:
    """Extract all mmCIF structures from API response.

    This function handles both JSON API responses and raw mmCIF text input.
    When the response contains multiple diffusion samples, all structures
    are returned.

    Args:
        response_data: Either a parsed JSON response dictionary from the API,
            a JSON string, or raw mmCIF text.

    Returns:
        List of mmCIF structure strings. Returns an empty list if no
        structures are found. Returns a single-element list if the input
        is raw mmCIF text.

    Example:
        >>> response = {"structures": [{"structure": "data_..."}]}
        >>> mmcifs = extract_all_mmcifs(response)
        >>> len(mmcifs)
        1
    """
    if isinstance(response_data, str):
        # Try parsing as JSON
        try:
            if response_data.lstrip().startswith("{"):
                response_data = json.loads(response_data)
            else:
                # Already mmCIF text - return as single-element list
                return [response_data]
        except json.JSONDecodeError:
            # Assume it's raw mmCIF
            return [response_data]

    # Extract all structures from JSON
    mmcifs = []
    if isinstance(response_data, dict):
        structures = response_data.get("structures")
        if structures and isinstance(structures, list):
            for struct in structures:
                if isinstance(struct, dict) and struct.get("structure"):
                    mmcifs.append(struct.get("structure"))

    return mmcifs


def extract_confidence_data(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract confidence scores from API response.

    Args:
        response_data: Parsed JSON response dictionary from the Boltz-2 API.

    Returns:
        Dictionary containing confidence-related metrics including pTM scores,
        ipTM scores, pLDDT scores, and QA metrics. Only keys with non-None
        values are included.

    Example:
        >>> data = {"confidence_scores": [0.9], "ptm_scores": [0.85]}
        >>> confidence = extract_confidence_data(data)
        >>> confidence["ptm_scores"]
        [0.85]
    """
    confidence_keys = [
        "confidence_scores",
        "ptm_scores",
        "iptm_scores",
        "complex_plddt_scores",
        "complex_iplddt_scores",
        "ma_qa_metric_local",
        "ma_qa_metric",
    ]
    return {k: response_data.get(k) for k in confidence_keys if response_data.get(k) is not None}


def extract_affinity_data(response_data: Dict[str, Any]) -> Optional[Any]:
    """Extract affinity data from API response.

    Args:
        response_data: Parsed JSON response dictionary from the Boltz-2 API.

    Returns:
        Affinity prediction data if present in the response, otherwise None.
        The format depends on the API response structure.

    Example:
        >>> data = {"affinities": [{"ligand": "L1", "value": -8.5}]}
        >>> affinity = extract_affinity_data(data)
        >>> affinity[0]["value"]
        -8.5
    """
    return response_data.get("affinities")


def extract_matrix_data(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract 2D matrix data (pairwise scores) from API response.

    Args:
        response_data: Parsed JSON response dictionary from the Boltz-2 API.

    Returns:
        Dictionary containing pairwise matrix data such as inter-chain
        ipTM scores and complex ipLDDT scores. Only keys with non-None
        values are included.

    Example:
        >>> data = {"pair_chains_iptm_scores": [[1.0, 0.8], [0.8, 1.0]]}
        >>> matrices = extract_matrix_data(data)
        >>> "pair_chains_iptm_scores" in matrices
        True
    """
    matrix_keys = ["pair_chains_iptm_scores", "complex_iplddt_scores"]
    return {k: response_data.get(k) for k in matrix_keys if response_data.get(k) is not None}


def split_structure_file(input_path: Path) -> Dict[str, Path]:
    """Split a Boltz-2 output file into separate artifacts.

    Produces multiple output files from a combined Boltz-2 output:
      - Full mmCIF file
      - Protein-only mmCIF (HETATM lines removed)
      - Confidence scores JSON
      - Affinity JSON
      - Matrices JSON

    Args:
        input_path: Path to mmCIF or JSON file from the Boltz-2 API.

    Returns:
        Dictionary mapping artifact type to file path. Keys include:
        'mmcif', 'protein_mmcif', 'confidence_json', 'affinity_json',
        'matrices_json'. Only successfully created artifacts are included.

    Raises:
        RuntimeError: If no mmCIF content can be found in the input file.

    Example:
        >>> artifacts = split_structure_file(Path("prediction.mmcif"))
        >>> print(artifacts["mmcif"])
        PosixPath('prediction.mmcif')
    """
    input_path = Path(input_path)
    base = input_path.stem
    out_dir = input_path.parent

    # Try to load JSON data
    full_json = None

    # Check for accompanying JSON file (same name with .json suffix)
    json_candidate = input_path.with_suffix(".json")
    if json_candidate.exists() and json_candidate != input_path:
        try:
            with open(json_candidate, "r", encoding="utf-8") as f:
                full_json = json.load(f)
        except Exception:
            pass

    # Read input file
    text = input_path.read_text(encoding="utf-8")

    # If input looks like JSON, parse it
    if full_json is None and text.lstrip().startswith("{"):
        try:
            full_json = json.loads(text)
        except Exception:
            pass

    # Extract mmCIF text
    mmcif_text = None
    if full_json:
        mmcifs = extract_all_mmcifs(full_json)
        if mmcifs:
            mmcif_text = mmcifs[0]

    if mmcif_text is None:
        # Try to find mmCIF content in raw text
        if "data_" in text or "loop_" in text:
            mmcif_text = text
        else:
            idx = text.find("data_")
            if idx == -1:
                idx = text.find("_entry.id")
            if idx != -1:
                mmcif_text = text[idx:]
            else:
                raise RuntimeError("Could not find mmCIF content in input file")

    generated: Dict[str, Path] = {}

    # Write full mmCIF
    mmcif_out = out_dir / f"{base}.mmcif"
    with open(mmcif_out, "w", encoding="utf-8") as f:
        f.write(mmcif_text)
    generated["mmcif"] = mmcif_out

    # Produce protein-only mmCIF (remove HETATM lines)
    lines = mmcif_text.splitlines()
    protein_lines = [ln for ln in lines if not ln.startswith("HETATM")]
    protein_out = out_dir / f"{base}_protein.mmcif"
    with open(protein_out, "w", encoding="utf-8") as f:
        f.write("\n".join(protein_lines))
    generated["protein_mmcif"] = protein_out

    # Extract JSON artifacts if available
    if full_json:
        # Confidence data
        confidence_data = extract_confidence_data(full_json)
        if confidence_data:
            conf_out = out_dir / f"{base}_confidence.json"
            with open(conf_out, "w", encoding="utf-8") as f:
                json.dump(confidence_data, f, indent=2)
            generated["confidence_json"] = conf_out

        # Affinity data
        affinity_data = extract_affinity_data(full_json)
        if affinity_data:  # Only write if non-empty
            aff_out = out_dir / f"{base}_affinity.json"
            with open(aff_out, "w", encoding="utf-8") as f:
                json.dump(affinity_data, f, indent=2)
            generated["affinity_json"] = aff_out

        # Matrix data
        matrix_data = extract_matrix_data(full_json)
        if matrix_data:
            mat_out = out_dir / f"{base}_matrices.json"
            with open(mat_out, "w", encoding="utf-8") as f:
                json.dump(matrix_data, f, indent=2)
            generated["matrices_json"] = mat_out

    return generated

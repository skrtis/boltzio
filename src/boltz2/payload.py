"""Payload building for Boltz-2 API requests.

This module provides functions for constructing API request payloads
from various input formats including YAML files and Python dictionaries.

Example:
    >>> from boltz2.payload import build_payload, load_payload_from_yaml
    >>> payload = build_payload("MKTAY...", "CCO")
    >>> yaml_payload = load_payload_from_yaml(Path("input.yaml"))
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml


def extract_metadata_name(yaml_path: Path) -> Optional[str]:
    """Extract the metadata name from a YAML configuration file.

    Looks for the `meta.name` field in the YAML file. This is useful for
    determining the output folder name based on the user's specified name
    rather than the filename.

    Args:
        yaml_path: Path to the YAML configuration file.

    Returns:
        The metadata name if found, otherwise None.

    Example:
        >>> name = extract_metadata_name(Path("protein_ligand.yaml"))
        >>> print(name)
        'prod-PDE3A-ensifentrine'
    """
    yaml_path = Path(yaml_path)
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if config and isinstance(config, dict):
            meta = config.get("meta", {})
            if isinstance(meta, dict):
                return meta.get("name")
    except Exception:
        pass
    return None


def load_payload_from_yaml(yaml_path: Path) -> Dict[str, Any]:
    """Load a Boltz-2 payload from a YAML file.

    Args:
        yaml_path: Path to the YAML configuration file.

    Returns:
        Dictionary suitable for the Boltz-2 API request.

    Raises:
        ValueError: If the YAML file is empty, invalid, or doesn't
            contain a mapping at the root level.

    Example:
        >>> payload = load_payload_from_yaml(Path("protein_ligand.yaml"))
        >>> "polymers" in payload
        True
    """
    yaml_path = Path(yaml_path)
    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError(f"YAML file is empty or invalid: {yaml_path}")
    if not isinstance(config, dict):
        raise ValueError(f"YAML root must be a mapping/dictionary: {yaml_path}")

    return build_payload_from_config(config)


def build_payload_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Boltz-2 payload from a configuration dict.

    Supports the Boltz-2 YAML input format with 'sequences' key containing
    proteins, RNA, DNA, and ligands.

    Args:
        config: Configuration dictionary, typically loaded from a YAML file.
            Should contain a 'sequences' list with molecule definitions.

    Returns:
        Complete payload dictionary ready for API request, with 'polymers'
        and 'ligands' lists plus prediction parameters.

    Example:
        >>> config = {"sequences": [{"protein": {"sequence": "MKTAY"}}]}
        >>> payload = build_payload_from_config(config)
        >>> payload["polymers"][0]["sequence"]
        'MKTAY'
    """
    payload: Dict[str, Any] = {}

    # Parse sequences into polymers and ligands
    sequences = config.get("sequences", [])
    polymers: List[Dict[str, Any]] = []
    ligands: List[Dict[str, Any]] = []

    for seq_item in sequences:
        if "protein" in seq_item:
            protein = seq_item["protein"]
            polymers.append({
                "molecule_type": "protein",
                "sequence": protein.get("sequence", ""),
                "cyclic": protein.get("cyclic", False),
            })
        elif "rna" in seq_item:
            rna = seq_item["rna"]
            polymers.append({
                "molecule_type": "rna",
                "sequence": rna.get("sequence", ""),
            })
        elif "dna" in seq_item:
            dna = seq_item["dna"]
            polymers.append({
                "molecule_type": "dna",
                "sequence": dna.get("sequence", ""),
            })
        elif "ligand" in seq_item:
            lig = seq_item["ligand"]
            ligand_entry: Dict[str, Any] = {
                "name": lig.get("id", lig.get("name", "ligand")),
            }
            if "smiles" in lig:
                ligand_entry["smiles"] = lig["smiles"]
            elif "ccd" in lig:
                ligand_entry["ccd"] = lig["ccd"]
            ligands.append(ligand_entry)

    if polymers:
        payload["polymers"] = polymers
    if ligands:
        payload["ligands"] = ligands

    # Add optional parameters with defaults
    param_defaults = {
        "recycling_steps": 3,
        "sampling_steps": 50,
        "diffusion_samples": 1,
        "step_scale": 1.638,
        "without_potentials": False,
        "output_format": "mmcif",
        "concatenate_msas": False,
        "sampling_steps_affinity": 200,
        "diffusion_samples_affinity": 5,
        "affinity_mw_correction": False,
    }

    for param, default in param_defaults.items():
        payload[param] = config.get(param, default)

    return payload


def build_payload(
    sequence: str,
    ligand_smiles: str,
    *,
    ligand_name: str = "ligand",
    cyclic: bool = False,
    recycling_steps: int = 3,
    sampling_steps: int = 50,
    diffusion_samples: int = 1,
    step_scale: float = 1.638,
    without_potentials: bool = False,
    output_format: str = "mmcif",
    concatenate_msas: bool = False,
    sampling_steps_affinity: int = 200,
    diffusion_samples_affinity: int = 5,
    affinity_mw_correction: bool = False,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a Boltz-2 prediction payload for protein+ligand.

    Args:
        sequence: Protein amino acid sequence (one-letter codes).
        ligand_smiles: Ligand SMILES string.
        ligand_name: Name for the ligand in output. Defaults to "ligand".
        cyclic: Whether the protein is cyclic. Defaults to False.
        recycling_steps: Number of recycling steps. Defaults to 3.
        sampling_steps: Number of diffusion sampling steps. Defaults to 50.
        diffusion_samples: Number of diffusion samples to generate. Defaults to 1.
        step_scale: Step scale parameter. Defaults to 1.638.
        without_potentials: Disable potential energy terms. Defaults to False.
        output_format: Output format, either "mmcif" or "pdb". Defaults to "mmcif".
        concatenate_msas: Whether to concatenate MSAs. Defaults to False.
        sampling_steps_affinity: Sampling steps for affinity prediction. Defaults to 200.
        diffusion_samples_affinity: Diffusion samples for affinity. Defaults to 5.
        affinity_mw_correction: Apply molecular weight correction to affinity. Defaults to False.
        overrides: Dictionary of additional payload keys to override. Defaults to None.

    Returns:
        Complete payload dictionary ready for API request.

    Example:
        >>> payload = build_payload("MKTAYIAK", "CCO", ligand_name="ethanol")
        >>> payload["polymers"][0]["sequence"]
        'MKTAYIAK'
    """
    payload = {
        "polymers": [
            {
                "molecule_type": "protein",
                "sequence": sequence,
                "cyclic": cyclic,
            }
        ],
        "ligands": [
            {
                "name": ligand_name,
                "smiles": ligand_smiles,
            }
        ],
        "recycling_steps": recycling_steps,
        "sampling_steps": sampling_steps,
        "diffusion_samples": diffusion_samples,
        "step_scale": step_scale,
        "without_potentials": without_potentials,
        "output_format": output_format,
        "concatenate_msas": concatenate_msas,
        "sampling_steps_affinity": sampling_steps_affinity,
        "diffusion_samples_affinity": diffusion_samples_affinity,
        "affinity_mw_correction": affinity_mw_correction,
    }

    if overrides:
        payload.update(overrides)

    return payload


def build_protein_only_payload(
    sequence: str,
    *,
    cyclic: bool = False,
    recycling_steps: int = 3,
    sampling_steps: int = 50,
    diffusion_samples: int = 1,
    step_scale: float = 1.638,
    without_potentials: bool = False,
    output_format: str = "mmcif",
    concatenate_msas: bool = False,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a Boltz-2 prediction payload for protein-only prediction.

    Args:
        sequence: Protein amino acid sequence (one-letter codes).
        cyclic: Whether the protein is cyclic. Defaults to False.
        recycling_steps: Number of recycling steps. Defaults to 3.
        sampling_steps: Number of diffusion sampling steps. Defaults to 50.
        diffusion_samples: Number of diffusion samples to generate. Defaults to 1.
        step_scale: Step scale parameter. Defaults to 1.638.
        without_potentials: Disable potential energy terms. Defaults to False.
        output_format: Output format, either "mmcif" or "pdb". Defaults to "mmcif".
        concatenate_msas: Whether to concatenate MSAs. Defaults to False.
        overrides: Dictionary of additional payload keys to override. Defaults to None.

    Returns:
        Complete payload dictionary ready for API request.

    Example:
        >>> payload = build_protein_only_payload("MKTAYIAK")
        >>> len(payload["polymers"])
        1
    """
    payload = {
        "polymers": [
            {
                "molecule_type": "protein",
                "sequence": sequence,
                "cyclic": cyclic,
            }
        ],
        "recycling_steps": recycling_steps,
        "sampling_steps": sampling_steps,
        "diffusion_samples": diffusion_samples,
        "step_scale": step_scale,
        "without_potentials": without_potentials,
        "output_format": output_format,
        "concatenate_msas": concatenate_msas,
    }

    if overrides:
        payload.update(overrides)

    return payload

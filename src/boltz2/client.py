"""Boltz-2 API client.

This module provides the main client interface for interacting with the
NVIDIA Boltz-2 protein structure prediction API.

Example:
    >>> from boltz2 import Boltz2Client
    >>> client = Boltz2Client()
    >>> result = client.generate_protein_ligand(
    ...     sequence="MKTAYIAKQRQISFVK...",
    ...     ligand_smiles="CCO"
    ... )
    >>> print(result['mmcif'])
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from boltz2.config import Boltz2Config, load_config
from boltz2.io import create_run_directory, save_json, save_mmcif
from boltz2.logging_config import get_logger
from boltz2.parser import extract_all_mmcifs, split_structure_file
from boltz2.payload import build_payload, build_protein_only_payload

logger = get_logger("client")


class Boltz2Client:
    """Client for interacting with the NVIDIA Boltz-2 API.

    This client provides methods for submitting protein structure prediction
    requests to the Boltz-2 API and handling the responses. It supports
    protein-only predictions as well as protein-ligand complex predictions.

    Attributes:
        config: The Boltz2Config instance containing API settings.

    Example:
        >>> # Initialize with environment variable
        >>> client = Boltz2Client()
        >>>
        >>> # Initialize with explicit API key
        >>> client = Boltz2Client(api_key="nvapi-xxx")
        >>>
        >>> # Generate a prediction
        >>> result = client.generate_protein_ligand(
        ...     sequence="MKTAYIAKQRQISFVK...",
        ...     ligand_smiles="CCO"
        ... )
    """

    def __init__(
        self,
        config: Optional[Boltz2Config] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 600,
    ):
        """Initialize the Boltz-2 client.

        Args:
            config: Pre-built config object. Takes precedence over other args.
            api_key: API key for authentication. If not provided, will be
                loaded from BOLTZ2_API_KEY environment variable.
            base_url: API endpoint URL. Defaults to NVIDIA's production API.
            timeout: Request timeout in seconds. Defaults to 600.

        Raises:
            ValueError: If no API key is found in config, parameters, or
                environment variables.

        Example:
            >>> client = Boltz2Client(api_key="nvapi-xxx", timeout=1200)
        """
        if config:
            self.config = config
        else:
            self.config = load_config(api_key=api_key, base_url=base_url, timeout=timeout)
        logger.debug("Boltz2Client initialized with base_url=%s", self.config.base_url)

    def predict(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a prediction request to the API.

        This is the low-level method for submitting requests. For most use
        cases, prefer the higher-level generate_* methods.

        Args:
            payload: Complete request payload as a dictionary. Should include
                'polymers' and optionally 'ligands' keys, plus prediction
                parameters.

        Returns:
            Parsed JSON response from the API containing structure predictions
            and metadata.

        Raises:
            RuntimeError: If the API request fails. The error includes the
                HTTP status code and error message from the API.

        Example:
            >>> payload = {"polymers": [...], "sampling_steps": 50}
            >>> response = client.predict(payload)
        """
        logger.debug("Sending prediction request to %s", self.config.base_url)
        response = requests.post(
            self.config.base_url,
            json=payload,
            headers=self.config.headers,
            timeout=self.config.timeout,
        )

        if not response.ok:
            try:
                err = response.json()
            except Exception:
                err = response.text
            logger.error("API request failed: %s %s", response.status_code, err)
            raise RuntimeError(f"Prediction request failed: {response.status_code} {err}")

        logger.debug("Received successful response from API")
        return response.json()

    def generate_protein_ligand(
        self,
        sequence: str,
        ligand_smiles: str,
        *,
        output_dir: Path = Path("structures"),
        output_name: Optional[str] = None,
        payload_overrides: Optional[Dict[str, Any]] = None,
        split_outputs: bool = False,
    ) -> Dict[str, Any]:
        """Generate a protein+ligand structure prediction.

        Submits a prediction request for a protein-ligand complex and saves
        the resulting structures to disk.

        Args:
            sequence: Protein amino acid sequence in single-letter code.
            ligand_smiles: Ligand structure in SMILES format.
            output_dir: Base directory for output files. Created if it doesn't
                exist. Defaults to 'structures'.
            output_name: Custom name for output files. If not provided, a
                timestamped name is generated.
            payload_overrides: Additional API parameters to override defaults,
                such as 'sampling_steps' or 'diffusion_samples'.
            split_outputs: If True, automatically split outputs into separate
                artifact files (protein-only mmCIF, confidence scores, etc.).

        Returns:
            Dictionary containing:
                - mmcif: Path to first mmCIF file (for backwards compatibility)
                - mmcifs: List of Paths to all mmCIF files (one per sample)
                - json: Path to JSON file containing raw API response
                - dir: Path to the output directory
                - name: The run name used for file naming
                - response: Raw API response dictionary
                - artifacts: Split artifact paths (only if split_outputs=True)

        Raises:
            RuntimeError: If the API request fails.

        Example:
            >>> result = client.generate_protein_ligand(
            ...     sequence="MKTAYIAKQRQISFVK...",
            ...     ligand_smiles="CCO",
            ...     output_dir=Path("./results"),
            ...     split_outputs=True
            ... )
            >>> print(f"Generated {len(result['mmcifs'])} structures")
        """
        # Build payload
        payload = build_payload(
            sequence=sequence,
            ligand_smiles=ligand_smiles,
            overrides=payload_overrides,
        )

        # Create output directory
        run_dir, run_name = create_run_directory(
            base_dir=output_dir,
            output_name=output_name,
            prefix="boltz2_protein_ligand",
        )

        logger.info("Sending predict request to: %s", self.config.base_url)

        # Send request
        response_data = self.predict(payload)

        # Save full JSON response
        json_path = run_dir / f"{run_name}.json"
        save_json(response_data, json_path)

        # Extract and save all mmCIF structures
        mmcif_texts = extract_all_mmcifs(response_data)
        mmcif_paths: List[Path] = []

        if len(mmcif_texts) == 0:
            # No structures found - save empty file for backwards compatibility
            mmcif_path = run_dir / f"{run_name}.mmcif"
            save_mmcif("", mmcif_path)
            mmcif_paths.append(mmcif_path)
        elif len(mmcif_texts) == 1:
            # Single structure - no numbering needed
            mmcif_path = run_dir / f"{run_name}.mmcif"
            save_mmcif(mmcif_texts[0], mmcif_path)
            mmcif_paths.append(mmcif_path)
        else:
            # Multiple structures - number them
            for i, mmcif_text in enumerate(mmcif_texts, start=1):
                mmcif_path = run_dir / f"{run_name}_{i}.mmcif"
                save_mmcif(mmcif_text, mmcif_path)
                mmcif_paths.append(mmcif_path)

        logger.info("Saved outputs -> dir: %s, mmCIF files: %d, JSON: %s",
                    run_dir, len(mmcif_paths), json_path.name)
        for p in mmcif_paths:
            logger.debug("  - %s", p.name)

        result = {
            "mmcif": mmcif_paths[0],  # First structure for backwards compatibility
            "mmcifs": mmcif_paths,    # All structures
            "json": json_path,
            "dir": run_dir,
            "name": run_name,
            "response": response_data,
        }

        # Optionally split outputs (for all structures)
        if split_outputs and mmcif_texts:
            all_artifacts: Dict[str, Any] = {}
            for i, mmcif_path in enumerate(mmcif_paths, start=1):
                artifacts = split_structure_file(mmcif_path)
                if len(mmcif_paths) == 1:
                    all_artifacts.update(artifacts)
                else:
                    all_artifacts[f"sample_{i}"] = artifacts
            result["artifacts"] = all_artifacts

        return result

    def generate_from_payload(
        self,
        payload: Dict[str, Any],
        *,
        output_dir: Path = Path("structures"),
        output_name: Optional[str] = None,
        split_outputs: bool = False,
    ) -> Dict[str, Any]:
        """Generate a structure prediction from a pre-built payload.

        This method is useful when loading configuration from a YAML file
        or when you need full control over the API payload.

        Args:
            payload: Complete API payload dictionary. Should contain 'polymers'
                and optionally 'ligands' keys, plus any prediction parameters.
            output_dir: Base directory for output files. Created if it doesn't
                exist. Defaults to 'structures'.
            output_name: Custom name for output files. If not provided, a
                timestamped name is generated.
            split_outputs: If True, automatically split outputs into separate
                artifact files (protein-only mmCIF, confidence scores, etc.).

        Returns:
            Dictionary containing:
                - mmcif: Path to first mmCIF file (for backwards compatibility)
                - mmcifs: List of Paths to all mmCIF files (one per sample)
                - json: Path to JSON file containing raw API response
                - dir: Path to the output directory
                - name: The run name used for file naming
                - response: Raw API response dictionary
                - artifacts: Split artifact paths (only if split_outputs=True)

        Raises:
            RuntimeError: If the API request fails.

        Example:
            >>> from boltz2.payload import load_payload_from_yaml
            >>> payload = load_payload_from_yaml("input.yaml")
            >>> result = client.generate_from_payload(payload, split_outputs=True)
        """
        # Create output directory
        run_dir, run_name = create_run_directory(
            base_dir=output_dir,
            output_name=output_name,
            prefix="boltz2",
        )

        logger.info("Sending predict request to: %s", self.config.base_url)

        # Send request
        response_data = self.predict(payload)

        # Save full JSON response
        json_path = run_dir / f"{run_name}.json"
        save_json(response_data, json_path)

        # Extract and save all mmCIF structures
        mmcif_texts = extract_all_mmcifs(response_data)
        mmcif_paths: List[Path] = []

        if len(mmcif_texts) == 0:
            # No structures found - save empty file for backwards compatibility
            mmcif_path = run_dir / f"{run_name}.mmcif"
            save_mmcif("", mmcif_path)
            mmcif_paths.append(mmcif_path)
        elif len(mmcif_texts) == 1:
            # Single structure - no numbering needed
            mmcif_path = run_dir / f"{run_name}.mmcif"
            save_mmcif(mmcif_texts[0], mmcif_path)
            mmcif_paths.append(mmcif_path)
        else:
            # Multiple structures - number them
            for i, mmcif_text in enumerate(mmcif_texts, start=1):
                mmcif_path = run_dir / f"{run_name}_{i}.mmcif"
                save_mmcif(mmcif_text, mmcif_path)
                mmcif_paths.append(mmcif_path)

        logger.info("Saved outputs -> dir: %s, mmCIF files: %d, JSON: %s",
                    run_dir, len(mmcif_paths), json_path.name)
        for p in mmcif_paths:
            logger.debug("  - %s", p.name)

        result = {
            "mmcif": mmcif_paths[0],  # First structure for backwards compatibility
            "mmcifs": mmcif_paths,    # All structures
            "json": json_path,
            "dir": run_dir,
            "name": run_name,
            "response": response_data,
        }

        # Optionally split outputs (for all structures)
        if split_outputs and mmcif_texts:
            all_artifacts: Dict[str, Any] = {}
            for i, mmcif_path in enumerate(mmcif_paths, start=1):
                artifacts = split_structure_file(mmcif_path)
                if len(mmcif_paths) == 1:
                    all_artifacts.update(artifacts)
                else:
                    all_artifacts[f"sample_{i}"] = artifacts
            result["artifacts"] = all_artifacts

        return result

    def generate_protein(
        self,
        sequence: str,
        *,
        output_dir: Path = Path("structures"),
        output_name: Optional[str] = None,
        payload_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a protein-only structure prediction.

        Submits a prediction request for a single protein without any ligands.

        Args:
            sequence: Protein amino acid sequence in single-letter code.
            output_dir: Base directory for output files. Created if it doesn't
                exist. Defaults to 'structures'.
            output_name: Custom name for output files. If not provided, a
                timestamped name is generated.
            payload_overrides: Additional API parameters to override defaults,
                such as 'sampling_steps' or 'diffusion_samples'.

        Returns:
            Dictionary containing:
                - mmcif: Path to first mmCIF file (for backwards compatibility)
                - mmcifs: List of Paths to all mmCIF files (one per sample)
                - json: Path to JSON file containing raw API response
                - dir: Path to the output directory
                - name: The run name used for file naming
                - response: Raw API response dictionary

        Raises:
            RuntimeError: If the API request fails.

        Example:
            >>> result = client.generate_protein(
            ...     sequence="MKTAYIAKQRQISFVK...",
            ...     output_dir=Path("./results")
            ... )
        """
        # Build payload
        payload = build_protein_only_payload(
            sequence=sequence,
            overrides=payload_overrides,
        )

        # Create output directory
        run_dir, run_name = create_run_directory(
            base_dir=output_dir,
            output_name=output_name,
            prefix="boltz2_protein",
        )

        logger.info("Sending predict request to: %s", self.config.base_url)

        # Send request
        response_data = self.predict(payload)

        # Save full JSON response
        json_path = run_dir / f"{run_name}.json"
        save_json(response_data, json_path)

        # Extract and save all mmCIF structures
        mmcif_texts = extract_all_mmcifs(response_data)
        mmcif_paths: List[Path] = []

        if len(mmcif_texts) == 0:
            # No structures found - save empty file for backwards compatibility
            mmcif_path = run_dir / f"{run_name}.mmcif"
            save_mmcif("", mmcif_path)
            mmcif_paths.append(mmcif_path)
        elif len(mmcif_texts) == 1:
            # Single structure - no numbering needed
            mmcif_path = run_dir / f"{run_name}.mmcif"
            save_mmcif(mmcif_texts[0], mmcif_path)
            mmcif_paths.append(mmcif_path)
        else:
            # Multiple structures - number them
            for i, mmcif_text in enumerate(mmcif_texts, start=1):
                mmcif_path = run_dir / f"{run_name}_{i}.mmcif"
                save_mmcif(mmcif_text, mmcif_path)
                mmcif_paths.append(mmcif_path)

        logger.info("Saved outputs -> dir: %s, mmCIF files: %d, JSON: %s",
                    run_dir, len(mmcif_paths), json_path.name)
        for p in mmcif_paths:
            logger.debug("  - %s", p.name)

        return {
            "mmcif": mmcif_paths[0],  # First structure for backwards compatibility
            "mmcifs": mmcif_paths,    # All structures
            "json": json_path,
            "dir": run_dir,
            "name": run_name,
            "response": response_data,
        }

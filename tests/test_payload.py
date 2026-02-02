"""Tests for boltz2.payload module."""

import pytest

from boltz2.payload import build_payload, build_protein_only_payload, build_payload_from_config


class TestBuildPayload:
    def test_basic_payload(self):
        payload = build_payload(
            sequence="MGDVEKGKKIVGAVIL",
            ligand_smiles="C1=CC=C(C=C1)C(=O)N",
        )

        assert payload["polymers"][0]["sequence"] == "MGDVEKGKKIVGAVIL"
        assert payload["polymers"][0]["molecule_type"] == "protein"
        assert payload["ligands"][0]["smiles"] == "C1=CC=C(C=C1)C(=O)N"
        assert payload["output_format"] == "mmcif"

    def test_custom_ligand_name(self):
        payload = build_payload(
            sequence="ACDEF",
            ligand_smiles="CCO",
            ligand_name="ethanol",
        )
        assert payload["ligands"][0]["name"] == "ethanol"

    def test_overrides(self):
        payload = build_payload(
            sequence="ACDEF",
            ligand_smiles="CCO",
            overrides={"sampling_steps": 100, "custom_key": "value"},
        )
        assert payload["sampling_steps"] == 100
        assert payload["custom_key"] == "value"

    def test_cyclic_protein(self):
        payload = build_payload(
            sequence="ACDEF",
            ligand_smiles="CCO",
            cyclic=True,
        )
        assert payload["polymers"][0]["cyclic"] is True


class TestBuildProteinOnlyPayload:
    def test_basic_payload(self):
        payload = build_protein_only_payload(sequence="MGDVEKGKKIVGAVIL")

        assert payload["polymers"][0]["sequence"] == "MGDVEKGKKIVGAVIL"
        assert "ligands" not in payload

    def test_overrides(self):
        payload = build_protein_only_payload(
            sequence="ACDEF",
            overrides={"recycling_steps": 5},
        )
        assert payload["recycling_steps"] == 5


class TestBuildPayloadFromConfig:
    def test_protein_ligand_config(self):
        config = {
            "sequences": [
                {"protein": {"id": "A", "sequence": "MGDVEKGKKIVGAVIL"}},
                {"ligand": {"id": "B", "smiles": "CCO"}},
            ]
        }
        payload = build_payload_from_config(config)

        assert len(payload["polymers"]) == 1
        assert payload["polymers"][0]["sequence"] == "MGDVEKGKKIVGAVIL"
        assert len(payload["ligands"]) == 1
        assert payload["ligands"][0]["smiles"] == "CCO"

    def test_protein_only_config(self):
        config = {
            "sequences": [
                {"protein": {"id": "A", "sequence": "ACDEF"}},
            ]
        }
        payload = build_payload_from_config(config)

        assert len(payload["polymers"]) == 1
        assert "ligands" not in payload or len(payload["ligands"]) == 0

    def test_multi_chain_config(self):
        config = {
            "sequences": [
                {"protein": {"id": "A", "sequence": "MGDVEK"}},
                {"protein": {"id": "B", "sequence": "ACDEF"}},
                {"ligand": {"id": "C", "smiles": "CCO"}},
            ]
        }
        payload = build_payload_from_config(config)

        assert len(payload["polymers"]) == 2
        assert len(payload["ligands"]) == 1

    def test_custom_parameters(self):
        config = {
            "sequences": [
                {"protein": {"id": "A", "sequence": "ACDEF"}},
            ],
            "sampling_steps": 100,
            "recycling_steps": 5,
        }
        payload = build_payload_from_config(config)

        assert payload["sampling_steps"] == 100
        assert payload["recycling_steps"] == 5

    def test_ligand_with_ccd(self):
        config = {
            "sequences": [
                {"protein": {"id": "A", "sequence": "ACDEF"}},
                {"ligand": {"id": "B", "ccd": "ATP"}},
            ]
        }
        payload = build_payload_from_config(config)

        assert payload["ligands"][0]["ccd"] == "ATP"
        assert "smiles" not in payload["ligands"][0]

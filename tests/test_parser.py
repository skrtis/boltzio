"""Tests for boltz2.parser module."""

import json
import pytest

from boltz2.parser import (
    extract_all_mmcifs,
    extract_confidence_data,
    extract_affinity_data,
    extract_matrix_data,
    split_structure_file,
)


class TestExtractAllMmcifs:
    def test_from_dict_with_single_structure(self):
        response = {
            "structures": [
                {"structure": "data_test\n_entry.id test\nATOM 1 CA"}
            ]
        }
        result = extract_all_mmcifs(response)
        assert len(result) == 1
        assert result[0] == "data_test\n_entry.id test\nATOM 1 CA"

    def test_from_dict_with_multiple_structures(self):
        response = {
            "structures": [
                {"structure": "data_test1\n_entry.id test1"},
                {"structure": "data_test2\n_entry.id test2"},
                {"structure": "data_test3\n_entry.id test3"},
            ]
        }
        result = extract_all_mmcifs(response)
        assert len(result) == 3
        assert result[0] == "data_test1\n_entry.id test1"
        assert result[1] == "data_test2\n_entry.id test2"
        assert result[2] == "data_test3\n_entry.id test3"

    def test_from_dict_without_structures(self):
        response = {"other_key": "value"}
        result = extract_all_mmcifs(response)
        assert result == []

    def test_from_raw_mmcif_string(self):
        mmcif_text = "data_test\n_entry.id test"
        result = extract_all_mmcifs(mmcif_text)
        assert len(result) == 1
        assert result[0] == mmcif_text

    def test_from_json_string(self):
        response = {"structures": [{"structure": "data_test"}]}
        json_str = json.dumps(response)
        result = extract_all_mmcifs(json_str)
        assert len(result) == 1
        assert result[0] == "data_test"


class TestExtractConfidenceData:
    def test_extracts_present_keys(self):
        response = {
            "confidence_scores": [0.9, 0.8],
            "ptm_scores": 0.85,
            "other_key": "ignored",
        }
        result = extract_confidence_data(response)
        assert "confidence_scores" in result
        assert "ptm_scores" in result
        assert "other_key" not in result

    def test_empty_response(self):
        result = extract_confidence_data({})
        assert result == {}


class TestExtractAffinityData:
    def test_present(self):
        response = {"affinities": [{"value": -7.5}]}
        result = extract_affinity_data(response)
        assert result == [{"value": -7.5}]

    def test_absent(self):
        response = {"other": "data"}
        result = extract_affinity_data(response)
        assert result is None


class TestExtractMatrixData:
    def test_extracts_matrices(self):
        response = {
            "pair_chains_iptm_scores": [[0.9, 0.8], [0.8, 0.9]],
            "other_key": "ignored",
        }
        result = extract_matrix_data(response)
        assert "pair_chains_iptm_scores" in result
        assert "other_key" not in result


class TestSplitStructureFile:
    def test_mmcif_input_does_not_write_another_full_mmcif(self, tmp_path):
        input_path = tmp_path / "prod-PDE3A-ensifentrine.mmcif"
        input_path.write_text(
            "data_test\nATOM 1 CA ALA A 1\nHETATM 2 C1 LIG L 1\n",
            encoding="utf-8",
        )

        artifacts = split_structure_file(input_path)

        # Existing mmCIF should be reused, not recreated.
        assert artifacts["mmcif"] == input_path

        protein_path = tmp_path / "prod-PDE3A-ensifentrine_protein.mmcif"
        assert artifacts["protein_mmcif"] == protein_path
        assert protein_path.exists()
        assert "HETATM" not in protein_path.read_text(encoding="utf-8")

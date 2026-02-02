"""Tests for boltz2.utils module."""

import pytest

from boltz2.utils import sanitize_name, generate_run_name


class TestSanitizeName:
    def test_basic_name(self):
        assert sanitize_name("my_protein") == "my_protein"

    def test_spaces_replaced(self):
        assert sanitize_name("my protein name") == "my_protein_name"

    def test_special_chars_removed(self):
        assert sanitize_name("protein@#$%test") == "proteintest"

    def test_keeps_allowed_chars(self):
        assert sanitize_name("protein-1_v2.0") == "protein-1_v2.0"

    def test_strips_whitespace(self):
        assert sanitize_name("  protein  ") == "protein"

    def test_empty_string(self):
        assert sanitize_name("") == ""

    def test_only_special_chars(self):
        assert sanitize_name("@#$%") == ""


class TestGenerateRunName:
    def test_with_output_name(self):
        result = generate_run_name(output_name="my_run")
        assert result == "my_run"

    def test_with_output_name_sanitized(self):
        result = generate_run_name(output_name="my run@test")
        assert result == "my_runtest"

    def test_without_output_name_uses_prefix(self):
        result = generate_run_name(prefix="test_prefix")
        assert result.startswith("test_prefix_")

    def test_empty_output_name_falls_back(self):
        result = generate_run_name(prefix="fallback", output_name="")
        assert result.startswith("fallback_")

    def test_special_chars_only_falls_back(self):
        result = generate_run_name(prefix="fallback", output_name="@#$%")
        assert result.startswith("fallback_")

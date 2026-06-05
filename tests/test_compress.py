"""Tests for pdf_tools.compress."""
from __future__ import annotations

from pathlib import Path

import pytest

from pdf_tools.compress import compress, PRESETS
from pdf_tools.utils.file_helpers import OUTPUT_SUBDIR


class TestCompress:
    def test_output_file_created(self, single_pdf, tmp_path):
        compress([single_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert list(out_dir.glob("*.pdf"))

    def test_output_is_valid_pdf(self, single_pdf, tmp_path):
        compress([single_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("*.pdf"))
        assert output.read_bytes()[:4] == b"%PDF"

    def test_light_preset_default(self, single_pdf, tmp_path):
        """Default level is 'light'; should not raise."""
        compress([single_pdf], overwrite=True, level="light")
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert list(out_dir.glob("*.pdf"))

    def test_aggressive_preset(self, single_pdf, tmp_path):
        compress([single_pdf], overwrite=True, level="aggressive")
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert list(out_dir.glob("*.pdf"))

    def test_unknown_level_falls_back_to_light(self, single_pdf, tmp_path):
        """An unrecognised level should not crash (falls back to 'light')."""
        compress([single_pdf], overwrite=True, level="nonexistent_level")
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert list(out_dir.glob("*.pdf"))

    def test_multiple_inputs(self, multi_pdfs, tmp_path):
        compress(multi_pdfs, overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf"))
        assert len(outputs) == 3

    def test_corrupt_pdf_skipped(self, tmp_path):
        corrupt = tmp_path / "bad.pdf"
        corrupt.write_bytes(b"this is not a pdf")
        compress([corrupt], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf")) if out_dir.exists() else []
        assert outputs == []

    def test_overwrite_false_increments(self, single_pdf, tmp_path):
        compress([single_pdf], overwrite=False)
        compress([single_pdf], overwrite=False)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf"))
        assert len(outputs) == 2

    def test_presets_dict_has_required_keys(self):
        for level, preset in PRESETS.items():
            assert "compress_streams" in preset
            assert "object_stream_mode" in preset
            assert "recompress_flate" in preset

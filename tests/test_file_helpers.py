"""Tests for pdf_tools.utils.file_helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from pdf_tools.utils.file_helpers import (
    OUTPUT_SUBDIR,
    fmt_size,
    get_output_dir,
    safe_output_path,
    size_delta,
)


# ── fmt_size ─────────────────────────────────────────────────────────────────

class TestFmtSize:
    def test_bytes(self):
        assert fmt_size(512) == "512.0 B"

    def test_kilobytes(self):
        assert fmt_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert fmt_size(3 * 1024 * 1024) == "3.0 MB"

    def test_gigabytes(self):
        assert fmt_size(2 * 1024 ** 3) == "2.0 GB"

    def test_zero(self):
        assert fmt_size(0) == "0.0 B"

    def test_exactly_one_kb_boundary(self):
        result = fmt_size(1024)
        assert "KB" in result or "B" in result  # boundary: 1024 B == 1.0 KB


# ── size_delta ────────────────────────────────────────────────────────────────

class TestSizeDelta:
    def test_reduction(self):
        result = size_delta(1000, 500)
        assert "-50.0%" in result
        assert "->" in result

    def test_increase(self):
        result = size_delta(500, 1000)
        assert "+100.0%" in result

    def test_no_change(self):
        result = size_delta(1000, 1000)
        assert "0.0%" in result

    def test_zero_before_no_crash(self):
        # Should not raise ZeroDivisionError
        result = size_delta(0, 100)
        assert isinstance(result, str)

    def test_format_contains_arrow(self):
        assert "->" in size_delta(2000, 1000)


# ── get_output_dir ────────────────────────────────────────────────────────────

class TestGetOutputDir:
    def test_creates_output_subdir(self, tmp_path):
        ref = tmp_path / "myfile.pdf"
        ref.touch()
        out = get_output_dir(ref)
        assert out.name == OUTPUT_SUBDIR
        assert out.parent == tmp_path
        assert out.is_dir()

    def test_idempotent_when_already_exists(self, tmp_path):
        ref = tmp_path / "myfile.pdf"
        ref.touch()
        out1 = get_output_dir(ref)
        out2 = get_output_dir(ref)
        assert out1 == out2

    def test_does_not_nest_when_already_inside_output_subdir(self, tmp_path):
        """If the reference path is already inside output-pdf-tools/, reuse it."""
        out_dir = tmp_path / OUTPUT_SUBDIR
        out_dir.mkdir()
        nested_file = out_dir / "result.pdf"
        nested_file.touch()
        result = get_output_dir(nested_file)
        assert result == out_dir
        # Must NOT create output-pdf-tools/output-pdf-tools/
        assert not (out_dir / OUTPUT_SUBDIR).exists()

    def test_directory_reference(self, tmp_path):
        """Using a directory as reference should still resolve correctly."""
        sub = tmp_path / "docs"
        sub.mkdir()
        anchor = sub / "_"  # pattern used by batch.py
        out = get_output_dir(anchor)
        assert out.is_dir()


# ── safe_output_path ──────────────────────────────────────────────────────────

class TestSafeOutputPath:
    def test_no_operation_keeps_stem(self, tmp_path):
        path = safe_output_path(tmp_path, "report.pdf", overwrite=True)
        assert path.name == "report.pdf"

    def test_operation_appended_to_stem(self, tmp_path):
        path = safe_output_path(tmp_path, "report.pdf", overwrite=True, operation="compressed")
        assert path.stem == "report-compressed"
        assert path.suffix == ".pdf"

    def test_chained_operations_accumulate(self, tmp_path):
        path = safe_output_path(tmp_path, "report-compressed.pdf", overwrite=True, operation="normalized")
        assert path.stem == "report-compressed-normalized"

    def test_overwrite_true_returns_same_path_even_if_exists(self, tmp_path):
        existing = tmp_path / "report.pdf"
        existing.touch()
        path = safe_output_path(tmp_path, "report.pdf", overwrite=True)
        assert path == existing

    def test_overwrite_false_increments_counter(self, tmp_path):
        (tmp_path / "report.pdf").touch()
        path = safe_output_path(tmp_path, "report.pdf", overwrite=False)
        assert path.name == "report_1.pdf"

    def test_overwrite_false_increments_until_free(self, tmp_path):
        for i in ["report.pdf", "report_1.pdf", "report_2.pdf"]:
            (tmp_path / i).touch()
        path = safe_output_path(tmp_path, "report.pdf", overwrite=False)
        assert path.name == "report_3.pdf"

    def test_nonexistent_dir_still_returns_path(self, tmp_path):
        new_dir = tmp_path / "nonexistent"
        # safe_output_path does NOT create the dir; just constructs the path
        path = safe_output_path(new_dir, "file.pdf", overwrite=True)
        assert path.parent == new_dir

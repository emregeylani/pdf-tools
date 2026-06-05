"""Tests for pdf_tools.normalize."""
from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from pdf_tools.normalize import normalize, A4_W, A4_H
from pdf_tools.utils.file_helpers import OUTPUT_SUBDIR


def _read_page_size(path: Path, page_idx: int = 0) -> tuple[float, float]:
    reader = PdfReader(str(path))
    page = reader.pages[page_idx]
    return float(page.mediabox.width), float(page.mediabox.height)


class TestNormalize:
    def test_portrait_page_becomes_a4(self, single_pdf, tmp_path):
        normalize([single_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("*normalized*"))
        w, h = _read_page_size(output)
        assert abs(w - A4_W) < 1
        assert abs(h - A4_H) < 1

    def test_landscape_page_becomes_landscape_a4(self, landscape_pdf, tmp_path):
        normalize([landscape_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("*normalized*"))
        w, h = _read_page_size(output)
        # Landscape A4: width should be the longer dimension
        assert w > h
        assert abs(w - A4_H) < 1
        assert abs(h - A4_W) < 1

    def test_page_count_preserved(self, two_page_pdf, tmp_path):
        normalize([two_page_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("*normalized*"))
        assert len(PdfReader(str(output)).pages) == 2

    def test_output_filename_contains_normalized(self, single_pdf, tmp_path):
        normalize([single_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.iterdir())
        assert any("normalized" in f.name for f in outputs)

    def test_multiple_inputs_each_normalized(self, multi_pdfs, tmp_path):
        normalize(multi_pdfs, overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*normalized*"))
        assert len(outputs) == 3

    def test_corrupt_pdf_skipped(self, tmp_path):
        corrupt = tmp_path / "bad.pdf"
        corrupt.write_bytes(b"not a pdf")
        normalize([corrupt], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*normalized*")) if out_dir.exists() else []
        assert outputs == []

    def test_overwrite_false_increments(self, single_pdf, tmp_path):
        normalize([single_pdf], overwrite=False)
        normalize([single_pdf], overwrite=False)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*normalized*"))
        assert len(outputs) == 2

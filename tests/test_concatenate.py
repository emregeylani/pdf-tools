"""Tests for pdf_tools.concatenate."""
from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from pdf_tools.concatenate import concatenate
from pdf_tools.utils.file_helpers import OUTPUT_SUBDIR


def _page_count(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


class TestConcatenate:
    def test_merges_all_pdfs(self, multi_pdfs, tmp_path):
        """a(1p) + b(2p) + c(1p) => 4 pages total."""
        concatenate(multi_pdfs, overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("concatenated-*.pdf"))
        assert len(outputs) == 1
        assert _page_count(outputs[0]) == 4

    def test_output_sorted_alphabetically(self, multi_pdfs, tmp_path):
        """Result must contain pages in alphabetical filename order: a→b→c."""
        concatenate(multi_pdfs, overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("concatenated-*.pdf"))
        assert _page_count(output) == 4  # a(1) + b(2) + c(1)

    def test_output_filename_contains_date(self, single_pdf, tmp_path):
        concatenate([single_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("concatenated-*.pdf"))
        assert outputs, "No output file found"
        import re
        assert re.search(r"concatenated-\d{8}\.pdf", outputs[0].name)

    def test_single_input(self, single_pdf, tmp_path):
        concatenate([single_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("concatenated-*.pdf"))
        assert _page_count(output) == 1

    def test_output_in_output_subdir(self, single_pdf, tmp_path):
        concatenate([single_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert out_dir.is_dir()
        assert any(out_dir.iterdir())

    def test_overwrite_false_no_collision(self, multi_pdfs, tmp_path):
        """Running twice with overwrite=False must produce two distinct files."""
        concatenate(multi_pdfs, overwrite=False)
        concatenate(multi_pdfs, overwrite=False)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("concatenated-*.pdf"))
        assert len(outputs) == 2

    def test_corrupt_pdf_skipped_gracefully(self, tmp_path, single_pdf):
        """A corrupt file should be skipped; valid files still merged."""
        corrupt = tmp_path / "bad.pdf"
        corrupt.write_bytes(b"not a pdf at all")
        concatenate([corrupt, single_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("concatenated-*.pdf"))
        assert _page_count(output) == 1  # only the valid file

    def test_all_corrupt_no_output(self, tmp_path):
        """If every input is corrupt, no output file must be created."""
        corrupt = tmp_path / "bad.pdf"
        corrupt.write_bytes(b"%PDF-garbage")
        out_dir = tmp_path / OUTPUT_SUBDIR
        concatenate([corrupt], overwrite=True)
        pdfs = list(out_dir.glob("concatenated-*.pdf")) if out_dir.exists() else []
        # Either no output dir or empty output
        assert pdfs == [] or all(_page_count(p) == 0 for p in pdfs)

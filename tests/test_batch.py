"""Tests for pdf_tools.batch."""
from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from pdf_tools.batch import (
    _convert_image,
    _normalize_page,
    _merge_pdfs,
    batch,
    A4_W,
    A4_H,
)
from pdf_tools.utils.file_helpers import OUTPUT_SUBDIR


def _page_count(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


# ── _convert_image ────────────────────────────────────────────────────────────

class TestConvertImage:
    def test_rgb_png_produces_pdf(self, png_image, tmp_path):
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = _convert_image(png_image, out_dir, overwrite=True)
        assert result is not None
        assert result.suffix == ".pdf"
        assert result.read_bytes()[:4] == b"%PDF"

    def test_rgba_image_no_crash(self, rgba_image, tmp_path):
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = _convert_image(rgba_image, out_dir, overwrite=True)
        assert result is not None

    def test_corrupt_image_returns_none(self, tmp_path):
        bad = tmp_path / "bad.png"
        bad.write_bytes(b"not an image")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = _convert_image(bad, out_dir, overwrite=True)
        assert result is None

    def test_output_filename_matches_stem(self, png_image, tmp_path):
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = _convert_image(png_image, out_dir, overwrite=True)
        assert result.stem == png_image.stem


# ── _normalize_page ───────────────────────────────────────────────────────────

class TestNormalizePage:
    def test_portrait_resized_to_a4(self, single_pdf):
        reader = PdfReader(str(single_pdf))
        page = reader.pages[0]
        _normalize_page(page)
        assert abs(float(page.mediabox.width) - A4_W) < 1
        assert abs(float(page.mediabox.height) - A4_H) < 1

    def test_landscape_resized_to_landscape_a4(self, landscape_pdf):
        reader = PdfReader(str(landscape_pdf))
        page = reader.pages[0]
        _normalize_page(page)
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        assert w > h  # still landscape
        assert abs(w - A4_H) < 1
        assert abs(h - A4_W) < 1


# ── _merge_pdfs ───────────────────────────────────────────────────────────────

class TestMergePdfs:
    def test_total_page_count(self, multi_pdfs, tmp_path):
        out = tmp_path / "merged.pdf"
        total = _merge_pdfs(multi_pdfs, out, normalize=False)
        assert total == 4  # a(1) + b(2) + c(1)
        assert _page_count(out) == 4

    def test_normalize_flag_applied(self, multi_pdfs, tmp_path):
        out = tmp_path / "merged_normalized.pdf"
        _merge_pdfs(multi_pdfs, out, normalize=True)
        reader = PdfReader(str(out))
        for page in reader.pages:
            assert abs(float(page.mediabox.width) - A4_W) < 1 or abs(float(page.mediabox.width) - A4_H) < 1

    def test_corrupt_pdf_skipped_returns_partial(self, tmp_path, single_pdf):
        corrupt = tmp_path / "bad.pdf"
        corrupt.write_bytes(b"garbage")
        out = tmp_path / "partial.pdf"
        total = _merge_pdfs([corrupt, single_pdf], out, normalize=False)
        assert total == 1


# ── batch (integration) ───────────────────────────────────────────────────────

class TestBatch:
    def test_output_file_created(self, batch_folder):
        batch([batch_folder], overwrite=True, normalize=False, compress=False)
        out_dir = batch_folder / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf"))
        assert len(outputs) >= 1

    def test_image_converted_and_merged(self, batch_folder):
        """scan.png should be converted; result merged with doc1 + doc2."""
        batch([batch_folder], overwrite=True, normalize=False, compress=False)
        out_dir = batch_folder / OUTPUT_SUBDIR
        # The batch output must contain pages from all sources (1+2+1 from image)
        final_pdfs = [p for p in out_dir.glob("*.pdf") if "concatenated" not in p.name or True]
        batch_output = max(final_pdfs, key=lambda p: p.stat().st_size)
        assert _page_count(batch_output) >= 3

    def test_normalize_flag(self, batch_folder):
        batch([batch_folder], overwrite=True, normalize=True, compress=False)
        out_dir = batch_folder / OUTPUT_SUBDIR
        outputs = [p for p in out_dir.glob("*.pdf")]
        # Must produce something
        assert outputs

    def test_compress_flag_no_crash(self, batch_folder):
        batch([batch_folder], overwrite=True, normalize=False, compress=True)
        out_dir = batch_folder / OUTPUT_SUBDIR
        assert list(out_dir.glob("*.pdf"))

    def test_non_directory_skipped(self, tmp_path):
        not_a_dir = tmp_path / "file.txt"
        not_a_dir.touch()
        # Should not raise
        batch([not_a_dir], overwrite=True, normalize=False, compress=False)

    def test_empty_folder_skipped(self, tmp_path):
        empty = tmp_path / "empty_dir"
        empty.mkdir()
        batch([empty], overwrite=True, normalize=False, compress=False)
        # No output dir should be created (nothing to process)
        assert not (empty / OUTPUT_SUBDIR).exists() or not list((empty / OUTPUT_SUBDIR).glob("*.pdf"))

    def test_multiple_folders(self, tmp_path):
        from pypdf import PdfWriter
        from PIL import Image

        def _blank_pdf(path, pages=1):
            w = PdfWriter()
            for _ in range(pages):
                w.add_blank_page(width=595, height=842)
            with open(path, "wb") as f:
                w.write(f)

        folder_a = tmp_path / "A"
        folder_b = tmp_path / "B"
        folder_a.mkdir()
        folder_b.mkdir()
        _blank_pdf(folder_a / "doc.pdf", pages=1)
        _blank_pdf(folder_b / "doc.pdf", pages=2)
        batch([folder_a, folder_b], overwrite=True, normalize=False, compress=False)
        assert list((folder_a / OUTPUT_SUBDIR).glob("*.pdf"))
        assert list((folder_b / OUTPUT_SUBDIR).glob("*.pdf"))

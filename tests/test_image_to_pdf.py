"""Tests for pdf_tools.image_to_pdf."""
from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from pdf_tools.image_to_pdf import image_to_pdf, SUPPORTED
from pdf_tools.utils.file_helpers import OUTPUT_SUBDIR


def _is_valid_pdf(path: Path) -> bool:
    return path.read_bytes()[:4] == b"%PDF"


class TestImageToPdf:
    def test_png_converted(self, png_image, tmp_path):
        image_to_pdf([png_image], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf"))
        assert len(outputs) == 1
        assert _is_valid_pdf(outputs[0])

    def test_jpeg_converted(self, jpeg_image, tmp_path):
        image_to_pdf([jpeg_image], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf"))
        assert len(outputs) == 1

    def test_bmp_converted(self, bmp_image, tmp_path):
        image_to_pdf([bmp_image], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert list(out_dir.glob("*.pdf"))

    def test_rgba_image_no_crash(self, rgba_image, tmp_path):
        """RGBA images must be flattened to RGB before saving."""
        image_to_pdf([rgba_image], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf"))
        assert len(outputs) == 1

    def test_output_filename_matches_stem(self, png_image, tmp_path):
        image_to_pdf([png_image], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("*.pdf"))
        assert output.stem == png_image.stem

    def test_unsupported_format_skipped(self, tmp_path):
        tiff = tmp_path / "image.tiff"
        from PIL import Image
        Image.new("RGB", (50, 50)).save(str(tiff), "TIFF")
        image_to_pdf([tiff], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf")) if out_dir.exists() else []
        assert outputs == []

    def test_output_is_single_page(self, png_image, tmp_path):
        image_to_pdf([png_image], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("*.pdf"))
        assert len(PdfReader(str(output)).pages) == 1

    def test_multiple_images_produce_multiple_pdfs(self, png_image, jpeg_image, tmp_path):
        image_to_pdf([png_image, jpeg_image], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf"))
        assert len(outputs) == 2

    def test_supported_set_contains_expected_formats(self):
        assert ".png" in SUPPORTED
        assert ".jpg" in SUPPORTED
        assert ".jpeg" in SUPPORTED
        assert ".bmp" in SUPPORTED

    def test_corrupt_image_skipped(self, tmp_path):
        bad = tmp_path / "bad.png"
        bad.write_bytes(b"not an image")
        image_to_pdf([bad], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*.pdf")) if out_dir.exists() else []
        assert outputs == []

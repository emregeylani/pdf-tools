"""Tests for pdf_tools.ocr.

EasyOCR ve pdf2image mock'lanır — model indirmez, poppler gerektirmez.
"""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from pdf_tools.ocr import (
    _build_text_overlay,
    _is_image_only,
    ocr,
    DEFAULT_LANGS,
    RASTER_DPI,
)
from pdf_tools.utils.file_helpers import OUTPUT_SUBDIR


# ── helpers ───────────────────────────────────────────────────────────────────

def _blank_image(w: int = 200, h: int = 300) -> Image.Image:
    return Image.new("RGB", (w, h), color=(255, 255, 255))


def _fake_ocr_result(text: str = "Merhaba", x1=10, y1=10, x2=100, y2=40):
    bbox = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
    return [bbox, text, 0.95]


def _make_image_only_pdf(path: Path, pages: int = 1) -> Path:
    """Blank PDF — no extractable text, simulates a scanned document."""
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(595, 842)
    with open(path, "wb") as f:
        w.write(f)
    return path


def _make_text_pdf(path: Path) -> Path:
    """PDF with extractable text layer (reportlab)."""
    from reportlab.pdfgen import canvas as rl_canvas
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(595, 842))
    c.setFont("Helvetica", 12)
    c.drawString(100, 700, "Hello World")
    c.save()
    buf.seek(0)
    path.write_bytes(buf.getvalue())
    return path


# ── _is_image_only ────────────────────────────────────────────────────────────

class TestIsImageOnly:

    def test_blank_pdf_is_image_only(self, tmp_path):
        pdf = _make_image_only_pdf(tmp_path / "blank.pdf")
        reader = PdfReader(str(pdf))
        assert _is_image_only(reader) is True

    def test_text_pdf_is_not_image_only(self, tmp_path):
        pdf = _make_text_pdf(tmp_path / "text.pdf")
        reader = PdfReader(str(pdf))
        assert _is_image_only(reader) is False


# ── _build_text_overlay ───────────────────────────────────────────────────────

class TestBuildTextOverlay:

    def test_returns_pdf_reader(self):
        results = [_fake_ocr_result("Test")]
        overlay = _build_text_overlay(results, 200, 300, 595, 842)
        assert isinstance(overlay, PdfReader)

    def test_single_page_output(self):
        results = [_fake_ocr_result("Hello")]
        overlay = _build_text_overlay(results, 200, 300, 595, 842)
        assert len(overlay.pages) == 1

    def test_empty_results_no_crash(self):
        overlay = _build_text_overlay([], 200, 300, 595, 842)
        assert len(overlay.pages) == 1

    def test_whitespace_only_text_skipped(self):
        results = [_fake_ocr_result("   ")]
        # Should not raise
        overlay = _build_text_overlay(results, 200, 300, 595, 842)
        assert overlay is not None

    def test_multiple_words(self):
        results = [
            _fake_ocr_result("Merhaba", x1=10, y1=10, x2=100, y2=40),
            _fake_ocr_result("Dünya",   x1=110, y1=10, x2=200, y2=40),
        ]
        overlay = _build_text_overlay(results, 200, 300, 595, 842)
        assert len(overlay.pages) == 1

    def test_coordinates_within_page(self):
        """Text at extreme corners should not crash."""
        results = [
            _fake_ocr_result("A", x1=0, y1=0, x2=1, y2=1),
            _fake_ocr_result("B", x1=199, y1=299, x2=200, y2=300),
        ]
        overlay = _build_text_overlay(results, 200, 300, 595, 842)
        assert overlay is not None

    def test_output_is_valid_pdf_bytes(self):
        results = [_fake_ocr_result("PDF")]
        overlay = _build_text_overlay(results, 200, 300, 595, 842)
        # Re-serialise and check magic bytes
        buf = io.BytesIO()
        PdfWriter()  # just ensure import works
        from pypdf import PdfWriter as W
        w = W()
        w.add_page(overlay.pages[0])
        w.write(buf)
        assert buf.getvalue()[:4] == b"%PDF"


# ── ocr (integration, mocked) ─────────────────────────────────────────────────

FAKE_IMAGE = _blank_image()
FAKE_OCR_RESULTS = [_fake_ocr_result("Merhaba"), _fake_ocr_result("Dünya", x1=110, y1=10, x2=200, y2=40)]


def _patch_ocr(monkeypatch):
    """Patch both easyocr and pdf2image so no models/poppler needed."""
    mock_reader = MagicMock()
    mock_reader.readtext.return_value = FAKE_OCR_RESULTS

    monkeypatch.setattr("pdf_tools.ocr._reader_cache", {"en,tr": mock_reader})

    mock_convert = MagicMock(return_value=[FAKE_IMAGE])
    return mock_reader, mock_convert


class TestOcr:

    def test_output_file_created(self, tmp_path, monkeypatch):
        src = _make_image_only_pdf(tmp_path / "scan.pdf")
        mock_reader, mock_convert = _patch_ocr(monkeypatch)
        with patch("pdf_tools.ocr.convert_from_path", mock_convert, create=True), \
             patch("pdf_tools.ocr.PdfReader", wraps=PdfReader):
            with patch("pdf_tools.ocr._get_reader", return_value=mock_reader):
                with patch("pdf_tools.ocr.convert_from_path", mock_convert):
                    ocr([src], langs=["tr", "en"], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert list(out_dir.glob("*ocr*"))

    def test_output_is_valid_pdf(self, tmp_path, monkeypatch):
        src = _make_image_only_pdf(tmp_path / "scan.pdf")
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = FAKE_OCR_RESULTS
        with patch("pdf_tools.ocr._get_reader", return_value=mock_reader), \
             patch("pdf_tools.ocr.convert_from_path", return_value=[FAKE_IMAGE]):
            ocr([src], langs=["tr", "en"], overwrite=True)
        out = next((tmp_path / OUTPUT_SUBDIR).glob("*ocr*"))
        assert out.read_bytes()[:4] == b"%PDF"

    def test_page_count_preserved(self, tmp_path, monkeypatch):
        src = _make_image_only_pdf(tmp_path / "scan.pdf", pages=2)
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []
        with patch("pdf_tools.ocr._get_reader", return_value=mock_reader), \
             patch("pdf_tools.ocr.convert_from_path", return_value=[FAKE_IMAGE, FAKE_IMAGE]):
            ocr([src], langs=["tr", "en"], overwrite=True)
        out = next((tmp_path / OUTPUT_SUBDIR).glob("*ocr*"))
        assert len(PdfReader(str(out)).pages) == 2

    def test_text_pdf_skipped(self, tmp_path, monkeypatch):
        src = _make_text_pdf(tmp_path / "text.pdf")
        mock_reader = MagicMock()
        with patch("pdf_tools.ocr._get_reader", return_value=mock_reader), \
             patch("pdf_tools.ocr.convert_from_path", return_value=[FAKE_IMAGE]) as mock_conv:
            ocr([src], langs=["tr", "en"], overwrite=True)
        # convert_from_path should never be called for text PDFs
        mock_conv.assert_not_called()
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*ocr*")) if out_dir.exists() else []
        assert outputs == []

    def test_corrupt_pdf_skipped(self, tmp_path, monkeypatch):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        mock_reader = MagicMock()
        with patch("pdf_tools.ocr._get_reader", return_value=mock_reader):
            ocr([bad], langs=["tr", "en"], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*ocr*")) if out_dir.exists() else []
        assert outputs == []

    def test_output_filename_contains_ocr(self, tmp_path, monkeypatch):
        src = _make_image_only_pdf(tmp_path / "invoice.pdf")
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []
        with patch("pdf_tools.ocr._get_reader", return_value=mock_reader), \
             patch("pdf_tools.ocr.convert_from_path", return_value=[FAKE_IMAGE]):
            ocr([src], langs=["tr", "en"], overwrite=True)
        out = next((tmp_path / OUTPUT_SUBDIR).glob("*.pdf"))
        assert "ocr" in out.name

    def test_overwrite_false_increments(self, tmp_path, monkeypatch):
        src = _make_image_only_pdf(tmp_path / "scan.pdf")
        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []
        with patch("pdf_tools.ocr._get_reader", return_value=mock_reader), \
             patch("pdf_tools.ocr.convert_from_path", return_value=[FAKE_IMAGE]):
            ocr([src], langs=["tr", "en"], overwrite=False)
            ocr([src], langs=["tr", "en"], overwrite=False)
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert len(list(out_dir.glob("*ocr*"))) == 2

    def test_rasterization_failure_skipped(self, tmp_path, monkeypatch):
        src = _make_image_only_pdf(tmp_path / "scan.pdf")
        mock_reader = MagicMock()
        with patch("pdf_tools.ocr._get_reader", return_value=mock_reader), \
             patch("pdf_tools.ocr.convert_from_path", side_effect=Exception("poppler not found")):
            ocr([src], langs=["tr", "en"], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*ocr*")) if out_dir.exists() else []
        assert outputs == []

    def test_default_langs_constant(self):
        assert "tr" in DEFAULT_LANGS
        assert "en" in DEFAULT_LANGS

    def test_raster_dpi_reasonable(self):
        assert 150 <= RASTER_DPI <= 400

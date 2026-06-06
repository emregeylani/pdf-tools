"""ocr: add a searchable invisible text layer to image-only PDF pages."""
from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

from pdf2image import convert_from_path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from pdf_tools.utils.file_helpers import get_output_dir, safe_output_path, fmt_size, size_delta
from pdf_tools.utils import logger as log

if TYPE_CHECKING:
    import easyocr as _easyocr

# Default languages — override via --lang CLI option
DEFAULT_LANGS = ["tr", "en"]

# DPI used when rasterizing PDF pages for OCR
RASTER_DPI = 200


# ── lazy reader ──────────────────────────────────────────────────────────────

_reader_cache: dict[str, "_easyocr.Reader"] = {}


def _get_reader(langs: list[str]) -> "_easyocr.Reader":
    """Return a cached EasyOCR Reader for the given language list.

    First call downloads models (~100–200 MB) if not already cached on disk.
    """
    import easyocr  # lazy — heavy import

    key = ",".join(sorted(langs))
    if key not in _reader_cache:
        log.info(f"Loading EasyOCR model (langs: {langs}) — first run may download models...")
        _reader_cache[key] = easyocr.Reader(langs, gpu=False, verbose=False)
    return _reader_cache[key]


# ── page helpers ─────────────────────────────────────────────────────────────

def _build_text_overlay(
    ocr_results: list,
    img_w: int,
    img_h: int,
    page_w: float,
    page_h: float,
) -> PdfReader:
    """Build a single-page PDF with invisible text positioned over OCR bboxes."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_w, page_h))
    c.setFillAlpha(0)  # fully transparent — searchable but invisible

    for item in ocr_results:
        bbox, text, _conf = item
        if not text.strip():
            continue

        # EasyOCR bbox: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
        x1_px = bbox[0][0]
        y2_px = bbox[2][1]  # bottom of bbox in image coords (Y increases downward)
        x2_px = bbox[1][0]

        # Scale from image pixels to PDF points
        x1 = x1_px / img_w * page_w
        y1 = (1 - y2_px / img_h) * page_h  # flip Y axis

        # Scale font size to bbox height
        bbox_h_px = bbox[2][1] - bbox[0][1]
        font_size = max(4, int(bbox_h_px / img_h * page_h))

        # Fit text width to bbox width
        bbox_w = (x2_px - x1_px) / img_w * page_w
        c.setFont("Helvetica", font_size)
        text_w = c.stringWidth(text, "Helvetica", font_size)
        if text_w > 0:
            c._horizScale = min(100, bbox_w / text_w * 100)

        c.drawString(x1, y1, text)
        c._horizScale = 100  # reset

    c.save()
    packet.seek(0)
    return PdfReader(packet)


def _is_image_only(reader: PdfReader) -> bool:
    """Heuristic: a PDF is image-only if it has no extractable text."""
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            return False
    return True


# ── main ─────────────────────────────────────────────────────────────────────

def ocr(input_paths: list[Path], langs: list[str], overwrite: bool) -> None:
    log.section("ocr")
    reader_ocr = _get_reader(langs)

    for src in input_paths:
        log.processing(src)

        try:
            pdf_reader = PdfReader(str(src))
        except Exception as exc:
            log.error(src, str(exc))
            continue

        if not _is_image_only(pdf_reader):
            log.info(f"skipped — document already contains text")
            continue

        total_pages = len(pdf_reader.pages)
        log.info(f"{total_pages} pages to process (langs: {langs}, dpi: {RASTER_DPI})")

        try:
            images = convert_from_path(str(src), dpi=RASTER_DPI)
        except Exception as exc:
            log.error(src, f"rasterization failed: {exc}")
            continue

        writer = PdfWriter()
        total_words = 0

        for i, (page, img) in enumerate(zip(pdf_reader.pages, images), 1):
            img_w, img_h = img.size
            page_w = float(page.mediabox.width)
            page_h = float(page.mediabox.height)

            log.info(f"  page {i}/{total_pages} — OCR...")
            results = reader_ocr.readtext(img)  # [[bbox, text, conf], ...]
            word_count = sum(1 for _, text, _ in results if text.strip())
            total_words += word_count
            log.info(f"  page {i} — {word_count} text regions found")

            overlay_reader = _build_text_overlay(results, img_w, img_h, page_w, page_h)
            page.merge_page(overlay_reader.pages[0])
            writer.add_page(page)

        out_dir = get_output_dir(src)
        out_path = safe_output_path(out_dir, f"{src.stem}-ocr.pdf", overwrite)

        with open(out_path, "wb") as fh:
            writer.write(fh)

        log.produced(
            out_path,
            f"{total_pages} pages  |  {total_words} text regions  |  "
            + size_delta(src.stat().st_size, out_path.stat().st_size),
        )

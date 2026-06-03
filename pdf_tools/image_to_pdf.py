"""image-to-pdf: convert PNG/JPG/JPEG/BMP images to same-named PDFs."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from pdf_tools.utils.file_helpers import get_output_dir, safe_output_path, fmt_size
from pdf_tools.utils import logger as log

SUPPORTED = {".png", ".jpg", ".jpeg", ".bmp"}

# A4 at 96 dpi (points)
A4_W_PT = 595.276
A4_H_PT = 841.890


def image_to_pdf(input_paths: list[Path], overwrite: bool) -> None:
    log.section("image-to-pdf")

    rows: list[tuple[str, ...]] = []

    for src in input_paths:
        if src.suffix.lower() not in SUPPORTED:
            log.skipped(src, f"unsupported format '{src.suffix}'")
            continue

        log.processing(src)
        try:
            img = Image.open(src)
        except Exception as exc:
            log.error(src, str(exc))
            continue

        # Convert to RGB (PDF doesn't support palette/RGBA directly)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        out_name = src.with_suffix(".pdf").name
        out_dir = get_output_dir(src)
        out_path = safe_output_path(out_dir, out_name, overwrite)

        img.save(str(out_path), "PDF", resolution=96)

        size_in = src.stat().st_size
        size_out = out_path.stat().st_size
        w, h = img.size
        log.produced(out_path, f"{w}×{h}px  |  {fmt_size(size_in)} → {fmt_size(size_out)}")
        rows.append((src.name, out_path.name, f"{w}×{h}", fmt_size(size_in), fmt_size(size_out)))

    if rows:
        log.subsection("Summary")
        log.summary_table(rows, ["Input", "Output", "Dimensions", "Input size", "Output size"])

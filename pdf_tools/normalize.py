"""normalize-page-size: resize every page to A4, preserving orientation."""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import FloatObject

from pdf_tools.utils.file_helpers import get_output_dir, safe_output_path, fmt_size
from pdf_tools.utils import logger as log

# A4 in points (1 pt = 1/72 inch)
A4_W = 595.276
A4_H = 841.890


def normalize(input_paths: list[Path], overwrite: bool) -> None:
    log.section("normalize-page-size")

    rows: list[tuple[str, ...]] = []

    for src in input_paths:
        log.processing(src)
        try:
            reader = PdfReader(str(src))
        except Exception as exc:
            log.error(src, str(exc))
            continue

        writer = PdfWriter()
        page_count = len(reader.pages)

        for page in reader.pages:
            # Detect orientation from original media box
            orig_w = float(page.mediabox.width)
            orig_h = float(page.mediabox.height)
            landscape = orig_w > orig_h

            target_w = A4_H if landscape else A4_W
            target_h = A4_W if landscape else A4_H

            # Scale to fit A4 while preserving aspect ratio
            scale_x = target_w / orig_w
            scale_y = target_h / orig_h
            scale = min(scale_x, scale_y)

            # Apply uniform scale via content transform, then set A4 mediabox
            page.add_transformation([scale, 0, 0, scale, 0, 0])  # type: ignore[arg-type]

            page.mediabox.lower_left = (FloatObject(0), FloatObject(0))
            page.mediabox.upper_right = (FloatObject(target_w), FloatObject(target_h))

            writer.add_page(page)

        out_dir = get_output_dir(src)
        out_path = safe_output_path(out_dir, src.name, overwrite, operation="normalized")

        with open(out_path, "wb") as fh:
            writer.write(fh)

        size_in = src.stat().st_size
        size_out = out_path.stat().st_size
        log.produced(out_path, f"{page_count} pages  |  {fmt_size(size_in)} → {fmt_size(size_out)}")
        rows.append((src.name, str(page_count), fmt_size(size_in), fmt_size(size_out)))

    if rows:
        log.subsection("Summary")
        log.summary_table(rows, ["File", "Pages", "Input size", "Output size"])

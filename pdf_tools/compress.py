"""compress: reduce PDF file size via pikepdf object-stream optimisation."""
from __future__ import annotations

from pathlib import Path

import pikepdf

from pdf_tools.utils.file_helpers import get_output_dir, safe_output_path, size_delta, fmt_size
from pdf_tools.utils import logger as log

# Compression level presets
PRESETS = {
    "light": dict(
        compress_streams=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate,
        recompress_flate=False,
    ),
    "aggressive": dict(
        compress_streams=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate,
        recompress_flate=True,
    ),
}


def compress(input_paths: list[Path], overwrite: bool, level: str = "light") -> None:
    log.section(f"compress  [dim](level: {level})[/]")

    preset = PRESETS.get(level, PRESETS["light"])
    rows: list[tuple[str, ...]] = []

    for src in input_paths:
        log.processing(src)
        size_before = src.stat().st_size

        try:
            pdf = pikepdf.open(str(src))
        except Exception as exc:
            log.error(src, str(exc))
            continue

        out_dir = get_output_dir(src)
        out_path = safe_output_path(out_dir, src.name, overwrite, operation="compressed")

        try:
            pdf.save(str(out_path), **preset)
        except Exception as exc:
            log.error(src, f"save failed: {exc}")
            pdf.close()
            continue
        finally:
            pdf.close()

        size_after = out_path.stat().st_size
        delta = size_delta(size_before, size_after)
        log.produced(out_path, delta)
        rows.append((src.name, fmt_size(size_before), fmt_size(size_after), delta.split("(")[1].rstrip(")")))

    if rows:
        log.subsection("Summary")
        log.summary_table(rows, ["File", "Before", "After", "Change"])

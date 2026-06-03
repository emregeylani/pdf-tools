"""concatenate: merge PDFs alphabetically into concatenated-DATE.pdf."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from pdf_tools.utils.file_helpers import get_output_dir, safe_output_path, fmt_size
from pdf_tools.utils import logger as log


def concatenate(input_paths: list[Path], overwrite: bool) -> None:
    log.section("concatenate")

    sorted_paths = sorted(input_paths, key=lambda p: p.name.lower())

    log.subsection("Input order (alphabetical)")
    for i, p in enumerate(sorted_paths, 1):
        log.info(f"{i:>3}. {p.name}  ({fmt_size(p.stat().st_size)})")

    writer = PdfWriter()
    total_pages = 0
    failed: list[str] = []

    for src in sorted_paths:
        log.processing(src)
        try:
            reader = PdfReader(str(src))
        except Exception as exc:
            log.error(src, str(exc))
            failed.append(src.name)
            continue

        pages = len(reader.pages)
        for page in reader.pages:
            writer.add_page(page)
        total_pages += pages
        log.info(f"added {pages} pages from {src.name}")

    if total_pages == 0:
        log.info("Nothing to write — aborting.")
        return

    today = date.today().strftime("%Y%m%d")
    out_name = f"concatenated-{today}.pdf"

    # Output dir is relative to the first (alphabetically) input file's parent
    out_dir = get_output_dir(sorted_paths[0])
    out_path = safe_output_path(out_dir, out_name, overwrite)

    with open(out_path, "wb") as fh:
        writer.write(fh)

    total_input = sum(p.stat().st_size for p in sorted_paths if p.name not in failed)
    size_out = out_path.stat().st_size

    log.produced(
        out_path,
        f"{len(sorted_paths) - len(failed)} files  |  {total_pages} pages  |  "
        f"{fmt_size(total_input)} → {fmt_size(size_out)}",
    )

    if failed:
        log.subsection("Failed files")
        for name in failed:
            log.info(f"  ✖ {name}")

"""split: extract page ranges from a PDF into a single output file."""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from pdf_tools.utils.file_helpers import get_output_dir, safe_output_path, fmt_size, size_delta
from pdf_tools.utils import logger as log


# ── range parser ─────────────────────────────────────────────────────────────

def parse_pages(spec: str, total: int) -> list[int]:
    """Parse a page range spec like '1-3,5,8' into a sorted list of 1-based page numbers.

    Raises ValueError with a descriptive message if any number is out of range
    or the spec is malformed.
    """
    pages: list[int] = []

    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            raw = part.split("-", 1)
            if len(raw) != 2 or not raw[0].strip() or not raw[1].strip():
                raise ValueError(f"Malformed range '{part}' — expected format: start-end")
            try:
                start, end = int(raw[0]), int(raw[1])
            except ValueError:
                raise ValueError(f"Non-integer value in range '{part}'")
            if start < 1 or end < 1:
                raise ValueError(f"Page numbers must be ≥ 1 (got '{part}')")
            if start > end:
                raise ValueError(f"Range start must be ≤ end (got '{part}')")
            if start > total:
                raise ValueError(f"Page {start} does not exist — document has {total} pages")
            if end > total:
                raise ValueError(f"Page {end} does not exist — document has {total} pages")
            pages.extend(range(start, end + 1))
        else:
            try:
                n = int(part)
            except ValueError:
                raise ValueError(f"Non-integer page number '{part}'")
            if n < 1:
                raise ValueError(f"Page numbers must be ≥ 1 (got {n})")
            if n > total:
                raise ValueError(f"Page {n} does not exist — document has {total} pages")
            pages.append(n)

    if not pages:
        raise ValueError("No pages selected — check your page range spec")

    # Deduplicate while preserving order, then sort
    seen: set[int] = set()
    result: list[int] = []
    for p in pages:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return sorted(result)


# ── main ─────────────────────────────────────────────────────────────────────

def split(input_paths: list[Path], pages_spec: str, overwrite: bool) -> None:
    log.section("split")

    for src in input_paths:
        log.processing(src)

        try:
            reader = PdfReader(str(src))
        except Exception as exc:
            log.error(src, str(exc))
            continue

        total = len(reader.pages)
        log.info(f"total pages in document: {total}")

        try:
            page_numbers = parse_pages(pages_spec, total)
        except ValueError as exc:
            log.error(src, str(exc))
            raise SystemExit(1)

        log.info(f"extracting pages: {page_numbers}")

        writer = PdfWriter()
        for n in page_numbers:
            writer.add_page(reader.pages[n - 1])  # pypdf is 0-based

        # Build output name: stem + page range tag + -split
        range_tag = pages_spec.replace(",", "_").replace("-", "to")
        out_name = f"{src.stem}-p{range_tag}-split.pdf"

        out_dir = get_output_dir(src)
        out_path = safe_output_path(out_dir, out_name, overwrite)

        with open(out_path, "wb") as fh:
            writer.write(fh)

        log.produced(
            out_path,
            f"{len(page_numbers)} pages extracted  |  "
            + size_delta(src.stat().st_size, out_path.stat().st_size),
        )

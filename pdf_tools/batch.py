"""
batch: for each given folder, convert images to PDF then concatenate
everything (existing PDFs + freshly converted ones) into a single PDF.

Workflow per folder:
  1. Find all PNG/JPG/JPEG/BMP files  -> convert each to PDF
  2. Collect all PDF files in folder  -> merge alphabetically
  3. Optionally normalize all pages to A4 before merging (--no-normalize to skip)
  4. Optionally compress the result   -> (--compress flag)
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pikepdf
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import FloatObject

from pdf_tools.utils.file_helpers import get_output_dir, safe_output_path, size_delta, fmt_size
from pdf_tools.utils import logger as log

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}

# A4 in points
A4_W = 595.276
A4_H = 841.890

COMPRESS_PRESET = dict(
    compress_streams=True,
    object_stream_mode=pikepdf.ObjectStreamMode.generate,
    recompress_flate=True,
)


# ── image conversion ──────────────────────────────────────────────────────────

def _convert_image(src: Path, out_dir: Path, overwrite: bool) -> Path | None:
    """Convert a single image to PDF. Returns output path or None on failure."""
    try:
        img = Image.open(src)
    except Exception as exc:
        log.error(src, str(exc))
        return None

    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    out_name = src.with_suffix(".pdf").name
    out_path = safe_output_path(out_dir, out_name, overwrite)
    img.save(str(out_path), "PDF", resolution=96)
    w, h = img.size
    log.produced(out_path, f"{w}×{h}px  |  {fmt_size(src.stat().st_size)} -> {fmt_size(out_path.stat().st_size)}")
    return out_path


# ── normalize (inline, applied per-page during merge) ─────────────────────────

def _normalize_page(page: object) -> None:
    """Resize a single pypdf page to A4 in-place, preserving orientation."""
    orig_w = float(page.mediabox.width)   # type: ignore[attr-defined]
    orig_h = float(page.mediabox.height)  # type: ignore[attr-defined]
    landscape = orig_w > orig_h

    target_w = A4_H if landscape else A4_W
    target_h = A4_W if landscape else A4_H

    scale = min(target_w / orig_w, target_h / orig_h)
    page.add_transformation([scale, 0, 0, scale, 0, 0])  # type: ignore[attr-defined]
    page.mediabox.lower_left = (FloatObject(0), FloatObject(0))           # type: ignore[attr-defined]
    page.mediabox.upper_right = (FloatObject(target_w), FloatObject(target_h))  # type: ignore[attr-defined]


# ── merge (with optional per-page normalize) ──────────────────────────────────

def _merge_pdfs(pdf_paths: list[Path], out_path: Path, normalize: bool) -> int:
    """Merge PDFs into out_path, optionally normalizing each page to A4."""
    writer = PdfWriter()
    total = 0
    for src in pdf_paths:
        try:
            reader = PdfReader(str(src))
        except Exception as exc:
            log.error(src, str(exc))
            continue
        for page in reader.pages:
            if normalize:
                _normalize_page(page)
            writer.add_page(page)
        total += len(reader.pages)
        log.info(f"  + {src.name}  ({len(reader.pages)} pages)")
    with open(out_path, "wb") as fh:
        writer.write(fh)
    return total


# ── compress ──────────────────────────────────────────────────────────────────

def _compress(path: Path) -> None:
    """In-place compress a PDF via pikepdf."""
    size_before = path.stat().st_size
    pdf = pikepdf.open(str(path), allow_overwriting_input=True)
    pdf.save(str(path), **COMPRESS_PRESET)
    pdf.close()
    log.info(f"compressed: {size_delta(size_before, path.stat().st_size)}")


# ── main entry ────────────────────────────────────────────────────────────────

def batch(
    folders: list[Path],
    overwrite: bool,
    normalize: bool,
    compress: bool,
) -> None:
    flags = " ".join(filter(None, [
        "[dim](+concatenate)[/]",
        "[dim](+normalize)[/]" if normalize else "",
        "[dim](+compress)[/]" if compress else "",
    ]))
    log.section(f"batch  {flags}")

    today = date.today().strftime("%Y%m%d")
    summary_rows: list[tuple[str, ...]] = []

    for folder in folders:
        if not folder.is_dir():
            log.skipped(folder, "not a directory")
            continue

        log.subsection(f"Folder: {folder}")
        out_dir = get_output_dir(folder / "_")  # anchor output inside folder

        # ── Step 1: convert images ────────────────────────────────────────────
        image_files = sorted(
            [f for f in folder.iterdir() if f.suffix.lower() in IMAGE_SUFFIXES],
            key=lambda p: p.name.lower(),
        )
        converted_pdfs: list[Path] = []
        if image_files:
            log.info(f"Converting {len(image_files)} image(s) to PDF ...")
            for img_file in image_files:
                log.processing(img_file)
                result = _convert_image(img_file, out_dir, overwrite)
                if result:
                    converted_pdfs.append(result)
        else:
            log.info("No images found.")

        # ── Step 2: collect all PDFs (originals + converted), sort alphabetically
        original_pdfs = sorted(
            [f for f in folder.iterdir() if f.suffix.lower() == ".pdf"],
            key=lambda p: p.name.lower(),
        )
        all_pdfs = sorted(
            original_pdfs + converted_pdfs,
            key=lambda p: p.name.lower(),
        )

        if not all_pdfs:
            log.skipped(folder, "no PDFs to merge after conversion")
            continue

        action = "concatenate" + (" + normalize" if normalize else "")
        log.subsection(action)
        log.info(f"Merging {len(all_pdfs)} PDF(s) alphabetically ...")

        out_name = f"{folder.name}-{today}.pdf"
        out_path = safe_output_path(out_dir, out_name, overwrite)

        # ── Step 3: merge (normalize applied per-page if requested) ──────────
        total_pages = _merge_pdfs(all_pdfs, out_path, normalize=normalize)

        # ── Step 4: optional compress ─────────────────────────────────────────
        if compress:
            _compress(out_path)

        final_size = out_path.stat().st_size
        log.produced(
            out_path,
            f"{len(all_pdfs)} files  |  {total_pages} pages  |  {fmt_size(final_size)}",
        )

        summary_rows.append((
            folder.name,
            str(len(image_files)),
            str(len(original_pdfs)),
            "yes" if normalize else "no",
            "yes" if compress else "no",
            str(total_pages),
            fmt_size(final_size),
            out_path.name,
        ))

    if summary_rows:
        log.subsection("Summary")
        log.summary_table(
            summary_rows,
            ["Folder", "Images", "PDFs", "Normalized", "Compressed", "Pages", "Size", "Output file"],
        )

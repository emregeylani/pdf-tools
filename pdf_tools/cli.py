"""pdf-tools CLI — entry point."""
from __future__ import annotations

import sys
from pathlib import Path

import click

# ── Custom --help ─────────────────────────────────────────────────────────────

FULL_HELP = """\
pdf-tools  —  PDF batch processing toolkit
===========================================

USAGE
  python3 pdf_tools <command> [OPTIONS] [FILES/FOLDERS...]
  python3 pdf_tools <command> --help     for full details on any command

COMMANDS
  normalize-page-size   Resize pages to A4, preserving orientation
  image-to-pdf          Convert PNG/JPG/JPEG/BMP images to PDF
  concatenate           Merge PDFs alphabetically into one file
  compress              Shrink PDF size  [--level light|aggressive]
  remove-images         Replace images with grey placeholders
  batch                 Per-folder pipeline: images->PDF, merge, normalize, compress
                        [--no-normalize] [--no-compress]
  split                 Extract page ranges into a single output PDF  [--pages 1-3,5,8]
  ocr                   Add invisible text layer to image-only PDFs  [--lang tr en]

OUTPUT
  Results go to output-pdf-tools/ next to each input.
  Filenames embed the operation: sample-compressed.pdf, sample-compressed-normalized.pdf

OPTIONS
  --overwrite   Overwrite existing files (default: add _1, _2, ...)
  --help        Show this message and exit
  --version     Show version and exit
"""


class FullHelpGroup(click.Group):
    """Custom Group that prints the full help page for --help / no args."""

    def get_help(self, ctx: click.Context) -> str:  # type: ignore[override]
        return FULL_HELP

    def invoke(self, ctx: click.Context) -> None:
        if not ctx.protected_args and not ctx.args:
            click.echo(FULL_HELP)
            ctx.exit()
        super().invoke(ctx)


# ── Shared options ────────────────────────────────────────────────────────────

_overwrite = click.option(
    "--overwrite", is_flag=True, default=False,
    help="Overwrite existing output files instead of adding a numeric suffix.",
)


def _resolve(paths: tuple[str, ...]) -> list[Path]:
    resolved: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.exists():
            resolved.append(path)
        else:
            matches = list(Path(".").glob(p))
            if matches:
                resolved.extend(matches)
            else:
                click.echo(f"Warning: '{p}' not found — skipped.", err=True)
    return sorted(set(resolved), key=lambda x: x.name.lower())


# ── CLI group ─────────────────────────────────────────────────────────────────

@click.group(cls=FullHelpGroup)
@click.version_option("0.1.0", prog_name="pdf-tools")
def cli() -> None:
    pass


# ── normalize-page-size ───────────────────────────────────────────────────────

@cli.command("normalize-page-size")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE ...]")
@_overwrite
def cmd_normalize(files: tuple[str, ...], overwrite: bool) -> None:
    """Resize all pages to A4, preserving landscape/portrait orientation."""
    from pdf_tools.normalize import normalize
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid files provided.")
    normalize(paths, overwrite)


# ── image-to-pdf ──────────────────────────────────────────────────────────────

@cli.command("image-to-pdf")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE ...]")
@_overwrite
def cmd_image_to_pdf(files: tuple[str, ...], overwrite: bool) -> None:
    """Convert PNG/JPG/JPEG/BMP images to same-named PDF files."""
    from pdf_tools.image_to_pdf import image_to_pdf
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid files provided.")
    image_to_pdf(paths, overwrite)


# ── concatenate ───────────────────────────────────────────────────────────────

@cli.command("concatenate")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE ...]")
@_overwrite
def cmd_concatenate(files: tuple[str, ...], overwrite: bool) -> None:
    """Merge multiple PDFs alphabetically into a single file."""
    from pdf_tools.concatenate import concatenate
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid PDF files provided.")
    concatenate(paths, overwrite)


# ── compress ──────────────────────────────────────────────────────────────────

@cli.command("compress")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE ...]")
@click.option(
    "--level", type=click.Choice(["light", "aggressive"]), default="light", show_default=True,
    help="light (default) or aggressive (recompress Flate streams).",
)
@_overwrite
def cmd_compress(files: tuple[str, ...], level: str, overwrite: bool) -> None:
    """Reduce PDF file size via stream and object-stream optimisation."""
    from pdf_tools.compress import compress
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid PDF files provided.")
    compress(paths, overwrite, level=level)


# ── remove-images ─────────────────────────────────────────────────────────────

@cli.command("remove-images")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE ...]")
@_overwrite
def cmd_remove_images(files: tuple[str, ...], overwrite: bool) -> None:
    """Replace all raster images with same-size grey placeholder boxes."""
    from pdf_tools.remove_images import remove_images
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid PDF files provided.")
    remove_images(paths, overwrite)


# ── batch ─────────────────────────────────────────────────────────────────────

@cli.command("batch")
@click.argument("folders", nargs=-1, required=True, metavar="FOLDER [FOLDER ...]")
@click.option(
    "--no-normalize", "skip_normalize", is_flag=True, default=False,
    help="Skip A4 normalization step (normalization is ON by default).",
)
@click.option(
    "--no-compress", "skip_compress", is_flag=True, default=False,
    help="Skip compression step (compression is ON by default).",
)
@_overwrite
def cmd_batch(folders: tuple[str, ...], skip_normalize: bool, skip_compress: bool, overwrite: bool) -> None:
    """Per-folder pipeline: convert images + normalize + merge [+ compress]."""
    from pdf_tools.batch import batch
    folder_paths = [Path(f) for f in folders]
    batch(folder_paths, overwrite=overwrite, normalize=not skip_normalize, compress=not skip_compress)


# ── split ─────────────────────────────────────────────────────────────────────

@cli.command("split")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE ...]")
@click.option(
    "--pages", "pages_spec", required=True, metavar="SPEC",
    help="Pages to extract, e.g. '1-3,5,8'. Ranges are inclusive. "
         "Invalid page numbers abort immediately.",
)
@_overwrite
def cmd_split(files: tuple[str, ...], pages_spec: str, overwrite: bool) -> None:
    """Extract page ranges from PDF(s) into a single output file per input."""
    from pdf_tools.split import split
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid PDF files provided.")
    split(paths, pages_spec, overwrite)


# ── ocr ───────────────────────────────────────────────────────────────────────

@cli.command("ocr")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE ...]")
@click.option(
    "--lang", "langs", multiple=True, default=["tr", "en"], show_default=True,
    metavar="LANG",
    help="OCR language codes (repeatable). Default: tr en. "
         "First run downloads EasyOCR models (~100–200 MB).",
)
@_overwrite
def cmd_ocr(files: tuple[str, ...], langs: tuple[str, ...], overwrite: bool) -> None:
    """Add a searchable invisible text layer to image-only PDF pages.

    Uses EasyOCR + pdf2image (requires poppler: apt install poppler-utils).
    Skips PDFs that already contain extractable text.
    """
    from pdf_tools.ocr import ocr
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid PDF files provided.")
    ocr(paths, list(langs), overwrite)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()

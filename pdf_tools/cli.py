"""pdf-tools CLI — entry point."""
from __future__ import annotations

from pathlib import Path

import click

# ── Shared options ────────────────────────────────────────────────────────────

_overwrite = click.option(
    "--overwrite", is_flag=True, default=False,
    help="Overwrite existing output files instead of adding a numeric suffix.",
)


def _resolve(paths: tuple[str, ...], glob_ok: bool = True) -> list[Path]:
    """Expand globs / resolve paths, return sorted list."""
    resolved: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.exists():
            resolved.append(path)
        else:
            # Try glob expansion relative to cwd
            matches = list(Path(".").glob(p))
            if matches:
                resolved.extend(matches)
            else:
                click.echo(f"Warning: '{p}' not found — skipped.", err=True)
    return sorted(set(resolved), key=lambda x: x.name.lower())


# ── CLI group ─────────────────────────────────────────────────────────────────

@click.group()
@click.version_option("0.1.0", prog_name="pdf-tools")
def cli() -> None:
    """PDF batch processing toolkit.\n
    Output files are written to an output-pdf-tools/ subfolder
    next to each input file.
    """


# ── normalize-page-size ───────────────────────────────────────────────────────

@cli.command("normalize-page-size")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE …]")
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
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE …]")
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
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE …]")
@_overwrite
def cmd_concatenate(files: tuple[str, ...], overwrite: bool) -> None:
    """Merge PDFs alphabetically into concatenated-DATE.pdf."""
    from pdf_tools.concatenate import concatenate
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid PDF files provided.")
    concatenate(paths, overwrite)


# ── compress ──────────────────────────────────────────────────────────────────

@cli.command("compress")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE …]")
@click.option(
    "--level", type=click.Choice(["light", "aggressive"]), default="light", show_default=True,
    help="Compression preset: light (fast) or aggressive (max size reduction).",
)
@_overwrite
def cmd_compress(files: tuple[str, ...], level: str, overwrite: bool) -> None:
    """Reduce PDF size via stream compression and object optimisation."""
    from pdf_tools.compress import compress
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid PDF files provided.")
    compress(paths, overwrite, level=level)


# ── remove-images ─────────────────────────────────────────────────────────────

@cli.command("remove-images")
@click.argument("files", nargs=-1, required=True, metavar="FILE [FILE …]")
@_overwrite
def cmd_remove_images(files: tuple[str, ...], overwrite: bool) -> None:
    """Replace all raster images with same-size grey placeholder boxes."""
    from pdf_tools.remove_images import remove_images
    paths = _resolve(files)
    if not paths:
        raise click.UsageError("No valid PDF files provided.")
    remove_images(paths, overwrite)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()

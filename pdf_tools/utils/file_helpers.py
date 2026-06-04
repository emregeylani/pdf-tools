"""File utility helpers for pdf-tools."""
from __future__ import annotations

from pathlib import Path


OUTPUT_SUBDIR = "output-pdf-tools"


def get_output_dir(reference_path: Path) -> Path:
    """Return (and create if needed) the output-pdf-tools dir next to reference_path."""
    out_dir = reference_path.parent / OUTPUT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def safe_output_path(output_dir: Path, filename: str, overwrite: bool, operation: str = "") -> Path:
    """
    Return a safe output Path, embedding the operation name before the extension.

    Examples (operation="compressed"):
      sample.pdf                        -> output-pdf-tools/sample-compressed.pdf
      sample-compressed.pdf exists, overwrite=False
                                        -> output-pdf-tools/sample-compressed_1.pdf

    If overwrite=True the collision counter is skipped.
    """
    src = Path(filename)
    op_tag = f"-{operation}" if operation else ""
    base_stem = f"{src.stem}{op_tag}"
    ext = src.suffix

    candidate = output_dir / f"{base_stem}{ext}"
    if overwrite or not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = output_dir / f"{base_stem}_{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def fmt_size(n_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n_bytes) < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024  # type: ignore[assignment]
    return f"{n_bytes:.1f} TB"


def size_delta(before: int, after: int) -> str:
    """e.g. '1.2 MB -> 340.0 KB  (-72.3%)'"""
    pct = (after - before) / before * 100 if before else 0
    sign = "-" if pct <= 0 else "+"
    return f"{fmt_size(before)} -> {fmt_size(after)}  ({sign}{abs(pct):.1f}%)"

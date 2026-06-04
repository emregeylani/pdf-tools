"""File utility helpers for pdf-tools."""
from __future__ import annotations

from pathlib import Path


OUTPUT_SUBDIR = "output-pdf-tools"


def get_output_dir(reference_path: Path) -> Path:
    """
    Return (and create if needed) the output-pdf-tools dir for a given input file.

    If the input file is already inside an output-pdf-tools/ folder, reuse that
    same folder instead of nesting a new one inside it.
    """
    resolved = reference_path.resolve()
    # Walk up: if any parent is named OUTPUT_SUBDIR, use it directly
    for parent in resolved.parents:
        if parent.name == OUTPUT_SUBDIR:
            return parent
    out_dir = resolved.parent / OUTPUT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def safe_output_path(output_dir: Path, filename: str, overwrite: bool, operation: str = "") -> Path:
    """
    Return a safe output Path, appending the operation name to whatever stem the
    input file already has — so chained operations accumulate naturally:

      sample.pdf                           -> sample-compressed.pdf
      sample-compressed.pdf                -> sample-compressed-normalized.pdf
      sample-compressed-normalized.pdf exists, overwrite=False
                                           -> sample-compressed-normalized_1.pdf
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

"""Shared pytest fixtures for pdf-tools tests."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfWriter


# ── helpers ──────────────────────────────────────────────────────────────────

def _write_blank_pdf(path: Path, pages: int = 1, width: int = 595, height: int = 842) -> Path:
    """Write a real (but blank) PDF to *path* and return the path."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=width, height=height)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        writer.write(fh)
    return path


def _write_image(path: Path, mode: str = "RGB", size: tuple[int, int] = (100, 80)) -> Path:
    """Write a tiny solid-colour PNG/JPEG/BMP and return the path."""
    img = Image.new(mode, size, color=(200, 100, 50) if mode == "RGB" else 200)
    suffix = path.suffix.lower()
    fmt_map = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".bmp": "BMP"}
    fmt = fmt_map.get(suffix, "PNG")
    if mode != "RGB" and fmt == "JPEG":
        img = img.convert("RGB")
    img.save(str(path), fmt)
    return path


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp(tmp_path: Path) -> Path:
    """Alias for tmp_path for brevity."""
    return tmp_path


@pytest.fixture
def single_pdf(tmp_path: Path) -> Path:
    return _write_blank_pdf(tmp_path / "single.pdf", pages=1)


@pytest.fixture
def two_page_pdf(tmp_path: Path) -> Path:
    return _write_blank_pdf(tmp_path / "two_page.pdf", pages=2)


@pytest.fixture
def landscape_pdf(tmp_path: Path) -> Path:
    return _write_blank_pdf(tmp_path / "landscape.pdf", pages=1, width=842, height=595)


@pytest.fixture
def multi_pdfs(tmp_path: Path) -> list[Path]:
    """Three PDFs: a.pdf (1p), b.pdf (2p), c.pdf (1p)."""
    return [
        _write_blank_pdf(tmp_path / "a.pdf", pages=1),
        _write_blank_pdf(tmp_path / "b.pdf", pages=2),
        _write_blank_pdf(tmp_path / "c.pdf", pages=1),
    ]


@pytest.fixture
def png_image(tmp_path: Path) -> Path:
    return _write_image(tmp_path / "photo.png", mode="RGB")


@pytest.fixture
def rgba_image(tmp_path: Path) -> Path:
    return _write_image(tmp_path / "alpha.png", mode="RGBA")


@pytest.fixture
def jpeg_image(tmp_path: Path) -> Path:
    return _write_image(tmp_path / "snap.jpg", mode="RGB")


@pytest.fixture
def bmp_image(tmp_path: Path) -> Path:
    return _write_image(tmp_path / "bitmap.bmp", mode="RGB")


@pytest.fixture
def batch_folder(tmp_path: Path) -> Path:
    """A folder with 2 PDFs + 1 PNG, ready for batch processing."""
    folder = tmp_path / "batch_input"
    folder.mkdir()
    _write_blank_pdf(folder / "doc1.pdf", pages=1)
    _write_blank_pdf(folder / "doc2.pdf", pages=2)
    _write_image(folder / "scan.png", mode="RGB")
    return folder

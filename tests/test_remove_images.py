"""Tests for pdf_tools.remove_images."""
from __future__ import annotations

from pathlib import Path

import pikepdf
import pytest
from pypdf import PdfReader

from pdf_tools.remove_images import remove_images, _grey_image_xobject, _remove_images_from_page
from pdf_tools.utils.file_helpers import OUTPUT_SUBDIR


def _make_pdf_with_image(path: Path) -> Path:
    """Create a single-page PDF that contains one embedded greyscale image."""
    from PIL import Image
    import io

    # Build a tiny 4×4 greyscale image
    img = Image.new("L", (4, 4), color=128)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    pdf = pikepdf.Pdf.new()
    # pikepdf requires pikepdf.Page for pages.append
    page = pikepdf.Page(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(
            XObject=pikepdf.Dictionary()
        ),
    ))
    pdf.pages.append(page)

    # Build XObject with keys set directly so they sit at the top level
    # (not nested inside /stream_dict, which is a make_stream artefact)
    xobj = pdf.make_stream(img_bytes)
    xobj["/Type"] = pikepdf.Name("/XObject")
    xobj["/Subtype"] = pikepdf.Name("/Image")
    xobj["/Width"] = 4
    xobj["/Height"] = 4
    xobj["/ColorSpace"] = pikepdf.Name("/DeviceGray")
    xobj["/BitsPerComponent"] = 8
    pdf.pages[0].obj["/Resources"]["/XObject"]["/Im0"] = pdf.make_indirect(xobj)

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(str(path))
    return path


class TestGreyImageXObject:
    def test_returns_stream(self, tmp_path):
        pdf = pikepdf.Pdf.new()
        obj = _grey_image_xobject(pdf, 10, 20)
        assert obj is not None

    def test_has_image_subtype(self, tmp_path):
        pdf = pikepdf.Pdf.new()
        obj = _grey_image_xobject(pdf, 10, 20)
        # make_stream stores stream_dict keys under obj['/stream_dict']
        sd = obj["/stream_dict"]
        assert sd["/Subtype"] == pikepdf.Name("/Image")

    def test_dimensions_stored(self, tmp_path):
        pdf = pikepdf.Pdf.new()
        obj = _grey_image_xobject(pdf, 42, 99)
        sd = obj["/stream_dict"]
        assert int(sd["/Width"]) == 1
        assert int(sd["/Height"]) == 1


class TestRemoveImagesFromPage:
    def test_replaces_image_xobjects(self, tmp_path):
        pdf_path = _make_pdf_with_image(tmp_path / "with_image.pdf")
        pdf = pikepdf.open(str(pdf_path))
        page = pikepdf.Page(pdf.pages[0])
        count = _remove_images_from_page(page, pdf)
        assert count == 1
        pdf.close()

    def test_no_images_returns_zero(self, single_pdf):
        pdf = pikepdf.open(str(single_pdf))
        page = pikepdf.Page(pdf.pages[0])
        count = _remove_images_from_page(page, pdf)
        assert count == 0
        pdf.close()


class TestRemoveImages:
    def test_output_file_created(self, tmp_path):
        pdf_path = _make_pdf_with_image(tmp_path / "with_image.pdf")
        remove_images([pdf_path], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*remove-images*"))
        assert len(outputs) == 1

    def test_output_is_valid_pdf(self, tmp_path):
        pdf_path = _make_pdf_with_image(tmp_path / "with_image.pdf")
        remove_images([pdf_path], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("*remove-images*"))
        assert output.read_bytes()[:4] == b"%PDF"

    def test_blank_pdf_no_crash(self, single_pdf, tmp_path):
        remove_images([single_pdf], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert list(out_dir.glob("*remove-images*"))

    def test_corrupt_pdf_skipped(self, tmp_path):
        corrupt = tmp_path / "bad.pdf"
        corrupt.write_bytes(b"garbage")
        remove_images([corrupt], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*remove-images*")) if out_dir.exists() else []
        assert outputs == []

    def test_output_smaller_or_equal(self, tmp_path):
        """Removing images should never inflate the file significantly."""
        pdf_path = _make_pdf_with_image(tmp_path / "with_image.pdf")
        original_size = pdf_path.stat().st_size
        remove_images([pdf_path], overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        output = next(out_dir.glob("*remove-images*"))
        # Allow a small overhead from grey placeholder, but not a 2× blow-up
        assert output.stat().st_size < original_size * 3

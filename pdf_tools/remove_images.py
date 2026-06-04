"""remove-images: replace all raster images with same-size grey boxes."""
from __future__ import annotations

from pathlib import Path

import pikepdf
from pikepdf import Dictionary, Name, Array
from pikepdf.canvas import Canvas, ContentStreamBuilder
from pypdf import PdfReader

from pdf_tools.utils.file_helpers import get_output_dir, safe_output_path, size_delta, fmt_size
from pdf_tools.utils import logger as log


def _grey_image_xobject(pdf: pikepdf.Pdf, width: int, height: int) -> pikepdf.Object:
    """
    Build a grey rectangle as an Image XObject (1×1 grey pixel, scaled via the CTM).
    This replaces the original image at the same location without touching layout.
    """
    grey_pixel = bytes([180])  # mid-grey
    return pdf.make_stream(
        grey_pixel,
        stream_dict=Dictionary(
            Type=Name("/XObject"),
            Subtype=Name("/Image"),
            Width=1,
            Height=1,
            ColorSpace=Name("/DeviceGray"),
            BitsPerComponent=8,
            Filter=Name("/FlateDecode"),
        ),
    )


def _remove_images_from_page(page: pikepdf.Page, pdf: pikepdf.Pdf) -> int:
    """Replace every Image XObject on a page with a grey placeholder. Returns count."""
    resources = page.obj.get("/Resources", Dictionary())
    xobjects = resources.get("/XObject", Dictionary())
    replaced = 0

    for key in list(xobjects.keys()):
        xobj = xobjects[key]
        if xobj.get("/Subtype") == Name("/Image"):
            # Grab dimensions for logging; replace with grey placeholder
            w = int(xobj.get("/Width", 1))
            h = int(xobj.get("/Height", 1))
            grey = _grey_image_xobject(pdf, w, h)
            xobjects[key] = pdf.make_indirect(grey)
            replaced += 1

    return replaced


def remove_images(input_paths: list[Path], overwrite: bool) -> None:
    log.section("remove-images")

    rows: list[tuple[str, ...]] = []

    for src in input_paths:
        log.processing(src)
        size_before = src.stat().st_size

        try:
            pdf = pikepdf.open(str(src))
        except Exception as exc:
            log.error(src, str(exc))
            continue

        total_replaced = 0
        for i, page in enumerate(pdf.pages):
            replaced = _remove_images_from_page(pikepdf.Page(page), pdf)
            if replaced:
                log.info(f"page {i + 1}: replaced {replaced} image(s) with grey box(es)")
            total_replaced += replaced

        out_dir = get_output_dir(src)
        out_path = safe_output_path(out_dir, src.name, overwrite, operation="remove-images")

        try:
            pdf.save(
                str(out_path),
                compress_streams=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )
        except Exception as exc:
            log.error(src, f"save failed: {exc}")
            pdf.close()
            continue
        finally:
            pdf.close()

        size_after = out_path.stat().st_size
        delta = size_delta(size_before, size_after)
        log.produced(out_path, f"{total_replaced} images removed  |  {delta}")
        rows.append((
            src.name,
            str(total_replaced),
            fmt_size(size_before),
            fmt_size(size_after),
            delta.split("(")[1].rstrip(")"),
        ))

    if rows:
        log.subsection("Summary")
        log.summary_table(rows, ["File", "Images removed", "Before", "After", "Change"])

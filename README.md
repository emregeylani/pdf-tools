# pdf-tools

A command-line toolkit for batch PDF processing.

## Requirements

- Python 3.9+

## Setup

```bash
python3 -m venv .venv-pdf
source .venv-pdf/bin/activate
pip install -r requirements.txt
```

## Commands

| Command | Description |
|---|---|
| `normalize-page-size` | Resize all pages to A4, preserving landscape/portrait orientation |
| `image-to-pdf` | Convert PNG/JPG/JPEG/BMP images to same-named PDF files |
| `concatenate` | Merge PDFs alphabetically into `concatenated-YYYYMMDD.pdf` |
| `compress` | Reduce file size via stream and object-stream optimisation |
| `remove-images` | Replace raster images with same-size grey placeholder boxes |

## Usage

```bash
python3 pdf_tools normalize-page-size scan1.pdf scan2.pdf
python3 pdf_tools image-to-pdf photo.jpg diagram.png
python3 pdf_tools concatenate *.pdf
python3 pdf_tools compress report.pdf --level aggressive
python3 pdf_tools remove-images heavy.pdf
```

### Options

`--overwrite` — overwrite existing output files instead of adding a numeric suffix (`_1`, `_2`, …).

All output files are written to an `output-pdf-tools/` subfolder next to each input file.
```bash
python3 pdf_tools batch invoices/ reports/ archive/
python3 pdf_tools batch invoices/ reports/ --compress   # also compress output
```

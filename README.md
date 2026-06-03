# pdf-tools

A command-line toolkit for batch PDF processing.

## Requirements

- Python 3.9+

## Installation

```bash
pip install -r requirements.txt
pip install -e .
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
# Normalize page sizes to A4
pdf-tools normalize-page-size scan1.pdf scan2.pdf

# Convert images to PDF
pdf-tools image-to-pdf photo.jpg diagram.png

# Merge all PDFs in the current folder alphabetically
pdf-tools concatenate *.pdf

# Compress a PDF (light or aggressive)
pdf-tools compress report.pdf --level aggressive

# Strip all images, replace with grey boxes
pdf-tools remove-images heavy.pdf
```

### Options

`--overwrite` — overwrite existing output files instead of adding a numeric suffix (`_1`, `_2`, …).

All output files are written to a `pdf-tools-output/` subfolder next to each input file.

## Running without installation

```bash
python3 pdf-tools
```

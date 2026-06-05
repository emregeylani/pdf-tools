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
| `batch` | Per-folder pipeline: images → PDF, merge, normalize, compress |

## Usage

```bash
python3 pdf_tools normalize-page-size scan1.pdf scan2.pdf
python3 pdf_tools image-to-pdf photo.jpg diagram.png
python3 pdf_tools concatenate *.pdf
python3 pdf_tools compress report.pdf
python3 pdf_tools compress report.pdf --level aggressive
python3 pdf_tools remove-images heavy.pdf
```

### `batch` — folder pipeline

Processes one or more folders end-to-end:
1. Converts images (PNG/JPG/JPEG/BMP) to PDF
2. Normalizes all pages to A4 *(on by default)*
3. Merges everything alphabetically into `<folder>-YYYYMMDD.pdf`
4. Compresses the result *(on by default)*

```bash
python3 pdf_tools batch invoices/ reports/ archive/
python3 pdf_tools batch invoices/ --no-normalize   # skip A4 normalization
python3 pdf_tools batch invoices/ --no-compress    # skip compression
```

### Options

| Option | Applies to | Description |
|---|---|---|
| `--overwrite` | all commands | Overwrite existing output files instead of adding a numeric suffix (`_1`, `_2`, …) |
| `--level light\|aggressive` | `compress` | Compression preset — `light` (default) or `aggressive` (recompresses Flate streams) |
| `--no-normalize` | `batch` | Skip A4 normalization (normalization is **on** by default) |
| `--no-compress` | `batch` | Skip compression (compression is **on** by default) |
| `--version` | top-level | Print version and exit |

### Output location & naming

All output files are written to an `output-pdf-tools/` subfolder next to each input file. Operation names are appended to the stem, so chained operations accumulate naturally:

```
sample.pdf  →  sample-compressed.pdf  →  sample-compressed-normalized.pdf
```

If a file already exists and `--overwrite` is not set, a numeric suffix is added: `sample-compressed_1.pdf`.

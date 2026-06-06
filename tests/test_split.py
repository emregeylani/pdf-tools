"""Tests for pdf_tools.split."""
from __future__ import annotations

import pytest
from pypdf import PdfReader

from pdf_tools.split import parse_pages, split
from pdf_tools.utils.file_helpers import OUTPUT_SUBDIR


# ── parse_pages ───────────────────────────────────────────────────────────────

class TestParsePages:

    def test_single_page(self):
        assert parse_pages("3", 10) == [3]

    def test_range(self):
        assert parse_pages("1-3", 10) == [1, 2, 3]

    def test_mixed(self):
        assert parse_pages("1-3,5,8", 10) == [1, 2, 3, 5, 8]

    def test_duplicates_removed(self):
        assert parse_pages("1,1,2", 5) == [1, 2]

    def test_result_is_sorted(self):
        assert parse_pages("5,1,3", 10) == [1, 3, 5]

    def test_first_page(self):
        assert parse_pages("1", 5) == [1]

    def test_last_page(self):
        assert parse_pages("5", 5) == [5]

    def test_full_range(self):
        assert parse_pages("1-5", 5) == [1, 2, 3, 4, 5]

    def test_whitespace_tolerant(self):
        assert parse_pages("1 - 3 , 5", 10) == [1, 2, 3, 5]

    # ── error cases ───────────────────────────────────────────────────────────

    def test_zero_page(self):
        with pytest.raises(ValueError, match="≥ 1"):
            parse_pages("0", 5)

    def test_page_exceeds_total(self):
        with pytest.raises(ValueError, match="does not exist"):
            parse_pages("6", 5)

    def test_range_end_exceeds_total(self):
        with pytest.raises(ValueError, match="does not exist"):
            parse_pages("3-9", 5)

    def test_range_start_exceeds_total(self):
        with pytest.raises(ValueError, match="does not exist"):
            parse_pages("7-9", 5)

    def test_reversed_range(self):
        with pytest.raises(ValueError, match="start must be ≤"):
            parse_pages("5-2", 10)

    def test_non_integer(self):
        with pytest.raises(ValueError, match="Non-integer"):
            parse_pages("abc", 5)

    def test_non_integer_in_range(self):
        with pytest.raises(ValueError, match="Non-integer"):
            parse_pages("1-abc", 5)

    def test_malformed_range_trailing_dash(self):
        with pytest.raises(ValueError, match="Malformed"):
            parse_pages("1-", 5)

    def test_malformed_range_leading_dash(self):
        with pytest.raises(ValueError, match="Malformed"):
            parse_pages("-3", 5)

    def test_empty_spec(self):
        with pytest.raises(ValueError, match="No pages selected"):
            parse_pages("", 5)

    def test_comma_only(self):
        with pytest.raises(ValueError, match="No pages selected"):
            parse_pages(",,,", 5)


# ── split (integration) ───────────────────────────────────────────────────────

class TestSplit:

    def test_output_file_created(self, two_page_pdf, tmp_path):
        split([two_page_pdf], "1", overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert list(out_dir.glob("*split*"))

    def test_correct_page_count(self, tmp_path):
        from pypdf import PdfWriter
        pdf = tmp_path / "five.pdf"
        w = PdfWriter()
        for _ in range(5):
            w.add_blank_page(595, 842)
        with open(pdf, "wb") as f:
            w.write(f)

        split([pdf], "1-3,5", overwrite=True)
        out = next((tmp_path / OUTPUT_SUBDIR).glob("*split*"))
        assert len(PdfReader(str(out)).pages) == 4

    def test_output_filename_contains_range(self, two_page_pdf, tmp_path):
        split([two_page_pdf], "1-2", overwrite=True)
        out = next((tmp_path / OUTPUT_SUBDIR).glob("*split*"))
        assert "1to2" in out.name

    def test_output_is_valid_pdf(self, two_page_pdf, tmp_path):
        split([two_page_pdf], "1", overwrite=True)
        out = next((tmp_path / OUTPUT_SUBDIR).glob("*split*"))
        assert out.read_bytes()[:4] == b"%PDF"

    def test_invalid_page_raises_systemexit(self, single_pdf):
        with pytest.raises(SystemExit):
            split([single_pdf], "99", overwrite=True)

    def test_corrupt_pdf_skipped(self, tmp_path):
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf")
        split([bad], "1", overwrite=True)
        out_dir = tmp_path / OUTPUT_SUBDIR
        outputs = list(out_dir.glob("*split*")) if out_dir.exists() else []
        assert outputs == []

    def test_overwrite_false_increments(self, two_page_pdf, tmp_path):
        split([two_page_pdf], "1", overwrite=False)
        split([two_page_pdf], "1", overwrite=False)
        out_dir = tmp_path / OUTPUT_SUBDIR
        assert len(list(out_dir.glob("*split*"))) == 2

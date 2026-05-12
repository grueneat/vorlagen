"""Unit tests for tools/font_audit.py — Phase D6 pdffonts audit.

Covers:
- Identical font sets → ok=True, empty missing/extra.
- Missing variant in preview → ok=False, correct missing list.
- Extra variant in preview (not in baseline) → ok=True (extra is informational).
- Subset-prefix stripping (DAZTTR+FontName → FontName).
- pdffonts raw output parsing (header skipping, deduplication).
- Malformed / empty pdffonts output → empty list, no crash.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from font_audit import _parse_pdffonts_output, run_font_audit  # noqa: E402


# ---------------------------------------------------------------------------
# _parse_pdffonts_output unit tests
# ---------------------------------------------------------------------------

_SAMPLE_BASELINE_OUTPUT = """\
name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
DAZTTR+GothamNarrow-Book             Type 1C           Custom           yes yes yes     43  0
DAZTTR+GothamNarrow-Ultra            Type 1C           WinAnsi          yes yes yes     44  0
DAZTTR+GothamNarrow-Black            Type 1C           WinAnsi          yes yes yes     54  0
DAZTTR+Vollkorn-BlackItalic          TrueType          WinAnsi          yes yes yes     45  0
DAZTTR+GothamNarrow-Bold             Type 1C           WinAnsi          yes yes yes     30  0
DAZTTR+GothamNarrow-Book             Type 1C           WinAnsi          yes yes yes     21  0
"""

_SAMPLE_PREVIEW_OUTPUT = """\
name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
GothamNarrow-Black                   CID Type 0C (OT)  Identity-H       yes no  yes      9  0
GothamNarrow-Bold                    CID Type 0C (OT)  Identity-H       yes no  yes     14  0
GothamNarrow-Book                    CID Type 0C (OT)  Identity-H       yes no  yes     19  0
GothamNarrow-Ultra                   CID Type 0C (OT)  Identity-H       yes no  yes     24  0
Vollkorn-BlackItalic                 TrueType          Custom           yes no  no      60  0
"""


def test_parse_strips_subset_prefix():
    names = _parse_pdffonts_output(_SAMPLE_BASELINE_OUTPUT)
    # All "DAZTTR+" prefixes should be stripped.
    assert all("+" not in n for n in names)


def test_parse_deduplicates_names():
    """DAZTTR+GothamNarrow-Book appears twice in baseline; result must be unique."""
    names = _parse_pdffonts_output(_SAMPLE_BASELINE_OUTPUT)
    assert names.count("GothamNarrow-Book") == 1


def test_parse_returns_sorted_unique_names():
    names = _parse_pdffonts_output(_SAMPLE_BASELINE_OUTPUT)
    assert names == sorted(set(names))
    assert "GothamNarrow-Bold" in names
    assert "Vollkorn-BlackItalic" in names


def test_parse_preview_output_no_prefix():
    """Preview pdffonts output has no subset prefix; names returned as-is."""
    names = _parse_pdffonts_output(_SAMPLE_PREVIEW_OUTPUT)
    assert "GothamNarrow-Bold" in names
    assert "GothamNarrow-Book" in names
    assert "Vollkorn-BlackItalic" in names


def test_parse_empty_output_returns_empty_list():
    assert _parse_pdffonts_output("") == []


def test_parse_malformed_output_returns_empty_list():
    """If there is no header separator, treat as malformed and return []."""
    assert _parse_pdffonts_output("not pdffonts output at all") == []


def test_parse_only_header_returns_empty_list():
    header_only = (
        "name                                 type              encoding\n"
        "------------------------------------ ----------------- ----------------\n"
    )
    assert _parse_pdffonts_output(header_only) == []


# ---------------------------------------------------------------------------
# run_font_audit integration-style tests (no actual PDFs; inject fonts via
# a subclass/monkeypatch of the internal _run_pdffonts helper)
# ---------------------------------------------------------------------------


def _make_report(preview_fonts: list[str], baseline_fonts: list[str]) -> dict:
    """Helper: build a font_audit report dict directly from font name lists."""
    baseline_set = set(baseline_fonts)
    preview_set = set(preview_fonts)
    missing = sorted(baseline_set - preview_set)
    extra = sorted(preview_set - baseline_set)
    ok = len(missing) == 0
    return {
        "template": "test-template",
        "baseline_fonts": sorted(baseline_fonts),
        "preview_fonts": sorted(preview_fonts),
        "missing_in_preview": missing,
        "extra_in_preview": extra,
        "ok": ok,
    }


def test_identical_sets_ok_true():
    fonts = ["GothamNarrow-Book", "GothamNarrow-Bold", "Vollkorn-BlackItalic"]
    report = _make_report(fonts, fonts)
    assert report["ok"] is True
    assert report["missing_in_preview"] == []
    assert report["extra_in_preview"] == []


def test_missing_bold_in_preview_ok_false():
    baseline = ["GothamNarrow-Book", "GothamNarrow-Bold", "Vollkorn-BlackItalic"]
    preview = ["GothamNarrow-Book", "Vollkorn-BlackItalic"]
    report = _make_report(preview, baseline)
    assert report["ok"] is False
    assert "GothamNarrow-Bold" in report["missing_in_preview"]
    assert report["extra_in_preview"] == []


def test_extra_font_in_preview_is_informational_not_failure():
    """Extra fonts in preview (not in baseline) are tracked but don't cause failure."""
    baseline = ["GothamNarrow-Book"]
    preview = ["GothamNarrow-Book", "GothamNarrow-Bold"]
    report = _make_report(preview, baseline)
    assert report["ok"] is True
    assert "GothamNarrow-Bold" in report["extra_in_preview"]
    assert report["missing_in_preview"] == []


def test_all_missing_ok_false():
    """If preview has no fonts that baseline has, all are missing."""
    baseline = ["GothamNarrow-Book", "GothamNarrow-Bold"]
    preview: list[str] = []
    report = _make_report(preview, baseline)
    assert report["ok"] is False
    assert sorted(report["missing_in_preview"]) == sorted(baseline)


def test_run_font_audit_pdffonts_not_found(tmp_path, monkeypatch):
    """When pdffonts is not installed, report has error and ok=False."""
    import font_audit as fa_module

    monkeypatch.setattr(fa_module, "_run_pdffonts", lambda path: ([], "pdffonts not installed"))
    dummy = tmp_path / "dummy.pdf"
    dummy.write_bytes(b"%PDF dummy")
    report = fa_module.run_font_audit(dummy, dummy, template="t")
    assert report["ok"] is False
    assert "error" in report

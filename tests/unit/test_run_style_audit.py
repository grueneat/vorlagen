"""Unit tests for tools/run_style_audit.py — Phase F per-Run style fidelity audit.

Covers:
1.  test_subset_prefix_stripped — 'DAZTTR+GothamNarrow-Bold' → 'GothamNarrow-Bold'
2.  test_size_within_tolerance_no_large_drift — 37.93 vs 38.0 → small drift, not large
3.  test_size_outside_tolerance_drift_reported — 11.0 vs 14.0 → large drift
4.  test_color_normalize_rgb_tuple — (1.0, 0.84, 0.0) → '#ffd700'
5.  test_color_normalize_gray — 0.5 → 'gray:128'
6.  test_color_normalize_cmyk — (0, 0, 1.0, 0) → 'cmyk:0.0,0.0,1.0,0.0'
7.  test_common_word_filter_excludes_high_frequency — 'et' × 6 → not in style_drifts
8.  test_unique_word_drift_reported — uniquely-occurring word with style drift → reported
9.  test_severity_classification — wrong-font → large; small color delta → small; sub-threshold → None
10. test_empty_word_lists — both PDFs empty → ok=true, no crash
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from run_style_audit import (  # noqa: E402
    _classify_severity,
    _normalize_color,
    _strip_subset_prefix,
    extract_words_with_style,
    run_style_audit,
    _yaml_dump,
    SIZE_SMALL_THRESHOLD_PT,
    SIZE_LARGE_THRESHOLD_PT,
    COLOR_SMALL_THRESHOLD,
    COLOR_LARGE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf(tmp_path: Path, name: str, text_lines: list[str]) -> Path:
    """Create a minimal Type1/Helvetica PDF with text_lines on one page."""
    content_ops: list[str] = []
    y = 720
    for line in text_lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_ops.append(f"BT /F1 12 Tf 72 {y} Td ({safe}) Tj ET")
        y -= 40
    stream_body = "\n".join(content_ops)
    stream_bytes = stream_body.encode("latin-1", errors="replace")
    stream_len = len(stream_bytes)

    objects: list[bytes] = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    objects.append(
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("ascii")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    pdf_parts: list[bytes] = [b"%PDF-1.4\n"]
    offsets: list[int] = []
    pos = len(pdf_parts[0])
    for obj in objects:
        offsets.append(pos)
        pdf_parts.append(obj)
        pos += len(obj)

    xref_offset = pos
    xref_lines = [f"xref\n0 {len(objects) + 1}\n", "0000000000 65535 f \n"]
    for off in offsets:
        xref_lines.append(f"{off:010d} 00000 n \n")
    pdf_parts.append("".join(xref_lines).encode("ascii"))
    pdf_parts.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )

    pdf_path = tmp_path / name
    pdf_path.write_bytes(b"".join(pdf_parts))
    return pdf_path


def _word(text: str, page: int, fontname: str = "TestFont-Regular",
          size: float = 12.0, color: str = "#000000") -> dict[str, Any]:
    """Build a synthetic word record as returned by extract_words_with_style."""
    return {
        "page": page,
        "text": text,
        "fontname": fontname,
        "size": round(size, 2),
        "color": color,
    }


def _patch_extract(monkeypatch, baseline_words: list[dict], preview_words: list[dict]):
    """Monkeypatch extract_words_with_style to return synthetic word lists."""
    import run_style_audit as rsa_module

    def fake_extract(pdf_path: Path) -> list[dict[str, Any]]:
        if "baseline" in str(pdf_path):
            return baseline_words
        return preview_words

    monkeypatch.setattr(rsa_module, "extract_words_with_style", fake_extract)


# ---------------------------------------------------------------------------
# Test 1: subset-prefix stripping
# ---------------------------------------------------------------------------

def test_subset_prefix_stripped():
    """'DAZTTR+GothamNarrow-Bold' → 'GothamNarrow-Bold'."""
    assert _strip_subset_prefix("DAZTTR+GothamNarrow-Bold") == "GothamNarrow-Bold"
    assert _strip_subset_prefix("GothamNarrow-Bold") == "GothamNarrow-Bold"
    assert _strip_subset_prefix("ABCDEF+Vollkorn-BlackItalic") == "Vollkorn-BlackItalic"
    # Subset prefix stripped in extract_words_with_style
    # (tested via real extraction below if PDF available; here we test the helper)


# ---------------------------------------------------------------------------
# Test 2: size within tolerance → small drift (not large)
# ---------------------------------------------------------------------------

def test_size_within_tolerance_no_large_drift(tmp_path, monkeypatch):
    """37.93 vs 38.0 (diff=0.07pt, well below large threshold) → small drift only if color differs enough, else None."""
    # diff=0.07pt < SIZE_SMALL_THRESHOLD_PT (0.5) → classify as None (below all thresholds)
    baseline_words = [_word("dreizeilige", 0, "Vollkorn-BlackItalic", 37.93, "#ffd700")]
    preview_words = [_word("dreizeilige", 0, "Vollkorn-BlackItalic", 38.0, "#ffd700")]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(preview_pdf, baseline_pdf, template="test")
    # size diff = 0.07pt < 0.5pt threshold → NOT reported (sub-threshold)
    assert report["ok"] is True
    assert report["style_drift_count"] == 0


def test_size_small_drift_in_small_range(tmp_path, monkeypatch):
    """Size diff 0.7pt (> 0.5pt small, <= 1.0pt large) → small severity."""
    baseline_words = [_word("Word", 0, "Vollkorn-BlackItalic", 12.0, "#000000")]
    preview_words = [_word("Word", 0, "Vollkorn-BlackItalic", 12.7, "#000000")]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(preview_pdf, baseline_pdf, template="test")
    assert report["style_drift_count"] == 1
    assert report["style_drifts"][0]["severity"] == "small"
    assert report["ok"] is True  # ok=True for small-only drifts


# ---------------------------------------------------------------------------
# Test 3: size outside large tolerance → large drift
# ---------------------------------------------------------------------------

def test_size_outside_tolerance_drift_reported(tmp_path, monkeypatch):
    """11.0 vs 14.0 (diff=3.0pt > SIZE_LARGE_THRESHOLD_PT=1.0) → large drift."""
    baseline_words = [_word("Headline", 0, "GothamNarrow-Ultra", 11.0, "#ffffff")]
    preview_words = [_word("Headline", 0, "GothamNarrow-Ultra", 14.0, "#ffffff")]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(preview_pdf, baseline_pdf, template="test")
    assert report["ok"] is False
    assert report["style_drift_count"] == 1
    drift = report["style_drifts"][0]
    assert drift["severity"] == "large"
    assert abs(drift["drift"]["size_pt"] - 3.0) < 0.01
    assert drift["drift"]["fontname"] is False  # font matches


# ---------------------------------------------------------------------------
# Test 4: _normalize_color — RGB tuple
# ---------------------------------------------------------------------------

def test_color_normalize_rgb_tuple():
    """(1.0, 0.84, 0.0) → '#ffd700' (gold)."""
    result = _normalize_color((1.0, 0.84, 0.0))
    # 0.84 × 255 = 214.2 → 214 = d6 (not d7)
    assert result.startswith("#")
    assert result == "#ffd600"  # precise: round(0.84×255)=214=0xd6 → #ffd600
    # Also test a clean primary
    assert _normalize_color((1.0, 0.0, 0.0)) == "#ff0000"
    assert _normalize_color((0.0, 0.0, 0.0)) == "#000000"
    assert _normalize_color((1.0, 1.0, 1.0)) == "#ffffff"


def test_color_normalize_rgb_tuple_gold():
    """Test exact gold color used in spec example."""
    # Gold: r=255, g=215, b=0 → #ffd700
    # As floats: (255/255, 215/255, 0/255) = (1.0, 0.8431..., 0.0)
    result = _normalize_color((1.0, 215 / 255, 0.0))
    assert result == "#ffd700"


# ---------------------------------------------------------------------------
# Test 5: _normalize_color — grayscale
# ---------------------------------------------------------------------------

def test_color_normalize_gray():
    """0.5 → 'gray:128' (round(0.5*255) = round(127.5) = 128)."""
    assert _normalize_color(0.5) == "gray:128"
    assert _normalize_color(0.0) == "gray:0"
    assert _normalize_color(1.0) == "gray:255"
    assert _normalize_color(None) == ""


# ---------------------------------------------------------------------------
# Test 6: _normalize_color — CMYK
# ---------------------------------------------------------------------------

def test_color_normalize_cmyk():
    """(0, 0, 1.0, 0) → 'cmyk:0.0,0.0,1.0,0.0'."""
    result = _normalize_color((0, 0, 1.0, 0))
    assert result == "cmyk:0.0,0.0,1.0,0.0"
    result2 = _normalize_color((0.85, 0.35, 0.95, 0.10))
    assert result2.startswith("cmyk:")


# ---------------------------------------------------------------------------
# Test 7: common-word filter excludes high-frequency words
# ---------------------------------------------------------------------------

def test_common_word_filter_excludes_high_frequency(tmp_path, monkeypatch):
    """'et' appearing 6 times on page → excluded from style_drifts."""
    common_threshold = 5
    # 6 "et" words in baseline with fontname A; 6 in preview with fontname B (large drift)
    baseline_words = [
        _word("et", 0, "GothamNarrow-Book", 10.0, "#000000")
        for _ in range(6)
    ]
    preview_words = [
        _word("et", 0, "Vollkorn-Regular", 10.0, "#000000")  # different font → large
        for _ in range(6)
    ]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(
        preview_pdf, baseline_pdf, template="test",
        common_word_threshold=common_threshold,
    )
    # All 6 "et" drifts should be suppressed by common-word filter
    assert report["style_drifts"] == []
    assert report["style_drift_count"] == 0
    assert report["suppressed_common_word_drifts_count"] == 6
    # ok=True because no large-severity drifts remain after filter
    assert report["ok"] is True


# ---------------------------------------------------------------------------
# Test 8: unique word drift reported alongside suppression
# ---------------------------------------------------------------------------

def test_unique_word_drift_reported(tmp_path, monkeypatch):
    """Uniquely-occurring word with font drift IS reported; common word is suppressed."""
    # 6 "et" words → suppressed
    baseline_words = [_word("et", 0, "GothamNarrow-Book", 10.0) for _ in range(6)]
    preview_words = [_word("et", 0, "Vollkorn-Regular", 10.0) for _ in range(6)]

    # 1 unique "Kandidat" with wrong font → must be reported
    baseline_words.append(_word("Kandidat", 0, "GothamNarrow-Ultra", 38.0, "#ffffff"))
    preview_words.append(_word("Kandidat", 0, "GothamNarrow-Black", 38.0, "#ffffff"))

    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(
        preview_pdf, baseline_pdf, template="test",
        common_word_threshold=5,
    )
    assert report["style_drift_count"] == 1
    assert report["style_drifts"][0]["text"] == "Kandidat"
    assert report["style_drifts"][0]["severity"] == "large"
    assert report["suppressed_common_word_drifts_count"] == 6
    assert report["ok"] is False


# ---------------------------------------------------------------------------
# Test 9: severity classification
# ---------------------------------------------------------------------------

def test_severity_classification():
    """Wrong font → large; small color delta → small; sub-threshold → None."""
    # Wrong font → large regardless of size/color
    assert _classify_severity(True, 0.0, 0.0) == "large"

    # Size > 1.0pt → large
    assert _classify_severity(False, 1.5, 0.0) == "large"

    # Color delta > 30 → large
    assert _classify_severity(False, 0.0, 35.0) == "large"

    # Size 0.7pt (0.5 < x <= 1.0) → small
    assert _classify_severity(False, 0.7, 0.0) == "small"

    # Color delta 15 (5 < x <= 30) → small
    assert _classify_severity(False, 0.0, 15.0) == "small"

    # Sub-threshold: size 0.3pt, color delta 3 → None
    assert _classify_severity(False, 0.3, 3.0) is None

    # Exactly at large threshold boundary: 1.0pt → small (not large, > not >=)
    assert _classify_severity(False, 1.0, 0.0) == "small"

    # Exactly at small threshold boundary: 0.5pt → None (not small, > not >=)
    assert _classify_severity(False, 0.5, 0.0) is None


# ---------------------------------------------------------------------------
# Test 10: empty word lists → ok=True, no crash
# ---------------------------------------------------------------------------

def test_empty_word_lists(tmp_path, monkeypatch):
    """Both PDFs have no words → ok=True, style_drift_count=0, no crash."""
    _patch_extract(monkeypatch, [], [])

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(preview_pdf, baseline_pdf, template="test")
    assert report["ok"] is True
    assert report["style_drift_count"] == 0
    assert report["style_drifts"] == []
    assert report["baseline_word_count"] == 0
    assert report["preview_word_count"] == 0
    assert report["suppressed_common_word_drifts_count"] == 0


# ---------------------------------------------------------------------------
# Additional: _yaml_dump determinism
# ---------------------------------------------------------------------------

def test_yaml_dump_deterministic():
    """_yaml_dump produces identical output on two calls (sort_keys=True)."""
    report = {
        "template": "test",
        "style_drift_count": 1,
        "ok": False,
        "style_drifts": [{"text": "Foo", "severity": "large"}],
    }
    assert _yaml_dump(report) == _yaml_dump(report)
    output = _yaml_dump(report)
    top_level_keys = [
        line.split(":")[0]
        for line in output.splitlines()
        if line and line[0].isalpha() and ":" in line
    ]
    assert top_level_keys == sorted(top_level_keys)


def test_word_missing_from_preview_skipped(tmp_path, monkeypatch):
    """Word absent from preview is skipped (D7 handles presence; F only audits style)."""
    baseline_words = [
        _word("OnlyInBaseline", 0, "GothamNarrow-Ultra", 38.0),
        _word("InBoth", 0, "GothamNarrow-Ultra", 38.0),
    ]
    preview_words = [
        _word("InBoth", 0, "GothamNarrow-Ultra", 38.0),
    ]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(preview_pdf, baseline_pdf, template="test")
    # "OnlyInBaseline" not matched → skipped; "InBoth" matches with same style → ok
    assert report["ok"] is True
    assert report["style_drift_count"] == 0


def test_greedy_no_double_counting(tmp_path, monkeypatch):
    """Same word appears twice; greedy match consumes each preview word once."""
    # Two "Title" words in baseline — same font
    baseline_words = [
        _word("Title", 0, "GothamNarrow-Ultra", 38.0),
        _word("Title", 0, "GothamNarrow-Ultra", 38.0),
    ]
    # Two "Title" words in preview — first has wrong font, second matches
    preview_words = [
        _word("Title", 0, "Vollkorn-Regular", 38.0),   # wrong font
        _word("Title", 0, "GothamNarrow-Ultra", 38.0), # correct
    ]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(preview_pdf, baseline_pdf, template="test")
    # First baseline "Title" consumed preview[0] (wrong font) → large drift
    # Second baseline "Title" consumed preview[1] (correct) → no drift
    assert report["style_drift_count"] == 1
    assert report["style_drifts"][0]["severity"] == "large"


# ---------------------------------------------------------------------------
# #37 P1 task 3: extraction-engine disagreement surfacing
# ---------------------------------------------------------------------------

def test_engine_disagreement_warn_when_counts_diverge(tmp_path, monkeypatch):
    """pdftotext 444/444 vs pdfplumber 464/458 → warn=True, deltas reported."""
    # Build 464 baseline + 458 preview pdfplumber words (no style drift).
    baseline_words = [
        _word(f"w{i}", 0, "TestFont-Regular", 12.0, "#000000")
        for i in range(464)
    ]
    preview_words = [
        _word(f"w{i}", 0, "TestFont-Regular", 12.0, "#000000")
        for i in range(458)
    ]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(
        preview_pdf, baseline_pdf, template="test",
        text_render_audit_counts={"baseline": 444, "preview": 444},
    )
    eed = report["extraction_engine_disagreement"]
    assert eed["baseline_pdfplumber"] == 464
    assert eed["preview_pdfplumber"] == 458
    assert eed["baseline_pdftotext"] == 444
    assert eed["preview_pdftotext"] == 444
    assert abs(eed["baseline_delta_pct"] - 4.5) < 0.05  # 20/444 ≈ 4.5%
    assert abs(eed["preview_delta_pct"] - 3.15) < 0.1   # 14/444 ≈ 3.15%
    assert eed["warn"] is True


def test_engine_disagreement_no_warn_when_counts_match(tmp_path, monkeypatch):
    """Matching counts (444/444 both engines) → warn=False."""
    baseline_words = [
        _word(f"w{i}", 0, "TestFont-Regular", 12.0, "#000000")
        for i in range(444)
    ]
    preview_words = list(baseline_words)
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(
        preview_pdf, baseline_pdf, template="test",
        text_render_audit_counts={"baseline": 444, "preview": 444},
    )
    eed = report["extraction_engine_disagreement"]
    assert eed["warn"] is False
    assert eed["baseline_delta_pct"] == 0.0
    assert eed["preview_delta_pct"] == 0.0


def test_engine_disagreement_field_absent_when_no_counts(tmp_path, monkeypatch):
    """``text_render_audit_counts=None`` → field absent from report."""
    baseline_words = [_word("a", 0)]
    preview_words = [_word("a", 0)]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(preview_pdf, baseline_pdf, template="test")
    assert "extraction_engine_disagreement" not in report


def test_engine_disagreement_does_not_downgrade_ok_alone(tmp_path, monkeypatch):
    """Disagreement alone (no large style drifts) keeps ok=True. The plan says
    disagreement is a WARNING, not a FAIL — surfaced via issue_parts in
    render_pipeline.py but not via the ok flag.
    """
    baseline_words = [
        _word(f"w{i}", 0, "TestFont-Regular", 12.0, "#000000")
        for i in range(464)
    ]
    preview_words = [
        _word(f"w{i}", 0, "TestFont-Regular", 12.0, "#000000")
        for i in range(458)
    ]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(
        preview_pdf, baseline_pdf, template="test",
        text_render_audit_counts={"baseline": 444, "preview": 444},
    )
    # No font/size/color drift in synthetic input → no large drifts → ok=true
    assert report["ok"] is True
    assert report["extraction_engine_disagreement"]["warn"] is True


def test_engine_disagreement_threshold_1pct_exclusive(tmp_path, monkeypatch):
    """Exactly 1 % delta is not a warning; > 1 % is."""
    # 1 % of 100 = 1 → at 1 % warn=False (threshold is strictly > 1.0)
    baseline_words = [_word(f"w{i}", 0) for i in range(101)]
    preview_words = [_word(f"w{i}", 0) for i in range(100)]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_style_audit(
        preview_pdf, baseline_pdf, template="test",
        text_render_audit_counts={"baseline": 100, "preview": 100},
    )
    eed = report["extraction_engine_disagreement"]
    # baseline 101 vs 100 → 1.0 % delta exactly → warn=False (boundary)
    assert eed["baseline_delta_pct"] == 1.0
    assert eed["warn"] is False

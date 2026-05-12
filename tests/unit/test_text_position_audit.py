"""Unit tests for tools/text_position_audit.py — Phase D8 per-word position drift audit.

Covers:
1. Identical word positions → ok=True, empty deltas.
2. Preview word shifted >threshold → reported in large_deltas with correct dx/dy.
3. Preview word shifted <threshold → NOT in deltas (AA noise filter).
4. Word missing from preview → skipped (D7 catches presence, D8 only does position).
5. Multiple instances of same word → greedy nearest-match, no double-counting.
6. _yaml_dump produces deterministic sorted-key output.
7. Common-word filter excludes high-frequency words from large_deltas.
8. Unique word delta still reported when common-word filter applied.
9. suppressed_common_word_deltas_count reflects number of filtered deltas.

Tests use monkeypatching of extract_words_with_positions to avoid real PDFs
for the parametric position tests; a real minimal PDF is used for the extract
function smoke test.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from text_position_audit import (  # noqa: E402
    extract_words_with_positions,
    run_text_position_audit,
    _yaml_dump,
    _word_matches_pdftotext,
)


# ---------------------------------------------------------------------------
# Minimal PDF factory (shared helper; identical to the one in test_text_render_audit)
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


# ---------------------------------------------------------------------------
# Helper: mock out extract_words_with_positions for parametric position tests
# ---------------------------------------------------------------------------

def _patch_extract(monkeypatch, baseline_words: list[dict], preview_words: list[dict]):
    """Monkeypatch extract_words_with_positions to return synthetic word lists."""
    import text_position_audit as tpa_module

    call_count = [0]

    def fake_extract(pdf_path: Path) -> list[dict[str, Any]]:
        call_count[0] += 1
        if "baseline" in str(pdf_path):
            return baseline_words
        return preview_words

    monkeypatch.setattr(tpa_module, "extract_words_with_positions", fake_extract)


def _word(text, page, x0, y0, x1=None, y1=None):
    """Shorthand to build a word record dict."""
    if x1 is None:
        x1 = x0 + 30.0
    if y1 is None:
        y1 = y0 + 12.0
    return {"text": text, "page": page, "x0_pt": x0, "y0_pt": y0,
            "x1_pt": x1, "y1_pt": y1}


# ---------------------------------------------------------------------------
# Test 1: Identical word positions → ok=True, empty deltas
# ---------------------------------------------------------------------------

def test_identical_positions_ok(tmp_path, monkeypatch):
    words = [_word("Hello", 0, 72.0, 62.0), _word("World", 0, 102.0, 62.0)]
    _patch_extract(monkeypatch, words, words)
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")
    report = run_text_position_audit(preview_pdf, baseline_pdf, template="test")
    assert report["ok"] is True
    assert report["large_deltas"] == []
    assert report["large_deltas_count"] == 0


# ---------------------------------------------------------------------------
# Test 2: Preview word shifted >threshold → in large_deltas with correct dx/dy
# ---------------------------------------------------------------------------

def test_large_shift_reported(tmp_path, monkeypatch):
    threshold = 2.0
    baseline_words = [_word("Leonore", 0, 100.0, 200.0)]
    # Shift x by 14.3pt (well above threshold)
    preview_words = [_word("Leonore", 0, 114.3, 200.0)]
    _patch_extract(monkeypatch, baseline_words, preview_words)
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")
    report = run_text_position_audit(preview_pdf, baseline_pdf, template="test",
                                     large_delta_threshold_pt=threshold)
    assert report["ok"] is False
    assert report["large_deltas_count"] == 1
    delta = report["large_deltas"][0]
    assert delta["text"] == "Leonore"
    assert abs(delta["dx_pt"] - 14.3) < 0.05
    assert abs(delta["dy_pt"]) < 0.05
    assert delta["severity"] == "large"


# ---------------------------------------------------------------------------
# Test 3: Preview word shifted <threshold → NOT in deltas (AA noise filter)
# ---------------------------------------------------------------------------

def test_sub_threshold_shift_not_reported(tmp_path, monkeypatch):
    threshold = 2.0
    baseline_words = [_word("Das", 0, 100.0, 200.0)]
    # Shift x by only 1.0pt (below 2.0 threshold)
    preview_words = [_word("Das", 0, 101.0, 200.0)]
    _patch_extract(monkeypatch, baseline_words, preview_words)
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")
    report = run_text_position_audit(preview_pdf, baseline_pdf, template="test",
                                     large_delta_threshold_pt=threshold)
    assert report["ok"] is True
    assert report["large_deltas"] == []


# ---------------------------------------------------------------------------
# Test 4: Word missing from preview → skipped (D7 handles; D8 only does position)
# ---------------------------------------------------------------------------

def test_missing_word_skipped(tmp_path, monkeypatch):
    baseline_words = [_word("Gruenen", 0, 100.0, 200.0), _word("Austria", 0, 200.0, 200.0)]
    # "Gruenen" absent from preview
    preview_words = [_word("Austria", 0, 200.0, 200.0)]
    _patch_extract(monkeypatch, baseline_words, preview_words)
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")
    report = run_text_position_audit(preview_pdf, baseline_pdf, template="test")
    # "Gruenen" missing → skipped; "Austria" at same position → ok
    assert report["ok"] is True
    assert report["large_deltas"] == []


# ---------------------------------------------------------------------------
# Test 5: Multiple instances of same word → greedy nearest-match, no double-counting
# ---------------------------------------------------------------------------

def test_greedy_no_double_counting(tmp_path, monkeypatch):
    threshold = 2.0
    # Two "Ja" words in baseline at different x positions
    baseline_words = [
        _word("Ja", 0, 100.0, 200.0),  # baseline word A
        _word("Ja", 0, 300.0, 200.0),  # baseline word B
    ]
    # Two "Ja" words in preview near the respective baseline positions
    preview_words = [
        _word("Ja", 0, 101.0, 200.0),  # near A (within threshold)
        _word("Ja", 0, 315.0, 200.0),  # near B, shifted 15pt (large delta)
    ]
    _patch_extract(monkeypatch, baseline_words, preview_words)
    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")
    report = run_text_position_audit(preview_pdf, baseline_pdf, template="test",
                                     large_delta_threshold_pt=threshold)
    # First "Ja" matches to nearest (101.0 → dx=1.0, below threshold).
    # Second "Ja" matches to remaining (315.0 → dx=15.0, large delta).
    assert report["large_deltas_count"] == 1
    assert abs(report["large_deltas"][0]["dx_pt"] - 15.0) < 0.1


# ---------------------------------------------------------------------------
# Test 6: extract_words_with_positions smoke test with real minimal PDF
# ---------------------------------------------------------------------------

def test_extract_words_real_pdf(tmp_path):
    pdf = _make_pdf(tmp_path, "test.pdf", ["Hello World"])
    records = extract_words_with_positions(pdf)
    texts = {r["text"] for r in records}
    assert "Hello" in texts
    assert "World" in texts
    # All records on page 0
    assert all(r["page"] == 0 for r in records)
    # Coordinates are floats
    for r in records:
        assert isinstance(r["x0_pt"], float)
        assert isinstance(r["y0_pt"], float)


# ---------------------------------------------------------------------------
# Test 7: _yaml_dump is deterministic and has sorted keys
# ---------------------------------------------------------------------------

def test_yaml_dump_deterministic():
    report = {
        "template": "test",
        "threshold_pt": 2.0,
        "common_word_threshold": 5,
        "large_deltas_count": 1,
        "suppressed_common_word_deltas_count": 0,
        "large_deltas": [
            {
                "text": "Foo",
                "page": 0,
                "baseline_xy_pt": [100.0, 200.0],
                "preview_xy_pt": [114.3, 200.0],
                "dx_pt": 14.3,
                "dy_pt": 0.0,
                "severity": "large",
            }
        ],
        "ok": False,
        "baseline_pdf": "/a/baseline.pdf",
        "preview_pdf": "/a/preview.pdf",
    }
    assert _yaml_dump(report) == _yaml_dump(report)
    output = _yaml_dump(report)
    # Extract only top-level keys (lines that start with a letter and contain ':')
    top_level_keys = [line.split(":")[0] for line in output.splitlines()
                      if line and line[0].isalpha() and ":" in line]
    assert top_level_keys == sorted(top_level_keys)


# ---------------------------------------------------------------------------
# Test 7: Common-word filter — high-frequency word excluded from large_deltas
# ---------------------------------------------------------------------------

def test_common_word_filter_excludes_high_frequency_word(tmp_path, monkeypatch):
    """Word 'et' appears 6 times in baseline → freq >= 5 → excluded from large_deltas.

    Even though greedy matching produces a large delta for each 'et', none
    appear in large_deltas because the word is above the common_word_threshold.
    """
    threshold = 2.0
    common_threshold = 5

    # 6 "et" words in baseline, each at x=100; 6 "et" in preview at x=500
    # (cross-column binding → large dx for every instance)
    baseline_words = [_word("et", 0, 100.0 + i * 0.1, 200.0) for i in range(6)]
    preview_words = [_word("et", 0, 500.0 + i * 0.1, 200.0) for i in range(6)]
    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_text_position_audit(
        preview_pdf, baseline_pdf, template="test",
        large_delta_threshold_pt=threshold,
        common_word_threshold=common_threshold,
    )
    # All 6 "et" deltas should be suppressed
    assert report["large_deltas"] == []
    assert report["large_deltas_count"] == 0
    assert report["suppressed_common_word_deltas_count"] == 6
    assert report["ok"] is True


# ---------------------------------------------------------------------------
# Test 8: Unique word delta still reported alongside common-word suppression
# ---------------------------------------------------------------------------

def test_unique_word_delta_still_reported(tmp_path, monkeypatch):
    """High-frequency 'et' is suppressed; unique 'Leonore' with large shift IS reported."""
    threshold = 2.0
    common_threshold = 5

    # 6 "et" words → will be suppressed
    baseline_words = [_word("et", 0, 100.0 + i * 0.1, 200.0) for i in range(6)]
    preview_words = [_word("et", 0, 500.0 + i * 0.1, 200.0) for i in range(6)]

    # 1 unique "Leonore" with large shift → should be reported
    baseline_words.append(_word("Leonore", 0, 300.0, 400.0))
    preview_words.append(_word("Leonore", 0, 314.3, 400.0))  # dx=14.3 > threshold

    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_text_position_audit(
        preview_pdf, baseline_pdf, template="test",
        large_delta_threshold_pt=threshold,
        common_word_threshold=common_threshold,
    )
    # "Leonore" should appear
    assert report["large_deltas_count"] == 1
    assert report["large_deltas"][0]["text"] == "Leonore"
    assert abs(report["large_deltas"][0]["dx_pt"] - 14.3) < 0.05
    # "et" suppressed
    assert report["suppressed_common_word_deltas_count"] == 6
    assert report["ok"] is False


# ---------------------------------------------------------------------------
# Test 9: suppressed_common_word_deltas_count matches number filtered
# ---------------------------------------------------------------------------

def test_suppressed_count_reflects_filter(tmp_path, monkeypatch):
    """suppressed_common_word_deltas_count == total large deltas minus filtered deltas."""
    threshold = 2.0
    common_threshold = 5

    # 3 common words with 5+ occurrences each → all suppressed
    # 2 unique words with large deltas → both reported
    baseline_words = []
    preview_words = []

    for word in ("et", "ut", "ad"):
        for i in range(5):
            baseline_words.append(_word(word, 0, 50.0 + i * 0.1, 100.0))
            preview_words.append(_word(word, 0, 400.0 + i * 0.1, 100.0))  # large dx

    for i, word in enumerate(("Kandidat", "Gruenen")):
        baseline_words.append(_word(word, 0, 200.0, 300.0 + i * 50))
        preview_words.append(_word(word, 0, 215.0, 300.0 + i * 50))  # dx=15 > threshold

    _patch_extract(monkeypatch, baseline_words, preview_words)

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_text_position_audit(
        preview_pdf, baseline_pdf, template="test",
        large_delta_threshold_pt=threshold,
        common_word_threshold=common_threshold,
    )
    assert report["large_deltas_count"] == 2
    assert report["suppressed_common_word_deltas_count"] == 15  # 3 words × 5 occurrences
    total = report["large_deltas_count"] + report["suppressed_common_word_deltas_count"]
    assert total == 17  # 15 suppressed + 2 reported


# ---------------------------------------------------------------------------
# Test 10 (#37 P1 task 2): reverse-glyph pdfplumber output filtered via pdftotext
# ---------------------------------------------------------------------------

def test_pdftotext_filter_drops_reversed_word(tmp_path, monkeypatch):
    """``:musserpmI`` (the reversed form of ``Impressum:``) is dropped because
    pdftotext does not emit it; the forward ``Impressum:`` survives."""
    import text_position_audit as tpa_module

    forward = _word("Impressum:", 0, 100.0, 200.0)
    reversed_glyph = _word(":musserpmI", 0, 100.0, 200.0)
    # Baseline has the reversed-glyph artefact AND the forward word; preview
    # has only the forward word. Without the filter, pdfplumber's reversed
    # version would have no preview match (D7-like skip) — but the test
    # exercises the filter directly by checking that the reversed word never
    # reaches the matcher.
    baseline_words = [forward, reversed_glyph]
    preview_words = [forward]

    def fake_extract(pdf_path):
        if "baseline" in str(pdf_path):
            return baseline_words
        return preview_words

    monkeypatch.setattr(tpa_module, "extract_words_with_positions", fake_extract)

    # pdftotext returns only the forward token on both pages.
    monkeypatch.setattr(
        tpa_module,
        "_pdftotext_tokens_per_page",
        lambda path: [{"impressum:"}],
    )

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_text_position_audit(preview_pdf, baseline_pdf, template="test")
    assert report["suppressed_unmatched_word_count"] == 1
    # The reversed word must not appear anywhere in large_deltas
    for d in report["large_deltas"]:
        assert "musserp" not in d["text"].lower()


# ---------------------------------------------------------------------------
# Test 11: matched-on-both-extractors word survives the filter
# ---------------------------------------------------------------------------

def test_matched_word_survives_pdftotext_filter(tmp_path, monkeypatch):
    """``Leonore`` present in both pdfplumber and pdftotext output survives."""
    import text_position_audit as tpa_module
    leonore = _word("Leonore", 0, 100.0, 200.0)

    monkeypatch.setattr(
        tpa_module,
        "extract_words_with_positions",
        lambda path: [leonore],
    )
    monkeypatch.setattr(
        tpa_module,
        "_pdftotext_tokens_per_page",
        lambda path: [{"leonore"}],
    )

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_text_position_audit(preview_pdf, baseline_pdf, template="test")
    # No drift, no suppression
    assert report["large_deltas_count"] == 0
    assert report["suppressed_unmatched_word_count"] == 0


# ---------------------------------------------------------------------------
# Test 12: pdftotext unavailable → graceful fall-back, no crash, count = -1
# ---------------------------------------------------------------------------

def test_pdftotext_unavailable_no_crash(tmp_path, monkeypatch):
    """When pdftotext is missing, the audit must NOT crash. The new
    ``suppressed_unmatched_word_count`` reports -1 to signal unavailability."""
    import text_position_audit as tpa_module
    leonore = _word("Leonore", 0, 100.0, 200.0)
    monkeypatch.setattr(
        tpa_module,
        "extract_words_with_positions",
        lambda path: [leonore],
    )
    monkeypatch.setattr(
        tpa_module,
        "_pdftotext_tokens_per_page",
        lambda path: None,
    )

    baseline_pdf = tmp_path / "baseline.pdf"
    preview_pdf = tmp_path / "preview.pdf"
    baseline_pdf.write_bytes(b"%PDF dummy")
    preview_pdf.write_bytes(b"%PDF dummy")

    report = run_text_position_audit(preview_pdf, baseline_pdf, template="test")
    assert report["suppressed_unmatched_word_count"] == -1
    assert report["ok"] is True


# ---------------------------------------------------------------------------
# Test 13: YAML output is deterministic (filter additions don't break sort)
# ---------------------------------------------------------------------------

def test_yaml_deterministic_with_filter_fields():
    report = {
        "template": "tpl",
        "threshold_pt": 2.0,
        "common_word_threshold": 5,
        "large_deltas_count": 0,
        "suppressed_common_word_deltas_count": 0,
        "suppressed_unmatched_word_count": -1,
        "large_deltas": [],
        "ok": True,
        "baseline_pdf": "b",
        "preview_pdf": "p",
    }
    assert _yaml_dump(report) == _yaml_dump(report)


# ---------------------------------------------------------------------------
# Test 14: _word_matches_pdftotext substring tolerance (trailing punctuation)
# ---------------------------------------------------------------------------

def test_word_matches_pdftotext_substring():
    tokens = {"impressum:", "leonore", "the"}
    assert _word_matches_pdftotext("Impressum:", tokens)
    assert _word_matches_pdftotext("Impressum", tokens)  # punctuation tolerant
    assert _word_matches_pdftotext("Leonore", tokens)
    assert not _word_matches_pdftotext(":musserpmI", tokens)
    assert not _word_matches_pdftotext("xyz123", tokens)
    assert not _word_matches_pdftotext("", tokens)

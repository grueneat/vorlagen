"""Unit tests for tools/text_position_audit.py — Phase D8 per-word position drift audit.

Covers:
1. Identical word positions → ok=True, empty deltas.
2. Preview word shifted >threshold → reported in large_deltas with correct dx/dy.
3. Preview word shifted <threshold → NOT in deltas (AA noise filter).
4. Word missing from preview → skipped (D7 catches presence, D8 only does position).
5. Multiple instances of same word → greedy nearest-match, no double-counting.
6. _yaml_dump produces deterministic sorted-key output.

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
        "large_deltas_count": 1,
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

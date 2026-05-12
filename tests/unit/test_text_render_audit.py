"""Unit tests for tools/text_render_audit.py — Phase D7 render-side text presence audit.

Covers:
1. Identical PDFs → ok=True, empty missing/extra.
2. Preview missing a word from baseline → ok=False, word in missing_in_preview.
3. Preview has extra word not in baseline → reported in extra_in_preview (ok=True).
4. NFC normalisation: combining-char é vs precomposed é → counted as same word.
5. Case insensitivity: "Leonore" baseline vs "leonore" preview → counted as match.
6. Subprocess error on missing PDF → raises with clear error message.
7. _yaml_dump is deterministic.
8. Ligature folding: ﬃ in baseline, ffi in preview → counted as same word.
9. Ligature folding: ﬁ in baseline, fi in preview → counted as same word.
10. All ligatures in U+FB00–U+FB06 range folded correctly.

All tests create minimal synthetic PDFs from raw bytes so they run offline in <5s.
"""
from __future__ import annotations

import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from text_render_audit import (  # noqa: E402
    extract_pdf_words,
    run_text_render_audit,
    _yaml_dump,
    _normalize_text,
    _LIGATURE_FOLD,
)


# ---------------------------------------------------------------------------
# Minimal PDF factory
# ---------------------------------------------------------------------------

def _make_pdf(tmp_path: Path, name: str, text_lines: list[str]) -> Path:
    """Create a minimal Type1/Helvetica PDF embedding text_lines on page 1.

    Uses only printable ASCII characters (Helvetica doesn't embed; text is
    extractable by pdftotext because the font encoding maps code points 1:1).
    Supports basic Latin text; sufficient for unit-test word tokenisation.
    """
    # Build page content stream with each line at y=720, 680, 640 … (points)
    content_ops: list[str] = []
    y = 720
    for line in text_lines:
        # Escape parentheses and backslash for PDF string literals.
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_ops.append(f"BT /F1 12 Tf 72 {y} Td ({safe}) Tj ET")
        y -= 40

    stream_body = "\n".join(content_ops)
    stream_bytes = stream_body.encode("latin-1", errors="replace")
    stream_len = len(stream_bytes)

    objects: list[bytes] = []
    # Object 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # Object 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # Object 3: Page
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    # Object 4: Content stream
    objects.append(
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("ascii")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    # Object 5: Font
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

    # xref table
    xref_offset = pos
    xref_lines = [f"xref\n0 {len(objects) + 1}\n", "0000000000 65535 f \n"]
    for off in offsets:
        xref_lines.append(f"{off:010d} 00000 n \n")
    xref_body = "".join(xref_lines).encode("ascii")
    pdf_parts.append(xref_body)

    trailer_body = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    pdf_parts.append(trailer_body)

    pdf_path = tmp_path / name
    pdf_path.write_bytes(b"".join(pdf_parts))
    return pdf_path


# ---------------------------------------------------------------------------
# Test 1: Identical PDFs → ok=True, empty missing/extra
# ---------------------------------------------------------------------------

def test_identical_pdfs_ok(tmp_path):
    lines = ["Hello World", "Leonore Gewessler"]
    pdf = _make_pdf(tmp_path, "a.pdf", lines)
    report = run_text_render_audit(pdf, pdf, template="test")
    assert report["ok"] is True
    assert report["missing_in_preview"] == {}
    assert report["extra_in_preview"] == {}
    assert report["baseline_word_count"] == report["preview_word_count"]


# ---------------------------------------------------------------------------
# Test 2: Preview missing a word → ok=False, word in missing_in_preview
# ---------------------------------------------------------------------------

def test_missing_word_in_preview(tmp_path):
    baseline_pdf = _make_pdf(tmp_path, "baseline.pdf", ["Hello World Gruenen"])
    preview_pdf = _make_pdf(tmp_path, "preview.pdf", ["Hello World"])
    report = run_text_render_audit(preview_pdf, baseline_pdf, template="test")
    assert report["ok"] is False
    assert "gruenen" in report["missing_in_preview"]
    assert report["missing_in_preview"]["gruenen"] == 1


# ---------------------------------------------------------------------------
# Test 3: Preview has extra word → in extra_in_preview (ok can be True)
# ---------------------------------------------------------------------------

def test_extra_word_in_preview(tmp_path):
    baseline_pdf = _make_pdf(tmp_path, "baseline.pdf", ["Hello World"])
    preview_pdf = _make_pdf(tmp_path, "preview.pdf", ["Hello World Extra"])
    report = run_text_render_audit(preview_pdf, baseline_pdf, template="test")
    assert "extra" in report["extra_in_preview"]
    # ok only fails on missing; extra is informational
    assert report["ok"] is True


# ---------------------------------------------------------------------------
# Test 4: NFC normalisation — combining é vs precomposed é same word
# ---------------------------------------------------------------------------

def test_nfc_normalisation(tmp_path):
    # NFD form: e + combining accent (two code points)
    nfd_word = "café"  # = "café" in NFD
    # NFC form: single precomposed é (one code point)
    nfc_word = unicodedata.normalize("NFC", nfd_word)  # = "café" in NFC

    # Both should tokenise to the same NFC word after normalisation.
    # Use ASCII fallback for PDF embedding (pdftotext normalises internally),
    # so we test the normalisation logic directly via extract_pdf_words monkeypatch.
    import text_render_audit as tra_module

    # Simulate extract_pdf_words returning NFD text for baseline, NFC for preview.
    original_extract = tra_module.extract_pdf_words

    def fake_extract(pdf_path):
        if "baseline" in str(pdf_path):
            text = unicodedata.normalize("NFC", nfd_word.lower())
            words = __import__("re").findall(r"[\w@.\-]+", text)
            return Counter(words)
        else:
            text = unicodedata.normalize("NFC", nfc_word.lower())
            words = __import__("re").findall(r"[\w@.\-]+", text)
            return Counter(words)

    tra_module.extract_pdf_words = fake_extract
    try:
        baseline_pdf = tmp_path / "baseline.pdf"
        preview_pdf = tmp_path / "preview.pdf"
        baseline_pdf.write_bytes(b"%PDF dummy")
        preview_pdf.write_bytes(b"%PDF dummy")
        report = run_text_render_audit(preview_pdf, baseline_pdf, template="test")
        # NFC normalisation means both forms map to the same word → no missing
        assert report["ok"] is True, f"NFC mismatch: {report['missing_in_preview']}"
    finally:
        tra_module.extract_pdf_words = original_extract


# ---------------------------------------------------------------------------
# Test 5: Case insensitivity — "Leonore" baseline vs "leonore" preview
# ---------------------------------------------------------------------------

def test_case_insensitive_matching(tmp_path):
    baseline_pdf = _make_pdf(tmp_path, "baseline.pdf", ["Leonore Gewessler"])
    preview_pdf = _make_pdf(tmp_path, "preview.pdf", ["leonore gewessler"])
    report = run_text_render_audit(preview_pdf, baseline_pdf, template="test")
    # Both are lowercased before counting → identical word counters → ok
    assert report["ok"] is True
    assert report["missing_in_preview"] == {}


# ---------------------------------------------------------------------------
# Test 6: Subprocess error on missing PDF → raises CalledProcessError
# ---------------------------------------------------------------------------

def test_subprocess_error_on_missing_pdf(tmp_path):
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(subprocess.CalledProcessError):
        extract_pdf_words(missing)


# ---------------------------------------------------------------------------
# Test 7: _yaml_dump is deterministic across repeated calls
# ---------------------------------------------------------------------------

def test_yaml_dump_deterministic():
    report = {
        "template": "test",
        "baseline_word_count": 10,
        "preview_word_count": 8,
        "missing_in_preview": {"foo": 2},
        "extra_in_preview": {},
        "ok": False,
        "baseline_pdf": "/a/baseline.pdf",
        "preview_pdf": "/a/preview.pdf",
    }
    assert _yaml_dump(report) == _yaml_dump(report)
    # Keys must be sorted
    output = _yaml_dump(report)
    # Extract only top-level keys (lines that start with a letter and contain ':')
    keys_in_order = [line.split(":")[0] for line in output.splitlines()
                     if line and line[0].isalpha() and ":" in line]
    assert keys_in_order == sorted(keys_in_order)


# ---------------------------------------------------------------------------
# Test 8: Ligature folding — ﬃ (U+FB03) baseline, ffi preview → same word
# ---------------------------------------------------------------------------

def test_ligature_ffi_normalized():
    """Baseline has 'ofﬃcia' (ﬃ ligature), preview has 'officia' (decomposed).
    After ligature folding both tokenise to 'officia' → no missing word.
    """
    import text_render_audit as tra_module

    original_extract = tra_module.extract_pdf_words

    def fake_extract(pdf_path: Path) -> Counter:
        import re as _re
        if "baseline" in str(pdf_path):
            # ﬃ ligature form
            text = _normalize_text("ofﬃcia")
            return Counter(_re.findall(r"[\w@.\-]+", text))
        else:
            # decomposed form
            text = _normalize_text("officia")
            return Counter(_re.findall(r"[\w@.\-]+", text))

    tra_module.extract_pdf_words = fake_extract
    try:
        baseline_pdf = Path("/dev/null")
        preview_pdf = Path("/dev/null")
        report = run_text_render_audit(preview_pdf, baseline_pdf, template="test")
        assert report["ok"] is True, (
            f"ﬃ→ffi ligature folding failed: missing={report['missing_in_preview']}"
        )
    finally:
        tra_module.extract_pdf_words = original_extract


# ---------------------------------------------------------------------------
# Test 9: Ligature folding — ﬁ (U+FB01) baseline, fi preview → same word
# ---------------------------------------------------------------------------

def test_ligature_fi_normalized():
    """Baseline has 'oﬁce' (ﬁ ligature), preview has 'ofice' (decomposed).
    After ligature folding both tokenise to 'ofice' → no missing word.
    """
    import text_render_audit as tra_module

    original_extract = tra_module.extract_pdf_words

    def fake_extract(pdf_path: Path) -> Counter:
        import re as _re
        if "baseline" in str(pdf_path):
            text = _normalize_text("oﬁce")
            return Counter(_re.findall(r"[\w@.\-]+", text))
        else:
            text = _normalize_text("ofice")
            return Counter(_re.findall(r"[\w@.\-]+", text))

    tra_module.extract_pdf_words = fake_extract
    try:
        baseline_pdf = Path("/dev/null")
        preview_pdf = Path("/dev/null")
        report = run_text_render_audit(preview_pdf, baseline_pdf, template="test")
        assert report["ok"] is True, (
            f"ﬁ→fi ligature folding failed: missing={report['missing_in_preview']}"
        )
    finally:
        tra_module.extract_pdf_words = original_extract


# ---------------------------------------------------------------------------
# Test 10: All ligatures U+FB00–U+FB06 fold to correct ASCII sequences
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ligature,expected", [
    ("ﬀ", "ff"),   # ﬀ
    ("ﬁ", "fi"),   # ﬁ
    ("ﬂ", "fl"),   # ﬂ
    ("ﬃ", "ffi"),  # ﬃ
    ("ﬄ", "ffl"),  # ﬄ
    ("ﬅ", "st"),   # ﬅ
    ("ﬆ", "st"),   # ﬆ
])
def test_all_ligatures_in_FB00_FB06_range(ligature: str, expected: str):
    """Each ligature in U+FB00–U+FB06 folds to the expected ASCII sequence."""
    # Verify the fold table covers every entry
    assert ligature in _LIGATURE_FOLD, f"{ligature!r} not in _LIGATURE_FOLD"
    assert _LIGATURE_FOLD[ligature] == expected

    # Verify _normalize_text actually performs the substitution
    result = _normalize_text(ligature)
    assert result == expected, f"_normalize_text({ligature!r}) → {result!r}, expected {expected!r}"

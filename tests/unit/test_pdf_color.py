"""Unit tests for tools/pdf_color.py — colour-consistent PDF rasterisation."""
from __future__ import annotations

import sys
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from pdf_color import (  # noqa: E402
    extract_output_intent_icc,
    fallback_cmyk_icc_path,
    pick_reference_cmyk_profile,
    rasterise_color_managed,
)


# ---------------------------------------------------------------------------
# Synthetic PDF builders
# ---------------------------------------------------------------------------

def _minimal_icc(device_class: bytes = b"prtr", space: bytes = b"CMYK") -> bytes:
    """Build a 132-byte stub that passes pdf_color's ICC sanity check.

    The check requires len >= 128 and the 'acsp' signature at offset 36.
    A real ICC profile is far larger; this stub is only here to exercise
    the extraction byte-plumbing without a multi-MB fixture.
    """
    icc = bytearray(132)
    icc[12:16] = device_class
    icc[16:20] = space
    icc[36:40] = b"acsp"
    return bytes(icc)


def _pdf_with_output_intent(icc_bytes: bytes, info: str) -> bytes:
    """Build a one-page PDF carrying an /OutputIntents with an ICC profile.

    ``info`` is the human-readable text; parens are escaped as ``\\( \\)``
    exactly as a real PDF literal string requires.
    """
    compressed = zlib.compress(icc_bytes)
    content = b"0 0 50 50 re f\n"
    escaped_info = info.replace("(", r"\(").replace(")", r"\)")
    objs: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R /OutputIntents [5 0 R] >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] "
        b"/Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream",
        (
            f"<< /Type /OutputIntent /S /GTS_PDFX "
            f"/Info ({escaped_info}) /DestOutputProfile 6 0 R >>"
        ).encode("latin-1"),
        b"<< /N 4 /Filter /FlateDecode /Length %d >>\nstream\n" % len(compressed)
        + compressed
        + b"\nendstream",
    ]
    out = b"%PDF-1.5\n"
    offsets: list[int] = []
    for i, o in enumerate(objs):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % (i + 1) + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
        % (len(objs) + 1, xref)
    )
    return out


# ---------------------------------------------------------------------------
# extract_output_intent_icc
# ---------------------------------------------------------------------------

def test_extract_output_intent_icc_returns_profile(tmp_path):
    """A PDF with an /OutputIntents profile yields the ICC bytes + info."""
    icc = _minimal_icc()
    pdf = tmp_path / "with_oi.pdf"
    pdf.write_bytes(_pdf_with_output_intent(icc, "PSO Uncoated v3 (FOGRA52)"))

    extracted, info = extract_output_intent_icc(pdf)
    assert extracted == icc
    assert info == "PSO Uncoated v3 (FOGRA52)"


def test_extract_output_intent_icc_handles_escaped_parens(tmp_path):
    """The /Info string's escaped parens are matched and unescaped."""
    pdf = tmp_path / "escaped.pdf"
    # The builder escapes ( ) as \( \) — a real PDF literal string. The
    # extractor must match the balanced literal and unescape it.
    pdf.write_bytes(
        _pdf_with_output_intent(_minimal_icc(), "Coated FOGRA39 (ISO 12647)")
    )
    _, info = extract_output_intent_icc(pdf)
    assert info == "Coated FOGRA39 (ISO 12647)"


def test_extract_output_intent_icc_none_when_absent(tmp_path):
    """A PDF with no output intent yields (None, None)."""
    pdf = tmp_path / "no_oi.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% no output intent\n%%EOF")
    extracted, info = extract_output_intent_icc(pdf)
    assert extracted is None
    assert info is None


def test_extract_output_intent_icc_rejects_non_icc_stream(tmp_path):
    """A DestOutputProfile stream lacking the 'acsp' signature is rejected."""
    junk = b"\x00" * 200  # 200 bytes, no 'acsp' at offset 36
    pdf = tmp_path / "junk_oi.pdf"
    pdf.write_bytes(_pdf_with_output_intent(junk, "bogus"))
    extracted, _ = extract_output_intent_icc(pdf)
    assert extracted is None


# ---------------------------------------------------------------------------
# fallback / reference-profile selection
# ---------------------------------------------------------------------------

def test_fallback_cmyk_icc_path_is_a_file_or_none():
    """fallback_cmyk_icc_path returns an existing file path, or None."""
    path = fallback_cmyk_icc_path()
    assert path is None or Path(path).is_file()


def test_pick_reference_prefers_baseline_output_intent(tmp_path):
    """When the baseline has an output intent, that profile is the reference."""
    icc = _minimal_icc()
    baseline = tmp_path / "baseline.pdf"
    preview = tmp_path / "preview.pdf"
    baseline.write_bytes(_pdf_with_output_intent(icc, "FOGRA52"))
    preview.write_bytes(b"%PDF-1.4\n% no oi\n%%EOF")

    profile, source = pick_reference_cmyk_profile(
        baseline, preview, tmp_path / "wd",
    )
    assert profile is not None
    assert Path(profile).read_bytes() == icc
    assert source.startswith("baseline:output-intent")
    assert "FOGRA52" in source


def test_pick_reference_falls_back_to_preview_output_intent(tmp_path):
    """When only the preview has an output intent, that profile is used."""
    icc = _minimal_icc()
    baseline = tmp_path / "baseline.pdf"
    preview = tmp_path / "preview.pdf"
    baseline.write_bytes(b"%PDF-1.4\n% no oi\n%%EOF")
    preview.write_bytes(_pdf_with_output_intent(icc, "FOGRA52"))

    profile, source = pick_reference_cmyk_profile(
        baseline, preview, tmp_path / "wd",
    )
    assert profile is not None
    assert source.startswith("preview:output-intent")


def test_pick_reference_falls_back_to_bundled_profile(tmp_path):
    """When neither PDF is self-describing, a bundled CMYK profile is used."""
    baseline = tmp_path / "baseline.pdf"
    preview = tmp_path / "preview.pdf"
    baseline.write_bytes(b"%PDF-1.4\n% no oi\n%%EOF")
    preview.write_bytes(b"%PDF-1.4\n% no oi\n%%EOF")

    profile, source = pick_reference_cmyk_profile(
        baseline, preview, tmp_path / "wd",
    )
    if fallback_cmyk_icc_path() is not None:
        assert source.startswith("bundled:")
        assert profile == fallback_cmyk_icc_path()
    else:
        assert source == "none:poppler-builtin"
        assert profile is None


# ---------------------------------------------------------------------------
# rasterise_color_managed
# ---------------------------------------------------------------------------

def _solid_cmyk_pdf(path: Path) -> None:
    """Write a one-page PDF with a full-page DeviceCMYK fill."""
    content = b"0.85 0.35 0.95 0.10 k 0 0 100 100 re f\n"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] "
        b"/Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream",
    ]
    out = b"%PDF-1.4\n"
    offsets: list[int] = []
    for i, o in enumerate(objs):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % (i + 1) + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
        % (len(objs) + 1, xref)
    )
    path.write_bytes(out)


def test_rasterise_color_managed_produces_png(tmp_path):
    """rasterise_color_managed renders one PNG per page."""
    pdf = tmp_path / "solid.pdf"
    _solid_cmyk_pdf(pdf)
    pages = rasterise_color_managed(pdf, tmp_path / "out", dpi=72)
    assert len(pages) == 1
    img = Image.open(pages[0]).convert("RGB")
    # The brand green renders as a green-dominant pixel.
    r, g, b = img.getpixel((img.size[0] // 2, img.size[1] // 2))
    assert g > r and g > b


def test_rasterise_color_managed_deterministic(tmp_path):
    """Two renders of the same PDF are byte-identical (deterministic)."""
    pdf = tmp_path / "solid.pdf"
    _solid_cmyk_pdf(pdf)
    a = rasterise_color_managed(pdf, tmp_path / "a", dpi=72)
    b = rasterise_color_managed(pdf, tmp_path / "b", dpi=72)
    assert a[0].read_bytes() == b[0].read_bytes()

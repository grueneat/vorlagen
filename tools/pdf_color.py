#!/usr/bin/env python3
"""Colour-consistent PDF rasterisation for baseline-vs-preview comparisons.

Why this module exists
----------------------
The IDML import pipeline compares two PDFs:

  * ``baseline.pdf`` — InDesign's PDF/X export. InDesign converts every
    swatch into the document's PDF/X **output intent** CMYK space (e.g.
    ``PSO Uncoated v3 (FOGRA52)``) and embeds that ICC profile as the
    ``/OutputIntents`` ``DestOutputProfile``. The brand green swatch
    ``Dunkelgrün`` (CMYK 85/35/95/10 in the IDML) is therefore stored in
    the *PDF* as the FOGRA-converted quadruple (e.g. 76/8/92/25).

  * ``preview.pdf`` — Scribus's PDF export with colour management OFF
    (``UseProfiles=0``). Scribus writes the SLA's raw DeviceCMYK verbatim,
    so the brand green is stored as the literal ``85 35 95 10 k`` — and the
    PDF carries no output intent at all.

Both PDFs depict the *same* brand colour, but they store **different
DeviceCMYK numbers** and only one of them carries an ICC profile. A naive
rasterisation (``pdftoppm``/``pdftocairo`` with no colour management)
applies one generic DeviceCMYK→sRGB transform to both — which is correct
for the profile-less preview but *wrong* for the FOGRA-encoded baseline.
The result is a uniform, colour-specific RGB offset across every brand
region (the ``region_color_audit`` ``icc_likely`` false positives) that is
a measurement artifact, not a converter bug.

The fix
-------
:func:`rasterise_color_managed` rasterises a PDF through poppler's ICC
pipeline. Both the baseline and the preview are rasterised with the **same**
``-defaultcmykprofile`` — the CMYK ICC profile recovered from whichever PDF
carries an ``/OutputIntents`` (normally the baseline). Interpreting both
PDFs' DeviceCMYK through one shared profile removes the systematic offset
caused by the inconsistency (one PDF profiled, the other not), so the
comparison reflects a real colour-managed render instead of an
unmanaged-DeviceCMYK mismatch.

Use :func:`pick_reference_cmyk_profile` to choose the shared profile for a
baseline/preview pair, then pass it to :func:`rasterise_color_managed` for
each PDF.

The module is deterministic: extraction is pure ``zlib`` + regex, and
poppler's PNG encoder writes no timestamps.
"""
# License: BSD (matches repo convention).
from __future__ import annotations

import re
import subprocess
import zlib
from pathlib import Path

# A bundled CMYK ICC profile used as the shared reference when neither PDF
# in a pair carries an output intent. ISO Coated v2 ships with Scribus and
# is a coated-stock CMYK working space close to the print targets the
# brand templates are authored for. The first existing path wins.
_FALLBACK_CMYK_ICC_CANDIDATES: tuple[str, ...] = (
    "/usr/share/scribus/profiles/ISOcoated_v2_300_bas.icc",
    "/usr/share/color/icc/ghostscript/default_cmyk.icc",
    "/usr/share/color/icc/default_cmyk.icc",
)


# ---------------------------------------------------------------------------
# Output-intent ICC extraction
# ---------------------------------------------------------------------------

def _expand_object_streams(data: bytes) -> bytes:
    """Return ``data`` with every Flate object stream decompressed + appended.

    PDF 1.5+ packs indirect objects into compressed ``/ObjStm`` streams, so a
    ``/OutputIntents`` reference is invisible to a raw byte scan. This
    decompresses every Flate stream and concatenates the plaintext so a
    regex scan can see object-stream content too.
    """
    chunks: list[bytes] = [data]
    for m in re.finditer(rb"<<(.*?)>>\s*stream\r?\n", data, re.DOTALL):
        header = m.group(1)
        if b"FlateDecode" not in header:
            continue
        start = m.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        raw = data[start:end].rstrip(b"\r\n")
        try:
            chunks.append(zlib.decompress(raw))
        except zlib.error:
            continue
    return b"\n".join(chunks)


def extract_output_intent_icc(pdf_path: Path) -> tuple[bytes | None, str | None]:
    """Extract a PDF's ``/OutputIntents`` ICC profile.

    Returns ``(icc_bytes, info_string)``. ``info_string`` is the
    ``/Info`` entry of the output intent (e.g. ``"PSO Uncoated v3
    (FOGRA52)"``) when present. Returns ``(None, None)`` when the PDF
    carries no output intent or the profile stream cannot be decoded.

    The lookup is tolerant: it scans both the raw bytes and decompressed
    object streams for a ``/DestOutputProfile N 0 R`` reference, then reads
    that object's (possibly Flate-compressed) stream.
    """
    data = pdf_path.read_bytes()
    haystack = _expand_object_streams(data)

    ref = re.search(rb"/DestOutputProfile\s+(\d+)\s+0\s+R", haystack)
    if not ref:
        return None, None
    obj_num = ref.group(1)

    # The ICC profile stream is a real object — find it in the raw bytes
    # (profile streams are large and live as direct objects, not in ObjStm).
    obj = re.search(
        rb"\b" + re.escape(obj_num) + rb"\s+0\s+obj(.*?)stream\r?\n",
        data,
        re.DOTALL,
    )
    if not obj:
        return None, None
    header = obj.group(1)
    start = obj.end()
    end = data.find(b"endstream", start)
    if end < 0:
        return None, None
    raw = data[start:end].rstrip(b"\r\n")
    if b"FlateDecode" in header:
        try:
            icc = zlib.decompress(raw)
        except zlib.error:
            return None, None
    else:
        icc = raw

    # Sanity-check: a valid ICC profile declares 'acsp' at byte offset 36.
    if len(icc) < 128 or icc[36:40] != b"acsp":
        return None, None

    # A PDF literal string escapes parens as \( \) — match a balanced
    # literal (non-paren / non-backslash chars, or any backslash escape).
    info_match = re.search(rb"/Info\s*\(((?:[^()\\]|\\.)*)\)", haystack)
    info = (
        info_match.group(1).decode("latin-1").replace("\\(", "(").replace("\\)", ")")
        if info_match
        else None
    )
    return icc, info


def fallback_cmyk_icc_path() -> str | None:
    """Return the first available bundled CMYK ICC profile path, or ``None``."""
    for candidate in _FALLBACK_CMYK_ICC_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Reference-profile selection for a baseline/preview pair
# ---------------------------------------------------------------------------

def pick_reference_cmyk_profile(
    baseline_pdf: Path,
    preview_pdf: Path,
    workdir: Path,
) -> tuple[str | None, str]:
    """Choose the shared CMYK ICC profile for comparing a baseline/preview pair.

    Both PDFs in a comparison must be rasterised with the *same*
    ``-defaultcmykprofile`` so their DeviceCMYK is interpreted in one
    colour space — otherwise a profiled baseline and a profile-less preview
    read as a uniform false offset.

    Resolution order:

      1. The baseline's embedded ``/OutputIntents`` ICC profile — this is
         the CMYK space InDesign actually converted the document into, so
         it is the most accurate shared reference. Written into ``workdir``
         as a file so it can be passed to poppler.
      2. The preview's embedded output intent, if the baseline has none.
      3. A bundled CMYK ICC profile (ISO Coated v2) when neither PDF is
         self-describing.

    Returns ``(profile_path, source_label)``. ``profile_path`` is ``None``
    only when no CMYK profile is available at all (poppler then falls back
    to its built-in generic transform — still applied identically to both).
    """
    workdir.mkdir(parents=True, exist_ok=True)
    for pdf, label in ((baseline_pdf, "baseline"), (preview_pdf, "preview")):
        icc, info = extract_output_intent_icc(pdf)
        if icc is not None:
            dest = workdir / "reference_cmyk.icc"
            dest.write_bytes(icc)
            tag = info or f"{label} output intent"
            return str(dest), f"{label}:output-intent ({tag})"

    bundled = fallback_cmyk_icc_path()
    if bundled is not None:
        return bundled, f"bundled:{Path(bundled).name}"
    return None, "none:poppler-builtin"


# ---------------------------------------------------------------------------
# Colour-managed rasterisation
# ---------------------------------------------------------------------------

def rasterise_color_managed(
    pdf_path: Path,
    out_prefix: Path,
    dpi: int = 150,
    cmyk_profile: str | None = None,
) -> list[Path]:
    """Rasterise every page of a PDF to PNG through poppler's ICC pipeline.

    ``cmyk_profile`` is the CMYK ICC profile used to interpret the PDF's
    DeviceCMYK colour (poppler's ``-defaultcmykprofile``). Pass the SAME
    profile when rasterising a baseline/preview pair — see
    :func:`pick_reference_cmyk_profile`.

    ``pdftoppm`` is used (not ``pdftocairo``) because only ``pdftoppm``
    exposes ``-defaultcmykprofile``. Both honour an embedded output intent;
    the explicit ``-defaultcmykprofile`` additionally pins the
    interpretation of *un-tagged* DeviceCMYK (the preview's case) so the
    two PDFs share one colour space.

    Returns a sorted list of PNG paths, one per page, in page order.
    """
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["pdftoppm", "-png", "-r", str(dpi)]
    if cmyk_profile:
        cmd += ["-defaultcmykprofile", cmyk_profile]
    cmd += [str(pdf_path), str(out_prefix)]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(out_prefix.parent.glob(f"{out_prefix.name}-*.png"))

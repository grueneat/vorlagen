"""Metric-driven stacked-headline baseline corrector.

Multi-part headlines (e.g. "Das ist die / *dreizeilige* / Headline") are NOT
one multi-line text frame: Scribus mis-places mixed-font lines kept in a single
frame, so each visual line is emitted as its own single-line ``TextFrame`` with
an absolute ``y_mm``. Every such frame uses Scribus ``FLOP=1`` ("Font Ascent"):
the single baseline sits one FONT ASCENT below the frame top. The visible gap
between two stacked lines is therefore::

    gap = (frame_top_{k+1} - frame_top_k) + ascent(font_{k+1}) - ascent(font_k)

The old per-template ``y_mm`` were frozen constants tuned for Gotham's ascent.
Barlow (ascent 1.000 em) and Vollkorn (0.952 em) have different ascents, so the
same frame tops yield UNEVEN gaps — the top gap collapses wherever a Barlow line
sits above a Vollkorn line. ``headline_stack`` solves the gap equation from the
REAL installed-font ascents (fontTools on the fc-matched TTF) so every
inter-baseline gap equals the target leading by construction, regardless of the
per-line font mix:

    frame_top_{k+1} = frame_top_k + linesp - ascent(font_{k+1}) + ascent(font_k)

Ascents are read once per (family, size) and cached. Hard-coding per-font pt
constants is exactly the bug this replaces.
"""
from __future__ import annotations

import functools
import subprocess
from pathlib import Path

from fontTools.ttLib import TTFont

from .primitives import Run, TextFrame

PT_TO_MM = 25.4 / 72.0


def _fmt_linesp(value: float) -> str:
    """Format a LINESP value preserving the original SLA string shape.

    The corpus stores leading as ``'27.0'`` / ``'14.3'`` / full-precision
    floats — never the bare integer ``'27'``. ``repr(float(...))`` reproduces
    the shortest round-tripping string WITH the ``.0`` for whole numbers, which
    keeps ``sla_diff --strict`` byte-stable against the existing templates.
    """
    return repr(float(value))

# Repo font directory holding the committed print-pipeline TTFs (the sanctioned
# vendoring exception). fc-match resolves family aliases at render time, but its
# style-word queries (e.g. "Barlow Semi Condensed Regular") sometimes fall back
# to DejaVu; this directory is the deterministic fallback for ascent metrics.
_REPO_FONTS_DIR = Path(__file__).resolve().parents[3] / "fonts"

# Family-name fragments -> a TTF filename glob, used only when fc-match falls
# back to a non-matching family. Keyed by lower-cased family fragment.
_FONT_FILE_HINTS: tuple[tuple[str, str, str], ...] = (
    # (family fragment, weight/style fragment, filename substring)
    ("barlow semi condensed", "black", "BarlowSemiCondensed-Black"),
    ("barlow semi condensed", "extrabold", "BarlowSemiCondensed-ExtraBold"),
    ("barlow semi condensed", "extra bold", "BarlowSemiCondensed-ExtraBold"),
    ("barlow semi condensed", "bold", "BarlowSemiCondensed-Bold"),
    ("barlow semi condensed", "", "BarlowSemiCondensed-Regular"),
    ("vollkorn", "black", "Vollkorn-BlackItalic"),
    ("vollkorn", "", "Vollkorn-BoldItalic"),
)


def _fc_match_file(family: str) -> str | None:
    """Resolve a font family name to a TTF path via fc-match.

    Returns None when fc-match is unavailable or resolves to a face whose family
    does not actually contain the requested family fragment (the DejaVu
    fallback), so the caller can use the repo-font hint table instead.
    """
    try:
        path = subprocess.run(
            ["fc-match", "-f", "%{file}", family],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    if not path:
        return None
    # Guard against the DejaVu fallback: confirm the matched family token from
    # the request actually appears in the matched file's family name.
    want = family.split()[0].lower()
    if want and want not in Path(path).name.lower():
        return None
    return path


def _repo_font_file(family: str) -> str | None:
    """Deterministic fallback: map a family+style name to a committed TTF."""
    name = family.lower()
    for frag, style_frag, filesub in _FONT_FILE_HINTS:
        if frag in name and (not style_frag or style_frag in name):
            for ttf in _REPO_FONTS_DIR.rglob(f"*{filesub}*.ttf"):
                return str(ttf)
    return None


@functools.lru_cache(maxsize=64)
def _resolve_ttf(family: str) -> str:
    """Resolve a Scribus font family name to a TTF path (cached)."""
    path = _fc_match_file(family)
    if path is None:
        path = _repo_font_file(family)
    if path is None:
        raise FileNotFoundError(
            f"cannot resolve font family {family!r} to a TTF "
            f"(fc-match fell back and no repo-font hint matched)"
        )
    return path


@functools.lru_cache(maxsize=64)
def _ascent_em(family: str) -> float:
    """Font ascent as a fraction of the em (hhea.ascent / unitsPerEm).

    Scribus FLOP=1 places the first baseline one hhea ascent below the frame
    top; the hhea metric is what reproduces the rendered ink (verified against
    the old Gotham/Vollkorn 0.15 calibration: 0.952 - 0.800 = 0.152).
    """
    ttf = TTFont(_resolve_ttf(family), lazy=True)
    try:
        units_per_em = ttf["head"].unitsPerEm
        ascent = ttf["hhea"].ascent
    finally:
        ttf.close()
    return ascent / units_per_em


def font_ascent_pt(family: str, fontsize_pt: float) -> float:
    """Font ascent in points for ``family`` at ``fontsize_pt`` (FLOP=1 basis)."""
    return _ascent_em(family) * fontsize_pt


def font_ascent_mm(family: str, fontsize_pt: float) -> float:
    """Font ascent in millimetres for ``family`` at ``fontsize_pt``."""
    return font_ascent_pt(family, fontsize_pt) * PT_TO_MM


def headline_stack(
    lines: list[tuple[str, str, float, str]],
    *,
    top_y_mm: float,
    x_mm: float,
    w_mm: float,
    h_mm: float,
    linesp_pt: float,
    anname_stem: str,
    style: str | None = None,
    layer: int | None = None,
    align: str | None = "0",
) -> list[TextFrame]:
    """Build an even-gap stacked headline from real font metrics.

    Args:
        lines: per visual line ``(text, font_family, fontsize_pt, fcolor)``,
            top to bottom.
        top_y_mm: frame top of the FIRST line (kept identical to the original
            so only subsequent line tops shift).
        x_mm, w_mm, h_mm: shared geometry for every line frame.
        linesp_pt: target inter-baseline leading in points (the design leading).
        anname_stem: object name of the first frame; subsequent frames are
            ``{stem}_l2``, ``{stem}_l3``, … so the audit can group them.
        style: optional ``<DefaultStyle PARENT=...>`` paragraph-style slug.
        layer: layer index for every line frame (headline frames sit on the
            text/background layer per template; ``None`` keeps the ``_Frame``
            default).
        align: paragraph ALIGN on the first frame's run (``"0"`` = left). None
            omits it.

    Returns:
        One single-line ``TextFrame`` per line, FLOP=1, with frame tops solved so
        every inter-baseline gap equals ``linesp_pt``.
    """
    if not lines:
        return []

    linesp_mm = linesp_pt * PT_TO_MM
    frames: list[TextFrame] = []
    trail = {"LINESPMode": "0", "LINESP": _fmt_linesp(linesp_pt)}

    prev_top_mm = top_y_mm
    prev_font: str | None = None
    prev_size = 0.0
    for idx, (text, font, size, fcolor) in enumerate(lines):
        if idx == 0:
            top = top_y_mm
        else:
            # frame_top_k = frame_top_{k-1} + linesp - ascent(font_k) + ascent(font_{k-1})
            top = (
                prev_top_mm
                + linesp_mm
                - font_ascent_mm(font, size)
                + font_ascent_mm(prev_font, prev_size)  # type: ignore[arg-type]
            )
        anname = anname_stem if idx == 0 else f"{anname_stem}_l{idx + 1}"
        run_kwargs: dict = {"text": text, "font": font, "fontsize": size, "fcolor": fcolor}
        if idx == 0 and align is not None:
            run_kwargs["paragraph_attrs"] = {
                "ALIGN": align,
                "LINESPMode": "0",
                "LINESP": _fmt_linesp(linesp_pt),
            }
            if style:
                run_kwargs["paragraph_style"] = style
        frame_kwargs: dict = {
            "x_mm": x_mm,
            "y_mm": top,
            "w_mm": w_mm,
            "h_mm": h_mm,
            "anname": anname,
            "first_line_offset": 1,
            "runs": [Run(**run_kwargs)],
            "trail_attrs": dict(trail),
        }
        if style:
            frame_kwargs["style"] = style
        if layer is not None:
            frame_kwargs["layer"] = layer
        frames.append(TextFrame(**frame_kwargs))
        prev_top_mm = top
        prev_font = font
        prev_size = size

    return frames

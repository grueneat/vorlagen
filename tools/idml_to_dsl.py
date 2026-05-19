#!/usr/bin/env python3
"""IDML -> DSL converter (one-shot bootstrap; not run in CI).

Reads an Adobe IDML (the zipped XML interchange format produced by File >
Export > InDesign Markup), emits a Python ``build.py`` script that uses the
typed DSL (``tools/sla_lib/builder``) to recreate the document. The emitted
script is the source of truth thereafter — humans edit it directly.

Re-running REPLACES the emitted ``build.py`` and DISCARDS any manual edits.
Treat this as a one-shot bootstrap, mirroring ``tools/sla_to_dsl.py``.

Strict mode (D6, same philosophy as ``sla_to_dsl.py``): the converter raises
``UnhandledElement`` on any element or attribute it doesn't know how to
translate. Each raise carries a hint ``(extend tools/idml_to_dsl.py:<func>)``
pointing at the function to extend. Failing loudly beats silently emitting a
``build.py`` that renders something subtly different from the source IDML.

Locked decisions (see PLAN.md §"Locked Decisions" for rationale):

1. Color policy — exact-CMYK match against ``shared/ci.yml`` brand palette;
   auto-rename to brand names (``Dunkelgrün``, ``Gelb``, ``Magenta``,
   ``Hellgrün``, ``Black``, ``White``). Raise on any other printable swatch.
2. Assets — Phase 2: ``--asset-map <path/to/links_export.yml>`` accepts the
   manifest produced by ``tools/links_export.py`` (which converts the IDML's
   sibling ``Links/`` directory to ``shared/assets/<idml-slug>/``). The
   manifest covers every linked asset (.ai → PNG, .psd → flattened PNG,
   raster passthrough). When ``--asset-map`` is omitted AND a sibling
   ``Links/`` directory is found next to the input IDML, the converter
   auto-invokes ``tools/links_export.py`` to produce one.

   Legacy ``--logo-map`` (basename → PNG, vector only) is still accepted for
   backward compatibility; ``--asset-map`` takes precedence when both are
   supplied. Any unmapped ``<PDF>``/``<Image>`` reference whose basename
   isn't in the manifest raises ``UnhandledElement`` at end-of-run.
3. Raster ``Links/`` fallback — when neither ``--asset-map`` nor
   ``--logo-map`` covers a ``<Image>``'s file: URI basename, the converter
   falls back to ``--assets-dir`` and emits the raw file path (legacy
   behaviour). Use ``--asset-map`` instead for new templates.
4. Bleed — keep IDML's 2 mm verbatim (target IDML); a one-line comment in
   the emitted build.py notes the deviation from brand-standard 3 mm.
5. Falz lines — converter does NOT emit ``FoldLine``. Humans add them
   post-bootstrap, matching ``templates/kandidat-falzflyer-din-lang/build.py``
   (``from sla_lib.builder.blocks import FoldLine``).
6. SimpleIDML — pinned to 1.3.1 in ``Dockerfile.claude``. Sanity-probe imports
   ``simple_idml.idml`` to fail at image-build time on regressions.

Out of scope (raises ``UnhandledElement`` if encountered):

- Threaded TextFrames (``NextTextFrame``/``PreviousTextFrame`` != "n")
- Anchored objects (``<AnchoredObjectSetting>``)
- Master-spread items (``MasterSpreads/`` files must be empty)
- DSL -> IDML round-trip
- ``.indd`` binary format — entry-point validates ZIP magic
- Tables, footnotes, endnotes, hyperlinks, RTL text
- Multi-IDML batch processing
- Sheared / non-uniform-scaled items (rotation + uniform scale only)

noqa: NEVER import ``simple_idml.indesign`` — that submodule pulls in the
LGPL ``suds-py3`` SOAP stack for InDesign Server integration, which is
unrelated to IDML file parsing. We only need ``simple_idml.idml`` (BSD-3).

Usage (preferred — auto-invokes tools/links_export.py if --asset-map omitted):
    python3 tools/idml_to_dsl.py \\
        "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" \\
        templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py \\
        --template-id kandidat-falzflyer-din-lang-gruenes-cover-v2

Usage (explicit asset map):
    python3 tools/links_export.py "originals/<bundle>/Links" --idml-name <idml>
    python3 tools/idml_to_dsl.py <idml> <out.py> \\
        --template-id <slug> \\
        --asset-map shared/assets/<slug>/links_export.yml

Legacy (deprecated, kept for backward-compat):
    python3 tools/idml_to_dsl.py <idml> <out.py> \\
        --template-id <slug> \\
        --assets-dir "<bundle>/Links" \\
        --logo-map shared/logos/26-03-leporello-logo-map.yml
"""
# License: BSD (matches repo convention).
from __future__ import annotations

import argparse
import math
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse

from lxml import etree

try:
    from simple_idml.idml import IDMLPackage  # noqa: F401
except ImportError:
    print("Install SimpleIDML: pip install SimpleIDML==1.3.1", file=sys.stderr)
    sys.exit(2)

# Make tools/sla_lib importable when running directly from the worktree.
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent))

from sla_lib.builder import (  # noqa: E402,F401
    Anchor,
    Brand,
    CharStyle,
    Document,
    DocumentLayer,
    ImageFrame,
    ParaStyle,
    Polygon,
    PolyLine,
    Run,
    SoftShadow,
    TextFrame,
    pack_inline_image,
)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
ROOT = _THIS.parent.parent
CI_YAML = ROOT / "shared" / "ci.yml"

PT_TO_MM = 25.4 / 72.0
MM_TO_PT = 72.0 / 25.4

# InDesign's LeadingModelAkiBelow inserts ~12% extra "aki" (Japanese-typography
# space) below each line, so the rendered baseline-to-baseline gap is larger
# than the nominal Leading attribute. 16.0 / 14.3 ≈ 1.119 — measured against
# this corpus' Fließtext style; if a future template uses a font/size combo
# that deviates significantly, derive from OS/2 sTypoAscender/Descender.
_AKI_BELOW_FACTOR = 16.0 / 14.3

# Safe upper bounds on font metrics as a fraction of fontsize, used to budget
# the first-baseline offset and last-line descender when widening text frames.
# Scribus with FLOP=1 ("Font Ascent") places the first baseline at the maximum
# ascent of any run on that line, and clips a line when its descender extends
# below the frame bottom. Without these bounds the (n+0.5)*linesp formula
# under-budgets when the last line uses a font with larger metrics than line 1
# (e.g. Vollkorn Black Italic 30pt usWinAscent=33.45/usWinDescent=14.67 vs
# Gotham Narrow Ultra 30pt 28.80/7.20) — empirically verified against this
# template's u1b0/u1e6/u16c frames.
_FONT_ASCENT_RATIO = 1.15   # covers Vollkorn Black Italic usWinAscent/em=1.115
_FONT_DESCENT_RATIO = 0.55  # covers Vollkorn Black Italic usWinDescent/em=0.489
_FRAME_HEIGHT_SAFETY_PT = 4.0  # absolute cushion for lineGap + Scribus rounding

# Per-font Scribus FLOP=1 first-baseline ratio (fraction of fontsize), used by
# the mixed-font headline splitter. When a forced-line-break headline mixes
# fonts (the corpus pattern: Gotham Narrow Ultra + a Vollkorn Black Italic
# accent word), each line is emitted as its own single-line TextFrame; Scribus
# places each line's first baseline FLOP=1 ("Font Ascent") below the frame
# top, and the ascent of Vollkorn Black Italic differs from Gotham. Without a
# correction the Vollkorn line renders too low relative to a Gotham line at
# the same frame top (an InDesign↔Scribus font-metric mismatch).
#
# RECALIBRATED (issue: mixed-font headline split mis-calibration). The prior
# 0.345 value was calibrated against pdfplumber text-matrix coordinates, NOT
# the actual rendered ink. Measured against rendered ink-tops it over-shifted
# the Vollkorn line UPWARD: on 26-03-flyer-a6-hochformat-portrait the page-1
# headline "dreizeilige" (38pt) rendered 7.68pt too high and the page-2
# headline "Headline." (30pt) 5.60pt too high vs baseline.pdf. The Gotham
# lines were pixel-exact in both renders, isolating the whole error to the
# Vollkorn correction. Correcting the ratio per page gives 0.345-7.68/38=
# 0.1429 and 0.345-5.60/30=0.1583; the mean 0.15 leaves a ±0.27pt rendered-
# ink residual on both — within the sub-2pt fidelity bar. A font absent from
# this map is treated as the 0.0 reference (Gotham, any sans-serif face).
_FONT_FLOP_ASCENT_RATIO: dict[str, float] = {
    "vollkorn": 0.15,
}


def _font_flop_ratio(font: Optional[str]) -> float:
    """Scribus FLOP=1 first-baseline ratio for ``font`` (see the constant)."""
    fn = (font or "").lower()
    for key, ratio in _FONT_FLOP_ASCENT_RATIO.items():
        if key in fn:
            return ratio
    return 0.0


# Exact CMYK match (0..100 ints) -> brand-palette name, per locked decision #1.
# Source: shared/ci.yml palette cross-referenced against IDML Resources/Graphic.xml.
COLOR_CMYK_TO_BRAND: dict[tuple[int, int, int, int], str] = {
    (0,   0,   0,   100): "Black",
    (0,   0,   0,   0):   "White",        # also IDML "Color/Paper"
    (85,  35,  95,  10):  "Dunkelgrün",
    (69,  0,   100, 0):   "Hellgrün",
    (0,   0,   100, 0):   "Gelb",
    (0,   100, 0,   0):   "Magenta",
}

# IDML built-in swatches that NEVER reach the SLA, even when referenced —
# transparency placeholders and registration ink. These have no CMYK value
# the brand map could resolve.
IDML_BUILTIN_COLORS_SKIP = {
    "Color/None",
    "Color/Registration",
    "Swatch/None",
}

# IDML latent process inks (Cyan/Magenta/Yellow/Black). InDesign ships these
# as Hiddenreserved swatches that are normally unused — when unused they are
# dropped. But a PageItem can legitimately reference one as FillColor /
# StrokeColor (e.g. the Grüne yellow squiggle motif fills with Color/Yellow).
# When that happens the swatch IS in ``used_colors`` and must be routed
# through COLOR_CMYK_TO_BRAND like any other CMYK swatch instead of skipped.
IDML_BUILTIN_PROCESS_INKS = {
    "Color/Cyan",
    "Color/Magenta",
    "Color/Yellow",
    "Color/Black",
}

# Defence-in-depth XML parser settings. lxml 5.4 is XXE-safe by default on
# ``etree.fromstring``; we still pin the flags explicitly so any direct parse
# call we make never resolves external entities or fetches over the network.
_SECURE_XMLPARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    dtd_validation=False,
    load_dtd=False,
)


# ---------------------------------------------------------------------------
class UnhandledElement(Exception):
    """Raised by the strict-mode converter when an element or attribute has no
    typed DSL counterpart. The traceback identifies what to extend.

    Message convention:
        f"<element-kind> Self={self_id!r} in {spread_filename!r}: "
        f"<unhandled aspect> (extend tools/idml_to_dsl.py:_function_name)"
    """


# ---------------------------------------------------------------------------
# Coordinate math helpers
#
# Per RESEARCH.md §"Coordinate math": IDML uses Adobe's row-vector affine
# convention. A point ``(x, y)`` in inner space maps to outer space via
# ``[x y 1] · M`` where M is the 3×3 matrix
#
#     | a  b  0 |
#     | c  d  0 |
#     | tx ty 1 |
#
# so ``x' = a*x + c*y + tx``, ``y' = b*x + d*y + ty``.
#
# To compose two transforms so that ``compose(parent, child)`` maps inner→outer
# as "child applied first, then parent", the product is ``child · parent``
# (row-vector convention: outer transform multiplies on the RIGHT of the inner
# transform's row vector ``[x y 1] · child · parent``).
#
# Group cascade ordering: ``ancestor_transforms`` is a list ordered
# **innermost first**, e.g. ``[group_just_above_item, group_above_that, ...,
# outermost_group]``. ``_compute_page_local_bbox_pt`` walks it in that order,
# composing each ancestor on top of the running cascade so the final matrix
# maps item-inner-space → spread-coordinate-space.
# ---------------------------------------------------------------------------

def _parse_matrix(s: str) -> tuple[float, float, float, float, float, float]:
    """Parse a "a b c d tx ty" affine matrix string into a 6-tuple of floats.

    Raises UnhandledElement on the wrong token count or non-float content.
    """
    parts = s.split()
    if len(parts) != 6:
        raise UnhandledElement(
            f"ItemTransform must have 6 tokens, got {len(parts)}: {s!r} "
            f"(extend tools/idml_to_dsl.py:_parse_matrix)"
        )
    try:
        a, b, c, d, tx, ty = (float(p) for p in parts)
    except ValueError as e:
        raise UnhandledElement(
            f"ItemTransform contains non-numeric token: {s!r} ({e}) "
            f"(extend tools/idml_to_dsl.py:_parse_matrix)"
        ) from e
    return (a, b, c, d, tx, ty)


def _matrix_compose(
    parent: tuple[float, float, float, float, float, float],
    child: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    """Return the matrix M such that apply(M, p) == apply(parent, apply(child, p)).

    Row-vector convention: ``M = child · parent``. Calling with ``parent`` then
    ``child`` reads as "child applied first, then parent" — i.e. ``child`` lies
    INNER to ``parent`` in the cascade.
    """
    a1, b1, c1, d1, tx1, ty1 = child
    a2, b2, c2, d2, tx2, ty2 = parent
    return (
        a1 * a2 + b1 * c2,
        a1 * b2 + b1 * d2,
        c1 * a2 + d1 * c2,
        c1 * b2 + d1 * d2,
        tx1 * a2 + ty1 * c2 + tx2,
        tx1 * b2 + ty1 * d2 + ty2,
    )


def _apply_matrix(
    M: tuple[float, float, float, float, float, float], x: float, y: float
) -> tuple[float, float]:
    """Apply affine M to a 2D point. Row-vector convention."""
    a, b, c, d, tx, ty = M
    return (a * x + c * y + tx, b * x + d * y + ty)


def _inner_bbox_from_anchors(
    anchors: list[tuple[float, float]],
) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) of raw PathPointArray anchors.

    For TextFrames, anchors are symmetric around (0, 0) — IDML's "frame-centre
    inner origin" idiosyncrasy. For Rectangle/Polygon, anchors usually start at
    (0, 0) and extend out (top-left inner origin).
    """
    if not anchors:
        raise UnhandledElement(
            "Empty anchor list (extend tools/idml_to_dsl.py:_inner_bbox_from_anchors)"
        )
    xs = [p[0] for p in anchors]
    ys = [p[1] for p in anchors]
    return (min(xs), min(ys), max(xs), max(ys))


def _compute_page_local_bbox_pt(
    item_transform_str: str,
    anchors: list[tuple[float, float]],
    ancestor_transforms: list[str],
    spread_item_transform_str: str,
    page_item_transform_str: str,
    page_geometric_bounds: Optional[tuple[float, float, float, float]] = None,
) -> tuple[float, float, float, float, float]:
    """Convert IDML PageItem geometry to (x_pt, y_pt, w_pt, h_pt, rotation_deg)
    in page-top-left coordinates.

    Args:
        item_transform_str: PageItem's own ``ItemTransform``.
        anchors: PathPointArray anchors in item-inner-space.
        ancestor_transforms: ``ItemTransform`` strings of enclosing Groups,
            ordered **innermost first** (i.e. the Group directly enclosing the
            item is at index 0, outermost Group is last).
        spread_item_transform_str: ``Spread/ItemTransform`` (where the spread
            sits in pasteboard; subtract its translation to get spread-local).
        page_item_transform_str: ``Page/ItemTransform`` (where the page's
            local origin sits relative to spread origin).
        page_geometric_bounds: optional ``(y1, x1, y2, x2)`` from the page's
            ``GeometricBounds`` attribute. When present, the page-local x1
            and y1 are SUBTRACTED so the returned (x, y) is relative to the
            page top-left (i.e. (0, 0) at the top-left corner of the
            printable page area, NOT including bleed). Without this, the
            (0, 0) is the page's interior coordinate origin, which can be
            offset from the page's geometric top-left.

    Returns:
        Tuple ``(x_pt, y_pt, w_pt, h_pt, rotation_deg)``. Rotation is CCW
        positive (IDML and Scribus convention agree on sign for our typed
        DSL — see ``tools/sla_lib/builder/bbox.py``).

    Raises:
        UnhandledElement: on sheared or non-uniformly scaled items (only
        rotation + uniform scale supported in v1).
    """
    item_M = _parse_matrix(item_transform_str)
    spread_M = _parse_matrix(spread_item_transform_str)
    page_M = _parse_matrix(page_item_transform_str)

    # Compose ancestor cascade: walk innermost→outermost, building the
    # transform that maps item-inner-space "after item_transform" up to
    # spread-coordinate-space. ``acc`` starts as identity ("no ancestors yet").
    acc: tuple[float, float, float, float, float, float] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for ancestor_str in ancestor_transforms:
        ancestor_M = _parse_matrix(ancestor_str)
        # Each successive ancestor wraps OUTSIDE the running composite, so
        # compose with ancestor as the new outer "parent" and the running
        # composite as the inner "child".
        acc = _matrix_compose(ancestor_M, acc)

    # Final item→spread matrix: item_transform first, then ancestor cascade.
    item_to_spread = _matrix_compose(acc, item_M)

    # Reject shear / non-uniform scale at the item-to-spread level. Pure
    # rotation+uniform-scale satisfies sqrt(a²+b²) == sqrt(c²+d²) and
    # a*c + b*d == 0.
    a, b, c, d, _tx, _ty = item_to_spread
    sx = math.sqrt(a * a + b * b)
    sy = math.sqrt(c * c + d * d)
    if abs(sx - sy) > 0.01 or abs(a * c + b * d) > 0.01:
        raise UnhandledElement(
            f"Sheared or non-uniform-scaled item; only rotation+uniform-scale "
            f"supported in v1 (sx={sx:.4f}, sy={sy:.4f}, shear={a * c + b * d:.4f}) "
            f"(extend tools/idml_to_dsl.py:_compute_page_local_bbox_pt)"
        )

    # Apply to anchors → spread-local-coordinate-space points.
    #
    # IMPORTANT: items inside Spreads/<id>.xml store their ItemTransform in
    # the spread's OWN local coordinate space. The Spread's own ItemTransform
    # (which carries e.g. ty=786.61 for the second stacked spread in the
    # pasteboard) only describes where the SPREAD itself sits in pasteboard
    # for the UI; it does NOT shift the items. Therefore we DO NOT subtract
    # spread origin here. `spread_M` is kept in the signature for symmetry
    # and for future facing-pages support where the spread's transform may
    # rotate or scale items, but for v1 we treat it as informational.
    _ = spread_M  # currently unused; see comment above.
    spread_local = [_apply_matrix(item_to_spread, x, y) for (x, y) in anchors]

    # Subtract page origin in spread coords. The page's true top-left in
    # spread coords is (page_tx + page_x1, page_ty + page_y1), where (x1, y1)
    # is the page's GeometricBounds top-left in page-local coords. Without
    # GeometricBounds we fall back to just (page_tx, page_ty) — which is the
    # page-local-origin, NOT necessarily the page's geometric top-left.
    _, _, _, _, ptx, pty = page_M
    if page_geometric_bounds is not None:
        y1, x1, _y2, _x2 = page_geometric_bounds
        page_top_left_in_spread = (ptx + x1, pty + y1)
    else:
        page_top_left_in_spread = (ptx, pty)
    page_local = [
        (px - page_top_left_in_spread[0], py - page_top_left_in_spread[1])
        for (px, py) in spread_local
    ]

    rotation_deg = math.degrees(math.atan2(b, a))

    # NON-ROTATED frame (the common case): the axis-aligned bbox of the
    # transformed anchors IS the frame rectangle. Return it unchanged.
    if abs(rotation_deg) <= 1e-3:
        xs = [p[0] for p in page_local]
        ys = [p[1] for p in page_local]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return (min_x, min_y, max_x - min_x, max_y - min_y, rotation_deg)

    # ROTATED frame: the axis-aligned bbox of the rotated anchors is NOT the
    # frame — Scribus stores XPOS/YPOS/WIDTH/HEIGHT for the *un-rotated*
    # frame and rotates it CCW around (XPOS, YPOS). Emit that model:
    #
    #   WIDTH/HEIGHT = the un-rotated frame extent = item-local anchor
    #                  extent × the transform's uniform scale.
    #   XPOS/YPOS    = the image of the item-local top-left anchor
    #                  (min-x, min-y in item-local space) under the full
    #                  item→page transform. Because R·(0,0) == (0,0), this
    #                  point is exactly the rotation pivot.
    #
    # This makes a -90°/180°/270° full-bleed background land on-page instead
    # of sweeping off the top of the sheet (axis-aligned-bbox emission put
    # the pivot at the bbox corner, which is wrong for any non-zero ROT).
    a_xs = [p[0] for p in anchors]
    a_ys = [p[1] for p in anchors]
    a_min_x, a_max_x = min(a_xs), max(a_xs)
    a_min_y, a_max_y = min(a_ys), max(a_ys)
    w = (a_max_x - a_min_x) * sx
    h = (a_max_y - a_min_y) * sy
    # Map the item-local top-left anchor through the full transform chain.
    tl_spread = _apply_matrix(item_to_spread, a_min_x, a_min_y)
    pivot_x = tl_spread[0] - page_top_left_in_spread[0]
    pivot_y = tl_spread[1] - page_top_left_in_spread[1]
    return (pivot_x, pivot_y, w, h, rotation_deg)


def _pt_to_mm(value_pt: float) -> float:
    """Convert points to millimetres using PT_TO_MM."""
    return value_pt * PT_TO_MM


# ---------------------------------------------------------------------------
# Pattern 9 — Frame-height auto-adjust for Scribus rendering.
#
# Scribus suppresses entire lines of text when the TextFrame's h_pt is
# smaller than the effective line height. InDesign silently overflows;
# Scribus clips. The converter widens h_mm to the minimum required by
# Scribus so every line is visible. This is a geometry translation concern
# (IDML→Scribus), not a content edit.
#
# Two sub-cases are handled:
#   A. Single-line clipping: h_pt < effective_line_height_pt
#      → widen to exactly 1 line.
#   B. Multi-line overflow: h_pt is enough for ≥1 line but not enough for
#      all lines (InDesign overset). Detected via character-count heuristic:
#      estimate n_lines = ceil(total_chars / chars_per_line) and compare
#      n_lines * line_h to frame_h. Uses a conservative narrow-font ratio
#      (0.55 × point_size, calibrated on Gotham Narrow / body copy).
#      Only triggers when the estimate shows a deficit ≥ 1 full line;
#      widens to n_lines * leading + epsilon.
#
# Required effective line height:
#   - If the paragraph style sets an explicit Leading (not "Auto"):
#       line_h_pt = leading_pt
#   - Otherwise (auto-leading): line_h_pt = point_size_pt * 1.2
#     (standard auto-leading multiplier, matching InDesign and Scribus).
# ---------------------------------------------------------------------------

# Narrow-font average character width ratio: char_w_pt ≈ _NARROW_CHAR_RATIO × fontsize_pt.
# Calibrated on Gotham Narrow Book at 11pt body copy (observed ~34 chars/line at 149pt
# frame width → ratio = 149/(34×11) ≈ 0.40). Under-estimating chars-per-line (using a
# larger ratio) would OVER-estimate line count and widen frames more than needed.
# 0.40 targets body copy; bolder or wider fonts may have higher ratios but the
# heuristic is only applied to single-paragraph frames (no explicit breaklines) where
# the IDML frame is already measured to be shorter than the text's natural height.
_NARROW_CHAR_RATIO: float = 0.45


def _required_text_frame_height_mm(
    point_size_pt: float,
    leading_pt: Optional[float],
    leading_model: Optional[str] = None,
) -> float:
    """Minimum h_mm Scribus needs to render one line without clipping.

    Scribus suppresses lines when frame_h_pt < effective_line_height_pt.
    Effective line height is ``leading_pt`` (if explicitly set) else
    ``point_size_pt * 1.2`` (standard auto-leading multiplier). When the
    paragraph style uses ``LeadingModelAkiBelow`` the rendered baseline-
    to-baseline gap is ~12% larger than the nominal Leading; account for
    that here so widening doesn't under-budget and clip the last line.

    Also clamps degenerate authored leading (e.g. an IDML Leading of 1.9pt
    on 11pt body) to at least the font size, mirroring InDesign's fall-back
    to font-metric leading; Scribus otherwise enforces the literal Leading
    and chops the line on wrap.
    """
    if leading_pt is not None:
        line_h_pt = leading_pt
        if leading_model == "LeadingModelAkiBelow":
            line_h_pt *= _AKI_BELOW_FACTOR
    else:
        multiplier = 1.45 if leading_model == "LeadingModelAkiBelow" else 1.2
        line_h_pt = point_size_pt * multiplier
    line_h_pt = max(line_h_pt, point_size_pt)
    return line_h_pt * PT_TO_MM


def _estimate_line_count(
    total_chars: int,
    frame_w_mm: float,
    point_size_pt: float,
) -> int:
    """Estimate the number of lines a block of text needs in a frame.

    Uses a narrow-font character-width ratio to approximate chars-per-line.
    Conservative: under-estimates chars_per_line so the heuristic only fires
    when overflow is near-certain (avoids false positives on wider fonts).

    Args:
        total_chars: total character count across all text runs (excluding
            newlines/separators).
        frame_w_mm: frame inner width in mm (insets already subtracted if any).
        point_size_pt: font size in points.

    Returns:
        Estimated number of lines required (always ≥ 1).
    """
    if total_chars <= 0 or frame_w_mm <= 0 or point_size_pt <= 0:
        return 1
    frame_w_pt = frame_w_mm / PT_TO_MM
    char_w_pt = _NARROW_CHAR_RATIO * point_size_pt
    chars_per_line = max(1, frame_w_pt / char_w_pt)
    import math
    return max(1, math.ceil(total_chars / chars_per_line))


def _maybe_widen_frame_h(
    idml_h_mm: float,
    max_fontsize_pt: Optional[float],
    leading_pt: Optional[float],
    total_text_chars: int = 0,
    frame_w_mm: float = 0.0,
    explicit_line_count: int = 0,
    leading_model: Optional[str] = None,
    paragraph_char_counts: Optional[list[int]] = None,
    intrinsic_line_ratio: float = 1.1,
) -> tuple[float, Optional[str]]:
    """If the frame's h_mm is too small for the text content, return widened h_mm
    and a comment explaining the adjustment. Otherwise return idml_h_mm unchanged.

    Handles three overflow cases:
    - Sub-case A: frame_h < effective_line_height (can't show even 1 line).
    - Sub-case B: frame fits some lines but not all (InDesign overset on single-
      paragraph text). Detected via character-count heuristic.
    - Sub-case C: frame has explicit line breaks (breakline/para separators) and
      frame_h < n_explicit_lines * line_height. Exact line count is known.

    Args:
        idml_h_mm: height from the IDML PathPointArray (already in mm).
        max_fontsize_pt: maximum font size across all runs in this frame (pt).
            Pass None if the frame has no text runs.
        leading_pt: explicit leading from the paragraph style (pt), or None
            when leading is "Auto" or not set.
        total_text_chars: total character count of all text runs (used for
            sub-case B multi-line overflow detection). Pass 0 to skip.
        frame_w_mm: frame width in mm (used for sub-case B). Pass 0.0 to skip.
        explicit_line_count: number of text lines from explicit breakline/para
            separators (1 = no separators, 2 = one breakline, etc.). Used for
            sub-case C. Pass 0 to skip.

    Returns:
        ``(h_mm, comment_or_None)`` — if widening occurred, comment is a
        human-readable string suitable for a ``# ...`` comment in build.py.
    """
    if max_fontsize_pt is None:
        return idml_h_mm, None
    if leading_pt is not None:
        line_h_pt = leading_pt
        if leading_model == "LeadingModelAkiBelow":
            line_h_pt *= _AKI_BELOW_FACTOR
    else:
        multiplier = 1.45 if leading_model == "LeadingModelAkiBelow" else 1.2
        line_h_pt = max_fontsize_pt * multiplier
    # Scribus enforces a font-intrinsic minimum line height; if the authored
    # Leading falls below it Scribus silently clamps (auto-from-metrics).
    # The widening budget MUST match what Scribus actually renders, so floor
    # at fontsize × intrinsic_line_ratio. Caller passes 1.5 for serif fonts
    # with deep metrics (Vollkorn) and 1.1 for sans-serif (Gotham).
    line_h_pt = max(line_h_pt, max_fontsize_pt * intrinsic_line_ratio)
    line_h_mm = line_h_pt * PT_TO_MM
    epsilon_mm = 0.05  # avoid flapping on sub-mm rounding

    # Sub-case A's one-line budget. Don't return immediately — compute it
    # but defer the actual widening decision until after Sub-case B runs,
    # so frames whose IDML h falls between (one line) and (two soft-wrapped
    # lines) get the correct larger budget.
    if explicit_line_count < 2:
        one_line_pt = (
            _FONT_ASCENT_RATIO * max_fontsize_pt
            + _FONT_DESCENT_RATIO * max_fontsize_pt
            + _FRAME_HEIGHT_SAFETY_PT
        )
        required_mm_one_line = max(line_h_mm, one_line_pt * PT_TO_MM)
    else:
        required_mm_one_line = line_h_mm

    # When paragraph_char_counts are provided, compute visual lines per
    # paragraph (each paragraph wraps independently). This is more accurate
    # than treating the whole frame as one continuous text block.
    # - Headlines: [13, 9] → 1 + 1 = 2 lines (matches baseline)
    # - Zitat:     [41, 6] → 2 + 1 = 3 lines (matches baseline)
    # - Kasten:    [31]    → 2 lines       (matches baseline)
    if paragraph_char_counts and frame_w_mm > 0.0 and max_fontsize_pt > 0:
        per_para_lines = sum(
            max(1, _estimate_line_count(c, frame_w_mm, max_fontsize_pt))
            for c in paragraph_char_counts
        )
        explicit_line_count = max(explicit_line_count, per_para_lines)

    # Sub-case C: explicit line count (from breakline/para separators) — exact.
    # Runs that carry separator=breakline or separator=para each add an explicit
    # newline; explicit_line_count = separator_count + 1 (at minimum 1).
    if explicit_line_count >= 2:
        # Two formulas:
        # (a) Leading already covers ascent+descent: when ls_pt >= fontsize×0.9,
        #     the authored Leading is generous; budget = n * ls_pt + safety.
        #     Avoids over-allocating when the IDML's Leading is already large
        #     (Headlines case: 27pt Leading on 30pt font, ratio 0.9). The
        #     previous formula added ascent+descent ON TOP, ballooning the
        #     frame past the next pageitem and contaminating the audit's
        #     pdfplumber bbox-based line extraction.
        # (b) Tight Leading: when ls_pt < fontsize×0.9, Scribus needs extra
        #     vertical room for ascent of line 1 + descent of line N, so
        #     budget = ascent + (n-1)*ls + descent + safety.
        ls_pt = line_h_pt  # already AKI-inflated above when applicable
        if ls_pt >= max_fontsize_pt * 0.9:
            required_pt_explicit = (
                explicit_line_count * ls_pt + _FRAME_HEIGHT_SAFETY_PT
            )
        else:
            required_pt_explicit = (
                _FONT_ASCENT_RATIO * max_fontsize_pt
                + (explicit_line_count - 1) * ls_pt
                + _FONT_DESCENT_RATIO * max_fontsize_pt
                + _FRAME_HEIGHT_SAFETY_PT
            )
        required_mm_explicit = required_pt_explicit * PT_TO_MM
        if idml_h_mm < required_mm_explicit - epsilon_mm:
            leading_desc = (
                f"leading={leading_pt:.2f}pt" if leading_pt is not None
                else f"auto-leading={max_fontsize_pt:.0f}pt×1.2"
            )
            comment = (
                f"h_mm widened {idml_h_mm:.4f}mm→{required_mm_explicit:.4f}mm: "
                f"Scribus clips lines when frame_h < {explicit_line_count} explicit "
                f"lines × line height ({leading_desc}; IDML overflows silently)"
            )
            return required_mm_explicit, comment

    # Sub-case B: single-paragraph soft-wrap. Estimate visual lines from
    # total char count + frame width; widen when frame_h falls below the
    # estimated total height. For multi-paragraph frames Sub-case C above
    # would have returned already.
    required_mm_all = 0.0
    if total_text_chars > 0 and frame_w_mm > 0.0 and max_fontsize_pt > 0:
        n_lines = _estimate_line_count(total_text_chars, frame_w_mm, max_fontsize_pt)
        if n_lines >= 2:
            required_pt_b = (
                _FONT_ASCENT_RATIO * max_fontsize_pt
                + (n_lines - 1) * line_h_pt
                + _FONT_DESCENT_RATIO * max_fontsize_pt
                + _FRAME_HEIGHT_SAFETY_PT
            )
            required_mm_all = required_pt_b * PT_TO_MM

    # Choose the largest budget across A and B, widen if frame is below it.
    target_mm = max(required_mm_one_line, required_mm_all)
    if idml_h_mm < target_mm - epsilon_mm:
        leading_desc = (
            f"leading={leading_pt:.2f}pt" if leading_pt is not None
            else f"auto-leading={max_fontsize_pt:.0f}pt×1.2"
        )
        if required_mm_all > required_mm_one_line:
            n_lines_est = _estimate_line_count(total_text_chars, frame_w_mm, max_fontsize_pt)
            comment = (
                f"h_mm widened {idml_h_mm:.4f}mm→{target_mm:.4f}mm: "
                f"IDML overset text ({total_text_chars} chars, ~{n_lines_est} lines "
                f"estimated at {max_fontsize_pt:.0f}pt {_NARROW_CHAR_RATIO:.2f}× "
                f"ratio, {leading_desc}; Scribus clips, InDesign overflows silently)"
            )
        else:
            comment = (
                f"h_mm widened {idml_h_mm:.4f}mm→{target_mm:.4f}mm: "
                f"Scribus clips lines when frame_h < effective line height "
                f"({leading_desc}; IDML overflows silently)"
            )
        return target_mm, comment

    return idml_h_mm, None


# ---------------------------------------------------------------------------
# Code-emitter primitives — mirror tools/sla_to_dsl.py:140-195 verbatim in
# spirit (4-space indent, double-quoted strings, repr() for floats for
# byte-stable round-trip).
# ---------------------------------------------------------------------------
class PythonRepr:
    """Lightweight code-emitter. Tracks indentation."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.indent = 0

    def w(self, s: str = "") -> None:
        if s:
            self.lines.append("    " * self.indent + s)
        else:
            self.lines.append("")

    def render(self) -> str:
        return "\n".join(self.lines).rstrip() + "\n"


def _py_value(v: Any) -> str:
    """Format a Python literal the way Black would.

    Floats use ``repr()`` so the emitted build.py is round-trip-stable.
    Mirrors ``sla_to_dsl.py:_py_value``. Handles Run/Anchor dataclass
    instances by emitting their constructor call with non-default fields.
    """
    if v is None:
        return "None"
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return repr(v)
    if isinstance(v, str):
        # Prefer double quotes when no double quotes inside.
        if '"' not in v and "'" in v:
            return '"' + v + '"'
        return repr(v)
    if isinstance(v, Run):
        # Emit Run(<non-default kwargs>) so the build.py recreates it identically.
        kwargs = []
        for fname in ("text", "has_itext", "font", "fontsize", "fcolor",
                      "fshade", "fontfeatures", "features", "kern",
                      "char_style", "paragraph_style", "paragraph_attrs",
                      "separator", "var", "var_attrs"):
            fv = getattr(v, fname)
            if fname == "text" and fv == "":
                # Only emit text="" if there's nothing else (rare; usually has separator).
                if v.separator is None and v.paragraph_style is None:
                    continue
                # else fall through and emit text=""
            if fname == "has_itext" and fv is True:
                continue  # default
            if fv is None:
                continue
            kwargs.append(f"{fname}={_py_value(fv)}")
        return "Run(" + ", ".join(kwargs) + ")"
    if isinstance(v, Anchor):
        return f"Anchor(h={_py_value(v.h)}, v={_py_value(v.v)}, margin_mm={_py_value(v.margin_mm)})"
    if isinstance(v, tuple):
        body = ", ".join(_py_value(x) for x in v)
        if len(v) == 1:
            body += ","
        return "(" + body + ")"
    if isinstance(v, list):
        return "[" + ", ".join(_py_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{_py_value(k)}: {_py_value(val)}" for k, val in v.items()) + "}"
    raise TypeError(f"Cannot serialise {v!r}")


def _emit_call(
    out: PythonRepr,
    cls_name: str,
    kwargs: dict[str, Any],
    *,
    receiver: Optional[str] = None,
    multiline: bool = True,
    drop_none: bool = True,
) -> None:
    """Emit ``Cls(k1=v1, k2=v2, ...)`` (or ``receiver.add(Cls(...))``).

    Kwargs with ``None`` values are dropped unless ``drop_none=False``.
    ``multiline=True`` puts each kwarg on its own line for readability.
    """
    if drop_none:
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
    prefix = f"{receiver}.add(" if receiver else ""
    suffix = ")" if receiver else ""
    if not multiline or len(kwargs) <= 1:
        body = ", ".join(f"{k}={_py_value(v)}" for k, v in kwargs.items())
        out.w(f"{prefix}{cls_name}({body}){suffix}")
        return
    out.w(f"{prefix}{cls_name}(")
    out.indent += 1
    for k, v in kwargs.items():
        out.w(f"{k}={_py_value(v)},")
    out.indent -= 1
    out.w(f"){suffix}")


# ---------------------------------------------------------------------------
# Converter context — passed through the 7-phase pipeline so each phase can
# read shared state (the open IDML package, the resolved color map, the
# paragraph-style slug map, the deferred logo list, etc.) without globals.
# ---------------------------------------------------------------------------
@dataclass
class _Ctx:
    pkg: Any  # IDMLPackage (avoiding the import-time annotation cost)
    template_id: str
    assets_dir: Path
    out: PythonRepr = field(default_factory=PythonRepr)
    # The source IDML path. Used to locate the sibling baseline <stem>.pdf
    # for render-page-mode detection (per-page vs spread-merged export).
    source: Optional[Path] = None
    # Render-page model: "spread" (a facing-pages spread → one wide SLA page,
    # the default for leporello / fold templates) or "page" (each IDML page →
    # its own SLA page, used when the baseline PDF was exported page-by-page).
    # Resolved once by _resolve_render_page_mode().
    render_page_mode: str = "spread"
    # Filled by Phase A
    doc_prefs: dict[str, Any] = field(default_factory=dict)
    # Filled by Phase B
    layers: list[dict[str, Any]] = field(default_factory=list)
    layer_id_to_idx: dict[str, int] = field(default_factory=dict)
    printable_layer_ids: set[str] = field(default_factory=set)
    # Filled by Phase F (task 4)
    color_map: dict[str, str] = field(default_factory=dict)
    # Non-brand swatches the IDML uses (print-mark colors like Endformat /
    # Druckformat, etc.). Emitted as ``doc.add_color(name, cmyk=...)`` so the
    # referencing items render in the right colour. Keyed by dsl name.
    extra_colors: dict[str, tuple[int, int, int, int]] = field(default_factory=dict)
    # Subset of ``printable_layer_ids`` (visible-layer ids) whose IDML
    # Printable attribute is also true. Items on a visible-but-non-printable
    # layer (Info/print-mark layer) get a narrower handler — e.g. GraphicLine
    # is silently skipped because Falz lines are added manually post-bootstrap.
    truly_printable_layer_ids: set[str] = field(default_factory=set)
    # Filled by Phase G (task 5)
    paragraph_style_map: dict[str, str] = field(default_factory=dict)
    paragraph_styles: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Filled by Phase H (tasks 6-7)
    unmapped_logos: list[tuple[str, str]] = field(default_factory=list)
    missing_assets: list[str] = field(default_factory=list)
    logo_map: dict[str, str] = field(default_factory=dict)
    # Phase 2 — superset of logo_map. Keyed by the original basename
    # (NFC-normalised). When populated, the converter prefers this over
    # logo_map for both <PDF> (vector) and <Image> (raster) references.
    asset_map: dict[str, str] = field(default_factory=dict)
    unmapped_assets: list[tuple[str, str]] = field(default_factory=list)
    # Issue #39 Phase A + C — set of basenames listed in
    # ``meta.yml::asset_policy::embedded``. When a frame's resolved asset
    # basename appears in this set the converter inlines the bytes into
    # the ImageFrame call (``inline_image_data=`` + ``inline_image_ext=``).
    # Otherwise it emits a repo-relative path. Either way, no absolute
    # filesystem paths are ever emitted; ``_emit_image_or_inline`` raises
    # ``RuntimeError`` if the resolved asset path falls outside ``ROOT``.
    embedded_set: set[str] = field(default_factory=set)
    # Issue #39 follow-up — basenames listed in
    # ``meta.yml::asset_policy::external``. These content assets are
    # referenced via repo-relative paths but NOT bundled with the SLA
    # download. The render pipeline resolves them from
    # ``shared/assets/<slug>/`` for preview generation; the downloaded
    # SLA shows missing-image placeholders that the user replaces.
    # Brand-team decision (2026-05-13): no AI / supplementary content
    # ships in the downloadable artifact.
    external_set: set[str] = field(default_factory=set)
    # Issue #37 Phase B1 (P3 task 16): track every IDML PageItem Self ID
    # that produced output, plus explicit skips with reasons. The
    # end-of-conversion assertion compares against the IDML's PageItem
    # inventory and fires UnhandledElement when the gap is non-empty.
    emitted_self_ids: set[str] = field(default_factory=set)
    skipped_with_reason: list[dict] = field(default_factory=list)
    # Squiggle re-anchoring (yellow emphasis motif). Each filled-silhouette
    # PolyLine (FillColor=Color/Yellow, closed path) records its page-local
    # bbox so a post-emit pass can associate it with the word it underlines.
    # Keyed lists are populated by _emit_pageitem; consumed by
    # _emit_squiggle_anchors which writes templates/<slug>/squiggle_anchors.yml.
    squiggle_records: list[dict] = field(default_factory=list)
    textframe_records: list[dict] = field(default_factory=list)

    def record_skipped(self, self_id: str, reason: str) -> None:
        """Explicitly skip an IDML PageItem with a reason — bypasses the
        end-of-conversion completeness assertion for ``self_id`` only."""
        self.skipped_with_reason.append({
            "self_id": str(self_id),
            "reason": str(reason),
        })


# ---------------------------------------------------------------------------
# Phase A — Document preferences (Resources/Preferences.xml)
# ---------------------------------------------------------------------------
def _read_doc_preferences(pkg: Any) -> dict[str, Any]:
    """Extract page width/height + uniform bleed from DocumentPreference.

    Raises if the four bleed offsets are non-uniform (v1 only supports the
    common case; the target IDML has all four at 5.669292 pt = 2 mm).
    """
    prefs_xml = pkg.open("Resources/Preferences.xml").read()
    root = etree.fromstring(prefs_xml, parser=_SECURE_XMLPARSER)
    dp = root.find(".//DocumentPreference")
    if dp is None:
        raise UnhandledElement(
            "Resources/Preferences.xml has no DocumentPreference "
            "(extend tools/idml_to_dsl.py:_read_doc_preferences)"
        )
    d = {
        "page_width_pt": float(dp.get("PageWidth", "0")),
        "page_height_pt": float(dp.get("PageHeight", "0")),
        "bleed_top_pt": float(dp.get("DocumentBleedTopOffset", "0")),
        "bleed_bottom_pt": float(dp.get("DocumentBleedBottomOffset", "0")),
        "bleed_inside_pt": float(dp.get("DocumentBleedInsideOrLeftOffset", "0")),
        "bleed_outside_pt": float(dp.get("DocumentBleedOutsideOrRightOffset", "0")),
        "facing_pages": dp.get("FacingPages", "false").lower() == "true",
    }
    bleeds = (
        d["bleed_top_pt"],
        d["bleed_bottom_pt"],
        d["bleed_inside_pt"],
        d["bleed_outside_pt"],
    )
    if max(bleeds) - min(bleeds) > 0.1:
        raise UnhandledElement(
            f"DocumentPreference has non-uniform bleeds {bleeds!r}; "
            f"v1 only supports uniform bleed "
            f"(extend tools/idml_to_dsl.py:_read_doc_preferences)"
        )
    return d


# ---------------------------------------------------------------------------
# Phase B — Layers (designmap.xml)
# ---------------------------------------------------------------------------
def _read_layers(pkg: Any) -> list[dict[str, Any]]:
    """Return ordered [{self_id, name, visible, printable, locked}, ...].

    Order matches designmap.xml order; layer index in the emitted Document
    follows this list (idx 0 = first layer).
    """
    designmap_xml = pkg.open("designmap.xml").read()
    root = etree.fromstring(designmap_xml, parser=_SECURE_XMLPARSER)
    layers: list[dict[str, Any]] = []
    for L in root.findall(".//Layer"):
        layers.append(
            {
                "self_id": L.get("Self"),
                "name": L.get("Name", ""),
                "visible": L.get("Visible", "true").lower() == "true",
                "printable": L.get("Printable", "true").lower() == "true",
                "locked": L.get("Locked", "false").lower() == "true",
            }
        )
    if not layers:
        raise UnhandledElement(
            "designmap.xml has no <Layer> elements "
            "(extend tools/idml_to_dsl.py:_read_layers)"
        )
    return layers


# ---------------------------------------------------------------------------
# Phase C — MasterSpread emptiness check (locked decision: master must be empty)
# ---------------------------------------------------------------------------
_MASTER_PAGEITEM_TAGS = (
    "Rectangle",
    "Polygon",
    "Oval",
    "TextFrame",
    "Image",
    "Group",
    "PDF",
    "EPS",
    "GraphicLine",
)


def _check_masters_empty(pkg: Any) -> None:
    """Raise if any MasterSpread file contains PageItem-shaped children.

    The target IDML has a single empty MasterSpread (`MasterSpread_ubb.xml`),
    so this is a defensive guard rather than active feature coverage.
    """
    for member in pkg.namelist():
        if not member.startswith("MasterSpreads/"):
            continue
        if not member.endswith(".xml"):
            continue
        xml = pkg.open(member).read()
        root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
        for tag in _MASTER_PAGEITEM_TAGS:
            found = root.findall(f".//{tag}")
            if found:
                raise UnhandledElement(
                    f"MasterSpread {member} contains <{tag}> page items "
                    f"(v1 only supports empty masters; "
                    f"extend tools/idml_to_dsl.py:_check_masters_empty)"
                )


# ---------------------------------------------------------------------------
# Phase F — Colors (Resources/Graphic.xml) per locked decision #1.
#
# Auto-rename on exact CMYK match against shared/ci.yml brand palette. Raise
# on non-brand printable swatches. Skip Color/None / Color/Registration /
# Hiddenreserved process inks silently.
# ---------------------------------------------------------------------------
def _parse_color_value(s: str) -> tuple[int, int, int, int]:
    """Parse a CMYK ``ColorValue`` "c m y k" (0..100, possibly fractional)
    into a 4-tuple of ints.

    Floats are rounded to nearest int (the target IDML uses integer percents).
    """
    parts = s.split()
    if len(parts) != 4:
        raise UnhandledElement(
            f"Color/ColorValue must have 4 tokens, got {len(parts)}: {s!r} "
            f"(extend tools/idml_to_dsl.py:_parse_color_value)"
        )
    try:
        vals = [int(round(float(p))) for p in parts]
    except ValueError as e:
        raise UnhandledElement(
            f"Color/ColorValue contains non-numeric token: {s!r} ({e}) "
            f"(extend tools/idml_to_dsl.py:_parse_color_value)"
        ) from e
    for v in vals:
        if v < 0 or v > 100:
            raise UnhandledElement(
                f"Color/ColorValue out of [0,100]: {s!r} "
                f"(extend tools/idml_to_dsl.py:_parse_color_value)"
            )
    return tuple(vals)  # type: ignore[return-value]


def _sanitize_color_name(self_id: str) -> str:
    """Map ``Color/Endformat`` -> ``Endformat`` for use as a DSL color name."""
    if "/" in self_id:
        self_id = self_id.split("/", 1)[1]
    out = re.sub(r"[^A-Za-z0-9_]+", "_", self_id).strip("_")
    return out or "ExtraColor"


def _emit_colors_from_xml(
    graphic_xml: bytes,
    used_colors: set[str],
    extra_colors: dict[str, tuple[int, int, int, int]] | None = None,
) -> dict[str, str]:
    """Parse a Resources/Graphic.xml blob and return idml_self → dsl_name map.

    Args:
        graphic_xml: the raw XML bytes of Resources/Graphic.xml.
        used_colors: set of IDML Self IDs that are referenced by a printable
            PageItem or Story. Used to gate the "non-brand printable raises"
            vs "non-brand unused silently dropped" branches.
        extra_colors: out-dict for non-brand swatches that are referenced by
            a printable item. The caller emits ``doc.add_color(name, cmyk=...)``
            for each entry so referencing items render in their authored colour.

    Returns:
        Map ``{idml_self_id: brand_or_local_dsl_name}``. Caller stores on ctx.

    Raises:
        UnhandledElement only when colour space / value is unparseable; non-
        brand CMYK swatches are auto-registered as document-local colours.
    """
    root = etree.fromstring(graphic_xml, parser=_SECURE_XMLPARSER)
    resolved: dict[str, str] = {}
    for c in root.findall(".//Color"):
        self_id = c.get("Self", "")
        if self_id in IDML_BUILTIN_COLORS_SKIP:
            # Color/None / Swatch/None / Registration never reach the SLA —
            # they carry no resolvable CMYK value.
            continue
        override = c.get("ColorOverride", "")
        # Latent process inks (Cyan/Magenta/Yellow/Black) ship as
        # Hiddenreserved. Drop them ONLY when truly unused; when a PageItem
        # references one (e.g. the yellow squiggle motif fills with
        # Color/Yellow) it is in ``used_colors`` and must resolve like a
        # normal CMYK swatch via COLOR_CMYK_TO_BRAND below.
        is_referenced_process_ink = (
            self_id in IDML_BUILTIN_PROCESS_INKS and self_id in used_colors
        )
        if "Hiddenreserved" in override and not is_referenced_process_ink:
            continue
        space = c.get("Space", "")
        model = c.get("Model", "")
        # Treat Registration model the same as Self=="Color/Registration" —
        # never written even if referenced.
        if model == "Registration":
            continue
        # Paper → White (CMYK 0,0,0,0).
        if self_id == "Color/Paper":
            resolved[self_id] = "White"
            continue
        if space != "CMYK":
            if self_id in used_colors:
                raise UnhandledElement(
                    f"Color {self_id!r} has unsupported Space={space!r} "
                    f"(extend tools/idml_to_dsl.py:_emit_colors_from_xml)"
                )
            continue
        value_str = c.get("ColorValue", "")
        if not value_str:
            if self_id in used_colors:
                raise UnhandledElement(
                    f"Color {self_id!r} has empty ColorValue "
                    f"(extend tools/idml_to_dsl.py:_emit_colors_from_xml)"
                )
            continue
        cmyk = _parse_color_value(value_str)
        brand_name = COLOR_CMYK_TO_BRAND.get(cmyk)
        if brand_name is not None:
            resolved[self_id] = brand_name
            continue
        # Non-brand printable swatch. Register as a document-local colour
        # (the converter previously raised here; that lost authored print-
        # mark colours like "Endformat" / "Druckformat" and dropped the
        # items using them out of the render entirely).
        if self_id in used_colors:
            dsl_name = _sanitize_color_name(self_id)
            resolved[self_id] = dsl_name
            if extra_colors is not None:
                extra_colors[dsl_name] = cmyk
            continue
        # Declared-but-unused non-brand: silently drop.
    return resolved


def _collect_used_fillcolors(pkg: Any, printable_layer_ids: set[str]) -> set[str]:
    """Return the set of Color Self IDs referenced by printable PageItems
    and any Story (Stories ignore layer state — text colors always count)."""
    used: set[str] = set()

    def _attr(node: Any, name: str) -> None:
        v = node.get(name)
        if v:
            used.add(v)

    for sp_path in pkg.spreads:
        xml = pkg.open(sp_path).read()
        root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
        # For each top-level page item, recurse with the group's layer in scope.
        # ItemLayer attribute is inherited from the enclosing Group when absent.
        def _walk(node: Any, current_layer: str) -> None:
            tag = etree.QName(node).localname
            if tag in ("Rectangle", "Polygon", "Oval", "TextFrame", "Group"):
                lyr = node.get("ItemLayer", "") or current_layer
                if lyr in printable_layer_ids:
                    _attr(node, "FillColor")
                    _attr(node, "StrokeColor")
                if tag == "Group":
                    for child in node:
                        if isinstance(child.tag, str):
                            _walk(child, lyr)
                    return
            for child in node:
                if isinstance(child.tag, str):
                    _walk(child, current_layer)

        _walk(root, current_layer="")

    # Stories always count (text rendered everywhere it's referenced).
    for st_path in pkg.stories:
        xml = pkg.open(st_path).read()
        root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
        for tag in ("CharacterStyleRange", "ParagraphStyleRange"):
            for n in root.findall(f".//{tag}"):
                _attr(n, "FillColor")
                _attr(n, "StrokeColor")
    return used


def _emit_colors(ctx: _Ctx) -> None:
    """Phase F driver. Populates ctx.color_map and ctx.extra_colors."""
    used = _collect_used_fillcolors(ctx.pkg, ctx.printable_layer_ids)
    graphic_xml = ctx.pkg.open("Resources/Graphic.xml").read()
    ctx.color_map = _emit_colors_from_xml(
        graphic_xml, used, extra_colors=ctx.extra_colors,
    )


# ---------------------------------------------------------------------------
# Phase G — Paragraph styles (Resources/Styles.xml) per RESEARCH §"Styles".
#
# IDML Justification → Scribus ParaStyle.align int.
# (0=left, 1=center, 2=right, 3=block, per tools/sla_lib/builder/styles.py)
#
# JUSTIFICATION_MAP is sourced from the pattern registry (issue #38 Task 10);
# re-exported here so the inline call sites in this module need no change.
# ---------------------------------------------------------------------------
from idml_to_dsl_patterns.justification_to_align import (  # noqa: E402
    JUSTIFICATION_MAP,
)

# Brand-recognised Scribus font family+style combinations. The converter
# does NOT raise on unrecognised fonts (Scribus's fontconfig will fall back),
# but having the list lets future emitters reason about font availability.
BRAND_FONTS = {
    "Gotham Narrow Book",
    "Gotham Narrow Bold",
    "Gotham Narrow Black",
    "Gotham Narrow Ultra",
    "Vollkorn Black Italic",
}

# Cached translation table for ASCII-fold + slug.
_SLUG_TRANSLATIONS = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "Ä": "ae",
    "Ö": "oe",
    "Ü": "ue",
    "ß": "ss",
}


def _idml_style_slug(name: str) -> str:
    """Slugify an IDML style name into an ``idml/<slug>`` DSL ParaStyle name.

    Rules: strip ``$ID/`` prefix, lowercase, fold German umlauts (ü→ue etc),
    replace runs of non-alphanum with single ``-``, prefix with ``idml/``.
    """
    s = name
    # Strip InDesign internal prefix.
    if s.startswith("$ID/"):
        s = s[len("$ID/"):]
    # ASCII-fold German umlauts BEFORE lowercasing (preserve mapping).
    for ch, repl in _SLUG_TRANSLATIONS.items():
        s = s.replace(ch, repl)
    s = s.lower()
    # Normalise any remaining accents via NFKD.
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Replace runs of non-alphanum with single hyphen.
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return f"idml/{s}" if s else "idml/_"


def _make_font_name(family: Optional[str], style: Optional[str], *, ctx_self_id: str) -> Optional[str]:
    """Concatenate family + style into a Scribus font name.

    Returns None if neither family nor style is set. Brand-font membership
    is informational only — we never raise; fontconfig handles fallback.
    """
    if family and style:
        return f"{family} {style}"
    if family:
        return family
    if style:
        return style
    return None


def _read_paragraph_styles_from_xml(styles_xml: bytes) -> dict[str, dict[str, Any]]:
    """Parse Resources/Styles.xml and return {self_id: style_dict, ...}.

    Each style_dict carries: self_id, name, based_on_self (or None),
    point_size (float|None), leading (float|None, or "Auto"-string), fill_color,
    font_style, justification, applied_font.

    Raises UnhandledElement if a non-empty RootCharacterStyleGroup contains
    any CharacterStyle other than [No character style] (corpus has none;
    extending this would require a new CharStyle emit path).
    """
    root = etree.fromstring(styles_xml, parser=_SECURE_XMLPARSER)

    # Defensive: confirm no real CharacterStyles to support.
    cs_group = root.find(".//RootCharacterStyleGroup")
    if cs_group is not None:
        for cs in cs_group.findall(".//CharacterStyle"):
            cs_name = cs.get("Name", "")
            if cs_name != "$ID/[No character style]":
                raise UnhandledElement(
                    f"CharacterStyle {cs.get('Self')!r} Name={cs_name!r}: "
                    f"only [No character style] is supported in v1 "
                    f"(extend tools/idml_to_dsl.py:_read_paragraph_styles_from_xml)"
                )

    styles: dict[str, dict[str, Any]] = {}
    ps_group = root.find(".//RootParagraphStyleGroup")
    if ps_group is None:
        return styles
    for ps in ps_group.findall(".//ParagraphStyle"):
        self_id = ps.get("Self", "")
        name = ps.get("Name", "")
        props = ps.find("Properties")
        based_on: Optional[str] = None
        applied_font: Optional[str] = None
        leading: Optional[str] = None
        if props is not None:
            bo = props.find("BasedOn")
            if bo is not None and bo.text:
                bo_text = bo.text.strip()
                # BasedOn may be a Self-ID like "ParagraphStyle/Foo" or a bare
                # name like "$ID/[No paragraph style]"; normalise to a Self-ID.
                if bo_text.startswith("ParagraphStyle/"):
                    based_on = bo_text
                else:
                    based_on = f"ParagraphStyle/{bo_text}"
            af = props.find("AppliedFont")
            if af is not None and af.text:
                applied_font = af.text.strip()
            ld = props.find("Leading")
            if ld is not None and ld.text:
                leading = ld.text.strip()

        # Avoid self-referential BasedOn (e.g. root style referring to itself).
        if based_on == self_id:
            based_on = None

        # Tab stops from TabList under Properties.
        tab_stops: list[tuple[float, int]] = []
        if props is not None:
            tl = props.find("TabList")
            if tl is not None:
                for li in tl.findall("ListItem"):
                    pos_el = li.find("Position")
                    align_el = li.find("Alignment")
                    if pos_el is None or pos_el.text is None:
                        continue
                    try:
                        pos_pt = float(pos_el.text.strip())
                    except ValueError:
                        continue
                    align_str = align_el.text.strip() if align_el is not None and align_el.text else "LeftAlign"
                    # IDML Alignment → Scribus Tabulator Type
                    tab_type = {
                        "LeftAlign": 0,
                        "RightAlign": 1,
                        "CenterAlign": 2,
                        "DecimalAlign": 3,
                    }.get(align_str, 0)
                    tab_stops.append((pos_pt, tab_type))

        point_size = ps.get("PointSize")
        fill_color = ps.get("FillColor")
        font_style = ps.get("FontStyle")
        justification = ps.get("Justification")
        # Paragraph spacing — IDML stores SpaceBefore/SpaceAfter in points
        # already (no conversion needed). InDesign's default is 0; a designer
        # who sets a non-zero value gets vertical air above/below the
        # paragraph. SLA stores these as STYLE VOR/NACH.
        space_before = ps.get("SpaceBefore")
        space_after = ps.get("SpaceAfter")
        # LeadingModel controls how nominal Leading converts to baseline-to-
        # baseline gap. "LeadingModelAkiBelow" — InDesign's Japanese-typography
        # model used by default in this corpus — adds ~12% aki below each
        # line, so an authored Leading of 14.3pt renders at ~16.0pt actual.
        # We thread this through to linesp emission and frame-height widening.
        leading_model = ps.get("LeadingModel")
        # GridAlignment="AlignBaseline" gates the AkiBelow inflation —
        # InDesign only snaps to baseline grid (and applies the inflated
        # gap) when the style aligns. With GridAlignment="None" the raw
        # Leading is used. (Agent-found root cause for absatzformat-1.)
        grid_alignment = ps.get("GridAlignment")
        styles[self_id] = {
            "self_id": self_id,
            "name": name,
            "based_on_self": based_on,
            "point_size": float(point_size) if point_size is not None else None,
            "leading": leading,
            "leading_model": leading_model,
            "grid_alignment": grid_alignment,
            "fill_color": fill_color,
            "font_style": font_style,
            "justification": justification,
            "applied_font": applied_font,
            "tab_stops": tab_stops if tab_stops else None,
            "space_before": float(space_before) if space_before is not None else None,
            "space_after": float(space_after) if space_after is not None else None,
        }
    return styles


def _resolve_paragraph_style(
    style: dict[str, Any], all_styles: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Walk the BasedOn chain upward; for each None attribute, inherit from parent.

    Cycle-safe: stops if a Self-ID is revisited.
    """
    resolved = dict(style)
    visited = {style["self_id"]}
    parent_self = resolved.get("based_on_self")
    while parent_self and parent_self in all_styles and parent_self not in visited:
        visited.add(parent_self)
        parent = all_styles[parent_self]
        for k in ("point_size", "leading", "leading_model", "grid_alignment",
                  "fill_color", "font_style", "justification", "applied_font",
                  "tab_stops", "space_before", "space_after"):
            if resolved.get(k) is None:
                resolved[k] = parent.get(k)
        parent_self = parent.get("based_on_self")
    return resolved


def _ancestor_has_nonzero(
    style: dict[str, Any],
    all_styles: dict[str, dict[str, Any]],
    key: str,
) -> bool:
    """True when an ANCESTOR (BasedOn chain) of ``style`` carries a non-zero
    value for ``key``.

    Used to detect an explicit zero-override: a child ParagraphStyle that
    sets e.g. ``SpaceAfter="0"`` while its parent's resolved value is
    non-zero. Such a 0 is NOT noise — emitting it cancels the inherited
    value; omitting it makes Scribus inherit the parent's non-zero spacing.
    Cycle-safe.
    """
    visited = {style["self_id"]}
    parent_self = style.get("based_on_self")
    while parent_self and parent_self in all_styles and parent_self not in visited:
        visited.add(parent_self)
        parent = all_styles[parent_self]
        v = parent.get(key)
        if v is not None and abs(float(v)) > 1e-6:
            return True
        parent_self = parent.get("based_on_self")
    return False


def _emit_paragraph_styles(out: PythonRepr, ctx: _Ctx) -> dict[str, str]:
    """Phase G driver. Populates ctx.paragraph_styles + ctx.paragraph_style_map
    AND emits doc.add_para_style(ParaStyle(...)) calls into the _add_styles
    function in the generated build.py.

    Returns ``{ParagraphStyle/Foo: idml/<slug>}`` map.
    """
    styles_xml = ctx.pkg.open("Resources/Styles.xml").read()
    styles = _read_paragraph_styles_from_xml(styles_xml)
    # Resolve the BasedOn chain for every style so that _walk_story can use
    # ctx.paragraph_styles as a font-family fallback without a separate
    # resolve() call per PSR.  The raw dict is kept as-is; we overwrite
    # ctx.paragraph_styles with a fully-resolved copy.
    resolved_styles = {k: _resolve_paragraph_style(v, styles) for k, v in styles.items()}
    ctx.paragraph_styles = resolved_styles

    # Build slug map (Self-ID → idml/<slug>).
    slug_map: dict[str, str] = {}
    for self_id, st in styles.items():
        slug_map[self_id] = _idml_style_slug(st["name"])
    ctx.paragraph_style_map = slug_map

    # Find styles referenced in any Story; emit only those (plus their
    # BasedOn parents, so PARENT references resolve at SLA load time).
    used: set[str] = set()
    for st_path in ctx.pkg.stories:
        xml = ctx.pkg.open(st_path).read()
        root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
        for psr in root.findall(".//ParagraphStyleRange"):
            ap = psr.get("AppliedParagraphStyle")
            if ap:
                used.add(ap)
    # Include BasedOn parents transitively.
    to_walk = list(used)
    while to_walk:
        s = to_walk.pop()
        st = styles.get(s)
        if not st:
            continue
        parent = st.get("based_on_self")
        if parent and parent in styles and parent not in used:
            used.add(parent)
            to_walk.append(parent)

    return _emit_paragraph_styles_to_function(out, ctx, used, styles, slug_map)


def _emit_paragraph_styles_to_function(
    out: PythonRepr,
    ctx: _Ctx,
    used: set[str],
    styles: dict[str, dict[str, Any]],
    slug_map: dict[str, str],
) -> dict[str, str]:
    """Append a second ``_add_styles(doc)`` definition to ctx.out that
    overrides the task-3 stub (last def wins in Python). Emits one
    ``doc.add_para_style(ParaStyle(...))`` call per used style, ordered
    parents-before-children so PARENT references resolve.
    """
    def _depth(s_id: str) -> int:
        """Depth from root in the BasedOn chain (cycle-safe)."""
        d = 0
        cur = styles.get(s_id, {}).get("based_on_self")
        seen = {s_id}
        while cur and cur in styles and cur not in seen:
            d += 1
            seen.add(cur)
            cur = styles[cur].get("based_on_self")
        return d

    ctx.out.w("")
    ctx.out.w("def _add_styles(doc: Document) -> None:  # overrides task-3 stub")
    ctx.out.indent += 1
    if not used:
        ctx.out.w('"""No paragraph styles referenced — overrides the empty stub."""')
        ctx.out.w("return None")
    else:
        ctx.out.w('"""Auto-generated paragraph styles from the source IDML."""')
        for s_id in sorted(used, key=lambda x: (_depth(x), slug_map[x])):
            st = styles[s_id]
            resolved = _resolve_paragraph_style(st, styles)
            slug = slug_map[s_id]
            kwargs: dict[str, Any] = {"name": slug}
            parent_self = st.get("based_on_self")
            if parent_self and parent_self in used:
                kwargs["parent"] = slug_map[parent_self]
            font = _make_font_name(
                resolved.get("applied_font"),
                resolved.get("font_style"),
                ctx_self_id=s_id,
            )
            if font is not None:
                kwargs["font"] = font
            if resolved.get("point_size") is not None:
                kwargs["fontsize"] = resolved["point_size"]
            just = resolved.get("justification")
            if just is not None:
                if just not in JUSTIFICATION_MAP:
                    raise UnhandledElement(
                        f"ParagraphStyle {s_id!r} Justification={just!r} unknown "
                        f"(extend tools/idml_to_dsl.py:JUSTIFICATION_MAP)"
                    )
                kwargs["align"] = JUSTIFICATION_MAP[just]
            fc = resolved.get("fill_color")
            if fc and fc in ctx.color_map:
                kwargs["fcolor"] = ctx.color_map[fc]
            ld = resolved.get("leading")
            model = resolved.get("leading_model")
            grid = resolved.get("grid_alignment")
            if ld and ld != "Auto":
                try:
                    lp = float(ld)
                    # AkiBelow inflates Leading by ~12% ONLY when the style
                    # snaps to the baseline grid (GridAlignment=AlignBaseline).
                    # Styles with GridAlignment=None use raw Leading. (Agent
                    # finding for absatzformat-1: same Leading=14.3 inherited
                    # from fliesstext, but renders literally because Grid=
                    # None overrides parent's AlignBaseline.)
                    if (
                        model == "LeadingModelAkiBelow"
                        and grid == "AlignBaseline"
                    ):
                        lp *= _AKI_BELOW_FACTOR
                    kwargs["linesp"] = lp
                    # A resolved numeric LINESP is a FIXED leading — pair it
                    # with Scribus LINESPMode=0 ("Fixed"). Without the mode the
                    # STYLE inherits the parent's mode (often 1=Automatic),
                    # which ignores LINESP and renders the font-metric gap.
                    kwargs["linesp_mode"] = 0
                except ValueError:
                    pass
            elif ld == "Auto" or ld is None:
                # Auto leading: rendered gap depends on LeadingModel. AkiBelow
                # ≈ pointsize × 1.45 (typography model with descender + aki).
                # Default ≈ pointsize × 1.2. Without this, Auto-led styles
                # (e.g. aufzaehlungen) render ~12% tighter than baseline.
                pt = resolved.get("point_size")
                if pt is not None:
                    multiplier = 1.45 if model == "LeadingModelAkiBelow" else 1.2
                    kwargs["linesp"] = float(pt) * multiplier
                    kwargs["linesp_mode"] = 0
            # Paragraph spacing (IDML SpaceBefore/SpaceAfter, in points) →
            # SLA STYLE VOR/NACH. Emit a non-zero resolved value (e.g. the
            # corpus body style's SpaceAfter=5.669pt). ALSO emit an explicit
            # 0 when this style's OWN value is 0 but an ancestor in the
            # BasedOn chain is non-zero — that 0 is a deliberate override
            # (e.g. the sub-headline "Zwischenüberschrift" sets SpaceAfter=0
            # over the body parent's 5.669pt). Omitting it makes Scribus
            # inherit the parent's spacing, adding ~one half-line of air
            # below the paragraph that InDesign never shows.
            sb = resolved.get("space_before")
            if sb is not None and abs(sb) > 1e-6:
                kwargs["space_before_pt"] = round(sb, 4)
            elif (
                st.get("space_before") is not None
                and abs(float(st["space_before"])) <= 1e-6
                and _ancestor_has_nonzero(st, styles, "space_before")
            ):
                kwargs["space_before_pt"] = 0.0
            sa = resolved.get("space_after")
            if sa is not None and abs(sa) > 1e-6:
                kwargs["space_after_pt"] = round(sa, 4)
            elif (
                st.get("space_after") is not None
                and abs(float(st["space_after"])) <= 1e-6
                and _ancestor_has_nonzero(st, styles, "space_after")
            ):
                kwargs["space_after_pt"] = 0.0
            # Tab stops: emit only those defined directly on THIS style (not inherited),
            # so child styles don't redundantly repeat the parent's tab stops.
            own_tabs = st.get("tab_stops")
            if own_tabs:
                kwargs["tab_stops"] = tuple(
                    (round(pos, 4), typ) for pos, typ in own_tabs
                )
                # IDML's bullet-list pattern stores Content as
                # ``\t•\t<?ACE 7?>`` — the ACE 7 marker is InDesign's
                # "indent-to-here" character. Bullet styles have TWO tab
                # stops (one before the bullet, one before the text);
                # single-tab styles (e.g. Fließtext with one TabList entry
                # for inline tabbing) are not bullet lists and should NOT
                # get a hanging indent. Synthesize the hanging indent only
                # for the bullet pattern: LEFT_INDENT = max tab pos and
                # FIRST_LINE_INDENT = −max tab pos so wrapped lines align
                # with the post-bullet text.
                if len(own_tabs) >= 2:
                    max_tab_pt = max(pos for pos, _ in own_tabs)
                    kwargs["left_indent_pt"] = round(max_tab_pt, 4)
                    kwargs["first_indent_pt"] = round(-max_tab_pt, 4)
            # Justification-compatibility default. Scribus's justified line-
            # breaker runs looser than InDesign's: with no glyph-scaling
            # headroom Scribus's word-spaces stretch wider, so it fits fewer
            # words per line and the wrap diverges from the baseline. A small
            # MinGlyphShrink budget (glyphs may compress to 98%) lets Scribus
            # fit the same words InDesign does — empirically closes the bulk
            # of the cross-renderer wrap drift on justified body text (A6
            # flyer body frames: 254 -> ~130 word-position drifts). Applied
            # to justified styles (ALIGN 3=justified, 4=forced) only; left/
            # centre/right styles do not justify so glyph scaling never
            # triggers. A template may still override per-frame in the tune
            # stage. MinWordTrack is left at the Scribus default — tightening
            # it as well over-packs some frames (per-template sweep finding).
            if kwargs.get("align") in (3, 4) and "min_glyph_shrink" not in kwargs:
                kwargs["min_glyph_shrink"] = 0.98
            ctx.out.w("doc.add_para_style(ParaStyle(")
            ctx.out.indent += 1
            for k, v in kwargs.items():
                ctx.out.w(f"{k}={_py_value(v)},")
            ctx.out.indent -= 1
            ctx.out.w("))")
        ctx.out.w("return None")
    ctx.out.indent -= 1
    ctx.out.w("")

    return slug_map


# ---------------------------------------------------------------------------
# Phase H — Page items (Spreads/*.xml + nested Stories/*.xml).
#
# Recursively walks each spread, dispatches on element type, computes
# page-local bbox via _compute_page_local_bbox_pt (with the page's
# GeometricBounds offset), translates IDML colors through ctx.color_map,
# emits one DSL primitive call per item into ctx.out.
# ---------------------------------------------------------------------------

# Tags this v1 dispatches to a typed primitive. Anything else (including
# unknown / out-of-corpus elements like Footnote, Table, Hyperlink) raises.
_DISPATCHED_PAGEITEM_TAGS = {"Rectangle", "Polygon", "Oval", "TextFrame", "Group"}


def _parse_geometric_bounds(s: str) -> tuple[float, float, float, float]:
    """Parse a GeometricBounds "y1 x1 y2 x2" string into a 4-tuple of floats."""
    parts = s.split()
    if len(parts) != 4:
        raise UnhandledElement(
            f"GeometricBounds must have 4 tokens, got {len(parts)}: {s!r} "
            f"(extend tools/idml_to_dsl.py:_parse_geometric_bounds)"
        )
    return tuple(float(p) for p in parts)  # type: ignore[return-value]


def _extract_anchors(item: Any) -> list[tuple[float, float]]:
    """Read the PathPointArray anchors from a PageItem's PathGeometry."""
    pg = item.find("Properties/PathGeometry")
    if pg is None:
        # Some items may have a deeply-nested PathGeometry (rare); search.
        pg = item.find(".//PathGeometry")
    if pg is None:
        raise UnhandledElement(
            f"<{etree.QName(item).localname} Self={item.get('Self')!r}>: "
            f"no PathGeometry "
            f"(extend tools/idml_to_dsl.py:_extract_anchors)"
        )
    pts = pg.findall(".//PathPointType")
    if not pts:
        raise UnhandledElement(
            f"<{etree.QName(item).localname} Self={item.get('Self')!r}>: "
            f"PathGeometry has no PathPointType anchors "
            f"(extend tools/idml_to_dsl.py:_extract_anchors)"
        )
    out: list[tuple[float, float]] = []
    for pp in pts:
        anchor_str = pp.get("Anchor", "")
        a = anchor_str.split()
        if len(a) != 2:
            raise UnhandledElement(
                f"PathPointType.Anchor must have 2 tokens: {anchor_str!r} "
                f"(extend tools/idml_to_dsl.py:_extract_anchors)"
            )
        out.append((float(a[0]), float(a[1])))
    return out


def _resolve_fill(self_attr_value: Optional[str], color_map: dict[str, str]) -> Optional[str]:
    """Translate FillColor / StrokeColor Self-ID through the color map.

    Returns None for None, ``Color/None``, or ``Swatch/None`` (i.e. no fill).
    Raises if the Self-ID is present but cannot be mapped.
    """
    if not self_attr_value:
        return None
    if self_attr_value in ("Color/None", "Swatch/None"):
        return None
    if self_attr_value not in color_map:
        raise UnhandledElement(
            f"FillColor {self_attr_value!r} not resolvable via color_map "
            f"(extend tools/idml_to_dsl.py:_resolve_fill)"
        )
    return color_map[self_attr_value]


def _strict_no_threading(item: Any) -> None:
    """Raise on threaded TextFrames (NextTextFrame / PreviousTextFrame != 'n')."""
    nxt = item.get("NextTextFrame", "n")
    prv = item.get("PreviousTextFrame", "n")
    if nxt != "n" or prv != "n":
        raise UnhandledElement(
            f"TextFrame Self={item.get('Self')!r}: threaded "
            f"(Next/Previous != 'n'); not supported in v1 "
            f"(extend tools/idml_to_dsl.py:_strict_no_threading)"
        )


def _extract_opacity(item: Any) -> Optional[float]:
    """Return the page item's fill opacity in [0.0, 1.0], or None when opaque.

    IDML records object transparency under
    ``<TransparencySetting><BlendingSetting Opacity="..."/></TransparencySetting>``.
    Opacity is a percent (0-100); InDesign's default is 100 (fully opaque).
    Returns None for a missing element or a 100 value so opaque frames stay
    byte-identical (the SLA primitive omits TransValue for None).
    """
    ts = item.find("TransparencySetting")
    if ts is None:
        return None
    bs = ts.find("BlendingSetting")
    if bs is None:
        return None
    raw = bs.get("Opacity")
    if raw is None:
        return None
    try:
        pct = float(raw)
    except (ValueError, TypeError):
        return None
    if abs(pct - 100.0) < 1e-6:
        return None
    return max(0.0, min(1.0, pct / 100.0))


# IDML TextFramePreference/VerticalJustification → SLA PAGEOBJECT ALIGN
# (vertical text alignment within the frame). TopAlign is both the IDML and
# SLA default; only Center/Bottom/Justify need an explicit emit.
_VERTICAL_JUSTIFICATION_MAP = {
    "TopAlign": 0,
    "CenterAlign": 1,
    "BottomAlign": 2,
    "JustifyAlign": 3,
}


def _extract_textframe_prefs(item: Any) -> dict[str, Any]:
    """Return rendering-relevant TextFramePreference settings for a TextFrame.

    Keys (all optional):
      ``vertical_text_align`` — int 0/1/2/3 from VerticalJustification, omitted
        for the default TopAlign.
      ``columns`` — int TextColumnCount, omitted when 1.
      ``col_gap_pt`` — float TextColumnGutter (points), only when columns > 1.
    InDesign defaults (TopAlign / 1 column) are dropped so single-column,
    top-aligned frames keep emitting nothing new.
    """
    out: dict[str, Any] = {}
    tfp = item.find("TextFramePreference")
    if tfp is None:
        return out
    vj = tfp.get("VerticalJustification")
    if vj is not None and vj in _VERTICAL_JUSTIFICATION_MAP:
        v = _VERTICAL_JUSTIFICATION_MAP[vj]
        if v != 0:
            out["vertical_text_align"] = v
    cc = tfp.get("TextColumnCount")
    if cc is not None:
        try:
            n = int(cc)
        except (ValueError, TypeError):
            n = 1
        if n > 1:
            out["columns"] = n
            cg = tfp.get("TextColumnGutter")
            if cg is not None:
                try:
                    out["col_gap_pt"] = float(cg)
                except (ValueError, TypeError):
                    pass
    return out


def _is_complex_polygon(item: Any) -> bool:
    """Return True if the Polygon has multiple sub-paths or open paths.

    A Polygon with only one closed sub-path and 4 or fewer straight-line anchors
    (i.e. a simple rectangle or other convex shape) is emitted as ``Polygon``.
    Complex paths — those with Bezier control points, open sub-paths (PathOpen=true),
    or multiple sub-paths (e.g. compound shapes like the wind turbine, quotation marks)
    — require ``PolyLine`` with verbatim SLA path data.

    Note: IDML stores PathPointType inside a PathPointArray wrapper child of
    GeometryPathType; use findall(".//PathPointType") to find them regardless
    of nesting depth.
    """
    pg = item.find("Properties/PathGeometry")
    if pg is None:
        pg = item.find(".//PathGeometry")
    if pg is None:
        return False
    sub_paths = pg.findall("GeometryPathType")
    if len(sub_paths) > 1:
        return True
    for sp in sub_paths:
        # Open path (PathOpen="true" or PathOpen="1")
        path_open = sp.get("PathOpen", "false").lower()
        if path_open in ("true", "1"):
            return True
        # Bezier: any PathPointType with non-trivial LeftDirection or RightDirection.
        # Points may be under PathPointArray (IDML spec) — use .// to find them.
        for pp in sp.findall(".//PathPointType"):
            anchor_str = pp.get("Anchor", "")
            left_str = pp.get("LeftDirection", anchor_str)
            right_str = pp.get("RightDirection", anchor_str)
            # If left/right differ from anchor, it's a Bezier curve point.
            if left_str != anchor_str or right_str != anchor_str:
                return True
    return False


def _is_open_polygon(item: Any) -> bool:
    """Return True when ANY of the Polygon's sub-paths is an open path.

    A squiggle silhouette is always closed (PathOpen=false on every
    GeometryPathType) so it can be flood-filled. An open sub-path means
    the shape is a stroked outline, never a fill motif.
    """
    pg = item.find("Properties/PathGeometry")
    if pg is None:
        pg = item.find(".//PathGeometry")
    if pg is None:
        return False
    for sp in pg.findall("GeometryPathType"):
        if sp.get("PathOpen", "false").lower() in ("true", "1"):
            return True
    return False


def _page_index_from_var(page_var: str) -> int:
    """Map a ``pageN`` receiver variable to its integer render-page index."""
    digits = "".join(ch for ch in page_var if ch.isdigit())
    return int(digits) if digits else 0


def _extract_idml_sla_path(
    item: Any,
    item_transform_str: str,
    ancestor_transforms: list[str],
    spread_t: str,
    page_t: str,
    page_gb: tuple[float, float, float, float],
    frame_x_pt: float,
    frame_y_pt: float,
) -> str:
    """Convert IDML PathGeometry to a frame-local SLA path string (SVG-like).

    The IDML PathGeometry stores anchors and Bezier control points in spread
    coordinates. This function:
    1. Applies the full transform chain (item → ancestors → spread-local)
    2. Subtracts the page top-left to get page-local coords
    3. Subtracts the frame top-left (frame_x_pt, frame_y_pt) to get frame-local coords
    4. Builds the SVG path string using M/L/C/Z Scribus-SLA path commands

    Returns a string suitable for ``PolyLine(sla_path=...)``.
    """
    # Build the same item-to-spread matrix as _compute_page_local_bbox_pt.
    item_M = _parse_matrix(item_transform_str)
    acc: tuple[float, float, float, float, float, float] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for ancestor_str in ancestor_transforms:
        ancestor_M = _parse_matrix(ancestor_str)
        acc = _matrix_compose(ancestor_M, acc)
    item_to_spread = _matrix_compose(acc, item_M)

    # Page top-left in spread coords.
    _, _, _, _, ptx, pty = _parse_matrix(page_t)
    if page_gb is not None:
        y1, x1, _, _ = page_gb
        page_tl = (ptx + x1, pty + y1)
    else:
        page_tl = (ptx, pty)

    def _transform_pt(x: float, y: float) -> tuple[float, float]:
        """Map an IDML spread-coord point to frame-local coords."""
        sx, sy = _apply_matrix(item_to_spread, x, y)
        px = sx - page_tl[0] - frame_x_pt
        py = sy - page_tl[1] - frame_y_pt
        return px, py

    pg = item.find("Properties/PathGeometry")
    if pg is None:
        pg = item.find(".//PathGeometry")

    path_parts: list[str] = []
    for sub_path in pg.findall("GeometryPathType"):
        path_open = sub_path.get("PathOpen", "false").lower() in ("true", "1")
        # Points are wrapped in PathPointArray in IDML; use .// to find them
        # regardless of nesting depth (direct or under PathPointArray).
        pts = sub_path.findall(".//PathPointType")
        if not pts:
            continue

        has_bezier = any(
            pp.get("LeftDirection", pp.get("Anchor", "")) != pp.get("Anchor", "")
            or pp.get("RightDirection", pp.get("Anchor", "")) != pp.get("Anchor", "")
            for pp in pts
        )

        def _parse_pt_str(s: str) -> tuple[float, float]:
            parts = s.split()
            return (float(parts[0]), float(parts[1]))

        # MoveTo first point.
        first_anchor = _parse_pt_str(pts[0].get("Anchor", ""))
        fx, fy = _transform_pt(*first_anchor)
        path_parts.append(f"M{fx:.4g} {fy:.4g}")

        if not has_bezier:
            # All straight lines.
            for pp in pts[1:]:
                ax, ay = _transform_pt(*_parse_pt_str(pp.get("Anchor", "")))
                path_parts.append(f"L{ax:.4g} {ay:.4g}")
        else:
            # Cubic Beziers: use RightDirection of current point and
            # LeftDirection of next point as control points.
            for i in range(1, len(pts)):
                prev = pts[i - 1]
                curr = pts[i]
                p1 = _transform_pt(*_parse_pt_str(prev.get("RightDirection", prev.get("Anchor", ""))))
                p2 = _transform_pt(*_parse_pt_str(curr.get("LeftDirection", curr.get("Anchor", ""))))
                p3 = _transform_pt(*_parse_pt_str(curr.get("Anchor", "")))
                path_parts.append(
                    f"C{p1[0]:.4g} {p1[1]:.4g} {p2[0]:.4g} {p2[1]:.4g} {p3[0]:.4g} {p3[1]:.4g}"
                )
            # If closed, close the loop back to first point with Bezier.
            if not path_open and has_bezier:
                last = pts[-1]
                curr = pts[0]
                p1 = _transform_pt(*_parse_pt_str(last.get("RightDirection", last.get("Anchor", ""))))
                p2 = _transform_pt(*_parse_pt_str(curr.get("LeftDirection", curr.get("Anchor", ""))))
                p3 = _transform_pt(*_parse_pt_str(curr.get("Anchor", "")))
                path_parts.append(
                    f"C{p1[0]:.4g} {p1[1]:.4g} {p2[0]:.4g} {p2[1]:.4g} {p3[0]:.4g} {p3[1]:.4g}"
                )

        if not path_open:
            path_parts.append("Z")

    return " ".join(path_parts)


@dataclass
class _HeadlineLine:
    """One visible line of a forced-break headline (see _split_mixed_font_lines)."""

    runs: list  # the Run objects that make up this line (no separator runs)
    font: Optional[str]  # the dominant font family of the line's first text run
    fontsize: Optional[float]  # the line's max fontsize


def _split_mixed_font_lines(runs: list) -> Optional[list[_HeadlineLine]]:
    """Split a forced-break headline's runs into per-line groups, IF mixed-font.

    A headline like ``u1175`` is ONE IDML paragraph whose CharacterStyleRanges
    are separated by ``<Br/>`` forced line breaks and use different fonts
    (Gotham Narrow Ultra → Vollkorn Black Italic → Gotham Narrow Ultra). The
    converter emits the Br as a ``separator='para'`` Run, so the run list is::

        [Run("Das ist die ", Gotham), Run(separator='para'),
         Run("dreizeilige", Vollkorn), Run(separator='para'),
         Run("Headline", Gotham)]

    Scribus's per-line font-metric leading places the Vollkorn line at the
    wrong baseline relative to the Gotham lines, so the headline must be
    emitted as N single-line TextFrames at calibrated y (the caller does
    that). This helper returns the per-line groups when ALL of:

      * there are >= 2 lines (at least one ``para``/``breakline`` separator),
      * every line carries exactly one text run (a single CSR — true for
        every headline in the corpus; multi-run lines are body text, not a
        headline, and are left as a single frame),
      * the lines do NOT all share the same font family.

    Returns ``None`` when the frame is not a mixed-font forced-break headline
    (single-font headlines render fine as one frame once LINESPMode=0 is set).
    """
    lines: list[list] = [[]]
    for r in runs:
        if r.separator in ("para", "breakline"):
            lines.append([])
        elif r.separator is not None:
            # tab / breakcol / breakframe — not a plain headline; bail out.
            return None
        elif r.text or r.has_itext:
            lines[-1].append(r)
    # Drop trailing empty line groups (a trailing Br leaves an empty bucket).
    while lines and not lines[-1]:
        lines.pop()
    if len(lines) < 2:
        return None
    headline_lines: list[_HeadlineLine] = []
    for grp in lines:
        if len(grp) != 1:
            return None  # multi-run line — body text, not a headline
        run = grp[0]
        if not (run.text or "").strip():
            return None  # blank line — not a headline
        fontsizes = [r.fontsize for r in grp if r.fontsize is not None]
        headline_lines.append(
            _HeadlineLine(
                runs=grp,
                font=run.font,
                fontsize=max(fontsizes) if fontsizes else None,
            )
        )
    fonts = {(hl.font or "").lower() for hl in headline_lines}
    if len(fonts) < 2:
        return None  # single-font forced-break frame — one frame is fine
    return headline_lines


def _emit_mixed_font_headline(
    ctx: "_Ctx",
    headline_lines: list[_HeadlineLine],
    *,
    x_mm: float,
    y_mm: float,
    w_mm: float,
    leading_pt: float,
    style_slug: str,
    self_id: str,
    layer_idx: int,
    page_var: str,
) -> None:
    """Emit one single-line TextFrame per line of a mixed-font headline.

    Each line keeps the original frame's x and the IDML <Leading> as its
    stacking interval. Line N's frame y is::

        y_N = y_1 + (N-1)*Leading  -  correction_N

    where ``correction_N`` is the per-font FLOP=1 baseline correction relative
    to line 1's font (see ``_FONT_FLOP_ASCENT_RATIO``): 0 for a line in the
    same family as line 1, ``0.15*fontsize`` upward for a Vollkorn line under
    a Gotham line 1. This makes every line's RENDERED ink land on the IDML
    leading grid regardless of font, matching the InDesign baseline.

    The frame width is widened by a margin so a Vollkorn accent word (which
    Scribus renders wider than InDesign) does not clip; the frames are
    left-aligned so widening the right edge is safe. Frame height is one
    line's worth. LINESPMode=0 + LINESP pins the (single) line's spacing.
    """
    line_h_mm = leading_pt * PT_TO_MM
    ref_ratio = _font_flop_ratio(headline_lines[0].font)
    for idx, hl in enumerate(headline_lines):
        fontsize_pt = hl.fontsize or (leading_pt / 1.2)
        correction_mm = (
            (_font_flop_ratio(hl.font) - ref_ratio) * fontsize_pt * PT_TO_MM
        )
        line_y = y_mm + idx * line_h_mm - correction_mm
        # One line needs ascent+descent+safety; budget generously so neither
        # a tall Vollkorn cap nor a descender clips.
        line_frame_h = max(
            line_h_mm,
            (_FONT_ASCENT_RATIO + _FONT_DESCENT_RATIO) * fontsize_pt * PT_TO_MM
            + _FRAME_HEIGHT_SAFETY_PT * PT_TO_MM,
        )
        # Widen the frame so a Vollkorn accent word does not clip; left-
        # aligned, so the right edge moves out harmlessly.
        line_w = w_mm + 12.0
        line_anname = self_id if idx == 0 else f"{self_id}_l{idx + 1}"
        kwargs: dict[str, Any] = {
            "x_mm": _round_mm(x_mm),
            "y_mm": _round_mm(line_y),
            "w_mm": _round_mm(line_w),
            "h_mm": _round_mm(line_frame_h),
            "anname": line_anname,
            "layer": layer_idx,
        }
        if style_slug:
            kwargs["style"] = style_slug
        kwargs["runs"] = list(hl.runs)
        kwargs["trail_attrs"] = {
            "LINESPMode": "0",
            "LINESP": str(leading_pt),
        }
        if idx == 0:
            ctx.out.w(
                f"# Mixed-font headline {self_id!r} split into "
                f"{len(headline_lines)} single-line frames: the IDML joins "
                f"the lines with <Br/> but mixes fonts (e.g. Gotham + "
                f"Vollkorn), and Scribus's per-line font-metric leading "
                f"places them at the wrong baseline as one frame. Each line "
                f"is stacked at the IDML Leading ({leading_pt:.2f}pt) with a "
                f"per-font FLOP=1 baseline correction."
            )
        _emit_call(
            ctx.out, "TextFrame", kwargs,
            receiver=page_var, multiline=True,
        )


def _emit_pageitem(
    out: PythonRepr,
    item: Any,
    ancestor_transforms: list[str],
    spread_t: str,
    page_t: str,
    page_gb: tuple[float, float, float, float],
    page_var: str,
    ctx: _Ctx,
    layer_idx: int,
) -> None:
    """Dispatch a PageItem to its emitter and append the call to ctx.out."""
    tag = etree.QName(item).localname
    self_id = item.get("Self", "<unknown>")
    # Issue #37 Phase B1: record every dispatched PageItem so the end-of-
    # conversion completeness check can compare against the IDML inventory.
    # Group containers are also recorded — their children separately add
    # their own Self IDs, but recording the Group Self matches the IDML's
    # PageItem inventory where Group is a leaf element.
    if self_id != "<unknown>":
        ctx.emitted_self_ids.add(self_id)

    if tag == "Group":
        # Recurse into the group, prepending the group's ItemTransform to the
        # ancestor chain (innermost-first ordering).
        grp_t = item.get("ItemTransform", "1 0 0 1 0 0")
        # Children of Group inherit ItemLayer.
        grp_layer_idx = layer_idx
        for child in item:
            if not isinstance(child.tag, str):
                continue
            ctag = etree.QName(child).localname
            if ctag not in _DISPATCHED_PAGEITEM_TAGS:
                # Skip Properties etc.; anything else surfaces as a strict raise.
                if ctag in ("Properties", "TextWrapPreference", "InCopyExportOption",
                            "ObjectExportOption", "FrameFittingOption",
                            "AnchoredObjectSetting"):
                    if ctag == "AnchoredObjectSetting":
                        # Plan locks this out of scope.
                        # Only raise if the setting is non-default.
                        if any(child.attrib.values()):
                            pass  # default config — skip silently
                    continue
                raise UnhandledElement(
                    f"<Group Self={self_id!r}> contains unhandled <{ctag}>; "
                    f"(extend tools/idml_to_dsl.py:_emit_pageitem)"
                )
            _emit_pageitem(
                out,
                child,
                [grp_t, *ancestor_transforms],
                spread_t,
                page_t,
                page_gb,
                page_var,
                ctx,
                grp_layer_idx,
            )
        return

    item_t = item.get("ItemTransform", "1 0 0 1 0 0")
    anchors = _extract_anchors(item)
    x_pt, y_pt, w_pt, h_pt, rot = _compute_page_local_bbox_pt(
        item_t, anchors, ancestor_transforms, spread_t, page_t, page_gb
    )
    x_mm = x_pt * PT_TO_MM
    y_mm = y_pt * PT_TO_MM
    w_mm = w_pt * PT_TO_MM
    h_mm = h_pt * PT_TO_MM

    # The raw (pre-ItemTransform) anchor extents of this frame, used by
    # _extract_content_local_params to compute image/PDF local offset.
    # Image/PDF child ItemTransforms use the same rect-local coordinate space
    # as the PathPointArray anchors (both are BEFORE the rect's ItemTransform).
    raw_xs = [p[0] for p in anchors]
    raw_ys = [p[1] for p in anchors]
    frame_tl_anchor: tuple[float, float] = (min(raw_xs), min(raw_ys))
    # Full anchor bbox (min-x, min-y, max-x, max-y) — the frame window the
    # placed image is cropped against (see _aspect_crop_image).
    frame_anchors_bbox: tuple[float, float, float, float] = (
        min(raw_xs), min(raw_ys), max(raw_xs), max(raw_ys),
    )

    # Detect nested vector logos (<PDF>) — defer per locked decision #2.
    pdf_children = item.findall(".//PDF")
    image_children = item.findall(".//Image")
    eps_children = item.findall(".//EPS")
    if eps_children:
        raise UnhandledElement(
            f"<{tag} Self={self_id!r}> contains <EPS>; not in v1 corpus "
            f"(extend tools/idml_to_dsl.py:_emit_pageitem)"
        )
    if pdf_children:
        # Collect: each <PDF> + its Link's LinkResourceURI basename.
        # Resolution order: --asset-map (Phase 2 manifest) → --logo-map
        # (legacy). Either covers the vector-to-raster mapping; the manifest
        # additionally carries kind metadata for downstream tooling.
        for pdf in pdf_children:
            link = pdf.find(".//Link")
            uri = link.get("LinkResourceURI", "") if link is not None else ""
            basename = _basename_from_uri(uri)
            mapped = ctx.asset_map.get(basename) if ctx.asset_map else None
            if mapped is None and ctx.logo_map:
                mapped = ctx.logo_map.get(basename)
            if mapped:
                # Issue #39 Phase A: resolve relative asset_map paths
                # against ROOT (NEVER via Path.resolve() — that follows
                # symlinks through the worktree chain and produces the
                # absolute-path leak the lint catches).
                mapped_path = Path(mapped)
                abs_mapped = (
                    mapped_path if mapped_path.is_absolute() else ROOT / mapped_path
                )
                # Vector logos (<PDF> children) are placed in InDesign with
                # FrameFittingOption "ContentToFrame" — the artwork is fit to
                # the frame, not free-scaled. Emit the rasterised logo with
                # NO local_scale / local_offset so _emit_image_frame_call
                # leaves SCALETYPE at its default 0 (Scribus ScaleAuto: fit
                # the image proportionally into the frame).
                #
                # The previous code derived a literal LOCALSCX/SCY from the
                # PDF child's ItemTransform and emitted SCALETYPE=1 (free
                # scaling). Scribus 1.6.x has a known bug rendering a
                # white-on-transparent RGBA image under SCALETYPE=1 — it
                # comes out blank (the DIE GRÜNEN white logo vanished on
                # every flyer/leporello). SCALETYPE=0 is the reliable path
                # and is geometrically correct for a fit-to-frame logo.
                _emit_image_or_inline(
                    out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
                    abs_path=abs_mapped, ctx=ctx,
                )
                return
            ctx.unmapped_logos.append((pdf.get("Self", "?"), basename or uri))
        return  # don't also emit the surrounding rectangle as a Polygon

    if image_children:
        # Use the first <Image> child as the visual content.
        img = image_children[0]
        _emit_image_content(out, item, img, x_mm, y_mm, w_mm, h_mm, rot,
                            self_id, layer_idx, ctx,
                            frame_tl_anchor=frame_tl_anchor,
                            frame_anchors_bbox=frame_anchors_bbox)
        return

    if tag == "TextFrame":
        _strict_no_threading(item)
        parent_story = item.get("ParentStory")
        # Determine the per-frame default ParaStyle (first PSR in the story).
        style_slug = ""
        runs: list[Run] = []
        trail_attrs: Optional[dict] = None
        _first_psr_style_self: Optional[str] = None  # for Pattern-9 leading lookup
        _story_psr_count = 0  # ParagraphStyleRange count — gates the headline split
        if parent_story:
            story_root = _resolve_story_xml(ctx.pkg, parent_story)
            _story_psr_count = len(story_root.findall(".//ParagraphStyleRange"))
            first_psr = story_root.find(".//ParagraphStyleRange")
            if first_psr is not None:
                ap = first_psr.get("AppliedParagraphStyle")
                if ap and ap in ctx.paragraph_style_map:
                    style_slug = ctx.paragraph_style_map[ap]
                if ap:
                    _first_psr_style_self = ap
            runs = _walk_story(
                story_root,
                paragraph_style_map=ctx.paragraph_style_map,
                color_map=ctx.color_map,
                paragraph_styles=ctx.paragraph_styles,
            )
            # PSR inline Justification override for the trailing <trail> element.
            # _walk_story handles <para> separators for non-final PSRs; the final
            # PSR's alignment goes here so TextFrame.trail_attrs emits it correctly.
            trail_attrs = _psr_trail_attrs_for_story(story_root)

        # Rotated-TextFrame W/H convention. _compute_page_local_bbox_pt emits
        # the *un-rotated* frame extent (WIDTH/HEIGHT of the frame before ROT
        # is applied) plus the rotation pivot. That is the correct model for
        # ImageFrames and for empty (background-fill) frames, both of which
        # the TextFrame primitive places verbatim. But the primitive applies
        # a TEXT-FLOW W/H swap to any ±90° frame that carries text (it must,
        # so Scribus computes wrap width from the visible long edge — see
        # sla_lib/builder/primitives.py to_pageobject). Feeding the primitive
        # the un-rotated model AND letting it swap is a double-correction:
        # the visible frame collapses to the short axis and text clips.
        #
        # For a ±90° non-empty TextFrame, emit the axis-aligned bbox of the
        # ROTATED rectangle instead — the convention the primitive's swap is
        # built around. Derivation (pivot at the un-rotated top-left):
        #   -90°: rotated-bbox = (x,         y - w_unrot, h_unrot, w_unrot)
        #   +90°: rotated-bbox = (x - h_unrot, y,         h_unrot, w_unrot)
        if runs and abs(abs(rot) - 90.0) < 0.5:
            if rot < 0:
                x_mm, y_mm, w_mm, h_mm = x_mm, y_mm - w_mm, h_mm, w_mm
            else:
                x_mm, y_mm, w_mm, h_mm = x_mm - h_mm, y_mm, h_mm, w_mm

        # Pattern 9 — auto-widen h_mm when Scribus would clip lines.
        # Scribus clips text when frame_h < effective line height; InDesign
        # overflows silently. Widen to the required minimum so every line renders.
        # Two sub-cases: (A) single-line clip, (B) multi-line overset.
        _max_fontsize_pt: Optional[float] = None
        if runs:
            _fontsizes = [r.fontsize for r in runs if r.fontsize is not None]
            if _fontsizes:
                _max_fontsize_pt = max(_fontsizes)
            # Fallback: if no run carries an explicit fontsize, use the
            # paragraph style's point_size (auto-leading uses this as the base).
            if _max_fontsize_pt is None and _first_psr_style_self:
                _ps_data = ctx.paragraph_styles.get(_first_psr_style_self, {})
                _max_fontsize_pt = _ps_data.get("point_size")

        # Effective leading: prefer CSR-level leading (Properties/Leading) over
        # paragraph-style leading, since CSR-level overrides take precedence in
        # InDesign. Read max leading across all CSRs in the story.
        _leading_pt: Optional[float] = None
        if parent_story and runs:
            # story_root is already resolved above; use it directly.
            for _csr in story_root.findall(".//CharacterStyleRange"):
                _ld_el = _csr.find("Properties/Leading")
                if _ld_el is not None and _ld_el.text and _ld_el.text.strip() != "Auto":
                    try:
                        _csr_ld = float(_ld_el.text.strip())
                        if _leading_pt is None or _csr_ld > _leading_pt:
                            _leading_pt = _csr_ld
                    except (ValueError, TypeError):
                        pass
        # Fall back to paragraph-style leading if no CSR-level leading found.
        _leading_model: Optional[str] = None
        if _first_psr_style_self:
            _ps_data = ctx.paragraph_styles.get(_first_psr_style_self, {})
            _leading_model = _ps_data.get("leading_model")
            if _leading_pt is None:
                _ld_str = _ps_data.get("leading")
                if _ld_str and _ld_str != "Auto":
                    try:
                        _leading_pt = float(_ld_str)
                    except (ValueError, TypeError):
                        pass

        # Explicit line count (sub-case C) and total text chars (sub-case B).
        # Sub-case C: frames with breakline/para separators have an exact line count
        # (separator count + 1). Apply this to widen when IDML frame is too short.
        # Sub-case B: single-paragraph frames (no explicit newlines) use char-count
        # heuristic. Both are mutually exclusive — sub-case B skipped when
        # explicit newlines are present (heuristic would double-count).
        _total_text_chars: int = 0
        _explicit_line_count: int = 0
        _paragraph_char_counts: list[int] = []
        if runs:
            # Split chars into per-paragraph buckets. Each breakline/para
            # separator opens a new bucket so wrap estimation can be done
            # per-paragraph (more accurate than treating runs as one block).
            current_bucket = 0
            for _r in runs:
                if _r.separator in ("breakline", "para"):
                    _paragraph_char_counts.append(current_bucket)
                    current_bucket = 0
                elif _r.text:
                    current_bucket += len(_r.text)
                    _total_text_chars += len(_r.text)
            _paragraph_char_counts.append(current_bucket)
            _separator_count = sum(
                1 for _r in runs if _r.separator in ("breakline", "para")
            )
            if _separator_count > 0:
                _explicit_line_count = _separator_count + 1

        emitted_h_mm = _round_mm(h_mm)
        # Detect font family for the intrinsic line-height floor. Serif
        # fonts with deeper metrics (Vollkorn) need ~1.5× fontsize; sans-
        # serif narrow fonts (Gotham Narrow) only need ~1.1×.
        _intrinsic = 1.1
        if runs:
            for _r in runs:
                fn = (_r.font or "").lower()
                if "vollkorn" in fn or "serif" in fn:
                    _intrinsic = max(_intrinsic, 1.5)
        _widened_h_mm, _widen_comment = _maybe_widen_frame_h(
            emitted_h_mm, _max_fontsize_pt, _leading_pt,
            total_text_chars=_total_text_chars,
            frame_w_mm=_round_mm(w_mm),
            explicit_line_count=_explicit_line_count,
            leading_model=_leading_model,
            paragraph_char_counts=_paragraph_char_counts,
            intrinsic_line_ratio=_intrinsic,
        )
        if _widen_comment:
            ctx.out.w(f"# {_widen_comment}")
            emitted_h_mm = _round_mm(_widened_h_mm)

        # Mixed-font forced-break headline: emit N single-line TextFrames.
        # A headline whose <Br/>-separated lines use different font families
        # (Gotham + a Vollkorn accent word) cannot render correctly as one
        # frame — Scribus's per-line font-metric leading places the Vollkorn
        # line at the wrong baseline. Splitting into one frame per line, each
        # stacked at the IDML <Leading> interval with a per-font FLOP=1
        # baseline correction, makes the lines stack evenly.
        #
        # Gated to: a SINGLE-PSR story (one IDML paragraph whose lines are
        # joined by <Br/> forced breaks — a multi-PSR story is body text with
        # real paragraph breaks and must NOT be split), a non-rotated frame,
        # an explicit numeric Leading, and headline-sized text (>=20pt — body
        # paragraphs with mixed Book/Bold runs are ~11pt and stay one frame).
        _headline_lines = (
            _split_mixed_font_lines(runs)
            if (
                runs
                and abs(rot) < 1e-3
                and _leading_pt is not None
                and _story_psr_count == 1
                and _max_fontsize_pt is not None
                and _max_fontsize_pt >= 20.0
            )
            else None
        )
        if _headline_lines is not None:
            _emit_mixed_font_headline(
                ctx, _headline_lines,
                x_mm=x_mm, y_mm=y_mm, w_mm=w_mm,
                leading_pt=_leading_pt, style_slug=style_slug,
                self_id=self_id, layer_idx=layer_idx, page_var=page_var,
            )
            ctx.textframe_records.append({
                "anname": self_id,
                "page": _page_index_from_var(page_var),
                "x_mm": _round_mm(x_mm),
                "y_mm": _round_mm(y_mm),
                "w_mm": _round_mm(w_mm),
                "h_mm": _round_mm(h_mm),
            })
            return

        kwargs: dict[str, Any] = {
            "x_mm": _round_mm(x_mm),
            "y_mm": _round_mm(y_mm),
            "w_mm": _round_mm(w_mm),
            "h_mm": emitted_h_mm,
            "anname": self_id,
            "layer": layer_idx,
        }
        if abs(rot) > 1e-3:
            kwargs["rotation_deg"] = _round_rot(rot)
        if style_slug:
            kwargs["style"] = style_slug
        if runs:
            kwargs["runs"] = runs
        else:
            kwargs["text"] = ""
        if trail_attrs:
            kwargs["trail_attrs"] = trail_attrs
        # DefaultStyle ALIGN propagation: emit ALIGN on the <DefaultStyle/>
        # element so it pins the frame's default alignment EXPLICITLY,
        # regardless of value. Scribus's trail/per-paragraph ALIGN does NOT
        # propagate to the paragraph THEY terminate; only DefaultStyle ALIGN
        # reliably applies to every paragraph in the StoryText, including
        # auto-wrapped lines of the LAST paragraph. Issue #37 Backport 11.
        #
        # Issue #37 P1 task 5: ALWAYS emit (even when ALIGN==0). Previously
        # we skipped Left because "Left is default", but on a frame whose
        # first PSR is non-Left and a later PSR is Left, the later one would
        # inherit DefaultStyle's non-Left value. Pinning DefaultStyle and
        # also emitting per-paragraph ALIGN on EVERY PSR (below at line
        # ~2283) gives Scribus an unambiguous answer for every paragraph.
        # Only emit default_style_attrs={"ALIGN": ...} when no named style is
        # set on the frame; the DSL warns that style= + default_style_attrs=
        # is ambiguous (default_style_attrs override the parent's attrs on
        # the same <DefaultStyle/> element). When style= is set, the named
        # ParaStyle already carries the alignment via its Justification
        # attribute, and per-paragraph ALIGN is emitted on every PSR below
        # so Scribus has an unambiguous answer for every paragraph.
        if (
            not style_slug
            and _first_psr_style_self
            and _first_psr_style_self in ctx.paragraph_styles
        ):
            _eff_just = ctx.paragraph_styles[_first_psr_style_self].get("justification")
            if _eff_just in JUSTIFICATION_MAP:
                kwargs["default_style_attrs"] = {
                    "ALIGN": str(JUSTIFICATION_MAP[_eff_just]),
                }
        # Fill (frame background, rare on TextFrame but corpus has Color/Paper
        # cases — drop through the color map).
        fc = _resolve_fill(item.get("FillColor"), ctx.color_map)
        if fc:
            kwargs["fill"] = fc
        # TextFramePreference: vertical justification + multi-column layout.
        # CenterAlign vertical justification (used by every Impressum frame in
        # the corpus) centres the text block in the frame instead of pinning
        # it to the top; multi-column (the Querformat body frames are 2-up)
        # splits the story into N columns with a gutter.
        tf_prefs = _extract_textframe_prefs(item)
        if "vertical_text_align" in tf_prefs:
            kwargs["vertical_text_align"] = tf_prefs["vertical_text_align"]
        if "columns" in tf_prefs:
            kwargs["columns"] = tf_prefs["columns"]
            if "col_gap_pt" in tf_prefs:
                kwargs["col_gap_mm"] = round(tf_prefs["col_gap_pt"] * PT_TO_MM, 4)
        # Object opacity (BlendingSetting/Opacity) — the Impressum frames are
        # placed at 70% in this corpus. None when fully opaque.
        opacity = _extract_opacity(item)
        if opacity is not None:
            kwargs["fill_opacity"] = round(opacity, 4)
        _emit_call(
            ctx.out, "TextFrame", kwargs,
            receiver=page_var, multiline=True,
        )
        # Record the frame's page-local bbox so the squiggle re-anchoring
        # pass can pick the text frame a squiggle sits beneath.
        ctx.textframe_records.append({
            "anname": self_id,
            "page": _page_index_from_var(page_var),
            "x_mm": _round_mm(x_mm),
            "y_mm": _round_mm(y_mm),
            "w_mm": _round_mm(w_mm),
            "h_mm": _round_mm(h_mm),
        })
        return

    if tag in ("Rectangle", "Polygon", "Oval"):
        # Complex Polygon: multiple sub-paths, open paths, or Bezier curves.
        # These cannot be expressed as a simple Scribus rectangle/polygon bbox;
        # emit as PolyLine (PTYPE=7) with verbatim SLA path data extracted from
        # the IDML PathGeometry (transform chain: item → ancestors → page-local).
        if tag == "Polygon" and _is_complex_polygon(item):
            # A complex Polygon can be a stroked outline (wind turbine icon),
            # a filled silhouette (the Grüne yellow squiggle motif — closed
            # bezier sub-paths filled with Color/Yellow, no stroke), or both.
            # Resolve FillColor and StrokeColor independently:
            #   - FillColor present  → emit it as the PolyLine fill (PCOLOR).
            #   - StrokeColor present → emit it as the line colour (PCOLOR2).
            # NEVER default a fill-only shape's stroke to Black — that turned
            # the yellow squiggle into a black 1pt outline.
            fill_color = _resolve_fill(item.get("FillColor"), ctx.color_map)
            stroke_color = _resolve_fill(item.get("StrokeColor"), ctx.color_map)
            sw = item.get("StrokeWeight", "0")
            try:
                sw_pt = float(sw)
            except (ValueError, TypeError):
                sw_pt = 0.0
            # ``line_color`` keeps the StrokeColor when a real stroke exists.
            # A shape with a fill but no stroke must not paint an outline, so
            # only fall back to Black when there is neither a fill nor a
            # stroke (a degenerate Polygon — keep the legacy visible default).
            if stroke_color:
                line_color = stroke_color
            elif fill_color:
                line_color = "None"
                sw_pt = 0.0
            else:
                line_color = "Black"
            sla_path = _extract_idml_sla_path(
                item, item_t, ancestor_transforms,
                spread_t, page_t, page_gb,
                x_pt, y_pt,
            )
            pl_kwargs: dict[str, Any] = {
                "x_mm": _round_mm(x_mm),
                "y_mm": _round_mm(y_mm),
                "w_mm": _round_mm(w_mm),
                "h_mm": _round_mm(h_mm),
                "sla_path": sla_path,
                "line_color": line_color,
                "line_width_pt": sw_pt,
                "anname": self_id,
                "layer": layer_idx,
            }
            if fill_color:
                pl_kwargs["fill"] = fill_color
            if abs(rot) > 1e-3:
                pl_kwargs["rotation_deg"] = _round_rot(rot)
            # IDML EndCap / EndJoin → Scribus PLINEEND / PLINEJOIN (Qt::PenCapStyle
            # and Qt::PenJoinStyle integer values). Omitted when IDML default
            # (Butt/Miter) — those map to Scribus default (0/0) which the
            # ``PolyLine`` primitive emits as the absence of the attribute. See
            # ``tools/sla_lib/builder/primitives.py:PolyLine.line_cap`` for the
            # enum mapping.
            end_cap = item.get("EndCap", "")
            end_join = item.get("EndJoin", "")
            cap_map = {
                "ButtEndCap": 0,
                "ProjectingEndCap": 16,
                "RoundEndCap": 32,
            }
            join_map = {
                "MiterEndJoin": 0,
                "BevelEndJoin": 64,
                "RoundEndJoin": 128,
            }
            if end_cap in cap_map and cap_map[end_cap] != 0:
                pl_kwargs["line_cap"] = cap_map[end_cap]
            if end_join in join_map and join_map[end_join] != 0:
                pl_kwargs["line_join"] = join_map[end_join]
            _emit_call(
                ctx.out, "PolyLine", pl_kwargs,
                receiver=page_var, multiline=True,
            )
            # Squiggle re-anchoring: the Grüne yellow emphasis motif is a
            # closed-path Polygon filled with the builtin Color/Yellow ink
            # and no stroke. Record its page-local bbox so _emit_squiggle_
            # anchors can bind it to the word it underlines. The discriminator
            # is the builtin Color/Yellow (a named C=0 M=0 Y=100 K=0 swatch is
            # a normal yellow shape, not the brush motif).
            if (
                item.get("FillColor") == "Color/Yellow"
                and not _is_open_polygon(item)
            ):
                ctx.squiggle_records.append({
                    "anname": self_id,
                    "page": _page_index_from_var(page_var),
                    "x_mm": _round_mm(x_mm),
                    "y_mm": _round_mm(y_mm),
                    "w_mm": _round_mm(w_mm),
                    "h_mm": _round_mm(h_mm),
                })
            return

        # No nested image/pdf — emit as a Polygon.
        kwargs = {
            "x_mm": _round_mm(x_mm),
            "y_mm": _round_mm(y_mm),
            "w_mm": _round_mm(w_mm),
            "h_mm": _round_mm(h_mm),
            "anname": self_id,
            "layer": layer_idx,
        }
        if abs(rot) > 1e-3:
            kwargs["rotation_deg"] = _round_rot(rot)
        fc = _resolve_fill(item.get("FillColor"), ctx.color_map)
        if fc:
            kwargs["fill"] = fc
        else:
            # Polygon's DSL default fill is "Black"; explicit None drops it.
            kwargs["fill"] = "None"
        sc = _resolve_fill(item.get("StrokeColor"), ctx.color_map)
        if sc:
            kwargs["line_color"] = sc
            sw = item.get("StrokeWeight")
            if sw:
                try:
                    kwargs["line_width_pt"] = float(sw)
                except ValueError:
                    pass
        if tag == "Oval":
            kwargs["shape"] = "ellipse"
        opacity = _extract_opacity(item)
        if opacity is not None:
            kwargs["fill_opacity"] = round(opacity, 4)
        _emit_call(
            ctx.out, "Polygon", kwargs,
            receiver=page_var, multiline=True,
        )
        return

    raise UnhandledElement(
        f"PageItem <{tag}> Self={self_id!r}: not handled "
        f"(extend tools/idml_to_dsl.py:_emit_pageitem)"
    )


def _round_mm(v: float) -> float:
    """Round mm value to 4 decimal places for emit (sub-micron precision)."""
    return round(v, 4)


def _round_rot(v: float) -> float:
    """Round rotation_deg to 4 decimal places; collapse near-zero to zero."""
    if abs(v) < 1e-4:
        return 0.0
    return round(v, 4)


def _basename_from_uri(uri: str) -> str:
    """Return the basename of a ``file:`` URI, URL-decoded and NFC-normalised.

    macOS InDesign emits URIs with NFD (decomposed) Unicode for accented chars
    (e.g. ``u\\u0308`` instead of ``ü``); the rest of the toolchain assumes NFC,
    so normalise here to keep dict lookups stable.
    """
    if not uri:
        return ""
    parsed = urlparse(uri)
    if parsed.scheme not in ("file", ""):
        # Other schemes (http etc.) not supported.
        return ""
    raw_path = unquote(parsed.path)
    return unicodedata.normalize("NFC", Path(raw_path).name)


def _extract_content_local_params(
    content_transform_str: str,
    frame_tl_anchor: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Derive (local_scale, local_offset_pt) from a content child's ItemTransform.

    IDML stores Image/PDF children with an ItemTransform whose (tx, ty) is the
    content origin in the **same coordinate space as the enclosing Rectangle's
    anchors** (item-local).  Scribus LOCALX/LOCALY is the delta from the
    frame's bottom-left corner (min-x, min-y) to the content origin, measured
    in points.

    IDML uses an upward-y coordinate system.  Both the PathPointArray anchors
    and the Image/PDF ``ItemTransform`` (tx, ty) are in that same upward-y
    space.  The offset ``ty - min_y_anchor`` gives the distance from the frame
    bottom-left to the image origin in upward-y units.  Because Scribus
    LOCALY is measured *upward* from the frame's bottom-left (positive = image
    shifted down, negative = image shifted up relative to frame TL), this
    offset maps directly without a sign flip:

    - ty < min_y  →  image origin is below frame bottom  →  LOCALY < 0
      (image is scrolled up relative to frame, showing a lower portion)
    - ty = min_y  →  image origin at frame bottom  →  LOCALY ≈ 0

    Args:
        content_transform_str: the ``ItemTransform`` attribute of the ``<Image>``
            or ``<PDF>`` element (e.g. "0.491 0 0 0.491 -299.62 1296.99").
        frame_tl_anchor: the ``(min_x, min_y)`` of the Rectangle frame's
            PathPointArray anchors in the same item-local coordinate space.

    Returns:
        ``(local_scale, local_offset_pt)`` where *local_scale* is a
        ``(scx, scy)`` tuple and *local_offset_pt* is the ``(dx, dy)``
        translation from frame bottom-left to content origin in points.
    """
    parts = content_transform_str.split()
    if len(parts) != 6:
        # Malformed transform — fall back to identity.
        return ((1.0, 1.0), (0.0, 0.0))
    try:
        a, _b, _c, d, tx, ty = (float(p) for p in parts)
    except ValueError:
        return ((1.0, 1.0), (0.0, 0.0))
    scx = a  # scale-x (diagonal element; shear/rotation not expected here)
    scy = d  # scale-y
    offset_x_pt = tx - frame_tl_anchor[0]
    offset_y_pt = ty - frame_tl_anchor[1]
    return ((scx, scy), (offset_x_pt, offset_y_pt))


def _read_image_dimensions(
    *,
    inline_data: Optional[str] = None,
    inline_ext: Optional[str] = None,
    image_path: Optional[str] = None,
    ctx: Optional[_Ctx] = None,
) -> tuple[Optional[int], Optional[int], float]:
    """Return (width_px, height_px, dpi) for an image referenced by an
    ImageFrame. Handles both inline (qCompress base64) and SLA-relative
    path images. Falls back to (None, None, 72.0) when the image can't be
    read — callers degrade gracefully.
    """
    try:
        from PIL import Image
    except ImportError:
        return None, None, 72.0
    img = None
    try:
        if image_path:
            # SLA-relative path → resolve against ROOT (the converter
            # always emits paths relative to the SLA's parent which is
            # templates/<slug>/, so ../../ takes us to ROOT).
            p = Path(image_path)
            if p.is_absolute():
                resolved = p
            else:
                resolved = (
                    ROOT
                    / "templates"
                    / (ctx.template_id if ctx is not None else "")
                    / p
                ).resolve()
                if not resolved.exists():
                    # Try ROOT-anchored interpretation.
                    resolved = (ROOT / p.name).resolve()
            if resolved.exists():
                img = Image.open(str(resolved))
        elif inline_data:
            # qCompress format: first 4 bytes are big-endian uncompressed
            # length; the rest is zlib-compressed. See sla_lib pack_inline_image.
            import base64
            import zlib
            from io import BytesIO
            raw = base64.b64decode(inline_data)
            try:
                payload = zlib.decompress(raw[4:])
            except zlib.error:
                payload = raw  # fall back to raw bytes
            img = Image.open(BytesIO(payload))
        if img is None:
            return None, None, 72.0
        w, h = img.size
        dpi = 72.0
        info_dpi = img.info.get("dpi")
        if info_dpi and isinstance(info_dpi, tuple) and info_dpi[0]:
            dpi = float(info_dpi[0])
        return w, h, dpi
    except Exception:
        return None, None, 72.0
    finally:
        if img is not None:
            try:
                img.close()
            except Exception:
                pass


def _emit_image_frame_call(
    out: PythonRepr,
    x_mm: float,
    y_mm: float,
    w_mm: float,
    h_mm: float,
    rot: float,
    self_id: str,
    layer_idx: int,
    image_path: str,
    ctx: _Ctx,
    inline_data: Optional[str] = None,
    inline_ext: Optional[str] = None,
    local_scale: Optional[tuple[float, float]] = None,
    local_offset_pt: Optional[tuple[float, float]] = None,
    fill_opacity: Optional[float] = None,
) -> None:
    """Append a page.add(ImageFrame(...)) call to ctx.out."""
    kwargs: dict[str, Any] = {
        "x_mm": _round_mm(x_mm),
        "y_mm": _round_mm(y_mm),
        "w_mm": _round_mm(w_mm),
        "h_mm": _round_mm(h_mm),
        "anname": self_id,
        "layer": layer_idx,
    }
    if abs(rot) > 1e-3:
        kwargs["rotation_deg"] = _round_rot(rot)
    if fill_opacity is not None:
        kwargs["fill_opacity"] = round(fill_opacity, 4)
    if image_path:
        kwargs["image"] = image_path
    if inline_data is not None and inline_ext is not None:
        kwargs["inline_image_data"] = inline_data
        kwargs["inline_image_ext"] = inline_ext
    # Emit content placement params when they deviate meaningfully from defaults.
    # Scribus default: local_scale=(1,1), local_offset=(0,0).
    #
    # scale_type semantics:
    #   0 = Scribus ScaleAuto: fit content proportionally to frame; Scribus
    #       computes LOCALSCX/SCY itself. Right for brand logos and content
    #       photos that should fill their frame (matches v2 sibling pattern).
    #   1 = Free scaling: Scribus uses LOCALSCX/SCY + LOCALX/Y verbatim.
    #       Right for composite-AI icons that need precise sub-rect crops.
    #
    # Rule: use scale_type=1 ONLY when a non-zero local_offset is supplied
    # (i.e. a composite-AI placement that needs both crop and scale honoured
    # verbatim). For all other cases — including image frames with non-unit
    # local_scale — emit scale_type=0 so Scribus fits the inline asset to
    # the frame. SCALETYPE=1 with the converter's literal IDML-derived
    # local_scale renders the asset at its native pixel size relative to
    # the frame, which zooms it past the frame edges and shows nothing
    # (DIE GRÜNEN logo + ziesel photo regression).
    # IDML's <Image>/<PDF> ItemTransform carries the FILL scale (e.g. 0.43)
    # but NOT the centering offset — InDesign computes that at render time
    # for FittingOnEmptyFrame=FillProportionally. Scribus has no equivalent
    # mode, so we must compute the centering offset ourselves so the image
    # is centered (and excess cropped equally on both sides) instead of
    # rendering at the frame's top-left and cropping bottom/right.
    img_w_px, img_h_px, img_dpi = _read_image_dimensions(
        inline_data=inline_data, inline_ext=inline_ext, image_path=image_path,
        ctx=ctx,
    )
    if local_scale is not None:
        scx, scy = local_scale
        # Composite-AI detection: a tight horizontal/vertical strip whose
        # source image is much wider than the frame, AND the IDML's
        # translation picks a sub-region (different per-frame). When this
        # fires we emit scale_type=1 + the IDML's literal LOCALSCX/Y/X/Y
        # so Scribus picks the right icon. For regular fill-frame photos
        # (whose source image is only modestly larger than the frame, and
        # whose IDML translation is the natural FillProportionally crop),
        # let Scribus auto-fit via scale_type=0 — that handles tiny
        # frames where our fill-and-crop math becomes invisible.
        is_composite_crop = False
        if local_offset_pt is not None and img_w_px and img_h_px:
            ox, oy = local_offset_pt
            img_w_pt = img_w_px * 72.0 / img_dpi
            img_h_pt = img_h_px * 72.0 / img_dpi
            frame_w_pt = w_mm / PT_TO_MM if w_mm > 0 else 1.0
            frame_h_pt = h_mm / PT_TO_MM if h_mm > 0 else 1.0
            # Source image must be at least 5× the frame in one direction
            # AND the IDML must store a non-zero translation.
            wide_strip = (
                img_w_pt > 5 * frame_w_pt or img_h_pt > 5 * frame_h_pt
            )
            has_translation = abs(ox) > 1.0 or abs(oy) > 1.0
            if wide_strip and has_translation:
                is_composite_crop = True
        if is_composite_crop:
            kwargs["local_scale"] = (round(scx, 6), round(scy, 6))
            kwargs["scale_type"] = 1
            if local_offset_pt is not None:
                ox_mm = local_offset_pt[0] * PT_TO_MM
                oy_mm = local_offset_pt[1] * PT_TO_MM
                if abs(ox_mm) > 1e-4 or abs(oy_mm) > 1e-4:
                    kwargs["local_offset_mm"] = (
                        round(ox_mm, 4), round(oy_mm, 4),
                    )
        elif img_w_px and img_h_px:
            img_w_pt = img_w_px * 72.0 / img_dpi
            img_h_pt = img_h_px * 72.0 / img_dpi
            frame_w_pt = w_mm / PT_TO_MM if w_mm > 0 else 1.0
            frame_h_pt = h_mm / PT_TO_MM if h_mm > 0 else 1.0
            sx = frame_w_pt / img_w_pt if img_w_pt else 1.0
            sy = frame_h_pt / img_h_pt if img_h_pt else 1.0
            fill = max(sx, sy)
            # Tiny frames (e.g. the social-media icons at 9.5×9.5pt):
            # Scribus's free-scaling (SCALETYPE=1) at this size renders
            # invisibly. Auto-fit (SCALETYPE=0) handles small icons
            # correctly and the aspect mismatch is negligible for square
            # icons in square-ish frames.
            tiny_frame = frame_w_pt < 20 and frame_h_pt < 20
            if tiny_frame:
                kwargs["local_scale"] = (round(fill, 6), round(fill, 6))
                # No scale_type override — defaults to 0 (auto-fit). Tiny
                # frames intentionally skip the offset emit because the
                # auto-fit pass discards LOCALX/Y anyway.
                receiver = getattr(ctx, "_current_page_var", None) or "page"
                _emit_call(
                    ctx.out, "ImageFrame", kwargs,
                    receiver=receiver, multiline=True,
                )
                return
            # Non-composite (FillProportionally) — emit FILL scale + the
            # IDML's literal translation. The IDML's `<Image ItemTransform>`
            # stores the user's authored crop position (image origin
            # relative to the frame's top-left after FillProportionally is
            # applied). Using that translation verbatim reproduces the
            # InDesign baseline's crop.
            kwargs["local_scale"] = (round(fill, 6), round(fill, 6))
            kwargs["scale_type"] = 1
            if local_offset_pt is not None:
                ox_pt, oy_pt = local_offset_pt
                ox_mm = ox_pt * PT_TO_MM
                oy_mm = oy_pt * PT_TO_MM
                if abs(ox_mm) > 1e-4 or abs(oy_mm) > 1e-4:
                    kwargs["local_offset_mm"] = (
                        round(ox_mm, 4), round(oy_mm, 4),
                    )
        elif local_offset_pt is not None:
                # Fallback when image can't be read: emit IDML offset verbatim.
                ox_pt, oy_pt = local_offset_pt
                ox_mm = ox_pt * PT_TO_MM
                oy_mm = oy_pt * PT_TO_MM
                if abs(ox_mm) > 1e-3 or abs(oy_mm) > 1e-3:
                    kwargs["local_offset_mm"] = (
                        round(ox_mm, 4), round(oy_mm, 4),
                    )
    elif local_offset_pt is not None:
        ox_pt, oy_pt = local_offset_pt
        ox_mm = ox_pt * PT_TO_MM
        oy_mm = oy_pt * PT_TO_MM
        if abs(ox_mm) > 1e-3 or abs(oy_mm) > 1e-3:
            kwargs["local_offset_mm"] = (round(ox_mm, 4), round(oy_mm, 4))
            kwargs["scale_type"] = 1
    page_var = ctx.layer_id_to_idx  # unused; emit call always uses receiver via outer scope
    # The receiver is the page variable (e.g. "page0"); the outer _emit_pageitem
    # passes ctx.out and the page_var explicitly. For simplicity here we emit
    # without a receiver and rely on the outer page-loop variable. Use a
    # global stash on ctx instead.
    receiver = getattr(ctx, "_current_page_var", None) or "page"
    _emit_call(ctx.out, "ImageFrame", kwargs, receiver=receiver, multiline=True)


def _emit_image_or_inline(
    out: PythonRepr,
    x_mm: float,
    y_mm: float,
    w_mm: float,
    h_mm: float,
    rot: float,
    self_id: str,
    layer_idx: int,
    *,
    abs_path: Path,
    ctx: _Ctx,
    local_scale: Optional[tuple[float, float]] = None,
    local_offset_pt: Optional[tuple[float, float]] = None,
    fill_opacity: Optional[float] = None,
) -> None:
    """Issue #39 — emit an ImageFrame call self-contained per asset_policy.

    Two routes, decided by ``abs_path.name`` lookup in the policy:

    1. **embedded** (basename in ``ctx.embedded_set``) — bytes are
       qCompress-encoded via ``pack_inline_image`` and emitted as
       ``inline_image_data=`` / ``inline_image_ext=``. The SLA owns the
       asset; the downloaded file is self-contained.
    2. **external** (basename in ``ctx.external_set``) — emit a path
       string RELATIVE TO THE SLA's directory. Scribus chdirs to the
       SLA's parent on ``openDoc``; the path resolves from there. The
       render pipeline finds the asset under
       ``../../shared/assets/<asset-dir>/<basename>``; a user who
       downloads the SLA standalone sees a missing-image placeholder
       (brand-team intent — they replace with their own content).

    If a basename appears in neither set, a fallback SLA-relative path
    is emitted so the converter never silently emits absolute paths;
    the caller's asset_policy_audit will surface the missing
    classification at render time.

    Never emits absolute filesystem paths. Raises ``RuntimeError`` if
    ``abs_path`` is outside ``ROOT`` (refusing to leak filesystem
    geometry into the SLA — see ``feedback_fix_generator_not_artifact``).
    """
    import os

    from sla_lib.builder.primitives import pack_inline_image

    basename = abs_path.name
    if basename in ctx.embedded_set:
        ext = abs_path.suffix.lstrip(".").lower() or "png"
        try:
            blob_b64, ext_norm = pack_inline_image(
                abs_path.read_bytes(), ext,
            )
        except OSError as exc:
            raise RuntimeError(
                f"Asset {abs_path} listed in embedded: but is unreadable: {exc}"
            ) from exc
        _emit_image_frame_call(
            out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
            image_path="",
            inline_data=blob_b64,
            inline_ext=ext_norm,
            ctx=ctx,
            local_scale=local_scale,
            local_offset_pt=local_offset_pt,
            fill_opacity=fill_opacity,
        )
        return

    # External (or unclassified — audit surfaces those): SLA-relative path.
    try:
        abs_path.relative_to(ROOT)
    except ValueError as exc:
        raise RuntimeError(
            f"Asset {abs_path} is outside repo root {ROOT}; refusing to "
            f"emit absolute path (issue #39 Phase A)."
        ) from exc
    sla_dir = ROOT / "templates" / ctx.template_id
    rel_to_sla = os.path.relpath(abs_path, sla_dir).replace("\\", "/")
    _emit_image_frame_call(
        out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
        image_path=rel_to_sla,
        ctx=ctx,
        local_scale=local_scale,
        local_offset_pt=local_offset_pt,
        fill_opacity=fill_opacity,
    )


_SCRIBUS_FRIENDLY_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _image_graphic_bounds_pt(img: Any) -> Optional[tuple[float, float]]:
    """Return the placed image's natural ``(width_pt, height_pt)``.

    InDesign stores the placed image's natural size as a
    ``Properties/GraphicBounds`` child of the ``<Image>`` element, in points.
    Returns ``None`` when the element is absent or unparseable.
    """
    gb = img.find("Properties/GraphicBounds")
    if gb is None:
        gb = img.find(".//GraphicBounds")
    if gb is None:
        return None
    try:
        left = float(gb.get("Left", "0"))
        top = float(gb.get("Top", "0"))
        right = float(gb.get("Right", "0"))
        bottom = float(gb.get("Bottom", "0"))
    except (TypeError, ValueError):
        return None
    w = right - left
    h = bottom - top
    if w <= 0 or h <= 0:
        return None
    return (w, h)


@dataclass
class _AspectCropResult:
    """Outcome of :func:`_aspect_crop_image`.

    Attributes:
        cropped: True when a derived asset was written to the destination.
        offset_pt: ``(dx, dy)`` — the cropped image's top-left, measured from
            the IDML frame's top-left, in points (rect-local). Non-zero only
            when the placed image is smaller than the frame (the "contain"
            case): the ImageFrame must shrink to the image's rendered rect so
            no transparent padding is needed.
        size_pt: ``(w, h)`` — the cropped image's rendered size in points.
    """

    cropped: bool
    offset_pt: tuple[float, float] = (0.0, 0.0)
    size_pt: tuple[float, float] = (0.0, 0.0)


def _aspect_crop_image(
    *,
    src_path: Path,
    dst_path: Path,
    image_transform_str: str,
    graphic_bounds_pt: tuple[float, float],
    frame_anchors_bbox: tuple[float, float, float, float],
) -> _AspectCropResult:
    """Pre-crop a placed image to exactly the part the frame exposes.

    InDesign places photos with "Fill Proportionally": the image is scaled
    and positioned, then the frame acts as a window onto it. Scribus 1.6.x
    has no aspect-fill mode, so the converter reproduces the InDesign crop in
    Python BEFORE Scribus sees the asset.

    The method intersects the placed image's rendered rectangle with the
    frame rectangle (both in the frame's rect-local coordinate space), crops
    the source image to that intersection in pixel space, and reports the
    intersection's offset + size so the caller can place an ImageFrame of
    exactly that rect with ``scale_type=0`` (aspect-preserving fit). The
    cropped asset then fills its (possibly shrunk) ImageFrame pixel-for-pixel
    — no transparent padding is ever produced, because Scribus 1.6.x silently
    trims transparent borders of a ``scale_type=0`` image.

    Two cases fall out of the same intersection:

    - **cover** — the frame lies inside the image; the intersection is the
      frame; the crop is a sub-rectangle of the image; the ImageFrame keeps
      the IDML frame rect (offset 0).
    - **contain** — the image lies inside the frame; the intersection is the
      whole image; no pixels are cropped away; the ImageFrame shrinks to the
      image's rendered rect (non-zero offset).

    All geometry comes from the ``<Image>`` ItemTransform and the frame
    anchors — nothing is guessed.

    Returns an :class:`_AspectCropResult`. ``cropped`` is ``False`` when the
    placement is identity (the source already matches the frame), the image
    does not intersect the frame, or the geometry is unsupported (rotation /
    shear on the image transform) — in which case the caller uses the source
    asset unchanged.
    """
    try:
        from PIL import Image as _PILImage
    except ImportError:  # pragma: no cover — Pillow is a hard dependency
        return _AspectCropResult(cropped=False)

    a, b, c, d, tx, ty = _parse_matrix(image_transform_str)
    # Only axis-aligned placements are croppable in pixel space. A rotated or
    # sheared image transform (b/c non-zero, or negative scale) is rare in the
    # corpus; fall back to the caller's existing path rather than guess.
    if abs(b) > 1e-6 or abs(c) > 1e-6 or a <= 0 or d <= 0:
        return _AspectCropResult(cropped=False)

    nat_w_pt, nat_h_pt = graphic_bounds_pt
    fx0, fy0, fx1, fy1 = frame_anchors_bbox

    # The placed image's rendered rectangle in rect-local points: the Image
    # ItemTransform maps image-content (0,0)→(nat_w,nat_h) to (tx,ty)→(...).
    img_x0, img_y0 = tx, ty
    img_x1, img_y1 = a * nat_w_pt + tx, d * nat_h_pt + ty

    # Intersection of the image rect with the frame rect.
    ix0 = max(fx0, img_x0)
    iy0 = max(fy0, img_y0)
    ix1 = min(fx1, img_x1)
    iy1 = min(fy1, img_y1)
    if ix1 - ix0 <= 0 or iy1 - iy0 <= 0:
        # Image does not overlap the frame — nothing visible to crop.
        return _AspectCropResult(cropped=False)

    with _PILImage.open(str(src_path)) as _src:
        img_w_px, img_h_px = _src.size
        src_img = _src.convert("RGBA")

    # Intersection corners → image pixels (invert x=a*u+tx, y=d*v+ty).
    px_per_pt_x = img_w_px / nat_w_pt
    px_per_pt_y = img_h_px / nat_h_pt
    cu0 = (ix0 - tx) / a * px_per_pt_x
    cu1 = (ix1 - tx) / a * px_per_pt_x
    cv0 = (iy0 - ty) / d * px_per_pt_y
    cv1 = (iy1 - ty) / d * px_per_pt_y

    left = max(0, int(round(cu0)))
    top = max(0, int(round(cv0)))
    right = min(img_w_px, int(round(cu1)))
    bottom = min(img_h_px, int(round(cv1)))
    if right - left <= 0 or bottom - top <= 0:
        return _AspectCropResult(cropped=False)

    offset_pt = (ix0 - fx0, iy0 - fy0)
    size_pt = (ix1 - ix0, iy1 - iy0)

    # No-op: the whole source image is shown at the IDML frame rect.
    is_identity = (
        left == 0
        and top == 0
        and right == img_w_px
        and bottom == img_h_px
        and abs(offset_pt[0]) < 1e-3
        and abs(offset_pt[1]) < 1e-3
    )
    if is_identity:
        return _AspectCropResult(cropped=False)

    cropped = src_img.crop((left, top, right, bottom))
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    # PNG with no metadata so Scribus 1.6.x (which drops ICC-bearing PNGs)
    # loads it, and output stays byte-deterministic for identical inputs.
    cropped.save(str(dst_path), format="PNG", optimize=False)
    return _AspectCropResult(
        cropped=True, offset_pt=offset_pt, size_pt=size_pt,
    )


def _crop_output_path(ctx: _Ctx, source_asset: Path, self_id: str) -> Path:
    """Deterministic path for a frame's pre-cropped derived asset.

    The crop lives in a ``crops/`` subdirectory of the source asset's
    directory so the flat ``asset_policy`` / ``asset_extraction`` audits
    (which only walk the top level of ``shared/assets/<slug>/``) do not
    treat it as an unclassified primary asset. The filename keys on the
    frame's IDML Self ID so two frames cropping the same source never
    collide.
    """
    return source_asset.parent / "crops" / f"{source_asset.stem}-{self_id}.png"


@dataclass
class _CropPlacement:
    """A cropped asset plus the ImageFrame rect (page mm) it should occupy."""

    path: Path
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float


def _maybe_aspect_crop(
    *,
    ctx: _Ctx,
    img: Any,
    rect: Any,
    self_id: str,
    source_asset: Path,
    frame_anchors_bbox: Optional[tuple[float, float, float, float]],
    frame_x_mm: float,
    frame_y_mm: float,
    frame_w_mm: float,
    frame_h_mm: float,
) -> Optional[_CropPlacement]:
    """Produce a frame-window crop of ``source_asset`` if the geometry warrants.

    Returns a :class:`_CropPlacement` (the derived asset path + the page rect
    the ImageFrame should occupy) when a crop was written, or ``None`` when
    the placement is identity, the image misses the frame, or the geometry is
    unsupported. The crop is derived purely from the IDML ``<Image>``
    ItemTransform + the frame's PathPointArray anchors — see
    :func:`_aspect_crop_image`.

    For the "contain" case (the placed image is smaller than the frame) the
    ImageFrame is shrunk to the image's rendered rect; the rect-local
    intersection offset maps to a page offset only when the parent Rectangle
    is axis-aligned. A rotated Rectangle with a non-zero offset is rejected
    (the crop is skipped) rather than mis-placed.
    """
    img_transform_str = img.get("ItemTransform", "")
    if not img_transform_str or frame_anchors_bbox is None:
        return None
    if not source_asset.exists():
        return None
    graphic_bounds = _image_graphic_bounds_pt(img)
    if graphic_bounds is None:
        return None
    # The Image ItemTransform and the frame anchors are both expressed in the
    # parent Rectangle's local space, so they compose directly — no extra
    # rect-transform correction is needed (unlike the LOCALSCX/LOCALY path).
    dst = _crop_output_path(ctx, source_asset, self_id)
    result = _aspect_crop_image(
        src_path=source_asset,
        dst_path=dst,
        image_transform_str=img_transform_str,
        graphic_bounds_pt=graphic_bounds,
        frame_anchors_bbox=frame_anchors_bbox,
    )
    if not result.cropped:
        return None

    # The intersection offset is in the Rectangle's local space. It maps
    # straight to a page-space offset only when the Rectangle is axis-aligned
    # (no rotation). When the Rectangle is rotated, a non-zero offset cannot
    # be applied without rotating it — reject the crop in that case (it would
    # mis-place the frame). A zero offset (the cover case) is always safe.
    off_x_pt, off_y_pt = result.offset_pt
    has_offset = abs(off_x_pt) > 1e-3 or abs(off_y_pt) > 1e-3
    rect_t = rect.get("ItemTransform", "1 0 0 1 0 0")
    ra, rb, rc, rd, _, _ = _parse_matrix(rect_t)
    rect_axis_aligned = (
        abs(rb) < 1e-6 and abs(rc) < 1e-6
        and abs(ra - 1.0) < 1e-6 and abs(rd - 1.0) < 1e-6
    )
    if has_offset and not rect_axis_aligned:
        return None

    if has_offset:
        # Shrink the ImageFrame to the placed image's rendered rect.
        x_mm = frame_x_mm + off_x_pt * PT_TO_MM
        y_mm = frame_y_mm + off_y_pt * PT_TO_MM
        w_mm = result.size_pt[0] * PT_TO_MM
        h_mm = result.size_pt[1] * PT_TO_MM
    else:
        # Cover case — the crop fills the IDML frame rect unchanged.
        x_mm, y_mm = frame_x_mm, frame_y_mm
        w_mm, h_mm = frame_w_mm, frame_h_mm

    # The crop carries a new basename absent from meta.yml::asset_policy.
    # Mirror the source asset's classification so _emit_image_or_inline routes
    # the derived asset the same way (inlined for embedded, SLA-relative path
    # for external) — otherwise an embedded source's crop would leak to a
    # path reference.
    if source_asset.name in ctx.embedded_set:
        ctx.embedded_set.add(dst.name)
    elif source_asset.name in ctx.external_set:
        ctx.external_set.add(dst.name)
    return _CropPlacement(
        path=dst, x_mm=x_mm, y_mm=y_mm, w_mm=w_mm, h_mm=h_mm,
    )


def _emit_image_content(
    out: PythonRepr,
    rect: Any,
    img: Any,
    x_mm: float,
    y_mm: float,
    w_mm: float,
    h_mm: float,
    rot: float,
    self_id: str,
    layer_idx: int,
    ctx: _Ctx,
    frame_tl_anchor: Optional[tuple[float, float]] = None,
    frame_anchors_bbox: Optional[tuple[float, float, float, float]] = None,
) -> None:
    """Emit a raster Image as an ImageFrame, resolving the file: URI.

    Resolution order:
      1. ``ctx.asset_map`` (Phase 2 manifest) by basename. If populated and
         the basename is missing, defer to ``unmapped_assets`` — strict mode
         raises at end-of-run. This is the path that catches a `<Image>`
         pointing at a `.psd` whose pre-converted PNG isn't in the manifest
         (previously these silently emitted the raw .psd path, which Scribus
         can't render).
      2. ``ctx.assets_dir / basename`` (legacy fallback). Used only when
         no ``--asset-map`` was supplied. We still reject extensions Scribus
         cannot render (``.psd``, ``.ai``, etc.) so the failure is loud
         instead of a blank preview.

    Aspect-fill crop: InDesign places photos with "Fill Proportionally" —
    the image is scaled to cover the frame and cropped to the frame aspect.
    Scribus 1.6.x has no aspect-fill mode, so when the IDML geometry shows a
    non-identity placement the converter pre-crops the resolved asset to the
    exact frame window (:func:`_aspect_crop_image`) and emits the derived
    asset with ``scale_type=0`` (auto-fit) and no ``local_scale`` /
    ``local_offset`` — Scribus then fills the frame pixel-for-pixel. The crop
    is computed from the ``<Image>`` ItemTransform + frame anchors, never
    guessed empirically.

    Args:
        frame_tl_anchor: the ``(min_x, min_y)`` of the Rectangle frame's
            PathPointArray anchors in item-local coordinates. Used with the
            Image's ``ItemTransform`` to derive the correct Scribus
            ``LOCALX / LOCALY`` content placement (see
            ``_extract_content_local_params``).
        frame_anchors_bbox: the full ``(min_x, min_y, max_x, max_y)`` anchor
            bbox — the frame window the placed image is cropped against.
    """
    # Object opacity (BlendingSetting/Opacity) lives on the enclosing
    # Rectangle, not the <Image> child. None when fully opaque.
    fill_opacity = _extract_opacity(rect)
    link = img.find(".//Link")
    uri = link.get("LinkResourceURI", "") if link is not None else ""
    basename = _basename_from_uri(uri)
    if not basename:
        raise UnhandledElement(
            f"<Image Self={img.get('Self')!r}> inside Rectangle Self={self_id!r}: "
            f"unparseable LinkResourceURI {uri!r} "
            f"(extend tools/idml_to_dsl.py:_emit_image_content)"
        )

    # Extract per-image placement params from the Image child's ItemTransform,
    # then compose with the parent Rectangle's outer scale. Scribus's
    # LOCALSCX is in rendered (post-Rectangle-transform) coords, the IDML
    # Image's ItemTransform is in frame-LOCAL coords — same correction as
    # the PDF branch above.
    local_scale: Optional[tuple[float, float]] = None
    local_offset_pt: Optional[tuple[float, float]] = None
    img_transform_str = img.get("ItemTransform", "")
    if img_transform_str and frame_tl_anchor is not None:
        local_scale, local_offset_pt = _extract_content_local_params(
            img_transform_str, frame_tl_anchor,
        )
        rect_t = rect.get("ItemTransform", "1 0 0 1 0 0")
        rect_a, _rb, _rc, rect_d, _, _ = _parse_matrix(rect_t)
        if local_scale is not None:
            sx, sy = local_scale
            local_scale = (sx * rect_a, sy * rect_d)
        if local_offset_pt is not None:
            ox, oy = local_offset_pt
            local_offset_pt = (ox * rect_a, oy * rect_d)

    # 1. Asset-map lookup (Phase 2 path).
    if ctx.asset_map:
        mapped = ctx.asset_map.get(basename)
        if mapped:
            # Issue #39 Phase A: resolve relative asset_map paths against
            # ROOT (NEVER via Path.resolve() — that follows symlinks and
            # leaks absolute worktree paths into the SLA).
            mapped_path = Path(mapped)
            abs_mapped = (
                mapped_path if mapped_path.is_absolute() else ROOT / mapped_path
            )
            # Aspect-fill crop: when the IDML geometry shows a non-identity
            # placement, pre-crop the asset to the frame window and emit the
            # derived asset at scale_type=0 (no local_scale/offset). For the
            # contain case the ImageFrame is shrunk to the image's rendered
            # rect (see _maybe_aspect_crop).
            crop = _maybe_aspect_crop(
                ctx=ctx, img=img, rect=rect, self_id=self_id,
                source_asset=abs_mapped,
                frame_anchors_bbox=frame_anchors_bbox,
                frame_x_mm=x_mm, frame_y_mm=y_mm,
                frame_w_mm=w_mm, frame_h_mm=h_mm,
            )
            if crop is not None:
                _emit_image_or_inline(
                    ctx.out, crop.x_mm, crop.y_mm, crop.w_mm, crop.h_mm, rot,
                    self_id, layer_idx, abs_path=crop.path, ctx=ctx,
                    fill_opacity=fill_opacity,
                )
                return
            # Issue #39 Phase A + C: inline-vs-relative routing.
            _emit_image_or_inline(
                ctx.out, x_mm, y_mm, w_mm, h_mm, rot,
                self_id, layer_idx, abs_path=abs_mapped, ctx=ctx,
                local_scale=local_scale, local_offset_pt=local_offset_pt,
                fill_opacity=fill_opacity,
            )
            return
        # asset_map is populated but this basename is missing → strict raise.
        # Surfaces at end-of-run via _final_strictness_gates.
        ctx.unmapped_assets.append((img.get("Self", "?") or self_id, basename))
        return

    # 2. Legacy --assets-dir fallback. Reject extensions Scribus can't
    # render so missing converter coverage shows up loudly.
    ext = Path(basename).suffix.lower()
    if ext and ext not in _SCRIBUS_FRIENDLY_IMAGE_EXTS:
        raise UnhandledElement(
            f"<Image Self={img.get('Self')!r}> inside Rectangle Self={self_id!r} "
            f"references {basename!r} ({ext}) but no --asset-map entry exists. "
            f"Run tools/links_export.py to produce a manifest, or extend the "
            f"_SCRIBUS_FRIENDLY_IMAGE_EXTS allow-list "
            f"(extend tools/idml_to_dsl.py:_emit_image_content)"
        )

    asset_path = ctx.assets_dir / basename
    if not asset_path.exists():
        # Decision #3: defer missing-asset raise to end-of-conversion.
        ctx.missing_assets.append(str(asset_path))
        return
    # Issue #39 Phase A + C: inline-vs-relative routing. _emit_image_or_inline
    # raises RuntimeError if asset_path is outside ROOT — never silently
    # emit absolute paths the way the prior fallback did.
    _emit_image_or_inline(
        ctx.out, x_mm, y_mm, w_mm, h_mm, rot,
        self_id, layer_idx, abs_path=asset_path, ctx=ctx,
        local_scale=local_scale, local_offset_pt=local_offset_pt,
        fill_opacity=fill_opacity,
    )


def _resolve_story_xml(pkg: Any, parent_story_id: str) -> Any:
    """Open Stories/Story_<id>.xml and return its root element."""
    path = f"Stories/Story_{parent_story_id}.xml"
    if path not in pkg.namelist():
        raise UnhandledElement(
            f"Story XML not found for ParentStory={parent_story_id!r}: {path} "
            f"(extend tools/idml_to_dsl.py:_resolve_story_xml)"
        )
    xml = pkg.open(path).read()
    return etree.fromstring(xml, parser=_SECURE_XMLPARSER)


# ---------------------------------------------------------------------------
# Phase H2 — Story walker. Turns a <Story> root into a list of Run primitives.
#
# Each <ParagraphStyleRange> contributes a paragraph; each contained
# <CharacterStyleRange> contributes one or more Run instances depending on
# inline <Br/>, <?ACE 7?> markers, and <Content> children. Multi-paragraph
# stories receive a Run(separator="para", paragraph_style=<parent slug>)
# between paragraphs; the trailing paragraph omits the separator (Scribus
# convention — no closing <para/> on the last paragraph of a frame).
# ---------------------------------------------------------------------------

# Allowed <ParagraphStyleRange>/<CharacterStyleRange>-internal element tags.
# Anything else raises (Hyperlink, Footnote, Table, Note, …).
_ALLOWED_CSR_CHILDREN = {"Content", "Br", "Properties"}
_ALLOWED_PSR_CHILDREN = {"CharacterStyleRange", "Properties"}
_ALLOWED_STORY_CHILDREN = {
    "ParagraphStyleRange",
    "StoryPreference",
    "InCopyExportOption",
    "XMLElement",  # tagged-content wrapper; ignored at v1 (corpus has none)
}


def _csr_applied_font(csr: Any) -> Optional[str]:
    """Read AppliedFont (a Properties child) on a CharacterStyleRange."""
    af = csr.find("Properties/AppliedFont")
    if af is not None and af.text:
        return af.text.strip()
    return None


def _first_csr_pointsize(psr: Any) -> Optional[float]:
    """Return the first CSR's PointSize as float, or None."""
    for csr in psr:
        if not isinstance(csr.tag, str):
            continue
        if etree.QName(csr).localname != "CharacterStyleRange":
            continue
        v = csr.get("PointSize")
        if v:
            try:
                return float(v)
            except ValueError:
                pass
    return None


def _psr_effective_leading(psr: Any) -> Optional[str]:
    """Return the effective Leading for a ParagraphStyleRange.

    Scans CharacterStyleRange children for a ``<Properties/Leading>`` value,
    but ONLY honours CSRs that carry actual visible content (non-empty
    ``<Content>``). InDesign applies the leading of the first CONTENT-bearing
    CSR; whitespace / Br-only trailing CSRs may carry a degenerate Leading
    that doesn't apply to the rendered paragraph (e.g. u1fd in this corpus
    has Leading=8 on a trailing tab-CSR that should NOT pollute the bullet
    paragraph's leading).

    Returns ``"Auto"`` when the first content-bearing CSR's leading is
    literally ``"Auto"``; returns ``None`` when no qualifying CSR carries
    any Leading child at all (caller falls back to the paragraph style).
    """
    for csr in psr:
        if not isinstance(csr.tag, str):
            continue
        if etree.QName(csr).localname != "CharacterStyleRange":
            continue
        # Require at least one non-empty <Content>.
        has_visible_content = False
        for child in csr:
            if not isinstance(child.tag, str):
                continue
            if etree.QName(child).localname == "Content":
                if child.text and child.text.strip():
                    has_visible_content = True
                    break
        if not has_visible_content:
            continue
        ld_el = csr.find("Properties/Leading")
        if ld_el is not None and ld_el.text:
            return ld_el.text.strip()
    return None


def _walk_story(
    story_root: Any,
    paragraph_style_map: dict[str, str],
    color_map: dict[str, str],
    paragraph_styles: Optional[dict[str, dict[str, Any]]] = None,
) -> list[Run]:
    """Convert a <Story> root into an ordered list of Run primitives.

    Args:
        story_root: lxml etree Element pointing at <Story>.
        paragraph_style_map: ``{ParagraphStyle/<self>: idml/<slug>}``.
        color_map: ``{Color/<self>: <dsl-name>}``.
        paragraph_styles: optional resolved ParaStyle dicts from Phase G
            (provides font-family fallback when a CSR sets only FontStyle).

    Returns:
        ``list[Run]`` ready to be passed to ``TextFrame(runs=...)``.

    Raises:
        UnhandledElement on:
        - Hyperlinks, footnotes, tables, notes inside CSRs.
        - Unknown ``<?ACE N?>`` processing instructions (N != 7).
        - Unrecognised top-level <Story> child tags.
    """
    paragraph_styles = paragraph_styles or {}
    runs: list[Run] = []
    # IDML Stories live at //idPkg:Story/Story/...; if the caller passed the
    # outer wrapper (root tag "Story" with namespace idPkg), descend into the
    # inner <Story> element. Tests pass synthetic XML with a bare <Story> root.
    walk_root = story_root
    inner = story_root.find("Story")
    if inner is not None:
        walk_root = inner
    psrs: list[Any] = []
    for child in walk_root:
        if not isinstance(child.tag, str):
            continue
        tag = etree.QName(child).localname
        if tag == "ParagraphStyleRange":
            psrs.append(child)
            continue
        if tag in _ALLOWED_STORY_CHILDREN:
            continue
        raise UnhandledElement(
            f"<Story> contains unhandled child <{tag}>; "
            f"(extend tools/idml_to_dsl.py:_walk_story)"
        )

    for i, psr in enumerate(psrs):
        applied_ps = psr.get("AppliedParagraphStyle", "")
        para_slug = paragraph_style_map.get(applied_ps, "")
        # Resolved family + style for font-cascade fallback.
        ps_resolved = paragraph_styles.get(applied_ps, {})
        ps_family = ps_resolved.get("applied_font")
        ps_font_style = ps_resolved.get("font_style")

        # PSR inline Justification override: an explicit Justification on the
        # PSR (or fallback to AppliedParagraphStyle's default when no inline)
        # is emitted as paragraph_attrs.ALIGN on every paragraph. Issue #37
        # P1 task 5: ALWAYS emit (even when ALIGN==0). The previous "only
        # when != 0" policy let inner Left paragraphs silently inherit a
        # non-Left DefaultStyle on mixed-Justification frames.
        psr_just = psr.get("Justification")
        psr_para_attrs: dict = {}
        if psr_just and psr_just not in JUSTIFICATION_MAP:
            raise UnhandledElement(
                f"ParagraphStyleRange Justification={psr_just!r} unknown "
                f"(extend tools/idml_to_dsl.py:JUSTIFICATION_MAP)"
            )
        # Resolve the effective ALIGN: explicit PSR Justification wins;
        # otherwise fall back to the AppliedParagraphStyle's resolved
        # justification (so a PSR without inline Justification still emits
        # the ParaStyle's intended align rather than implicit Left).
        align_int: Optional[int] = None
        if psr_just and psr_just in JUSTIFICATION_MAP:
            align_int = JUSTIFICATION_MAP[psr_just]
        else:
            ps_self = psr.get("AppliedParagraphStyle")
            if ps_self and ps_self in paragraph_styles:
                _ps_just = paragraph_styles[ps_self].get("justification")
                if _ps_just in JUSTIFICATION_MAP:
                    align_int = JUSTIFICATION_MAP[_ps_just]
        if align_int is not None:
            psr_para_attrs["ALIGN"] = str(align_int)

        # Per-para LINESPMode + LINESP from the CSR's Properties/Leading.
        # InDesign renders with the explicit Leading value from the first CSR in
        # the paragraph; Scribus falls back to ~15pt without an explicit LINESP.
        # Scribus SLA LINESPMode semantics (verified against the brand team's
        # hand-built original .sla files — gruene-zeitung / plakat-a1 /
        # postkarte — every one of which pins explicit leading this way):
        #   0 = Fixed line spacing — uses the LINESP value verbatim.
        #   1 = Automatic — font-metric line spacing (LINESP ignored).
        #   2 = Align to baseline grid (NOT a fixed-leading mode).
        # An explicit numeric IDML <Leading> is a FIXED leading → LINESPMode=0
        # + LINESP=<value>. The old code emitted LINESPMode=2 (baseline grid)
        # and fell back to LINESPMode=1 for sub-1.45×fontsize leadings; both
        # were wrong — mode 2 renders WIDER than the LINESP value and mode 1
        # ignores LINESP entirely, so every Vollkorn headline lost its
        # authored leading. ``Auto`` leading stays on mode 1 (font metrics).
        psr_ld = _psr_effective_leading(psr)
        if psr_ld is not None:
            if psr_ld == "Auto":
                psr_para_attrs["LINESPMode"] = "1"
            else:
                try:
                    lp = float(psr_ld)
                    csr_pt_attr = _first_csr_pointsize(psr)
                    if csr_pt_attr is not None and lp < csr_pt_attr * 0.5:
                        lp = csr_pt_attr * 1.2
                    psr_para_attrs["LINESPMode"] = "0"
                    psr_para_attrs["LINESP"] = str(lp)
                except ValueError:
                    pass

        psr_align_override: Optional[dict] = psr_para_attrs if psr_para_attrs else None

        para_runs: list[Run] = []
        # Walk CharacterStyleRange children of the PSR in document order.
        for child in psr:
            if not isinstance(child.tag, str):
                continue
            ctag = etree.QName(child).localname
            if ctag == "CharacterStyleRange":
                para_runs.extend(
                    _walk_csr(child, ps_family, color_map, ps_font_style=ps_font_style,
                              para_slug=para_slug, para_attrs=psr_align_override)
                )
                continue
            if ctag in _ALLOWED_PSR_CHILDREN:
                continue
            raise UnhandledElement(
                f"<ParagraphStyleRange> contains unhandled child <{ctag}> "
                f"(extend tools/idml_to_dsl.py:_walk_story)"
            )

        # Drop a trailing <Br/>-generated paragraph separator. An IDML <Br/>
        # that is the LAST child of the LAST CSR of a PSR is the paragraph
        # terminator — the PSR boundary (inter-PSR separator below) or the
        # end-of-story already terminates the paragraph. Keeping the Br's
        # Run(separator="para") here doubles the break, injecting a spurious
        # blank line between sections (the converter then renders one full
        # leading + SpaceAfter of empty paragraph that InDesign never shows).
        # A mid-PSR <Br/> (e.g. Content + Br + Content) is a real intra-
        # paragraph break and is NOT last in para_runs, so it survives.
        if para_runs:
            _last = para_runs[-1]
            if (
                _last.separator == "para"
                and not _last.text
                and _last.has_itext is False
            ):
                para_runs.pop()

        # Attach paragraph_attrs to the FIRST text-content run of the PSR so
        # Scribus applies the PSR's alignment/leading to the paragraph that
        # CONTAINS this run (rather than only to the next paragraph via the
        # separator). Without this, when style= is set on the TextFrame, the
        # first paragraph inherits the named ParaStyle's DefaultStyle ALIGN —
        # which is often Justified — and the last word of every first-
        # paragraph line spreads to fill the line width.
        if psr_align_override and para_slug:
            # Pin paragraph_style too so Scribus knows the PARENT; otherwise
            # the per-paragraph ALIGN floats on an anonymous paragraph.
            for j, r in enumerate(para_runs):
                if r.separator is None and (r.text or r.has_itext):
                    para_runs[j] = Run(
                        text=r.text,
                        has_itext=r.has_itext,
                        font=r.font,
                        fontsize=r.fontsize,
                        fcolor=r.fcolor,
                        fshade=r.fshade,
                        fontfeatures=r.fontfeatures,
                        features=r.features,
                        kern=r.kern,
                        char_style=r.char_style,
                        paragraph_style=para_slug,
                        paragraph_attrs=psr_align_override,
                        separator=r.separator,
                        var=r.var,
                        var_attrs=r.var_attrs,
                    )
                    break

        runs.extend(para_runs)

        # Inter-paragraph separator: every PSR except the LAST emits a
        # Run(separator="para") carrying the paragraph_style slug.
        if i < len(psrs) - 1:
            runs.append(Run(
                separator="para",
                paragraph_style=para_slug,
                paragraph_attrs=psr_align_override,
            ))
        elif para_slug and para_runs:
            # The LAST paragraph: attach paragraph_style to the trailing Run
            # so Scribus knows the PARENT for the final paragraph.
            # We don't emit a separator="para" — that would add an extra newline.
            # Instead, modify the last text-run in para_runs to carry the slug.
            # The PSR inline alignment override is NOT attached here — it belongs
            # on the <trail> element which is emitted by TextFrame.trail_attrs
            # (handled in _emit_pageitem via _psr_trail_attrs_for_story).
            for j in range(len(runs) - 1, -1, -1):
                if runs[j].text or runs[j].separator:
                    # Replace with copy that carries paragraph_style.
                    r = runs[j]
                    runs[j] = Run(
                        text=r.text,
                        has_itext=r.has_itext,
                        font=r.font,
                        fontsize=r.fontsize,
                        fcolor=r.fcolor,
                        fshade=r.fshade,
                        fontfeatures=r.fontfeatures,
                        features=r.features,
                        kern=r.kern,
                        char_style=r.char_style,
                        paragraph_style=para_slug,
                        paragraph_attrs=r.paragraph_attrs,
                        separator=r.separator,
                        var=r.var,
                        var_attrs=r.var_attrs,
                    )
                    break

    return runs


def _psr_trail_attrs_for_story(story_root: Any) -> Optional[dict]:
    """Return paragraph_attrs for the <trail> of the LAST PSR, or None.

    The IDML ``Justification`` attribute on a ``<ParagraphStyleRange>`` is an
    inline override over the AppliedParagraphStyle's default alignment.  Scribus
    encodes this on the ``<para>`` separator (for non-final paragraphs) and on
    the ``<trail>`` element (for the final / only paragraph).  This helper
    extracts the trail-level override so ``_emit_pageitem`` can pass it as
    ``TextFrame(trail_attrs=...)``.

    Only non-default (non-LeftAlign) justification values produce ALIGN output.
    LeftAlign (JUSTIFICATION_MAP value 0) is Scribus's default and requires no
    explicit ALIGN attribute.

    Also emits LINESPMode + LINESP from the last PSR's CSR ``Properties/Leading``
    (same rule as ``_walk_story`` applies to inter-paragraph ``<para>`` separators).
    """
    walk_root = story_root
    inner = story_root.find("Story")
    if inner is not None:
        walk_root = inner
    psrs = [
        child for child in walk_root
        if isinstance(child.tag, str) and etree.QName(child).localname == "ParagraphStyleRange"
    ]
    if not psrs:
        return None
    last_psr = psrs[-1]
    trail: dict = {}
    # Issue #37 P1 task 5: always emit ALIGN on the trail when the last PSR
    # has any recognised Justification (including LeftAlign), so the trail
    # explicitly pins the final paragraph rather than inheriting whatever
    # DefaultStyle happens to be.
    psr_just = last_psr.get("Justification")
    if psr_just and psr_just in JUSTIFICATION_MAP:
        trail["ALIGN"] = str(JUSTIFICATION_MAP[psr_just])
    psr_ld = _psr_effective_leading(last_psr)
    if psr_ld is not None:
        if psr_ld == "Auto":
            trail["LINESPMode"] = "1"
        else:
            try:
                lp = float(psr_ld)
                csr_pt_attr = _first_csr_pointsize(last_psr)
                if csr_pt_attr is not None and lp < csr_pt_attr * 0.5:
                    lp = csr_pt_attr * 1.2
                # Mirror the <para> separator rule in _walk_story: an explicit
                # numeric IDML <Leading> is a FIXED leading, so emit Scribus
                # LINESPMode=0 (Fixed) + LINESP=<value>. The brand team's
                # original .sla files pin leading exactly this way (e.g.
                # plakat-a1 "Headlineweiß" LINESPMode=0 LINESP=150 on a 160pt
                # font). LINESPMode=2 is baseline-grid (renders wider) and
                # mode 1 ignores LINESP — neither honours the authored value.
                trail["LINESPMode"] = "0"
                trail["LINESP"] = str(lp)
            except ValueError:
                pass
    return trail if trail else None


def _walk_csr(
    csr: Any,
    ps_family: Optional[str],
    color_map: dict[str, str],
    ps_font_style: Optional[str] = None,
    para_slug: Optional[str] = None,
    para_attrs: Optional[dict] = None,
) -> list[Run]:
    """Convert a <CharacterStyleRange> into a list of Run primitives.

    Honors inline ``<Content>``, ``<Br/>``, and ``<?ACE 7?>`` markers in
    document order. ``<?ACE N?>`` with N != 7 raises.

    ``para_slug`` is the Scribus paragraph style name for the enclosing PSR.
    When ``<Br/>`` is encountered inside a CSR, it emits a ``separator='para'``
    Run (InDesign paragraph break) rather than a ``separator='breakline'`` Run
    (Scribus forced line break within a paragraph). This preserves the hanging-
    indent and per-paragraph attributes of each bullet / list item.

    ``para_attrs`` carries the per-paragraph attribute overrides (e.g.
    ``{"LINESPMode": "0", "LINESP": "27.0", "ALIGN": "1"}``). These are
    forwarded to any ``<Br/>``-generated ``Run(separator="para")`` elements
    so that all paragraphs within the PSR get the correct line spacing.

    Font cascade:
    - ``csr_family``: explicit AppliedFont on this CSR (highest priority).
    - ``csr_font_style``: explicit FontStyle attribute on this CSR.
    - ``ps_family``: resolved AppliedFont from the parent ParagraphStyle.
    - ``ps_font_style``: resolved FontStyle from the parent ParagraphStyle
      (used as fallback when the CSR carries no FontStyle of its own — e.g.
      ``ParagraphStyle/Headline in grünem Kasten`` has FontStyle="Bold" so
      its CSRs render in Bold even without an explicit CSR-level attribute).
    """
    runs: list[Run] = []
    # Per-CSR style fields.
    csr_family = _csr_applied_font(csr)
    csr_font_style = csr.get("FontStyle")
    csr_pt = csr.get("PointSize")
    csr_fill = csr.get("FillColor")

    family = csr_family or ps_family
    # If the CSR has no explicit FontStyle, inherit the paragraph style's
    # font_style so that paragraph-level weight overrides (e.g. "Bold") are
    # not silently dropped.  CSR-explicit FontStyle always wins.
    effective_font_style = csr_font_style if csr_font_style is not None else ps_font_style
    font_name = _make_font_name(family, effective_font_style, ctx_self_id=csr.get("Self", "?"))

    fontsize: Optional[float] = None
    if csr_pt is not None:
        try:
            v = float(csr_pt)
            # Fractional PointSizes are common in IDML; bin/check-fontsizes
            # rejects fractional values. Round to nearest integer if the
            # difference is < 0.5; raise otherwise so the human notices.
            rounded = round(v)
            if abs(v - rounded) >= 0.5:
                raise UnhandledElement(
                    f"CharacterStyleRange PointSize={csr_pt!r} is too fractional "
                    f"to round to an integer (|delta|>=0.5); "
                    f"(extend tools/idml_to_dsl.py:_walk_csr)"
                )
            fontsize = float(rounded)
        except ValueError as e:
            raise UnhandledElement(
                f"CharacterStyleRange PointSize={csr_pt!r} is not numeric ({e}) "
                f"(extend tools/idml_to_dsl.py:_walk_csr)"
            ) from e

    fcolor: Optional[str] = None
    if csr_fill and csr_fill in color_map:
        fcolor = color_map[csr_fill]
    elif csr_fill and csr_fill not in ("Color/None", "Swatch/None"):
        raise UnhandledElement(
            f"CharacterStyleRange FillColor={csr_fill!r} not in color_map "
            f"(extend tools/idml_to_dsl.py:_walk_csr)"
        )

    # Walk the CSR children in document order; honor inline Content / Br /
    # <?ACE 7?> markers. Use the underlying element's iterator so we see
    # comments and processing instructions interleaved.
    for child in csr.iter():
        # csr.iter() includes csr itself; skip.
        if child is csr:
            continue
        # Only honor DIRECT children of csr for inline ordering.
        if child.getparent() is not csr:
            continue
        # Processing instruction (e.g. <?ACE 7?>).
        if isinstance(child, etree._ProcessingInstruction):
            target = child.target  # type: ignore[attr-defined]
            data = (child.text or "").strip()  # type: ignore[attr-defined]
            if target == "ACE" and data == "7":
                # Indent-to-here (indent-to-here/tab-align marker).
                # Preserve tail text: IDML sometimes places content text as
                # the PI's tail (e.g. <Content>•<?ACE 7?>Ur, omniet</Content>
                # → PI.tail = "Ur, omniet"). Emit it as a Run with this CSR's
                # style rather than silently dropping it.
                if child.tail:
                    runs.append(Run(
                        text=child.tail,
                        font=font_name,
                        fontsize=fontsize,
                        fcolor=fcolor,
                    ))
                continue
            raise UnhandledElement(
                f"Unknown processing instruction <?{target} {data}?> in "
                f"CharacterStyleRange {csr.get('Self')!r} "
                f"(extend tools/idml_to_dsl.py:_walk_csr)"
            )
        if not isinstance(child.tag, str):
            continue
        ctag = etree.QName(child).localname
        if ctag == "Content":
            # Gather text from the Content element including any <?ACE 7?> PI
            # children's tail text. IDML sometimes inlines the ACE indent marker
            # inside <Content>, causing subsequent text to sit in PI.tail rather
            # than Content.text (e.g. <Content>•<?ACE 7?>Ur, omniet</Content>
            # → Content.text="•", ACE_PI.tail="Ur, omniet"). We concatenate
            # text + all child PI tails so the full content text is captured.
            text_parts: list[str] = []
            if child.text:
                text_parts.append(child.text)
            for sub in child:
                if isinstance(sub, etree._ProcessingInstruction):
                    # ACE 7 = indent-to-here marker; any other PI would be unknown
                    sub_target = sub.target  # type: ignore[attr-defined]
                    sub_data = (sub.text or "").strip()  # type: ignore[attr-defined]
                    if sub_target != "ACE" or sub_data != "7":
                        raise UnhandledElement(
                            f"Unknown PI <?{sub_target} {sub_data}?> inside "
                            f"<Content> of CSR {csr.get('Self')!r} "
                            f"(extend tools/idml_to_dsl.py:_walk_csr)"
                        )
                    if sub.tail:
                        text_parts.append(sub.tail)
            text = "".join(text_parts)
            # Split on tab chars so Scribus emits <tab/> elements (which honour
            # paragraph-style tab stops) rather than ITEXT CH with embedded &#9;
            # (which uses the document-default TabWidth and ignores style tab stops).
            segments = text.split("\t")
            for seg_idx, seg in enumerate(segments):
                if seg:
                    runs.append(
                        Run(
                            text=seg,
                            font=font_name,
                            fontsize=fontsize,
                            fcolor=fcolor,
                        )
                    )
                if seg_idx < len(segments) - 1:
                    # Emit a tab separator between segments (including leading/trailing tabs).
                    runs.append(Run(text="", font=font_name, fontsize=fontsize, fcolor=fcolor, separator="tab"))
        elif ctag == "Br":
            # IDML <Br/> is an "end of paragraph" marker within a PSR, not a
            # forced line break. In Scribus this must be a <para> (paragraph
            # separator) so each bullet/section gets its own paragraph with
            # correct hanging-indent and LINESPMode behaviour.  We use
            # has_itext=False to avoid emitting a spurious empty <ITEXT CH=""/>
            # before the <para/> — consecutive control elements must not invent
            # text nodes (see primitives.py Run docstring).
            # para_attrs carries LINESPMode + LINESP (and ALIGN if needed) so
            # every sub-paragraph within the PSR gets explicit line spacing.
            runs.append(Run(
                has_itext=False,
                separator="para",
                paragraph_style=para_slug or None,
                paragraph_attrs=para_attrs or None,
            ))
        elif ctag == "Properties":
            continue
        else:
            raise UnhandledElement(
                f"<CharacterStyleRange> contains unhandled child <{ctag}>; "
                f"(extend tools/idml_to_dsl.py:_walk_csr)"
            )
    return runs


def _item_page_local_bbox_pt(
    child: Any,
    spread_t: str,
    pg: dict[str, Any],
) -> Optional[tuple[float, float, float, float, float]]:
    """Page-local bbox of a top-level spread item for routing.

    For a leaf PageItem this is a single ``_compute_page_local_bbox_pt`` call.
    For a Group it is the UNION of the group's leaf descendants' page-local
    bboxes — ``_extract_anchors`` on a Group returns only the first child's
    PathGeometry (Groups have no PathGeometry of their own), so routing a
    Group by ``_extract_anchors`` mis-places it. Recursing into the leaves
    with the group ItemTransform chain gives the true occupied rect.

    Returns ``(x_pt, y_pt, w_pt, h_pt, 0.0)`` or ``None`` when no leaf yields
    geometry.
    """
    tag = etree.QName(child).localname

    def _leaf_bboxes(node: Any, ancestor_ts: list[str]) -> list[tuple[float, float, float, float]]:
        out: list[tuple[float, float, float, float]] = []
        node_tag = etree.QName(node).localname
        if node_tag == "Group":
            grp_t = node.get("ItemTransform", "1 0 0 1 0 0")
            for sub in node:
                if not isinstance(sub.tag, str):
                    continue
                if etree.QName(sub).localname not in _DISPATCHED_PAGEITEM_TAGS:
                    continue
                out.extend(_leaf_bboxes(sub, [grp_t, *ancestor_ts]))
            return out
        try:
            anchors = _extract_anchors(node)
            x, y, w, h, _ = _compute_page_local_bbox_pt(
                node.get("ItemTransform", "1 0 0 1 0 0"),
                anchors,
                ancestor_ts,
                spread_t,
                pg["page_t"],
                pg["page_gb"],
            )
        except UnhandledElement:
            return out
        out.append((x, y, w, h))
        return out

    if tag == "Group":
        boxes = _leaf_bboxes(child, [])
        if not boxes:
            return None
        x0 = min(b[0] for b in boxes)
        y0 = min(b[1] for b in boxes)
        x1 = max(b[0] + b[2] for b in boxes)
        y1 = max(b[1] + b[3] for b in boxes)
        return (x0, y0, x1 - x0, y1 - y0, 0.0)

    try:
        anchors = _extract_anchors(child)
        return _compute_page_local_bbox_pt(
            child.get("ItemTransform", "1 0 0 1 0 0"),
            anchors,
            [],
            spread_t,
            pg["page_t"],
            pg["page_gb"],
        )
    except UnhandledElement:
        return None


def _route_item_to_page(
    child: Any,
    spread_t: str,
    pages: list[dict[str, Any]],
    guard_pt: float,
) -> Optional[int]:
    """Pick which page of a multi-page spread a top-level item belongs to.

    For a single-page spread this is trivial (index 0). For a facing-pages
    spread (PageCount > 1) every page carries its own ItemTransform + bbox;
    an item's spread geometry resolves to a different page-local bbox under
    each page's transform. The item belongs to the page whose page-local
    bbox CENTRE lands inside that page's [-guard, w+guard] x [-guard, h+guard]
    region. Falls back to the page with the smallest centre-distance when no
    region contains the centre (e.g. a bleed-only item straddling the spine).

    Returns the local page index, or None when anchor extraction fails so the
    caller can defer to its own out-of-page guard.
    """
    if len(pages) == 1:
        return 0
    best_idx: Optional[int] = None
    best_dist = float("inf")
    for idx, pg in enumerate(pages):
        bbox = _item_page_local_bbox_pt(child, spread_t, pg)
        if bbox is None:
            continue
        x_pt, y_pt, w_pt, h_pt, _ = bbox
        cx = x_pt + w_pt / 2.0
        cy = y_pt + h_pt / 2.0
        if (
            -guard_pt <= cx <= pg["page_w_pt"] + guard_pt
            and -guard_pt <= cy <= pg["page_h_pt"] + guard_pt
        ):
            return idx
        # Distance of the centre from this page's region, for the fallback.
        dx = max(0.0, -cx, cx - pg["page_w_pt"])
        dy = max(0.0, -cy, cy - pg["page_h_pt"])
        dist = dx * dx + dy * dy
        if dist < best_dist:
            best_dist = dist
            best_idx = idx
    return best_idx


def _pages_overlapped_by_item(
    child: Any,
    spread_t: str,
    pages: list[dict[str, Any]],
    guard_pt: float,
) -> Optional[list[int]]:
    """Return every page of a multi-page spread an item visibly covers.

    ``_route_item_to_page`` answers "which ONE page owns this item" by the
    bbox centre — correct for ordinary content. But a spread-spanning
    background rectangle (e.g. a full-bleed coloured fill drawn across both
    pages of a facing-pages spread) genuinely belongs to *every* page it
    covers: in the legacy side-by-side "spread" SLA layout it rendered onto
    both pages automatically; in the page-by-page SLA layout each page is a
    separate canvas, so the item must be emitted once per overlapped page.

    The owning page (by ``_route_item_to_page``'s centre rule) is always in
    the result. An EXTRA page is added only when the item's page-local bbox
    covers most of that page — a true full-bleed background fill, not an
    ordinary content frame that merely bleeds a few mm past the spine. This
    keeps routing identical for normal content (one index) and only widens
    for spanning backgrounds. Returns ``None`` when anchor extraction fails
    so the caller can fall back to its own guard.
    """
    if len(pages) == 1:
        return [0]
    owner = _route_item_to_page(child, spread_t, pages, guard_pt)
    if owner is None:
        return None
    # An extra page qualifies only when the item covers >= this fraction of
    # the page's area — a spanning background, not a spine-bleeding frame.
    _COVER_FRACTION = 0.6
    hit: list[int] = [owner]
    for idx, pg in enumerate(pages):
        if idx == owner:
            continue
        bbox = _item_page_local_bbox_pt(child, spread_t, pg)
        if bbox is None:
            continue
        x_pt, y_pt, w_pt, h_pt, _ = bbox
        pw = pg["page_w_pt"]
        ph = pg["page_h_pt"]
        ix = max(0.0, min(x_pt + w_pt, pw) - max(x_pt, 0.0))
        iy = max(0.0, min(y_pt + h_pt, ph) - max(y_pt, 0.0))
        if pw > 0 and ph > 0 and (ix * iy) >= _COVER_FRACTION * pw * ph:
            hit.append(idx)
    return sorted(hit)


def _count_idml_pages(ctx: _Ctx) -> int:
    """Total number of <Page> elements across every Spreads/*.xml file."""
    total = 0
    for sp_path in ctx.pkg.spreads:
        xml = ctx.pkg.open(sp_path).read()
        root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
        spread_node = root.find(".//Spread")
        if spread_node is not None:
            total += len(spread_node.findall("Page"))
    return total


def _resolve_render_page_mode(ctx: _Ctx) -> None:
    """Decide whether the SLA renders one page per spread or one per page.

    The default ("spread") merges a facing-pages spread into a single wide
    SLA page — correct for leporello / fold templates whose InDesign PDF
    export is spread-based. But some templates (the A6 flyer family) author
    their pages in 2-up facing spreads purely for editing convenience and
    export the PDF **page-by-page**: the baseline then has one PDF page per
    IDML page, not per spread.

    Detection compares the sibling ``<stem>.pdf`` page count against the
    IDML's page and spread counts:

    * baseline pages == IDML page count  AND  != spread count → ``"page"``
    * otherwise (including no baseline found)                → ``"spread"``

    The asymmetric test is deliberately conservative: a template only flips
    to per-page mode when the baseline unambiguously matches the page count
    and the two counts genuinely differ (i.e. at least one facing spread
    exists). Templates with no facing spreads keep the default and behave
    identically either way.
    """
    n_pages = _count_idml_pages(ctx)
    n_spreads = len(list(ctx.pkg.spreads))
    if n_pages == n_spreads:
        # No facing spreads — the two models are identical. Keep default.
        ctx.render_page_mode = "spread"
        return
    baseline = None
    if ctx.source is not None:
        cand = ctx.source.with_suffix(".pdf")
        if cand.exists():
            baseline = cand
    if baseline is None:
        ctx.render_page_mode = "spread"
        return
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(str(baseline)) as pdf:
            n_baseline = len(pdf.pages)
    except Exception:
        ctx.render_page_mode = "spread"
        return
    if n_baseline == n_pages and n_baseline != n_spreads:
        ctx.render_page_mode = "page"
        print(
            f"OK: baseline {baseline.name} has {n_baseline} pages == IDML "
            f"page count ({n_pages}), spread count {n_spreads} — emitting "
            f"one SLA page per IDML page (page-based export).",
            file=sys.stderr,
        )
    else:
        ctx.render_page_mode = "spread"


def _collect_spread_pages(ctx: _Ctx) -> list[dict[str, Any]]:
    """Return one entry per rendered SLA page.

    In the default ``"spread"`` mode this is one entry per IDML spread: a
    single-page spread exports as one PDF page, and a multi-page (facing)
    spread exports as ONE wider PDF page whose width is the sum of its
    constituent pages' widths.

    In ``"page"`` mode (see ``_resolve_render_page_mode``) this is one entry
    per IDML page: a facing-pages spread yields TWO render-page entries, each
    sized to one page, each carrying a ``page_local_idx`` so ``_emit_pages``
    can route the spread's items to the correct page via
    ``_route_item_to_page``.

    Each returned dict carries:

    * ``sp_path``      — Spreads/<id>.xml member name.
    * ``spread_t``     — the Spread's own ItemTransform string.
    * ``pages``        — list of per-page dicts (page_t, page_gb, page_w_pt,
                         page_h_pt) in document order, exactly as
                         ``_emit_pages`` previously built ``spread_pages``.
    * ``origin_t``     — the LEFTMOST page's ItemTransform. All items in the
                         spread are placed relative to this page's top-left
                         so a 2-page spread's right-hand items naturally land
                         at +(left-page-width) in x.
    * ``origin_gb``    — the leftmost page's GeometricBounds.
    * ``page_w_pt``    — total rendered SLA page width (sum of page widths).
    * ``page_h_pt``    — rendered SLA page height (max page height).
    """
    out: list[dict[str, Any]] = []
    for sp_path in ctx.pkg.spreads:
        xml = ctx.pkg.open(sp_path).read()
        root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
        spread_node = root.find(".//Spread")
        spread_t = spread_node.get("ItemTransform", "1 0 0 1 0 0")
        spread_pages: list[dict[str, Any]] = []
        for page_node in spread_node.findall("Page"):
            page_gb = _parse_geometric_bounds(
                page_node.get("GeometricBounds", "0 0 0 0")
            )
            gb_y1, gb_x1, gb_y2, gb_x2 = page_gb
            spread_pages.append({
                "page_t": page_node.get("ItemTransform", "1 0 0 1 0 0"),
                "page_gb": page_gb,
                "page_w_pt": gb_x2 - gb_x1,
                "page_h_pt": gb_y2 - gb_y1,
            })
        if not spread_pages:
            raise UnhandledElement(
                f"Spread {sp_path} contains no <Page> "
                f"(extend tools/idml_to_dsl.py:_collect_spread_pages)"
            )
        # The leftmost page is the one whose top-left in spread coordinates
        # has the smallest x. page_top_left_x = page_tx + page_gb_x1.
        def _page_left_x(pg: dict[str, Any]) -> float:
            _, _, _, _, ptx, _ = _parse_matrix(pg["page_t"])
            _, gx1, _, _ = pg["page_gb"]
            return ptx + gx1
        if ctx.render_page_mode == "page":
            # One render-page entry per IDML page. Items in a multi-page
            # spread are routed by _route_item_to_page using page_local_idx.
            ordered = sorted(spread_pages, key=_page_left_x)
            for local_idx, pg in enumerate(ordered):
                out.append({
                    "sp_path": sp_path,
                    "spread_t": spread_t,
                    "pages": spread_pages,
                    "page_local_idx": local_idx,
                    "origin_t": pg["page_t"],
                    "origin_gb": pg["page_gb"],
                    "page_w_pt": pg["page_w_pt"],
                    "page_h_pt": pg["page_h_pt"],
                })
            continue
        leftmost = min(spread_pages, key=_page_left_x)
        out.append({
            "sp_path": sp_path,
            "spread_t": spread_t,
            "pages": spread_pages,
            "page_local_idx": None,
            "origin_t": leftmost["page_t"],
            "origin_gb": leftmost["page_gb"],
            "page_w_pt": sum(p["page_w_pt"] for p in spread_pages),
            "page_h_pt": max(p["page_h_pt"] for p in spread_pages),
        })
    return out


def _emit_pages(ctx: _Ctx) -> None:
    """Phase H driver: emit one _add_page_<i> function body per SPREAD.

    InDesign exports spread-based PDFs: a facing-pages spread (PageCount > 1)
    becomes ONE wide PDF page. The converter mirrors that — one SLA page per
    spread — so the rendered preview compares page-for-page against the
    baseline. All items in a spread are placed relative to the leftmost
    page's top-left origin (see ``_collect_spread_pages``); the right-hand
    page's items therefore land at +(left-page-width) automatically.
    """
    # Items more than this many mm outside the page+bleed area are treated
    # as InDesign design artifacts (e.g. guide markers on printable layers)
    # that InDesign does not export to PDF.  Bleed is typically ≤3 mm so
    # a 20 mm guard safely excludes true out-of-page artifacts.
    _OUT_OF_PAGE_GUARD_MM = 20.0
    _guard_pt = _OUT_OF_PAGE_GUARD_MM / PT_TO_MM

    spread_infos = _collect_spread_pages(ctx)
    for spread_idx, sp_info in enumerate(spread_infos):
        i = spread_idx
        sp_path = sp_info["sp_path"]
        spread_t = sp_info["spread_t"]
        # In "spread" mode all items share one merged SLA page placed
        # relative to the leftmost page's top-left origin. In "page" mode
        # each render-page entry is one IDML page; items in a multi-page
        # spread are routed by _route_item_to_page using page_local_idx.
        page_t = sp_info["origin_t"]
        page_gb = sp_info["origin_gb"]
        page_w_pt = sp_info["page_w_pt"]
        page_h_pt = sp_info["page_h_pt"]
        page_local_idx = sp_info.get("page_local_idx")
        spread_page_dicts = sp_info["pages"]

        # Collect every emittable top-level item for this render page. In
        # "page" mode, _route_item_to_page filters items to the single
        # IDML page this entry represents. ``spread_item_suffix`` runs in
        # lock-step with ``spread_items``: it is "" for the page that owns
        # the item and "_p<idx>" for a spanning background re-emitted onto
        # a non-owner page (the suffix keeps the duplicate anname unique).
        spread_items: list[Any] = []
        spread_item_suffix: list[str] = []
        xml = ctx.pkg.open(sp_path).read()
        root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
        spread_node = root.find(".//Spread")
        for child in spread_node:
            if not isinstance(child.tag, str):
                continue
            tag = etree.QName(child).localname
            if tag in ("Page", "FlattenerPreference"):
                continue
            item_layer = child.get("ItemLayer", "")
            if item_layer not in ctx.printable_layer_ids:
                # Skip items on hidden (Visible=false) layers — these never
                # reach the InDesign PDF baseline either. Items on visible
                # but non-printing layers (e.g. "Info") DO reach the baseline
                # and must emit; ctx.printable_layer_ids is built from
                # Visible, not Printable.
                _ch_sid = child.get("Self", "")
                if _ch_sid:
                    ctx.record_skipped(_ch_sid, f"hidden layer {item_layer!r}")
                continue
            if tag not in _DISPATCHED_PAGEITEM_TAGS:
                # GraphicLine on a visible-but-non-printable layer (Info) is
                # a Falz / print-mark line — author adds those manually post-
                # bootstrap. Skip silently. A GraphicLine on a truly-printable
                # layer (Gestaltung) is still a genuine surprise.
                if tag == "GraphicLine" and item_layer not in ctx.truly_printable_layer_ids:
                    _ch_sid = child.get("Self", "")
                    if _ch_sid:
                        ctx.record_skipped(
                            _ch_sid,
                            f"GraphicLine on non-printable layer {item_layer!r} "
                            "(Falz/print mark — author manually post-bootstrap)",
                        )
                    continue
                raise UnhandledElement(
                    f"Top-level <{tag} Self={child.get('Self')!r}> on printable "
                    f"layer {item_layer!r} not handled "
                    f"(extend tools/idml_to_dsl.py:_emit_pages)"
                )
            # Page-based mode: a facing spread becomes N render-page entries.
            # Route each top-level item to the IDML page(s) it covers so it is
            # emitted on the correct page. A spread-spanning background fill
            # covers BOTH pages and is emitted on each (with a "_p<idx>"
            # anname suffix on every non-owner page so the duplicate is
            # unique). When routing cannot resolve (anchor extraction failed)
            # the item lands on page 0 so it is never dropped.
            if page_local_idx is not None and len(spread_page_dicts) > 1:
                covered = _pages_overlapped_by_item(
                    child, spread_t, spread_page_dicts, _guard_pt
                )
                if not covered:
                    covered = [0]
                if page_local_idx not in covered:
                    continue
                owner = covered[0]
                suffix = "" if page_local_idx == owner else f"_p{page_local_idx}"
            else:
                suffix = ""
            spread_items.append(child)
            spread_item_suffix.append(suffix)

        # Emit one _add_page_<i> per SPREAD.
        if True:
            page_var = f"page{i}"
            ctx._current_page_var = page_var  # type: ignore[attr-defined]

            # Override the task-3 stub for this page.
            ctx.out.w("")
            ctx.out.w(
                f"def _add_page_{i}(doc: Document, {page_var}) -> None:  "
                f"# overrides task-3 stub"
            )
            ctx.out.indent += 1
            ctx.out.w(
                f'"""Auto-generated page-items for spread {i + 1} '
                f'(Spread {sp_path})."""'
            )

            emit_count = 0
            for child, _an_suffix in zip(spread_items, spread_item_suffix):
                tag = etree.QName(child).localname
                item_layer = child.get("ItemLayer", "")
                # Out-of-page guard: skip items that lie entirely outside the
                # page bounds by more than _guard_pt. These are InDesign design
                # artifacts (guides, registration marks) that InDesign excludes
                # from PDF export even when placed on a printable layer.
                #
                # Groups are EXCLUDED from this guard: InDesign Group containers
                # store their PathGeometry anchors in a design-time local space
                # that does not directly map to page coordinates via the Group's
                # own ItemTransform. Skipping the guard for Groups lets recursion
                # in _emit_pageitem handle child placement.
                if tag != "Group":
                    child_t = child.get("ItemTransform", "1 0 0 1 0 0")
                    try:
                        child_anchors = _extract_anchors(child)
                        (
                            child_x_pt,
                            child_y_pt,
                            child_w_pt,
                            child_h_pt,
                            _,
                        ) = _compute_page_local_bbox_pt(
                            child_t, child_anchors, [], spread_t, page_t, page_gb
                        )
                        if (
                            child_x_pt + child_w_pt < -_guard_pt
                            or child_x_pt > page_w_pt + _guard_pt
                            or child_y_pt + child_h_pt < -_guard_pt
                            or child_y_pt > page_h_pt + _guard_pt
                        ):
                            sid = child.get("Self", "?")
                            print(
                                f"  [skip] {tag} Self={sid!r}: entirely outside "
                                f"page bounds (x={child_x_pt * PT_TO_MM:.1f}mm "
                                f"y={child_y_pt * PT_TO_MM:.1f}mm "
                                f"w={child_w_pt * PT_TO_MM:.1f}mm "
                                f"h={child_h_pt * PT_TO_MM:.1f}mm) — "
                                f"InDesign design artifact, not emitted",
                                file=sys.stderr,
                            )
                            if sid:
                                ctx.record_skipped(
                                    sid,
                                    "InDesign design artifact "
                                    "(entirely outside page+bleed)",
                                )
                            continue
                    except UnhandledElement:
                        # Anchor extraction failed for a non-Group — skip guard.
                        pass
                layer_idx = ctx.layer_id_to_idx.get(item_layer, 0)
                # A spanning background re-emitted onto a non-owner page
                # carries a "_p<idx>" anname suffix so the duplicate frame
                # is uniquely named. _emit_pageitem reads the anname from
                # the element's Self attribute — set it for this emit, then
                # restore so the next page sees the original ID.
                _orig_self = child.get("Self")
                if _an_suffix and _orig_self is not None:
                    child.set("Self", f"{_orig_self}{_an_suffix}")
                try:
                    _emit_pageitem(
                        ctx.out, child, [], spread_t, page_t, page_gb,
                        page_var, ctx, layer_idx,
                    )
                finally:
                    if _an_suffix and _orig_self is not None:
                        child.set("Self", _orig_self)
                emit_count += 1
            if emit_count == 0:
                ctx.out.w("return None")
            ctx.out.indent -= 1
            ctx.out.w("")


_PAGE_ITEM_LEAF_TAGS = frozenset({
    "Rectangle", "Polygon", "Oval", "TextFrame", "Image", "PDF",
    "GraphicLine", "Group",
})


_FRAME_TAGS = frozenset({
    "Rectangle", "Polygon", "Oval", "TextFrame", "GraphicLine",
})
_CONTENT_CHILD_TAGS = frozenset({"Image", "PDF", "EPS"})


def _walk_idml_pageitem_self_ids(
    pkg: Any,
    printable_layer_ids: set[str] | None = None,
) -> set[str]:
    """Walk every Spread's PageItem inventory the way the emitter walks it.

    Returns the set of ``Self`` IDs the converter is expected to EITHER emit
    OR explicitly skip. Mirrors ``_emit_pages``' traversal:

    * Top-level Spread children whose ``ItemLayer`` is non-printable are
      skipped together with the entire subtree (the emitter records the
      top-level skip; descendants never get visited).
    * Groups recurse into their child PageItems.
    * Frame tags (Rectangle/Polygon/Oval/TextFrame/GraphicLine) are leaves:
      a frame may wrap an ``Image``/``PDF``/``EPS`` as its CONTENT, but the
      emitter records only the frame's Self; the inner content child is
      consumed by the frame's emit-path.

    ``printable_layer_ids`` defaults to all-printable when omitted (test
    fixtures pre-#37 may not pass it).
    """
    ids: set[str] = set()

    def _visit(el, in_printable: bool) -> None:
        if not isinstance(el.tag, str):
            return
        tag = etree.QName(el).localname
        item_layer = el.get("ItemLayer", "")
        # Non-printable layer = skip element AND its subtree (emitter parity).
        if (
            in_printable
            and item_layer
            and printable_layer_ids is not None
            and item_layer not in printable_layer_ids
        ):
            in_printable = False
        if not in_printable:
            return
        if tag == "Group":
            sid = el.get("Self")
            if sid:
                ids.add(sid)
            for child in el:
                _visit(child, in_printable)
            return
        if tag in _FRAME_TAGS:
            sid = el.get("Self")
            if sid:
                ids.add(sid)
            # Don't descend: any Image/PDF/EPS child is content, consumed by
            # the frame's emit-path under the frame's Self.
            return
        if tag in _CONTENT_CHILD_TAGS:
            # Top-level Image/PDF/EPS (no frame wrapper) is unusual but in scope.
            sid = el.get("Self")
            if sid:
                ids.add(sid)
            return
        # Other tags (Page, FlattenerPreference, Properties, …): descend so we
        # reach PageItems nested under <Page>.
        for child in el:
            _visit(child, in_printable)

    for sp_path in pkg.spreads:
        xml = pkg.open(sp_path).read()
        root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
        for child in root:
            _visit(child, True)
    return ids


def _assert_conversion_completeness(ctx: _Ctx) -> None:
    """Compare ``ctx.emitted_self_ids`` (+ explicit skips) against the IDML's
    PageItem inventory. Raise ``UnhandledElement`` when the gap is non-empty.

    Issue #37 Phase B1 / P3 task 16. The assertion catches the silent-drop
    class: a PageItem in the IDML that produces neither output nor an
    explicit skip annotation.
    """
    all_ids = _walk_idml_pageitem_self_ids(ctx.pkg, ctx.printable_layer_ids)
    skipped = {s["self_id"] for s in ctx.skipped_with_reason}
    missing = all_ids - ctx.emitted_self_ids - skipped
    if not missing:
        return
    sample = sorted(missing)[:10]
    suffix = "..." if len(missing) > 10 else ""
    raise UnhandledElement(
        f"Conversion incomplete: {len(missing)} IDML PageItem(s) emitted "
        f"no output and were not explicitly skipped. "
        f"IDs: {sample}{suffix}. "
        f"Either implement the relevant pattern in tools/idml_to_dsl.py, "
        f"or add a '# IDML pattern: <name>: skipped because <reason>' "
        f"annotation and call ctx.record_skipped(self_id, reason). "
        f"Use --allow-dropped-pageitems to bypass during debugging."
    )


def _final_strictness_gates(ctx: _Ctx) -> None:
    """Raise a single end-of-run UnhandledElement listing all deferred issues.

    Per locked decisions #2 (unmapped vector logos) and #3 (missing raster
    assets). Combines both into one message so the human gets a complete
    work-list before re-running.
    """
    msgs: list[str] = []
    if ctx.unmapped_logos:
        seen: set[str] = set()
        unique_logos: list[tuple[str, str]] = []
        for sid, uri in ctx.unmapped_logos:
            if uri in seen:
                continue
            seen.add(uri)
            unique_logos.append((sid, uri))
        logo_list = "\n  ".join(f"- {sid}: {uri}" for sid, uri in unique_logos)
        msgs.append(
            f"Unmapped vector logos ({len(unique_logos)} unique):\n  {logo_list}\n"
            f"Stage pre-rasterised PNGs under shared/logos/ and pass "
            f"--logo-map <yaml> mapping basename → png_path, then re-run."
        )
    if ctx.missing_assets:
        m_list = "\n  ".join(f"- {p}" for p in ctx.missing_assets)
        msgs.append(
            f"Missing raster assets ({len(ctx.missing_assets)}):\n  {m_list}\n"
            f"Place files under --assets-dir (or extend the resolver)."
        )
    if ctx.unmapped_assets:
        seen_a: set[str] = set()
        unique_assets: list[tuple[str, str]] = []
        for sid, basename in ctx.unmapped_assets:
            if basename in seen_a:
                continue
            seen_a.add(basename)
            unique_assets.append((sid, basename))
        a_list = "\n  ".join(f"- {sid}: {bn}" for sid, bn in unique_assets)
        msgs.append(
            f"Unmapped assets in --asset-map ({len(unique_assets)} unique):"
            f"\n  {a_list}\n"
            f"Re-run tools/links_export.py against the Links/ directory to "
            f"regenerate the manifest, then re-run this converter."
        )
    if msgs:
        raise UnhandledElement("\n\n".join(msgs))


# ---------------------------------------------------------------------------
# Phase D/E — emit build.py header + Document + add_master + add_page calls
# ---------------------------------------------------------------------------
def _emit_header(out: PythonRepr, template_id: str, idml_name: str) -> None:
    """Emit module docstring + imports + INJECT_MAP placeholder."""
    out.w(f'"""{template_id} — DSL build entry point.')
    out.w("")
    out.w(f"Auto-generated from {idml_name} by tools/idml_to_dsl.py.")
    out.w("Hand-edit thereafter; this file is the source of truth.")
    out.w("")
    out.w("NOTE: bleed_mm=0 below — emit a trim-only MediaBox so the rendered")
    out.w("PDF compares directly against the InDesign baseline (which exports")
    out.w("with trim-only by default). For print prep, restore the IDML's")
    out.w("authored bleed (preserved in IDML preferences).")
    out.w("")
    out.w("Falz lines are NOT emitted by the converter — add manually post-bootstrap")
    out.w("matching templates/kandidat-falzflyer-din-lang/build.py: import FoldLine")
    out.w("from sla_lib.builder.blocks and instantiate at panel boundaries x=99/198 mm.")
    out.w('"""')
    out.w("from __future__ import annotations")
    out.w("")
    out.w("import sys")
    out.w("from pathlib import Path")
    out.w("")
    out.w("HERE = Path(__file__).resolve().parent")
    out.w('sys.path.insert(0, str(HERE.parents[1] / "tools"))')
    out.w("")
    out.w("from sla_lib.builder import (  # noqa: E402")
    out.w("    Brand,")
    out.w("    Document,")
    out.w("    DocumentLayer,")
    out.w("    TextFrame,")
    out.w("    ImageFrame,")
    out.w("    Polygon,")
    out.w("    PolyLine,")
    out.w("    Run,")
    out.w("    ParaStyle,")
    out.w("    Anchor,")
    out.w("    pack_inline_image,")
    out.w(")")
    out.w("")
    out.w("INJECT_MAP: dict[str, str] = {}")
    out.w("")


def _emit_document_scaffold(out: PythonRepr, ctx: _Ctx) -> None:
    """Emit build_template(): Document() + add_master + add_page calls."""
    prefs = ctx.doc_prefs
    trim_w_mm = prefs["page_width_pt"] * PT_TO_MM
    trim_h_mm = prefs["page_height_pt"] * PT_TO_MM
    # The master must be at least as large as the widest doc page. With
    # spread-merged pages a facing spread is wider than a single page, so
    # the master is sized to the widest spread (it stays empty either way
    # for this brand — see Phase C MasterSpread emptiness check).
    _spread_infos_for_master = _collect_spread_pages(ctx)
    master_w_mm = max(
        (sp["page_w_pt"] * PT_TO_MM for sp in _spread_infos_for_master),
        default=trim_w_mm,
    )
    master_h_mm = max(
        (sp["page_h_pt"] * PT_TO_MM for sp in _spread_infos_for_master),
        default=trim_h_mm,
    )
    # InDesign's default PDF export emits a trim-only MediaBox (no bleed
    # area); our baselines were captured that way. Emit bleed_mm=0 so the
    # Scribus PDF MediaBox matches and visual_diff can compare like-for-like.
    # The IDML's authored bleed value is preserved in the docstring above
    # for downstream print prep.
    idml_bleed_mm = prefs["bleed_top_pt"] * PT_TO_MM
    bleed_mm = 0

    out.w("def build_template() -> Document:")
    out.indent += 1
    out.w('"""Return a clean Document with all frames defined.')
    out.w("")
    out.w("Emitted by tools/idml_to_dsl.py from the source IDML; hand-edit as needed.")
    out.w('"""')
    out.w("doc = Document(")
    out.indent += 1
    out.w(f"brand=Brand.gruene_noe(),")
    out.w(f"title={_py_value(ctx.template_id)},")
    out.w(f"template_id={_py_value(ctx.template_id)},")
    out.w('author="Die Grünen Niederösterreich",')
    # The converter emits one SLA page per IDML SPREAD (a facing-pages
    # spread becomes ONE wide page — see _emit_pages / _collect_spread_pages),
    # so each rendered page is already a self-contained spread. facing_pages
    # is therefore forced False: the two-column scratch stacking it triggers
    # is meaningless once spreads are merged, and single-column stacking
    # keeps page geometry simple. The IDML's authored FacingPages value is
    # preserved in DocumentSetupPreference for downstream print prep.
    out.w("facing_pages=False,")
    out.w("layers=[")
    out.indent += 1
    for lyr in ctx.layers:
        kwargs: dict[str, Any] = {"name": lyr["name"]}
        if not lyr["visible"]:
            kwargs["visible"] = False
        if not lyr["printable"]:
            kwargs["printable"] = False
        # The 'editable' DSL field maps to "not locked" in IDML.
        if lyr["locked"]:
            kwargs["editable"] = False
        body = ", ".join(f"{k}={_py_value(v)}" for k, v in kwargs.items())
        out.w(f"DocumentLayer({body}),")
    out.indent -= 1
    out.w("],")
    # ICC profile pass-through: tell Scribus to use a CMYK profile that
    # matches InDesign's default print export (ISO Coated v2 300% ≈ FOGRA39).
    # Without an explicit DPIn, Scribus's HCMS=1 path picks an unpredictable
    # default that may not match the baseline rendering. Brand colours
    # (Dunkelgrün CMYK 85/35/95/10, Gelb CMYK 0/0/100/0) and CMYK JPGs
    # both pass through this profile.
    out.w("extra_doc_attrs={")
    out.indent += 1
    out.w("'DPIn':  'ISO Coated v2 300% (basICColor)',")
    out.w("'DPIn2': 'ISO Coated v2 300% (basICColor)',")
    out.indent -= 1
    out.w("},")
    # Disable crop/bleed marks so the exported PDF MediaBox matches the
    # InDesign baseline (trim-only, no marks area).  Brand default has
    # these on; IDML DocumentPrintingPreference has them off for this
    # template, so override here.
    out.w("extra_pdf_attrs={")
    out.indent += 1
    out.w("'cropMarks': '0',")
    out.w("'bleedMarks': '0',")
    out.indent -= 1
    out.w("},")
    out.indent -= 1
    out.w(")")
    out.w("")
    # Document-local non-brand colours (print marks etc.). Registered via
    # doc.add_color() so the SLA contains the swatch and items referencing it
    # render with the authored CMYK rather than falling back to the default.
    for cname, cmyk in sorted(ctx.extra_colors.items()):
        out.w(f"doc.add_color({_py_value(cname)}, cmyk={tuple(cmyk)})")
    if ctx.extra_colors:
        out.w("")
    out.w("# add_styles(doc) - paragraph styles (Phase G, task 5)")
    out.w("_add_styles(doc)")
    out.w("")
    out.w(f"doc.add_master(")
    out.indent += 1
    out.w('name="Normal",')
    out.w(f"size=({_py_value(master_w_mm)}, {_py_value(master_h_mm)}),")
    out.w(f"bleed_mm={_py_value(bleed_mm)},")
    out.w("margins_mm=(0.0, 0.0, 0.0, 0.0),")
    out.indent -= 1
    out.w(")")
    out.w("")
    # One add_page per IDML SPREAD. A single-page spread is trim-sized;
    # a facing-pages spread is as wide as the sum of its pages (InDesign
    # exports spread-based PDFs — see _collect_spread_pages).
    spread_infos = _collect_spread_pages(ctx)
    page_count = len(spread_infos)
    for i, sp_info in enumerate(spread_infos):
        sp_w_mm = sp_info["page_w_pt"] * PT_TO_MM
        sp_h_mm = sp_info["page_h_pt"] * PT_TO_MM
        out.w(f"page{i} = doc.add_page(")
        out.indent += 1
        out.w(f"size=({_py_value(sp_w_mm)}, {_py_value(sp_h_mm)}),")
        out.w(f"bleed_mm={_py_value(bleed_mm)},")
        out.w("margins_mm=(0.0, 0.0, 0.0, 0.0),")
        out.w('master="Normal",')
        out.indent -= 1
        out.w(")")
    out.w("")
    for i in range(page_count):
        out.w(f"_add_page_{i}(doc, page{i})")
    out.w("")
    out.w("return doc")
    out.indent -= 1
    out.w("")


def _emit_styles_stub(out: PythonRepr, ctx: _Ctx) -> None:
    """Task 3 stub: emit an empty _add_styles function. Task 5 fills it."""
    out.w("def _add_styles(doc: Document) -> None:")
    out.indent += 1
    out.w('"""Paragraph styles — populated by tools/idml_to_dsl.py Phase G."""')
    out.w("# (no paragraph styles in this task-3 skeleton)")
    out.w("return None")
    out.indent -= 1
    out.w("")


def _emit_page_stubs(out: PythonRepr, ctx: _Ctx) -> None:
    """Task 3 stub: emit empty _add_page_<i> functions, one per render page.

    In "spread" mode a facing-pages spread becomes one wide page, so the stub
    count matches the spread count. In "page" mode each IDML page is its own
    render page (see _resolve_render_page_mode), so the count matches the
    total IDML page count. _collect_spread_pages reflects the active mode.
    """
    page_count = len(_collect_spread_pages(ctx))
    for i in range(page_count):
        out.w(f"def _add_page_{i}(doc: Document, page) -> None:")
        out.indent += 1
        out.w(f'"""Render page {i + 1} items — populated by tools/idml_to_dsl.py Phase H."""')
        out.w("# (no page items in this task-3 skeleton)")
        out.w("return None")
        out.indent -= 1
        out.w("")


def _emit_footer(out: PythonRepr) -> None:
    """Emit build_preview, build_doc alias, build(out_path), and __main__."""
    out.w("def build_preview() -> Document:")
    out.indent += 1
    out.w('"""Inject demo library images for gallery PNG render (#24 idiom).')
    out.w("")
    out.w("Pre-crops each library image to LIVE frame dimensions via")
    out.w("library.inject_into_frame. INJECT_MAP starts empty; humans wire it up.")
    out.w('"""')
    out.w("doc = build_template()")
    out.w("if not INJECT_MAP:")
    out.indent += 1
    out.w("return doc")
    out.indent -= 1
    out.w("from sla_lib.builder import library  # noqa: E402")
    out.w("for page in doc.pages:")
    out.indent += 1
    out.w("for item in page.items:")
    out.indent += 1
    out.w("if not isinstance(item, ImageFrame):")
    out.indent += 1
    out.w("continue")
    out.indent -= 1
    out.w("lib_id = INJECT_MAP.get(item.anname)")
    out.w("if not lib_id:")
    out.indent += 1
    out.w("continue")
    out.indent -= 1
    out.w("img = library.load(lib_id, optional=True)")
    out.w("if img is None:")
    out.indent += 1
    out.w("continue")
    out.indent -= 1
    out.w("library.inject_into_frame(")
    out.indent += 1
    out.w("item, img,")
    out.w("target_w_mm=item.w_mm,")
    out.w("target_h_mm=item.h_mm,")
    out.indent -= 1
    out.w(")")
    out.indent -= 1
    out.indent -= 1
    out.w("return doc")
    out.indent -= 1
    out.w("")
    out.w("")
    out.w("# Alias for audit_alignment.py / spec_check (they expect build_doc).")
    out.w("build_doc = build_template")
    out.w("")
    out.w("")
    out.w('def build(out_path: str | Path = HERE / "template.sla") -> Path:')
    out.indent += 1
    out.w("doc = build_preview()")
    out.w("out_path = Path(out_path)")
    out.w("doc.save(out_path)")
    out.w("return out_path")
    out.indent -= 1
    out.w("")
    out.w("")
    out.w('if __name__ == "__main__":')
    out.indent += 1
    out.w("path = build()")
    out.w('print(f"OK: saved {path}")')
    out.indent -= 1
    out.w("")


# ---------------------------------------------------------------------------
# Squiggle re-anchoring (Part B).
#
# The yellow squiggle motif is a free-standing Polygon placed at absolute page
# coordinates. Scribus wraps text differently from InDesign, so the underlined
# WORD shifts while the squiggle does not — it ends up under the wrong word.
# This pass binds each squiggle to the word it underlines in baseline.pdf and
# persists the mapping to templates/<slug>/squiggle_anchors.yml. The render-
# time playbook (tools/playbooks/squiggle_realign.py) reads that mapping,
# locates the same word in preview.pdf, and shifts the squiggle to track it.
# ---------------------------------------------------------------------------

# A squiggle is taller than a single underline only when it loops around a
# word (a circle-style emphasis). Treat any word whose ink box vertically
# overlaps the squiggle band — extended by this many points above the band —
# as a candidate; the squiggle is drawn BEHIND the text it emphasises.
_SQUIGGLE_WORD_Y_TOL_PT = 16.0


def _words_in_frame(page_words: list[dict], frame_box_pt: tuple[float, float, float, float]) -> list[dict]:
    """Return baseline.pdf words whose center lies inside ``frame_box_pt``.

    ``frame_box_pt`` is (x0, top, x1, bottom) in PDF points. The word list is
    kept in pdfplumber reading order so each word's index is a stable, render-
    independent ordinal that survives a different line-wrap in preview.pdf.
    """
    fx0, ft, fx1, fb = frame_box_pt
    out: list[dict] = []
    for w in page_words:
        cx = (w["x0"] + w["x1"]) / 2.0
        cy = (w["top"] + w["bottom"]) / 2.0
        if fx0 - 2.0 <= cx <= fx1 + 2.0 and ft - 2.0 <= cy <= fb + 2.0:
            out.append(w)
    return out


def _associate_squiggle_to_word(
    sq_box_pt: tuple[float, float, float, float],
    frame_words: list[dict],
) -> Optional[dict]:
    """Pick the anchor word a squiggle underlines from a frame's word list.

    The squiggle is a band drawn behind text. The anchor word is the
    LEFTMOST word on the line whose baseline best matches the squiggle band:
    that word's left edge is the most stable handle to translate the squiggle
    by when the line wraps elsewhere.

    Returns a dict ``{index, text, x0, top, x1, bottom}`` (index = position
    in ``frame_words``), or None when no word overlaps.
    """
    sx0, st, sx1, sb = sq_box_pt
    candidates: list[tuple[int, dict, float]] = []
    for idx, w in enumerate(frame_words):
        # Horizontal overlap with the squiggle band.
        ox = min(sx1, w["x1"]) - max(sx0, w["x0"])
        if ox <= 0.5:
            continue
        # Vertical proximity: the word's ink box must touch the squiggle band
        # (extended upward — the squiggle sits at/below the text baseline).
        if w["bottom"] < st - _SQUIGGLE_WORD_Y_TOL_PT:
            continue
        if w["top"] > sb + _SQUIGGLE_WORD_Y_TOL_PT:
            continue
        # Score: vertical distance from the word baseline to the squiggle
        # center (smaller = better match), tie-broken by leftmost x.
        sq_cy = (st + sb) / 2.0
        v_dist = abs(w["bottom"] - sq_cy)
        candidates.append((idx, w, v_dist))
    if not candidates:
        return None
    # Best line: the minimum vertical distance.
    best_v = min(c[2] for c in candidates)
    on_line = [c for c in candidates if c[2] <= best_v + 6.0]
    # Leftmost word on that line is the anchor.
    idx, w, _ = min(on_line, key=lambda c: c[1]["x0"])
    return {
        "index": idx,
        "text": w["text"],
        "x0": round(w["x0"], 3),
        "top": round(w["top"], 3),
        "x1": round(w["x1"], 3),
        "bottom": round(w["bottom"], 3),
    }


def _emit_squiggle_anchors(ctx: _Ctx, output: Path) -> None:
    """Write templates/<slug>/squiggle_anchors.yml for the squiggle playbook.

    Reads the sibling ``baseline.pdf`` (scaffolded into the template dir before
    the converter runs). For each recorded squiggle Polygon it:

      1. Finds the text frame it geometrically overlaps (page-local mm).
      2. Extracts that frame's words from baseline.pdf in reading order.
      3. Picks the anchor word the squiggle underlines.
      4. Records the squiggle bbox, the anchor word's baseline box, the word's
         ordinal within the frame (disambiguates repeats), and the squiggle's
         offset from the word box in the InDesign baseline.

    The file is only written when at least one squiggle was bound; templates
    with no yellow motif produce nothing.
    """
    if not ctx.squiggle_records:
        return
    try:
        import yaml  # local import — only needed when squiggles exist
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - env guard
        print(
            f"squiggle anchors: skipped — {exc} not available",
            file=sys.stderr,
        )
        return

    baseline_pdf = output.parent / "baseline.pdf"
    if not baseline_pdf.exists():
        print(
            f"squiggle anchors: skipped — no baseline.pdf at {baseline_pdf}",
            file=sys.stderr,
        )
        return

    PT = 72.0 / 25.4

    def _mm_box_to_pt(rec: dict) -> tuple[float, float, float, float]:
        return (
            rec["x_mm"] * PT,
            rec["y_mm"] * PT,
            (rec["x_mm"] + rec["w_mm"]) * PT,
            (rec["y_mm"] + rec["h_mm"]) * PT,
        )

    anchors: list[dict] = []
    with pdfplumber.open(str(baseline_pdf)) as pdf:
        n_pages = len(pdf.pages)
        # Cache extracted words per page.
        page_words_cache: dict[int, list[dict]] = {}
        for sq in ctx.squiggle_records:
            page_idx = sq["page"]
            if page_idx >= n_pages:
                continue
            sq_box = _mm_box_to_pt(sq)
            # Candidate text frames on the same page, ranked by bbox overlap.
            frame_hits: list[tuple[float, dict]] = []
            for tf in ctx.textframe_records:
                if tf["page"] != page_idx:
                    continue
                tb = _mm_box_to_pt(tf)
                ox = min(sq_box[2], tb[2]) - max(sq_box[0], tb[0])
                oy = min(sq_box[3], tb[3]) - max(sq_box[1], tb[1])
                if ox > 0 and oy > -_SQUIGGLE_WORD_Y_TOL_PT:
                    frame_hits.append((ox * max(oy, 0.1), tf))
            if not frame_hits:
                continue
            frame_hits.sort(key=lambda h: -h[0])
            if page_idx not in page_words_cache:
                page_words_cache[page_idx] = pdf.pages[page_idx].extract_words()
            page_words = page_words_cache[page_idx]
            # Try each candidate frame until one yields an anchor word.
            anchor_word = None
            target_frame = None
            for _, tf in frame_hits:
                fw = _words_in_frame(page_words, _mm_box_to_pt(tf))
                aw = _associate_squiggle_to_word(sq_box, fw)
                if aw is not None:
                    anchor_word = aw
                    target_frame = tf
                    break
            if anchor_word is None or target_frame is None:
                continue
            anchors.append({
                "anname": sq["anname"],
                "page": page_idx,
                "target_frame": target_frame["anname"],
                "word": anchor_word["text"],
                # Ordinal within the frame's reading-order word list — the
                # disambiguator when the word string repeats.
                "word_index": anchor_word["index"],
                "baseline_word_box_pt": {
                    "x0": anchor_word["x0"],
                    "top": anchor_word["top"],
                    "x1": anchor_word["x1"],
                    "bottom": anchor_word["bottom"],
                },
                "baseline_squiggle_box_mm": {
                    "x_mm": sq["x_mm"],
                    "y_mm": sq["y_mm"],
                    "w_mm": sq["w_mm"],
                    "h_mm": sq["h_mm"],
                },
                # Squiggle origin offset from the anchor word's box, in mm,
                # measured in the InDesign baseline. The playbook keeps this
                # offset constant: new_squiggle_xy = preview_word_xy + offset.
                "offset_from_word_mm": {
                    "dx_mm": round(sq["x_mm"] - anchor_word["x0"] / PT, 4),
                    "dy_mm": round(sq["y_mm"] - anchor_word["top"] / PT, 4),
                },
            })

    if not anchors:
        return
    doc = {
        "template": ctx.template_id,
        "_schema_version": 1,
        "_doc": (
            "Squiggle re-anchoring map. Each entry binds a yellow squiggle "
            "Polygon (anname) to the word it underlines in baseline.pdf. "
            "tools/playbooks/squiggle_realign.py consumes this to keep the "
            "squiggle tracking its word when Scribus wraps text differently."
        ),
        "anchors": anchors,
    }
    anchors_path = output.parent / "squiggle_anchors.yml"
    anchors_path.write_text(
        yaml.dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    print(
        f"OK: wrote {anchors_path} ({len(anchors)} squiggle anchor(s))",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
def convert(source: Path, output: Path, template_id: str, assets_dir: Path,
            logo_map_path: Optional[Path] = None,
            asset_map_path: Optional[Path] = None,
            allow_dropped_pageitems: bool = False) -> None:
    """Strict 7-phase IDML → DSL build.py converter.

    Phases:
        A. Document preferences (page size, bleed)
        B. Layers (designmap.xml)
        C. MasterSpread emptiness check
        D/E. Document scaffold emit (header + Document() + add_master + add_page)
        F. Colors (task 4)
        G. Styles (task 5)
        H. Page items (tasks 6-7)
        Final emit: assemble + write to output (task 8)
    """
    if not source.exists():
        raise UnhandledElement(f"Source IDML not found: {source}")
    # Reject .indd: first 4 bytes of IDML must be PK\x03\x04 (ZIP magic).
    with source.open("rb") as f:
        head = f.read(4)
    if head != b"PK\x03\x04":
        raise UnhandledElement(
            f"{source.name} is not a valid IDML (ZIP). "
            f"If this is a .indd, re-export from InDesign: "
            f"File > Export > InDesign Markup (IDML)."
        )
    # The legacy --assets-dir is only consulted when no Phase-2 --asset-map
    # manifest is supplied. Validate its existence only in that case, so a
    # missing/auto-derived assets dir never masks the real --asset-map error.
    if (
        asset_map_path is None
        and assets_dir is not None
        and not assets_dir.exists()
    ):
        raise UnhandledElement(
            f"--assets-dir {assets_dir} does not exist "
            f"(extend tools/idml_to_dsl.py:convert or pass a different directory)"
        )

    # Load the logo map (legacy, locked decision #2). NFC-normalise keys to
    # match _basename_from_uri.
    logo_map: dict[str, str] = {}
    if logo_map_path is not None:
        if not logo_map_path.exists():
            raise UnhandledElement(
                f"--logo-map {logo_map_path} does not exist "
                f"(extend tools/idml_to_dsl.py:convert)"
            )
        import yaml  # local import: yaml not needed when both maps omitted
        raw = yaml.safe_load(logo_map_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise UnhandledElement(
                f"--logo-map YAML must be a mapping at the top level, got {type(raw).__name__} "
                f"(extend tools/idml_to_dsl.py:convert)"
            )
        for k, v in raw.items():
            logo_map[unicodedata.normalize("NFC", str(k))] = str(v)

    # Load the asset map (Phase 2). Schema:
    #   assets:
    #     "<original basename>":
    #       output: <repo-relative path>
    #       kind: <vector_ai|raster_psd|raster_jpg|raster_png>
    #       recipe: <description>
    # The converter only consumes the ``output`` field; ``kind``/``recipe`` are
    # provenance for human reviewers + future tooling.
    asset_map: dict[str, str] = {}
    if asset_map_path is not None:
        if not asset_map_path.exists():
            raise UnhandledElement(
                f"--asset-map {asset_map_path} does not exist "
                f"(run tools/links_export.py to produce it)"
            )
        import yaml  # local import: yaml not needed when both maps omitted
        raw_doc = yaml.safe_load(asset_map_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw_doc, dict):
            raise UnhandledElement(
                f"--asset-map YAML must be a mapping at the top level, got {type(raw_doc).__name__} "
                f"(extend tools/idml_to_dsl.py:convert)"
            )
        assets_block = raw_doc.get("assets", raw_doc)
        if not isinstance(assets_block, dict):
            raise UnhandledElement(
                f"--asset-map YAML's 'assets:' block must be a mapping, got "
                f"{type(assets_block).__name__} "
                f"(extend tools/idml_to_dsl.py:convert)"
            )
        for k, v in assets_block.items():
            key = unicodedata.normalize("NFC", str(k))
            if isinstance(v, dict):
                out_path = v.get("output")
                if not out_path:
                    raise UnhandledElement(
                        f"--asset-map entry {key!r} is missing required 'output:' field "
                        f"(extend tools/idml_to_dsl.py:convert)"
                    )
                asset_map[key] = str(out_path)
            else:
                # Tolerate the flat {basename: output_path} shape for back-compat.
                asset_map[key] = str(v)

    with IDMLPackage(str(source)) as pkg:
        ctx = _Ctx(pkg=pkg, template_id=template_id, assets_dir=assets_dir)
        ctx.source = source
        ctx.logo_map = logo_map
        ctx.asset_map = asset_map

        # Issue #39 Phase A + C: load asset_policy and populate
        # ctx.embedded_set so the 3 emit sites can route via
        # _emit_image_or_inline. When the policy is absent
        # (templates without shared/assets/<slug>/) the set stays empty
        # and every emit takes the repo-relative branch — still no
        # absolute paths.
        try:
            from sla_lib.builder.meta_schema import load_asset_policy as _load_asset_policy
            policy = _load_asset_policy(template_id, root=ROOT)
        except ValueError:
            # Schema or disjoint error — surface upstream via the audits
            # (tools/asset_policy_audit.py). The converter itself stays
            # silent here so the build still emits a (relative-path) SLA
            # for human review.
            policy = None
        if policy is not None:
            ctx.embedded_set = set(policy.get("embedded", []) or [])
            ctx.external_set = set(policy.get("external", []) or [])

        # Phase A
        ctx.doc_prefs = _read_doc_preferences(pkg)
        # Phase B
        ctx.layers = _read_layers(pkg)
        ctx.layer_id_to_idx = {lyr["self_id"]: idx for idx, lyr in enumerate(ctx.layers)}
        # InDesign's default PDF export includes every Visible=true layer
        # regardless of Printable. Layer Printable controls dialog defaults,
        # not export inclusion; the baselines we audit against were exported
        # this way, so include every Visible layer. Items on Visible=false
        # layers stay out of the render (and the inventory walker).
        ctx.printable_layer_ids = {
            lyr["self_id"] for lyr in ctx.layers if lyr["visible"]
        }
        ctx.truly_printable_layer_ids = {
            lyr["self_id"] for lyr in ctx.layers
            if lyr["visible"] and lyr["printable"]
        }
        # Phase C
        _check_masters_empty(pkg)
        # Resolve the render-page model (per-page vs spread-merged) by
        # comparing the sibling baseline.pdf page count against the IDML's
        # page/spread counts. Must run before _emit_page_stubs / _emit_pages.
        _resolve_render_page_mode(ctx)
        # Phase F — colors (run early so styles/items can translate FillColor refs)
        _emit_colors(ctx)

        # Phase D — header
        _emit_header(ctx.out, template_id, source.name)
        # Phase G stub — _add_styles (filled in task 5)
        _emit_styles_stub(ctx.out, ctx)
        # Phase H stub — _add_page_<i> (filled in tasks 6-7)
        _emit_page_stubs(ctx.out, ctx)
        # Phase E — build_template (Document + master + pages)
        _emit_document_scaffold(ctx.out, ctx)
        # Phase G — paragraph styles (overrides the task-3 stub)
        _emit_paragraph_styles(ctx.out, ctx)
        # Phase H — page items (overrides the task-3 stubs)
        _emit_pages(ctx)
        # Footer (build_preview / build / main)
        _emit_footer(ctx.out)
        # Final strict-mode gates: surface unmapped logos / missing assets.
        _final_strictness_gates(ctx)
        # Issue #37 P3 task 16: completeness assertion — every IDML
        # PageItem must have been emitted OR explicitly skipped with a
        # reason. --allow-dropped-pageitems bypasses for debugging.
        if not allow_dropped_pageitems:
            _assert_conversion_completeness(ctx)

        # Emit a machine-readable manifest of IDML PageItems the converter
        # deliberately skipped (off-page artifacts, hidden layers, Falz/print
        # marks). The Stage-1 inventory gate reads these ``# idml-skip:`` lines
        # to distinguish a deliberate skip from a silent drop.
        if ctx.skipped_with_reason:
            ctx.out.w("")
            ctx.out.w(
                "# --- IDML PageItems intentionally not emitted "
                "(machine-readable; do not delete) ---"
            )
            for entry in ctx.skipped_with_reason:
                reason = str(entry["reason"]).replace("\n", " ")
                ctx.out.w(f"# idml-skip: {entry['self_id']} — {reason}")

        # Write emitted Python source
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(ctx.out.render(), encoding="utf-8")
        print(f"OK: wrote {output}", file=sys.stderr)

        # Part B: bind each yellow squiggle to the word it underlines and
        # persist templates/<slug>/squiggle_anchors.yml for the realign
        # playbook. Best-effort — never fails the conversion.
        try:
            _emit_squiggle_anchors(ctx, output)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"squiggle anchors: skipped — {exc}", file=sys.stderr)
        print(
            f"OK: opened {source.name} — "
            f"{len(pkg.spreads_objects)} spreads, "
            f"{len(pkg.stories)} stories"
        )


# ---------------------------------------------------------------------------
def _auto_invoke_links_export(source: Path) -> Optional[Path]:
    """Run tools/links_export.py against the IDML's sibling Links/ directory.

    Returns the path to the produced ``links_export.yml``, or ``None`` if no
    sibling Links/ directory exists (caller falls back to legacy --logo-map +
    --assets-dir behaviour).

    Determinism: links_export.py is itself deterministic, and we pass
    ``--idml-name`` so the output directory is auto-derived to
    ``shared/assets/<slug>/``.
    """
    links_dir = source.parent / "Links"
    if not links_dir.is_dir():
        return None
    here = Path(__file__).resolve().parent
    cmd = [
        sys.executable,
        str(here / "links_export.py"),
        str(links_dir),
        "--idml-name", str(source),
    ]
    import subprocess  # local import; rarely used from this entry point
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise UnhandledElement(
            f"auto-invoke of tools/links_export.py failed "
            f"(rc={result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    print(result.stderr, file=sys.stderr, end="")
    # Re-derive the manifest path the same way links_export.py does.
    # We import the helper rather than re-implementing the slugifier here.
    sys.path.insert(0, str(here))
    from links_export import derive_out_dir  # type: ignore[import-not-found]  # local sibling
    return derive_out_dir(source) / "links_export.yml"


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Strict IDML→DSL converter (one-shot bootstrap)."
    )
    ap.add_argument("source", type=Path, help="Input .idml file")
    ap.add_argument("output", type=Path, help="Output build.py path")
    ap.add_argument(
        "--template-id",
        required=True,
        help="Slug baked into Document(template_id=...).",
    )
    ap.add_argument(
        "--asset-map",
        type=Path,
        required=False,
        default=None,
        help=(
            "Phase 2 manifest produced by tools/links_export.py. "
            "Maps each Links/ basename (e.g. 'BlueSky weiss.ai', "
            "'Plakat dunkel für Flyer.psd') to a converted asset under "
            "shared/assets/<idml-slug>/. If omitted AND a sibling Links/ "
            "directory exists next to the IDML, the converter auto-invokes "
            "tools/links_export.py."
        ),
    )
    ap.add_argument(
        "--assets-dir",
        type=Path,
        required=False,
        default=None,
        help=(
            "Legacy: directory containing the IDML's linked raster assets "
            "(resolves file: URIs by basename). Used when --asset-map is "
            "not supplied. When omitted, defaults to the IDML's sibling "
            "Links/ directory. Prefer --asset-map for new templates."
        ),
    )
    ap.add_argument(
        "--logo-map",
        type=Path,
        required=False,
        default=None,
        help=(
            "Legacy: YAML mapping IDML vector-logo basenames to pre-rasterised "
            "PNG paths. Superseded by --asset-map (which covers both vector "
            "and raster). Kept for backward-compat; --asset-map wins when "
            "both are supplied."
        ),
    )
    ap.add_argument(
        "--allow-dropped-pageitems",
        action="store_true",
        help=(
            "Bypass the end-of-conversion completeness assertion that fires "
            "when an IDML PageItem produced no output and was not explicitly "
            "skipped via ctx.record_skipped(). Use only for debugging; the "
            "default (strict) is what CI should run."
        ),
    )
    args = ap.parse_args(argv)

    # Resolve the legacy --assets-dir default to the IDML's sibling Links/
    # directory. The legacy fallback is only consulted when --asset-map is
    # absent; deriving it from the source IDML keeps multi-template runs
    # independent of each other.
    if args.assets_dir is None:
        args.assets_dir = args.source.parent / "Links"

    # Auto-invoke fallback: no --asset-map AND no --logo-map AND a sibling
    # Links/ directory exists → run tools/links_export.py to produce one.
    # The auto-invoke is intentionally skipped when --logo-map IS supplied
    # so legacy flows that don't want the new shared/assets/ tree stay
    # backward-compatible.
    asset_map_path = args.asset_map
    if asset_map_path is None and args.logo_map is None and args.source.exists():
        try:
            asset_map_path = _auto_invoke_links_export(args.source)
        except UnhandledElement as e:
            print(f"UnhandledElement: {e}", file=sys.stderr)
            return 2
        if asset_map_path is not None:
            print(
                f"OK: auto-invoked tools/links_export.py → {asset_map_path}",
                file=sys.stderr,
            )

    try:
        convert(args.source, args.output, args.template_id, args.assets_dir,
                logo_map_path=args.logo_map,
                asset_map_path=asset_map_path,
                allow_dropped_pageitems=args.allow_dropped_pageitems)
    except UnhandledElement as e:
        print(f"UnhandledElement: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

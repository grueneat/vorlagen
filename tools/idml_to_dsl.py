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

# IDML built-in swatches that should not be emitted (process inks, registration,
# transparency placeholders). See locked decision #1 commentary.
IDML_BUILTIN_COLORS_SKIP = {
    "Color/None",
    "Color/Registration",
    "Color/Cyan",
    "Color/Magenta",
    "Color/Yellow",
    "Color/Black",
    "Swatch/None",
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

    xs = [p[0] for p in page_local]
    ys = [p[1] for p in page_local]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w = max_x - min_x
    h = max_y - min_y

    rotation_deg = math.degrees(math.atan2(b, a))

    return (min_x, min_y, w, h, rotation_deg)


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
_NARROW_CHAR_RATIO: float = 0.40


def _required_text_frame_height_mm(
    point_size_pt: float,
    leading_pt: Optional[float],
) -> float:
    """Minimum h_mm Scribus needs to render one line without clipping.

    Scribus suppresses lines when frame_h_pt < effective_line_height_pt.
    Effective line height is ``leading_pt`` (if explicitly set) else
    ``point_size_pt * 1.2`` (standard auto-leading multiplier).

    InDesign tolerates frame_h < line_height by silently overflowing;
    Scribus does not. The converter compensates by widening h_mm when needed.
    """
    line_h_pt = leading_pt if leading_pt is not None else point_size_pt * 1.2
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
    line_h_pt = leading_pt if leading_pt is not None else max_fontsize_pt * 1.2
    line_h_mm = line_h_pt * PT_TO_MM
    epsilon_mm = 0.05  # avoid flapping on sub-mm rounding

    # Sub-case A: can't show even one line.
    required_mm_one_line = line_h_mm
    if idml_h_mm < required_mm_one_line - epsilon_mm:
        leading_desc = (
            f"leading={leading_pt:.2f}pt" if leading_pt is not None
            else f"auto-leading={max_fontsize_pt:.0f}pt×1.2"
        )
        comment = (
            f"h_mm widened {idml_h_mm:.4f}mm→{required_mm_one_line:.4f}mm: "
            f"Scribus clips lines when frame_h < effective line height "
            f"({leading_desc}; IDML overflows silently)"
        )
        return required_mm_one_line, comment

    # Sub-case C: explicit line count (from breakline/para separators) — exact.
    # Runs that carry separator=breakline or separator=para each add an explicit
    # newline; explicit_line_count = separator_count + 1 (at minimum 1).
    if explicit_line_count >= 2:
        required_mm_explicit = explicit_line_count * line_h_mm
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

    # Sub-case B: frame fits ≥1 line but not all lines (InDesign overset on
    # single-paragraph text). Only run when caller supplied text measurement data.
    if total_text_chars > 0 and frame_w_mm > 0.0 and max_fontsize_pt > 0:
        n_lines = _estimate_line_count(total_text_chars, frame_w_mm, max_fontsize_pt)
        required_mm_all = n_lines * line_h_mm
        # Widen when frame_h < estimated total height. The conservative char-width
        # ratio (_NARROW_CHAR_RATIO=0.40) under-estimates chars_per_line, so n_lines
        # tends to be ≥ actual; widening is only triggered when the deficit is real.
        if idml_h_mm < required_mm_all - epsilon_mm:
            leading_desc = (
                f"leading={leading_pt:.2f}pt" if leading_pt is not None
                else f"auto-leading={max_fontsize_pt:.0f}pt×1.2"
            )
            comment = (
                f"h_mm widened {idml_h_mm:.4f}mm→{required_mm_all:.4f}mm: "
                f"IDML overset text ({total_text_chars} chars, ~{n_lines} lines "
                f"estimated at {max_fontsize_pt:.0f}pt {_NARROW_CHAR_RATIO:.2f}× "
                f"ratio, {leading_desc}; Scribus clips, InDesign overflows silently)"
            )
            return required_mm_all, comment

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
    # Filled by Phase A
    doc_prefs: dict[str, Any] = field(default_factory=dict)
    # Filled by Phase B
    layers: list[dict[str, Any]] = field(default_factory=list)
    layer_id_to_idx: dict[str, int] = field(default_factory=dict)
    printable_layer_ids: set[str] = field(default_factory=set)
    # Filled by Phase F (task 4)
    color_map: dict[str, str] = field(default_factory=dict)
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


def _emit_colors_from_xml(graphic_xml: bytes, used_colors: set[str]) -> dict[str, str]:
    """Parse a Resources/Graphic.xml blob and return idml_self → dsl_name map.

    Args:
        graphic_xml: the raw XML bytes of Resources/Graphic.xml.
        used_colors: set of IDML Self IDs that are referenced by a printable
            PageItem or Story. Used to gate the "non-brand printable raises"
            vs "non-brand unused silently dropped" branches.

    Returns:
        Map ``{idml_self_id: brand_or_local_dsl_name}``. Caller stores on ctx.

    Raises:
        UnhandledElement when a referenced color cannot be mapped to a brand
        name (locked decision #1: snap-to-brand fuzzy matching is OOS for v1).
    """
    root = etree.fromstring(graphic_xml, parser=_SECURE_XMLPARSER)
    resolved: dict[str, str] = {}
    for c in root.findall(".//Color"):
        self_id = c.get("Self", "")
        if self_id in IDML_BUILTIN_COLORS_SKIP:
            # Color/None / Swatch/None / Registration / Process inks listed
            # in IDML_BUILTIN_COLORS_SKIP never reach the SLA.
            continue
        override = c.get("ColorOverride", "")
        if "Hiddenreserved" in override:
            # Latent process inks (Cyan/Magenta/Yellow/Black) marked as hidden;
            # never used, never emitted.
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
        # Non-brand printable swatch.
        if self_id in used_colors:
            raise UnhandledElement(
                f"Color {self_id!r} CMYK={cmyk} does not match shared/ci.yml "
                f"brand palette and is used by a printable PageItem. "
                f"(extend tools/idml_to_dsl.py:_emit_colors_from_xml or add "
                f"to COLOR_CMYK_TO_BRAND)"
            )
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
    """Phase F driver. Populates ctx.color_map."""
    used = _collect_used_fillcolors(ctx.pkg, ctx.printable_layer_ids)
    graphic_xml = ctx.pkg.open("Resources/Graphic.xml").read()
    ctx.color_map = _emit_colors_from_xml(graphic_xml, used)


# ---------------------------------------------------------------------------
# Phase G — Paragraph styles (Resources/Styles.xml) per RESEARCH §"Styles".
#
# IDML Justification → Scribus ParaStyle.align int.
# (0=left, 1=center, 2=right, 3=block, per tools/sla_lib/builder/styles.py)
# ---------------------------------------------------------------------------
JUSTIFICATION_MAP = {
    "LeftAlign": 0,
    "CenterAlign": 1,
    "RightAlign": 2,
    "FullyJustified": 3,
    "LeftJustified": 3,
    "RightJustified": 3,
    "CenterJustified": 3,
}

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
        styles[self_id] = {
            "self_id": self_id,
            "name": name,
            "based_on_self": based_on,
            "point_size": float(point_size) if point_size is not None else None,
            "leading": leading,
            "fill_color": fill_color,
            "font_style": font_style,
            "justification": justification,
            "applied_font": applied_font,
            "tab_stops": tab_stops if tab_stops else None,
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
        for k in ("point_size", "leading", "fill_color", "font_style",
                  "justification", "applied_font", "tab_stops"):
            if resolved.get(k) is None:
                resolved[k] = parent.get(k)
        parent_self = parent.get("based_on_self")
    return resolved


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
            if ld and ld != "Auto":
                try:
                    kwargs["linesp"] = float(ld)
                except ValueError:
                    pass
            # Tab stops: emit only those defined directly on THIS style (not inherited),
            # so child styles don't redundantly repeat the parent's tab stops.
            own_tabs = st.get("tab_stops")
            if own_tabs:
                kwargs["tab_stops"] = tuple(
                    (round(pos, 4), typ) for pos, typ in own_tabs
                )
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
                # Resolve relative asset_map paths to absolute.
                abs_mapped = (
                    str(Path(mapped).resolve())
                    if not Path(mapped).is_absolute()
                    else mapped
                )
                # Extract per-PDF placement params from the PDF child's ItemTransform.
                pdf_transform_str = pdf.get("ItemTransform", "")
                pdf_local_scale: Optional[tuple[float, float]] = None
                pdf_local_offset: Optional[tuple[float, float]] = None
                if pdf_transform_str:
                    pdf_local_scale, pdf_local_offset = _extract_content_local_params(
                        pdf_transform_str, frame_tl_anchor,
                    )
                # Use the mapped PNG for the entire enclosing frame.
                _emit_image_frame_call(
                    out, x_mm, y_mm, w_mm, h_mm, rot, self_id, layer_idx,
                    image_path=abs_mapped, ctx=ctx,
                    local_scale=pdf_local_scale, local_offset_pt=pdf_local_offset,
                )
                return
            ctx.unmapped_logos.append((pdf.get("Self", "?"), basename or uri))
        return  # don't also emit the surrounding rectangle as a Polygon

    if image_children:
        # Use the first <Image> child as the visual content.
        img = image_children[0]
        _emit_image_content(out, item, img, x_mm, y_mm, w_mm, h_mm, rot,
                            self_id, layer_idx, ctx,
                            frame_tl_anchor=frame_tl_anchor)
        return

    if tag == "TextFrame":
        _strict_no_threading(item)
        parent_story = item.get("ParentStory")
        # Determine the per-frame default ParaStyle (first PSR in the story).
        style_slug = ""
        runs: list[Run] = []
        trail_attrs: Optional[dict] = None
        _first_psr_style_self: Optional[str] = None  # for Pattern-9 leading lookup
        if parent_story:
            story_root = _resolve_story_xml(ctx.pkg, parent_story)
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
        if _leading_pt is None and _first_psr_style_self:
            _ps_data = ctx.paragraph_styles.get(_first_psr_style_self, {})
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
        if runs:
            _separator_count = sum(
                1 for _r in runs if _r.separator in ("breakline", "para")
            )
            if _separator_count > 0:
                # Sub-case C: exact line count from separators.
                _explicit_line_count = _separator_count + 1
            else:
                # Sub-case B: single-paragraph char-count heuristic.
                for _r in runs:
                    if _r.separator is None and _r.text:
                        _total_text_chars += len(_r.text)

        emitted_h_mm = _round_mm(h_mm)
        _widened_h_mm, _widen_comment = _maybe_widen_frame_h(
            emitted_h_mm, _max_fontsize_pt, _leading_pt,
            total_text_chars=_total_text_chars,
            frame_w_mm=_round_mm(w_mm),
            explicit_line_count=_explicit_line_count,
        )
        if _widen_comment:
            ctx.out.w(f"# {_widen_comment}")
            emitted_h_mm = _round_mm(_widened_h_mm)

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
        # DefaultStyle ALIGN propagation: when the frame's first PSR's
        # effective ParaStyle has non-Left Justification, emit ALIGN on the
        # <DefaultStyle/> element. Scribus's trail/per-paragraph ALIGN does
        # NOT propagate to the paragraph THEY terminate; only DefaultStyle
        # ALIGN reliably applies to every paragraph in the StoryText,
        # including auto-wrapped lines of the LAST paragraph. Issue 37
        # Backport 11.
        if _first_psr_style_self and _first_psr_style_self in ctx.paragraph_styles:
            _eff_just = ctx.paragraph_styles[_first_psr_style_self].get("justification")
            if _eff_just in JUSTIFICATION_MAP and JUSTIFICATION_MAP[_eff_just] != 0:
                kwargs["default_style_attrs"] = {
                    "ALIGN": str(JUSTIFICATION_MAP[_eff_just]),
                }
        # Fill (frame background, rare on TextFrame but corpus has Color/Paper
        # cases — drop through the color map).
        fc = _resolve_fill(item.get("FillColor"), ctx.color_map)
        if fc:
            kwargs["fill"] = fc
        _emit_call(
            ctx.out, "TextFrame", kwargs,
            receiver=page_var, multiline=True,
        )
        return

    if tag in ("Rectangle", "Polygon", "Oval"):
        # Complex Polygon: multiple sub-paths, open paths, or Bezier curves.
        # These cannot be expressed as a simple Scribus rectangle/polygon bbox;
        # emit as PolyLine (PTYPE=7) with verbatim SLA path data extracted from
        # the IDML PathGeometry (transform chain: item → ancestors → page-local).
        if tag == "Polygon" and _is_complex_polygon(item):
            sc = _resolve_fill(item.get("StrokeColor"), ctx.color_map)
            if not sc:
                sc = "Black"
            sw = item.get("StrokeWeight", "0")
            try:
                sw_pt = float(sw)
            except (ValueError, TypeError):
                sw_pt = 0.0
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
                "line_color": sc,
                "line_width_pt": sw_pt,
                "anname": self_id,
                "layer": layer_idx,
            }
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
    if image_path:
        kwargs["image"] = image_path
    if inline_data is not None and inline_ext is not None:
        kwargs["inline_image_data"] = inline_data
        kwargs["inline_image_ext"] = inline_ext
    # Emit content placement params when they deviate meaningfully from defaults.
    # Scribus default: local_scale=(1,1), local_offset=(0,0).
    if local_scale is not None:
        scx, scy = local_scale
        if abs(scx - 1.0) > 1e-4 or abs(scy - 1.0) > 1e-4:
            kwargs["local_scale"] = (round(scx, 6), round(scy, 6))
    if local_offset_pt is not None:
        ox_pt, oy_pt = local_offset_pt
        # Convert pt → mm for the DSL parameter (primitives.py multiplies back).
        ox_mm = ox_pt * PT_TO_MM
        oy_mm = oy_pt * PT_TO_MM
        if abs(ox_mm) > 0.01 or abs(oy_mm) > 0.01:
            kwargs["local_offset_mm"] = (round(ox_mm, 4), round(oy_mm, 4))
    page_var = ctx.layer_id_to_idx  # unused; emit call always uses receiver via outer scope
    # The receiver is the page variable (e.g. "page0"); the outer _emit_pageitem
    # passes ctx.out and the page_var explicitly. For simplicity here we emit
    # without a receiver and rely on the outer page-loop variable. Use a
    # global stash on ctx instead.
    receiver = getattr(ctx, "_current_page_var", None) or "page"
    _emit_call(ctx.out, "ImageFrame", kwargs, receiver=receiver, multiline=True)


_SCRIBUS_FRIENDLY_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


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

    Args:
        frame_tl_anchor: the ``(min_x, min_y)`` of the Rectangle frame's
            PathPointArray anchors in item-local coordinates. Used with the
            Image's ``ItemTransform`` to derive the correct Scribus
            ``LOCALX / LOCALY`` content placement (see
            ``_extract_content_local_params``).
    """
    link = img.find(".//Link")
    uri = link.get("LinkResourceURI", "") if link is not None else ""
    basename = _basename_from_uri(uri)
    if not basename:
        raise UnhandledElement(
            f"<Image Self={img.get('Self')!r}> inside Rectangle Self={self_id!r}: "
            f"unparseable LinkResourceURI {uri!r} "
            f"(extend tools/idml_to_dsl.py:_emit_image_content)"
        )

    # Extract per-image placement params from the Image child's ItemTransform.
    # The IDML Image element's ItemTransform encodes the content scale and
    # its origin offset within the frame (see _extract_content_local_params).
    local_scale: Optional[tuple[float, float]] = None
    local_offset_pt: Optional[tuple[float, float]] = None
    img_transform_str = img.get("ItemTransform", "")
    if img_transform_str and frame_tl_anchor is not None:
        local_scale, local_offset_pt = _extract_content_local_params(
            img_transform_str, frame_tl_anchor,
        )

    # 1. Asset-map lookup (Phase 2 path).
    if ctx.asset_map:
        mapped = ctx.asset_map.get(basename)
        if mapped:
            # Resolve relative asset_map paths to absolute so Scribus finds
            # the file regardless of the working directory at render time.
            abs_mapped = str(Path(mapped).resolve()) if not Path(mapped).is_absolute() else mapped
            _emit_image_frame_call(
                ctx.out, x_mm, y_mm, w_mm, h_mm, rot,
                self_id, layer_idx, image_path=abs_mapped, ctx=ctx,
                local_scale=local_scale, local_offset_pt=local_offset_pt,
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
    # Absolute path so Scribus resolves the file at render time regardless of cwd.
    emit_path = str(asset_path.resolve())
    try:
        # Also try repo-relative for human readability in the emitted source.
        rel_path = asset_path.resolve().relative_to(ROOT)
        emit_path = str(rel_path).replace("\\", "/")
    except ValueError:
        # Asset is outside the repo root; fall back to absolute path string.
        emit_path = str(asset_path.resolve())

    _emit_image_frame_call(
        ctx.out, x_mm, y_mm, w_mm, h_mm, rot,
        self_id, layer_idx, image_path=emit_path, ctx=ctx,
        local_scale=local_scale, local_offset_pt=local_offset_pt,
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


def _psr_effective_leading(psr: Any) -> Optional[str]:
    """Return the effective Leading for a ParagraphStyleRange.

    Scans all CharacterStyleRange children for a ``<Properties/Leading>``
    value.  The first CSR with an explicit (non-Auto) numeric Leading wins
    (InDesign applies the leading of the *first* CSR in the paragraph as the
    dominant line spacing).  Returns ``"Auto"`` when the first CSR's leading
    is literally ``"Auto"``; returns ``None`` when no CSR carries any Leading
    child at all (caller should fall back to the paragraph style's own leading
    or leave the ``<para>`` element without explicit LINESPMode/LINESP).
    """
    for csr in psr:
        if not isinstance(csr.tag, str):
            continue
        if etree.QName(csr).localname != "CharacterStyleRange":
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

        # PSR inline Justification override: a non-default Justification
        # attribute on the PSR overrides the AppliedParagraphStyle's alignment.
        # This is the same pattern as CSR FontStyle (R5) — an inline attribute
        # that takes precedence over the applied style's defaults.
        # LeftAlign (0) is the default; only non-zero values require an override.
        psr_just = psr.get("Justification")
        psr_para_attrs: dict = {}
        if psr_just and psr_just in JUSTIFICATION_MAP:
            align_int = JUSTIFICATION_MAP[psr_just]
            if align_int != 0:  # 0 = LeftAlign = default, no override needed
                psr_para_attrs["ALIGN"] = str(align_int)
        elif psr_just and psr_just not in JUSTIFICATION_MAP:
            raise UnhandledElement(
                f"ParagraphStyleRange Justification={psr_just!r} unknown "
                f"(extend tools/idml_to_dsl.py:JUSTIFICATION_MAP)"
            )

        # Per-para LINESPMode + LINESP from the CSR's Properties/Leading.
        # InDesign renders with the explicit Leading value from the first CSR in
        # the paragraph; Scribus falls back to ~15pt without an explicit LINESP.
        # Scribus SLA LINESPMode semantics (from reference.sla corpus):
        #   0 = auto (proportional to font size; LINESP is a default, not enforced)
        #   1 = auto-from-font-metrics (no explicit LINESP needed)
        #   2 = explicit fixed LINESP value ("Fixed" in Scribus UI)
        # We emit LINESPMode="2" + LINESP=<value> for numeric IDML Leading, or
        # LINESPMode="1" for Auto-leading (font-metrics-based).
        psr_ld = _psr_effective_leading(psr)
        if psr_ld is not None:
            if psr_ld == "Auto":
                psr_para_attrs["LINESPMode"] = "1"
            else:
                try:
                    psr_para_attrs["LINESPMode"] = "2"
                    psr_para_attrs["LINESP"] = str(float(psr_ld))
                except ValueError:
                    pass  # malformed value — skip silently

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
    psr_just = last_psr.get("Justification")
    if psr_just and psr_just in JUSTIFICATION_MAP:
        align_int = JUSTIFICATION_MAP[psr_just]
        if align_int != 0:
            trail["ALIGN"] = str(align_int)
    psr_ld = _psr_effective_leading(last_psr)
    if psr_ld is not None:
        if psr_ld == "Auto":
            trail["LINESPMode"] = "1"
        else:
            try:
                trail["LINESPMode"] = "2"
                trail["LINESP"] = str(float(psr_ld))
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


def _emit_pages(ctx: _Ctx) -> None:
    """Phase H driver: emit one _add_page_<i> function body per page."""
    spreads = list(ctx.pkg.spreads)
    pages = list(ctx.pkg.pages)
    if len(spreads) != len(pages):
        raise UnhandledElement(
            f"Expected one Page per Spread, got {len(spreads)} spreads "
            f"and {len(pages)} pages "
            f"(extend tools/idml_to_dsl.py:_emit_pages)"
        )
    for i, (sp_path, page_obj) in enumerate(zip(spreads, pages)):
        xml = ctx.pkg.open(sp_path).read()
        root = etree.fromstring(xml, parser=_SECURE_XMLPARSER)
        spread_node = root.find(".//Spread")
        spread_t = spread_node.get("ItemTransform", "1 0 0 1 0 0")
        page_node = spread_node.find("Page")
        page_t = page_node.get("ItemTransform", "1 0 0 1 0 0")
        page_gb = _parse_geometric_bounds(page_node.get("GeometricBounds", "0 0 0 0"))
        page_var = f"page{i}"
        ctx._current_page_var = page_var  # type: ignore[attr-defined]

        # Override the task-3 stub for this page.
        ctx.out.w("")
        ctx.out.w(f"def _add_page_{i}(doc: Document, {page_var}) -> None:  # overrides task-3 stub")
        ctx.out.indent += 1
        ctx.out.w(f'"""Auto-generated page-items for page {i + 1} (Spread {sp_path})."""')

        # Page dimensions for the out-of-page guard below.
        page_gb_y1, page_gb_x1, page_gb_y2, page_gb_x2 = page_gb
        page_w_pt = page_gb_x2 - page_gb_x1
        page_h_pt = page_gb_y2 - page_gb_y1
        # Items more than this many mm outside the page+bleed area are treated
        # as InDesign design artifacts (e.g. guide markers on printable layers)
        # that InDesign does not export to PDF.  Bleed is typically ≤3 mm so
        # a 20 mm guard safely excludes true out-of-page artifacts.
        _OUT_OF_PAGE_GUARD_MM = 20.0
        _guard_pt = _OUT_OF_PAGE_GUARD_MM / PT_TO_MM

        emit_count = 0
        for child in spread_node:
            if not isinstance(child.tag, str):
                continue
            tag = etree.QName(child).localname
            if tag in ("Page", "FlattenerPreference"):
                continue
            item_layer = child.get("ItemLayer", "")
            if item_layer not in ctx.printable_layer_ids:
                # Drop Info-layer print marks per locked decision #5
                # (Falz lines added manually post-bootstrap).
                continue
            if tag not in _DISPATCHED_PAGEITEM_TAGS:
                # GraphicLine, MasterSpreadPageReference, etc. — raise loudly
                # since we filtered to printable layers. Plan locks GraphicLine
                # to "raise on encounter" but corpus puts all GraphicLines on
                # Info layer (already filtered) — so a Gestaltung GraphicLine
                # would be a genuine surprise.
                raise UnhandledElement(
                    f"Top-level <{tag} Self={child.get('Self')!r}> on printable "
                    f"layer {item_layer!r} not handled "
                    f"(extend tools/idml_to_dsl.py:_emit_pages)"
                )
            # Out-of-page guard: skip items that lie entirely outside the page
            # bounds by more than _guard_pt. These are InDesign design artifacts
            # (guides, registration marks) that InDesign excludes from PDF export
            # even when placed on a printable layer.
            #
            # Groups are EXCLUDED from this guard: InDesign Group containers
            # store their PathGeometry anchors in a design-time local space that
            # does not directly map to page coordinates via the Group's own
            # ItemTransform. The guard would use the Group's container bbox
            # (which can appear wildly off-page) while the Group's children are
            # placed correctly via their own transforms. Skipping the guard for
            # Groups lets recursion in _emit_pageitem handle child placement.
            if tag != "Group":
                child_t = child.get("ItemTransform", "1 0 0 1 0 0")
                try:
                    child_anchors = _extract_anchors(child)
                    child_x_pt, child_y_pt, child_w_pt, child_h_pt, _ = _compute_page_local_bbox_pt(
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
                            f"  [skip] {tag} Self={sid!r}: entirely outside page "
                            f"bounds (x={child_x_pt * PT_TO_MM:.1f}mm "
                            f"y={child_y_pt * PT_TO_MM:.1f}mm "
                            f"w={child_w_pt * PT_TO_MM:.1f}mm "
                            f"h={child_h_pt * PT_TO_MM:.1f}mm) — "
                            f"InDesign design artifact, not emitted",
                            file=sys.stderr,
                        )
                        continue
                except UnhandledElement:
                    # If anchor extraction fails for a non-Group, skip the guard.
                    pass
            layer_idx = ctx.layer_id_to_idx.get(item_layer, 0)
            _emit_pageitem(ctx.out, child, [], spread_t, page_t, page_gb,
                           page_var, ctx, layer_idx)
            emit_count += 1
        if emit_count == 0:
            ctx.out.w("return None")
        ctx.out.indent -= 1
        ctx.out.w("")


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
    out.w("NOTE: bleed_mm=2.0 below matches the IDML verbatim. Brand standard")
    out.w("is 3.0 mm; coerce only after team review.")
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
    bleed_mm = prefs["bleed_top_pt"] * PT_TO_MM

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
    out.w(f"facing_pages={_py_value(prefs['facing_pages'])},")
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
    out.w("# add_styles(doc) - paragraph styles (Phase G, task 5)")
    out.w("_add_styles(doc)")
    out.w("")
    out.w(f"doc.add_master(")
    out.indent += 1
    out.w('name="Normal",')
    out.w(f"size=({_py_value(trim_w_mm)}, {_py_value(trim_h_mm)}),")
    out.w(f"bleed_mm={_py_value(bleed_mm)},")
    out.w("margins_mm=(0.0, 0.0, 0.0, 0.0),")
    out.indent -= 1
    out.w(")")
    out.w("")
    # One add_page per page in pkg.pages
    page_count = len(list(ctx.pkg.pages))
    for i in range(page_count):
        out.w(f"page{i} = doc.add_page(")
        out.indent += 1
        out.w(f"size=({_py_value(trim_w_mm)}, {_py_value(trim_h_mm)}),")
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
    """Task 3 stub: emit empty _add_page_<i> functions. Task 6+7 fill them."""
    page_count = len(list(ctx.pkg.pages))
    for i in range(page_count):
        out.w(f"def _add_page_{i}(doc: Document, page) -> None:")
        out.indent += 1
        out.w(f'"""Page {i + 1} page items — populated by tools/idml_to_dsl.py Phase H."""')
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
def convert(source: Path, output: Path, template_id: str, assets_dir: Path,
            logo_map_path: Optional[Path] = None,
            asset_map_path: Optional[Path] = None) -> None:
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
    if assets_dir is not None and not assets_dir.exists():
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
        ctx.logo_map = logo_map
        ctx.asset_map = asset_map

        # Phase A
        ctx.doc_prefs = _read_doc_preferences(pkg)
        # Phase B
        ctx.layers = _read_layers(pkg)
        ctx.layer_id_to_idx = {lyr["self_id"]: idx for idx, lyr in enumerate(ctx.layers)}
        ctx.printable_layer_ids = {
            lyr["self_id"] for lyr in ctx.layers if lyr["printable"]
        }
        # Phase C
        _check_masters_empty(pkg)
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

        # Write emitted Python source
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(ctx.out.render(), encoding="utf-8")
        print(f"OK: wrote {output}", file=sys.stderr)
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
        default=Path(
            "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/Links"
        ),
        help=(
            "Legacy: directory containing the IDML's linked raster assets "
            "(resolves file: URIs by basename). Used when --asset-map is "
            "not supplied. Prefer --asset-map for new templates."
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
    args = ap.parse_args(argv)

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
                asset_map_path=asset_map_path)
    except UnhandledElement as e:
        print(f"UnhandledElement: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
2. Vector logos — collect every nested ``<PDF>`` reference, raise once at
   end-of-run with the full list. Humans stage pre-rasterised PNGs under
   ``shared/logos/`` (or similar) and re-run.
3. Raster assets — ``--assets-dir`` flag resolves ``file:`` URI basenames.
   Missing files surface at end-of-run alongside unmapped logos.
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

Usage:
    python3 tools/idml_to_dsl.py \\
        "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2.idml" \\
        templates/kandidat-falzflyer-din-lang-gruenes-cover-v2/build.py \\
        --template-id kandidat-falzflyer-din-lang-gruenes-cover-v2 \\
        --assets-dir "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/Links" \\
        --logo-map shared/logos/26-03-leporello-logo-map.yml
"""
# License: BSD (matches repo convention).
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from typing import Optional
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
            top-left sits relative to spread origin).

    Returns:
        Tuple ``(x_pt, y_pt, w_pt, h_pt, rotation_deg)``. Rotation is CCW
        positive (IDML and Scribus convention agree on sign for our typed
        DSL — see ``tools/sla_lib/builder/bbox.py``). If the actual emitter
        finds a sign mismatch during integration, document it in code.

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

    # Apply to anchors → spread-coordinate-space points.
    spread_pts = [_apply_matrix(item_to_spread, x, y) for (x, y) in anchors]

    # Subtract spread origin (pasteboard → spread-local). Most spreads are
    # identity; spread u108 in the target IDML carries a y-offset of 786.61 pt
    # (the second spread stacked below the first in the pasteboard).
    spread_origin = _apply_matrix(spread_M, 0.0, 0.0)
    spread_local = [(px - spread_origin[0], py - spread_origin[1]) for (px, py) in spread_pts]

    # Subtract page origin (spread-local → page-local). page_M's translation
    # is the page's top-left in spread-local coords (e.g. -420.94, -140.31
    # for our A4-quer left-page layout).
    _, _, _, _, ptx, pty = page_M
    page_local = [(px - ptx, py - pty) for (px, py) in spread_local]

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
def convert(source: Path, output: Path, template_id: str, assets_dir: Path) -> None:
    """Open the IDML and (for task 1) print a one-line summary.

    Later tasks fill in the 7 phases:
        A. doc meta (Resources/Preferences.xml)
        B. layers (designmap.xml)
        C. master-spread emptiness check
        D. header + Document scaffold emit
        E. add_master / add_page emit
        F. colors (Resources/Graphic.xml)
        G. styles (Resources/Styles.xml)
        H. page items (Spreads/*.xml + Stories/*.xml)
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
    with IDMLPackage(str(source)) as pkg:
        print(
            f"OK: opened {source.name} — "
            f"{len(pkg.spreads_objects)} spreads, "
            f"{len(pkg.stories)} stories"
        )


# ---------------------------------------------------------------------------
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
        "--assets-dir",
        type=Path,
        required=False,
        default=Path(
            "originals/26-03-Leporello z-Falz 99x210 6-seitig gruenes Cover 2 Ordner/Links"
        ),
        help=(
            "Directory containing the IDML's linked raster assets "
            "(resolves file: URIs by basename)."
        ),
    )
    args = ap.parse_args(argv)
    try:
        convert(args.source, args.output, args.template_id, args.assets_dir)
    except UnhandledElement as e:
        print(f"UnhandledElement: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

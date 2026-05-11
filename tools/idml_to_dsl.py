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
    Mirrors ``sla_to_dsl.py:_py_value``.
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
                  "justification", "applied_font"):
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
    ctx.paragraph_styles = styles

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
            logo_map_path: Optional[Path] = None) -> None:
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
        # Defer this until task 8's logo handling lands. For task 3 we don't
        # actually consume the assets dir yet; only warn.
        print(
            f"WARN: --assets-dir {assets_dir} does not exist (raster assets will fail in task 6)",
            file=sys.stderr,
        )

    with IDMLPackage(str(source)) as pkg:
        ctx = _Ctx(pkg=pkg, template_id=template_id, assets_dir=assets_dir)

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
        # Footer (build_preview / build / main)
        _emit_footer(ctx.out)

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

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

        # Phase D — header
        _emit_header(ctx.out, template_id, source.name)
        # Phase G stub — _add_styles (filled in task 5)
        _emit_styles_stub(ctx.out, ctx)
        # Phase H stub — _add_page_<i> (filled in tasks 6-7)
        _emit_page_stubs(ctx.out, ctx)
        # Phase E — build_template (Document + master + pages)
        _emit_document_scaffold(ctx.out, ctx)
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

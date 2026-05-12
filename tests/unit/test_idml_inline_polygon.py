"""Unit tests for inline <Polygon> (and <Rectangle>/<Oval>) PageItems with
PathGeometry + StrokeColor/FillColor and no <Image>/<PDF> child.

Exercises the code path at tools/idml_to_dsl.py lines ~1347-1380 that emits a
DSL Polygon primitive for hand-drawn vector content (e.g. the yellow wind
turbine on the v2 falzflyer cover, IDML Self='u2b0').

Tests use _emit_pageitem directly with a synthetic lxml Element and a minimal
_Ctx/PythonRepr, keeping no filesystem dependency.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from idml_to_dsl import (  # noqa: E402
    PythonRepr,
    _Ctx,
    _emit_pageitem,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IDENT = "1 0 0 1 0 0"

# page_gb: (y1, x1, y2, x2) in IDML convention (row-major).
# A 100×200 pt page with its top-left at spread origin.
_PAGE_GB: tuple[float, float, float, float] = (0.0, 0.0, 200.0, 100.0)


def _make_ctx(color_map: dict[str, str] | None = None) -> _Ctx:
    """Minimal _Ctx — only color_map is needed for the inline-polygon path."""
    ctx = _Ctx.__new__(_Ctx)  # skip __init__ (dataclass field defaults below)
    ctx.pkg = None
    ctx.template_id = "test"
    ctx.assets_dir = Path("/tmp")
    ctx.out = PythonRepr()
    ctx.doc_prefs = {}
    ctx.layers = []
    ctx.layer_id_to_idx = {}
    ctx.printable_layer_ids = set()
    ctx.color_map = color_map or {}
    ctx.paragraph_style_map = {}
    ctx.paragraph_styles = {}
    ctx.unmapped_logos = []
    ctx.missing_assets = []
    ctx.logo_map = {}
    ctx.asset_map = {}
    ctx.unmapped_assets = []
    return ctx


def _polygon_element(
    self_id: str = "testpoly",
    *,
    stroke_color: str | None = None,
    fill_color: str | None = None,
    stroke_weight: str | None = None,
    item_transform: str = IDENT,
    anchors: list[tuple[float, float]] | None = None,
) -> etree._Element:
    """Build a synthetic <Polygon> element with a simple PathGeometry."""
    if anchors is None:
        # 20×10 pt rectangle starting at spread origin
        anchors = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)]

    attrs: dict[str, str] = {"Self": self_id, "ItemTransform": item_transform}
    if stroke_color:
        attrs["StrokeColor"] = stroke_color
    if fill_color:
        attrs["FillColor"] = fill_color
    if stroke_weight:
        attrs["StrokeWeight"] = stroke_weight

    poly = etree.Element("Polygon", **attrs)
    props = etree.SubElement(poly, "Properties")
    pg = etree.SubElement(props, "PathGeometry")
    gpt = etree.SubElement(pg, "GeometryPathType", PathOpen="false")
    ppa = etree.SubElement(gpt, "PathPointArray")
    for x, y in anchors:
        etree.SubElement(
            ppa,
            "PathPointType",
            Anchor=f"{x} {y}",
            LeftDirection=f"{x} {y}",
            RightDirection=f"{x} {y}",
        )
    return poly


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_inline_polygon_stroke_only_emits_polygon():
    """A <Polygon> with only StrokeColor (no Fill, no Image) is emitted as a
    DSL Polygon with line_color and no fill kwarg (fill='None')."""
    color_map = {"Color/C=0 M=0 Y=100 K=0": "Gelb"}
    ctx = _make_ctx(color_map)

    poly = _polygon_element(
        self_id="u2b0",
        stroke_color="Color/C=0 M=0 Y=100 K=0",
        stroke_weight="4.203916263369494",
        item_transform="1 0 0 1 10 20",
    )

    _emit_pageitem(
        ctx.out,
        poly,
        ancestor_transforms=[],
        spread_t=IDENT,
        page_t=IDENT,
        page_gb=_PAGE_GB,
        page_var="page0",
        ctx=ctx,
        layer_idx=0,
    )

    code = ctx.out.render()
    assert "Polygon(" in code, f"Expected Polygon() call in output:\n{code}"
    assert "anname='u2b0'" in code
    assert "line_color='Gelb'" in code
    assert "line_width_pt=4.203916263369494" in code
    # fill is explicitly set to 'None' when no FillColor present
    assert "fill='None'" in code


def test_inline_polygon_fill_only_emits_polygon():
    """A <Polygon> with only FillColor (no Stroke, no Image) is emitted as a
    DSL Polygon with fill kwarg and no line_color."""
    color_map = {"Color/C=85 M=35 Y=95 K=10": "Dunkelgrün"}
    ctx = _make_ctx(color_map)

    poly = _polygon_element(
        self_id="pfill",
        fill_color="Color/C=85 M=35 Y=95 K=10",
    )

    _emit_pageitem(
        ctx.out,
        poly,
        ancestor_transforms=[],
        spread_t=IDENT,
        page_t=IDENT,
        page_gb=_PAGE_GB,
        page_var="page0",
        ctx=ctx,
        layer_idx=1,
    )

    code = ctx.out.render()
    assert "Polygon(" in code
    assert "anname='pfill'" in code
    assert "fill='Dunkelgrün'" in code
    assert "line_color" not in code


def test_inline_rectangle_without_image_emits_polygon():
    """A <Rectangle> with FillColor and no <Image> child falls through to the
    same Polygon emit path as a raw <Polygon>."""
    color_map = {"Color/C=0 M=100 Y=0 K=0": "Magenta"}
    ctx = _make_ctx(color_map)

    # Build a <Rectangle> element (same structure, different tag)
    rect = etree.Element(
        "Rectangle",
        Self="rect1",
        ItemTransform=IDENT,
        FillColor="Color/C=0 M=100 Y=0 K=0",
    )
    props = etree.SubElement(rect, "Properties")
    pg = etree.SubElement(props, "PathGeometry")
    gpt = etree.SubElement(pg, "GeometryPathType", PathOpen="false")
    ppa = etree.SubElement(gpt, "PathPointArray")
    for x, y in [(0.0, 0.0), (30.0, 0.0), (30.0, 15.0), (0.0, 15.0)]:
        etree.SubElement(ppa, "PathPointType", Anchor=f"{x} {y}",
                         LeftDirection=f"{x} {y}", RightDirection=f"{x} {y}")

    _emit_pageitem(
        ctx.out,
        rect,
        ancestor_transforms=[],
        spread_t=IDENT,
        page_t=IDENT,
        page_gb=_PAGE_GB,
        page_var="page0",
        ctx=ctx,
        layer_idx=0,
    )

    code = ctx.out.render()
    assert "Polygon(" in code
    assert "anname='rect1'" in code
    assert "fill='Magenta'" in code


def test_inline_oval_emits_polygon_with_ellipse_shape():
    """A <Oval> with FillColor and no Image emits Polygon with shape='ellipse'."""
    color_map = {"Color/C=69 M=0 Y=100 K=0": "Hellgrün"}
    ctx = _make_ctx(color_map)

    oval = etree.Element(
        "Oval",
        Self="oval1",
        ItemTransform=IDENT,
        FillColor="Color/C=69 M=0 Y=100 K=0",
    )
    props = etree.SubElement(oval, "Properties")
    pg = etree.SubElement(props, "PathGeometry")
    gpt = etree.SubElement(pg, "GeometryPathType", PathOpen="false")
    ppa = etree.SubElement(gpt, "PathPointArray")
    for x, y in [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)]:
        etree.SubElement(ppa, "PathPointType", Anchor=f"{x} {y}",
                         LeftDirection=f"{x} {y}", RightDirection=f"{x} {y}")

    _emit_pageitem(
        ctx.out,
        oval,
        ancestor_transforms=[],
        spread_t=IDENT,
        page_t=IDENT,
        page_gb=_PAGE_GB,
        page_var="page0",
        ctx=ctx,
        layer_idx=0,
    )

    code = ctx.out.render()
    assert "Polygon(" in code
    assert "anname='oval1'" in code
    assert "shape='ellipse'" in code


def test_inline_polygon_cmyk_yellow_maps_to_gelb():
    """The canonical turbine case: StrokeColor CMYK 0,0,100,0 maps to 'Gelb'."""
    # The color_map key used by the converter is the Self attribute of the
    # Color element, which equals the display name 'Color/C=0 M=0 Y=100 K=0'.
    color_map = {"Color/C=0 M=0 Y=100 K=0": "Gelb"}
    ctx = _make_ctx(color_map)

    poly = _polygon_element(
        self_id="u2b0_canonical",
        stroke_color="Color/C=0 M=0 Y=100 K=0",
        stroke_weight="4.203916263369494",
    )

    _emit_pageitem(
        ctx.out,
        poly,
        ancestor_transforms=[],
        spread_t=IDENT,
        page_t=IDENT,
        page_gb=_PAGE_GB,
        page_var="page0",
        ctx=ctx,
        layer_idx=0,
    )

    code = ctx.out.render()
    assert "line_color='Gelb'" in code, (
        f"Expected 'Gelb' (brand name for CMYK 0,0,100,0) in output:\n{code}"
    )


def test_inline_polygon_ancestor_transform_cascades():
    """A <Polygon> inside a Group inherits the group's ItemTransform via
    ancestor_transforms, shifting position in page-local coordinates."""
    color_map = {"Color/C=0 M=0 Y=100 K=0": "Gelb"}
    ctx = _make_ctx(color_map)

    # Polygon anchors at (0,0)→(20,10) in its own local space.
    poly = _polygon_element(
        self_id="child_poly",
        stroke_color="Color/C=0 M=0 Y=100 K=0",
        item_transform=IDENT,  # no extra shift on the polygon itself
    )

    # Group ItemTransform shifts by (50, 30) — ancestor_transforms are
    # innermost-first, so just one entry here.
    group_t = "1 0 0 1 50 30"

    _emit_pageitem(
        ctx.out,
        poly,
        ancestor_transforms=[group_t],
        spread_t=IDENT,
        page_t=IDENT,
        page_gb=_PAGE_GB,
        page_var="page0",
        ctx=ctx,
        layer_idx=0,
    )

    code = ctx.out.render()
    assert "Polygon(" in code
    # x should be around 50pt * PT_TO_MM ≈ 17.64mm
    import re
    m = re.search(r"x_mm=([\d.]+)", code)
    assert m is not None, f"No x_mm in output:\n{code}"
    x_val = float(m.group(1))
    PT_TO_MM = 25.4 / 72.0
    assert x_val == pytest.approx(50.0 * PT_TO_MM, rel=1e-3)

"""Unit tests for the yellow squiggle motif — colour fix + re-anchoring.

Covers:
  * the complex-Polygon PolyLine branch routing a FillColor-bearing squiggle
    to a yellow FILL (PCOLOR) and no stroke — not a black 1pt outline;
  * ``_is_open_polygon`` / ``_page_index_from_var`` helpers;
  * ``_associate_squiggle_to_word`` / ``_words_in_frame`` word-binding logic;
  * the squiggle_realign playbook's word location + shift computation.
"""
from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from idml_to_dsl import (  # noqa: E402
    PythonRepr,
    _Ctx,
    _associate_squiggle_to_word,
    _emit_pageitem,
    _is_open_polygon,
    _page_index_from_var,
    _words_in_frame,
)

IDENT = "1 0 0 1 0 0"
_PAGE_GB: tuple[float, float, float, float] = (0.0, 0.0, 400.0, 300.0)


def _make_ctx(color_map: dict[str, str] | None = None) -> _Ctx:
    ctx = _Ctx.__new__(_Ctx)
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
    ctx.emitted_self_ids = set()
    ctx.skipped_with_reason = []
    ctx.squiggle_records = []
    ctx.textframe_records = []
    return ctx


def _squiggle_polygon(
    self_id: str = "u11e3",
    *,
    fill_color: str | None = "Color/Yellow",
    stroke_color: str | None = None,
    path_open: bool = False,
) -> etree._Element:
    """Build a synthetic bezier (complex) closed Polygon — the squiggle shape."""
    attrs: dict[str, str] = {"Self": self_id, "ItemTransform": IDENT}
    if fill_color:
        attrs["FillColor"] = fill_color
    if stroke_color:
        attrs["StrokeColor"] = stroke_color
    poly = etree.Element("Polygon", **attrs)
    props = etree.SubElement(poly, "Properties")
    pg = etree.SubElement(props, "PathGeometry")
    gpt = etree.SubElement(
        pg, "GeometryPathType",
        PathOpen="true" if path_open else "false",
    )
    ppa = etree.SubElement(gpt, "PathPointArray")
    # Bezier points (LeftDirection != Anchor) so _is_complex_polygon is True.
    pts = [
        (0.0, 0.0, -2.0, -1.0, 2.0, 1.0),
        (40.0, 0.0, 38.0, -1.0, 42.0, 1.0),
        (40.0, 6.0, 42.0, 5.0, 38.0, 7.0),
        (0.0, 6.0, 2.0, 5.0, -2.0, 7.0),
    ]
    for ax, ay, lx, ly, rx, ry in pts:
        etree.SubElement(
            ppa, "PathPointType",
            Anchor=f"{ax} {ay}",
            LeftDirection=f"{lx} {ly}",
            RightDirection=f"{rx} {ry}",
        )
    return poly


# ---------------------------------------------------------------------------
# Part A — colour fix
# ---------------------------------------------------------------------------
def test_squiggle_emits_yellow_fill_no_black_stroke():
    """A closed bezier Polygon filled with Color/Yellow emits as a PolyLine
    with fill='Gelb' and line_color='None' — never a black outline."""
    ctx = _make_ctx({"Color/Yellow": "Gelb"})
    poly = _squiggle_polygon(self_id="u11e3", fill_color="Color/Yellow")
    _emit_pageitem(
        ctx.out, poly, ancestor_transforms=[], spread_t=IDENT,
        page_t=IDENT, page_gb=_PAGE_GB, page_var="page1", ctx=ctx, layer_idx=0,
    )
    code = ctx.out.render()
    assert "PolyLine(" in code
    assert "anname='u11e3'" in code
    assert "fill='Gelb'" in code
    assert "line_color='None'" in code
    assert "line_color='Black'" not in code


def test_squiggle_records_anchor_metadata():
    """A yellow closed Polygon is recorded for re-anchoring with its page."""
    ctx = _make_ctx({"Color/Yellow": "Gelb"})
    poly = _squiggle_polygon(self_id="u11e3", fill_color="Color/Yellow")
    _emit_pageitem(
        ctx.out, poly, ancestor_transforms=[], spread_t=IDENT,
        page_t=IDENT, page_gb=_PAGE_GB, page_var="page2", ctx=ctx, layer_idx=0,
    )
    assert len(ctx.squiggle_records) == 1
    rec = ctx.squiggle_records[0]
    assert rec["anname"] == "u11e3"
    assert rec["page"] == 2
    assert rec["w_mm"] > 0 and rec["h_mm"] > 0


def test_stroked_complex_polygon_keeps_stroke_no_fill():
    """A complex Polygon with a real StrokeColor and no FillColor stays a
    stroked outline — line_color set, no fill kwarg, NOT recorded as squiggle."""
    ctx = _make_ctx({"Color/C=0 M=0 Y=100 K=0": "Gelb"})
    poly = _squiggle_polygon(
        self_id="u2b0", fill_color=None,
        stroke_color="Color/C=0 M=0 Y=100 K=0",
    )
    poly.set("StrokeWeight", "2.16")
    _emit_pageitem(
        ctx.out, poly, ancestor_transforms=[], spread_t=IDENT,
        page_t=IDENT, page_gb=_PAGE_GB, page_var="page0", ctx=ctx, layer_idx=0,
    )
    code = ctx.out.render()
    assert "PolyLine(" in code
    assert "line_color='Gelb'" in code
    assert "fill=" not in code
    assert ctx.squiggle_records == []


def test_named_yellow_swatch_is_not_a_squiggle():
    """A FillColor that is the NAMED C=0 M=0 Y=100 K=0 swatch (not the builtin
    Color/Yellow) is a normal yellow shape, not the brush motif — not recorded."""
    ctx = _make_ctx({"Color/C=0 M=0 Y=100 K=0": "Gelb"})
    poly = _squiggle_polygon(
        self_id="ushape", fill_color="Color/C=0 M=0 Y=100 K=0",
    )
    _emit_pageitem(
        ctx.out, poly, ancestor_transforms=[], spread_t=IDENT,
        page_t=IDENT, page_gb=_PAGE_GB, page_var="page0", ctx=ctx, layer_idx=0,
    )
    assert ctx.squiggle_records == []
    # Still emits the yellow fill — colour fix applies to any FillColor.
    assert "fill='Gelb'" in ctx.out.render()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def test_is_open_polygon():
    closed = _squiggle_polygon(path_open=False)
    open_p = _squiggle_polygon(path_open=True)
    assert _is_open_polygon(closed) is False
    assert _is_open_polygon(open_p) is True


def test_page_index_from_var():
    assert _page_index_from_var("page0") == 0
    assert _page_index_from_var("page12") == 12
    assert _page_index_from_var("page") == 0


# ---------------------------------------------------------------------------
# Part B — word association
# ---------------------------------------------------------------------------
def _word(text, x0, top, x1, bottom):
    return {"text": text, "x0": x0, "top": top, "x1": x1, "bottom": bottom}


def test_words_in_frame_filters_by_center():
    page_words = [
        _word("inside", 10, 10, 30, 22),
        _word("outside", 200, 200, 230, 212),
    ]
    got = _words_in_frame(page_words, (0.0, 0.0, 100.0, 100.0))
    assert [w["text"] for w in got] == ["inside"]


def test_associate_squiggle_picks_leftmost_word_on_band():
    # A squiggle band underlining the second text line.
    frame_words = [
        _word("first", 10, 5, 50, 17),     # line 1
        _word("second", 55, 5, 95, 17),    # line 1
        _word("Lia", 10, 25, 30, 37),      # line 2
        _word("vellam", 35, 25, 80, 37),   # line 2
    ]
    # Squiggle band sits just under line 2's words.
    sq_box = (8.0, 35.0, 82.0, 39.0)
    anchor = _associate_squiggle_to_word(sq_box, frame_words)
    assert anchor is not None
    assert anchor["text"] == "Lia"          # leftmost on the matched line
    assert anchor["index"] == 2             # ordinal in frame_words


def test_associate_squiggle_returns_none_when_no_overlap():
    frame_words = [_word("far", 500, 500, 540, 512)]
    assert _associate_squiggle_to_word((0.0, 0.0, 50.0, 4.0), frame_words) is None


# ---------------------------------------------------------------------------
# Playbook — squiggle_realign
# ---------------------------------------------------------------------------
def test_playbook_find_preview_word_by_ordinal():
    from playbooks.squiggle_realign import _find_preview_word

    frame_box = (0.0, 0.0, 200.0, 200.0)
    page_words = [
        _word("Lia", 10, 100, 30, 112),
        _word("vellam", 35, 100, 80, 112),
        _word("Lia", 10, 150, 30, 162),   # repeat — ordinal disambiguates
    ]
    # word_index 2 → the SECOND "Lia".
    w = _find_preview_word(page_words, frame_box, "Lia", 2)
    assert w is not None and w["top"] == 150


def test_playbook_shift_squiggle(tmp_path):
    from playbooks.squiggle_realign import _shift_squiggle

    build = tmp_path / "build.py"
    build.write_text(
        "    page1.add(PolyLine(\n"
        "        x_mm=14.8,\n"
        "        y_mm=89.8,\n"
        "        w_mm=19.2,\n"
        "        h_mm=1.0,\n"
        "        sla_path='M0 0 Z',\n"
        "        fill='Gelb',\n"
        "        line_color='None',\n"
        "        anname='u11e3',\n"
        "        layer=0,\n"
        "    ))\n"
    )
    wrote, msg = _shift_squiggle(build, "u11e3", -1.5, 2.0, "track word")
    assert wrote is True
    text = build.read_text()
    assert "x_mm=13.3" in text
    assert "y_mm=91.8" in text
    assert "squiggle_realign.py" in text  # provenance marker


def test_playbook_no_anchors_file(tmp_path):
    from playbooks.squiggle_realign import apply

    (tmp_path / "templates" / "demo").mkdir(parents=True)
    n, log = apply("demo", tmp_path, dry_run=True)
    assert n == 0
    assert "no squiggle_anchors.yml" in log[0]

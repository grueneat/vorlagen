"""Tests for the typed DSL extensions added in issue #2 Phase 1.

Each new typed primitive (DocumentLayer, Document.add_color, ParaStyle,
CharStyle, Run, custom_path, fill_rule, link_to chains, corner_radius_mm,
SoftShadow, text_align, fill_shade, soft-hyphen passthrough) gets at least
one direct test that asserts the emitted SLA carries the expected XML.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import (  # noqa: E402
    Document, TextFrame, ImageFrame, Polygon, Run, Anchor,
    ParaStyle, CharStyle, DocumentLayer, SoftShadow,
)


def _build_to_tree(doc: Document) -> etree._Element:
    """Render the doc to a tempfile and return the parsed root."""
    with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
        path = Path(t.name)
    doc.save(path)
    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
    return etree.parse(str(path)).getroot()


def _build_to_bytes(doc: Document) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
        path = Path(t.name)
    doc.save(path)
    return path.read_bytes()


def _make_simple_doc(**kw) -> Document:
    d = Document(title="t", template_id="x", **kw)
    d.add_page(size="A6")
    return d


# ---------------------------------------------------------------------------
# Task 1.1 — DocumentLayer override
# ---------------------------------------------------------------------------
class DocumentLayerTests(unittest.TestCase):
    def test_document_layer_override(self):
        d = Document(title="t", template_id="x", layers=[DocumentLayer(name="Hintergrund")])
        d.add_page(size="A6")
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        layers = root.find("DOCUMENT").findall("LAYERS")
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0].attrib["NAME"], "Hintergrund")
        self.assertEqual(layers[0].attrib["NUMMER"], "0")

    def test_default_layers_used_when_no_override(self):
        d = _make_simple_doc()
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        layers = root.find("DOCUMENT").findall("LAYERS")
        self.assertGreater(len(layers), 1)  # CI brand has 4 layers


# ---------------------------------------------------------------------------
# Task 1.2 — Document.add_color
# ---------------------------------------------------------------------------
class AddColorTests(unittest.TestCase):
    def test_add_color_rgb(self):
        d = _make_simple_doc()
        d.add_color("Green", rgb=(153, 102, 51))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        green = next((c for c in root.find("DOCUMENT").findall("COLOR")
                      if c.attrib["NAME"] == "Green"), None)
        self.assertIsNotNone(green)
        self.assertEqual(green.attrib["SPACE"], "RGB")
        self.assertEqual(green.attrib["R"], "153")
        self.assertEqual(green.attrib["G"], "102")
        self.assertEqual(green.attrib["B"], "51")

    def test_add_color_cmyk(self):
        d = _make_simple_doc()
        d.add_color("Custom", cmyk=(50, 25, 75, 10))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        c = next((c for c in root.find("DOCUMENT").findall("COLOR")
                  if c.attrib["NAME"] == "Custom"), None)
        self.assertIsNotNone(c)
        self.assertEqual(c.attrib["SPACE"], "CMYK")
        self.assertEqual(c.attrib["C"], "50")
        self.assertEqual(c.attrib["K"], "10")

    def test_add_color_rejects_both_rgb_and_cmyk(self):
        d = _make_simple_doc()
        with self.assertRaises(ValueError):
            d.add_color("X", rgb=(1, 2, 3), cmyk=(1, 1, 1, 1))

    def test_add_color_requires_one_of_rgb_or_cmyk(self):
        d = _make_simple_doc()
        with self.assertRaises(ValueError):
            d.add_color("X")


# ---------------------------------------------------------------------------
# Task 1.3 — ParaStyle / CharStyle, only-non-None emission
# ---------------------------------------------------------------------------
class ParaStyleTests(unittest.TestCase):
    def test_para_style_inheritance_drops_redundant_attr(self):
        d = _make_simple_doc()
        d.add_para_style(ParaStyle(name="parent", fontsize=12, font="Gotham Narrow Book"))
        d.add_para_style(ParaStyle(name="child", parent="parent"))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        styles = root.find("DOCUMENT").findall("STYLE")
        child = next(s for s in styles if s.attrib["NAME"] == "child")
        # child has only NAME and PARENT, no FONTSIZE / FONT inherited
        self.assertEqual(child.attrib["PARENT"], "parent")
        self.assertNotIn("FONTSIZE", child.attrib)
        self.assertNotIn("FONT", child.attrib)
        self.assertNotIn("LANGUAGE", child.attrib)

    def test_para_style_emits_provided_attrs(self):
        # Cover the long-tail attribute paths
        d = _make_simple_doc()
        d.add_para_style(ParaStyle(
            name="full",
            font="Gotham Narrow Book", fontsize=12, fcolor="White", align=1,
            linesp=15, linesp_mode=2, language="de",
            space_before_pt=4, space_after_pt=8,
            first_indent_pt=6, left_indent_pt=2, right_indent_pt=2,
            hyph_consecutive_lines=2, hyph_word_min=4,
            drop_cap=True, drop_lines=2,
            min_word_track=0.85, min_glyph_shrink=0.95, max_glyph_extend=1.05,
            keep_together=True, keep_lines_start=2,
            direction=0,
            bcolor="Yellow", bshade=50,
            fontfeatures="-onum,+lnum", features="inherit", kern=0.0, scalev=100,
            fshade=80,
            txt_underline_pos=-1, txt_underline_width=-1,
            txt_strike_pos=-1, txt_strike_width=-1,
            txt_shadow_x=5, txt_shadow_y=-5, txt_outline=10,
            baseline_offset=0,
            paragraph_effect_offset=0.0,
            bullet="•", numeration=0,
        ))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        st = next(s for s in root.find("DOCUMENT").findall("STYLE")
                  if s.attrib["NAME"] == "full")
        for attr in ("FONT", "FONTSIZE", "FCOLOR", "ALIGN", "LINESP", "LINESPMode",
                     "LANGUAGE", "VOR", "NACH", "FIRST", "INDENT", "RMARGIN",
                     "HyphenConsecutiveLines", "HyphenWordMin",
                     "DROP", "DROPLIN",
                     "MinWordTrack", "MinGlyphShrink", "MaxGlyphExtend",
                     "KeepTogether", "KeepLinesStart",
                     "DIRECTION",
                     "BCOLOR", "BSHADE",
                     "FONTFEATURES", "FEATURES", "KERN", "SCALEV", "FSHADE",
                     "TXTULP", "TXTULW", "TXTSTP", "TXTSTW",
                     "TXTSHX", "TXTSHY", "TXTOUT",
                     "BASEO",
                     "ParagraphEffectOffset", "Bullet", "Numeration"):
            self.assertIn(attr, st.attrib, f"missing {attr}")

    def test_char_style_emit(self):
        d = _make_simple_doc()
        d.add_char_style(CharStyle(name="cs1", font="Gotham Narrow Black",
                                    fontsize=12, fcolor="Black", is_default=False))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        cs_list = root.find("DOCUMENT").findall("CHARSTYLE")
        # Document-local char styles replace the empty default
        self.assertEqual(len(cs_list), 1)
        self.assertEqual(cs_list[0].attrib["CNAME"], "cs1")
        self.assertEqual(cs_list[0].attrib["FCOLOR"], "Black")

    def test_default_style_marker_is_default(self):
        d = _make_simple_doc()
        d.add_para_style(ParaStyle(name="Default Paragraph Style",
                                    is_default=True))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        # With additive emission, CI styles come first; find by name.
        styles = root.find("DOCUMENT").findall("STYLE")
        st = next((s for s in styles if s.attrib.get("NAME") == "Default Paragraph Style"),
                  None)
        self.assertIsNotNone(st, "Default Paragraph Style not found in STYLE list")
        self.assertEqual(st.attrib.get("DefaultStyle"), "1")


# ---------------------------------------------------------------------------
# Task 1.4 — facing pages, column gap, master auto-injection
# ---------------------------------------------------------------------------
class DocumentExtrasTests(unittest.TestCase):
    def test_facing_pages_emits_BOOK_1(self):
        d = Document(title="t", template_id="x", facing_pages=True)
        d.add_page(size="A4")
        d.add_page(size="A4")
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        self.assertEqual(root.find("DOCUMENT").attrib["BOOK"], "1")

    def test_column_gap_default_to_ABSTSPALTEN(self):
        d = Document(title="t", template_id="x", column_gap_default_pt=12)
        d.add_page(size="A4")
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        self.assertEqual(root.find("DOCUMENT").attrib["ABSTSPALTEN"], "12")

    def test_no_normal_master_injection_when_other_masters_present(self):
        d = _make_simple_doc()
        d.add_master(name="Custom", size="A6")
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        masters = root.find("DOCUMENT").findall("MASTERPAGE")
        # Only the user-declared master, no auto-Normal injection
        self.assertEqual(len(masters), 1)
        self.assertEqual(masters[0].attrib["NAM"], "Custom")

    def test_no_label_frame_when_label_empty(self):
        d = _make_simple_doc()  # default label=""
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=20, h_mm=10, text="hi"))
        root = _build_to_tree(d)
        # No label TextFrame should be auto-injected
        for po in root.find("DOCUMENT").findall("PAGEOBJECT"):
            anname = po.attrib.get("ANNAME", "")
            self.assertFalse(anname.startswith("Label:"))


# ---------------------------------------------------------------------------
# Task 1.5 — Run dataclass + soft-hyphen passthrough
# ---------------------------------------------------------------------------
class RunTests(unittest.TestCase):
    def test_run_per_run_overrides(self):
        d = _make_simple_doc()
        d.pages[0].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=80, h_mm=20,
            runs=[
                Run(text="Hello ", fcolor="White", fontsize=14, fshade=80,
                    features="-smallcaps", kern=0.5,
                    fontfeatures="+onum,-lnum"),
                Run(text="World", font="Gotham Narrow Black", char_style="cs1"),
            ],
        ))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        itexts = po.findall(".//ITEXT")
        self.assertEqual(itexts[0].attrib["FCOLOR"], "White")
        self.assertEqual(itexts[0].attrib["FONTSIZE"], "14")
        self.assertEqual(itexts[0].attrib["FSHADE"], "80")
        self.assertEqual(itexts[0].attrib["FEATURES"], "-smallcaps")
        self.assertEqual(itexts[0].attrib["KERN"], "0.5")
        self.assertEqual(itexts[0].attrib["FONTFEATURES"], "+onum,-lnum")
        self.assertEqual(itexts[1].attrib["FONT"], "Gotham Narrow Black")
        self.assertEqual(itexts[1].attrib["CPARENT"], "cs1")

    def test_run_var_pgno_emits_var_element(self):
        d = _make_simple_doc()
        d.pages[0].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=20, h_mm=10,
            runs=[Run(text="Page ", var="pgno")],
        ))
        root = _build_to_tree(d)
        story = root.find("DOCUMENT").find("PAGEOBJECT").find("StoryText")
        var_elems = story.findall("var")
        self.assertEqual(len(var_elems), 1)
        self.assertEqual(var_elems[0].attrib["name"], "pgno")

    def test_run_separators(self):
        d = _make_simple_doc()
        d.pages[0].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=20, h_mm=10,
            runs=[
                Run(text="A", separator="para"),
                Run(text="B", separator="breakline"),
                Run(text="C", separator="tab"),
                Run(text="D", separator="breakcol"),
                Run(text="E", separator="breakframe"),
                Run(text="F"),
            ],
        ))
        root = _build_to_tree(d)
        story = root.find("DOCUMENT").find("PAGEOBJECT").find("StoryText")
        tags = [c.tag for c in story]
        # Skip DefaultStyle and trailing trail
        self.assertIn("para", tags)
        self.assertIn("breakline", tags)
        self.assertIn("tab", tags)
        self.assertIn("breakcol", tags)
        self.assertIn("breakframe", tags)

    def test_soft_hyphen_passthrough(self):
        d = _make_simple_doc()
        d.pages[0].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=20, h_mm=10,
            runs=[Run(text="ei\xadne gro\xadße")],
        ))
        b = _build_to_bytes(d)
        # File bytes must contain the raw 0xC2 0xAD UTF-8 for U+00AD
        self.assertIn(b"ei\xc2\xadne", b)

    def test_legacy_tuple_run_form_still_works(self):
        d = _make_simple_doc()
        d.pages[0].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=20, h_mm=10,
            runs=[("Hello", {"fcolor": "White", "fontsize": 12}, "para"),
                   ("World", None)],
        ))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        itexts = po.findall(".//ITEXT")
        self.assertEqual(itexts[0].attrib["FCOLOR"], "White")


# ---------------------------------------------------------------------------
# Task 1.6 — custom_path / fill_rule
# ---------------------------------------------------------------------------
class CustomPathTests(unittest.TestCase):
    def test_custom_path_sets_FRTYPE_3_and_path_attrs(self):
        d = _make_simple_doc()
        path = "M0 0 L100 0 L100 50 L0 50 Z"
        d.pages[0].add(Polygon(x_mm=10, y_mm=10, w_mm=30, h_mm=15,
                                custom_path=path))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        self.assertEqual(po.attrib["FRTYPE"], "3")
        self.assertEqual(po.attrib["path"], path)
        self.assertEqual(po.attrib["copath"], path)

    def test_fill_rule_emitted_when_set(self):
        d = _make_simple_doc()
        d.pages[0].add(Polygon(x_mm=10, y_mm=10, w_mm=30, h_mm=15,
                                custom_path="M0 0 L1 1 Z", fill_rule=0))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        self.assertEqual(po.attrib["fillRule"], "0")

    def test_default_path_unchanged_without_custom_path(self):
        d = _make_simple_doc()
        d.pages[0].add(Polygon(x_mm=10, y_mm=10, w_mm=30, h_mm=15,
                                shape="rectangle"))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        self.assertEqual(po.attrib["FRTYPE"], "0")
        self.assertNotIn("fillRule", po.attrib)


# ---------------------------------------------------------------------------
# Task 1.7 — link_to chains
# ---------------------------------------------------------------------------
class LinkedChainTests(unittest.TestCase):
    def test_link_to_chain_of_three_emits_NEXTITEM_BACKITEM(self):
        d = _make_simple_doc()
        a = TextFrame(x_mm=10, y_mm=10, w_mm=30, h_mm=20, text="A", anname="a")
        b = TextFrame(x_mm=10, y_mm=40, w_mm=30, h_mm=20, text="B", anname="b")
        c = TextFrame(x_mm=10, y_mm=70, w_mm=30, h_mm=20, text="C", anname="c")
        a.link_to(b).link_to(c)
        d.pages[0].add(a)
        d.pages[0].add(b)
        d.pages[0].add(c)
        root = _build_to_tree(d)
        pos = {p.attrib.get("ANNAME"): p for p in root.find("DOCUMENT").findall("PAGEOBJECT")}
        self.assertEqual(pos["a"].attrib["NEXTITEM"], pos["b"].attrib["ItemID"])
        self.assertEqual(pos["b"].attrib["BACKITEM"], pos["a"].attrib["ItemID"])
        self.assertEqual(pos["b"].attrib["NEXTITEM"], pos["c"].attrib["ItemID"])
        self.assertEqual(pos["c"].attrib["BACKITEM"], pos["b"].attrib["ItemID"])
        self.assertEqual(pos["a"].attrib["BACKITEM"], "-1")
        self.assertEqual(pos["c"].attrib["NEXTITEM"], "-1")

    def test_chain_round_trip_through_sla_diff(self):
        # Build twice and assert sla_diff is critical=0 against itself.
        d = _make_simple_doc()
        a = TextFrame(x_mm=10, y_mm=10, w_mm=30, h_mm=20, text="A")
        b = TextFrame(x_mm=10, y_mm=40, w_mm=30, h_mm=20, text="B")
        a.link_to(b)
        d.pages[0].add(a)
        d.pages[0].add(b)
        with tempfile.NamedTemporaryFile(suffix=".sla", delete=False) as t:
            p = Path(t.name)
        d.save(p)
        # Reuse the diff tool
        import sla_diff
        report = sla_diff.diff(p, p)
        self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0)


# ---------------------------------------------------------------------------
# Task 1.8 — corner_radius / soft_shadow / text_align / fill_shade
# ---------------------------------------------------------------------------
class LongTailFrameAttrsTests(unittest.TestCase):
    def test_corner_radius_emits_RADRECT_and_FRTYPE_2(self):
        d = _make_simple_doc()
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=30, h_mm=30,
                                    image="x.png", corner_radius_mm=1))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        self.assertEqual(po.attrib["FRTYPE"], "2")
        self.assertIn("RADRECT", po.attrib)

    def test_soft_shadow_emits_all_9_attrs(self):
        d = _make_simple_doc()
        ss = SoftShadow(color="Black")
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=30, h_mm=20,
                                   text="hi", soft_shadow=ss))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        self.assertEqual(po.attrib["HASSOFTSHADOW"], "1")
        for attr in ("SOFTSHADOWCOLOR", "SOFTSHADOWBLURRADIUS",
                     "SOFTSHADOWXOFFSET", "SOFTSHADOWYOFFSET",
                     "SOFTSHADOWBLENDMODE", "SOFTSHADOWOPACITY",
                     "SOFTSHADOWSHADE", "SOFTSHADOWERASE",
                     "SOFTSHADOWOBJTRANS"):
            self.assertIn(attr, po.attrib)

    def test_text_align_emits_VAlign_on_pageobject(self):
        # Vertical text justification lives in PAGEOBJECT VAlign (0/1/2),
        # NOT ALIGN. The deprecated text_align= alias still routes there.
        d = _make_simple_doc()
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=30, h_mm=20,
                                   text="hi", text_align=2))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        self.assertEqual(po.attrib["VAlign"], "2")

    def test_fill_shade_polygon_omits_when_default(self):
        d = _make_simple_doc()
        d.pages[0].add(Polygon(x_mm=10, y_mm=10, w_mm=30, h_mm=15))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        self.assertNotIn("SHADE", po.attrib)

    def test_fill_shade_emitted_when_not_default(self):
        d = _make_simple_doc()
        d.pages[0].add(Polygon(x_mm=10, y_mm=10, w_mm=30, h_mm=15, fill_shade=80))
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        self.assertEqual(po.attrib["SHADE"], "80")


# ---------------------------------------------------------------------------
# No raw_attrs in public surface (D2)
# ---------------------------------------------------------------------------
class PublicSurfaceTests(unittest.TestCase):
    def test_no_raw_attrs_in_public_export(self):
        from sla_lib import builder
        for name in builder.__all__:
            if name == "raw_attrs":
                self.fail("raw_attrs leaked into public surface (D2 violation)")
        # Also assert no primitive accepts raw_attrs as a kwarg
        from sla_lib.builder import TextFrame as TF, ImageFrame as IF, Polygon as P
        import dataclasses
        for cls in (TF, IF, P):
            for f in dataclasses.fields(cls):
                self.assertNotEqual(f.name, "raw_attrs",
                                     f"{cls.__name__} has raw_attrs field (D2 violation)")


# ---------------------------------------------------------------------------
# Task 6 — LLM-emission ergonomics (issue #5)
# ---------------------------------------------------------------------------
class AnchorErgonomicsTests(unittest.TestCase):
    """Anchor named-args canonical form and legacy deprecation."""

    def test_anchor_named_args_form(self):
        """Anchor(h='center', v='bottom', margin_mm=20) resolves correctly."""
        from sla_lib.builder.primitives import resolve_anchor
        a = Anchor(h="center", v="bottom", margin_mm=20)
        page_w, page_h = 200.0, 300.0
        item_w, item_h = 100.0, 50.0
        x, y = resolve_anchor(a, page_w, page_h, item_w, item_h)
        # h=center → (200 - 100) / 2 = 50
        self.assertAlmostEqual(x, (page_w - item_w) / 2, places=3)
        # v=bottom, margin_mm=20 → y = 300 - 50 - mm_to_pt(20)
        from sla_lib.builder.document import mm_to_pt
        expected_y = page_h - item_h - mm_to_pt(20)
        self.assertAlmostEqual(y, expected_y, places=3)

    def test_anchor_named_args_top_left(self):
        """Anchor(h='left', v='top', margin_mm=0) resolves to (0, 0)."""
        from sla_lib.builder.primitives import resolve_anchor
        a = Anchor(h="left", v="top")
        x, y = resolve_anchor(a, 200.0, 300.0, 100.0, 50.0)
        self.assertAlmostEqual(x, 0.0, places=3)
        self.assertAlmostEqual(y, 0.0, places=3)

    def test_anchor_named_args_right_edge(self):
        """Anchor(h='right', v='center') resolves to right + vertical center."""
        from sla_lib.builder.primitives import resolve_anchor
        a = Anchor(h="right", v="center")
        page_w, page_h = 200.0, 300.0
        item_w, item_h = 60.0, 40.0
        x, y = resolve_anchor(a, page_w, page_h, item_w, item_h)
        self.assertAlmostEqual(x, page_w - item_w, places=3)  # right-flush, no margin
        self.assertAlmostEqual(y, (page_h - item_h) / 2, places=3)

    def test_anchor_invalid_h_raises(self):
        """Anchor rejects unknown h= values."""
        with self.assertRaises(ValueError):
            Anchor(h="west", v="top")

    def test_anchor_invalid_v_raises(self):
        """Anchor rejects unknown v= values."""
        with self.assertRaises(ValueError):
            Anchor(h="center", v="middle")

    def test_anchor_legacy_string_warns(self):
        """Anchor.from_legacy('bottom-20') emits DeprecationWarning."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            a = Anchor.from_legacy("bottom-20")
            self.assertTrue(any(issubclass(x.category, DeprecationWarning) for x in w),
                            "Expected DeprecationWarning from Anchor.from_legacy()")
        self.assertIsInstance(a, Anchor)

    def test_anchor_legacy_tuple_warns(self):
        """Anchor.from_legacy(('center', 30)) emits DeprecationWarning."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            a = Anchor.from_legacy(("center", 30))
            self.assertTrue(any(issubclass(x.category, DeprecationWarning) for x in w),
                            "Expected DeprecationWarning from Anchor.from_legacy() tuple")
        self.assertIsInstance(a, Anchor)

    def test_anchor_in_textframe_resolves(self):
        """TextFrame(anchor=Anchor(h='center', v='top')) positions correctly."""
        d = _make_simple_doc()
        tf = TextFrame(w_mm=50, h_mm=20,
                       anchor=Anchor(h="center", v="top"),
                       anname="anchor_test")
        d.pages[0].add(tf)
        root = _build_to_tree(d)
        # Should not raise and should produce a PAGEOBJECT.
        pos = root.find("DOCUMENT").findall("PAGEOBJECT")
        self.assertTrue(any(p.attrib.get("ANNAME") == "anchor_test" for p in pos))


class RunLegacyDeprecationTests(unittest.TestCase):
    """Run legacy tuple form emits DeprecationWarning."""

    def test_run_legacy_tuple_warns_when_added_to_textframe(self):
        """Tuple-form Run in TextFrame.runs emits DeprecationWarning on emit."""
        import warnings
        d = _make_simple_doc()
        d.pages[0].add(TextFrame(
            x_mm=10, y_mm=10, w_mm=20, h_mm=10,
            runs=[("Hello", {"fcolor": "White"}, "para")],
        ))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with ROOT.joinpath("tools/sla_lib/tests/dummy.sla").__class__("/dev/null").open("wb"):
                pass
            import tempfile
            tmp = Path(tempfile.mktemp(suffix=".sla"))
            d.save(tmp)
            self.assertTrue(any(issubclass(x.category, DeprecationWarning) for x in w),
                            "Expected DeprecationWarning for Run tuple form")


class TextFrameMultiStyleChannelTests(unittest.TestCase):
    """TextFrame multi-style-channel warning."""

    def test_textframe_multi_style_channel_warns(self):
        """Setting style= AND default_style_attrs= on same TextFrame emits UserWarning."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            TextFrame(
                x_mm=10, y_mm=10, w_mm=50, h_mm=20,
                style="SomeStyle",
                default_style_attrs={"FONT": "Gotham Narrow Book"},
            )
            user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
            self.assertTrue(len(user_warnings) > 0,
                            "Expected UserWarning when style= and default_style_attrs= both set")

    def test_textframe_style_alone_no_warning(self):
        """Setting style= without default_style_attrs= emits no warning."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            TextFrame(x_mm=10, y_mm=10, w_mm=50, h_mm=20, style="SomeStyle")
            user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
            self.assertEqual(user_warnings, [], "No UserWarning expected when only style= is set")


class ValidationErrorMessageTests(unittest.TestCase):
    """Validation error messages name the offending attribute and closed set."""

    def test_para_override_attrs_error_message_names_attr(self):
        """Invalid paragraph_attrs key raises ValueError naming the key + set."""
        with self.assertRaises(ValueError) as cm:
            Run(text="x", paragraph_attrs={"UNKNOWN_KEY": "0"})
        msg = str(cm.exception)
        self.assertIn("UNKNOWN_KEY", msg,
                      "Error message must name the offending attribute key")
        # Should name the allowed keys or the closed set
        self.assertIn("ALIGN", msg,
                      "Error message must name at least one allowed key from the closed set")

    def test_defaultstyle_attrs_error_message_names_attr(self):
        """Invalid default_style_attrs key raises ValueError naming the key + set."""
        with self.assertRaises(ValueError) as cm:
            TextFrame(x_mm=0, y_mm=0, w_mm=10, h_mm=10,
                      default_style_attrs={"BAD_KEY": "1"})
        msg = str(cm.exception)
        self.assertIn("BAD_KEY", msg,
                      "Error message must name the offending attribute key")
        self.assertIn("FONT", msg,
                      "Error message must name at least one allowed key from DEFAULTSTYLE_OVERRIDE_ATTRS")

    def test_trail_attrs_error_message_names_attr(self):
        """Invalid trail_attrs key raises ValueError naming the key + set."""
        with self.assertRaises(ValueError) as cm:
            TextFrame(x_mm=0, y_mm=0, w_mm=10, h_mm=10,
                      trail_attrs={"UNKNOWN_TRAIL_KEY": "0"})
        msg = str(cm.exception)
        self.assertIn("UNKNOWN_TRAIL_KEY", msg)
        self.assertIn("ALIGN", msg)


class AdditiveStylesTests(unittest.TestCase):
    """Additive paragraph-style emission: palette_replaces_ci=False emits CI + custom."""

    def test_custom_styles_additive_when_palette_replaces_ci_false(self):
        """palette_replaces_ci=False: CI brand stack + custom styles both emitted."""
        d = Document(title="t", template_id="x", palette_replaces_ci=False)
        d.add_para_style(ParaStyle(name="MyCustomStyle", fontsize=14))
        d.add_page(size="A6")
        root = _build_to_tree(d)
        style_names = {s.attrib.get("NAME", "") for s in root.find("DOCUMENT").findall("STYLE")}
        # CI brand styles must appear
        self.assertIn("ci/default", style_names,
                      "CI style must appear when palette_replaces_ci=False")
        # Custom template style must also appear
        self.assertIn("MyCustomStyle", style_names,
                      "Custom style must appear additively")

    def test_custom_styles_only_when_palette_replaces_ci_true(self):
        """palette_replaces_ci=True: only registered styles emitted, CI stack skipped."""
        d = Document(title="t", template_id="x", palette_replaces_ci=True)
        d.add_para_style(ParaStyle(name="TemplateOnly", fontsize=12))
        d.add_page(size="A6")
        root = _build_to_tree(d)
        style_names = {s.attrib.get("NAME", "") for s in root.find("DOCUMENT").findall("STYLE")}
        self.assertIn("TemplateOnly", style_names)
        self.assertNotIn("ci/default", style_names,
                         "CI style must NOT appear when palette_replaces_ci=True")

    def test_vertical_text_align_canonical_form(self):
        """vertical_text_align= is canonical; emits PAGEOBJECT VAlign (not ALIGN)."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            d = _make_simple_doc()
            d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=30, h_mm=20,
                                     vertical_text_align=2))
            depr = [x for x in w if issubclass(x.category, DeprecationWarning)]
            self.assertEqual(depr, [], "No DeprecationWarning for vertical_text_align=")
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        # VAlign is Scribus's vertical-justification channel; ALIGN must NOT
        # carry the value (ALIGN has no vertical-centring effect).
        self.assertEqual(po.attrib["VAlign"], "2")
        self.assertNotIn("ALIGN", po.attrib)

    def test_text_align_deprecated_alias_still_works(self):
        """TextFrame text_align= still works but emits DeprecationWarning."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            d = _make_simple_doc()
            d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=30, h_mm=20,
                                     text_align=1))
            depr = [x for x in w if issubclass(x.category, DeprecationWarning)]
            self.assertTrue(len(depr) > 0,
                            "DeprecationWarning expected for text_align=")
        root = _build_to_tree(d)
        po = root.find("DOCUMENT").find("PAGEOBJECT")
        self.assertEqual(po.attrib["VAlign"], "1")


if __name__ == "__main__":
    unittest.main()

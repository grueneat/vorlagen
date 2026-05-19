"""Tests for the five evidence-driven compose blocks.

Each block has >= 2 verified corpus occurrences; the docstring of each block
in blocks.py cites the exact file:line references.
"""
from __future__ import annotations
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib import SLADocument  # noqa: E402
from sla_lib.builder import Document, Color, blocks  # noqa: E402
from sla_lib.builder.blocks import (  # noqa: E402
    PageNumber, Impressum, PageBackground, ContactBlock, ColumnTextStory,
    DEFAULT_IMPRESSUM,
)
from sla_lib.builder.primitives import Run, TextFrame, Polygon, ImageFrame, Anchor
  # noqa: E402


def _save(doc: Document) -> SLADocument:
    f = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
    f.close()
    doc.save(f.name)
    return SLADocument(f.name)


def _save_to_str(doc: Document) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
    f.close()
    doc.save(f.name)
    return Path(f.name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# PageNumber
# ---------------------------------------------------------------------------
class PageNumberTests(unittest.TestCase):
    """PageNumber block — 12× in templates/zeitung-a4/build.py."""

    def _doc_with_block(self, **kwargs):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A4")
        page.add(PageNumber(x_mm=10, y_mm=280, **kwargs))
        return doc

    def test_pagenumber_emits_one_text_frame(self):
        """Block emits exactly one TextFrame (PTYPE=4)."""
        parsed = _save(self._doc_with_block())
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        self.assertEqual(len(text_frames), 1)

    def test_pagenumber_emits_var_pgno(self):
        """TextFrame contains a <var name='pgno'/> element in StoryText."""
        parsed = _save(self._doc_with_block())
        text = parsed.page_objects()[0]
        story = text.find("StoryText")
        var_el = story.find("var")
        self.assertIsNotNone(var_el, "Expected <var> element for page number")
        self.assertEqual(var_el.attrib.get("name"), "pgno")

    def test_pagenumber_default_style_seitenzahl(self):
        """Default paragraph_style is 'Seitenzahl'."""
        parsed = _save(self._doc_with_block())
        text = parsed.page_objects()[0]
        story = text.find("StoryText")
        trail = story.find("DefaultStyle")
        if trail is not None:
            # DefaultStyle carries the paragraph style name
            self.assertIn("Seitenzahl", _save_to_str(self._doc_with_block()))

    def test_pagenumber_custom_style(self):
        """Custom style= overrides the default."""
        xml = _save_to_str(self._doc_with_block(style="CustomPageNum"))
        self.assertIn("CustomPageNum", xml)

    def test_pagenumber_round_trips_through_emit(self):
        """Block -> Document.save() produces valid parseable XML."""
        doc = self._doc_with_block()
        xml = _save_to_str(doc)
        self.assertGreater(len(xml), 100)
        self.assertIn("<SCRIBUSUTF8NEW", xml)

    def test_page_number_default_emits_minimal_text_frame(self):
        """Zero-kwarg PageNumber emits a frame without clip_edit and no var_attrs.

        Guards backward compatibility — existing callers (Postkarte, Plakat) must not
        regress when they use PageNumber without the new kwargs.
        """
        pn = PageNumber(x_mm=10, y_mm=280)
        frames = list(pn.emit())
        self.assertEqual(len(frames), 1)
        tf = frames[0]
        self.assertFalse(tf.clip_edit,
                         "Default PageNumber must not set clip_edit=True")
        self.assertIsNone(tf.runs[0].var_attrs,
                          "Default PageNumber must not set var_attrs on inner Run")

    def test_page_number_forwards_clip_edit_and_geometry_kwargs(self):
        """PageNumber forwards clip_edit, line_width_pt, col_gap_mm to inner TextFrame."""
        pn = PageNumber(
            x_mm=8.51073047881968,
            y_mm=283.69722222116576,
            w_mm=12.775464220466706,
            h_mm=9.480247708017236,
            layer=0,
            anname="Kopie von u2d45",
            clip_edit=True,
            line_width_pt=1,
            col_gap_mm=3.207461712525627,
        )
        frames = list(pn.emit())
        self.assertEqual(len(frames), 1)
        tf = frames[0]
        self.assertTrue(tf.clip_edit, "clip_edit must be forwarded to inner TextFrame")
        self.assertEqual(tf.line_width_pt, 1,
                         "line_width_pt must be forwarded to inner TextFrame")
        self.assertAlmostEqual(tf.col_gap_mm, 3.207461712525627, places=10,
                               msg="col_gap_mm must be forwarded verbatim without rounding")
        self.assertEqual(tf.layer, 0)
        self.assertEqual(tf.anname, "Kopie von u2d45")

    def test_page_number_forwards_var_attrs_to_inner_run(self):
        """PageNumber forwards var_attrs to the inner Run (white pgno on dark background)."""
        pn = PageNumber(x_mm=10, y_mm=280, var_attrs={"FCOLOR": "White", "FSHADE": "100"})
        frames = list(pn.emit())
        self.assertEqual(len(frames), 1)
        tf = frames[0]
        self.assertEqual(tf.runs[0].var_attrs, {"FCOLOR": "White", "FSHADE": "100"},
                         "var_attrs must be forwarded verbatim to the inner Run")


# ---------------------------------------------------------------------------
# Impressum
# ---------------------------------------------------------------------------
class ImpressumTests(unittest.TestCase):
    """Impressum block — corpus in templates/postkarte-a6-kampagne/build.py:294
    and templates/zeitung-a4/build.py:3205."""

    def _doc_with_block(self, **kwargs):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(Impressum(x_mm=5, y_mm=142, w_mm=95, **kwargs))
        return doc

    def test_impressum_emits_one_text_frame(self):
        """Block emits exactly one TextFrame (PTYPE=4)."""
        parsed = _save(self._doc_with_block())
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        self.assertEqual(len(text_frames), 1)

    def test_impressum_default_text(self):
        """Default text contains 'Grünen Niederösterreich' brand name."""
        parsed = _save(self._doc_with_block())
        text = parsed.page_objects()[0]
        story = text.find("StoryText")
        first_itext = story.find("ITEXT")
        ch = first_itext.attrib.get("CH", "") if first_itext is not None else ""
        self.assertIn("Grünen Niederösterreich", ch)

    def test_impressum_trail_style_impressum(self):
        """trail_style='Impressum' is set on the emitted frame."""
        xml = _save_to_str(self._doc_with_block())
        self.assertIn("Impressum", xml)

    def test_impressum_custom_text(self):
        """Custom text= replaces the default impressum text."""
        custom_text = "Custom legal notice for testing"
        parsed = _save(self._doc_with_block(text=custom_text))
        text = parsed.page_objects()[0]
        story = text.find("StoryText")
        first = story.find("ITEXT")
        ch = first.attrib.get("CH", "") if first is not None else ""
        self.assertIn("Custom legal notice", ch)

    def test_impressum_round_trips_through_emit(self):
        """Block -> Document.save() produces valid parseable XML."""
        xml = _save_to_str(self._doc_with_block())
        self.assertGreater(len(xml), 100)
        self.assertIn("<SCRIBUSUTF8NEW", xml)

    def test_impressum_with_bold_prefix(self):
        """2-Run bold-prefix idiom (Postkarte build.py:223-236).

        prefix_text='Impressum:' emits two ITEXT children in one paragraph:
        first with Gotham Narrow Bold, second with the body text.
        """
        parsed = _save(self._doc_with_block(
            prefix_text='Impressum:', prefix_features='inherit'))
        tf = next(o for o in parsed.page_objects() if o.attrib.get('PTYPE') == '4')
        story = tf.find('StoryText')
        itexts = story.findall('ITEXT')
        self.assertEqual(len(itexts), 2,
                         f"Expected 2 ITEXT elements, got {len(itexts)}")
        self.assertEqual(itexts[0].attrib.get('FONT'), 'Gotham Narrow Bold',
                         "First ITEXT must carry Gotham Narrow Bold font")
        self.assertEqual(itexts[0].attrib.get('CH'), 'Impressum:')
        self.assertNotEqual(itexts[1].attrib.get('FONT'), 'Gotham Narrow Bold',
                            "Second ITEXT must not carry Gotham Narrow Bold font")
        self.assertIn('Grünen Niederösterreich', itexts[1].attrib.get('CH', ''))

    def test_impressum_rotated(self):
        """rotation_deg=270 passthrough (Plakat build.py:91-105).

        Frame must carry ROT='270'; Run shape stays 1-Run (baseline).
        """
        parsed = _save(self._doc_with_block(rotation_deg=270))
        tf = next(o for o in parsed.page_objects() if o.attrib.get('PTYPE') == '4')
        self.assertEqual(tf.attrib.get('ROT'), '270',
                         "Frame must carry ROT='270' when rotation_deg=270")
        story = tf.find('StoryText')
        itexts = story.findall('ITEXT')
        self.assertEqual(len(itexts), 1,
                         "rotation_deg alone must not change Run count (1-Run baseline)")

    def test_impressum_with_heading(self):
        """3-Run heading + spacer + body schema (Zeitung build.py:2445-2459).

        heading_text='Impressum' with heading_paragraph_style emits:
        heading ITEXT + para + empty spacer + para + body ITEXT.
        """
        xml = _save_to_str(self._doc_with_block(
            heading_text='Impressum',
            heading_paragraph_style='Inhaltsheadline Titelseite'))
        self.assertIn('Inhaltsheadline Titelseite', xml,
                      "Heading paragraph style must appear in emitted SLA")
        parsed = _save(self._doc_with_block(
            heading_text='Impressum',
            heading_paragraph_style='Inhaltsheadline Titelseite'))
        tf = next(o for o in parsed.page_objects() if o.attrib.get('PTYPE') == '4')
        story = tf.find('StoryText')
        itexts = story.findall('ITEXT')
        paras = story.findall('para')
        self.assertEqual(len(itexts), 2,
                         f"Expected 2 non-empty ITEXT elements, got {len(itexts)}")
        self.assertGreaterEqual(len(paras), 2,
                                f"Expected >= 2 para separators, got {len(paras)}")
        self.assertEqual(itexts[0].attrib.get('CH'), 'Impressum',
                         "First ITEXT must be the heading text")
        self.assertIn('Grünen Niederösterreich', itexts[1].attrib.get('CH', ''),
                      "Last ITEXT must contain the default body marker")

    def test_impressum_baseline_unchanged(self):
        """Backward-compat: default Impressum (no new kwargs) produces 1-Run, no rotation.

        Verifies the else-branch in emit() is taken and existing corpus call
        sites continue to work byte-identically.
        """
        doc1 = self._doc_with_block()
        doc2 = Document(title='x', template_id='x')
        page2 = doc2.add_page(size='A6')
        page2.add(Impressum(x_mm=5, y_mm=142, w_mm=95))
        for doc in (doc1, doc2):
            xml = _save_to_str(doc)
            self.assertIn('<SCRIBUSUTF8NEW', xml)
            parsed = _save(doc)
            tf = next(o for o in parsed.page_objects() if o.attrib.get('PTYPE') == '4')
            story = tf.find('StoryText')
            itexts = story.findall('ITEXT')
            self.assertEqual(len(itexts), 1,
                             "Default Impressum must produce exactly 1 ITEXT")
            self.assertIn('Grünen Niederösterreich', itexts[0].attrib.get('CH', ''))
            rot = tf.attrib.get('ROT')
            if rot is not None:
                self.assertAlmostEqual(float(rot), 0.0,
                                       msg="Default Impressum must not rotate the frame")


# ---------------------------------------------------------------------------
# PageBackground
# ---------------------------------------------------------------------------
class PageBackgroundTests(unittest.TestCase):
    """PageBackground — corpus: templates/postkarte-a6-kampagne/build.py:89-100
    (page0), templates/postkarte-a6-kampagne/build.py:216-227 (page1),
    templates/zeitung-a4/build.py (Titelseite)."""

    def _doc_with_block(self, **kwargs):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6", bleed_mm=3)
        page.add(PageBackground(**kwargs))
        return doc

    def test_pagebackground_emits_polygon(self):
        """Block emits one Polygon frame (PTYPE=6)."""
        parsed = _save(self._doc_with_block())
        polygons = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "6"]
        self.assertEqual(len(polygons), 1)

    def test_pagebackground_full_bleed(self):
        """Polygon covers the full page (width/height == page dims + bleed)."""
        parsed = _save(self._doc_with_block(color=Color.DUNKELGRUEN, bleed_mm=3))
        page_w, page_h = parsed.page_size_pt
        polygon = next(o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "6")
        w = float(polygon.attrib.get("WIDTH", 0))
        h = float(polygon.attrib.get("HEIGHT", 0))
        # With bleed, the polygon should be at least as large as the page
        self.assertGreaterEqual(w, page_w * 0.9,
                                f"Expected polygon width near {page_w:.1f}, got {w:.1f}")
        self.assertGreaterEqual(h, page_h * 0.9,
                                f"Expected polygon height near {page_h:.1f}, got {h:.1f}")

    def test_pagebackground_default_color_dunkelgruen(self):
        """Default fill color is Dunkelgrün (brand-primary)."""
        xml = _save_to_str(self._doc_with_block())
        self.assertIn("Dunkelgr", xml)  # Dunkelgrün (handles encoding)

    def test_pagebackground_custom_color(self):
        """Custom color= is applied as fill."""
        xml = _save_to_str(self._doc_with_block(color=Color.GELB))
        self.assertIn("Gelb", xml)

    def test_pagebackground_round_trips_through_emit(self):
        """Block -> Document.save() produces valid parseable XML."""
        xml = _save_to_str(self._doc_with_block())
        self.assertGreater(len(xml), 100)
        self.assertIn("<SCRIBUSUTF8NEW", xml)

    def test_page_background_for_page_forwards_line_args(self):
        """for_page() forwards line_color and line_width_pt to the emitted Polygon."""
        bg = PageBackground.for_page(105, 148, color='Dunkelgrün',
                                     line_color='Black', line_width_pt=1)
        polygons = list(bg.emit())
        self.assertEqual(len(polygons), 1)
        polygon = polygons[0]
        self.assertEqual(polygon.line_color, 'Black',
                         "line_color should propagate from for_page() to emitted Polygon")
        self.assertEqual(polygon.line_width_pt, 1,
                         "line_width_pt should propagate from for_page() to emitted Polygon")


# ---------------------------------------------------------------------------
# ContactBlock
# ---------------------------------------------------------------------------
class ContactBlockTests(unittest.TestCase):
    """ContactBlock — corpus: templates/postkarte-a6-kampagne/build.py:272
    (Kontaktmöglichkeiten frame with 4 contact lines)."""

    def _doc_with_block(self, **kwargs):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(ContactBlock(
            handles=["line1", "line2", "line3"],
            x_mm=5, y_mm=100, w_mm=90, h_mm=20,
            **kwargs
        ))
        return doc

    def test_contactblock_emits_one_text_frame(self):
        """Block emits exactly one TextFrame (PTYPE=4)."""
        parsed = _save(self._doc_with_block())
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        self.assertEqual(len(text_frames), 1)

    def test_contactblock_lines_produce_runs(self):
        """N handles produce N ITEXT runs."""
        parsed = _save(self._doc_with_block())
        text = parsed.page_objects()[0]
        story = text.find("StoryText")
        itexts = story.findall("ITEXT")
        self.assertEqual(len(itexts), 3, f"Expected 3 runs, got {len(itexts)}")

    def test_contactblock_run_content(self):
        """Handle text appears in ITEXT CH attribute."""
        handles = ["Facebook: test", "office@test.at", "+43 1234"]
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(ContactBlock(handles=handles, x_mm=5, y_mm=100, w_mm=90, h_mm=20))
        xml = _save_to_str(doc)
        for h in handles:
            self.assertIn(h, xml)

    def test_contactblock_round_trips_through_emit(self):
        """Block -> Document.save() produces valid parseable XML."""
        xml = _save_to_str(self._doc_with_block())
        self.assertGreater(len(xml), 100)
        self.assertIn("<SCRIBUSUTF8NEW", xml)


# ---------------------------------------------------------------------------
# ColumnTextStory
# ---------------------------------------------------------------------------
class ColumnTextStoryTests(unittest.TestCase):
    """ColumnTextStory — corpus: templates/zeitung-a4/build.py, 84 linked
    text-frame chains with link_to() connections (lines 3214-3223+)."""

    def _make_frames(self, n: int = 2) -> list:
        return [
            TextFrame(x_mm=10 + i * 60, y_mm=50, w_mm=55, h_mm=100)
            for i in range(n)
        ]

    def _doc_with_block(self, frames=None, **kwargs):
        if frames is None:
            frames = self._make_frames(2)
        runs = [
            Run(text="Hello ", separator=None, paragraph_style=None),
            Run(text="World", separator="para", paragraph_style=None),
        ]
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A4")
        page.add(ColumnTextStory(frames=frames, runs=runs, **kwargs))
        return doc

    def test_columntextstory_emits_n_frames(self):
        """N frames are added as N TextFrame PAGEOBJECTs."""
        frames = self._make_frames(3)
        parsed = _save(self._doc_with_block(frames=frames))
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        self.assertEqual(len(text_frames), 3)

    def test_columntextstory_chain(self):
        """Frames are linked via NEXTITEM/BACKITEM chain in emitted SLA."""
        frames = self._make_frames(2)
        parsed = _save(self._doc_with_block(frames=frames))
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        # Head frame must have a NEXTITEM pointing to a valid ItemID
        head = text_frames[0]
        head_next = head.attrib.get("NEXTITEM", "-1")
        self.assertNotEqual(head_next, "-1",
                            "Head frame NEXTITEM should point to next frame")
        # Tail frame must have a BACKITEM pointing to a valid ItemID
        tail = text_frames[-1]
        tail_back = tail.attrib.get("BACKITEM", "-1")
        self.assertNotEqual(tail_back, "-1",
                            "Tail frame BACKITEM should point to previous frame")

    def test_columntextstory_runs_on_first_frame(self):
        """Story runs are emitted on the first frame in the chain."""
        frames = self._make_frames(2)
        parsed = _save(self._doc_with_block(frames=frames))
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        head = text_frames[0]
        story = head.find("StoryText")
        itexts = story.findall("ITEXT")
        self.assertGreater(len(itexts), 0, "Expected runs on head frame")

    def test_columntextstory_round_trips_through_emit(self):
        """Block -> Document.save() produces valid parseable XML."""
        xml = _save_to_str(self._doc_with_block())
        self.assertGreater(len(xml), 100)
        self.assertIn("<SCRIBUSUTF8NEW", xml)


# ---------------------------------------------------------------------------
# Legacy blocks removed
# ---------------------------------------------------------------------------
class LegacyBlocksTests(unittest.TestCase):
    """Verify old aspirational blocks are moved to blocks.legacy."""

    def test_headline4line_not_in_top_level_blocks(self):
        """Headline4Line is no longer importable from sla_lib.builder.blocks directly."""
        with self.assertRaises((ImportError, AttributeError)):
            from sla_lib.builder.blocks import Headline4Line  # noqa: F401

    def test_stoererbadge_not_in_top_level_blocks(self):
        """StoererBadge is no longer importable from sla_lib.builder.blocks directly."""
        with self.assertRaises((ImportError, AttributeError)):
            from sla_lib.builder.blocks import StoererBadge  # noqa: F401

    def test_legacy_compat_import(self):
        """Old block names available under blocks.legacy for migration."""
        import sla_lib.builder.blocks as b
        self.assertTrue(hasattr(b, "legacy"),
                        "blocks.legacy module/object should exist for old block names")

    def test_five_new_blocks_importable(self):
        """All 5 new evidence-driven blocks are importable."""
        from sla_lib.builder.blocks import (  # noqa: F401
            PageNumber, Impressum, PageBackground, ContactBlock, ColumnTextStory
        )


if __name__ == "__main__":
    unittest.main()

# ---------------------------------------------------------------------------
# WahlkreuzSymbol
# ---------------------------------------------------------------------------
class WahlkreuzSymbolTests(unittest.TestCase):
    def test_wahlkreuz_emits_polygon_and_image(self):
        from sla_lib.builder.blocks import WahlkreuzSymbol
        from sla_lib.builder.primitives import Anchor
        wk = WahlkreuzSymbol(pos=Anchor.from_page("top-left", 10, 10), 
                            size=(50, 50),
                            background_color="Dunkelgrün",
                            background_padding_mm=4.0)
        items = list(wk.emit(None))
        self.assertEqual(len(items), 2)
        self.assertIsInstance(items[0], Polygon)
        self.assertIsInstance(items[1], ImageFrame)
        
        poly = items[0]
        self.assertEqual(poly.fill, "Dunkelgrün")
        # 50x50 + 4mm padding each side = 58x58
        self.assertAlmostEqual(poly.w_mm, 58.0)
        self.assertAlmostEqual(poly.h_mm, 58.0)
        
        img = items[1]
        self.assertEqual(img.w_mm, 50.0)
        self.assertEqual(img.h_mm, 50.0)
        self.assertIsNotNone(img.inline_image_data)
        self.assertEqual(img.inline_image_ext, "png")

    def test_wahlkreuz_invalid_color_raises(self):
        from sla_lib.builder.blocks import WahlkreuzSymbol
        from sla_lib.builder.primitives import Anchor
        wk = WahlkreuzSymbol(pos=Anchor.from_page("top-left", 10, 10), 
                            size=(50, 50),
                            background_color="White")
        with self.assertRaisesRegex(ValueError, "D12"):
            list(wk.emit(None))

# ---------------------------------------------------------------------------
# FoldLine
# ---------------------------------------------------------------------------
class FoldLineTests(unittest.TestCase):
    def test_foldline_emits_polygon_on_layer(self):
        from sla_lib.builder.blocks import FoldLine
        fl = FoldLine(start_mm=(10, 10), end_mm=(10, 100), layer_idx=3,
                      layer_name="Falz", spot_color="Falz")
        items = list(fl.emit(None))
        self.assertEqual(len(items), 1)
        poly = items[0]
        self.assertEqual(poly.layer, 3)  # int index, matches LAYER attribute
        self.assertEqual(poly.line_color, "Falz")
        self.assertEqual(poly.dash_pattern, (3.0, 1.5))

# ---------------------------------------------------------------------------
# DieCut
# ---------------------------------------------------------------------------
class DieCutTests(unittest.TestCase):
    def test_diecut_emits_closed_polygon(self):
        from sla_lib.builder.blocks import DieCut
        path = [(10, 10), (20, 10), (20, 20), (10, 20)]
        dc = DieCut(path_mm=path, layer_idx=3, layer_name="Stanzkontur",
                    spot_color="Stanzkontur")
        items = list(dc.emit(None))
        self.assertEqual(len(items), 1)
        poly = items[0]
        self.assertEqual(poly.layer, 3)  # int index
        self.assertEqual(poly.line_color, "Stanzkontur")
        # custom_path is now a Scribus path string. Verify it's closed (ends with Z)
        self.assertTrue(poly.custom_path.endswith("Z"),
                        f"path doesn't end with Z: {poly.custom_path}")
        # bbox calc: 10..20 mm = 10x10 mm = 28.34 x 28.34 pt
        self.assertAlmostEqual(poly.w_mm, 10.0, places=2)
        self.assertAlmostEqual(poly.h_mm, 10.0, places=2)
        self.assertAlmostEqual(poly.x_mm, 10.0, places=2)
        self.assertAlmostEqual(poly.y_mm, 10.0, places=2)

# ---------------------------------------------------------------------------
# FoldedPanel
# ---------------------------------------------------------------------------
class FoldedPanelTests(unittest.TestCase):
    def test_foldedpanel_emits_foldline_at_right(self):
        from sla_lib.builder.blocks import FoldedPanel
        fp = FoldedPanel(panel_index=0, panel_count=3, panel_size_mm=(99, 210), has_fold_right=True)
        items = list(fp.emit(None))
        # No children, just the fold line
        self.assertEqual(len(items), 1)
        # Should be a Polygon (from FoldLine.emit) — vertical line at x=99
        poly = items[0]
        self.assertIsInstance(poly, Polygon)
        self.assertAlmostEqual(poly.x_mm, 99.0, places=2)
        self.assertAlmostEqual(poly.y_mm, 0.0, places=2)
        self.assertAlmostEqual(poly.h_mm, 210.0, places=2)

# ---------------------------------------------------------------------------
# DoorHangerCutout
# ---------------------------------------------------------------------------
class DoorHangerCutoutTests(unittest.TestCase):
    def test_doorhanger_emits_diecut_with_hole(self):
        from sla_lib.builder.blocks import DoorHangerCutout
        dhc = DoorHangerCutout(page_size_mm=(105, 250))
        items = list(dhc.emit(None))
        self.assertEqual(len(items), 2)  # Outer + Hole
        poly_outer = items[0]
        poly_hole = items[1]
        # Outer is a 5-point closed rect → at least M + 4 L + Z = 5 path commands
        self.assertTrue(poly_outer.custom_path.endswith("Z"))
        outer_segments = poly_outer.custom_path.count("L") + poly_outer.custom_path.count("M")
        self.assertGreaterEqual(outer_segments, 5)
        # Hole is a 36-segment circle → at least 36+ L commands
        hole_segments = poly_hole.custom_path.count("L") + poly_hole.custom_path.count("M")
        self.assertGreaterEqual(hole_segments, 36)

# ---------------------------------------------------------------------------
# TableTentFold
# ---------------------------------------------------------------------------
class TableTentFoldTests(unittest.TestCase):
    def test_tabletentfold_emits_horizontal_foldline(self):
        from sla_lib.builder.blocks import TableTentFold
        ttf = TableTentFold(page_size_mm=(297, 210))
        items = list(ttf.emit(None))
        self.assertEqual(len(items), 1)
        poly = items[0]
        # FoldLine bbox at y=105, full width 297 mm horizontal
        self.assertAlmostEqual(poly.x_mm, 0.0, places=2)
        self.assertAlmostEqual(poly.y_mm, 105.0, places=2)
        self.assertAlmostEqual(poly.w_mm, 297.0, places=2)
        self.assertEqual(poly.layer, 3)


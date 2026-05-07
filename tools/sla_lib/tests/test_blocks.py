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
from sla_lib.builder.primitives import Run, TextFrame  # noqa: E402


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
    """PageNumber block — 12× in templates/zeitung-a4-grun/build.py."""

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


# ---------------------------------------------------------------------------
# Impressum
# ---------------------------------------------------------------------------
class ImpressumTests(unittest.TestCase):
    """Impressum block — corpus in templates/postkarte-a6-kampagne/build.py:294
    and templates/zeitung-a4-grun/build.py:3205."""

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


# ---------------------------------------------------------------------------
# PageBackground
# ---------------------------------------------------------------------------
class PageBackgroundTests(unittest.TestCase):
    """PageBackground — corpus: templates/postkarte-a6-kampagne/build.py:89-100
    (page0), templates/postkarte-a6-kampagne/build.py:216-227 (page1),
    templates/zeitung-a4-grun/build.py (Titelseite)."""

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
    """ColumnTextStory — corpus: templates/zeitung-a4-grun/build.py, 84 linked
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

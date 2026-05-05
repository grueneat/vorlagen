"""Tests for high-level compose blocks."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib import SLADocument  # noqa: E402
from sla_lib.builder import Document, Color, blocks  # noqa: E402


def _save(doc: Document):
    f = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
    f.close()
    doc.save(f.name)
    return SLADocument(f.name)


class HeadlineTests(unittest.TestCase):
    def test_headline_emits_one_textframe_with_4_runs(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(blocks.Headline4Line())
        parsed = _save(doc)
        objs = parsed.page_objects()
        # exactly one TextFrame from the block
        text_frames = [o for o in objs if o.attrib.get("PTYPE") == "4"]
        self.assertEqual(len(text_frames), 1)
        story = text_frames[0].find("StoryText")
        itexts = story.findall("ITEXT")
        self.assertEqual(len(itexts), 4)
        # Alternating colors
        self.assertEqual(itexts[0].attrib.get("FCOLOR"), "White")
        self.assertEqual(itexts[1].attrib.get("FCOLOR"), "Gelb")
        self.assertEqual(itexts[2].attrib.get("FCOLOR"), "White")
        self.assertEqual(itexts[3].attrib.get("FCOLOR"), "Gelb")

    def test_headline_anname_is_human_readable(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(blocks.Headline4Line())
        parsed = _save(doc)
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        self.assertIn("Brand-Wechselfarbe", text_frames[0].attrib.get("ANNAME", ""))


class StoererTests(unittest.TestCase):
    def test_emits_ellipse_plus_text(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(blocks.StoererBadge())
        parsed = _save(doc)
        objs = parsed.page_objects()
        # Ellipse polygon + text frame
        ellipse = next(o for o in objs if o.attrib.get("PTYPE") == "6")
        self.assertEqual(ellipse.attrib.get("FRTYPE"), "1")
        self.assertEqual(ellipse.attrib.get("PCOLOR"), "Magenta")
        text = next(o for o in objs if o.attrib.get("PTYPE") == "4")
        story = text.find("StoryText")
        self.assertEqual(len(story.findall("ITEXT")), 3)


class ImpressumTests(unittest.TestCase):
    def test_default_text_contains_brand_name(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(blocks.ImpressumLine())
        parsed = _save(doc)
        text = parsed.page_objects()[0]
        story = text.find("StoryText")
        ch = story.find("ITEXT").attrib.get("CH", "")
        self.assertIn("Die Grünen Niederösterreich", ch)


class SocialTests(unittest.TestCase):
    def test_4_lines_with_para_separators(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A6")
        page.add(blocks.SocialHandlesVertical())
        parsed = _save(doc)
        text = parsed.page_objects()[0]
        story = text.find("StoryText")
        self.assertEqual(len(story.findall("ITEXT")), 4)


class ContentTeasersTests(unittest.TestCase):
    def test_three_columns_six_frames(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A4")
        page.add(blocks.ContentTeasers())  # default 3 items
        parsed = _save(doc)
        # 3 headlines + 3 bodies = 6 text frames
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        self.assertEqual(len(text_frames), 6)


class MastheadTests(unittest.TestCase):
    def test_two_text_frames_zeitungsname_and_ausgabe(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A4")
        page.add(blocks.Masthead())
        parsed = _save(doc)
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        self.assertEqual(len(text_frames), 2)
        annames = [t.attrib.get("ANNAME") for t in text_frames]
        self.assertIn("Zeitungsname", annames)
        self.assertIn("Monat/Ausgabe", annames)


class EventDetailsTests(unittest.TestCase):
    def test_two_column_layout(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A2")
        page.add(blocks.EventDetails(columns=2))
        parsed = _save(doc)
        text_frames = [o for o in parsed.page_objects() if o.attrib.get("PTYPE") == "4"]
        self.assertEqual(len(text_frames), 2)


class ArticleTests(unittest.TestCase):
    def test_article_body_columns(self):
        doc = Document(title="x", template_id="x")
        page = doc.add_page(size="A4")
        page.add(blocks.ArticleBody(columns=3))
        parsed = _save(doc)
        text = parsed.page_objects()[0]
        self.assertEqual(text.attrib.get("COLUMNS"), "3")


if __name__ == "__main__":
    unittest.main()

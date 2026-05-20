"""Unit tests for tools/impressum.py.

Covers the impressum data source loader, the SLA substitution against a real
committed template, and the no-impressum-frame error path via a synthetic SLA.
"""
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure tools/ is on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from impressum import (  # noqa: E402
    apply_impressum,
    find_impressum_frames,
    load_bundeslaender,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_TEMPLATE = REPO_ROOT / "templates" / "flyer-a6-querformat-portraet" / "template.sla"


class LoadBundeslaenderTest(unittest.TestCase):
    def test_nine_entries_and_valid_default(self):
        data = load_bundeslaender()
        self.assertEqual(len(data["bundeslaender"]), 9)
        slugs = {e["slug"] for e in data["bundeslaender"]}
        self.assertIn(data["default"], slugs)
        # Every entry carries the legally required fields.
        for entry in data["bundeslaender"]:
            self.assertTrue(entry["impressum"])
            self.assertIn("druck", entry)


class ApplyImpressumTest(unittest.TestCase):
    def test_substitutes_real_template(self):
        data = load_bundeslaender()
        entry = next(e for e in data["bundeslaender"] if e["slug"] == "tirol")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "tirol.sla"
            count = apply_impressum(REAL_TEMPLATE, out, entry)
            self.assertGreaterEqual(count, 1)
            text = out.read_text(encoding="utf-8")
            # Bundesland impressum is present, placeholder is gone.
            self.assertIn("Innsbruck", text)
            self.assertIn("Impressum: ", text)
            self.assertNotIn("xxxxxx", text)

    def test_raises_without_impressum_frame(self):
        data = load_bundeslaender()
        entry = data["bundeslaender"][0]
        synthetic = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<SCRIBUSUTF8NEW><DOCUMENT>'
            '<PAGEOBJECT PTYPE="4"><StoryText>'
            '<ITEXT CH="kein Hinweis hier"/>'
            '</StoryText></PAGEOBJECT>'
            '</DOCUMENT></SCRIBUSUTF8NEW>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            sla = Path(tmp) / "synthetic.sla"
            sla.write_text(synthetic, encoding="utf-8")
            out = Path(tmp) / "out.sla"
            with self.assertRaises(RuntimeError):
                apply_impressum(sla, out, entry)

    def test_find_impressum_frames_is_case_insensitive(self):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(
            '<DOCUMENT>'
            '<PAGEOBJECT PTYPE="4"><StoryText>'
            '<ITEXT CH="IMPRES"/><ITEXT CH="sum: xxxxxx"/>'
            '</StoryText></PAGEOBJECT>'
            '<PAGEOBJECT PTYPE="4"><StoryText>'
            '<ITEXT CH="anderer Text"/>'
            '</StoryText></PAGEOBJECT>'
            '</DOCUMENT>'
        )
        frames = find_impressum_frames(root)
        self.assertEqual(len(frames), 1)

    def test_find_impressum_frames_matches_anname(self):
        """A frame named 'Impressum' is detected even when its text carries
        no literal word (e.g. tischschild-a5-quer)."""
        import xml.etree.ElementTree as ET

        root = ET.fromstring(
            '<DOCUMENT>'
            '<PAGEOBJECT PTYPE="4" ANNAME="Impressum (Tent)"><StoryText>'
            '<ITEXT CH="Medieninhaber: Die Gruenen"/>'
            '</StoryText></PAGEOBJECT>'
            '</DOCUMENT>'
        )
        frames = find_impressum_frames(root)
        self.assertEqual(len(frames), 1)


if __name__ == "__main__":
    unittest.main()

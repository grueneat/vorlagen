"""Unit tests for tools/font_variants.py.

Covers the font alternatives data-source loader, the SLA font substitution
against the real flyer template, and the no-Gotham-reference error path via
a synthetic SLA.
"""
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure tools/ is on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from font_variants import (  # noqa: E402
    apply_font,
    load_alternatives,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
# The comparison swaps from the frozen Gotham baseline (the production
# template.sla has moved to Barlow Semi Condensed, Issue c8bg0).
FLYER_TEMPLATE = (
    REPO_ROOT
    / "templates"
    / "flyer-a6-hochformat-gruenes-cover"
    / "fonts"
    / "_base-gotham.sla"
)
ALTERNATIVES_DIR = REPO_ROOT / "shared" / "fonts" / "alternatives"


class LoadAlternativesTest(unittest.TestCase):
    def test_entries_each_complete(self):
        data = load_alternatives()
        # The comparison set: tracking variants of Montserrat (-4, -5) and
        # Raleway (-3, -4, -5). All free (SIL OFL), none with own binaries —
        # they borrow Montserrat/Raleway via files_from. Gotham Narrow (the
        # proprietary baseline) is added by the build tool, not the data source.
        self.assertEqual(len(data["fonts"]), 5)
        for entry in data["fonts"]:
            # German summary is mandatory (Issue 42 acceptance criterion).
            self.assertTrue(entry["summary"].strip())
            # The weight map covers all four Gotham Narrow weights.
            self.assertEqual(
                set(entry["weights"]), {"Book", "Bold", "Black", "Ultra"}
            )
            from font_variants import resolve_files
            src_slug, files = resolve_files(data, entry)
            self.assertTrue(files)
            if entry.get("proprietary"):
                # Proprietary fonts (Tahoma) are deliberately NOT committed —
                # the .ttf binaries are git-ignored (see .gitignore). They are
                # present only on a maintainer machine for local rendering, so
                # their on-disk presence is not asserted here.
                continue
            # Every bundled free font file actually exists in the repo
            # (tracking variants borrow another entry's files via files_from).
            for fname in files:
                fpath = ALTERNATIVES_DIR / src_slug / fname
                self.assertTrue(fpath.exists(), f"missing bundled file {fpath}")

    def test_no_proprietary_entries(self):
        data = load_alternatives()
        proprietary = [e["slug"] for e in data["fonts"] if e.get("proprietary")]
        self.assertEqual(proprietary, [])

    def test_all_entries_are_tracking_variants(self):
        data = load_alternatives()
        for e in data["fonts"]:
            # Every comparison column is a tracking variant: numeric KERN and a
            # base family it borrows binaries from.
            self.assertIsInstance(e.get("track"), int)
            self.assertIn(e["family"], {"Montserrat", "Raleway"})
            self.assertTrue(e.get("files_from"))


class ApplyFontTest(unittest.TestCase):
    def test_substitutes_real_template(self):
        data = load_alternatives()
        entry = next(e for e in data["fonts"] if e["slug"] == "montserrat-eng4")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "montserrat.sla"
            count = apply_font(FLYER_TEMPLATE, out, entry)
            self.assertGreaterEqual(count, 1)
            text = out.read_text(encoding="utf-8")
            # The alternative family is present, Gotham Narrow is gone.
            self.assertIn("Montserrat Regular", text)
            self.assertNotIn("Gotham Narrow", text)
            # The other two fonts are intentionally left untouched.
            self.assertIn("Minion Pro Regular", text)
            self.assertIn("Vollkorn Black Italic", text)

    def test_raises_without_gotham_reference(self):
        data = load_alternatives()
        entry = data["fonts"][0]
        synthetic = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<SCRIBUSUTF8NEW><DOCUMENT>"
            '<PAGEOBJECT PTYPE="4"><StoryText>'
            '<ITEXT CH="kein Gotham hier" FONT="Vollkorn Black Italic"/>'
            "</StoryText></PAGEOBJECT>"
            "</DOCUMENT></SCRIBUSUTF8NEW>"
        )
        with tempfile.TemporaryDirectory() as tmp:
            sla = Path(tmp) / "synthetic.sla"
            sla.write_text(synthetic, encoding="utf-8")
            out = Path(tmp) / "out.sla"
            with self.assertRaises(RuntimeError):
                apply_font(sla, out, entry)

    def test_is_idempotent(self):
        """A second pass over an already-substituted SLA is byte-identical."""
        data = load_alternatives()
        entry = next(e for e in data["fonts"] if e["slug"] == "raleway-eng4")
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.sla"
            second = Path(tmp) / "b.sla"
            apply_font(FLYER_TEMPLATE, first, entry)
            apply_font(FLYER_TEMPLATE, second, entry)
            self.assertEqual(
                first.read_bytes(), second.read_bytes()
            )


if __name__ == "__main__":
    unittest.main()

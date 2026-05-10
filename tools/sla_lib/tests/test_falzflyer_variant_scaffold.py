"""Variant-scaffold unit tests (issue #29 T02).

Verifies that ``templates/kandidat-falzflyer-din-lang/variant_scaffold.py``:
  - Builds a 2-page Document via ``build_variant_front()`` with default P2.
  - Round-trips through ``doc.save(...)`` without raising.
  - Re-emits all 5 production P2 PAGEOBJECTs (Top-Band, Top-Title,
    Teaser-Headline, Body-Backing, Teaser-Body).
  - Replaces P2 cleanly when a custom ``render_p2`` callable is passed
    (no leftover production P2 items).
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = ROOT / "templates" / "kandidat-falzflyer-din-lang"
sys.path.insert(0, str(ROOT / "tools"))


def _load_variant_scaffold():
    """Load variant_scaffold.py without polluting sys.modules across tests."""
    spec = importlib.util.spec_from_file_location(
        "_test_variant_scaffold",
        TEMPLATE_DIR / "variant_scaffold.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VariantScaffoldDefaultTest(unittest.TestCase):
    def setUp(self):
        self.scaffold = _load_variant_scaffold()

    def test_build_default_returns_two_page_document(self):
        doc = self.scaffold.build_variant_front()
        self.assertEqual(len(doc.pages), 2,
                         "falzflyer must be 2 pages (front + back)")

    def test_default_p2_anames_present(self):
        doc = self.scaffold.build_variant_front()
        page0 = doc.pages[0]
        annames = {getattr(item, "anname", "") for item in page0.items}
        for required in (
            "P2 Top-Band",
            "P2 Top-Title",
            "P2 Teaser-Headline",
            "P2 Body-Backing",
            "P2 Teaser-Body",
        ):
            self.assertIn(required, annames,
                          f"default P2 missing anname {required!r}")

    def test_default_round_trips_to_sla(self):
        doc = self.scaffold.build_variant_front()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "variant.sla"
            doc.save(out)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000,
                               "SLA file suspiciously small")

    def test_p2_strip_replaces_existing_items(self):
        from sla_lib.builder import TextFrame, Run

        marker = "P2 Variant-Marker-Frame"

        def custom_p2(doc, page):
            page.add(TextFrame(
                x_mm=105, y_mm=8, w_mm=87, h_mm=14,
                layer=2,
                style="falzflyer/top-title",
                runs=[Run(text="custom",
                          paragraph_style="falzflyer/top-title")],
                anname=marker,
            ))

        doc = self.scaffold.build_variant_front(custom_p2)
        page0 = doc.pages[0]
        annames = [getattr(item, "anname", "") for item in page0.items]

        production_p2 = [
            a for a in annames
            if a.startswith("P2 ") and a != marker
        ]
        self.assertEqual(production_p2, [],
                         f"production P2 items leaked: {production_p2}")
        self.assertIn(marker, annames,
                      "custom P2 render_p2 was not invoked")

    def test_back_page_unchanged_by_variant(self):
        from sla_lib.builder import TextFrame, Run

        def custom_p2(doc, page):
            page.add(TextFrame(
                x_mm=105, y_mm=8, w_mm=87, h_mm=14,
                layer=2, style="falzflyer/top-title",
                runs=[Run(text="x",
                          paragraph_style="falzflyer/top-title")],
                anname="P2 Stub",
            ))

        doc = self.scaffold.build_variant_front(custom_p2)
        page1 = doc.pages[1]
        annames = {getattr(item, "anname", "") for item in page1.items}
        # Back page anchors that MUST survive
        for required in (
            "P4 Top-Band",
            "P5 Top-Band",
            "P6 Hintergrund",
            "P6 QR-Code (mitmachen)",
            "P6 Logo Grüne (weiss)",
        ):
            self.assertIn(required, annames,
                          f"variant scaffold corrupted back page (missing {required!r})")


if __name__ == "__main__":
    unittest.main()

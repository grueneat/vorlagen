"""Tests for the Brand profile (tools/sla_lib/builder/brand.py)."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Brand, Document, Page  # noqa: E402
from sla_lib.builder.ci import BrandColor  # noqa: E402
from sla_lib import SLADocument  # noqa: E402


def _save_and_reload(doc: Document) -> SLADocument:
    """Save doc to a temp file and load it back via SLADocument."""
    f = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
    f.close()
    doc.save(f.name)
    return SLADocument(f.name)


def _save_to_str(doc: Document) -> str:
    """Save doc to a temp file and return the raw XML string."""
    f = tempfile.NamedTemporaryFile(suffix=".sla", delete=False)
    f.close()
    doc.save(f.name)
    return Path(f.name).read_text(encoding="utf-8")


class TestBrandGrueneNoe(unittest.TestCase):
    """Brand.gruene_noe() loads correct data."""

    def setUp(self):
        self.brand = Brand.gruene_noe()

    def test_brand_loads_gruene_noe_name(self):
        """Brand.name and short are set from ci.yml."""
        self.assertEqual(self.brand.name, "Die Grünen Niederösterreich")
        self.assertEqual(self.brand.short, "Grüne NÖ")

    def test_brand_loads_gruene_noe_colors(self):
        """Brand.colors contains all 7 CI brand colors with correct CMYK."""
        expected = {
            "Black": (0, 0, 0, 100),
            "White": (0, 0, 0, 0),
            "Registration": (100, 100, 100, 100),
            "Dunkelgrün": (85, 35, 95, 10),
            "Hellgrün": (69, 0, 100, 0),
            "Gelb": (0, 0, 100, 0),
            "Magenta": (0, 100, 0, 0),
        }
        for cname, cmyk in expected.items():
            self.assertIn(cname, self.brand.colors, f"Missing brand color: {cname}")
            self.assertEqual(self.brand.colors[cname].cmyk, cmyk,
                             f"CMYK mismatch for {cname}")

    def test_brand_default_doc_attrs_count(self):
        """Brand.default_doc_attrs contains exactly 113 keys."""
        self.assertEqual(len(self.brand.default_doc_attrs), 113,
                         f"Expected 113 keys, got {len(self.brand.default_doc_attrs)}")

    def test_brand_default_pdf_attrs_count(self):
        """Brand.default_pdf_attrs contains exactly 34 keys."""
        self.assertEqual(len(self.brand.default_pdf_attrs), 34,
                         f"Expected 34 keys, got {len(self.brand.default_pdf_attrs)}")

    def test_brand_para_styles_present(self):
        """Brand.para_styles contains all CI brand styles."""
        expected_styles = [
            "ci/default", "ci/headline-ultra", "ci/headline-vollkorn-italic",
            "ci/body-12", "ci/body-11", "ci/impressum", "ci/stoerer", "ci/cta",
        ]
        for sname in expected_styles:
            self.assertIn(sname, self.brand.para_styles,
                          f"Missing brand para style: {sname}")

    def test_brand_layers_present(self):
        """Brand.layers contains the 4 CI layer stack entries."""
        layer_names = [l.name for l in self.brand.layers]
        self.assertIn("Hintergrund", layer_names)
        self.assertIn("Text", layer_names)
        self.assertIn("Hilfslinien", layer_names)

    def test_brand_is_frozen(self):
        """Brand is a frozen dataclass — immutable after construction."""
        with self.assertRaises((AttributeError, TypeError)):
            self.brand.name = "mutated"  # type: ignore[misc]

    def test_brand_two_calls_produce_equal_objects(self):
        """Two Brand.gruene_noe() calls produce equal (==) objects."""
        brand2 = Brand.gruene_noe()
        self.assertEqual(self.brand.name, brand2.name)
        self.assertEqual(self.brand.default_doc_attrs, brand2.default_doc_attrs)
        self.assertEqual(self.brand.default_pdf_attrs, brand2.default_pdf_attrs)


class TestDocumentWithBrand(unittest.TestCase):
    """Document(brand=Brand.gruene_noe()) wires brand into emit pipeline."""

    def _make_doc(self, **kwargs) -> Document:
        brand = Brand.gruene_noe()
        doc = Document(template_id="test", brand=brand, hcms=True, **kwargs)
        page = doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
        return doc

    def test_document_with_brand_auto_registers_palette(self):
        """Document(brand=...) includes all brand colors in emitted COLOR list."""
        doc = self._make_doc()
        sla = _save_and_reload(doc)
        color_names = {c.attrib["NAME"] for c in sla.iter_colors()}
        for expected in ("Black", "White", "Dunkelgrün", "Gelb", "Magenta"):
            self.assertIn(expected, color_names,
                          f"Brand color {expected!r} not found in emitted SLA")

    def test_document_with_brand_auto_registers_styles(self):
        """Document(brand=...) includes CI brand styles in emitted SLA."""
        doc = self._make_doc()
        xml_str = _save_to_str(doc)
        self.assertIn("ci/headline-ultra", xml_str)
        self.assertIn("ci/impressum", xml_str)

    def test_extra_doc_attrs_override_brand_defaults(self):
        """Per-template extra_doc_attrs override brand defaults (escape hatch)."""
        brand = Brand.gruene_noe()
        # Brand default has PENLINE=Green; override with Magenta
        doc = Document(template_id="test", brand=brand, hcms=True,
                       extra_doc_attrs={"PENLINE": "Magenta"})
        doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
        xml_str = _save_to_str(doc)
        # PENLINE=Magenta should appear; PENLINE=Green should not
        self.assertIn('PENLINE="Magenta"', xml_str)
        self.assertNotIn('PENLINE="Green"', xml_str)

    def test_extra_pdf_attrs_override_brand_defaults(self):
        """Per-template extra_pdf_attrs override brand defaults."""
        brand = Brand.gruene_noe()
        # Brand default has UseSpotColors=1; override with 0
        doc = Document(template_id="test", brand=brand, hcms=True,
                       extra_pdf_attrs={"UseSpotColors": "0"})
        doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
        xml_str = _save_to_str(doc)
        self.assertIn('UseSpotColors="0"', xml_str)

    def test_brand_default_doc_attrs_applied(self):
        """Brand default_doc_attrs keys appear in the emitted document attrs."""
        doc = self._make_doc()
        xml_str = _save_to_str(doc)
        # ALAYER='0' is one of the 113 brand defaults
        self.assertIn('ALAYER="0"', xml_str)
        # AUTOL='100' is another
        self.assertIn('AUTOL="100"', xml_str)

    def test_template_add_color_appended_to_brand_palette(self):
        """A template-specific color added via add_color() appears alongside brand colors."""
        doc = self._make_doc()
        doc.add_color("TemplateRed", rgb=(255, 0, 0))
        sla = _save_and_reload(doc)
        color_names = {c.attrib["NAME"] for c in sla.iter_colors()}
        self.assertIn("TemplateRed", color_names)
        self.assertIn("Dunkelgrün", color_names)  # brand color still present

    def test_no_brand_unchanged_behavior(self):
        """Document() without brand= behaves identically to pre-Brand baseline."""
        doc = Document(
            template_id="no-brand-test",
            palette_replaces_ci=True,
            hcms=True,
        )
        doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
        sla = _save_and_reload(doc)
        # Without brand, palette_replaces_ci=True means only explicit colors
        color_names = {c.attrib["NAME"] for c in sla.iter_colors()}
        # CI colors NOT added because palette_replaces_ci=True and no add_color calls
        self.assertNotIn("Dunkelgrün", color_names)

    def test_no_brand_palette_replaces_ci_false(self):
        """Document() without brand but palette_replaces_ci=False still emits CI colors."""
        doc = Document(
            template_id="no-brand-test",
            palette_replaces_ci=False,
            hcms=True,
        )
        doc.add_page(size="A6", orientation="portrait", bleed_mm=3)
        sla = _save_and_reload(doc)
        color_names = {c.attrib["NAME"] for c in sla.iter_colors()}
        self.assertIn("Dunkelgrün", color_names)


if __name__ == "__main__":
    unittest.main()

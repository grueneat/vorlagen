"""Tests for brand-CI constraint predicates.

Synthetic minimal Documents — do NOT depend on real templates here
(real-template drift discovery happens in Phase 4 / Task 8).
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.primitives import TextFrame, ImageFrame, Polygon  # noqa: E402
from sla_lib.builder.brand_constraints import (  # noqa: E402
    BRAND_CONSTRAINTS,
    BrandRule,
    _ColorPaletteRule,
    _FontFamilyRule,
    _LineSpacingRule,
    _HlSlDistanceRule,
    _LogoSize3MRule,
    _TextOnGreenRule,
    _Bleed3mmRule,
    _WahlkreuzColoredBgRule,
    _InsidePageRule,                # Issue #14
    _SpineSafetyRule,               # Issue #22 (T04)
    _UndeclaredDriftRule,           # Issue #22 (T05)
)


def _doc(size="A6", orientation="portrait", bleed=3.0):
    """Minimal doc with one page."""
    d = Document(title="t", template_id="t")
    d.add_page(size=size, orientation=orientation, bleed_mm=bleed)
    return d


def _find_rule(rid: str) -> BrandRule:
    for r in BRAND_CONSTRAINTS:
        if r.id == rid:
            return r
    raise AssertionError(f"rule {rid} not in BRAND_CONSTRAINTS")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class RegistryTests(unittest.TestCase):
    def test_eleven_rules_exact(self):
        # 11 rules: 9 baseline (Issue #12) + #14 inside_page +
        # #22 spine_safety + #22 undeclared_alignment_drift.
        self.assertEqual(len(BRAND_CONSTRAINTS), 11)

    def test_ids_are_canonical(self):
        ids = [r.id for r in BRAND_CONSTRAINTS]
        expected = {
            "brand:color_palette",
            "brand:font_family",
            "brand:line_spacing_0.9",
            "brand:hl_sl_distance_x2",
            "brand:logo_size_3M",
            "brand:text_on_green",
            "brand:bleed_3mm",
            "brand:wahlkreuz_colored_bg",
            "brand:inside_page",
            "brand:spine_safety",                # Issue #22 (T04)
            "brand:undeclared_alignment_drift",  # Issue #22 (T05)
        }
        self.assertEqual(set(ids), expected)


# ---------------------------------------------------------------------------
# brand:color_palette
# ---------------------------------------------------------------------------
class ColorPaletteRuleTests(unittest.TestCase):
    def test_brand_colors_pass(self):
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=0, w_mm=10, h_mm=10, fill="Black"))
        d.pages[0].add(Polygon(x_mm=0, y_mm=20, w_mm=10, h_mm=10, fill="Dunkelgrün"))
        rule = _find_rule("brand:color_palette")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_unknown_color_fails(self):
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=0, w_mm=10, h_mm=10, fill="Hotpink"))
        rule = _find_rule("brand:color_palette")
        v = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0].rule_id, "brand:color_palette")

    def test_doc_extra_color_passes(self):
        d = _doc()
        d.add_color("CustomTeal", rgb=(0, 128, 128))
        d.pages[0].add(Polygon(x_mm=0, y_mm=0, w_mm=10, h_mm=10, fill="CustomTeal"))
        rule = _find_rule("brand:color_palette")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


# ---------------------------------------------------------------------------
# brand:font_family
# ---------------------------------------------------------------------------
class FontFamilyRuleTests(unittest.TestCase):
    def test_default_font_passes(self):
        # Default Document deffont is "Gotham Narrow Book" — in ci.yml fonts
        d = _doc()
        d.pages[0].add(TextFrame(x_mm=0, y_mm=0, w_mm=10, h_mm=10, text="x"))
        rule = _find_rule("brand:font_family")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_unknown_font_fails(self):
        d = _doc()
        # Override doc deffont to something off-brand by mutating doc.deffont
        d.deffont = "Comic Sans MS"
        tf = TextFrame(x_mm=0, y_mm=0, w_mm=10, h_mm=10, text="x")
        d.pages[0].add(tf)
        rule = _find_rule("brand:font_family")
        v = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(v), 1)

    def test_non_textframe_skipped(self):
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=0, w_mm=10, h_mm=10, fill="Black"))
        rule = _find_rule("brand:font_family")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


# ---------------------------------------------------------------------------
# brand:line_spacing_0.9
# ---------------------------------------------------------------------------
class LineSpacingRuleTests(unittest.TestCase):
    def test_correct_factor_passes(self):
        from sla_lib.builder.styles import ParaStyle
        d = _doc()
        d.add_para_style(ParaStyle(name="x/h1", font="Gotham Narrow Book",
                                    fontsize=20.0, linesp=18.0))
        d.pages[0].add(TextFrame(x_mm=0, y_mm=0, w_mm=10, h_mm=10))
        rule = _find_rule("brand:line_spacing_0.9")
        v = rule.check(list(d.iter_all_primitives()), d)
        # The doc-level extra style we just added has fs=20 / ls=18 = factor 0.9
        # but other CI styles may have different ratios. Filter to our style:
        ours = [x for x in v if "x/h1" in x.message]
        self.assertEqual(ours, [])

    def test_wrong_factor_fails(self):
        from sla_lib.builder.styles import ParaStyle
        d = _doc()
        d.add_para_style(ParaStyle(name="x/loose", font="Gotham Narrow Book",
                                    fontsize=20.0, linesp=30.0))  # off
        rule = _find_rule("brand:line_spacing_0.9")
        v = rule.check(list(d.iter_all_primitives()), d)
        ours = [x for x in v if "x/loose" in x.message]
        self.assertEqual(len(ours), 1)

    def test_inherited_style_skipped(self):
        from sla_lib.builder.styles import ParaStyle
        d = _doc()
        # No fontsize/linesp set — inherits from PARENT — skip.
        d.add_para_style(ParaStyle(name="x/inherits", parent="ci/body-12"))
        rule = _find_rule("brand:line_spacing_0.9")
        v = rule.check(list(d.iter_all_primitives()), d)
        ours = [x for x in v if "x/inherits" in x.message]
        self.assertEqual(ours, [])


# ---------------------------------------------------------------------------
# brand:hl_sl_distance_x2
# ---------------------------------------------------------------------------
class HlSlDistanceRuleTests(unittest.TestCase):
    def test_correct_distance_passes(self):
        d = _doc()
        # baseline_mm=5.4 default; expected dy = 10.8 ± 1.0
        hl = TextFrame(x_mm=0, y_mm=10, w_mm=50, h_mm=20, anname="Headline These")
        sl = TextFrame(x_mm=0, y_mm=40.8, w_mm=50, h_mm=8, anname="Sub-Headline")
        d.pages[0].add(hl)
        d.pages[0].add(sl)
        rule = _find_rule("brand:hl_sl_distance_x2")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_wrong_distance_fails(self):
        d = _doc()
        hl = TextFrame(x_mm=0, y_mm=10, w_mm=50, h_mm=20, anname="Headline X")
        sl = TextFrame(x_mm=0, y_mm=80, w_mm=50, h_mm=8, anname="Sub-Headline X")
        # gap = 80 - 30 = 50mm; expected ~10.8 — fails
        d.pages[0].add(hl)
        d.pages[0].add(sl)
        rule = _find_rule("brand:hl_sl_distance_x2")
        v = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(v), 1)

    def test_no_subline_skips(self):
        d = _doc()
        d.pages[0].add(TextFrame(x_mm=0, y_mm=10, w_mm=50, h_mm=20, anname="Headline X"))
        rule = _find_rule("brand:hl_sl_distance_x2")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


# ---------------------------------------------------------------------------
# brand:logo_size_3M
# ---------------------------------------------------------------------------
class LogoSize3MRuleTests(unittest.TestCase):
    def test_a3_quer_logo_3m_passes(self):
        # A3 quer: 420x297mm; kurze_kante=297; M=17.82; 3M=53.46
        d = Document(title="t", template_id="t")
        d.add_page(size="A3", orientation="landscape")
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=53.46, h_mm=40,
                                   anname="Logo Grüne (top-left)"))
        rule = _find_rule("brand:logo_size_3M")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_oversize_logo_fails(self):
        d = Document(title="t", template_id="t")
        d.add_page(size="A3", orientation="landscape")
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=80, h_mm=40,
                                   anname="Logo Grüne"))
        rule = _find_rule("brand:logo_size_3M")
        v = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(v), 1)

    def test_non_logo_image_skipped(self):
        d = Document(title="t", template_id="t")
        d.add_page(size="A3", orientation="landscape")
        d.pages[0].add(ImageFrame(x_mm=10, y_mm=10, w_mm=80, h_mm=40,
                                   anname="Hero Photo"))
        rule = _find_rule("brand:logo_size_3M")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


# ---------------------------------------------------------------------------
# brand:text_on_green
# ---------------------------------------------------------------------------
class TextOnGreenRuleTests(unittest.TestCase):
    def test_white_headline_on_green_passes(self):
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=0, w_mm=100, h_mm=100,
                                fill="Dunkelgrün", anname="Hero-Hintergrund"))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=80, h_mm=30,
                                  text="x", style="ci/headline-ultra",
                                  fcolor="White", anname="Headline"))
        rule = _find_rule("brand:text_on_green")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_white_headline_on_white_fails(self):
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=0, w_mm=100, h_mm=100,
                                fill="White", anname="bg"))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=80, h_mm=30,
                                  text="x", style="ci/headline-ultra",
                                  fcolor="White", anname="Headline"))
        rule = _find_rule("brand:text_on_green")
        v = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(v), 1)

    def test_non_white_text_exempt(self):
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=0, w_mm=100, h_mm=100,
                                fill="White", anname="bg"))
        d.pages[0].add(TextFrame(x_mm=10, y_mm=10, w_mm=80, h_mm=30,
                                  text="x", style="ci/headline-ultra",
                                  fcolor="Black", anname="Headline"))
        rule = _find_rule("brand:text_on_green")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


# ---------------------------------------------------------------------------
# brand:bleed_3mm
# ---------------------------------------------------------------------------
class Bleed3mmRuleTests(unittest.TestCase):
    def test_3mm_passes(self):
        d = _doc(bleed=3.0)
        rule = _find_rule("brand:bleed_3mm")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_zero_fails(self):
        d = _doc(bleed=0.0)
        rule = _find_rule("brand:bleed_3mm")
        v = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(v), 1)

    def test_5mm_fails(self):
        d = _doc(bleed=5.0)
        rule = _find_rule("brand:bleed_3mm")
        v = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(v), 1)


# ---------------------------------------------------------------------------
# brand:wahlkreuz_colored_bg
# ---------------------------------------------------------------------------
class WahlkreuzColoredBgRuleTests(unittest.TestCase):
    def test_wahlkreuz_on_green_passes(self):
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=0, w_mm=100, h_mm=100,
                                fill="Dunkelgrün", anname="bg"))
        d.pages[0].add(Polygon(x_mm=20, y_mm=20, w_mm=10, h_mm=10,
                                fill="White", anname="Wahlkreuz Symbol"))
        rule = _find_rule("brand:wahlkreuz_colored_bg")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])

    def test_wahlkreuz_on_white_fails(self):
        d = _doc()
        d.pages[0].add(Polygon(x_mm=0, y_mm=0, w_mm=100, h_mm=100,
                                fill="White", anname="bg"))
        d.pages[0].add(Polygon(x_mm=20, y_mm=20, w_mm=10, h_mm=10,
                                fill="White", anname="Wahlkreuz Symbol"))
        rule = _find_rule("brand:wahlkreuz_colored_bg")
        v = rule.check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(v), 1)

    def test_no_wahlkreuz_passes(self):
        d = _doc()
        rule = _find_rule("brand:wahlkreuz_colored_bg")
        self.assertEqual(rule.check(list(d.iter_all_primitives()), d), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

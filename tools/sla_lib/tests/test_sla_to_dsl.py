"""Round-trip tests for the converter (tools/sla_to_dsl.py).

Each test runs:
    1. converter on the original SLA -> emits build.py + asset sidecars
    2. ``python build.py`` -> produces template.sla
    3. ``sla_diff`` against the original -> asserts critical=0, warning=0

The committed ``templates/<id>/build.py`` is what these tests actually
validate (the converter is a one-shot bootstrap; humans hand-edit thereafter).
We re-run the converter inside a tempdir to also assert the bootstrap path
stays clean.
"""
from __future__ import annotations

import importlib
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import sla_diff  # noqa: E402


def _diff_clean(left: Path, right: Path) -> sla_diff.DiffReport:
    return sla_diff.diff(left, right)


def _run_build(build_py: Path) -> Path:
    """Run ``python build.py`` with PYTHONPATH set to the repo's tools/.
    Returns the path of the produced template.sla."""
    env = {
        **{k: v for k, v in __import__("os").environ.items() if not k.startswith("PYTHONPATH")},
        "PYTHONPATH": str(ROOT / "tools"),
    }
    result = subprocess.run(
        [sys.executable, str(build_py)],
        capture_output=True, text=True, env=env, cwd=str(build_py.parent),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"build.py failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return build_py.parent / "template.sla"


class PostkarteRoundTrip(unittest.TestCase):
    """Run the committed templates/postkarte-a6-kampagne/build.py and assert
    sla_diff against the original is clean (no critical, no warning)."""

    TEMPLATE_DIR = ROOT / "templates" / "postkarte-a6-kampagne"
    ORIGINAL = ROOT / "postkarte-vorlage-original.sla"

    def test_build_emits_template(self):
        sla = _run_build(self.TEMPLATE_DIR / "build.py")
        self.assertTrue(sla.exists())

    def test_diff_against_original_clean(self):
        sla = _run_build(self.TEMPLATE_DIR / "build.py")
        report = _diff_clean(self.ORIGINAL, sla)
        self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                         msg=f"critical issues: "
                             f"{[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_CRITICAL]}")
        # build.py now uses brand=Brand.gruene_noe() which injects ci/* paragraph styles
        # and brand layers — these extra-style / extra-layer warnings are additive-only
        # (do not change rendering) and are tolerated the same way as PostkarteConverterFreshRun.
        non_brand_warnings = [
            i for i in report.issues
            if i.severity == sla_diff.SEVERITY_WARNING
            and not (i.code in ("extra-style", "extra-layer"))
        ]
        self.assertEqual(non_brand_warnings, [],
                         msg=f"unexpected warning issues: "
                             f"{[i.short() for i in non_brand_warnings]}")


class PostkarteConverterFreshRun(unittest.TestCase):
    """Run the converter from scratch in a tempdir and verify it still produces
    a clean diff. Catches regressions where someone manually edited build.py
    in a way the converter wouldn't reproduce."""

    ORIGINAL = ROOT / "postkarte-vorlage-original.sla"

    def test_fresh_convert_is_clean(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            spec = importlib.util.spec_from_file_location(
                "sla_to_dsl", str(ROOT / "tools" / "sla_to_dsl.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.convert(self.ORIGINAL, tmp / "build.py",
                         "postkarte-a6-kampagne", tmp / "assets")
            sla = _run_build(tmp / "build.py")
            report = _diff_clean(self.ORIGINAL, sla)
            self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                             msg=f"critical issues: "
                                 f"{[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_CRITICAL]}")
            # The converter now emits brand=Brand.gruene_noe() which injects:
            # - CI paragraph styles (ci/default, ci/headline-ultra, ...) not in originals
            # - All 4 brand layers (originals may only have Hintergrund)
            # These are additive-only (do not change rendering) and expected.
            # Filter them out and assert no OTHER warnings exist.
            non_brand_warnings = [
                i for i in report.issues
                if i.severity == sla_diff.SEVERITY_WARNING
                and not (i.code in ("extra-style", "extra-layer"))
            ]
            self.assertEqual(non_brand_warnings, [],
                             msg=f"unexpected warning issues: "
                                 f"{[i.short() for i in non_brand_warnings]}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class PlakatRoundTrip(unittest.TestCase):
    """Plakat reproduction: 9 frames, 7 soft-hyphens, 90-deg rotation, 0 chains."""

    TEMPLATE_DIR = ROOT / "templates" / "plakat-a1-hochformat"
    ORIGINAL = ROOT / "plakat-a1-hochformat-original.sla"

    def test_diff_against_original_clean(self):
        sla = _run_build(self.TEMPLATE_DIR / "build.py")
        report = _diff_clean(self.ORIGINAL, sla)
        self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                         msg=f"critical: {[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_CRITICAL]}")
        # build.py now uses brand=Brand.gruene_noe() which injects ci/* paragraph
        # styles, brand layers (Bilder/Text/Hilfslinien), and the full 7-color
        # palette. The original Plakat SLA carries only 5 of 7 brand colors, so
        # rebuilding adds 2 extra-color warnings (Hellgrün, Magenta). All three
        # categories of warnings are additive-only (do not change rendering) and
        # are tolerated the same way as PostkarteRoundTrip.
        _BRAND_COLOR_NAMES = (
            "Black", "White", "Registration",
            "Dunkelgrün", "Hellgrün", "Gelb", "Magenta",
        )
        non_brand_warnings = [
            i for i in report.issues
            if i.severity == sla_diff.SEVERITY_WARNING
            and not (
                i.code in ("extra-style", "extra-layer")
                or (i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES)
            )
        ]
        self.assertEqual(non_brand_warnings, [],
                         msg=f"unexpected warning issues: "
                             f"{[i.short() for i in non_brand_warnings]}")

    def test_soft_hyphens_byte_preserved(self):
        sla_path = _run_build(self.TEMPLATE_DIR / "build.py")
        b = sla_path.read_bytes()
        # \xad as UTF-8 is two bytes: 0xC2 0xAD. Plakat has 7 soft-hyphens
        # split across "ei<shy>ne", "vier<shy>zei<shy>li<shy>ge", and
        # "Ü<shy>ber<shy>schrift".
        self.assertIn(b"ei\xc2\xadne", b)
        self.assertIn(b"vier\xc2\xadzei\xc2\xadli\xc2\xadge", b)
        self.assertIn(b"\xc3\x9c\xc2\xadber\xc2\xadschrift", b)


class ZeitungRoundTrip(unittest.TestCase):
    """Zeitung reproduction: 14 pages, 140 frames, 14 linked chains, 23 styles,
    12 var pgno, 86 FRTYPE=3 paths, 6 inline images, 2 master pages, facing-pages.

    Issue #16: zeitung intentionally diverges from the upstream original SLA at
    two frames (build.py:1802 P9 Spread; build.py:2061 unnamed page-12 polygon
    moved to page12). The committed build.py therefore no longer round-trips
    byte-stable against ``gruene-zeitung-vorlage-original.sla`` — see the
    template's meta.yml::sla_diff_strict=false and the README divergence note.
    The committed-build round-trip test below tolerates the two known frame-move
    criticals; ``ZeitungConverterFreshRun`` (further down) keeps validating the
    converter's bootstrap path stays clean against the unmodified original.
    """

    TEMPLATE_DIR = ROOT / "templates" / "zeitung-a4-grun"
    ORIGINAL = ROOT / "gruene-zeitung-vorlage-original.sla"

    # Issue #16: criticals + drift warnings on these OwnPages are intentional
    # — the two moved frames change the per-page item count and PTYPE/FRTYPE
    # sequence on pages 11 and 12 (0-indexed) and shift the matched-by-position
    # PAGEOBJECT indices, surfacing as position-/size-drift warnings on the
    # adjacent objects. The Frame A move on page 9 (P9 Spread x=210→0) shows
    # up as a single XPOS drift on PAGEOBJECT[89] OwnPage=9. Anything outside
    # this allow-list is a real round-trip regression and must fail the test.
    _ALLOWED_CRITICAL_OWNPAGES = ("11", "12")
    _ALLOWED_DRIFT_OWNPAGES = ("9", "11", "12")
    _DRIFT_WARNING_CODES = (
        "position-drift",
        "size-drift",
        # Knock-on warnings from positional re-matching of shifted frames
        # within pages 11 / 12 (per-paragraph override and ITEXT content
        # mismatches against neighbouring objects):
        "para-attr-value-mismatch",
        "storytext-element-attr-value-mismatch",
    )

    def _critical_path_ownpage(self, issue) -> str | None:
        """Extract the OwnPage segment from an issue path, or None.

        sla_diff issue paths look like ``PAGEOBJECT[107] OwnPage=11 .PTYPE``;
        we slice out the digit string after ``OwnPage=`` so we can allow-list
        the two pages that issue #16 intentionally diverged on.
        """
        path = issue.path or ""
        marker = "OwnPage="
        idx = path.find(marker)
        if idx < 0:
            return None
        rest = path[idx + len(marker):]
        # Stop at the next space or bracket (path is space-separated tokens).
        end = len(rest)
        for i, ch in enumerate(rest):
            if ch in (" ", ".", "[", "]"):
                end = i
                break
        return rest[:end] or None

    def test_diff_against_original_clean(self):
        sla = _run_build(self.TEMPLATE_DIR / "build.py")
        report = _diff_clean(self.ORIGINAL, sla)
        # Issue #16: filter out criticals on the two intentionally diverged
        # pages. Anything on a different page is a real regression.
        criticals_off_allowed_pages = [
            i for i in report.issues
            if i.severity == sla_diff.SEVERITY_CRITICAL
            and self._critical_path_ownpage(i) not in self._ALLOWED_CRITICAL_OWNPAGES
        ]
        self.assertEqual(
            criticals_off_allowed_pages, [],
            msg=(
                f"unexpected criticals outside the issue #16 allowed pages "
                f"({self._ALLOWED_CRITICAL_OWNPAGES}): "
                f"{[i.short() for i in criticals_off_allowed_pages]}"
            ),
        )
        # build.py now uses brand=Brand.gruene_noe() which injects ci/* paragraph
        # styles, the 4-layer brand stack (Hintergrund/Bilder/Text/Hilfslinien),
        # and the full 7-color palette. Zeitung's original SLA carries a single
        # legacy layer named 'Ebene 1' that the brand stack replaces, so rebuilding
        # adds a 'missing-layer Ebene 1' warning. All four categories of warnings
        # are additive-only or replacement-only (do not change rendering) and are
        # tolerated the same way as PostkarteRoundTrip and PlakatRoundTrip.
        _BRAND_COLOR_NAMES = (
            "Black", "White", "Registration",
            "Dunkelgrün", "Hellgrün", "Gelb", "Magenta",
        )
        _LEGACY_LAYER_NAMES = ("Ebene 1",)
        non_brand_warnings = [
            i for i in report.issues
            if i.severity == sla_diff.SEVERITY_WARNING
            and not (
                i.code in ("extra-style", "extra-layer")
                or (i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES)
                or (i.code == "missing-layer" and i.left in _LEGACY_LAYER_NAMES)
                # Issue #16: tolerate drift on the two intentionally diverged
                # pages (the frame moves shift positional matching for
                # neighbouring objects on the same OwnPage) and the single
                # XPOS drift on the moved P9 Spread frame itself (page 9).
                or (
                    i.code in self._DRIFT_WARNING_CODES
                    and self._critical_path_ownpage(i) in self._ALLOWED_DRIFT_OWNPAGES
                )
            )
        ]
        self.assertEqual(non_brand_warnings, [],
                         msg=f"unexpected warning issues: "
                             f"{[i.short() for i in non_brand_warnings]}")

    def test_chain_topology_intact(self):
        sla = _run_build(self.TEMPLATE_DIR / "build.py")
        report = _diff_clean(self.ORIGINAL, sla)
        chain_issues = [i for i in report.issues
                        if i.code.startswith("chain-")]
        self.assertEqual(chain_issues, [],
                         msg=f"chain issues: {[i.short() for i in chain_issues]}")


class ZeitungConverterFreshRun(unittest.TestCase):
    """Run the converter from scratch in a tempdir against the Zeitung
    original and verify the diff stays clean. Mirror of
    PostkarteConverterFreshRun adapted for Zeitung's 14-page facing-pages
    layout, linked-story chains, and 'Ebene 1' legacy layer."""

    ORIGINAL = ROOT / "gruene-zeitung-vorlage-original.sla"

    def test_fresh_convert_is_clean(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            spec = importlib.util.spec_from_file_location(
                "sla_to_dsl", str(ROOT / "tools" / "sla_to_dsl.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.convert(self.ORIGINAL, tmp / "build.py",
                         "zeitung-a4-grun", tmp / "assets")
            sla = _run_build(tmp / "build.py")
            report = _diff_clean(self.ORIGINAL, sla)
            self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                             msg=f"critical issues: "
                                 f"{[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_CRITICAL]}")
            _BRAND_COLOR_NAMES = (
                "Black", "White", "Registration",
                "Dunkelgrün", "Hellgrün", "Gelb", "Magenta",
            )
            _LEGACY_LAYER_NAMES = ("Ebene 1",)
            non_brand_warnings = [
                i for i in report.issues
                if i.severity == sla_diff.SEVERITY_WARNING
                and not (
                    i.code in ("extra-style", "extra-layer")
                    or (i.code == "extra-color" and i.right in _BRAND_COLOR_NAMES)
                    or (i.code == "missing-layer" and i.left in _LEGACY_LAYER_NAMES)
                )
            ]
            self.assertEqual(non_brand_warnings, [],
                             msg=f"unexpected warning issues: "
                                 f"{[i.short() for i in non_brand_warnings]}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class StoryTextRoundTripTests(unittest.TestCase):
    """Direct tests on the converter's StoryText walker (_build_runs).

    Specifically exercise the consecutive-control-element case: two adjacent
    <para/> elements in the source encode an empty paragraph used for
    vertical spacing. The walker must NOT collapse them into a single Run
    or the body text drifts up by ~1 line per missing empty paragraph.
    """

    @classmethod
    def setUpClass(cls):
        # Imported lazily so the bare-converter sys.path setup at the top of
        # this module is in effect first.
        import sla_to_dsl  # noqa: E402
        cls.sla_to_dsl = sla_to_dsl

    def _runs(self, story_xml: str) -> list[dict]:
        from lxml import etree
        story = etree.fromstring(story_xml.strip())
        return self.sla_to_dsl._build_runs(story)

    def test_double_para_preserves_empty_paragraph(self):
        runs = self._runs("""
            <StoryText>
              <ITEXT CH="A"/>
              <para PARENT="Headline"/>
              <para PARENT="Headline"/>
              <ITEXT CH="B"/>
              <trail/>
            </StoryText>
        """)
        # Expected: 3 runs — "A" with para, empty with para, "B" (no sep yet)
        self.assertEqual(len(runs), 3, msg=f"expected 3 runs, got {len(runs)}: {runs}")
        self.assertEqual(runs[0]["text"], "A")
        self.assertEqual(runs[0].get("separator"), "para")
        self.assertEqual(runs[0].get("paragraph_style"), "Headline")
        self.assertEqual(runs[1]["text"], "")
        self.assertEqual(runs[1].get("separator"), "para")
        self.assertEqual(runs[1].get("paragraph_style"), "Headline")
        self.assertEqual(runs[2]["text"], "B")

    def test_para_then_breakline_keeps_both(self):
        """A <para/> followed by <breakline/> represents a paragraph end
        plus a forced line break — both must be preserved."""
        runs = self._runs("""
            <StoryText>
              <ITEXT CH="X"/>
              <para PARENT="Body"/>
              <breakline/>
              <ITEXT CH="Y"/>
              <trail/>
            </StoryText>
        """)
        self.assertEqual(len(runs), 3)
        self.assertEqual(runs[0]["text"], "X")
        self.assertEqual(runs[0].get("separator"), "para")
        self.assertEqual(runs[1]["text"], "")
        self.assertEqual(runs[1].get("separator"), "breakline")
        self.assertEqual(runs[2]["text"], "Y")

    def test_triple_para_keeps_all_three_paragraphs(self):
        """Three consecutive <para/>s = two empty paragraphs of vertical
        spacing. None should collapse."""
        runs = self._runs("""
            <StoryText>
              <ITEXT CH="A"/>
              <para PARENT="P1"/>
              <para PARENT="P2"/>
              <para PARENT="P3"/>
              <ITEXT CH="B"/>
              <trail/>
            </StoryText>
        """)
        # Expected: 4 runs — A+para[P1], ''+para[P2], ''+para[P3], B
        self.assertEqual(len(runs), 4, msg=f"expected 4 runs, got {len(runs)}: {runs}")
        para_styles = [r.get("paragraph_style") for r in runs[:3]]
        self.assertEqual(para_styles, ["P1", "P2", "P3"])

    def test_single_para_unchanged(self):
        """The one-empty-text + one-control-element case must not regress."""
        runs = self._runs("""
            <StoryText>
              <ITEXT CH="A"/>
              <para PARENT="Body"/>
              <ITEXT CH="B"/>
              <trail/>
            </StoryText>
        """)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["text"], "A")
        self.assertEqual(runs[0].get("separator"), "para")
        self.assertEqual(runs[1]["text"], "B")
        self.assertNotIn("separator", runs[1])


class ParagraphAttributeRoundTripTests(unittest.TestCase):
    """Per-<para>/<trail> attribute overrides (ALIGN, LINESP, LINESPMode) must
    survive the converter→build.py→builder round-trip. Dropping them silently
    is the bug PR #3 had: ALIGN="0" overrides on Headlines were ignored, so
    lines that should have rendered left-aligned ended up centered.
    """

    @classmethod
    def setUpClass(cls):
        import sla_to_dsl  # noqa: E402
        cls.sla_to_dsl = sla_to_dsl
        # Lazy import; avoids module-load ordering surprises on first import.
        from sla_lib.builder.primitives import (  # noqa: E402
            PARAGRAPH_OVERRIDE_ATTRS, Run, TextFrame,
        )
        cls.PARAGRAPH_OVERRIDE_ATTRS = PARAGRAPH_OVERRIDE_ATTRS
        cls.Run = Run
        cls.TextFrame = TextFrame

    # ---- converter side -------------------------------------------------
    def _runs(self, story_xml: str) -> list[dict]:
        from lxml import etree
        story = etree.fromstring(story_xml.strip())
        return self.sla_to_dsl._build_runs(story)

    def test_align_override_captured_into_paragraph_attrs(self):
        runs = self._runs("""
            <StoryText>
              <ITEXT CH="Headline"/>
              <para PARENT="Headline in grünem Kasten" ALIGN="0"/>
              <ITEXT CH="Body"/>
              <trail/>
            </StoryText>
        """)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["paragraph_style"], "Headline in grünem Kasten")
        self.assertEqual(runs[0].get("paragraph_attrs"), {"ALIGN": "0"})
        # The plain run after the para must NOT inherit overrides.
        self.assertNotIn("paragraph_attrs", runs[1])

    def test_linesp_mode_override_captured(self):
        runs = self._runs("""
            <StoryText>
              <ITEXT CH="x"/>
              <para PARENT="NormalParagraphStyle" LINESPMode="1"/>
              <ITEXT CH="y"/>
              <trail/>
            </StoryText>
        """)
        self.assertEqual(runs[0]["paragraph_attrs"], {"LINESPMode": "1"})

    def test_multiple_overrides_on_one_para(self):
        runs = self._runs("""
            <StoryText>
              <ITEXT CH="x"/>
              <para PARENT="P" ALIGN="3" LINESPMode="2" LINESP="13"/>
              <ITEXT CH="y"/>
              <trail/>
            </StoryText>
        """)
        self.assertEqual(
            runs[0]["paragraph_attrs"],
            {"ALIGN": "3", "LINESPMode": "2", "LINESP": "13"},
        )

    def test_unhandled_para_attr_raises(self):
        from sla_to_dsl import UnhandledElement
        with self.assertRaises(UnhandledElement) as cm:
            self._runs("""
                <StoryText>
                  <ITEXT CH="x"/>
                  <para PARENT="P" SOMETHING_NEW="42"/>
                  <trail/>
                </StoryText>
            """)
        self.assertIn("SOMETHING_NEW", str(cm.exception))

    # ---- builder side ---------------------------------------------------
    def _bare_page(self):
        """Return a Page sufficient to call to_pageobject() on a TextFrame."""
        from sla_lib.builder.document import Page, mm_to_pt
        return Page(width_pt=mm_to_pt(100), height_pt=mm_to_pt(100))

    def _idgen(self):
        from sla_lib.builder.document import _IdGen
        return _IdGen()

    def test_textframe_emits_paragraph_attrs_on_para(self):
        tf = self.TextFrame(
            x_mm=10, y_mm=10, w_mm=80, h_mm=20,
            anname="t1",
            runs=[
                self.Run(text="Headline", separator="para",
                          paragraph_style="Headline in grünem Kasten",
                          paragraph_attrs={"ALIGN": "0"}),
                self.Run(text="Body"),
            ],
            trail_style="Body",
        )
        po = tf.to_pageobject(self._idgen(), self._bare_page())
        story = po.find("StoryText")
        paras = [c for c in story if c.tag == "para"]
        self.assertEqual(len(paras), 1)
        self.assertEqual(paras[0].attrib.get("PARENT"), "Headline in grünem Kasten")
        self.assertEqual(paras[0].attrib.get("ALIGN"), "0")

    def test_textframe_emits_trail_attrs(self):
        tf = self.TextFrame(
            x_mm=10, y_mm=10, w_mm=80, h_mm=20,
            anname="t2",
            runs=[self.Run(text="Headline")],
            trail_style="Headline in grünem Kasten",
            trail_attrs={"ALIGN": "0"},
        )
        po = tf.to_pageobject(self._idgen(), self._bare_page())
        story = po.find("StoryText")
        trails = [c for c in story if c.tag == "trail"]
        self.assertEqual(len(trails), 1)
        self.assertEqual(trails[0].attrib.get("ALIGN"), "0")
        self.assertEqual(trails[0].attrib.get("PARENT"), "Headline in grünem Kasten")

    def test_textframe_omits_trail_when_last_run_para_terminated(self):
        """When the last run already ends with separator='para', there's no
        unterminated final paragraph and the original SLA omits <trail/>.
        Emitting one anyway adds a phantom empty paragraph the diff (rightly)
        flags as a count mismatch."""
        tf = self.TextFrame(
            x_mm=10, y_mm=10, w_mm=80, h_mm=20,
            anname="t3",
            runs=[
                self.Run(text="A", separator="para", paragraph_style="P"),
                self.Run(text="B", separator="para", paragraph_style="P"),
            ],
        )
        po = tf.to_pageobject(self._idgen(), self._bare_page())
        story = po.find("StoryText")
        trails = [c for c in story if c.tag == "trail"]
        paras = [c for c in story if c.tag == "para"]
        self.assertEqual(len(paras), 2)
        self.assertEqual(len(trails), 0,
                          msg="trail must be omitted when last run is para-terminated")

    def test_invalid_paragraph_attr_key_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            self.Run(text="x", paragraph_attrs={"UNKNOWN_KEY": "0"})
        with self.assertRaises(ValueError):
            self.TextFrame(x_mm=0, y_mm=0, w_mm=10, h_mm=10,
                            trail_attrs={"UNKNOWN_KEY": "0"})

    # ---- end-to-end via the converter on a synthetic SLA ----------------
    def test_para_overrides_round_trip_through_builder(self):
        """Build a tiny synthetic SLA on the fly with ALIGN overrides on
        <para> and <trail>, run it through the converter→build.py→builder,
        and assert the regenerated SLA has the same per-paragraph
        attributes verbatim.
        """
        import importlib.util
        import shutil
        import tempfile

        from lxml import etree

        tmp = Path(tempfile.mkdtemp())
        try:
            # Construct a minimal SLA the converter accepts. Simplest path:
            # take the Postkarte original (small, valid), rewrite a single
            # frame's StoryText to contain the override pattern we care
            # about, then run the converter on the result.
            src = (ROOT / "postkarte-vorlage-original.sla").read_bytes()
            tree = etree.fromstring(src)
            # Find the first PAGEOBJECT[PTYPE=4] and inject a synthetic
            # StoryText with an ALIGN override.
            doc = tree.find("DOCUMENT")
            target = None
            for po in doc.findall("PAGEOBJECT"):
                if po.attrib.get("PTYPE") == "4":
                    target = po
                    break
            self.assertIsNotNone(target)
            # Replace storytext with our fixture
            old = target.find("StoryText")
            target.remove(old)
            new_story = etree.SubElement(target, "StoryText")
            etree.SubElement(new_story, "DefaultStyle").set("PARENT", "Default Paragraph Style")
            it1 = etree.SubElement(new_story, "ITEXT"); it1.set("CH", "Eins")
            p1 = etree.SubElement(new_story, "para"); p1.set("PARENT", "Default Paragraph Style"); p1.set("ALIGN", "0")
            it2 = etree.SubElement(new_story, "ITEXT"); it2.set("CH", "Zwei")
            tr = etree.SubElement(new_story, "trail"); tr.set("PARENT", "Default Paragraph Style"); tr.set("ALIGN", "1")
            (tmp / "src.sla").write_bytes(etree.tostring(tree, xml_declaration=True, encoding="UTF-8"))

            # Run the converter on the mutated SLA.
            spec = importlib.util.spec_from_file_location(
                "sla_to_dsl_local", str(ROOT / "tools" / "sla_to_dsl.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.convert(tmp / "src.sla", tmp / "build.py",
                         "synthetic", tmp / "assets")

            # Build it.
            build_sla = _run_build(tmp / "build.py")

            # Read back and find the same frame's StoryText.
            built = etree.parse(str(build_sla)).getroot()
            built_doc = built.find("DOCUMENT")
            for po in built_doc.findall("PAGEOBJECT"):
                if po.attrib.get("PTYPE") == "4":
                    story = po.find("StoryText")
                    paras = [c for c in story if c.tag == "para"]
                    trails = [c for c in story if c.tag == "trail"]
                    if paras and any(p.attrib.get("ALIGN") == "0" for p in paras):
                        # Assert ALIGN=0 made it onto the para
                        self.assertEqual(paras[0].attrib.get("ALIGN"), "0")
                        self.assertEqual(trails[0].attrib.get("ALIGN"), "1")
                        return
            self.fail("could not find the synthetic frame in the rebuilt SLA")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ConverterTask5BehaviorsTests(unittest.TestCase):
    """Unit tests for Task 5 converter changes:
    5a – emit brand=Brand.gruene_noe() and filter brand-default attrs,
    5b – omit xpos_pt/ypos_pt/width_pt/height_pt for non-inline frames,
    5c – omit custom_path= for CLIPEDIT=1 FRTYPE=3 rect frames.
    """

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sla_to_dsl_t5", str(ROOT / "tools" / "sla_to_dsl.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls.sla_to_dsl = mod

    def _fresh_convert(self, sla_path: Path) -> str:
        """Run the converter on sla_path in a tmpdir and return the build.py text."""
        import shutil
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        try:
            self.sla_to_dsl.convert(sla_path, tmp / "build.py",
                                    "test-id", tmp / "assets")
            return (tmp / "build.py").read_text(encoding="utf-8")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ---- 5a: Brand emission -------------------------------------------------

    def test_5a_brand_emitted_in_postkarte(self):
        """Converter emits brand=Brand.gruene_noe() in the Document() call."""
        code = self._fresh_convert(ROOT / "postkarte-vorlage-original.sla")
        self.assertIn("brand=Brand.gruene_noe()", code,
                      "Converter must emit brand=Brand.gruene_noe() in Document()")

    def test_5a_brand_emitted_in_plakat(self):
        """brand=Brand.gruene_noe() appears in Plakat conversion output."""
        code = self._fresh_convert(ROOT / "plakat-a1-hochformat-original.sla")
        self.assertIn("brand=Brand.gruene_noe()", code)

    def test_5a_brand_emitted_in_zeitung(self):
        """brand=Brand.gruene_noe() appears in Zeitung conversion output."""
        code = self._fresh_convert(ROOT / "gruene-zeitung-vorlage-original.sla")
        self.assertIn("brand=Brand.gruene_noe()", code)

    def test_5a_brand_colors_not_re_emitted(self):
        """add_color() calls for CI brand colors (Dunkelgrün, Gelb …) are absent."""
        code = self._fresh_convert(ROOT / "postkarte-vorlage-original.sla")
        for ci_color in ("Dunkelgrün", "Hellgrün", "Gelb", "Magenta",
                         "Dunkelgr", "Hellgr"):  # match partial to catch encoding variants
            # CI colors should NOT appear as add_color arguments
            self.assertNotIn(f'add_color("{ci_color}', code,
                             f"CI brand color {ci_color!r} must not be re-emitted via add_color()")

    def test_5a_palette_replaces_ci_not_emitted(self):
        """palette_replaces_ci= is NOT emitted — brand= handles it automatically."""
        code = self._fresh_convert(ROOT / "postkarte-vorlage-original.sla")
        self.assertNotIn("palette_replaces_ci", code,
                         "palette_replaces_ci must not appear; Brand sets it automatically")

    def test_5a_document_layer_not_emitted(self):
        """DocumentLayer list is NOT emitted — brand= supplies layers."""
        code = self._fresh_convert(ROOT / "postkarte-vorlage-original.sla")
        self.assertNotIn("DocumentLayer", code,
                         "DocumentLayer must not appear; Brand supplies the layer stack")

    # ---- 5b: Drop redundant pt kwargs for non-inline frames ----------------

    def test_5b_non_inline_frames_have_no_xpos_pt(self):
        """All occurrences of xpos_pt= in Postkarte belong to inline image frames."""
        code = self._fresh_convert(ROOT / "postkarte-vorlage-original.sla")
        # page_xpos_pt= is on add_page/add_master calls (page geometry), not frames.
        # Frame-level xpos_pt= must appear exactly as many times as inline_image_data=.
        xpos_count = code.count("xpos_pt=") - code.count("page_xpos_pt=")
        inline_count = code.count("inline_image_data=")
        self.assertEqual(xpos_count, inline_count,
                         f"xpos_pt= count ({xpos_count}) must equal "
                         f"inline_image_data= count ({inline_count}); "
                         f"non-inline frames must not carry xpos_pt=")

    def test_5b_plakat_inline_image_keeps_xpos_pt(self):
        """Inline image frames in Plakat DO carry xpos_pt= for precision."""
        code = self._fresh_convert(ROOT / "plakat-a1-hochformat-original.sla")
        # Plakat has 1 inline image frame; it must keep xpos_pt.
        # page_xpos_pt= on add_page calls is distinct; subtract those.
        xpos_count = code.count("xpos_pt=") - code.count("page_xpos_pt=")
        inline_count = code.count("inline_image_data=")
        self.assertGreater(inline_count, 0,
                           "Plakat must have inline_image_data= for its logo")
        self.assertEqual(xpos_count, inline_count,
                         f"Plakat: frame xpos_pt= ({xpos_count}) must match "
                         f"inline image count ({inline_count})")

    def test_5b_zeitung_inline_images_keep_xpos_pt(self):
        """Zeitung has 6 inline images; xpos_pt= count matches inline image count."""
        code = self._fresh_convert(ROOT / "gruene-zeitung-vorlage-original.sla")
        # page_xpos_pt= on add_page/add_master calls must not be counted.
        xpos_count = code.count("xpos_pt=") - code.count("page_xpos_pt=")
        inline_count = code.count("inline_image_data=")
        self.assertEqual(xpos_count, inline_count,
                         f"xpos_pt= count ({xpos_count}) must equal "
                         f"inline_image_data= count ({inline_count})")

    # ---- 5c: Clip-rect auto-generation (converter side) --------------------

    def test_5c_zeitung_clip_rect_frames_omit_custom_path(self):
        """Zeitung's 86 CLIPEDIT=1 FRTYPE=3 rect frames produce no custom_path=."""
        code = self._fresh_convert(ROOT / "gruene-zeitung-vorlage-original.sla")
        # The Zeitung has 86 FRTYPE=3 frames whose path is a rectangle.
        # After Task 5c the converter must omit custom_path= for all of them.
        # We count custom_path= occurrences: only non-rect bezier curves should remain.
        custom_path_count = code.count("custom_path=")
        # Zeitung has 0 non-rect custom paths (all 86 FRTYPE=3 are rect)
        self.assertEqual(custom_path_count, 0,
                         f"Zeitung should have 0 custom_path= after Task 5c, "
                         f"got {custom_path_count}")

    def test_5c_postkarte_non_rect_bezier_keeps_custom_path(self):
        """Postkarte's non-rectangular bezier paths are preserved in custom_path=."""
        code = self._fresh_convert(ROOT / "postkarte-vorlage-original.sla")
        # Postkarte has non-rect custom paths (leaf/badge bezier curves)
        custom_path_count = code.count("custom_path=")
        self.assertGreater(custom_path_count, 0,
                           "Postkarte has non-rect bezier paths; custom_path= must be emitted")

    # ---- 5c: _is_rect_path unit tests --------------------------------------

    def test_5c_is_rect_path_right_first_winding(self):
        """_is_rect_path accepts right-first winding (M0 0 Lw 0 Lw h L0 h L0 0 Z)."""
        fn = self.sla_to_dsl._is_rect_path
        w, h = 100.0, 50.0
        path = f"M0 0 L{w} 0 L{w} {h} L0 {h} L0 0 Z"
        self.assertTrue(fn(path, w, h))

    def test_5c_is_rect_path_vertical_first_winding(self):
        """_is_rect_path accepts vertical-first winding (M0 0 L0 h Lw h Lw 0 L0 0 Z)."""
        fn = self.sla_to_dsl._is_rect_path
        w, h = 314.646, 436.535
        path = f"M0 0 L0 {h} L{w} {h} L{w} 0 L0 0 Z"
        self.assertTrue(fn(path, w, h))

    def test_5c_is_rect_path_with_float_precision(self):
        """_is_rect_path accepts Scribus-style truncated floats (%.4g precision)."""
        fn = self.sla_to_dsl._is_rect_path
        # Scribus stores coords with ~4 significant figures; 199.843 vs 199.8425…
        path = "M0 0 L199.843 0 L199.843 283.465 L0 283.465 L0 0 Z"
        self.assertTrue(fn(path, 199.8425196850394, 283.46456692913383))

    def test_5c_is_rect_path_non_rect_path_rejected(self):
        """_is_rect_path returns False for a non-rectangular bezier path."""
        fn = self.sla_to_dsl._is_rect_path
        bezier = "M0 0 C50 0 100 50 100 100 C100 150 50 200 0 200 Z"
        self.assertFalse(fn(bezier, 100.0, 200.0))

    def test_5c_is_rect_path_wrong_dimensions_rejected(self):
        """_is_rect_path returns False when path dimensions don't match frame."""
        fn = self.sla_to_dsl._is_rect_path
        w, h = 100.0, 50.0
        # Path for 200x100 frame, not 100x50
        path = f"M0 0 L200 0 L200 100 L0 100 L0 0 Z"
        self.assertFalse(fn(path, w, h))

    def test_5c_is_rect_path_non_origin_rect_rejected(self):
        """_is_rect_path returns False when rect doesn't start at origin."""
        fn = self.sla_to_dsl._is_rect_path
        # Rect offset from (0,0) — not a valid frame path
        path = "M10 10 L110 10 L110 60 L10 60 L10 10 Z"
        self.assertFalse(fn(path, 100.0, 50.0))

    def test_5c_is_rect_path_empty_string_rejected(self):
        """_is_rect_path returns False for empty or malformed strings."""
        fn = self.sla_to_dsl._is_rect_path
        self.assertFalse(fn("", 100.0, 50.0))
        self.assertFalse(fn("M0 0 Z", 100.0, 50.0))


if __name__ == "__main__":
    unittest.main()

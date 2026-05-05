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
        self.assertEqual(report.summary[sla_diff.SEVERITY_WARNING], 0,
                         msg=f"warning issues: "
                             f"{[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_WARNING]}")


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
            self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0)
            self.assertEqual(report.summary[sla_diff.SEVERITY_WARNING], 0)
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
        self.assertEqual(report.summary[sla_diff.SEVERITY_WARNING], 0,
                         msg=f"warning: {[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_WARNING]}")

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
    12 var pgno, 86 FRTYPE=3 paths, 6 inline images, 2 master pages, facing-pages."""

    TEMPLATE_DIR = ROOT / "templates" / "zeitung-a4-grun"
    ORIGINAL = ROOT / "gruene-zeitung-vorlage-original.sla"

    def test_diff_against_original_clean(self):
        sla = _run_build(self.TEMPLATE_DIR / "build.py")
        report = _diff_clean(self.ORIGINAL, sla)
        self.assertEqual(report.summary[sla_diff.SEVERITY_CRITICAL], 0,
                         msg=f"critical: {[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_CRITICAL]}")
        self.assertEqual(report.summary[sla_diff.SEVERITY_WARNING], 0,
                         msg=f"warning: {[i.short() for i in report.issues if i.severity == sla_diff.SEVERITY_WARNING]}")

    def test_chain_topology_intact(self):
        sla = _run_build(self.TEMPLATE_DIR / "build.py")
        report = _diff_clean(self.ORIGINAL, sla)
        chain_issues = [i for i in report.issues
                        if i.code.startswith("chain-")]
        self.assertEqual(chain_issues, [],
                         msg=f"chain issues: {[i.short() for i in chain_issues]}")


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


if __name__ == "__main__":
    unittest.main()

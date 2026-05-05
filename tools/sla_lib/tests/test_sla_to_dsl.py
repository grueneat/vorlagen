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


if __name__ == "__main__":
    unittest.main()

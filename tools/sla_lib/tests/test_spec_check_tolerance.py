"""Tests for spec_check 0.5mm tolerance + severity buckets (Issue #12 D8)."""
from __future__ import annotations
import io
import sys
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import spec_check as sc  # noqa: E402


# ---------------------------------------------------------------------------
# _classify bucketing
# ---------------------------------------------------------------------------
class ClassifyBucketTests(unittest.TestCase):
    def test_zero_silent(self):
        self.assertEqual(sc._classify(0.0, 0.5), "silent")

    def test_below_silent_threshold(self):
        self.assertEqual(sc._classify(0.03, 0.5), "silent")

    def test_just_at_silent_threshold(self):
        # <0.05 silent, ==0.05 info (>=)
        self.assertEqual(sc._classify(0.05, 0.5), "info")

    def test_within_tolerance(self):
        self.assertEqual(sc._classify(0.2, 0.5), "info")
        self.assertEqual(sc._classify(0.45, 0.5), "info")

    def test_at_tolerance_boundary(self):
        self.assertEqual(sc._classify(0.5, 0.5), "info")

    def test_above_tolerance_error(self):
        self.assertEqual(sc._classify(0.6, 0.5), "error")
        self.assertEqual(sc._classify(1.0, 0.5), "error")

    def test_legacy_0_1_tolerance_keeps_old_behavior(self):
        # With tolerance 0.1, the 0.2mm drift is now error (was already)
        self.assertEqual(sc._classify(0.2, 0.1), "error")
        # 0.05mm is info (was previously also info-equivalent)
        self.assertEqual(sc._classify(0.05, 0.1), "info")


# ---------------------------------------------------------------------------
# Synthetic spec/SLA fixture for end-to-end check()
# ---------------------------------------------------------------------------
def _write_spec_and_sla(tmp: Path, slug: str, spec_x: float, sla_x: float):
    """Write a minimal spec markdown + a stub template.sla so spec_check
    can read both. The frame's anname is "TestFrame"; only x_mm differs.
    """
    specs_dir = tmp / "templates" / "_specs"
    tmpl_dir = tmp / "templates" / slug
    specs_dir.mkdir(parents=True, exist_ok=True)
    tmpl_dir.mkdir(parents=True, exist_ok=True)

    spec_md = textwrap.dedent(f"""\
        # spec for {slug}

        ```yaml
        slots:
          - anname: "TestFrame"
            x_mm: {spec_x}
            y_mm: 10
            w_mm: 50
            h_mm: 20
        ```
    """)
    (specs_dir / f"{slug}.md").write_text(spec_md, encoding="utf-8")

    PT = sc.PT_PER_MM
    sla_xml = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <SCRIBUSUTF8NEW Version="1.6.5">
          <DOCUMENT>
            <PAGE PAGEXPOS="0" PAGEYPOS="0" PAGEWIDTH="595" PAGEHEIGHT="842" NUM="0"/>
            <PAGEOBJECT XPOS="{sla_x * PT}" YPOS="{10 * PT}" WIDTH="{50 * PT}" HEIGHT="{20 * PT}" OwnPage="0" PTYPE="4" ANNAME="TestFrame"/>
          </DOCUMENT>
        </SCRIBUSUTF8NEW>
    """)
    (tmpl_dir / "template.sla").write_text(sla_xml, encoding="utf-8")


class CheckEndToEndTests(unittest.TestCase):
    def _run(self, spec_x: float, sla_x: float, tol: float = 0.5):
        with TemporaryDirectory() as td:
            tmp = Path(td)
            slug = "fixture"
            _write_spec_and_sla(tmp, slug, spec_x, sla_x)
            # Monkey-patch the module's path constants
            orig_specs = sc.SPECS_DIR
            orig_tmpl = sc.TEMPLATES_DIR
            sc.SPECS_DIR = tmp / "templates" / "_specs"
            sc.TEMPLATES_DIR = tmp / "templates"
            try:
                return sc.check(slug, tolerance_mm=tol)
            finally:
                sc.SPECS_DIR = orig_specs
                sc.TEMPLATES_DIR = orig_tmpl

    def test_zero_drift_silent(self):
        errors, msgs = self._run(spec_x=20.0, sla_x=20.0)
        self.assertEqual(errors, 0)
        # Message list contains no "info:" or "error:" lines for x_mm
        info_or_err = [m for m in msgs if "x_mm" in m]
        self.assertEqual(info_or_err, [])

    def test_silent_threshold_below_005(self):
        errors, msgs = self._run(spec_x=20.0, sla_x=20.03)
        self.assertEqual(errors, 0)
        info_or_err = [m for m in msgs if "x_mm" in m]
        self.assertEqual(info_or_err, [])

    def test_info_drift_logged_non_blocking(self):
        errors, msgs = self._run(spec_x=20.0, sla_x=20.2)
        self.assertEqual(errors, 0)
        info_lines = [m for m in msgs if m.startswith("info:") and "x_mm" in m]
        self.assertEqual(len(info_lines), 1)

    def test_info_at_tolerance_boundary(self):
        errors, msgs = self._run(spec_x=20.0, sla_x=20.45)
        self.assertEqual(errors, 0)
        info_lines = [m for m in msgs if m.startswith("info:") and "x_mm" in m]
        self.assertEqual(len(info_lines), 1)

    def test_error_above_tolerance(self):
        errors, msgs = self._run(spec_x=20.0, sla_x=20.6)
        self.assertEqual(errors, 1)
        err_lines = [m for m in msgs if m.startswith("error:") and "x_mm" in m]
        self.assertEqual(len(err_lines), 1)

    def test_error_large_drift(self):
        errors, msgs = self._run(spec_x=20.0, sla_x=21.0)
        self.assertEqual(errors, 1)

    def test_legacy_tolerance_0_1(self):
        # 0.2mm drift exceeds 0.1 tol → error in legacy mode
        errors, msgs = self._run(spec_x=20.0, sla_x=20.2, tol=0.1)
        self.assertEqual(errors, 1)


# ---------------------------------------------------------------------------
# YAML float-coordinate parsing (D8: spec slots accept floats with 1 decimal)
# ---------------------------------------------------------------------------
class FloatCoordinateParsingTests(unittest.TestCase):
    def _run(self, x_decl: str) -> tuple[int, list[str]]:
        with TemporaryDirectory() as td:
            tmp = Path(td)
            slug = "fl"
            specs_dir = tmp / "templates" / "_specs"
            tmpl_dir = tmp / "templates" / slug
            specs_dir.mkdir(parents=True)
            tmpl_dir.mkdir(parents=True)
            spec_md = textwrap.dedent(f"""\
                ```yaml
                slots:
                  - anname: "F"
                    x_mm: {x_decl}
                    y_mm: 10
                    w_mm: 50
                    h_mm: 20
                ```
            """)
            (specs_dir / f"{slug}.md").write_text(spec_md, encoding="utf-8")
            PT = sc.PT_PER_MM
            sla_x_mm = 12.5
            sla_xml = textwrap.dedent(f"""\
                <?xml version="1.0" encoding="UTF-8"?>
                <SCRIBUSUTF8NEW Version="1.6.5">
                  <DOCUMENT>
                    <PAGE PAGEXPOS="0" PAGEYPOS="0" PAGEWIDTH="595" PAGEHEIGHT="842" NUM="0"/>
                    <PAGEOBJECT XPOS="{sla_x_mm * PT}" YPOS="{10 * PT}" WIDTH="{50 * PT}" HEIGHT="{20 * PT}" OwnPage="0" PTYPE="4" ANNAME="F"/>
                  </DOCUMENT>
                </SCRIBUSUTF8NEW>
            """)
            (tmpl_dir / "template.sla").write_text(sla_xml, encoding="utf-8")
            orig_specs = sc.SPECS_DIR
            orig_tmpl = sc.TEMPLATES_DIR
            sc.SPECS_DIR = specs_dir
            sc.TEMPLATES_DIR = tmp / "templates"
            try:
                return sc.check(slug, tolerance_mm=0.5)
            finally:
                sc.SPECS_DIR = orig_specs
                sc.TEMPLATES_DIR = orig_tmpl

    def test_float_one_decimal_parses(self):
        # Spec declares 12.5; SLA carries 12.5 — silent.
        errors, msgs = self._run("12.5")
        self.assertEqual(errors, 0)
        info_or_err = [m for m in msgs if "x_mm" in m]
        self.assertEqual(info_or_err, [])

    def test_int_legacy_still_parses(self):
        # Spec declares 12 (int); SLA at 12.5 — drift 0.5mm exactly at tol → info.
        errors, msgs = self._run("12")
        self.assertEqual(errors, 0)
        info_lines = [m for m in msgs if m.startswith("info:") and "x_mm" in m]
        self.assertEqual(len(info_lines), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

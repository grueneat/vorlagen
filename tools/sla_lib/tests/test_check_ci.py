"""Unit tests for tools/check_ci.py — synthetic SLA fragments with known drift."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from check_ci import (  # noqa: E402
    check_sla,
    load_ci,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    SEVERITY_INFO,
)


CLEAN_SLA = """<?xml version="1.0" encoding="UTF-8"?>
<SCRIBUSUTF8NEW Version="1.6.5">
  <DOCUMENT>
    <COLOR NAME="Black" SPACE="CMYK" C="0" M="0" Y="0" K="100"/>
    <COLOR NAME="White" SPACE="CMYK" C="0" M="0" Y="0" K="0"/>
    <COLOR NAME="Dunkelgrün" SPACE="CMYK" C="85" M="35" Y="95" K="10"/>
    <COLOR NAME="Gelb" SPACE="CMYK" C="0" M="0" Y="100" K="0"/>
    <STYLE NAME="ci/default" ALIGN="0" FONT="Gotham Narrow Book" FONTSIZE="12" FCOLOR="White"/>
    <STYLE NAME="ci/headline-ultra" ALIGN="1" FONT="Gotham Narrow Ultra" FONTSIZE="27" FCOLOR="White"/>
  </DOCUMENT>
</SCRIBUSUTF8NEW>
"""

DRIFT_SLA = """<?xml version="1.0" encoding="UTF-8"?>
<SCRIBUSUTF8NEW Version="1.6.5">
  <DOCUMENT>
    <COLOR NAME="Black" SPACE="CMYK" C="0" M="0" Y="0" K="100"/>
    <COLOR NAME="White" SPACE="CMYK" C="0" M="0" Y="0" K="0"/>
    <!-- WRONG: Dunkelgrün has different CMYK -->
    <COLOR NAME="Dunkelgrün" SPACE="CMYK" C="50" M="0" Y="50" K="0"/>
    <!-- EXTRA: legacy RGB-Green color leaked in -->
    <COLOR NAME="Green" SPACE="RGB" R="0" G="255" B="0"/>
    <STYLE NAME="LegacyHeadline" FONT="Helvetica" FONTSIZE="20" FCOLOR="Black"/>
    <STYLE NAME="ci/headline-ultra" ALIGN="1" FONT="Gotham Narrow Ultra" FONTSIZE="27" FCOLOR="White"/>
  </DOCUMENT>
</SCRIBUSUTF8NEW>
"""


class CheckCIBasic(unittest.TestCase):
    def setUp(self) -> None:
        self.ci = load_ci(ROOT / "shared" / "ci.yml")

    def _write(self, content: str) -> Path:
        f = tempfile.NamedTemporaryFile("w", suffix=".sla", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return Path(f.name)

    def test_clean_minimal(self):
        path = self._write(CLEAN_SLA)
        report = check_sla(path, self.ci)
        critical = [i for i in report.issues if i.severity == SEVERITY_CRITICAL]
        warnings = [i for i in report.issues if i.severity == SEVERITY_WARNING]
        # No critical, no warnings expected
        self.assertEqual(critical, [])
        self.assertEqual(warnings, [])

    def test_drift_detected(self):
        path = self._write(DRIFT_SLA)
        report = check_sla(path, self.ci)
        codes = [i.code for i in report.issues]
        self.assertIn("color-drift", codes)       # Dunkelgrün wrong CMYK
        self.assertIn("extra-color", codes)       # Green
        self.assertIn("extra-style", codes)       # LegacyHeadline
        # color-drift is critical
        critical = [i for i in report.issues if i.severity == SEVERITY_CRITICAL]
        self.assertTrue(any(i.code == "color-drift" for i in critical))


class CheckCIAgainstOriginals(unittest.TestCase):
    """Confirm the originals show the documented drift."""

    def setUp(self) -> None:
        self.ci = load_ci(ROOT / "shared" / "ci.yml")

    def test_postkarte_has_extra_green(self):
        report = check_sla(ROOT / "postkarte-vorlage-original.sla", self.ci)
        extra_colors = [
            i for i in report.issues
            if i.code == "extra-color" and i.detail.get("name") == "Green"
        ]
        self.assertEqual(len(extra_colors), 1)

    def test_zeitung_has_extra_green(self):
        report = check_sla(ROOT / "gruene-zeitung-vorlage-original.sla", self.ci)
        extra_colors = [
            i for i in report.issues
            if i.code == "extra-color" and i.detail.get("name") == "Green"
        ]
        self.assertEqual(len(extra_colors), 1)

    def test_plakat_has_no_extra_green(self):
        report = check_sla(ROOT / "plakat-a1-hochformat-original.sla", self.ci)
        extra_colors = [
            i for i in report.issues
            if i.code == "extra-color" and i.detail.get("name") == "Green"
        ]
        self.assertEqual(extra_colors, [])


if __name__ == "__main__":
    unittest.main()

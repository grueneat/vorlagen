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


if __name__ == "__main__":
    unittest.main()

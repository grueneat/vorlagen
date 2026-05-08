"""Tests for structural_check orchestrator + meta_schema validation.

Synthetic build modules are written to a tmp templates/<slug>/build.py
and loaded via the orchestrator's importlib loader. The --all real-
templates integration runs only after Task 6 wires build_doc() onto
all 8 templates — flag-skipped here.
"""
from __future__ import annotations
import json
import sys
import textwrap
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import structural_check as sc  # noqa: E402
from sla_lib.builder.meta_schema import load_brand_overrides  # noqa: E402


# Whether to enable the --all real-templates smoke test.  The plan says
# this lights up at the end of Task 6 once every template exposes
# build_doc().  We auto-detect: if all real templates expose build_doc(),
# the test runs.  Otherwise it's skipped.
def _all_have_build_doc() -> bool:
    slugs = sc.discover_template_slugs(ROOT)
    if not slugs:
        return False
    for s in slugs:
        try:
            mod = sc._load_build_module(s, ROOT)
        except Exception:
            return False
        if not hasattr(mod, "build_doc"):
            return False
    return True


# ---------------------------------------------------------------------------
# tmp template scaffolding helpers
# ---------------------------------------------------------------------------
def _write_template(tmp: Path, slug: str, build_py: str, meta_yml: str = "") -> Path:
    """Lay out a workspace-shaped tree at ``tmp`` containing
    templates/<slug>/build.py and an optional meta.yml.
    """
    (tmp / "templates" / slug).mkdir(parents=True, exist_ok=True)
    (tmp / "templates" / slug / "build.py").write_text(build_py, encoding="utf-8")
    if meta_yml:
        (tmp / "templates" / slug / "meta.yml").write_text(meta_yml, encoding="utf-8")
    return tmp


_SAMPLE_BUILD_PASSING = """\
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from sla_lib.builder import (
    Document, TextFrame, same_y, inside,
)

def build_doc():
    d = Document(title="t", template_id="t")
    page = d.add_page(size="A6")
    a = TextFrame(x_mm=10, y_mm=20, w_mm=20, h_mm=10, anname="A")
    b = TextFrame(x_mm=40, y_mm=20, w_mm=20, h_mm=10, anname="B")
    page.add(a)
    page.add(b)
    return d

CONSTRAINTS = [same_y("A", "B")]
"""

_SAMPLE_BUILD_FAILING = """\
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from sla_lib.builder import (
    Document, TextFrame, same_y, inside,
)

def build_doc():
    d = Document(title="t", template_id="t")
    page = d.add_page(size="A6")
    a = TextFrame(x_mm=10, y_mm=20, w_mm=20, h_mm=10, anname="A")
    b = TextFrame(x_mm=40, y_mm=80, w_mm=20, h_mm=10, anname="B")
    page.add(a)
    page.add(b)
    return d

CONSTRAINTS = [same_y("A", "B")]
"""

_SAMPLE_BUILD_ORPHAN = """\
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from sla_lib.builder import Document, TextFrame, same_y

def build_doc():
    d = Document(title="t", template_id="t")
    d.add_page(size="A6")
    return d

CONSTRAINTS = [same_y("Foo", "Bar")]
"""

_SAMPLE_BUILD_NO_BUILD_DOC = """\
def build():
    return None
"""


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------
def _brand_overrides_for_synthetic() -> str:
    """Override every brand rule that the default CI palette violates.

    The CI ParaStyle defaults in shared/ci.yml have linesp/fontsize
    ratios that are NOT exactly 0.9 (e.g. 13/12 = 1.083) — this is
    real-world drift that Phase 4 captures via meta.yml overrides. For
    Task 5 synthetic tests, we override the offending rules so the
    constraint-level pass/fail/warn semantics can be tested in
    isolation.
    """
    return textwrap.dedent("""\
        brand_overrides:
          - id: brand:line_spacing_0.9
            reason: "synthetic test — CI palette default ratios drift; covered by Phase 4 on real templates"
    """)


class CheckTemplateTests(unittest.TestCase):
    def test_passing_constraint(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            _write_template(root, "passing", _SAMPLE_BUILD_PASSING,
                             _brand_overrides_for_synthetic())
            rep = sc.check_template("passing", root)
            self.assertIsNone(rep.fatal_error)
            # exactly one constraint with severity=pass
            passes = [i for i in rep.constraint_issues if i.severity == "pass"]
            self.assertEqual(len(passes), 1)
            # No CONSTRAINTS-level errors (brand-rule errors handled by overrides)
            errs_constraint = [i for i in rep.constraint_issues if i.severity == "error"]
            self.assertEqual(errs_constraint, [])

    def test_failing_constraint(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            _write_template(root, "failing", _SAMPLE_BUILD_FAILING,
                             _brand_overrides_for_synthetic())
            rep = sc.check_template("failing", root)
            errs = [i for i in rep.constraint_issues if i.severity == "error"]
            self.assertEqual(len(errs), 1)
            self.assertTrue(rep.has_errors)

    def test_orphan_anname_warning(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            _write_template(root, "orphan", _SAMPLE_BUILD_ORPHAN,
                             _brand_overrides_for_synthetic())
            rep = sc.check_template("orphan", root)
            warns = [i for i in rep.constraint_issues if i.severity == "warning"]
            self.assertEqual(len(warns), 1)
            errs_constraint = [i for i in rep.constraint_issues if i.severity == "error"]
            self.assertEqual(errs_constraint, [])

    def test_missing_build_doc_fatal(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            _write_template(root, "no_bd", _SAMPLE_BUILD_NO_BUILD_DOC)
            rep = sc.check_template("no_bd", root)
            self.assertIsNotNone(rep.fatal_error)
            self.assertIn("build_doc", rep.fatal_error)
            self.assertTrue(rep.has_errors)

    def test_meta_yml_brand_override_skips_rule(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            meta = textwrap.dedent("""\
                brand_overrides:
                  - id: brand:logo_size_3M
                    reason: "test override for unit suite"
            """)
            _write_template(root, "ovrd", _SAMPLE_BUILD_PASSING, meta)
            rep = sc.check_template("ovrd", root)
            ids = [rid for rid, _ in rep.skipped_brand_rules]
            self.assertIn("brand:logo_size_3M", ids)


class MarkdownOutputTests(unittest.TestCase):
    def test_markdown_renders_all_sections(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            _write_template(root, "md", _SAMPLE_BUILD_PASSING)
            rep = sc.check_template("md", root)
            md = rep.to_markdown()
            self.assertIn("templates/md", md)
            self.assertIn("CONSTRAINTS", md)
            self.assertIn("BRAND_CONSTRAINTS", md)
            self.assertIn("Result:", md)


class CliExitCodeTests(unittest.TestCase):
    def test_exit_zero_on_pass(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            _write_template(root, "ok", _SAMPLE_BUILD_PASSING,
                             _brand_overrides_for_synthetic())
            rc = sc.main(["ok", "--root", str(root)])
            self.assertEqual(rc, 0)

    def test_exit_one_on_constraint_failure(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            _write_template(root, "bad", _SAMPLE_BUILD_FAILING,
                             _brand_overrides_for_synthetic())
            rc = sc.main(["bad", "--root", str(root)])
            self.assertEqual(rc, 1)

    def test_exit_zero_on_warning_only(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            _write_template(root, "warn", _SAMPLE_BUILD_ORPHAN,
                             _brand_overrides_for_synthetic())
            rc = sc.main(["warn", "--root", str(root)])
            self.assertEqual(rc, 0)


class MetaSchemaTests(unittest.TestCase):
    def test_valid_overrides_returns_ids(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            slug = "schema_ok"
            (root / "templates" / slug).mkdir(parents=True)
            (root / "templates" / slug / "meta.yml").write_text(textwrap.dedent("""\
                brand_overrides:
                  - id: brand:logo_size_3M
                    reason: "test"
                  - id: brand:hl_sl_distance_x2
                    reason: "test 2"
            """), encoding="utf-8")
            ids = load_brand_overrides(slug, root)
            self.assertEqual(ids, {"brand:logo_size_3M", "brand:hl_sl_distance_x2"})

    def test_missing_file_returns_empty_set(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            self.assertEqual(load_brand_overrides("nope", root), set())

    def test_malformed_id_pattern_raises(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            slug = "bad"
            (root / "templates" / slug).mkdir(parents=True)
            (root / "templates" / slug / "meta.yml").write_text(textwrap.dedent("""\
                brand_overrides:
                  - id: not_a_brand_id
                    reason: "x"
            """), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_brand_overrides(slug, root)

    def test_missing_reason_raises(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            slug = "noReason"
            (root / "templates" / slug).mkdir(parents=True)
            (root / "templates" / slug / "meta.yml").write_text(textwrap.dedent("""\
                brand_overrides:
                  - id: brand:logo_size_3M
            """), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_brand_overrides(slug, root)

    def test_unknown_id_warns_not_raises(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            root = Path(td)
            slug = "unkn"
            (root / "templates" / slug).mkdir(parents=True)
            (root / "templates" / slug / "meta.yml").write_text(textwrap.dedent("""\
                brand_overrides:
                  - id: brand:unknown_rule
                    reason: "typo on purpose"
            """), encoding="utf-8")
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter("always")
                ids = load_brand_overrides(slug, root)
            self.assertEqual(ids, {"brand:unknown_rule"})
            self.assertTrue(any("brand:unknown_rule" in str(w.message) for w in ws))


@unittest.skipUnless(_all_have_build_doc(),
                     "all real templates must expose build_doc() — runs after Task 6")
class AllRealTemplatesIntegrationTests(unittest.TestCase):
    def test_all_templates_callable_via_build_doc(self):
        slugs = sc.discover_template_slugs(ROOT)
        self.assertGreaterEqual(len(slugs), 1)
        for slug in slugs:
            with self.subTest(slug=slug):
                rep = sc.check_template(slug, ROOT)
                # build_doc itself must succeed (constraint/brand failures
                # are EXPECTED in Phase 4 before brand_overrides are added).
                self.assertIsNone(rep.fatal_error,
                                  msg=f"{slug}: {rep.fatal_error}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

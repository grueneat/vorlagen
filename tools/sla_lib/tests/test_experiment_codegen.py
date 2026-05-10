"""Variant-codegen unit tests (issue #30 T16a).

Three test classes mirror the codegen tool's responsibilities:

  - ``PromptRenderingTest`` — envelope, scaffolding contract, DSL
    signature, and reference files all substitute into the prompt and
    the hypothesis fields are visible.
  - ``ModuleValidationTest`` — synthetic good Python passes; synthetic
    envelope-violating Python is rejected.
  - ``SkipExistingTest`` — slugs with an existing ``.py`` builder are
    skipped unless ``--force`` is set.

Subprocess fan-out is bypassed via ``runner_overrides`` (canned LLM
output), the same pattern the hypothesis-gen tests use.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import experiment_codegen as cg  # noqa: E402
from experiment_envelope import load_envelope  # noqa: E402


# ---------------------------------------------------------------------------
# Test fixtures — small but complete enough to exercise envelope + render
# ---------------------------------------------------------------------------

# A variant module that re-emits production P2 verbatim — known to pass
# the envelope (this is the test_experiment_render fixture pattern).
GOOD_VARIANT_SOURCE = """\
from __future__ import annotations


def render_p2(doc, page) -> None:
    from variant_scaffold import render_p2_default

    render_p2_default(doc, page)
"""

# A variant module that emits a frame far outside the page bbox — this
# will trip brand:inside_page and (depending on envelope) other geometry
# rules. The envelope-violation path must reject it.
BAD_VARIANT_SOURCE = """\
from __future__ import annotations

from sla_lib.builder import Run, TextFrame


def render_p2(doc, page) -> None:
    from variant_scaffold import render_p2_default

    render_p2_default(doc, page)
    page.add(TextFrame(
        x_mm=600, y_mm=600, w_mm=200, h_mm=50,
        layer=2, style='falzflyer/top-title',
        runs=[Run(text='oops',
                  paragraph_style='falzflyer/top-title')],
        anname='P2 Overflow',
    ))
"""

# Source the LLM "emitted" wrapped in a ```python fence — the extractor
# must strip the fence before writing.
FENCED_GOOD_RESPONSE = "Here is the file:\n\n```python\n" + GOOD_VARIANT_SOURCE + "```\nDone.\n"


def _fake_proc(stdout: str) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr="", returncode=0)


def _make_manifest(slugs: list[str]) -> dict:
    return {
        "id": "test-codegen-exp",
        "subject": "falzflyer-p2-mein-plan-v2",
        "target_weak_area": "test fixture",
        "contributing_llms": ["fixture:claude", "fixture:codex"],
        "created": "2026-05-10",
        "prompt_version": "test",
        "hypotheses": [
            {
                "slug": slug,
                "name": f"Fixture hypothesis {i}",
                "axis_commitments": ["density"],
                "rationale": "Fixture; re-emits production P2.",
                "expected_outcome": "Test fixture.",
                "sources": ["fixture:claude"],
                "builder": f"variants/{slug}.py",
                "wildcard": (i == 0),
            }
            for i, slug in enumerate(slugs)
        ],
    }


def _setup_experiment(exp_id: str) -> Path:
    """Create a real experiment dir under ROOT with manifest + constraints."""
    exp_dir = ROOT / "experiments" / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "variants").mkdir(parents=True, exist_ok=True)

    manifest = _make_manifest([
        f"fixture-slug-{i:02d}" for i in range(1, 11)
    ])
    (exp_dir / "manifest.yml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    (exp_dir / "constraints.yml").write_text(
        yaml.safe_dump({
            "extends": str(
                ROOT / "experiments" / "_constraints"
                / "falzflyer-default.yml"
            ),
            "tested_axis": "density+form",
        }),
        encoding="utf-8",
    )
    return exp_dir


def _teardown_experiment(exp_dir: Path) -> None:
    if exp_dir.exists():
        shutil.rmtree(exp_dir)


# ---------------------------------------------------------------------------
# Prompt-rendering test
# ---------------------------------------------------------------------------

class PromptRenderingTest(unittest.TestCase):
    """Envelope + scaffolding + reference files all substitute correctly."""

    def setUp(self):
        raw = tempfile.mkdtemp(prefix="codegen_prompt_")
        self.tmp_root = Path(raw)
        slug = "test-codegen-prompt-" + raw.rsplit("/", 1)[-1].lower().replace("_", "-")
        # ROOT-relative exp_id (codegen reads from ROOT/experiments).
        clean = "".join(c for c in slug if c.isalnum() or c == "-").strip("-")
        self.exp_id = f"test-{clean[-20:]}"
        self.exp_dir = _setup_experiment(self.exp_id)

    def tearDown(self):
        _teardown_experiment(self.exp_dir)
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_prompt_includes_all_required_sections(self):
        # Drop the 3 retained variant files into the test experiment so
        # _read_reference_files has something to embed.
        for slug in cg.REFERENCE_SLUGS_DEFAULT:
            src = (
                ROOT / "experiments" / "falzflyer-p2-mein-plan-v2"
                / "variants" / f"{slug}.py"
            )
            if src.exists():
                shutil.copy2(src, self.exp_dir / "variants" / f"{slug}.py")

        envelope = load_envelope(self.exp_dir)
        references_blob = cg._read_reference_files(self.exp_dir)
        hypothesis = {
            "slug": "novel-strategy-x",
            "name": "Novel strategy X with explicit hierarchy",
            "axis_commitments": ["density", "hierarchy"],
            "rationale": "Detailed rationale for novel strategy X.",
            "expected_outcome": "Higher transport.",
            "wildcard": False,
        }
        prompt = cg.render_prompt(
            hypothesis=hypothesis,
            envelope=envelope,
            references_blob=references_blob,
        )

        # Hypothesis fields appear verbatim.
        self.assertIn("novel-strategy-x", prompt)
        self.assertIn("Novel strategy X with explicit hierarchy", prompt)
        self.assertIn("`density`", prompt)
        self.assertIn("`hierarchy`", prompt)
        self.assertIn("Detailed rationale for novel strategy X.", prompt)
        self.assertIn("Higher transport.", prompt)

        # Envelope-derived rule listing is present (brand_rules header).
        self.assertIn("Brand rules", prompt)
        self.assertIn("brand:inside_page", prompt)
        self.assertIn("Layer-1 thresholds", prompt)
        self.assertIn("Tested axis", prompt)

        # DSL signature + scaffold contract appear.
        self.assertIn("sla_lib.builder", prompt)
        self.assertIn("render_p2(doc, page)", prompt)
        self.assertIn("Scaffold contract", prompt)
        self.assertIn('"P2 "', prompt)

        # Reference files are embedded.
        self.assertIn("Reference: `numbered-priority-list-v2`", prompt)
        self.assertIn("Reference: `manifesto-single-statement-v2`", prompt)
        self.assertIn("Reference: `dunkelgrun-rules-between-items-v2`", prompt)

        # Output contract is present and clear.
        self.assertIn("Output the Python file and nothing else", prompt)


# ---------------------------------------------------------------------------
# Module-validation test
# ---------------------------------------------------------------------------

class ModuleValidationTest(unittest.TestCase):

    def setUp(self):
        raw = tempfile.mkdtemp(prefix="codegen_validate_")
        self.tmp_root = Path(raw)
        clean = "".join(c for c in raw.rsplit("/", 1)[-1].lower() if c.isalnum() or c == "-").strip("-")
        self.exp_id = f"test-{clean[-20:]}"
        self.exp_dir = _setup_experiment(self.exp_id)

    def tearDown(self):
        _teardown_experiment(self.exp_dir)
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_good_module_passes_envelope(self):
        slug = "fixture-slug-01"
        target = self.exp_dir / "variants" / f"{slug}.py"
        target.write_text(GOOD_VARIANT_SOURCE, encoding="utf-8")

        envelope = load_envelope(self.exp_dir)
        violations = cg.validate_variant_module(
            py_path=target, slug=slug, envelope=envelope,
        )
        self.assertEqual(
            violations, [],
            f"good variant should pass envelope; got {violations}",
        )

    def test_envelope_violation_is_caught(self):
        slug = "fixture-slug-02"
        target = self.exp_dir / "variants" / f"{slug}.py"
        target.write_text(BAD_VARIANT_SOURCE, encoding="utf-8")

        envelope = load_envelope(self.exp_dir)
        violations = cg.validate_variant_module(
            py_path=target, slug=slug, envelope=envelope,
        )
        self.assertGreater(
            len(violations), 0,
            "overflow variant must produce >=1 envelope violation",
        )
        rule_ids = {v.rule_id for v in violations}
        # brand:inside_page must fire on an off-page frame.
        self.assertIn(
            "brand:inside_page", rule_ids,
            f"expected brand:inside_page violation; got {rule_ids}",
        )

    def test_missing_render_p2_raises(self):
        slug = "fixture-slug-03"
        target = self.exp_dir / "variants" / f"{slug}.py"
        target.write_text(
            "from __future__ import annotations\n\n"
            "def not_render_p2(doc, page): pass\n",
            encoding="utf-8",
        )
        envelope = load_envelope(self.exp_dir)
        with self.assertRaises(cg.CodegenValidationError) as ctx:
            cg.validate_variant_module(
                py_path=target, slug=slug, envelope=envelope,
            )
        self.assertIn("render_p2", str(ctx.exception))


# ---------------------------------------------------------------------------
# Skip-existing + integration test
# ---------------------------------------------------------------------------

class SkipExistingTest(unittest.TestCase):

    def setUp(self):
        raw = tempfile.mkdtemp(prefix="codegen_skip_")
        self.tmp_root = Path(raw)
        clean = "".join(c for c in raw.rsplit("/", 1)[-1].lower() if c.isalnum() or c == "-").strip("-")
        self.exp_id = f"test-{clean[-20:]}"
        self.exp_dir = _setup_experiment(self.exp_id)

    def tearDown(self):
        _teardown_experiment(self.exp_dir)
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_existing_py_is_not_regenerated(self):
        # Pre-populate one slug's builder; --only that slug; expect skip
        # (no call to runner_overrides).
        slug = "fixture-slug-01"
        target = self.exp_dir / "variants" / f"{slug}.py"
        marker = "# PRE-EXISTING SENTINEL — do not overwrite\n" + GOOD_VARIANT_SOURCE
        target.write_text(marker, encoding="utf-8")
        original_bytes = target.read_bytes()

        call_count = {"n": 0}

        def boom_runner(prompt):
            call_count["n"] += 1
            raise AssertionError(
                "runner should NOT be called when target exists and --force is False"
            )

        rc = cg.run_codegen(
            exp_id=self.exp_id,
            only=slug,
            force=False,
            llms=("claude",),
            runner_overrides={"claude": boom_runner},
            log=lambda _msg: None,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(call_count["n"], 0, "no LLM call should happen")
        self.assertEqual(
            target.read_bytes(), original_bytes,
            "pre-existing builder must not be overwritten",
        )

    def test_force_regenerates(self):
        slug = "fixture-slug-02"
        target = self.exp_dir / "variants" / f"{slug}.py"
        marker = "# STALE — should be overwritten\n" + BAD_VARIANT_SOURCE
        target.write_text(marker, encoding="utf-8")

        def good_runner(prompt):
            return _fake_proc(FENCED_GOOD_RESPONSE)

        rc = cg.run_codegen(
            exp_id=self.exp_id,
            only=slug,
            force=True,
            llms=("claude",),
            runner_overrides={"claude": good_runner},
            log=lambda _msg: None,
        )
        self.assertEqual(rc, 0)
        self.assertTrue(target.exists())
        new_text = target.read_text(encoding="utf-8")
        self.assertNotIn("STALE", new_text)
        self.assertIn("def render_p2", new_text)

        # Raw response was preserved under _llm-raw/codegen/.
        raw_dir = self.exp_dir / "_llm-raw" / "codegen"
        self.assertTrue(raw_dir.exists())
        raws = list(raw_dir.iterdir())
        self.assertGreaterEqual(len(raws), 1)

    def test_failing_llm_falls_back_to_second(self):
        slug = "fixture-slug-03"

        # Claude returns the bad (envelope-violating) source; codex
        # returns the good source. We expect the second LLM to win.
        call_log: list[str] = []

        def claude_bad(prompt):
            call_log.append("claude")
            return _fake_proc("```python\n" + BAD_VARIANT_SOURCE + "```")

        def codex_good(prompt):
            call_log.append("codex")
            return _fake_proc("```python\n" + GOOD_VARIANT_SOURCE + "```")

        rc = cg.run_codegen(
            exp_id=self.exp_id,
            only=slug,
            force=False,
            llms=("claude", "codex"),
            runner_overrides={"claude": claude_bad, "codex": codex_good},
            log=lambda _msg: None,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(call_log, ["claude", "codex"])

        target = self.exp_dir / "variants" / f"{slug}.py"
        self.assertTrue(target.exists())
        self.assertIn("render_p2_default", target.read_text(encoding="utf-8"))

    def test_all_llms_fail_leaves_no_file(self):
        slug = "fixture-slug-04"

        def claude_bad(prompt):
            return _fake_proc("```python\n" + BAD_VARIANT_SOURCE + "```")

        def codex_bad(prompt):
            return _fake_proc("not python at all, no fences either")

        rc = cg.run_codegen(
            exp_id=self.exp_id,
            only=slug,
            force=False,
            llms=("claude", "codex"),
            runner_overrides={"claude": claude_bad, "codex": codex_bad},
            log=lambda _msg: None,
        )
        # rc=0 even on per-slug failure (failures are non-fatal at the
        # run-level, mirroring experiment_render's drop behaviour).
        self.assertEqual(rc, 0)
        target = self.exp_dir / "variants" / f"{slug}.py"
        self.assertFalse(target.exists(), "failing slug must leave no builder")


# ---------------------------------------------------------------------------
# Extraction helper test
# ---------------------------------------------------------------------------

class ExtractPythonBlockTest(unittest.TestCase):

    def test_extracts_from_fenced_block(self):
        text = "Sure:\n```python\nimport x\ndef render_p2(d, p): pass\n```\n"
        out = cg.extract_python_block(text)
        self.assertIsNotNone(out)
        assert out is not None  # for type checker
        self.assertIn("def render_p2", out)
        self.assertNotIn("```", out)

    def test_returns_none_when_no_render_p2(self):
        text = "```python\nprint('hello')\n```"
        self.assertIsNone(cg.extract_python_block(text))

    def test_unwraps_claude_json_envelope(self):
        import json
        wrapper = json.dumps({
            "result": "```python\nimport x\ndef render_p2(d, p): pass\n```",
            "type": "result",
        })
        out = cg.extract_python_block(wrapper)
        self.assertIsNotNone(out)
        assert out is not None  # for type checker
        self.assertIn("def render_p2", out)

    def test_returns_inline_python_without_fence(self):
        text = (
            "from __future__ import annotations\n\n"
            "def render_p2(doc, page):\n    pass\n"
        )
        out = cg.extract_python_block(text)
        self.assertIsNotNone(out)
        assert out is not None  # for type checker
        self.assertIn("def render_p2", out)


if __name__ == "__main__":
    unittest.main()

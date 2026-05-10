"""Hypothesis-generator unit tests (issue #29 T05).

Mocks the multi-LLM subprocess fan-out using ``runner_overrides`` so the
test does not depend on PATH availability of claude/codex/gemini. Three
canned LLM responses exercise:

  - Fenced JSON wrapped in a markdown code block (claude-style).
  - Plain JSON array (codex-style).
  - Slug-overlap dedup (gemini reuses one of claude's slugs).

Asserts the merged manifest validates against the schema, raw outputs
land in _llm-raw/, sources reflect attribution, wildcard is preserved.
Then a second test confirms that <2 successful LLMs exits 2.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

import experiment_hypothesis_gen as hg  # noqa: E402


def _fake_proc(stdout: str) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr="", returncode=0)


CLAUDE_RESPONSE = """Here are my hypotheses for the falzflyer P2 panel.

```json
[
  {
    "slug": "cut-to-three-with-body",
    "name": "Cut to three items, add one-sentence body",
    "axis_commitments": ["density", "hierarchy"],
    "rationale": "Drop from five peer slogans to three, give each item a body sentence.",
    "expected_outcome": "Higher transport, possibly lower appeal.",
    "wildcard": false
  },
  {
    "slug": "vollkorn-italic-emphasis",
    "name": "Vollkorn Italic for emphasized line",
    "axis_commitments": ["typography", "hierarchy"],
    "rationale": "Use Vollkorn italic for the cornerstone slogan.",
    "expected_outcome": "Editorial register.",
    "wildcard": false
  },
  {
    "slug": "asymmetric-not-centered",
    "name": "Asymmetric balance with rules",
    "axis_commitments": ["asymmetry", "whitespace-strategy"],
    "rationale": "Replace centered list with left-aligned items.",
    "expected_outcome": "Higher appeal for design-literate.",
    "wildcard": false
  },
  {
    "slug": "voice-personal-i",
    "name": "Personal voice — first person",
    "axis_commitments": ["voice-formality"],
    "rationale": "Convert bullet slogans to first-person commitments.",
    "expected_outcome": "Higher transport from concrete commitments.",
    "wildcard": false
  },
  {
    "slug": "handwritten-margin",
    "name": "Handwritten margin notes",
    "axis_commitments": ["wildcard"],
    "rationale": "Wild-card. Handwritten margin annotations from the candidate.",
    "expected_outcome": "Will polarise.",
    "wildcard": true
  }
]
```
"""

CODEX_RESPONSE = """[
  {
    "slug": "privilege-one-yellow-accent",
    "name": "Privilege one item via Hellgrün to Gelb swap",
    "axis_commitments": ["accent-strategy", "hierarchy"],
    "rationale": "Single most-important item gets a Gelb backing.",
    "expected_outcome": "Higher transport for the highlighted item.",
    "wildcard": false
  },
  {
    "slug": "full-bleed-photo-collage",
    "name": "Replace text panel with photo collage",
    "axis_commitments": ["photographic-vs-typographic", "density"],
    "rationale": "Swap schlagworte for a 2x2 photo collage with one-word captions.",
    "expected_outcome": "Higher emotional appeal.",
    "wildcard": false
  },
  {
    "slug": "numbered-priority-list",
    "name": "Numbered 1..5 priority list with rules between",
    "axis_commitments": ["hierarchy", "density"],
    "rationale": "Number each slogan and add thin Dunkelgrün rules.",
    "expected_outcome": "Higher transport.",
    "wildcard": false
  },
  {
    "slug": "typographic-poster",
    "name": "Typographic poster — one giant statement",
    "axis_commitments": ["typography", "density"],
    "rationale": "Replace the list with one giant Vollkorn Black statement.",
    "expected_outcome": "Polarising.",
    "wildcard": false
  },
  {
    "slug": "whitespace-three-line-poem",
    "name": "Three short lines with massive whitespace",
    "axis_commitments": ["whitespace-strategy", "density"],
    "rationale": "Reduce content to three short lines, force slow read.",
    "expected_outcome": "Strong appeal.",
    "wildcard": false
  }
]
"""

# Gemini reuses claude's `vollkorn-italic-emphasis` slug to exercise dedup.
GEMINI_RESPONSE = """{"hypotheses": [
  {
    "slug": "vollkorn-italic-emphasis",
    "name": "Italic emphasis with Vollkorn",
    "axis_commitments": ["typography"],
    "rationale": "Use Vollkorn italic for emphasis.",
    "expected_outcome": "Adds editorial feel.",
    "wildcard": false
  },
  {
    "slug": "diagonal-fold-bleed",
    "name": "Diagonal photo bleed across the panel",
    "axis_commitments": ["asymmetry", "photographic-vs-typographic"],
    "rationale": "Run a portrait diagonally across the panel.",
    "expected_outcome": "Polarising.",
    "wildcard": false
  }
]}
"""


class HypothesisGenTest(unittest.TestCase):

    def setUp(self):
        # Redirect ROOT so the generator writes into a tempdir, not the
        # real repo. The module-level constant is recomputed on import,
        # so we patch via attribute.
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_root = Path(self.tmp.name)
        self.exp_dir = self.tmp_root / "experiments" / "test-exp"
        self._orig_root = hg.ROOT
        # ROOT is used to compute exp_dir and SCHEMA_PATH; only exp_dir
        # path needs redirection. We monkey-patch ROOT so writes go to
        # the tempdir, but keep SCHEMA_PATH pointed at the real schema
        # so validation runs against the canonical contract.
        hg.ROOT = self.tmp_root
        # Copy schema into the temp tree so validator finds it via the
        # patched ROOT — easier than rewriting two constants.
        schema_dst = self.tmp_root / "experiments" / "_schema"
        schema_dst.mkdir(parents=True, exist_ok=True)
        (schema_dst / "manifest.schema.yaml").write_bytes(
            (self._orig_root / "experiments" / "_schema" / "manifest.schema.yaml").read_bytes()
        )
        hg.SCHEMA_PATH = schema_dst / "manifest.schema.yaml"
        # Use the real prompt template (T06 makes it non-empty); for
        # this test we only need it to render without error.
        prompt = self.tmp_root / "prompt.md"
        prompt.write_text(
            "Subject: {subject}\n\nWeak area:\n\n{weak_area_quote}\n",
            encoding="utf-8",
        )
        self.prompt_path = prompt

    def tearDown(self):
        hg.ROOT = self._orig_root
        hg.SCHEMA_PATH = self._orig_root / "experiments" / "_schema" / "manifest.schema.yaml"
        self.tmp.cleanup()

    def _make_overrides(self, claude=True, codex=True, gemini=True):
        overrides = {}
        if claude:
            overrides["claude"] = lambda prompt: _fake_proc(CLAUDE_RESPONSE)
        if codex:
            overrides["codex"] = lambda prompt: _fake_proc(CODEX_RESPONSE)
        if gemini:
            overrides["gemini"] = lambda prompt: _fake_proc(GEMINI_RESPONSE)
        return overrides

    def test_three_llm_run_writes_valid_manifest(self):
        rc = hg.run_generation(
            exp_id="test-exp",
            subject="falzflyer-p2-mein-plan",
            prompt_path=self.prompt_path,
            requested_llms=["claude", "codex", "gemini"],
            no_gemini=False,
            n_target=12,
            runner_overrides=self._make_overrides(),
        )
        self.assertEqual(rc, 0, "expected exit 0 on happy path")

        manifest_yml = self.exp_dir / "manifest.yml"
        manifest_json = self.exp_dir / "manifest.json"
        self.assertTrue(manifest_yml.exists(), "manifest.yml not written")
        self.assertTrue(manifest_json.exists(), "manifest.json not written")

        import yaml
        manifest = yaml.safe_load(manifest_yml.read_text(encoding="utf-8"))

        # Hypothesis count: 5 from claude + 5 from codex + 2 from gemini,
        # minus 1 duplicate (vollkorn-italic-emphasis) = 11 merged.
        self.assertGreaterEqual(len(manifest["hypotheses"]), 10,
                                f"expected >= 10 hypotheses, got {len(manifest['hypotheses'])}")
        slugs = [h["slug"] for h in manifest["hypotheses"]]
        self.assertEqual(len(slugs), len(set(slugs)),
                         f"slug collision after merge: {slugs}")

        # At least one wildcard.
        self.assertTrue(any(h["wildcard"] for h in manifest["hypotheses"]))

        # Two contributing LLMs minimum (we expect three).
        self.assertGreaterEqual(len(manifest["contributing_llms"]), 2)

        # Dedup attribution: vollkorn-italic-emphasis must list both
        # claude and gemini in sources.
        vollkorn = [h for h in manifest["hypotheses"]
                    if h["slug"] == "vollkorn-italic-emphasis"]
        self.assertEqual(len(vollkorn), 1)
        self.assertIn("claude", vollkorn[0]["sources"])
        self.assertIn("gemini", vollkorn[0]["sources"])

        # Raw outputs preserved.
        raw_dir = self.exp_dir / "_llm-raw"
        self.assertTrue(raw_dir.exists())
        raws = list(raw_dir.iterdir())
        self.assertEqual(len(raws), 3,
                         f"expected 3 raw stdouts, got {len(raws)}")

    def test_single_llm_exits_2(self):
        # Only claude succeeds; codex throws, gemini throws.
        def boom(prompt):
            raise RuntimeError("simulated subprocess failure")
        overrides = {
            "claude": lambda prompt: _fake_proc(CLAUDE_RESPONSE),
            "codex": boom,
            "gemini": boom,
        }
        rc = hg.run_generation(
            exp_id="test-exp",
            subject="falzflyer-p2-mein-plan",
            prompt_path=self.prompt_path,
            requested_llms=["claude", "codex", "gemini"],
            no_gemini=False,
            n_target=12,
            runner_overrides=overrides,
        )
        self.assertEqual(rc, 2,
                         "expected exit 2 when fewer than 2 LLMs respond")

    def test_unparseable_response_is_audited_but_not_counted(self):
        # claude returns nonsense; codex + gemini parse fine, but the
        # merged pool only has 6 unique hypotheses + 1 synthetic wildcard
        # = 7 — below the schema's minItems 10. We expect exit 3
        # (schema validation failure), a draft manifest written, and
        # raw output preserved for ALL three LLMs (including claude's
        # unparseable response, for audit).
        overrides = {
            "claude": lambda prompt: _fake_proc("I refuse, no JSON for you."),
            "codex": lambda prompt: _fake_proc(CODEX_RESPONSE),
            "gemini": lambda prompt: _fake_proc(GEMINI_RESPONSE),
        }
        rc = hg.run_generation(
            exp_id="test-exp",
            subject="falzflyer-p2-mein-plan",
            prompt_path=self.prompt_path,
            requested_llms=["claude", "codex", "gemini"],
            no_gemini=False,
            n_target=12,
            runner_overrides=overrides,
        )
        self.assertEqual(rc, 3, "expected schema-fail exit when pool too small")
        self.assertTrue(
            (self.exp_dir / "manifest.draft.yml").exists(),
            "manifest.draft.yml must be written on schema failure",
        )
        # Raw output for claude was still saved (audit) even though
        # parse failed.
        raw_files = list((self.exp_dir / "_llm-raw").iterdir())
        names = sorted(p.name.split("-", 1)[0] for p in raw_files)
        self.assertEqual(names, ["claude", "codex", "gemini"])

    def test_wildcard_synthesised_when_missing(self):
        # Strip wildcard flag from claude's response; codex has none either.
        no_wildcard = CLAUDE_RESPONSE.replace('"wildcard": true', '"wildcard": false')
        overrides = {
            "claude": lambda prompt: _fake_proc(no_wildcard),
            "codex": lambda prompt: _fake_proc(CODEX_RESPONSE),
        }
        rc = hg.run_generation(
            exp_id="test-exp",
            subject="falzflyer-p2-mein-plan",
            prompt_path=self.prompt_path,
            requested_llms=["claude", "codex"],
            no_gemini=True,
            n_target=12,
            runner_overrides=overrides,
        )
        self.assertEqual(rc, 0)
        import yaml
        manifest = yaml.safe_load((self.exp_dir / "manifest.yml").read_text(encoding="utf-8"))
        wildcards = [h for h in manifest["hypotheses"] if h["wildcard"]]
        self.assertEqual(len(wildcards), 1)
        self.assertEqual(wildcards[0]["slug"], "wildcard-placeholder")


class JSONExtractorTest(unittest.TestCase):
    def test_strips_fence(self):
        text = '```json\n[{"slug": "x"}]\n```\n'
        self.assertEqual(hg.extract_json_block(text), '[{"slug": "x"}]')

    def test_first_to_last(self):
        text = 'Here you go: [{"slug": "x"}, {"slug": "y"}] hope that helps.'
        self.assertEqual(
            hg.extract_json_block(text),
            '[{"slug": "x"}, {"slug": "y"}]',
        )

    def test_handles_nested_braces_in_strings(self):
        text = 'Reply: [{"name": "x [inner] y"}]'
        self.assertEqual(
            hg.extract_json_block(text),
            '[{"name": "x [inner] y"}]',
        )

    def test_returns_none_when_no_block(self):
        self.assertIsNone(hg.extract_json_block("just words, no JSON here"))

    def test_unwraps_claude_print_json_wrapper(self):
        # claude --print --output-format json wraps replies in {"result": "...", ...}
        wrapper = json.dumps({
            "result": "Here you go:\n```json\n[{\"slug\": \"x\"}]\n```\n",
            "type": "result",
        })
        self.assertEqual(hg.extract_json_block(wrapper), '[{"slug": "x"}]')


if __name__ == "__main__":
    unittest.main()

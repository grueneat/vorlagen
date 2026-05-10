"""Prompt-template structural tests (issue #29 T06).

Verifies the prompt at ``tools/experiment_generate/prompt_template.md``
contains every element required by RESEARCH.md "Hypothesis generation
prompt" and pitfalls research §1:
  - >= 4 lines starting with 'GOOD:' and >= 4 starting with 'BAD:'
  - Substitution tokens {subject} and {weak_area_quote}
  - All 9 axis_commitments enum values literally present
  - Mandatory wildcard clause
  - Strict JSON output schema with at least one example
  - Rendered length 6000-30000 chars (matches "1500-5000 tokens" target)
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROMPT_PATH = ROOT / "tools" / "experiment_generate" / "prompt_template.md"
sys.path.insert(0, str(ROOT / "tools"))

import experiment_hypothesis_gen as hg  # noqa: E402


AXES_VOCAB = [
    "density", "hierarchy", "typography", "asymmetry",
    "photographic-vs-typographic", "accent-strategy",
    "whitespace-strategy", "voice-formality", "wildcard",
]


class PromptTemplateTest(unittest.TestCase):

    def setUp(self):
        self.text = PROMPT_PATH.read_text(encoding="utf-8")

    def test_file_non_trivially_long(self):
        self.assertGreater(len(self.text), 3000,
                           "prompt template suspiciously short")

    def test_at_least_four_good_examples(self):
        good_lines = [
            ln for ln in self.text.splitlines()
            if re.match(r"^\s*[-*]?\s*GOOD\s*:", ln)
        ]
        self.assertGreaterEqual(
            len(good_lines), 4,
            f"need >=4 GOOD: examples; got {len(good_lines)}",
        )

    def test_at_least_four_bad_examples(self):
        bad_lines = [
            ln for ln in self.text.splitlines()
            if re.match(r"^\s*[-*]?\s*BAD\s*:", ln)
        ]
        self.assertGreaterEqual(
            len(bad_lines), 4,
            f"need >=4 BAD: examples; got {len(bad_lines)}",
        )

    def test_substitution_tokens_present(self):
        self.assertIn("{subject}", self.text)
        self.assertIn("{weak_area_quote}", self.text)

    def test_all_axis_vocab_terms_present(self):
        missing = [a for a in AXES_VOCAB if a not in self.text]
        self.assertEqual(
            missing, [],
            f"prompt is missing axis vocab terms: {missing}",
        )

    def test_mandatory_wildcard_clause(self):
        self.assertRegex(
            self.text,
            r"\bwildcard\b",
            "prompt must mention wildcard explicitly",
        )
        self.assertIn(
            '"wildcard": true', self.text,
            "prompt must show literal '\"wildcard\": true' as the schema example",
        )

    def test_strict_json_schema_example_present(self):
        self.assertIn("```json", self.text)
        self.assertIn("slug", self.text)
        self.assertIn("axis_commitments", self.text)
        self.assertIn("rationale", self.text)
        self.assertIn("expected_outcome", self.text)

    def test_rendered_prompt_length_in_target_band(self):
        rendered = hg.render_prompt(
            self.text,
            subject="falzflyer-p2-mein-plan",
            weak_area_quote=(
                "P2 currently presents five short slogans as an even-spaced peer "
                "list — five items that read as roughly equal weight, no "
                "hierarchy, no argument, no entry point."
            ),
            constraint_envelope="### Brand rules\n- inside_page\n",
            v1_anti_examples="### v1-test\n- broken\n",
        )
        n = len(rendered)
        self.assertGreaterEqual(
            n, 6000,
            f"rendered prompt only {n} chars; expected >= 6000 (~1500 tokens)",
        )
        self.assertLessEqual(
            n, 30000,
            f"rendered prompt {n} chars; expected <= 30000 (~7500 tokens)",
        )

    def test_render_substitutes_tokens(self):
        rendered = hg.render_prompt(
            self.text,
            subject="my-subject",
            weak_area_quote="Quoted weak area.",
            constraint_envelope="ENV-MD",
            v1_anti_examples="ANTI-MD",
        )
        self.assertIn("my-subject", rendered)
        self.assertIn("Quoted weak area.", rendered)
        self.assertIn("ENV-MD", rendered)
        self.assertIn("ANTI-MD", rendered)
        self.assertNotIn("{subject}", rendered)
        self.assertNotIn("{weak_area_quote}", rendered)
        self.assertNotIn("{constraint_envelope}", rendered)
        self.assertNotIn("{v1_anti_examples}", rendered)


if __name__ == "__main__":
    unittest.main()

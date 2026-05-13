"""Synthetic-fixture mutation tests for the comparator.

These tests do NOT require the anchor leporello template (which is sparse
in the worktree). They build inventory snapshots in-memory and feed them
directly to ``tools.inventory_compare.compare``. The goal (review fix L4):
ensure at least one mutation path runs in every CI environment, no matter
how sparse the checkout.

The anchor-bound tests in ``test_inventory_gate_mutations.py`` remain the
full-fidelity gate verification; this file complements them for envs
where ``/workspace/originals`` or the materialised anchor template are
absent.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
WORKTREE = HERE.parents[2]
if str(WORKTREE) not in sys.path:
    sys.path.insert(0, str(WORKTREE))

from tools.inventory_compare import compare  # noqa: E402


def _minimal_snapshot() -> dict:
    """Return a minimal but schema-shaped inventory snapshot.

    Mirrors the YAML shape ``tools/walkers/schema.py`` emits, with one row
    per top-level collection so the comparator has something to walk.
    """
    return {
        "schema_version": 1,
        "template": "synthetic",
        "text_runs": {
            "total_idml": 1,
            "by_paragraph_style": [
                {
                    "style": "ParagraphStyle/Body",
                    "idml_count": 1,
                    "build_py_count": 1,
                    "sla_itext_count": 1,
                    "pdf_word_count": 0,
                },
            ],
            "every_idml_run_present_in_build_py": True,
            "build_py_runs": [
                {"text": "hello", "font": "Helv", "fontsize": 10.0,
                 "fcolor": "Black", "paragraph_style": "idml/body",
                 "text_source": "build_py"},
            ],
            "idml_runs": [
                {"text": "hello", "font": "Helv", "fontsize": 10.0,
                 "fcolor": "Black", "paragraph_style": "ParagraphStyle/Body",
                 "text_source": "build_py"},
            ],
        },
        "frames": {
            "text_frames": [
                {"anname": "uA", "idml_self": "uA",
                 "idml_position_mm": [0, 0, 100, 100],
                 "build_py_position_mm": [0, 0, 100, 100],
                 "sla_pageobject_present": True,
                 "sla_storytext_runs": 1, "source": "idml"},
            ],
            "image_frames": [
                {"anname": "uB", "idml_self": "uB", "idml_link": "x.jpg",
                 "idml_position_mm": [0, 0, 50, 50],
                 "build_py_position_mm": [0, 0, 50, 50],
                 "build_py_image_ref": "x.jpg",
                 "sla_pageobject_present": True, "sla_pfile_present": True,
                 "pdf_image_present": True, "source": "idml"},
            ],
            "polygon_frames": [],
            "group_frames": [],
        },
        "paragraph_styles": [
            {"idml": "ParagraphStyle/Body", "build_py": "idml/body",
             "build_py_extra_pstyle": True, "sla_pstyle_present": True},
        ],
        "colors": [
            {"idml": "Color/Brand", "cmyk": [0, 100, 0, 0],
             "build_py_extra_color": True, "sla_color_present": True},
        ],
        "assets": [
            {"basename": "x.jpg", "on_disk": True, "classified": "external",
             "referenced_from_frames": ["uB"], "parent_composite": None,
             "sha256": "deadbeef", "byte_length": 1024},
        ],
        "words": {
            "baseline_pdf_count": 1, "preview_pdf_count": 1,
            "missing_from_preview": [], "extra_in_preview": [],
        },
        "parse_warnings": [],
    }


class SyntheticGateRegressionTest(unittest.TestCase):
    """Each test mutates a copy of the minimal snapshot and checks rc + diff."""

    def setUp(self) -> None:
        self.base = _minimal_snapshot()

    def test_self_compare_exits_0(self) -> None:
        result = compare(self.base, self.base)
        self.assertEqual(result["summary"]["exit_code"], 0)
        self.assertEqual(result["missing"], {})
        self.assertEqual(result["extra"], {})

    def test_dropped_anname_is_missing(self) -> None:
        # Remove the image frame's anname → comparator should report a
        # missing frame and exit 2.
        actual = _minimal_snapshot()
        actual["frames"]["image_frames"] = []
        result = compare(self.base, actual)
        self.assertEqual(result["summary"]["exit_code"], 2)
        self.assertIn("uB", result["missing"].get("frames.image_frames", []))

    def test_pfile_flipped_to_false_is_missing(self) -> None:
        # Flip sla_pfile_present from True → False on the existing image
        # frame. The F7 expansion should report the anname under
        # frames.image_frames.sla_pfile and exit 2.
        actual = _minimal_snapshot()
        actual["frames"]["image_frames"][0]["sla_pfile_present"] = False
        result = compare(self.base, actual)
        self.assertEqual(result["summary"]["exit_code"], 2)
        self.assertIn(
            "uB", result["missing"].get("frames.image_frames.sla_pfile", []),
        )

    def test_pstyle_build_py_dropped_is_missing(self) -> None:
        # Set both build_py and build_py_extra_pstyle to falsy. Comparator
        # should report the IDML key under paragraph_styles.build_py.
        actual = _minimal_snapshot()
        actual["paragraph_styles"][0]["build_py"] = None
        actual["paragraph_styles"][0]["build_py_extra_pstyle"] = False
        result = compare(self.base, actual)
        self.assertEqual(result["summary"]["exit_code"], 2)
        self.assertIn(
            "ParagraphStyle/Body",
            result["missing"].get("paragraph_styles.build_py", []),
        )

    def test_color_build_py_dropped_is_missing(self) -> None:
        # Flip build_py_extra_color False → comparator reports the IDML
        # color key under colors.build_py.
        actual = _minimal_snapshot()
        actual["colors"][0]["build_py_extra_color"] = False
        result = compare(self.base, actual)
        self.assertEqual(result["summary"]["exit_code"], 2)
        self.assertIn(
            "Color/Brand",
            result["missing"].get("colors.build_py", []),
        )

    def test_on_disk_flipped_to_false_is_missing(self) -> None:
        # An asset that used to be on disk is no longer; the gate should
        # report it under assets.on_disk and exit 2 (F7).
        actual = _minimal_snapshot()
        actual["assets"][0]["on_disk"] = False
        result = compare(self.base, actual)
        self.assertEqual(result["summary"]["exit_code"], 2)
        self.assertIn(
            "x.jpg", result["missing"].get("assets.on_disk", []),
        )

    def test_set_equality_flag_false_is_missing(self) -> None:
        # When every_idml_run_present_in_build_py flips to False, the gate
        # surfaces it as a missing section.
        actual = _minimal_snapshot()
        actual["text_runs"]["every_idml_run_present_in_build_py"] = False
        result = compare(self.base, actual)
        self.assertEqual(result["summary"]["exit_code"], 2)
        self.assertIn(
            "text_runs.every_idml_run_present_in_build_py",
            result["missing"],
        )

    def test_delta_summary_split(self) -> None:
        # Add a positive-delta count change (idml_count goes up by 1) and a
        # negative-delta (build_py_count goes down by 1) — delta_summary
        # should split them so a CI consumer can distinguish.
        actual = _minimal_snapshot()
        actual["text_runs"]["by_paragraph_style"][0]["idml_count"] = 2
        actual["text_runs"]["by_paragraph_style"][0]["build_py_count"] = 0
        result = compare(self.base, actual)
        summary = result["summary"]
        self.assertEqual(summary["exit_code"], 2)  # negative delta → rc=2
        ds = summary.get("delta_summary", {})
        self.assertGreater(ds.get("positive", 0), 0)
        self.assertGreater(ds.get("negative", 0), 0)


if __name__ == "__main__":
    unittest.main()

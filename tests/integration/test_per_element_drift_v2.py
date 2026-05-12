"""Integration tests for per_element_drift against the real v2 falzflyer data."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from per_element_drift import aggregate_per_element  # noqa: E402

SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
VALIDATION_DIR = ROOT / "build" / "validation" / SLUG
DIFF_BBOXES = VALIDATION_DIR / "diff_bboxes.json"
VISUAL_DIFF = VALIDATION_DIR / "visual_diff.json"

# Known hotspot slots on page 1 (0-indexed) from diff_bbox data exploration.
KNOWN_PAGE1_HOTSPOTS = {"u2cd", "u295", "u265", "u3a2"}


def _skip_if_missing():
    for p in (DIFF_BBOXES, VISUAL_DIFF):
        if not p.exists():
            pytest.skip(f"Required fixture not found: {p}")


def test_produces_sensible_top5():
    """Top 5 contributors per page all have positive mismatch pixels."""
    _skip_if_missing()
    diff_bboxes = json.loads(DIFF_BBOXES.read_text(encoding="utf-8"))
    visual_diff = json.loads(VISUAL_DIFF.read_text(encoding="utf-8"))
    result = aggregate_per_element(diff_bboxes, visual_diff)
    assert len(result["pages"]) == 2
    for page in result["pages"]:
        top5 = page["top_contributors"][:5]
        assert len(top5) >= 1, f"page {page['page']} has no contributors"
        for c in top5:
            assert c["mismatch_px_summed"] > 0
            assert c["pct_of_page_mismatch"] > 0.0
            assert c["slot"]


def test_known_hotspot_in_top3_page1():
    """At least one known hotspot slot appears in top-3 on page 1."""
    _skip_if_missing()
    diff_bboxes = json.loads(DIFF_BBOXES.read_text(encoding="utf-8"))
    visual_diff = json.loads(VISUAL_DIFF.read_text(encoding="utf-8"))
    result = aggregate_per_element(diff_bboxes, visual_diff)
    page1 = result["pages"][1]
    top3_slots = {c["slot"] for c in page1["top_contributors"][:3]}
    assert top3_slots & KNOWN_PAGE1_HOTSPOTS, (
        f"Expected at least one of {KNOWN_PAGE1_HOTSPOTS} in top-3 of page 1; "
        f"got {top3_slots}"
    )


def test_pct_of_page_mismatch_sums_lte_100():
    """Sum of pct_of_page_mismatch across all contributors cannot exceed 100%
    (bboxes may not cover all mismatch pixels, so sum can be less than 100)."""
    _skip_if_missing()
    diff_bboxes = json.loads(DIFF_BBOXES.read_text(encoding="utf-8"))
    visual_diff = json.loads(VISUAL_DIFF.read_text(encoding="utf-8"))
    result = aggregate_per_element(diff_bboxes, visual_diff)
    for page in result["pages"]:
        total_pct = sum(c["pct_of_page_mismatch"] for c in page["top_contributors"])
        assert total_pct <= 100.01, (  # small rounding tolerance
            f"page {page['page']}: sum of pct_of_page_mismatch={total_pct:.2f} exceeds 100%"
        )


def test_runtime_under_2s():
    """Aggregation of real v2 falzflyer data completes in under 2 seconds."""
    _skip_if_missing()
    diff_bboxes = json.loads(DIFF_BBOXES.read_text(encoding="utf-8"))
    visual_diff = json.loads(VISUAL_DIFF.read_text(encoding="utf-8"))
    t0 = time.monotonic()
    aggregate_per_element(diff_bboxes, visual_diff)
    elapsed = time.monotonic() - t0
    assert elapsed < 2.0, f"aggregate_per_element took {elapsed:.2f}s (limit: 2s)"


def test_top3_no_over_attribution():
    """#37 P1 task 1 acceptance: top-3 contributors per page sum to ≤100 %
    (was 139 % before the HSL-halo normalisation fix)."""
    _skip_if_missing()
    diff_bboxes = json.loads(DIFF_BBOXES.read_text(encoding="utf-8"))
    visual_diff = json.loads(VISUAL_DIFF.read_text(encoding="utf-8"))
    result = aggregate_per_element(diff_bboxes, visual_diff)
    for page in result["pages"]:
        top3 = page["top_contributors"][:3]
        total = sum(c["pct_of_page_mismatch"] for c in top3)
        assert total <= 100.5, (
            f"page {page['page']}: top-3 sum {total:.2f}% (> 100.5% — HSL halo "
            "over-attribution regressed)"
        )


def test_normalisation_factor_field_present():
    """#37 P1 task 1: each page has a `normalisation_factor` field."""
    _skip_if_missing()
    diff_bboxes = json.loads(DIFF_BBOXES.read_text(encoding="utf-8"))
    visual_diff = json.loads(VISUAL_DIFF.read_text(encoding="utf-8"))
    result = aggregate_per_element(diff_bboxes, visual_diff)
    for page in result["pages"]:
        assert "normalisation_factor" in page
        assert isinstance(page["normalisation_factor"], float)
        # On v2 falzflyer, the bboxes over-cover the AE mismatch ~1.5-2× so
        # the factor sits between 0.3 and 1.5. (0 only when total_mismatch_px=0
        # which doesn't apply here.)
        assert 0.0 < page["normalisation_factor"] < 5.0

"""Unit tests for tools/per_element_drift.py."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from per_element_drift import UNATTRIBUTED_KEY, aggregate_per_element  # noqa: E402


def _make_vd(mismatch_pixels: int = 100_000, mismatch_pct: float = 7.65) -> dict:
    return {"pages": [{"mismatch_pixels": mismatch_pixels, "mismatch_pct": mismatch_pct}]}


def _make_db(bboxes: list[dict]) -> dict:
    return {"template_slug": "test", "pages": [{"page": 0, "bboxes": bboxes}]}


# ---------------------------------------------------------------------------
# 1. Multiple bboxes for same slot aggregate
# ---------------------------------------------------------------------------

def test_aggregates_multiple_bboxes_per_slot():
    db = _make_db([
        {"attributed_slot": "u3a2", "area_px": 10_000},
        {"attributed_slot": "u3a2", "area_px": 5_000},
        {"attributed_slot": "u3a2", "area_px": 3_000},
    ])
    result = aggregate_per_element(db, _make_vd())
    contribs = result["pages"][0]["top_contributors"]
    assert len(contribs) == 1
    assert contribs[0]["slot"] == "u3a2"
    assert contribs[0]["mismatch_px_summed"] == 18_000
    assert contribs[0]["bbox_count"] == 3


# ---------------------------------------------------------------------------
# 2. Null attributed_slot goes under sentinel
# ---------------------------------------------------------------------------

def test_unattributed_bboxes_collected_under_sentinel():
    db = _make_db([
        {"attributed_slot": None, "area_px": 5_000},
        {"attributed_slot": None, "area_px": 3_000},
        {"attributed_slot": "u3a2", "area_px": 1_000},
    ])
    result = aggregate_per_element(db, _make_vd())
    contribs = result["pages"][0]["top_contributors"]
    slots = {c["slot"] for c in contribs}
    assert UNATTRIBUTED_KEY in slots
    unattr = next(c for c in contribs if c["slot"] == UNATTRIBUTED_KEY)
    assert unattr["mismatch_px_summed"] == 8_000
    assert unattr["bbox_count"] == 2


# ---------------------------------------------------------------------------
# 3. top_contributors sorted descending by pixel count
# ---------------------------------------------------------------------------

def test_top_contributors_sorted_desc_by_pixel_count():
    db = _make_db([
        {"attributed_slot": "small", "area_px": 100},
        {"attributed_slot": "large", "area_px": 50_000},
        {"attributed_slot": "medium", "area_px": 20_000},
    ])
    result = aggregate_per_element(db, _make_vd())
    pxs = [c["mismatch_px_summed"] for c in result["pages"][0]["top_contributors"]]
    assert pxs == sorted(pxs, reverse=True)
    assert pxs[0] == 50_000


# ---------------------------------------------------------------------------
# 4. pct_of_page_total_drift computed correctly
# ---------------------------------------------------------------------------

def test_pct_of_total_drift_computed_correctly():
    # 100k total mismatch px, 7.65% mismatch_pct; slot with 30k px → 2.295pp
    vd = _make_vd(mismatch_pixels=100_000, mismatch_pct=7.65)
    db = _make_db([{"attributed_slot": "u3a2", "area_px": 30_000}])
    result = aggregate_per_element(db, vd)
    contrib = result["pages"][0]["top_contributors"][0]
    # 30000/100000 * 7.65 = 2.295
    assert abs(contrib["pct_of_page_total_drift"] - 2.295) < 0.001
    # pct_of_page_mismatch = 30.0
    assert abs(contrib["pct_of_page_mismatch"] - 30.0) < 0.01


# ---------------------------------------------------------------------------
# 5. Empty page bboxes produces empty contributions without crashing
# ---------------------------------------------------------------------------

def test_empty_page_bboxes_produces_empty_contributions():
    db = _make_db([])
    result = aggregate_per_element(db, _make_vd())
    page = result["pages"][0]
    assert page["top_contributors"] == []
    assert page["bbox_count"] == 0


# ---------------------------------------------------------------------------
# 6. Percentages use visual_diff's authoritative total (not summed bbox area)
# ---------------------------------------------------------------------------

def test_uses_visual_diff_authoritative_total():
    # visual_diff says 200k px mismatch; bboxes sum to only 50k
    # (they don't cover the full mismatch — overlap, AA noise, etc.)
    vd = _make_vd(mismatch_pixels=200_000, mismatch_pct=9.0)
    db = _make_db([
        {"attributed_slot": "u3a2", "area_px": 40_000},
        {"attributed_slot": "u52d", "area_px": 10_000},
    ])
    result = aggregate_per_element(db, vd)
    contribs = result["pages"][0]["top_contributors"]
    u3a2 = next(c for c in contribs if c["slot"] == "u3a2")
    # 40000 / 200000 * 100 = 20.0% of page mismatch
    assert abs(u3a2["pct_of_page_mismatch"] - 20.0) < 0.01
    # 40000 / 200000 * 9.0 = 1.8pp of page drift
    assert abs(u3a2["pct_of_page_total_drift"] - 1.8) < 0.001


# ---------------------------------------------------------------------------
# 7. Top 20 cap
# ---------------------------------------------------------------------------

def test_top_20_cap():
    bboxes = [{"attributed_slot": f"u{i:03d}", "area_px": i + 1} for i in range(30)]
    db = _make_db(bboxes)
    result = aggregate_per_element(db, _make_vd())
    assert len(result["pages"][0]["top_contributors"]) == 20


# ---------------------------------------------------------------------------
# 8. Multi-page: each page uses its own visual_diff denominator
# ---------------------------------------------------------------------------

def test_multi_page_uses_own_page_denominators():
    db = {
        "template_slug": "test-tpl",
        "pages": [
            {"page": 0, "bboxes": [{"attributed_slot": "u1", "area_px": 10_000}]},
            {"page": 1, "bboxes": [{"attributed_slot": "u2", "area_px": 5_000}]},
        ],
    }
    vd = {
        "pages": [
            {"mismatch_pixels": 100_000, "mismatch_pct": 7.0},
            {"mismatch_pixels": 50_000, "mismatch_pct": 5.0},
        ]
    }
    result = aggregate_per_element(db, vd)
    assert len(result["pages"]) == 2
    # page 0: 10000/100000 * 7.0 = 0.7pp
    assert abs(result["pages"][0]["top_contributors"][0]["pct_of_page_total_drift"] - 0.7) < 0.001
    # page 1: 5000/50000 * 5.0 = 0.5pp
    assert abs(result["pages"][1]["top_contributors"][0]["pct_of_page_total_drift"] - 0.5) < 0.001


# ---------------------------------------------------------------------------
# 9. Zero total_mismatch_px doesn't divide by zero
# ---------------------------------------------------------------------------

def test_zero_total_mismatch_no_crash():
    vd = _make_vd(mismatch_pixels=0, mismatch_pct=0.0)
    db = _make_db([{"attributed_slot": "u3a2", "area_px": 1000}])
    result = aggregate_per_element(db, vd)
    c = result["pages"][0]["top_contributors"][0]
    assert c["pct_of_page_mismatch"] == 0.0
    assert c["pct_of_page_total_drift"] == 0.0

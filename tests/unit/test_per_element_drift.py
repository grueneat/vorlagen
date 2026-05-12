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
# 4. pct_of_page_total_drift computed correctly (with HSL-halo normalisation)
# ---------------------------------------------------------------------------

def test_pct_of_total_drift_computed_correctly():
    # 100k total mismatch px, 7.65% mismatch_pct; single slot owns all 30k bbox px.
    # Under the post-#37 normalisation, the bbox sum (30k) rescales to the
    # authoritative mismatch (100k) so that single slot owns 100 % of the page.
    vd = _make_vd(mismatch_pixels=100_000, mismatch_pct=7.65)
    db = _make_db([{"attributed_slot": "u3a2", "area_px": 30_000}])
    result = aggregate_per_element(db, vd)
    contrib = result["pages"][0]["top_contributors"][0]
    # sole slot owns the whole page once HSL halo is normalised back to AE pixels
    assert abs(contrib["pct_of_page_mismatch"] - 100.0) < 0.01
    assert abs(contrib["pct_of_page_total_drift"] - 7.65) < 0.001


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
# 6. Percentages rescale via normalisation so per-slot pcts are additive
# ---------------------------------------------------------------------------

def test_pcts_normalise_to_authoritative_total():
    # visual_diff says 200k px mismatch; bboxes sum to only 50k (rare under-
    # attribution case — the dominant pattern in real data is over-attribution
    # because of HSL halo dilation). The normalisation factor still applies:
    # each slot's share of the bbox-sum is its share of the page mismatch.
    vd = _make_vd(mismatch_pixels=200_000, mismatch_pct=9.0)
    db = _make_db([
        {"attributed_slot": "u3a2", "area_px": 40_000},
        {"attributed_slot": "u52d", "area_px": 10_000},
    ])
    result = aggregate_per_element(db, vd)
    contribs = result["pages"][0]["top_contributors"]
    u3a2 = next(c for c in contribs if c["slot"] == "u3a2")
    # 40000 / 50000 (sum_bbox) = 80% of page mismatch
    assert abs(u3a2["pct_of_page_mismatch"] - 80.0) < 0.01
    # 80% of 9.0 = 7.2pp of page drift
    assert abs(u3a2["pct_of_page_total_drift"] - 7.2) < 0.001
    # additivity: top contributors plus unattributed sum to ≤ 100 %
    total_pct = sum(c["pct_of_page_mismatch"] for c in contribs)
    assert total_pct <= 100.5


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
    # page 0: sole slot, normalised to 100 % → 7.0pp
    assert abs(result["pages"][0]["top_contributors"][0]["pct_of_page_total_drift"] - 7.0) < 0.001
    # page 1: sole slot, normalised to 100 % → 5.0pp
    assert abs(result["pages"][1]["top_contributors"][0]["pct_of_page_total_drift"] - 5.0) < 0.001
    # normalisation_factor surfaced per page
    assert result["pages"][0]["normalisation_factor"] == 10.0  # 100k / 10k
    assert result["pages"][1]["normalisation_factor"] == 10.0  # 50k / 5k


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
    # normalisation_factor is 0 when no authoritative mismatch — no divide-by-zero
    assert result["pages"][0]["normalisation_factor"] == 0.0


# ---------------------------------------------------------------------------
# 10. HSL-halo normalisation: three slots sized 200/150/100 → additive 100 %
# ---------------------------------------------------------------------------

def test_hsl_halo_normalisation_three_slots_sum_to_100():
    # Plan task 1: bbox sums of 200+150+100 = 450 against 300 authoritative px.
    # After normalisation, pct_of_page_mismatch matches area_px/sum_bbox * 100.
    vd = _make_vd(mismatch_pixels=300, mismatch_pct=5.0)
    db = _make_db([
        {"attributed_slot": "u1", "area_px": 200},
        {"attributed_slot": "u2", "area_px": 150},
        {"attributed_slot": "u3", "area_px": 100},
    ])
    result = aggregate_per_element(db, vd)
    contribs = result["pages"][0]["top_contributors"]
    expected = {"u1": 44.44, "u2": 33.33, "u3": 22.22}
    for c in contribs:
        assert abs(c["pct_of_page_mismatch"] - expected[c["slot"]]) < 0.05, c
    total = sum(c["pct_of_page_mismatch"] for c in contribs)
    assert 99.5 <= total <= 100.5
    # normalisation_factor surfaced
    assert abs(result["pages"][0]["normalisation_factor"] - (300 / 450)) < 1e-4


# ---------------------------------------------------------------------------
# 11. normalisation_factor field is always present per page
# ---------------------------------------------------------------------------

def test_normalisation_factor_field_present():
    vd = _make_vd(mismatch_pixels=100_000, mismatch_pct=7.0)
    db = _make_db([{"attributed_slot": "u1", "area_px": 50_000}])
    result = aggregate_per_element(db, vd)
    page = result["pages"][0]
    assert "normalisation_factor" in page
    # 100k / 50k = 2.0
    assert abs(page["normalisation_factor"] - 2.0) < 1e-4

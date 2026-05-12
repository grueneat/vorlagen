"""Unit tests for tools/diff_bbox_extract.py drift_type classifier
(Issue #37 P3 task 15)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from diff_bbox_extract import _classify_drift_type  # noqa: E402


def _bbox_at(x=0, y=0, w=30, h=30) -> dict:
    return {"bbox_px": {"x": x, "y": y, "w": w, "h": h}}


def _draw_square(img: Image.Image, x: int, y: int, w: int, h: int) -> None:
    d = ImageDraw.Draw(img)
    d.rectangle([x, y, x + w - 1, y + h - 1], fill="black")


def test_classify_missing(tmp_path):
    """Baseline has a black square, preview is empty → 'missing'."""
    base = Image.new("L", (60, 60), 255)
    _draw_square(base, 5, 5, 25, 25)  # baseline has ink in bbox area
    prev = Image.new("L", (60, 60), 255)  # preview is blank
    base_p = tmp_path / "base.png"
    prev_p = tmp_path / "prev.png"
    base.save(base_p)
    prev.save(prev_p)
    assert _classify_drift_type(_bbox_at(0, 0, 30, 30), base_p, prev_p) == "missing"


def test_classify_extra(tmp_path):
    """Baseline blank, preview has a black square → 'extra'."""
    base = Image.new("L", (60, 60), 255)
    prev = Image.new("L", (60, 60), 255)
    _draw_square(prev, 5, 5, 25, 25)
    base_p = tmp_path / "base.png"
    prev_p = tmp_path / "prev.png"
    base.save(base_p)
    prev.save(prev_p)
    assert _classify_drift_type(_bbox_at(0, 0, 30, 30), base_p, prev_p) == "extra"


def test_classify_position_similar_density(tmp_path):
    """Both crops have similar ink density (text shifted but same length) → 'position'."""
    base = Image.new("L", (60, 60), 255)
    _draw_square(base, 5, 5, 15, 15)  # ~ 225 dark pixels in 30×30 bbox
    prev = Image.new("L", (60, 60), 255)
    _draw_square(prev, 15, 5, 15, 15)  # similar density, shifted right
    base_p = tmp_path / "base.png"
    prev_p = tmp_path / "prev.png"
    base.save(base_p)
    prev.save(prev_p)
    assert _classify_drift_type(_bbox_at(0, 0, 30, 30), base_p, prev_p) == "position"


def test_classify_text_large_density_delta(tmp_path):
    """Baseline 50% ink density, preview 10% → 'text' (large content delta)."""
    base = Image.new("L", (60, 60), 255)
    _draw_square(base, 0, 0, 30, 15)  # half the bbox is filled
    prev = Image.new("L", (60, 60), 255)
    _draw_square(prev, 0, 0, 30, 3)   # only 10% of the bbox
    base_p = tmp_path / "base.png"
    prev_p = tmp_path / "prev.png"
    base.save(base_p)
    prev.save(prev_p)
    assert _classify_drift_type(_bbox_at(0, 0, 30, 30), base_p, prev_p) == "text"


def test_classify_unknown_both_blank(tmp_path):
    """Both crops blank → 'unknown'."""
    base = Image.new("L", (60, 60), 255)
    prev = Image.new("L", (60, 60), 255)
    base_p = tmp_path / "base.png"
    prev_p = tmp_path / "prev.png"
    base.save(base_p)
    prev.save(prev_p)
    assert _classify_drift_type(_bbox_at(0, 0, 30, 30), base_p, prev_p) == "unknown"


def test_classify_missing_png_returns_unknown(tmp_path):
    """Nonexistent file path → 'unknown' (no crash)."""
    out = _classify_drift_type(
        _bbox_at(0, 0, 30, 30),
        tmp_path / "nope.png",
        tmp_path / "also-nope.png",
    )
    assert out == "unknown"


def test_classify_none_paths_returns_unknown():
    """None paths → 'unknown'."""
    assert _classify_drift_type(_bbox_at(0, 0, 30, 30), None, None) == "unknown"


def test_drift_type_field_present_in_extract_all(tmp_path, monkeypatch):
    """End-to-end: extract_all attaches `drift_type` to each bbox record."""
    import diff_bbox_extract as dbe

    # Fake out the heavy bits — extract_bboxes_px returns a single bbox per page.
    monkeypatch.setattr(
        dbe, "extract_bboxes_px",
        lambda *a, **k: [
            {"x_px": 0, "y_px": 0, "w_px": 30, "h_px": 30, "area_px": 900,
             "mean_color": "#ff0000"},
        ],
    )
    monkeypatch.setattr(dbe, "load_dpi", lambda *a, **k: 150)
    monkeypatch.setattr(dbe, "load_template_slots", lambda slug: {})

    # Fake visual_diff.json with one page.
    vd_payload = {
        "pages": [{"page": 0, "delta_png": "diff-page-01.png"}],
    }
    import json
    out_dir = tmp_path
    (out_dir / "visual_diff.json").write_text(
        json.dumps(vd_payload), encoding="utf-8",
    )
    # Provide baseline + dsl PNGs so the classifier samples real images.
    base = Image.new("L", (60, 60), 255)
    _draw_square(base, 5, 5, 25, 25)
    prev = Image.new("L", (60, 60), 255)
    base.save(out_dir / "baseline-page-1.png")
    prev.save(out_dir / "dsl-page-1.png")
    # Stub the delta PNG too (extract_bboxes_px is mocked but extract_all
    # passes the path through; it just needs to exist).
    Image.new("RGB", (60, 60), "black").save(out_dir / "diff-page-01.png")

    payload = dbe.extract_all(out_dir, template_slug=None)
    bbox = payload["pages"][0]["bboxes"][0]
    assert "drift_type" in bbox
    # Baseline has ink, preview empty → missing
    assert bbox["drift_type"] == "missing"


def test_no_drift_type_flag_skips_classification(tmp_path, monkeypatch):
    """classify_drift=False → bbox records have no drift_type field."""
    import diff_bbox_extract as dbe

    monkeypatch.setattr(
        dbe, "extract_bboxes_px",
        lambda *a, **k: [
            {"x_px": 0, "y_px": 0, "w_px": 30, "h_px": 30, "area_px": 900,
             "mean_color": "#ff0000"},
        ],
    )
    monkeypatch.setattr(dbe, "load_dpi", lambda *a, **k: 150)
    monkeypatch.setattr(dbe, "load_template_slots", lambda slug: {})

    vd_payload = {"pages": [{"page": 0, "delta_png": "diff-page-01.png"}]}
    import json
    (tmp_path / "visual_diff.json").write_text(
        json.dumps(vd_payload), encoding="utf-8",
    )
    Image.new("RGB", (60, 60), "black").save(tmp_path / "diff-page-01.png")

    payload = dbe.extract_all(tmp_path, classify_drift=False)
    bbox = payload["pages"][0]["bboxes"][0]
    assert "drift_type" not in bbox

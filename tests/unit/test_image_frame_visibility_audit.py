"""Unit tests for tools/image_frame_visibility_audit.py.

Focus: the asset-render-ratio metric (the missing-asset blind-spot fix).

Raw bbox ink density is fooled by a missing white-on-transparent asset:
when the asset fails to render the bbox simply shows the page background,
and a coloured page background reads as a tolerable "faint" density even
though the brand asset is 100% absent. ``measure_asset_render_ratio``
works per-pixel against the baseline asset so it detects the asset's OWN
content; ``measure_frame_visibility`` then hard-fails (``invisible``) when
that ratio drops below the floor — never tolerates it as ``faint``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

Image = pytest.importorskip("PIL.Image", reason="Pillow required").Image
from PIL import Image as PILImage  # noqa: E402

from image_frame_visibility_audit import (  # noqa: E402
    ImageFrameInfo,
    _MIN_ASSET_RENDER_RATIO,
    measure_asset_render_ratio,
    measure_frame_visibility,
)


# Map a 200x200 px region to a mm bbox at 150 dpi so _bbox_pixels lands
# squarely on the synthetic image.
_DPI = 150
_REGION_PX = 200
_MM = _REGION_PX / (72.0 / 25.4 * (_DPI / 72.0))
_BBOX = (0.0, 0.0, _MM, _MM)
_BG = (200, 210, 180)  # a coloured page background


def _img(fill: tuple[int, int, int]) -> "PILImage.Image":
    return PILImage.new("RGB", (_REGION_PX, _REGION_PX), fill)


def _paint(img: "PILImage.Image", colour: tuple[int, int, int],
           box: tuple[int, int, int, int]) -> None:
    px = img.load()
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        for x in range(x0, x1):
            px[x, y] = colour


# ---------------------------------------------------------------------------
# measure_asset_render_ratio
# ---------------------------------------------------------------------------
def test_render_ratio_present_asset_near_one():
    """When the asset renders identically the ratio is ~1."""
    bl = _img(_BG)
    pv = _img(_BG)
    _paint(bl, (20, 30, 25), (20, 20, 180, 180))   # dark logo glyphs
    _paint(pv, (20, 30, 25), (20, 20, 180, 180))   # rendered the same
    ratio, ink, rendered = measure_asset_render_ratio(bl, pv, _BBOX, _DPI, _BG)
    assert ink > 0
    assert ratio > 0.95


def test_render_ratio_missing_asset_near_zero():
    """A genuinely missing asset — preview shows only the page background
    — yields a near-zero ratio even though the bbox is full of background
    ink that the raw density metric would mistake for a faint asset."""
    bl = _img(_BG)
    pv = _img(_BG)
    _paint(bl, (20, 30, 25), (20, 20, 180, 180))   # baseline has the logo
    # preview: asset never rendered; bbox is pure page background.
    ratio, ink, rendered = measure_asset_render_ratio(bl, pv, _BBOX, _DPI, _BG)
    assert ink > 0
    assert ratio < 0.05


def test_render_ratio_background_bleed_through_still_fails():
    """The blind-spot case: the asset is absent but a NON-background
    colour bleeds through the bbox. Raw density reads this as healthy
    "ink"; the asset-render ratio still collapses because that ink is
    not the asset's own content."""
    bl = _img(_BG)
    pv = _img(_BG)
    _paint(bl, (20, 30, 25), (20, 20, 180, 180))     # dark logo
    _paint(pv, (110, 120, 95), (20, 20, 180, 180))   # bleed: not the logo,
    #                                                  far from page bg too
    ratio, ink, rendered = measure_asset_render_ratio(bl, pv, _BBOX, _DPI, _BG)
    assert ratio < _MIN_ASSET_RENDER_RATIO


# ---------------------------------------------------------------------------
# measure_frame_visibility — classification gate
# ---------------------------------------------------------------------------
def test_frame_visibility_present_asset_ok(tmp_path):
    bl_p = tmp_path / "bl-1.png"
    pv_p = tmp_path / "pv-1.png"
    bl = _img(_BG)
    pv = _img(_BG)
    _paint(bl, (20, 30, 25), (20, 20, 180, 180))
    _paint(pv, (20, 30, 25), (20, 20, 180, 180))
    bl.save(bl_p)
    pv.save(pv_p)
    info = ImageFrameInfo("logo", 0, _BBOX, None, True, None)
    row = measure_frame_visibility(info, [bl_p], [pv_p], _DPI)
    assert row["classification"] == "ok"
    assert row["asset_render_ratio"] > 0.95


def test_frame_visibility_missing_asset_is_hard_failure(tmp_path):
    """A missing brand asset must classify as ``invisible_in_preview`` —
    a hard FAILURE — never as a tolerated ``faint_in_preview``."""
    bl_p = tmp_path / "bl-1.png"
    pv_p = tmp_path / "pv-1.png"
    bl = _img(_BG)
    pv = _img(_BG)
    _paint(bl, (20, 30, 25), (20, 20, 180, 180))   # logo present in baseline
    # preview: logo absent — bbox is pure page background.
    bl.save(bl_p)
    pv.save(pv_p)
    info = ImageFrameInfo("logo", 0, _BBOX, None, True, None)
    row = measure_frame_visibility(info, [bl_p], [pv_p], _DPI)
    assert row["classification"] == "invisible_in_preview"
    assert row["asset_render_ratio"] < _MIN_ASSET_RENDER_RATIO


def test_frame_visibility_bleed_through_not_tolerated_as_faint(tmp_path):
    """Deliberately-broken case proving the audit now fails: the asset is
    absent but the bbox shows a non-background bleed colour. The OLD
    visibility-ratio metric reads this as healthy ink (ratio ~1.0) and
    passes; the asset-render metric collapses → hard failure."""
    bl_p = tmp_path / "bl-1.png"
    pv_p = tmp_path / "pv-1.png"
    bl = _img(_BG)
    pv = _img(_BG)
    _paint(bl, (20, 30, 25), (20, 20, 180, 180))     # baseline logo
    _paint(pv, (110, 120, 95), (20, 20, 180, 180))   # bleed-through, no logo
    bl.save(bl_p)
    pv.save(pv_p)
    info = ImageFrameInfo("logo", 0, _BBOX, None, True, None)
    row = measure_frame_visibility(info, [bl_p], [pv_p], _DPI)
    # The old metric would have been fooled — confirm it reads "healthy".
    assert row["visibility_ratio"] > 0.7
    # The new gate fails it anyway.
    assert row["classification"] == "invisible_in_preview"
    assert row["asset_render_ratio"] < _MIN_ASSET_RENDER_RATIO

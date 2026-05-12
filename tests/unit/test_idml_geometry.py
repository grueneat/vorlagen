"""Unit tests for the IDML geometry helpers (issue 35, task 2).

These pin the 3-stacked coordinate cascade math: parse a "a b c d tx ty"
ItemTransform string, compose Group transforms outermost-first, apply to
PathPointArray anchors, subtract spread+page origins, and return
(x_pt, y_pt, w_pt, h_pt, rotation_deg) in page-top-left coordinates.

Test corpus is hand-picked from the target IDML's most awkward frames:
- Axis-aligned rectangle (the easy case)
- 90° rotated TextFrame with frame-centre inner origin (u347)
- 9° rotated cover panel (u186)
- Nested Group (synthetic; corpus has 5+10 group instances)
- Shear/non-uniform-scale rejection (strict-mode guard)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from idml_to_dsl import (  # noqa: E402
    UnhandledElement,
    _apply_matrix,
    _compute_page_local_bbox_pt,
    _inner_bbox_from_anchors,
    _matrix_compose,
    _parse_matrix,
)

IDENT = "1 0 0 1 0 0"


def test_identity_compose():
    I = _parse_matrix(IDENT)
    M = _parse_matrix("0.5 0 0 0.5 10 20")
    assert _matrix_compose(I, M) == M
    assert _matrix_compose(M, I) == M


def test_translation_only():
    M = _parse_matrix("1 0 0 1 100 200")
    assert _apply_matrix(M, 0, 0) == pytest.approx((100, 200))
    assert _apply_matrix(M, 5, 7) == pytest.approx((105, 207))


def test_axis_aligned_rectangle():
    # Rectangle at spread (100,100), 50×30 pt, no rotation, no ancestors,
    # spread identity, page origin at (-420.94, -140.31) per target IDML.
    anchors = [(0, 0), (50, 0), (50, 30), (0, 30)]
    x, y, w, h, rot = _compute_page_local_bbox_pt(
        item_transform_str="1 0 0 1 100 100",
        anchors=anchors,
        ancestor_transforms=[],
        spread_item_transform_str=IDENT,
        page_item_transform_str="1 0 0 1 -420.94 -140.31",
    )
    assert (w, h) == pytest.approx((50, 30))
    assert rot == pytest.approx(0, abs=1e-6)
    # Item lives at page-local (100 - (-420.94), 100 - (-140.31)) = (520.94, 240.31)
    assert x == pytest.approx(520.94)
    assert y == pytest.approx(240.31)


def test_rotated_90deg_textframe():
    # Mimics target IDML's u347: 90° CCW, TextFrame inner anchors symmetric
    # around 0. ItemTransform≈"0 -1 1 0 124.68 180.78"; spread u108 carries
    # a y-offset 786.61 pt.
    anchors = [
        (-49.5, -148.82),
        (49.5, -148.82),
        (49.5, 148.82),
        (-49.5, 148.82),
    ]
    x, y, w, h, rot = _compute_page_local_bbox_pt(
        item_transform_str="0 -1 1 0 124.68 180.78",
        anchors=anchors,
        ancestor_transforms=[],
        spread_item_transform_str="1 0 0 1 0 786.61",
        page_item_transform_str="1 0 0 1 -420.94 -140.31",
    )
    # After 90° CCW, the inner 99×297.64 rectangle becomes 297.64×99 AABB
    assert (w, h) == pytest.approx((297.64, 99), rel=1e-3)
    # Rotation is ±90°; we don't pin sign here (Scribus CCW convention may flip
    # during emit testing — convention documented in code).
    assert abs(abs(rot) - 90) < 1


def test_rotated_9deg_frame():
    # u186 cover panel: ItemTransform "0.9877 -0.1564 0.1564 0.9877 11.54 233.10".
    anchors = [(0, 0), (60, 0), (60, 40), (0, 40)]
    _, _, w, h, rot = _compute_page_local_bbox_pt(
        item_transform_str="0.9877 -0.1564 0.1564 0.9877 11.54 233.10",
        anchors=anchors,
        ancestor_transforms=[],
        spread_item_transform_str=IDENT,
        page_item_transform_str="1 0 0 1 -420.94 -140.31",
    )
    # 9° rotation → AABB grows past the raw 60×40
    assert w > 60 and h > 40
    assert abs(abs(rot) - 9) < 0.5


def test_nested_group():
    # Outer group translates (50,50); inner group rotates 90°; item at (10,0)..(20,10).
    # ancestor_transforms order is inner→outer (innermost first in the list).
    anchors = [(0, 0), (10, 0), (10, 10), (0, 10)]
    _, _, w, h, rot = _compute_page_local_bbox_pt(
        item_transform_str="1 0 0 1 10 0",
        anchors=anchors,
        ancestor_transforms=["0 -1 1 0 0 0", "1 0 0 1 50 50"],
        spread_item_transform_str=IDENT,
        page_item_transform_str=IDENT,
    )
    # Item passes through inner→outer correctly: shape stays 10×10
    assert (w, h) == pytest.approx((10, 10), abs=0.01)
    assert abs(abs(rot) - 90) < 1


def test_inner_bbox_from_anchors():
    assert _inner_bbox_from_anchors([(0, 0), (50, 30), (50, 0), (0, 30)]) == (0, 0, 50, 30)
    assert _inner_bbox_from_anchors([(-5, -3), (5, -3), (5, 3), (-5, 3)]) == (-5, -3, 5, 3)


def test_shear_rejected():
    with pytest.raises(UnhandledElement):
        _compute_page_local_bbox_pt(
            item_transform_str="1 0.5 0 1 0 0",  # shear
            anchors=[(0, 0), (10, 0), (10, 10), (0, 10)],
            ancestor_transforms=[],
            spread_item_transform_str=IDENT,
            page_item_transform_str=IDENT,
        )


def test_page_geometric_bounds_offset():
    """Pages can have a non-(0,0) interior origin; GeometricBounds y1/x1
    must be subtracted to get a true page-top-left coord system.

    Mirrors the target IDML's cover spread:
      Page u10f: ItemTransform '1 0 0 1 -420.94 -140.31',
                 GeometricBounds '-157.32 0 437.95 841.89' (y1 x1 y2 x2)
      Rect at spread origin (0, 0) with anchors at the spread-trim bbox.
    """
    anchors = [
        (-420.9448818897638, -297.6377952755905),
        (-420.9448818897638, 297.6377952755905),
        (420.9448818897638, 297.6377952755905),
        (420.9448818897638, -297.6377952755905),
    ]
    # Without geometric_bounds — comes out offset.
    x_no_gb, y_no_gb, w_no_gb, h_no_gb, _ = _compute_page_local_bbox_pt(
        item_transform_str="1 0 0 1 0 0",
        anchors=anchors,
        ancestor_transforms=[],
        spread_item_transform_str=IDENT,
        page_item_transform_str="1 0 0 1 -420.9448818897638 -140.31496062992127",
    )
    assert w_no_gb == pytest.approx(841.89, rel=1e-3)
    assert h_no_gb == pytest.approx(595.28, rel=1e-3)
    # WITH geometric_bounds — rectangle aligns to page top-left.
    x, y, w, h, _ = _compute_page_local_bbox_pt(
        item_transform_str="1 0 0 1 0 0",
        anchors=anchors,
        ancestor_transforms=[],
        spread_item_transform_str=IDENT,
        page_item_transform_str="1 0 0 1 -420.9448818897638 -140.31496062992127",
        page_geometric_bounds=(-157.32283464566927, 0.0, 437.9527559055118, 841.8897637795276),
    )
    assert x == pytest.approx(0, abs=0.01)
    assert y == pytest.approx(0, abs=0.01)
    assert (w, h) == pytest.approx((841.89, 595.28), rel=1e-3)


def test_two_level_nested_group():
    """Three-level cascade: item inside inner Group inside outer Group.

    Mirrors u50c (outer) → u508 (inner) → u477 (Rectangle) from the target
    IDML, which is a 2-deep Group nesting for the BlueSky social icon.

    Outer group: tx=7.37, ty=0  (u50c ItemTransform, simplified)
    Inner group: tx=0, ty=0    (u508 identity)
    Item:        tx=388.37, ty=249.00  (u477 ItemTransform, simplified)
    Anchors:     (-87.90, -19.48) to (-78.40, -10.13)  (9.50×9.35 pt)

    ancestor_transforms order: innermost-first → [inner_group, outer_group]
    """
    anchors = [
        (-87.90, -19.48),
        (-87.90, -10.13),
        (-78.40, -10.13),
        (-78.40, -19.48),
    ]
    # outer → inner → item cascade
    x, y, w, h, rot = _compute_page_local_bbox_pt(
        item_transform_str="1 0 0 1 388.37 249.00",
        anchors=anchors,
        # innermost first: inner group (identity), then outer group (tx=7.37)
        ancestor_transforms=["1 0 0 1 0 0", "1 0 0 1 7.37 0"],
        spread_item_transform_str=IDENT,
        page_item_transform_str=IDENT,
    )
    # Width/height unchanged by pure translations
    assert (w, h) == pytest.approx((9.50, 9.35), abs=0.01)
    assert rot == pytest.approx(0, abs=1e-4)
    # x: (-87.90 + 388.37) + 0 + 7.37 = 307.84
    # y: (-19.48 + 249.00) + 0 + 0 = 229.52
    assert x == pytest.approx(307.84, abs=0.1)
    assert y == pytest.approx(229.52, abs=0.1)


def test_parse_matrix_rejects_bad_token_count():
    with pytest.raises(UnhandledElement):
        _parse_matrix("1 0 0 1 0")  # only 5 tokens
    with pytest.raises(UnhandledElement):
        _parse_matrix("1 0 0 1 0 0 0")  # 7 tokens


# ---------------------------------------------------------------------------
# Issue #37 P1 task 4 — Backport 10 edge fix: emit scale_type=1 whenever the
# converter actually expresses a non-trivial crop (local_scale != (1,1) or
# local_offset_mm != (0,0)). Otherwise Scribus's default SCALETYPE=0
# (ScaleAuto = fit-to-frame) silently ignores the LOCAL* params.
# ---------------------------------------------------------------------------

from idml_to_dsl import (  # noqa: E402
    PythonRepr,
    _Ctx,
    _emit_image_frame_call,
)


def _make_ctx() -> _Ctx:
    ctx = _Ctx(pkg=None, template_id="test", assets_dir=Path("."), out=PythonRepr())
    ctx._current_page_var = "page0"  # type: ignore[attr-defined]
    return ctx


def _emit(ctx, **kwargs) -> str:
    """Emit an ImageFrame call with sensible defaults; return the rendered output."""
    _emit_image_frame_call(
        ctx.out,
        x_mm=10.0,
        y_mm=20.0,
        w_mm=50.0,
        h_mm=40.0,
        rot=0.0,
        self_id="u123",
        layer_idx=0,
        image_path="img.png",
        ctx=ctx,
        **kwargs,
    )
    return ctx.out.render()


def test_scale_type_emitted_when_local_scale_deviates():
    """Local scale (0.5, 0.5) ≠ unity → scale_type=1 emitted."""
    ctx = _make_ctx()
    rendered = _emit(ctx, local_scale=(0.5, 0.5), local_offset_pt=(0.0, 0.0))
    assert "scale_type=1" in rendered
    assert "local_scale=(0.5, 0.5)" in rendered


def test_no_scale_type_for_full_fit_image():
    """Local scale (1, 1) and zero offset → no scale_type kwarg (inherits default 0)."""
    ctx = _make_ctx()
    rendered = _emit(ctx, local_scale=(1.0, 1.0), local_offset_pt=(0.0, 0.0))
    assert "scale_type=" not in rendered
    assert "local_scale" not in rendered
    assert "local_offset_mm" not in rendered


def test_scale_type_emitted_when_local_offset_non_trivial():
    """Non-zero local_offset (5.0pt → ~1.76mm) → scale_type=1 emitted."""
    ctx = _make_ctx()
    rendered = _emit(ctx, local_scale=(1.0, 1.0), local_offset_pt=(5.0, -3.0))
    assert "scale_type=1" in rendered
    assert "local_offset_mm" in rendered


def test_scale_type_emitted_once_when_both_deviate():
    """Both local_scale and local_offset non-trivial → scale_type=1 appears exactly once."""
    ctx = _make_ctx()
    rendered = _emit(ctx, local_scale=(0.5, 0.5), local_offset_pt=(5.0, -3.0))
    assert rendered.count("scale_type=1") == 1
    assert "local_scale=(0.5, 0.5)" in rendered
    assert "local_offset_mm" in rendered


def test_scale_type_not_emitted_when_offset_sub_mm():
    """Sub-0.01 mm offset (rounding noise) → treated as zero → no scale_type."""
    ctx = _make_ctx()
    # 0.001 pt ≈ 0.0003 mm — below the 0.01 mm threshold
    rendered = _emit(ctx, local_scale=(1.0, 1.0), local_offset_pt=(0.001, 0.001))
    assert "scale_type=" not in rendered
    assert "local_offset_mm" not in rendered

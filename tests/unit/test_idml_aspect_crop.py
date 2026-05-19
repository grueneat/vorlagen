"""Unit tests for the IDML aspect-fill pre-crop (tools/idml_to_dsl.py).

InDesign places photos with "Fill Proportionally": the image is scaled and
positioned, then the frame is a window onto it. Scribus 1.6.x has no
aspect-fill mode, so the converter pre-crops the image to the part the frame
exposes (``_aspect_crop_image``) and reports the rect the ImageFrame should
occupy. The crop is derived purely from the ``<Image>`` ItemTransform + the
frame anchors — never guessed.

Two cases are exercised:

  * cover  — the frame lies inside the image; the intersection is the frame;
             the crop is a sub-rectangle of the image (the pine banner).
  * contain — the image lies inside the frame; the intersection is the whole
             image; nothing is cropped; the ImageFrame shrinks to the image's
             rendered rect (the Leonore portrait).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_to_dsl import (  # noqa: E402
    _aspect_crop_image,
    _image_graphic_bounds_pt,
)
from lxml import etree  # noqa: E402


def _make_image(tmp_path: Path, w_px: int, h_px: int, color=(20, 120, 60)) -> Path:
    from PIL import Image

    p = tmp_path / "src.png"
    Image.new("RGB", (w_px, h_px), color).save(p)
    return p


# ---------------------------------------------------------------------------
# GraphicBounds parsing
# ---------------------------------------------------------------------------
def test_graphic_bounds_from_image_element():
    xml = (
        '<Image><Properties>'
        '<GraphicBounds Left="0" Top="0" Right="623.52" Bottom="415.68"/>'
        '</Properties></Image>'
    )
    img = etree.fromstring(xml)
    gb = _image_graphic_bounds_pt(img)
    assert gb == pytest.approx((623.52, 415.68))


def test_graphic_bounds_missing_returns_none():
    img = etree.fromstring("<Image><Properties/></Image>")
    assert _image_graphic_bounds_pt(img) is None


# ---------------------------------------------------------------------------
# Cover case — frame inside image (the pine banner)
# ---------------------------------------------------------------------------
def test_cover_case_crops_band_no_offset(tmp_path: Path):
    # Pine u906 geometry: image 2598×1732 px, GraphicBounds 623.52×415.68 pt,
    # placed at scale 0.68648 with translation, frame is a wide short band.
    src = _make_image(tmp_path, 2598, 1732)
    dst = tmp_path / "crops" / "out.png"
    res = _aspect_crop_image(
        src_path=src,
        dst_path=dst,
        image_transform_str=(
            "0.6864759687948939 0 0 0.686475968794894 "
            "-299.6220472440946 1231.370078740158"
        ),
        graphic_bounds_pt=(623.52, 415.68),
        frame_anchors_bbox=(
            -299.6220472440945, 1363.39406699834,
            128.4094488188977, 1483.2755905511817,
        ),
    )
    assert res.cropped is True
    assert dst.exists()
    # Cover case: the frame lies inside the image → no ImageFrame offset.
    assert res.offset_pt == pytest.approx((0.0, 0.0), abs=1e-3)
    # Crop aspect must equal the frame aspect (so scale_type=0 fills exactly).
    from PIL import Image

    with Image.open(dst) as im:
        crop_aspect = im.size[0] / im.size[1]
    frame_aspect = (128.4094488188977 - (-299.6220472440945)) / (
        1483.2755905511817 - 1363.39406699834
    )
    assert crop_aspect == pytest.approx(frame_aspect, rel=2e-3)
    # Full image width is shown, only a vertical band of its height.
    with Image.open(dst) as im:
        assert im.size[0] == 2598
        assert im.size[1] < 1732


# ---------------------------------------------------------------------------
# Contain case — image inside frame (the Leonore portrait)
# ---------------------------------------------------------------------------
def test_contain_case_shrinks_frame_to_image(tmp_path: Path):
    # Leonore u9cc geometry: image 1388×2362 px, GraphicBounds 333.12×566.88
    # pt, placed at scale 0.48994 centred in a wider frame.
    src = _make_image(tmp_path, 1388, 2362)
    dst = tmp_path / "crops" / "out.png"
    res = _aspect_crop_image(
        src_path=src,
        dst_path=dst,
        image_transform_str=(
            "0.4899398523046795 0 0 0.4899398523046795 "
            "-566.7299238205528 -903.8280269431841"
        ),
        graphic_bounds_pt=(333.12, 566.88),
        frame_anchors_bbox=(
            -602.5520179621226, -903.8280269431841,
            -367.69906607924827, -626.0020406867501,
        ),
    )
    assert res.cropped is True
    # Contain case: the image is narrower than the frame → non-zero x offset,
    # the ImageFrame shrinks to the image's rendered size.
    assert res.offset_pt[0] > 1.0
    assert res.offset_pt[1] == pytest.approx(0.0, abs=0.5)
    # Reported size is the placed image's rendered rect (scale × GraphicBounds).
    assert res.size_pt[0] == pytest.approx(333.12 * 0.4899398523046795, rel=1e-3)
    # Nothing was cropped away — the whole source image is kept.
    from PIL import Image

    with Image.open(dst) as im:
        assert im.size == (1388, 2362)


# ---------------------------------------------------------------------------
# Degenerate / unsupported geometry
# ---------------------------------------------------------------------------
def test_identity_placement_is_noop(tmp_path: Path):
    # Image exactly fills the frame at scale 1.0, no translation → no crop.
    src = _make_image(tmp_path, 100, 100)
    dst = tmp_path / "crops" / "out.png"
    res = _aspect_crop_image(
        src_path=src,
        dst_path=dst,
        image_transform_str="1 0 0 1 0 0",
        graphic_bounds_pt=(100.0, 100.0),
        frame_anchors_bbox=(0.0, 0.0, 100.0, 100.0),
    )
    assert res.cropped is False
    assert not dst.exists()


def test_rotated_image_transform_skipped(tmp_path: Path):
    # A sheared / rotated <Image> transform (b/c non-zero) is not croppable
    # in pixel space — the helper bows out so the caller falls back.
    src = _make_image(tmp_path, 100, 100)
    dst = tmp_path / "crops" / "out.png"
    res = _aspect_crop_image(
        src_path=src,
        dst_path=dst,
        image_transform_str="0 -1 1 0 0 0",
        graphic_bounds_pt=(100.0, 100.0),
        frame_anchors_bbox=(0.0, 0.0, 100.0, 100.0),
    )
    assert res.cropped is False
    assert not dst.exists()


def test_image_outside_frame_skipped(tmp_path: Path):
    # The placed image does not overlap the frame at all → nothing to crop.
    src = _make_image(tmp_path, 100, 100)
    dst = tmp_path / "crops" / "out.png"
    res = _aspect_crop_image(
        src_path=src,
        dst_path=dst,
        image_transform_str="1 0 0 1 500 500",
        graphic_bounds_pt=(100.0, 100.0),
        frame_anchors_bbox=(0.0, 0.0, 100.0, 100.0),
    )
    assert res.cropped is False
    assert not dst.exists()

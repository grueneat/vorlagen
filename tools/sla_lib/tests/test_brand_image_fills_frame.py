"""Tests for brand:image_fills_frame rule + library.compute_aspect_fill helper.

Issue #24. Synthetic primitives only — keeps unit tests fast (<1s) and
template-agnostic. Real-template invariants live in
``test_zeitung_geometry.py::ImageContentExtentInvariantTests``.

Coverage matrix:

  1. Empty image frame skipped (the 3-Dunkelgruen-polygon class).
  2. Inline JPEG matched dims passes (no violation).
  3. Inline JPEG undersized on interior frame -> warning.
  4. Inline JPEG undersized on full-bleed frame -> error.
  5. Disk image resolved against template root + missing file -> warning.
  6. scale_type=1 + ratio=1 letterbox INSIDE detected.
  7. scale_type=1 + ratio=0 stretch skipped (no violation).
  8. compute_aspect_fill returns qMax scalar (cover math).
  9. qCompress roundtrip decode (sanity for the rule's reverse path).
 10. DPI from JFIF density (rule honors non-300 DPI).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from PIL import Image  # noqa: E402

from sla_lib.builder import Document  # noqa: E402
from sla_lib.builder.brand_constraints import (  # noqa: E402
    _ImageFillsFrameRule,
)
from sla_lib.builder.library import compute_aspect_fill  # noqa: E402
from sla_lib.builder.primitives import (  # noqa: E402
    ImageFrame,
    pack_inline_image,
)


def _make_jpeg_bytes(w_px: int, h_px: int, dpi: int = 300) -> bytes:
    """Make a tiny JPEG of given pixel dims + JFIF density.

    Solid-colour image; bytes-deterministic per Pillow==12.2.0.
    """
    im = Image.new("RGB", (w_px, h_px), (128, 128, 128))
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=80, dpi=(dpi, dpi))
    return buf.getvalue()


def _doc_a4_facing(bleed=3.0):
    """A4 facing-pages doc with one page, bleed=3."""
    d = Document(title="t", template_id="t", facing_pages=True)
    d.add_page(size="A4", bleed_mm=bleed)
    return d


def _rule() -> _ImageFillsFrameRule:
    return _ImageFillsFrameRule(
        id="brand:image_fills_frame", name="", description="",
    )


class EmptyImageFrameTests(unittest.TestCase):
    def test_empty_image_frame_skipped(self):
        """ImageFrame with no image/src/inline_image_data -> 0 violations.

        Models the 3 unnamed Dunkelgruen polygons on Zeitung pages
        12/13/14 (per locked decision #3, Issue #24).
        """
        d = _doc_a4_facing()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=50,
            image="", src="", inline_image_data=None,
            fill="Dunkelgruen", anname="solid_polygon",
        ))
        viols = _rule().check(list(d.iter_all_primitives()), d)
        self.assertEqual(viols, [])


class InlineJpegMatchedDimsTests(unittest.TestCase):
    def test_inline_jpeg_matched_dims_passes(self):
        """100x100mm frame + JPEG at exactly 100x100mm @ 300dpi -> 0 viols."""
        # 100mm at 300dpi = 100 / 25.4 * 300 ~ 1181.10 px. Round.
        px = int(round(100.0 * 300 / 25.4))   # 1181
        jpg = _make_jpeg_bytes(px, px, dpi=300)
        data, _ext = pack_inline_image(jpg, "jpg")
        d = _doc_a4_facing()
        d.pages[0].add(ImageFrame(
            x_mm=20, y_mm=20, w_mm=100, h_mm=100,
            inline_image_data=data, inline_image_ext="jpg",
            scale_type=0, anname="hero",
        ))
        viols = _rule().check(list(d.iter_all_primitives()), d)
        self.assertEqual(viols, [], msg=f"unexpected: {viols}")


class InlineJpegUndersizedInteriorTests(unittest.TestCase):
    def test_inline_jpeg_undersized_fails_warning(self):
        """100x100mm frame + JPEG at 95x100mm @ 300dpi (interior) -> 1 warning."""
        # 95mm wide x 100mm tall.
        w_px = int(round(95.0 * 300 / 25.4))   # 1122
        h_px = int(round(100.0 * 300 / 25.4))  # 1181
        jpg = _make_jpeg_bytes(w_px, h_px, dpi=300)
        data, _ext = pack_inline_image(jpg, "jpg")
        d = _doc_a4_facing()
        # Interior frame: not touching any bleed (well inside 210x297 page).
        d.pages[0].add(ImageFrame(
            x_mm=50, y_mm=50, w_mm=100, h_mm=100,
            inline_image_data=data, inline_image_ext="jpg",
            scale_type=0, anname="interior_hero",
        ))
        viols = _rule().check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(viols), 1, msg=f"expected 1, got: {viols}")
        v = viols[0]
        self.assertEqual(v.severity, "warning")
        self.assertEqual(v.rule_id, "brand:image_fills_frame")
        # Message must mention the gap and the INJECT_MAP fix line.
        self.assertIn("white margin", v.message)
        self.assertIn("update INJECT_MAP target", v.message)
        # Gap_w should be ~5mm (100 frame - 95 rendered = 5).
        self.assertIn("5.0", v.message)


class InlineJpegUndersizedFullBleedTests(unittest.TestCase):
    def test_inline_jpeg_undersized_full_bleed_fails_error(self):
        """Same JPEG on a frame whose bbox reaches -bleed -> error severity."""
        w_px = int(round(95.0 * 300 / 25.4))
        h_px = int(round(100.0 * 300 / 25.4))
        jpg = _make_jpeg_bytes(w_px, h_px, dpi=300)
        data, _ext = pack_inline_image(jpg, "jpg")
        d = _doc_a4_facing(bleed=3.0)
        # x=-3 reaches the left bleed (x0 == -bleed).
        d.pages[0].add(ImageFrame(
            x_mm=-3, y_mm=50, w_mm=100, h_mm=100,
            inline_image_data=data, inline_image_ext="jpg",
            scale_type=0, anname="full_bleed_hero",
        ))
        viols = _rule().check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(viols), 1, msg=f"expected 1, got: {viols}")
        self.assertEqual(viols[0].severity, "error")


class DiskImageResolutionTests(unittest.TestCase):
    def test_disk_image_missing_file_warns(self):
        """frame.image points to a non-existent disk path -> 1 warning."""
        d = _doc_a4_facing()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=50, h_mm=50,
            image="nonexistent/missing.jpg",
            scale_type=0, anname="missing_disk",
        ))
        viols = _rule().check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(viols), 1, msg=f"got: {viols}")
        self.assertEqual(viols[0].severity, "warning")
        self.assertIn("asset missing/corrupt", viols[0].message)

    def test_disk_image_resolved_against_template_root_passes(self):
        """frame.image resolves against doc._template_root + matched dims -> 0 viols."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            asset_rel = "themen/synthetic.jpg"
            asset_path = tmp_root / asset_rel
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            # 100mm at 300dpi.
            px = int(round(100.0 * 300 / 25.4))
            asset_path.write_bytes(_make_jpeg_bytes(px, px, dpi=300))

            d = _doc_a4_facing()
            d._template_root = tmp_root  # type: ignore[attr-defined]
            d.pages[0].add(ImageFrame(
                x_mm=20, y_mm=20, w_mm=100, h_mm=100,
                image=asset_rel, scale_type=0, anname="disk_hero",
            ))
            viols = _rule().check(list(d.iter_all_primitives()), d)
            self.assertEqual(viols, [], msg=f"got: {viols}")


class ScaleTypeMatrixTests(unittest.TestCase):
    def test_scale_type_1_ratio_1_letterbox_inside_detected(self):
        """200x100px @ 300dpi (~16.93x8.47mm) on 50x50mm frame, st=1, r=1.

        qMin scaling: s = min(50/16.93, 50/8.47) = min(2.95, 5.91) = 2.95.
        Rendered = 16.93*2.95 x 8.47*2.95 = 50.00 x 25.00 mm.
        Frame is 50x50, gap_h = 25mm > tol (0.5mm floor) -> warning.
        """
        jpg = _make_jpeg_bytes(200, 100, dpi=300)
        data, _ext = pack_inline_image(jpg, "jpg")
        d = _doc_a4_facing()
        d.pages[0].add(ImageFrame(
            x_mm=50, y_mm=50, w_mm=50, h_mm=50,
            inline_image_data=data, inline_image_ext="jpg",
            scale_type=1, ratio=1, anname="aspect_mismatch_st1_r1",
        ))
        viols = _rule().check(list(d.iter_all_primitives()), d)
        self.assertEqual(len(viols), 1, msg=f"got: {viols}")
        self.assertIn("white margin", viols[0].message)

    def test_scale_type_1_ratio_0_stretch_skipped(self):
        """Same setup but ratio=0 -> stretch fills exactly, no violation."""
        jpg = _make_jpeg_bytes(200, 100, dpi=300)
        data, _ext = pack_inline_image(jpg, "jpg")
        d = _doc_a4_facing()
        d.pages[0].add(ImageFrame(
            x_mm=50, y_mm=50, w_mm=50, h_mm=50,
            inline_image_data=data, inline_image_ext="jpg",
            scale_type=1, ratio=0, anname="stretch_st1_r0",
        ))
        viols = _rule().check(list(d.iter_all_primitives()), d)
        self.assertEqual(viols, [], msg=f"got: {viols}")


class ComputeAspectFillTests(unittest.TestCase):
    def test_compute_aspect_fill_returns_qmax_scalar(self):
        """compute_aspect_fill returns (s, s) where s = qMax of per-axis ratios.

        100x100mm frame + 1000x500px @ 300dpi:
          asset_mm = (84.67, 42.33).
          per_axis_scale = (100/84.67, 100/42.33) = (1.181, 2.362).
          qMax = 2.362 (cover / fill math).
        """
        sx, sy = compute_aspect_fill(100, 100, 1000, 500, dpi=300)
        self.assertEqual(sx, sy)
        self.assertAlmostEqual(sx, 2.362, delta=0.001)

    def test_compute_aspect_fill_taller_asset(self):
        """Tall asset on square frame: qMax picks the wide-side scale."""
        sx, sy = compute_aspect_fill(100, 100, 500, 1000, dpi=300)
        self.assertEqual(sx, sy)
        # asset_mm = (42.33, 84.67); ratios = (2.362, 1.181); qMax = 2.362.
        self.assertAlmostEqual(sx, 2.362, delta=0.001)

    def test_compute_aspect_fill_wider_frame(self):
        """Wide frame, small asset -> identity-ish scale on long axis."""
        # 200x100mm frame, 1000x500px @ 300dpi (asset is also 2:1 aspect).
        # asset_mm = (84.67, 42.33). ratios = (200/84.67, 100/42.33)
        # = (2.362, 2.362). qMax = 2.362.
        sx, sy = compute_aspect_fill(200, 100, 1000, 500, dpi=300)
        self.assertEqual(sx, sy)
        self.assertAlmostEqual(sx, 2.362, delta=0.001)


class QCompressRoundtripTests(unittest.TestCase):
    def test_qcompress_roundtrip_decode(self):
        """Encode via pack_inline_image, decode via the rule's reverse.

        Validates the qCompress-reverse path independent of rule logic.
        """
        import base64
        import struct
        import zlib
        original = _make_jpeg_bytes(500, 300, dpi=300)
        b64, _ext = pack_inline_image(original, "jpg")
        raw = base64.b64decode(b64)
        decoded_len = struct.unpack(">I", raw[:4])[0]
        self.assertEqual(decoded_len, len(original))
        decoded = zlib.decompress(raw[4:])
        self.assertEqual(decoded, original)
        # Decoded JPEG must round-trip through PIL with same dims.
        im = Image.open(BytesIO(decoded))
        self.assertEqual(im.size, (500, 300))


class DpiFromJfifDensityTests(unittest.TestCase):
    def test_dpi_from_jfif_density(self):
        """JPEG saved at 150dpi + frame dims matching JPEG @ 150dpi -> 0 viols.

        500x300px @ 150dpi -> ~84.67x50.80 mm. Frame matches -> rule
        reads JFIF density correctly and computes the right rendered mm.
        """
        jpg = _make_jpeg_bytes(500, 300, dpi=150)
        data, _ext = pack_inline_image(jpg, "jpg")
        # Compute frame dims at 150dpi exactly.
        w_mm_at_150 = 500 * 25.4 / 150  # 84.67
        h_mm_at_150 = 300 * 25.4 / 150  # 50.80
        d = _doc_a4_facing()
        d.pages[0].add(ImageFrame(
            x_mm=10, y_mm=10, w_mm=w_mm_at_150, h_mm=h_mm_at_150,
            inline_image_data=data, inline_image_ext="jpg",
            scale_type=0, anname="dpi_150_hero",
        ))
        viols = _rule().check(list(d.iter_all_primitives()), d)
        self.assertEqual(viols, [], msg=f"got: {viols}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

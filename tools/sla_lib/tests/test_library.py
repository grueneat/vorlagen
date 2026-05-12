"""Unit tests for tools/sla_lib/builder/library.py (issue #13).

Covers:
  - load() raise-vs-optional behavior
  - all_images() iteration
  - find() filters by tags + category
  - crop_for_frame() determinism (byte-identical on reruns)
  - crop_for_frame() watermark-after-crop regression (R-WATERMARK-CROP)
    - portrait source → landscape crop: band visible at the bottom of output
    - landscape source → portrait crop: band visible at the bottom of output
  - crop_focus saliency anchor (post-merge crop quality fix)
    - LibraryImage.crop_focus_x/_y read from manifest with default 0.5
    - crop_for_frame uses focus point, differs from default-centered crop
    - legacy ``centering`` field still honored for back-compat
    - malformed crop_focus silently degrades to (0.5, 0.5)
  - validate_manifest() catches schema violations
  - regenerate() (with codex.generate_image mocked) returns True

Tests use a self-contained fixture under tools/sla_lib/tests/fixtures/library/
seeded by the test setup — no real codex calls, no real library bytes.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

import yaml
from PIL import Image

# Ensure tools/ is on the import path for codex_image_gen and library.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from sla_lib.builder import library  # noqa: E402
import codex_image_gen  # noqa: E402


def _make_jpg(path: Path, size: tuple[int, int], color: tuple[int, int, int] = (180, 180, 180)) -> None:
    """Synthesize a solid-color JPG at given path/size and overlay the
    Symbolfoto watermark band so the migrated bytes look like real library
    output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", size, color)
    watermarked = codex_image_gen._apply_watermark_to_image(im)
    watermarked.save(
        str(path),
        format="JPEG",
        quality=80,
        optimize=True,
        subsampling=2,
        progressive=False,
    )


def _bottom_is_dark(jpeg_bytes: bytes) -> bool:
    """Return True if the bottom 4% of the JPEG is materially darker than the
    middle band (= watermark band visible)."""
    with Image.open(BytesIO(jpeg_bytes)) as im:
        rgb = im.convert("L")
    w, h = rgb.size
    # Sample ~bottom 2% (well inside band) and ~middle 50%.
    bottom_band = rgb.crop((0, int(h * 0.97), w, h))
    middle_band = rgb.crop((0, int(h * 0.40), w, int(h * 0.60)))
    bot_pixels = list(bottom_band.getdata())
    mid_pixels = list(middle_band.getdata())
    bot_mean = sum(bot_pixels) / len(bot_pixels)
    mid_mean = sum(mid_pixels) / len(mid_pixels)
    # 30 L-units is a generous floor: the band is ~63% alpha black on grey
    # mid-tones, easy difference.
    return (mid_mean - bot_mean) > 30


class LibraryFixture:
    """Build a tiny self-contained library at a temp dir + monkeypatch
    LIBRARY_ROOT/MANIFEST_PATH to point at it for the duration of a test."""

    def __init__(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "portraits").mkdir()
        (self.root / "themen").mkdir()
        (self.root / "kontext").mkdir()
        # Two portraits + two themen entries — minimum diversity for the find()
        # tests.
        _make_jpg(self.root / "portraits" / "alice.jpg", (1024, 1536))   # portrait aspect
        _make_jpg(self.root / "portraits" / "bob.jpg", (1024, 1536))     # portrait aspect
        _make_jpg(self.root / "themen" / "topic1.jpg", (1536, 1024))     # landscape
        _make_jpg(self.root / "themen" / "topic2.jpg", (1536, 1024))     # landscape

        manifest = {
            "images": {
                "portrait_alice": {
                    "path": "portraits/alice.jpg",
                    "prompt": "A demo portrait prompt for alice — long enough to satisfy schema minLength.",
                    "tags": ["portrait", "gender:female"],
                    "synthetic": True,
                    "license_note": "AI-generated demo image; not a real person.",
                    "size": "1024x1536",
                    "watermark": "Symbolfoto — KI-generiert",
                },
                "portrait_bob": {
                    "path": "portraits/bob.jpg",
                    "prompt": "A demo portrait prompt for bob — long enough to satisfy schema minLength.",
                    "tags": ["portrait", "gender:male"],
                    "synthetic": True,
                    "license_note": "AI-generated demo image; not a real person.",
                    "size": "1024x1536",
                    "watermark": "Symbolfoto — KI-generiert",
                },
                "themen_topic1": {
                    "path": "themen/topic1.jpg",
                    "prompt": "A demo themen prompt for topic1 — long enough to satisfy schema minLength.",
                    "tags": ["themen", "topic:demo"],
                    "synthetic": True,
                    "license_note": "AI-generated demo image; not a real place.",
                    "size": "1536x1024",
                    "watermark": "Symbolfoto — KI-generiert",
                },
                "themen_topic2": {
                    "path": "themen/topic2.jpg",
                    "prompt": "A demo themen prompt for topic2 — long enough to satisfy schema minLength.",
                    "tags": ["themen", "topic:demo"],
                    "synthetic": True,
                    "license_note": "AI-generated demo image; not a real place.",
                    "size": "1536x1024",
                    "watermark": "Symbolfoto — KI-generiert",
                },
            }
        }
        self.manifest_path = self.root / "manifest.yml"
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(manifest, f, sort_keys=False, allow_unicode=True)

    def cleanup(self) -> None:
        self.tmpdir.cleanup()


class LoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = LibraryFixture()
        self.p_root = mock.patch.object(library, "LIBRARY_ROOT", self.fx.root)
        self.p_man = mock.patch.object(library, "MANIFEST_PATH", self.fx.manifest_path)
        self.p_root.start()
        self.p_man.start()

    def tearDown(self) -> None:
        self.p_root.stop()
        self.p_man.stop()
        self.fx.cleanup()

    def test_load_known_id(self) -> None:
        img = library.load("portrait_alice")
        self.assertIsNotNone(img)
        assert img is not None  # mypy
        self.assertEqual(img.id, "portrait_alice")
        self.assertTrue(img.path.is_absolute())
        self.assertTrue(len(img.bytes) > 0)
        self.assertEqual(img.meta["tags"], ["portrait", "gender:female"])

    def test_load_missing_required_raises(self) -> None:
        with self.assertRaises(library.LibraryError):
            library.load("does_not_exist")

    def test_load_missing_optional_returns_none(self) -> None:
        self.assertIsNone(library.load("does_not_exist", optional=True))


class AllImagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = LibraryFixture()
        self.p_root = mock.patch.object(library, "LIBRARY_ROOT", self.fx.root)
        self.p_man = mock.patch.object(library, "MANIFEST_PATH", self.fx.manifest_path)
        self.p_root.start()
        self.p_man.start()

    def tearDown(self) -> None:
        self.p_root.stop()
        self.p_man.stop()
        self.fx.cleanup()

    def test_iterates_all_entries(self) -> None:
        all_imgs = library.all_images()
        self.assertEqual(
            set(all_imgs.keys()),
            {"portrait_alice", "portrait_bob", "themen_topic1", "themen_topic2"},
        )


class FindTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = LibraryFixture()
        self.p_root = mock.patch.object(library, "LIBRARY_ROOT", self.fx.root)
        self.p_man = mock.patch.object(library, "MANIFEST_PATH", self.fx.manifest_path)
        self.p_root.start()
        self.p_man.start()

    def tearDown(self) -> None:
        self.p_root.stop()
        self.p_man.stop()
        self.fx.cleanup()

    def test_find_by_tags(self) -> None:
        portraits = library.find(tags=["portrait"])
        self.assertEqual([im.id for im in portraits], ["portrait_alice", "portrait_bob"])

    def test_find_by_specific_tag(self) -> None:
        female = library.find(tags=["portrait", "gender:female"])
        self.assertEqual([im.id for im in female], ["portrait_alice"])

    def test_find_by_category(self) -> None:
        themen = library.find(category="themen")
        self.assertEqual([im.id for im in themen], ["themen_topic1", "themen_topic2"])


class CropForFrameTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = LibraryFixture()
        self.p_root = mock.patch.object(library, "LIBRARY_ROOT", self.fx.root)
        self.p_man = mock.patch.object(library, "MANIFEST_PATH", self.fx.manifest_path)
        self.p_root.start()
        self.p_man.start()

    def tearDown(self) -> None:
        self.p_root.stop()
        self.p_man.stop()
        self.fx.cleanup()

    def test_determinism(self) -> None:
        img = library.load("themen_topic1")
        assert img is not None
        out1 = library.crop_for_frame(img, target_w_mm=87, target_h_mm=24)
        out2 = library.crop_for_frame(img, target_w_mm=87, target_h_mm=24)
        self.assertEqual(out1, out2, "crop output not byte-deterministic")

    def test_landscape_crop_from_portrait_keeps_watermark(self) -> None:
        # portrait (1024×1536) → landscape (200×60mm ≈ wide) — the source band
        # would be cropped off by ImageOps.fit; we expect the band re-stamped
        # on the cropped output.
        img = library.load("portrait_alice")
        assert img is not None
        out = library.crop_for_frame(img, target_w_mm=200, target_h_mm=60)
        self.assertTrue(
            _bottom_is_dark(out),
            "watermark band missing from portrait→landscape crop output",
        )

    def test_portrait_crop_from_landscape_keeps_watermark(self) -> None:
        # landscape (1536×1024) → portrait (87×105mm ≈ tall) — left/right is
        # cropped, vertical scale changes; band must still be present.
        img = library.load("themen_topic1")
        assert img is not None
        out = library.crop_for_frame(img, target_w_mm=87, target_h_mm=105)
        self.assertTrue(
            _bottom_is_dark(out),
            "watermark band missing from landscape→portrait crop output",
        )

    def test_target_dimensions_in_pixels(self) -> None:
        img = library.load("themen_topic1")
        assert img is not None
        out = library.crop_for_frame(img, target_w_mm=87, target_h_mm=24, dpi=300)
        with Image.open(BytesIO(out)) as decoded:
            w, h = decoded.size
        # 87mm @ 300dpi = 87 * 300/25.4 = 1027.56 → 1028 px
        # 24mm @ 300dpi = 24 * 300/25.4 = 283.46 → 283 px
        self.assertEqual(w, round(87 * 300 / 25.4))
        self.assertEqual(h, round(24 * 300 / 25.4))

    def test_jpeg_carries_target_dpi_density(self) -> None:
        """Output JPEG must embed the target DPI in its JFIF density header.

        Scribus reads JFIF density to compute on-page mm size; without it the
        default 72 dpi makes a 2480-px crop overflow a 595-pt frame ~3.4×,
        which surfaced as the live gallery's sky-only / window-only renders
        (root cause of the user-reported regression). Pinning density keeps
        the SLA frame's SCALETYPE round-trip-safe AND makes the image render
        at its physical mm size.
        """
        img = library.load("themen_topic1")
        assert img is not None
        out = library.crop_for_frame(img, target_w_mm=87, target_h_mm=24, dpi=300)
        with Image.open(BytesIO(out)) as decoded:
            self.assertEqual(decoded.info.get("dpi"), (300, 300))

    def test_apply_watermark_false_skips_band(self) -> None:
        # Using a fresh non-watermarked source so the test is unambiguous: build
        # an unwatermarked file directly. The library entry already has a
        # watermarked file; crop with apply_watermark=False uses that as input
        # but does not re-stamp.
        # Plain solid grey (no watermark), bytes-only path.
        unwm_path = self.fx.root / "themen" / "topic_unwm.jpg"
        Image.new("RGB", (1536, 1024), (180, 180, 180)).save(
            str(unwm_path),
            format="JPEG",
            quality=80,
            optimize=True,
            subsampling=2,
            progressive=False,
        )
        # Patch in a fake LibraryImage pointing at the un-watermarked file.
        img = library.LibraryImage(
            id="topic_unwm",
            path=unwm_path,
            bytes=unwm_path.read_bytes(),
            meta={"path": "themen/topic_unwm.jpg", "watermark": "x"},
        )
        out = library.crop_for_frame(img, target_w_mm=87, target_h_mm=24, apply_watermark=False)
        self.assertFalse(
            _bottom_is_dark(out),
            "expected no watermark band when apply_watermark=False",
        )


class CropFocusTests(unittest.TestCase):
    """Saliency-anchor crop tests — the post-merge crop quality fix.

    Background: the live gallery showed ``window-only``, ``hair-only`` and
    ``sky-only`` crops because every aspect-mismatched slot used the implicit
    centre (0.5, 0.5). ``crop_focus: [x, y]`` per manifest entry biases the
    crop toward the visual subject; this fixture-test pins the contract.
    """

    def setUp(self) -> None:
        self.fx = LibraryFixture()
        self.p_root = mock.patch.object(library, "LIBRARY_ROOT", self.fx.root)
        self.p_man = mock.patch.object(library, "MANIFEST_PATH", self.fx.manifest_path)
        self.p_root.start()
        self.p_man.start()

    def tearDown(self) -> None:
        self.p_root.stop()
        self.p_man.stop()
        self.fx.cleanup()

    def _set_field(self, image_id: str, field: str, value) -> None:
        """Mutate one manifest entry's field (or remove if value is None)."""
        with open(self.fx.manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if value is None:
            data["images"][image_id].pop(field, None)
        else:
            data["images"][image_id][field] = value
        with open(self.fx.manifest_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    # ---- Property accessors --------------------------------------------------

    def test_default_focus_is_image_center(self) -> None:
        img = library.load("portrait_alice")
        assert img is not None
        self.assertEqual(img.crop_focus_x, 0.5)
        self.assertEqual(img.crop_focus_y, 0.5)

    def test_crop_focus_read_from_manifest(self) -> None:
        self._set_field("portrait_alice", "crop_focus", [0.50, 0.30])
        img = library.load("portrait_alice")
        assert img is not None
        self.assertAlmostEqual(img.crop_focus_x, 0.50)
        self.assertAlmostEqual(img.crop_focus_y, 0.30)

    def test_legacy_centering_field_honored(self) -> None:
        # No crop_focus, but a legacy `centering` from earlier schema. The
        # property must still pick it up so that any pre-existing entries
        # don't silently regress to image-center.
        self._set_field("portrait_alice", "centering", [0.45, 0.55])
        img = library.load("portrait_alice")
        assert img is not None
        self.assertAlmostEqual(img.crop_focus_x, 0.45)
        self.assertAlmostEqual(img.crop_focus_y, 0.55)

    def test_crop_focus_takes_precedence_over_centering(self) -> None:
        # If both are set, crop_focus wins (canonical name).
        self._set_field("portrait_alice", "centering", [0.10, 0.10])
        self._set_field("portrait_alice", "crop_focus", [0.90, 0.90])
        img = library.load("portrait_alice")
        assert img is not None
        self.assertAlmostEqual(img.crop_focus_x, 0.90)
        self.assertAlmostEqual(img.crop_focus_y, 0.90)

    def test_malformed_focus_falls_back_to_center(self) -> None:
        # Wrong arity, wrong types, out-of-range — all degrade to (0.5, 0.5).
        for bad in ([0.5], "centre", [None, 0.3], [1.2, "x"]):
            self._set_field("portrait_alice", "crop_focus", bad)
            img = library.load("portrait_alice")
            assert img is not None
            self.assertEqual(img.crop_focus_x, 0.5, f"bad input: {bad!r}")
            self.assertEqual(img.crop_focus_y, 0.5, f"bad input: {bad!r}")

    def test_out_of_range_focus_is_clamped(self) -> None:
        # Defensive: numeric typos like 30 (instead of 0.30) clamp to 1.0
        # rather than raising or returning the default. Avoids silent breakage
        # on a single bad number.
        self._set_field("portrait_alice", "crop_focus", [-0.5, 1.5])
        img = library.load("portrait_alice")
        assert img is not None
        self.assertEqual(img.crop_focus_x, 0.0)
        self.assertEqual(img.crop_focus_y, 1.0)

    # ---- Crop output -------------------------------------------------------

    def test_focus_changes_cropped_pixel_content(self) -> None:
        """Two distinct focus points must produce visually different crops.

        Strategy: build a 1024×1536 source with a *vertical gradient* (top is
        bright, bottom is dark). Crop a wide-short region (200×60) from a
        *portrait* source — the height has to be cropped. With focus y=0.10
        we keep the brightest top band; with y=0.90 we keep the darkest
        bottom band. Compare mean luminance.

        This proves the focus argument actually flows through ImageOps.fit,
        not just survives validation.
        """
        gradient_path = self.fx.root / "themen" / "gradient.jpg"
        # Vertical luminance gradient, 1024 wide × 1536 tall.
        grad = Image.new("RGB", (1024, 1536))
        for y in range(1536):
            v = int(255 * (1 - y / 1535))   # 255 at top, 0 at bottom
            for x in range(1024):
                grad.putpixel((x, y), (v, v, v))
        grad.save(
            str(gradient_path), format="JPEG", quality=95, optimize=True,
            subsampling=2, progressive=False,
        )
        # Inject as a fresh manifest entry so library.load() picks it up.
        with open(self.fx.manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data["images"]["themen_gradient"] = {
            "path": "themen/gradient.jpg",
            "prompt": "A vertical luminance gradient — long enough to satisfy schema minLength.",
            "tags": ["themen", "topic:test"],
            "synthetic": True,
        }
        with open(self.fx.manifest_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

        # Crop with focus=top.
        self._set_field("themen_gradient", "crop_focus", [0.5, 0.10])
        img_top = library.load("themen_gradient")
        assert img_top is not None
        out_top = library.crop_for_frame(
            img_top, target_w_mm=200, target_h_mm=60, apply_watermark=False,
        )

        # Crop with focus=bottom.
        self._set_field("themen_gradient", "crop_focus", [0.5, 0.90])
        img_bot = library.load("themen_gradient")
        assert img_bot is not None
        out_bot = library.crop_for_frame(
            img_bot, target_w_mm=200, target_h_mm=60, apply_watermark=False,
        )

        # Pixel content must differ — proves crop_focus reaches ImageOps.fit.
        self.assertNotEqual(
            out_top, out_bot,
            "crop_focus had no effect on output bytes — the parameter is dead",
        )

        # Stronger check: top crop is brighter than bottom crop on a vertical
        # gradient. This catches the case where focus axes are swapped.
        with Image.open(BytesIO(out_top)) as im_t, Image.open(BytesIO(out_bot)) as im_b:
            mean_top = sum(im_t.convert("L").getdata()) / (im_t.width * im_t.height)
            mean_bot = sum(im_b.convert("L").getdata()) / (im_b.width * im_b.height)
        self.assertGreater(
            mean_top, mean_bot + 30,
            f"top-focus mean={mean_top:.1f} should be ≫ bottom-focus mean={mean_bot:.1f} "
            f"on a vertical gradient",
        )

    def test_focus_determinism(self) -> None:
        # Same focus + same source → byte-identical output across runs.
        self._set_field("portrait_alice", "crop_focus", [0.50, 0.35])
        img1 = library.load("portrait_alice")
        img2 = library.load("portrait_alice")
        assert img1 is not None and img2 is not None
        out1 = library.crop_for_frame(img1, target_w_mm=87, target_h_mm=24)
        out2 = library.crop_for_frame(img2, target_w_mm=87, target_h_mm=24)
        self.assertEqual(out1, out2, "crop_for_frame with crop_focus is not deterministic")

    def test_focus_in_manifest_validates(self) -> None:
        # crop_focus is a valid manifest field per the JSON schema.
        self._set_field("portrait_alice", "crop_focus", [0.50, 0.35])
        self.assertEqual(library.validate_manifest(), [])

    def test_focus_out_of_schema_range_caught(self) -> None:
        # Schema rejects values outside [0, 1] — even though the runtime
        # clamps them, the manifest itself should fail validation as a
        # signal that the entry is malformed.
        self._set_field("portrait_alice", "crop_focus", [1.2, 0.5])
        errors = library.validate_manifest()
        self.assertTrue(errors, "expected schema violation for crop_focus > 1.0")


class InjectIntoFrameTests(unittest.TestCase):
    """One-call inject helper — encapsulates the three things every gallery
    build.py must get right: crop to frame aspect, pack as inline JPEG, and
    set ``scale_type = 0`` (Scribus ScaleAuto) so the inline image actually
    fits the frame on render. SCALETYPE was the root cause of the live
    gallery's sky-only / window-only crops.
    """

    def setUp(self) -> None:
        self.fx = LibraryFixture()
        self.p_root = mock.patch.object(library, "LIBRARY_ROOT", self.fx.root)
        self.p_man = mock.patch.object(library, "MANIFEST_PATH", self.fx.manifest_path)
        self.p_root.start()
        self.p_man.start()

    def tearDown(self) -> None:
        self.p_root.stop()
        self.p_man.stop()
        self.fx.cleanup()

    def test_sets_inline_image_and_scale_type(self) -> None:
        from sla_lib.builder.primitives import ImageFrame

        # Fresh frame with the dataclass default (scale_type=0 = ScaleAuto;
        # issue 37 Backport 10 flipped the default from 1 → 0 because
        # Scribus 1.6.x renders small white-on-transparent RGBA PNGs
        # invisible when SCALETYPE=1 at high downscale ratios).
        frame = ImageFrame(x_mm=0, y_mm=0, w_mm=87, h_mm=24)
        self.assertEqual(frame.scale_type, 0, "precondition: default is ScaleAuto")
        self.assertIsNone(frame.inline_image_data)

        # Simulate the pre-fix manual setting to exercise the inject path's
        # explicit assignment (the call must still set scale_type=0 even
        # when the caller previously set it to 1).
        frame.scale_type = 1

        img = library.load("themen_topic1")
        assert img is not None
        library.inject_into_frame(frame, img, target_w_mm=87, target_h_mm=24)

        # Inline image installed, scale_type flipped to ScaleAuto so Scribus
        # actually fits the image to the frame.
        self.assertIsNotNone(frame.inline_image_data)
        self.assertEqual(frame.inline_image_ext, "jpg")
        self.assertEqual(
            frame.scale_type, 0,
            "inject_into_frame must set scale_type=0 (ScaleAuto) — without "
            "it the inline image renders at native pixel size and overflows "
            "the frame, the SCALETYPE bug behind the gallery regression",
        )


class ValidateManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = LibraryFixture()
        self.p_root = mock.patch.object(library, "LIBRARY_ROOT", self.fx.root)
        self.p_man = mock.patch.object(library, "MANIFEST_PATH", self.fx.manifest_path)
        self.p_root.start()
        self.p_man.start()

    def tearDown(self) -> None:
        self.p_root.stop()
        self.p_man.stop()
        self.fx.cleanup()

    def test_valid_manifest_returns_empty(self) -> None:
        self.assertEqual(library.validate_manifest(), [])

    def test_missing_required_field_caught(self) -> None:
        # Strip 'prompt' from one entry.
        with open(self.fx.manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        del data["images"]["portrait_alice"]["prompt"]
        with open(self.fx.manifest_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

        errors = library.validate_manifest()
        self.assertTrue(errors)
        self.assertTrue(any("prompt" in e for e in errors), f"errors: {errors}")

    def test_invalid_id_pattern_caught(self) -> None:
        # IDs must match ^[a-z][a-z0-9_]*$. Add an entry with uppercase + dash.
        with open(self.fx.manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data["images"]["BadID-WithDashes"] = {
            "path": "portraits/alice.jpg",
            "prompt": "Long-enough prompt to satisfy schema minLength constraint.",
            "tags": ["portrait"],
            "synthetic": True,
        }
        with open(self.fx.manifest_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

        errors = library.validate_manifest()
        self.assertTrue(errors, "expected schema violation for invalid ID pattern")


class RegenerateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = LibraryFixture()
        self.p_root = mock.patch.object(library, "LIBRARY_ROOT", self.fx.root)
        self.p_man = mock.patch.object(library, "MANIFEST_PATH", self.fx.manifest_path)
        self.p_root.start()
        self.p_man.start()

    def tearDown(self) -> None:
        self.p_root.stop()
        self.p_man.stop()
        self.fx.cleanup()

    def test_regenerate_invokes_generate_image(self) -> None:
        # Force regen by deleting the file first.
        target = self.fx.root / "portraits" / "alice.jpg"
        target.unlink()

        def fake_generate(prompt, output_path, size):
            # Simulate codex producing the output.
            Image.new("RGB", (1024, 1536), (200, 200, 200)).save(
                str(output_path), format="JPEG", quality=80
            )
            return 0

        with mock.patch.object(codex_image_gen, "generate_image", side_effect=fake_generate) as m:
            ok = library.regenerate("portrait_alice", force=True)

        self.assertTrue(ok)
        self.assertEqual(m.call_count, 1)
        kwargs = m.call_args.kwargs
        self.assertIn("prompt", kwargs)
        self.assertIn("output_path", kwargs)
        self.assertEqual(kwargs["output_path"], target.resolve())

    def test_regenerate_unknown_id_raises(self) -> None:
        with self.assertRaises(library.LibraryError):
            library.regenerate("never_existed", force=True)


if __name__ == "__main__":
    unittest.main()

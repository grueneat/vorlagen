"""Unit tests for tools/sla_lib/builder/library.py (issue #13).

Covers:
  - load() raise-vs-optional behavior
  - all_images() iteration
  - find() filters by tags + category
  - crop_for_frame() determinism (byte-identical on reruns)
  - crop_for_frame() watermark-after-crop regression (R-WATERMARK-CROP)
    - portrait source → landscape crop: band visible at the bottom of output
    - landscape source → portrait crop: band visible at the bottom of output
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

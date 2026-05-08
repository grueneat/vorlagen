"""Unit tests for tools/codex_image_gen.py.

Covers the issue #11 extensions:
  - subprocess.run is invoked with stdin=DEVNULL (regression — codex hangs
    indefinitely on captured stdout without it).
  - add_demo_watermark overlays a visible bottom band.
  - recover_codex_output salvages output from the codex cache directory when
    the codex agent saved to its own cache instead of the requested target.
  - parse_manifest tolerates the qr_codes: sibling key.

No real codex calls are made: subprocess.run is monkey-patched at the
module level for any test that touches generate_image / run_codex_for_image.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

# Ensure tools/ is on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

import codex_image_gen  # noqa: E402


def _make_grey_jpg(path: Path, size: tuple[int, int] = (1024, 1536)) -> Path:
    """Create a synthetic mid-grey JPEG at ``path``."""
    Image.new("RGB", size, (180, 180, 180)).save(str(path), format="JPEG", quality=85)
    return path


def _mean_brightness(img: Image.Image) -> float:
    """Return the mean L-channel brightness of a Pillow Image."""
    pixels = list(img.convert("L").getdata())
    return sum(pixels) / len(pixels) if pixels else 0.0


class AddDemoWatermarkTests(unittest.TestCase):
    """add_demo_watermark — visible bottom band; format-aware re-encode."""

    def test_overlays_caption_band_darker_than_middle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            jpg = _make_grey_jpg(Path(td) / "demo.jpg", size=(1024, 1536))
            codex_image_gen.add_demo_watermark(jpg)
            with Image.open(str(jpg)) as out:
                self.assertEqual(out.size, (1024, 1536))
                w, h = out.size
                # Bottom 5% should be measurably darker than middle 50% due to
                # the dark band overlay.
                bottom = out.crop((0, h * 95 // 100, w, h))
                middle = out.crop((0, h * 30 // 100, w, h * 70 // 100))
                self.assertLess(
                    _mean_brightness(bottom),
                    _mean_brightness(middle),
                    "bottom band should be darker than middle (watermark missing?)",
                )

    def test_uses_fallback_font_when_gotham_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            jpg = _make_grey_jpg(Path(td) / "demo.jpg", size=(512, 768))
            with mock.patch.object(
                codex_image_gen, "GOTHAM_BOOK_PATH", Path("/nonexistent/font.otf")
            ):
                # Should not raise even when the brand font is missing.
                codex_image_gen.add_demo_watermark(jpg)
            self.assertTrue(jpg.exists())

    def test_returns_path_for_chaining(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            jpg = _make_grey_jpg(Path(td) / "demo.jpg", size=(400, 600))
            result = codex_image_gen.add_demo_watermark(jpg)
            self.assertEqual(result, jpg)


class ApplyWatermarkToImageTests(unittest.TestCase):
    """_apply_watermark_to_image — pure in-memory variant for library reuse."""

    def test_returns_new_image_with_band(self) -> None:
        # Solid mid-grey source so the band's contribution is unambiguous.
        src = Image.new("RGB", (512, 768), (180, 180, 180))
        out = codex_image_gen._apply_watermark_to_image(src)
        self.assertIsInstance(out, Image.Image)
        self.assertEqual(out.size, src.size)

        # Bottom-center pixel must be much darker than top-center pixel.
        w, h = out.size
        top = out.getpixel((w // 2, 5))
        bottom = out.getpixel((w // 2, h - 5))
        self.assertLess(
            sum(bottom) / 3,
            sum(top) / 3,
            "bottom row should be in the dark watermark band",
        )

    def test_does_not_mutate_input(self) -> None:
        src = Image.new("RGB", (256, 384), (180, 180, 180))
        # Capture a reference pixel from the bottom row before the call.
        before = src.getpixel((128, 380))
        _ = codex_image_gen._apply_watermark_to_image(src)
        # Source pixel must be unchanged.
        self.assertEqual(src.getpixel((128, 380)), before)


class RecoverCodexOutputTests(unittest.TestCase):
    """recover_codex_output — copies newest cache file when target missing."""

    def test_copies_newest_file_when_target_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            search = tdpath / "cache"
            search.mkdir()
            cached = search / "abc-123.png"
            Image.new("RGB", (32, 32), (255, 0, 0)).save(str(cached))
            target = tdpath / "out" / "image.png"
            self.assertFalse(target.exists())

            ok = codex_image_gen.recover_codex_output(
                target,
                search_dir=search,
                started_at=0.0,
            )
            self.assertTrue(ok)
            self.assertTrue(target.exists())

    def test_returns_false_when_target_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            search = tdpath / "cache"
            search.mkdir()
            (search / "newer.png").write_bytes(b"PNGdata")
            target = tdpath / "image.png"
            target.write_bytes(b"existing")

            ok = codex_image_gen.recover_codex_output(
                target,
                search_dir=search,
                started_at=0.0,
            )
            self.assertFalse(ok)
            self.assertEqual(target.read_bytes(), b"existing")

    def test_returns_false_when_no_file_newer_than_started_at(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            search = tdpath / "cache"
            search.mkdir()
            old = search / "old.png"
            old.write_bytes(b"old")
            # Force the file's mtime well into the past.
            past = time.time() - 86400
            import os
            os.utime(str(old), (past, past))

            target = tdpath / "image.png"
            ok = codex_image_gen.recover_codex_output(
                target,
                search_dir=search,
                started_at=time.time() - 60,  # narrow recent window
            )
            self.assertFalse(ok)
            self.assertFalse(target.exists())

    def test_returns_false_when_search_dir_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            target = tdpath / "image.png"
            ok = codex_image_gen.recover_codex_output(
                target,
                search_dir=tdpath / "nonexistent",
                started_at=0.0,
            )
            self.assertFalse(ok)


class ParseManifestQRCodesKeyTests(unittest.TestCase):
    """parse_manifest tolerates the qr_codes: sibling key."""

    def test_qr_codes_sibling_key_is_passed_through(self) -> None:
        import yaml

        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "manifest.yml"
            manifest.write_text(
                yaml.safe_dump(
                    {
                        "slug": "demo",
                        "images": [
                            {
                                "name": "x",
                                "prompt": "p",
                                "output_path": "samples/x.jpg",
                            }
                        ],
                        "qr_codes": [
                            {
                                "name": "q",
                                "target_url": "https://example.org/",
                                "output_path": "samples/q.png",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            data = codex_image_gen.parse_manifest(manifest)
            self.assertEqual(len(data["images"]), 1)
            # Unknown sibling keys are passed through untouched.
            self.assertEqual(len(data["qr_codes"]), 1)
            self.assertEqual(data["qr_codes"][0]["target_url"], "https://example.org/")

    def test_missing_images_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "manifest.yml"
            manifest.write_text("slug: demo\n", encoding="utf-8")
            data = codex_image_gen.parse_manifest(manifest)
            self.assertEqual(data["images"], [])

    def test_invalid_images_value_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "manifest.yml"
            manifest.write_text(
                "slug: demo\nimages: not-a-list\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                codex_image_gen.parse_manifest(manifest)


class SubprocessStdinDevnullTests(unittest.TestCase):
    """Regression: codex blocks on captured stdout without stdin=DEVNULL."""

    def test_generate_image_passes_devnull_stdin(self) -> None:
        captured: dict = {}

        class _FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            captured.update(kwargs)
            return _FakeResult()

        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            target = tdpath / "image.jpg"
            # Pre-populate the target so generate_image's
            # post-condition checks pass without invoking the watermark
            # (we'll mock that too).
            _make_grey_jpg(target, size=(256, 384))

            with mock.patch.object(
                codex_image_gen.subprocess, "run", side_effect=_fake_run
            ), mock.patch.object(
                codex_image_gen, "add_demo_watermark"
            ) as wm_mock:
                rc = codex_image_gen.generate_image(
                    "test prompt", target, size="1024x1536"
                )

            self.assertEqual(rc, 0)
            self.assertIn("stdin", captured)
            self.assertEqual(
                captured["stdin"],
                subprocess.DEVNULL,
                "MUST pass stdin=DEVNULL or codex hangs indefinitely",
            )
            wm_mock.assert_called_once()


class GenerateImageRecoveryAndWatermarkTests(unittest.TestCase):
    """generate_image wires recover_codex_output and add_demo_watermark."""

    def test_recovers_when_codex_saves_to_cache(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            target = tdpath / "out" / "image.jpg"
            cache_dir = tdpath / "cache"
            cache_dir.mkdir()
            cached_png = cache_dir / "uuid.png"

            class _FakeResult:
                returncode = 0
                stdout = ""
                stderr = ""

            def _fake_run_then_drop_image(cmd, **kwargs):
                # Simulate codex: it returns 0 AFTER having saved a PNG to its
                # cache directory (mtime in the future relative to started_at).
                Image.new("RGB", (64, 96), (200, 200, 200)).save(str(cached_png))
                return _FakeResult()

            with mock.patch.object(
                codex_image_gen.subprocess, "run", side_effect=_fake_run_then_drop_image
            ), mock.patch.object(
                codex_image_gen, "DEFAULT_CODEX_GEN_DIR", cache_dir
            ), mock.patch.object(
                codex_image_gen, "add_demo_watermark"
            ) as wm_mock:
                rc = codex_image_gen.generate_image(
                    "prompt", target, size="1024x1536"
                )

            self.assertEqual(rc, 0)
            self.assertTrue(target.exists())
            wm_mock.assert_called_once()

    def test_returns_one_when_codex_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "image.jpg"

            class _FakeResult:
                returncode = 1
                stdout = ""
                stderr = "codex error"

            with mock.patch.object(
                codex_image_gen.subprocess, "run", return_value=_FakeResult()
            ):
                rc = codex_image_gen.generate_image("prompt", target, size=None)
            self.assertEqual(rc, 1)
            self.assertFalse(target.exists())


class ParseLibraryManifestTests(unittest.TestCase):
    """parse_library_manifest — dict-keyed-by-id schema (issue #13)."""

    def _write(self, td: Path, body: str) -> Path:
        m = td / "manifest.yml"
        m.write_text(body, encoding="utf-8")
        return m

    def test_dict_form_parses_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            m = self._write(tdpath, """
images:
  portrait_alice:
    path: portraits/alice.jpg
    prompt: A long-enough demo prompt for alice.
    tags: [portrait]
    synthetic: true
  themen_topic1:
    path: themen/topic1.jpg
    prompt: A long-enough demo prompt for topic1.
    tags: [themen]
    synthetic: true
""")
            data = codex_image_gen.parse_library_manifest(m)
            self.assertEqual(set(data.keys()), {"portrait_alice", "themen_topic1"})
            self.assertEqual(data["portrait_alice"]["path"], "portraits/alice.jpg")

    def test_missing_images_key_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            m = self._write(Path(td), "slug: demo\n")
            with self.assertRaises(ValueError):
                codex_image_gen.parse_library_manifest(m)

    def test_list_images_raises(self) -> None:
        # Per-template manifests use list — library mode rejects.
        with tempfile.TemporaryDirectory() as td:
            m = self._write(Path(td), """
images:
  - id: foo
    prompt: bar
""")
            with self.assertRaises(ValueError):
                codex_image_gen.parse_library_manifest(m)

    def test_missing_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                codex_image_gen.parse_library_manifest(Path(td) / "nope.yml")


class RegenLibraryTests(unittest.TestCase):
    """regen_library — iterates entries, dispatches to generate_image."""

    def _scaffold(self, td: Path) -> Path:
        """Create a tiny library manifest with two entries; no JPGs yet."""
        m = td / "manifest.yml"
        m.write_text(
            """
images:
  portrait_alice:
    path: portraits/alice.jpg
    prompt: A long-enough demo prompt for alice (>=20 chars).
    tags: [portrait]
    synthetic: true
    size: "1024x1536"
  themen_topic1:
    path: themen/topic1.jpg
    prompt: A long-enough demo prompt for topic1 (>=20 chars).
    tags: [themen]
    synthetic: true
    size: "1536x1024"
""",
            encoding="utf-8",
        )
        return m

    def test_regen_all_calls_generate_image_per_entry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            m = self._scaffold(Path(td))
            calls = []

            def fake_gen(prompt, output_path, size):
                calls.append((output_path.name, size))
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (64, 64), (180, 180, 180)).save(
                    str(output_path), format="JPEG", quality=80
                )
                return 0

            with mock.patch.object(codex_image_gen, "generate_image", side_effect=fake_gen), \
                    mock.patch.object(codex_image_gen, "codex_login_status", return_value="ok"):
                rc = codex_image_gen.regen_library(m, force=True)
            self.assertEqual(rc, 0)
            self.assertEqual(len(calls), 2)
            names = sorted(c[0] for c in calls)
            self.assertEqual(names, ["alice.jpg", "topic1.jpg"])

    def test_single_id_filters_to_one_entry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            m = self._scaffold(Path(td))

            def fake_gen(prompt, output_path, size):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (64, 64), (180, 180, 180)).save(
                    str(output_path), format="JPEG", quality=80
                )
                return 0

            with mock.patch.object(codex_image_gen, "generate_image", side_effect=fake_gen) as gm, \
                    mock.patch.object(codex_image_gen, "codex_login_status", return_value="ok"):
                rc = codex_image_gen.regen_library(m, ids=["themen_topic1"], force=True)
            self.assertEqual(rc, 0)
            self.assertEqual(gm.call_count, 1)

    def test_unknown_id_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            m = self._scaffold(Path(td))
            with mock.patch.object(codex_image_gen, "codex_login_status", return_value="ok"):
                rc = codex_image_gen.regen_library(m, ids=["never_existed"], force=True)
            self.assertEqual(rc, 1)

    def test_force_bypasses_skip(self) -> None:
        # Pre-populate the output so the mtime check would otherwise skip.
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            m = self._scaffold(tdpath)
            (tdpath / "portraits").mkdir()
            (tdpath / "themen").mkdir()
            Image.new("RGB", (64, 64), (180, 180, 180)).save(
                str(tdpath / "portraits" / "alice.jpg"), format="JPEG"
            )
            Image.new("RGB", (64, 64), (180, 180, 180)).save(
                str(tdpath / "themen" / "topic1.jpg"), format="JPEG"
            )
            # bump mtime so they look fresh
            now = time.time()
            import os
            os.utime(tdpath / "portraits" / "alice.jpg", (now + 60, now + 60))
            os.utime(tdpath / "themen" / "topic1.jpg", (now + 60, now + 60))

            def fake_gen(prompt, output_path, size):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (64, 64), (200, 100, 100)).save(
                    str(output_path), format="JPEG", quality=80
                )
                return 0

            # Without --force: skips both.
            with mock.patch.object(codex_image_gen, "generate_image", side_effect=fake_gen) as gm, \
                    mock.patch.object(codex_image_gen, "codex_login_status", return_value="ok"):
                rc = codex_image_gen.regen_library(m, force=False)
            self.assertEqual(rc, 0)
            self.assertEqual(gm.call_count, 0)

            # With --force: generates both.
            with mock.patch.object(codex_image_gen, "generate_image", side_effect=fake_gen) as gm, \
                    mock.patch.object(codex_image_gen, "codex_login_status", return_value="ok"):
                rc = codex_image_gen.regen_library(m, force=True)
            self.assertEqual(rc, 0)
            self.assertEqual(gm.call_count, 2)

    def test_dry_run_does_not_call_codex(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            m = self._scaffold(Path(td))
            with mock.patch.object(codex_image_gen, "generate_image") as gm:
                rc = codex_image_gen.regen_library(m, force=True, dry_run=True)
            self.assertEqual(rc, 0)
            gm.assert_not_called()


if __name__ == "__main__":
    unittest.main()

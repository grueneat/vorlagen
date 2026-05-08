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


if __name__ == "__main__":
    unittest.main()

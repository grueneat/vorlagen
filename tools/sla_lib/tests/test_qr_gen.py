"""Unit tests for tools/qr_gen.py.

All tests use ``tmp_path`` (or ``tempfile``) for isolation. Pin assumption:
qrcode==8.2 + Pillow>=12.2 (pinned in Dockerfile.claude). Documented at the
top of tools/qr_gen.py.
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from pyzbar.pyzbar import decode

# Ensure tools/ is on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

import qr_gen  # noqa: E402

# URL/version table from PLAN.md — every URL we ship demo QRs for.
URL_TABLE = [
    "https://noe.gruene.at/",
    "https://noe.gruene.at/themen/",
    "https://noe.gruene.at/mitmachen/",
    "https://noe.gruene.at/termine/",
]


def _build_synthetic_logo(path: Path, *, side: int = 96) -> Path:
    """Create a small green-circle PNG suitable for embed-test."""
    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse(
        (4, 4, side - 4, side - 4),
        fill=(28, 72, 33, 255),
    )
    img.save(str(path), format="PNG", optimize=True)
    return path


def _decode_url(path: Path) -> str | None:
    """Return the decoded URL from a QR PNG, or None if no decode."""
    decoded = decode(Image.open(str(path)))
    if not decoded:
        return None
    return decoded[0].data.decode("utf-8")


class GenerateQRDecodesTests(unittest.TestCase):
    """test_generate_qr_decodes_with_pyzbar — all URLs round-trip via pyzbar."""

    def test_all_table_urls_decode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            for i, url in enumerate(URL_TABLE):
                out = tdpath / f"qr-{i}.png"
                qr_gen.generate_qr_png(url, out)
                self.assertTrue(out.exists(), f"missing {out}")
                self.assertEqual(_decode_url(out), url, f"decode mismatch for {url}")


class ByteDeterminismTests(unittest.TestCase):
    """test_qr_byte_determinism — two runs with identical inputs produce same bytes."""

    def test_two_runs_identical_bytes(self) -> None:
        url = "https://noe.gruene.at/mitmachen/"
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "a.png"
            p2 = Path(td) / "b.png"
            qr_gen.generate_qr_png(url, p1)
            qr_gen.generate_qr_png(url, p2)
            h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
            self.assertEqual(h1, h2, "qrcode 8.2 + Pillow 12.2 must be byte-stable")

    def test_logo_embed_byte_determinism(self) -> None:
        url = "https://noe.gruene.at/"
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            logo = _build_synthetic_logo(tdpath / "logo.png")
            p1 = tdpath / "a.png"
            p2 = tdpath / "b.png"
            qr_gen.generate_qr_png(url, p1, embed_logo=logo)
            qr_gen.generate_qr_png(url, p2, embed_logo=logo)
            h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
            h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
            self.assertEqual(h1, h2, "logo-embedded QR must also be byte-stable")


class LogoEmbedScannableTests(unittest.TestCase):
    """test_qr_logo_embed_still_decodes — center logo at ECC=H scans cleanly."""

    def test_logo_does_not_break_decode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            logo = _build_synthetic_logo(tdpath / "logo.png")
            for i, url in enumerate(URL_TABLE):
                out = tdpath / f"qr-{i}.png"
                qr_gen.generate_qr_png(url, out, embed_logo=logo, error_correction="H")
                self.assertEqual(
                    _decode_url(out),
                    url,
                    f"ECC=H must absorb center-logo occlusion for {url}",
                )


class ParseManifestTests(unittest.TestCase):
    """test_parse_manifest_permissive — missing keys don't raise."""

    def _write(self, path: Path, content: str) -> Path:
        path.write_text(content, encoding="utf-8")
        return path

    def test_minimal_manifest_with_only_slug(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mp = self._write(Path(td) / "manifest.yml", "slug: demo\n")
            data = qr_gen.parse_manifest(mp)
            self.assertEqual(data["slug"], "demo")
            self.assertEqual(data["qr_codes"], [])
            self.assertEqual(data["images"], [])

    def test_manifest_without_qr_codes_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mp = self._write(
                Path(td) / "manifest.yml",
                "slug: demo\nimages:\n  - name: x\n    output_path: x.jpg\n",
            )
            data = qr_gen.parse_manifest(mp)
            self.assertEqual(data["qr_codes"], [])
            self.assertEqual(len(data["images"]), 1)

    def test_manifest_without_images_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mp = self._write(
                Path(td) / "manifest.yml",
                (
                    "slug: demo\n"
                    "qr_codes:\n"
                    "  - name: q\n"
                    "    target_url: https://example.org/\n"
                    "    output_path: samples/q.png\n"
                ),
            )
            data = qr_gen.parse_manifest(mp)
            self.assertEqual(data["images"], [])
            self.assertEqual(len(data["qr_codes"]), 1)

    def test_non_dict_qr_codes_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mp = self._write(
                Path(td) / "manifest.yml",
                "slug: demo\nqr_codes: not-a-list\n",
            )
            with self.assertRaises(ValueError):
                qr_gen.parse_manifest(mp)


class CLIMainTests(unittest.TestCase):
    """test_cli_main_reads_manifest_and_writes_files."""

    def test_main_writes_qr_files_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            samples = tdpath / "samples"
            samples.mkdir()
            (samples / "manifest.yml").write_text(
                (
                    "slug: demo\n"
                    "qr_codes:\n"
                    "  - name: qr-1\n"
                    "    target_url: https://noe.gruene.at/\n"
                    "    output_path: samples/qr-1.png\n"
                    "    box_size: 6\n"
                    "    border: 4\n"
                ),
                encoding="utf-8",
            )
            rc = qr_gen.main([str(tdpath)])
            self.assertEqual(rc, 0)
            out = samples / "qr-1.png"
            self.assertTrue(out.exists())
            self.assertEqual(_decode_url(out), "https://noe.gruene.at/")

    def test_main_with_empty_qr_codes_is_noop_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdpath = Path(td)
            samples = tdpath / "samples"
            samples.mkdir()
            (samples / "manifest.yml").write_text(
                "slug: demo\nimages: []\n",
                encoding="utf-8",
            )
            rc = qr_gen.main([str(tdpath)])
            self.assertEqual(rc, 0)

    def test_main_invalid_path_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            rc = qr_gen.main([str(Path(td) / "does-not-exist")])
            self.assertEqual(rc, 1)


class CircularMaskTests(unittest.TestCase):
    """circular_mask zeroes alpha outside the inscribed circle."""

    def test_corners_become_transparent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.png"
            dst = Path(td) / "out.png"
            # Solid red square 100x100, fully opaque.
            Image.new("RGBA", (100, 100), (255, 0, 0, 255)).save(str(src))
            qr_gen.circular_mask(src, dst)
            out = Image.open(str(dst)).convert("RGBA")
            self.assertEqual(out.size, (100, 100))
            # Corner pixel is outside the inscribed circle -> alpha 0.
            self.assertEqual(out.getpixel((0, 0))[3], 0)
            # Center pixel is inside the circle -> opaque.
            self.assertGreater(out.getpixel((50, 50))[3], 200)


if __name__ == "__main__":
    unittest.main()

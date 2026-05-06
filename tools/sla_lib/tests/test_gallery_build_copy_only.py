"""Unit tests for tools/gallery_build.py (copy-only refactor, issue #4).

All tests use synthetic template directories built in temporary directories
and redirect SITE_PUBLIC via unittest.mock. No subprocess calls; no rendering.
"""
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import yaml

# Ensure tools/ is on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

import gallery_build  # noqa: E402
from gallery_build import process_template, _fail_missing  # noqa: E402


def _write_meta(tdir: Path, meta: dict) -> None:
    (tdir / "meta.yml").write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _make_non_family_template(tdir: Path, *, page_count: int = 2) -> None:
    """Create a complete non-family template fixture."""
    _write_meta(tdir, {
        "id": tdir.name,
        "version": "0.1.0",
        "title": "Test Postcard",
        "original_sla": "../../some-original.sla",
    })
    (tdir / "template.sla").write_bytes(b"<SLA/>")
    (tdir / "preview.pdf").write_bytes(b"%PDF-1.4")
    for i in range(1, page_count + 1):
        (tdir / f"page-0{i}.png").write_bytes(b"PNG")


def _make_family_template(tdir: Path, *, codes: list = None, page_count: int = 1) -> None:
    """Create a complete family template fixture."""
    if codes is None:
        codes = ["a0"]
    sizes = [{"code": c, "format": c.upper(), "mm": [100, 200]} for c in codes]
    _write_meta(tdir, {
        "id": tdir.name,
        "type": "family",
        "original_sla": "../../some-original.sla",
        "sizes": sizes,
    })
    (tdir / "template.sla").write_bytes(b"<SLA/>")
    for code in codes:
        (tdir / f"{code}.sla").write_bytes(b"<SLA/>")
        (tdir / f"{code}.pdf").write_bytes(b"%PDF-1.4")
        for i in range(1, page_count + 1):
            (tdir / f"{code}-page-0{i}.png").write_bytes(b"PNG")


class NonFamilySuccessTests(unittest.TestCase):
    """Tests for the non-family copy-only branch (success paths)."""

    def test_non_family_success_returns_meta_with_previews(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "postkarte-test"
            tdir.mkdir()
            site_public = Path(td) / "public"
            _make_non_family_template(tdir, page_count=2)
            with unittest.mock.patch.object(gallery_build, "SITE_PUBLIC", site_public):
                result = process_template(tdir)
            self.assertIsNotNone(result)
            self.assertEqual(len(result["_previews"]), 2)
            self.assertIn("Seite 1", result["_previews"][0]["label"])
            self.assertIn("Seite 2", result["_previews"][1]["label"])

    def test_non_family_copies_artifacts_to_site_public(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "postcard"
            tdir.mkdir()
            site_public = Path(td) / "public"
            _make_non_family_template(tdir, page_count=2)
            with unittest.mock.patch.object(gallery_build, "SITE_PUBLIC", site_public):
                process_template(tdir)
            pub_dir = site_public / "postcard"
            self.assertTrue((pub_dir / "template.sla").exists())
            self.assertTrue((pub_dir / "preview.pdf").exists())
            self.assertTrue((pub_dir / "page-01.png").exists())
            self.assertTrue((pub_dir / "page-02.png").exists())

    def test_skip_no_meta_yml(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "empty-dir"
            tdir.mkdir()
            result = process_template(tdir)
            self.assertIsNone(result)


class NonFamilyFailureTests(unittest.TestCase):
    """Tests for the non-family copy-only branch (failure paths)."""

    def test_missing_pdf_raises_system_exit(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "missing-pdf"
            tdir.mkdir()
            site_public = Path(td) / "public"
            _make_non_family_template(tdir)
            (tdir / "preview.pdf").unlink()  # Remove the PDF.
            with unittest.mock.patch.object(gallery_build, "SITE_PUBLIC", site_public):
                with self.assertRaises(SystemExit) as ctx:
                    process_template(tdir)
            self.assertIn("FATAL", str(ctx.exception))

    def test_missing_pngs_raises_system_exit(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "missing-pngs"
            tdir.mkdir()
            site_public = Path(td) / "public"
            _make_non_family_template(tdir)
            for png in tdir.glob("page-*.png"):
                png.unlink()
            with unittest.mock.patch.object(gallery_build, "SITE_PUBLIC", site_public):
                with self.assertRaises(SystemExit):
                    process_template(tdir)

    def test_fail_missing_message_contains_run_render_gallery(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "fail-test"
            tdir.mkdir()
            site_public = Path(td) / "public"
            _make_non_family_template(tdir)
            (tdir / "preview.pdf").unlink()
            with unittest.mock.patch.object(gallery_build, "SITE_PUBLIC", site_public):
                with self.assertRaises(SystemExit) as ctx:
                    process_template(tdir)
            self.assertIn("bin/render-gallery", str(ctx.exception))


class FamilySuccessTests(unittest.TestCase):
    """Tests for the family copy-only branch (success paths)."""

    def test_family_success_returns_meta_with_downloads_and_previews(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "plakat-test"
            tdir.mkdir()
            site_public = Path(td) / "public"
            _make_family_template(tdir, codes=["a0"])
            with unittest.mock.patch.object(gallery_build, "SITE_PUBLIC", site_public):
                result = process_template(tdir)
            self.assertIsNotNone(result)
            self.assertEqual(len(result["_downloads"]), 1)
            self.assertEqual(len(result["_previews"]), 1)
            self.assertEqual(result["_previews"][0]["label"], "A0")

    def test_family_copies_all_size_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "plakat-multi"
            tdir.mkdir()
            site_public = Path(td) / "public"
            _make_family_template(tdir, codes=["a0", "a1"])
            with unittest.mock.patch.object(gallery_build, "SITE_PUBLIC", site_public):
                process_template(tdir)
            pub_dir = site_public / "plakat-multi"
            for code in ["a0", "a1"]:
                self.assertTrue((pub_dir / f"{code}.sla").exists())
                self.assertTrue((pub_dir / f"{code}.pdf").exists())
                self.assertTrue((pub_dir / f"{code}-page-01.png").exists())


class FamilyFailureTests(unittest.TestCase):
    """Tests for the family copy-only branch (failure paths)."""

    def test_family_missing_pdf_raises_system_exit(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "plakat-fail"
            tdir.mkdir()
            site_public = Path(td) / "public"
            _make_family_template(tdir, codes=["a0"])
            (tdir / "a0.pdf").unlink()
            with unittest.mock.patch.object(gallery_build, "SITE_PUBLIC", site_public):
                with self.assertRaises(SystemExit) as ctx:
                    process_template(tdir)
            self.assertIn("FATAL", str(ctx.exception))


class NoCopyOfRenderFunctionsTests(unittest.TestCase):
    """Structural tests confirming render functions are absent."""

    def test_no_render_pdf_attribute(self):
        self.assertFalse(hasattr(gallery_build, "render_pdf"))

    def test_no_pdf_to_pngs_attribute(self):
        self.assertFalse(hasattr(gallery_build, "pdf_to_pngs"))

    def test_no_subprocess_import(self):
        import subprocess
        # gallery_build should NOT have imported subprocess.
        self.assertFalse(
            hasattr(gallery_build, "subprocess"),
            "gallery_build must not import subprocess (rendering removed)",
        )


if __name__ == "__main__":
    unittest.main()

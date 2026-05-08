"""Unit tests for tools/render_pipeline.py helper functions.

All tests are Scribus-free: they operate on hand-crafted byte strings and
synthetic YAML fixtures. No subprocess calls to xvfb-run or Scribus.
"""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure tools/ is on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from render_pipeline import (  # noqa: E402
    EPOCH_DATE,
    FIXED_PDF_ID,
    _scrub_pdf_metadata,
    _select_render_source,
    _sha256_of,
    _update_meta_hash,
    _zero_pad_pngs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf_bytes(ts: bytes, idhex: bytes) -> bytes:
    """Build a minimal synthetic PDF byte string with variable metadata."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Creator (Test)\n"
        b"/CreationDate (D:" + ts + b"Z)\n"
        b"/ModDate (D:" + ts + b"Z)\n"
        b">>\n"
        b"endobj\n"
        b"xref\n"
        b"trailer\n"
        b"<< /Root 1 0 R\n"
        b"/ID [<" + idhex + b"><" + idhex + b">]\n"
        b">>\n"
        b"%%EOF\n"
    )


TS_A = b"20260506120000"  # 14 bytes
TS_B = b"20260506120003"
ID_A = b"aabbccddeeff00112233445566778899"
ID_B = b"99887766554433221100ffeeddccbbaa"


class ScrubPdfMetadataTests(unittest.TestCase):
    """Tests for _scrub_pdf_metadata()."""

    def _write_pdf(self, path: Path, ts: bytes, idhex: bytes) -> None:
        path.write_bytes(_make_pdf_bytes(ts, idhex))

    def test_scrub_replaces_creation_and_mod_date(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.pdf"
            self._write_pdf(p, TS_A, ID_A)
            _scrub_pdf_metadata(p)
            data = p.read_bytes()
            # Original timestamp must be gone.
            self.assertNotIn(b"D:" + TS_A + b"Z", data)
            # Fixed epoch date must be present twice (CreationDate + ModDate).
            self.assertEqual(data.count(EPOCH_DATE), 2)

    def test_scrub_replaces_trailer_id(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.pdf"
            self._write_pdf(p, TS_A, ID_A)
            _scrub_pdf_metadata(p)
            data = p.read_bytes()
            # Original ID must be gone.
            self.assertNotIn(ID_A, data)
            # Fixed ID must appear twice in the /ID array.
            self.assertIn(b"/ID [<" + FIXED_PDF_ID + b"><" + FIXED_PDF_ID + b">]", data)

    def test_scrub_is_idempotent(self):
        """Running scrub twice must produce the same bytes as running once."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.pdf"
            self._write_pdf(p, TS_A, ID_A)
            _scrub_pdf_metadata(p)
            h1 = hashlib.sha256(p.read_bytes()).hexdigest()
            _scrub_pdf_metadata(p)
            h2 = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(h1, h2)

    def test_scrub_normalises_two_different_renders(self):
        """Two renders (TS_A, ID_A) and (TS_B, ID_B) must match after scrub."""
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "r1.pdf"
            p2 = Path(td) / "r2.pdf"
            self._write_pdf(p1, TS_A, ID_A)
            self._write_pdf(p2, TS_B, ID_B)
            _scrub_pdf_metadata(p1)
            _scrub_pdf_metadata(p2)
            self.assertEqual(p1.read_bytes(), p2.read_bytes())

    def test_scrub_is_length_preserving(self):
        """File size must not change after scrub (xref offsets depend on this)."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.pdf"
            self._write_pdf(p, TS_A, ID_A)
            before = len(p.read_bytes())
            _scrub_pdf_metadata(p)
            after = len(p.read_bytes())
            self.assertEqual(before, after)


class UpdateMetaHashTests(unittest.TestCase):
    """Tests for _update_meta_hash()."""

    _HASH_A = "a" * 64
    _HASH_B = "b" * 64
    _HASH_C = "c" * 64
    _HASH_D = "d" * 64

    def _base_meta(self, has_field: bool = False, family: bool = False) -> str:
        lines = [
            "id: test-template",
            "version: 0.1.0",
            "title: Test Template",
            "original_sla: ../../some-original.sla",
        ]
        if has_field:
            if family:
                lines += [
                    "previews_for_sla:",
                    f"  a0: {self._HASH_A}",
                    f"  a1: {self._HASH_B}",
                ]
            else:
                lines.append(f"previews_for_sla: {self._HASH_A}")
        lines += [
            "ci_overrides:",
            "  non_ci_styles:",
            "    - Default Paragraph Style",
        ]
        return "\n".join(lines) + "\n"

    def test_inserts_below_original_sla_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "meta.yml"
            p.write_text(self._base_meta(has_field=False), encoding="utf-8")
            _update_meta_hash(p, self._HASH_B)
            text = p.read_text(encoding="utf-8")
            # Field must be present.
            self.assertIn(f"previews_for_sla: {self._HASH_B}", text)
            # Must appear directly after original_sla: line.
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if line.startswith("original_sla:"):
                    self.assertIn("previews_for_sla:", lines[i + 1])
                    break

    def test_replaces_existing_str_value(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "meta.yml"
            p.write_text(self._base_meta(has_field=True), encoding="utf-8")
            _update_meta_hash(p, self._HASH_B)
            text = p.read_text(encoding="utf-8")
            self.assertIn(f"previews_for_sla: {self._HASH_B}", text)
            # Old hash must be gone.
            self.assertNotIn(f"previews_for_sla: {self._HASH_A}", text)

    def test_writes_dict_for_family(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "meta.yml"
            p.write_text(self._base_meta(has_field=False), encoding="utf-8")
            hashes = {"a0": self._HASH_A, "a1": self._HASH_B}
            _update_meta_hash(p, hashes)
            text = p.read_text(encoding="utf-8")
            self.assertIn("previews_for_sla:", text)
            self.assertIn(f"  a0: {self._HASH_A}", text)
            self.assertIn(f"  a1: {self._HASH_B}", text)

    def test_replaces_existing_dict_with_new_dict(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "meta.yml"
            p.write_text(self._base_meta(has_field=True, family=True), encoding="utf-8")
            new_hashes = {"a0": self._HASH_C, "a1": self._HASH_D}
            _update_meta_hash(p, new_hashes)
            text = p.read_text(encoding="utf-8")
            self.assertIn(f"  a0: {self._HASH_C}", text)
            self.assertIn(f"  a1: {self._HASH_D}", text)
            self.assertNotIn(self._HASH_A, text)
            self.assertNotIn(self._HASH_B, text)

    def test_does_not_disturb_unrelated_lines(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "meta.yml"
            original = self._base_meta(has_field=False)
            p.write_text(original, encoding="utf-8")
            _update_meta_hash(p, self._HASH_B)
            text = p.read_text(encoding="utf-8")
            # All original top-level keys must survive (except previews_for_sla).
            for key_prefix in ("id:", "version:", "title:", "original_sla:", "ci_overrides:"):
                self.assertIn(key_prefix, text, f"key '{key_prefix}' missing after hash update")

    def test_idempotent_string_update(self):
        """Writing the same hash twice must not change the file content."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "meta.yml"
            p.write_text(self._base_meta(has_field=False), encoding="utf-8")
            _update_meta_hash(p, self._HASH_A)
            h1 = hashlib.sha256(p.read_bytes()).hexdigest()
            _update_meta_hash(p, self._HASH_A)
            h2 = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(h1, h2)


class Sha256OfTests(unittest.TestCase):
    """Tests for _sha256_of()."""

    def test_known_hash(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.txt"
            p.write_bytes(b"hello\n")
            result = _sha256_of(p)
            self.assertEqual(
                result,
                "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
            )

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "empty.txt"
            p.write_bytes(b"")
            result = _sha256_of(p)
            self.assertEqual(
                result,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            )


class ZeroPadPngsTests(unittest.TestCase):
    """Tests for _zero_pad_pngs()."""

    def test_renames_single_digit_files(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            for n in range(1, 10):
                (tdir / f"page-{n}.png").write_bytes(b"PNG")
            _zero_pad_pngs(tdir, "page")
            names = {p.name for p in tdir.iterdir()}
            for n in range(1, 10):
                self.assertIn(f"page-0{n}.png", names)
                self.assertNotIn(f"page-{n}.png", names)

    def test_skips_already_padded_files(self):
        """Files like page-01.png must not be double-padded."""
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            (tdir / "page-01.png").write_bytes(b"PNG")
            (tdir / "page-10.png").write_bytes(b"PNG")
            _zero_pad_pngs(tdir, "page")
            names = {p.name for p in tdir.iterdir()}
            # page-01.png stays page-01.png (not page-001.png).
            self.assertIn("page-01.png", names)
            # page-10.png has 2 digits, no single-digit glob match.
            self.assertIn("page-10.png", names)

    def test_noop_on_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            _zero_pad_pngs(tdir, "page")  # must not raise
            self.assertEqual(list(tdir.iterdir()), [])


class SelectRenderSourceTests(unittest.TestCase):
    """Issue #13 / D3: render source picks template-preview.sla when present."""

    def test_prefers_preview_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            (tdir / "template.sla").write_text("clean", encoding="utf-8")
            (tdir / "template-preview.sla").write_text("preview", encoding="utf-8")
            self.assertEqual(
                _select_render_source(tdir),
                tdir / "template-preview.sla",
            )

    def test_falls_back_to_template_when_no_preview(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            (tdir / "template.sla").write_text("clean", encoding="utf-8")
            self.assertEqual(
                _select_render_source(tdir),
                tdir / "template.sla",
            )


if __name__ == "__main__":
    unittest.main()

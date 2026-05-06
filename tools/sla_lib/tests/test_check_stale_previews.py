"""Unit tests for tools/check_stale_previews.py.

All tests use synthetic template directories built in temporary directories.
No subprocess calls; drives _check_template directly.
"""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

# Ensure tools/ is on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from check_stale_previews import _check_template, _sha256_of  # noqa: E402


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class TemplateFixtureHelper:
    """Mixin providing synthetic template fixture builders."""

    def _make_non_family(
        self,
        tdir: Path,
        *,
        has_original_sla: bool = True,
        previews_for_sla: str | None = "_auto",
        sla_content: bytes = b"sla content",
    ) -> Path:
        """Build a synthetic non-family template directory."""
        sla = tdir / "template.sla"
        sla.write_bytes(sla_content)
        hash_val = _sha256(sla_content)

        meta = {
            "id": tdir.name,
            "version": "0.1.0",
            "title": "Test Template",
        }
        if has_original_sla:
            meta["original_sla"] = "../../some-original.sla"
        if previews_for_sla == "_auto":
            meta["previews_for_sla"] = hash_val
        elif previews_for_sla is not None:
            meta["previews_for_sla"] = previews_for_sla
        # If previews_for_sla is None, field is absent.

        (tdir / "meta.yml").write_text(
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return sla

    def _make_family(
        self,
        tdir: Path,
        *,
        codes: list[str] = None,
        previews_for_sla: dict | None = "_auto",
        sla_contents: dict | None = None,
    ) -> dict[str, Path]:
        """Build a synthetic family template directory."""
        if codes is None:
            codes = ["a0", "a1"]
        if sla_contents is None:
            sla_contents = {c: f"sla content {c}".encode() for c in codes}

        slas = {}
        hashes = {}
        for code in codes:
            sla = tdir / f"{code}.sla"
            content = sla_contents.get(code, f"sla content {code}".encode())
            sla.write_bytes(content)
            slas[code] = sla
            hashes[code] = _sha256(content)

        meta = {
            "id": tdir.name,
            "type": "family",
            "original_sla": "../../some-original.sla",
            "sizes": [{"code": c, "format": c.upper(), "mm": [100, 200]} for c in codes],
        }
        if previews_for_sla == "_auto":
            meta["previews_for_sla"] = hashes
        elif previews_for_sla is not None:
            meta["previews_for_sla"] = previews_for_sla
        # If previews_for_sla is None, field is absent.

        (tdir / "meta.yml").write_text(
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return slas


class CleanNonFamilyTests(TemplateFixtureHelper, unittest.TestCase):
    """Clean (non-stale) non-family template checks."""

    def test_clean_non_family_returns_empty_errors(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "test-template"
            tdir.mkdir()
            self._make_non_family(tdir)
            errors = _check_template(tdir)
            self.assertEqual(errors, [])

    def test_skip_no_original_sla(self):
        """Templates without original_sla (e.g. smoke) must be skipped."""
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "smoke-template"
            tdir.mkdir()
            self._make_non_family(tdir, has_original_sla=False)
            errors = _check_template(tdir)
            self.assertEqual(errors, [])

    def test_skip_no_meta_yml(self):
        """Directory without meta.yml must return empty errors."""
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "empty-dir"
            tdir.mkdir()
            errors = _check_template(tdir)
            self.assertEqual(errors, [])


class StaleNonFamilyTests(TemplateFixtureHelper, unittest.TestCase):
    """Stale non-family template checks."""

    def test_stale_non_family_wrong_hash(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "stale-template"
            tdir.mkdir()
            self._make_non_family(tdir, previews_for_sla="a" * 64)  # wrong hash
            errors = _check_template(tdir)
            self.assertEqual(len(errors), 1)
            self.assertIn("template.sla hash mismatch", errors[0])
            self.assertIn("bin/render-gallery", errors[0])

    def test_missing_previews_for_sla_field(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "missing-field-template"
            tdir.mkdir()
            self._make_non_family(tdir, previews_for_sla=None)  # no field
            errors = _check_template(tdir)
            self.assertEqual(len(errors), 1)
            self.assertIn("previews_for_sla missing", errors[0])
            self.assertIn("bin/render-gallery", errors[0])

    def test_error_message_contains_template_id(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "my-template-id"
            tdir.mkdir()
            self._make_non_family(tdir, previews_for_sla=None)
            errors = _check_template(tdir)
            self.assertTrue(any("my-template-id" in e for e in errors))


class CleanFamilyTests(TemplateFixtureHelper, unittest.TestCase):
    """Clean (non-stale) family template checks."""

    def test_clean_family_returns_empty_errors(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "plakat-test"
            tdir.mkdir()
            self._make_family(tdir, codes=["a0", "a1"])
            errors = _check_template(tdir)
            self.assertEqual(errors, [])


class StaleFamilyTests(TemplateFixtureHelper, unittest.TestCase):
    """Stale family template checks."""

    def test_stale_family_one_size(self):
        """Mutating one size SLA must produce an error for that size only."""
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "plakat-stale"
            tdir.mkdir()
            slas = self._make_family(tdir, codes=["a0", "a1"])
            # Mutate a1 after hash was recorded.
            slas["a1"].write_bytes(b"different content")
            errors = _check_template(tdir)
            self.assertEqual(len(errors), 1)
            self.assertIn("a1", errors[0])
            self.assertIn("SLA hash mismatch", errors[0])
            self.assertIn("bin/render-gallery", errors[0])

    def test_missing_field_family(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "plakat-no-field"
            tdir.mkdir()
            self._make_family(tdir, codes=["a0", "a1"], previews_for_sla=None)
            errors = _check_template(tdir)
            self.assertEqual(len(errors), 1)
            self.assertIn("previews_for_sla missing", errors[0])

    def test_all_sizes_stale_produces_one_error_per_size(self):
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td) / "plakat-all-stale"
            tdir.mkdir()
            slas = self._make_family(tdir, codes=["a0", "a1"])
            slas["a0"].write_bytes(b"changed a0")
            slas["a1"].write_bytes(b"changed a1")
            errors = _check_template(tdir)
            self.assertEqual(len(errors), 2)
            codes_in_errors = [e for e in errors if "a0" in e or "a1" in e]
            self.assertEqual(len(codes_in_errors), 2)


class Sha256OfTests(unittest.TestCase):
    """Tests for _sha256_of()."""

    def test_known_hash(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.txt"
            p.write_bytes(b"hello\n")
            self.assertEqual(
                _sha256_of(p),
                "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
            )


if __name__ == "__main__":
    unittest.main()

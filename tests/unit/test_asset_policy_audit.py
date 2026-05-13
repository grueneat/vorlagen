"""Unit tests for tools/asset_policy_audit.py (issue #39 Phase B)."""
from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import asset_policy_audit as apa  # noqa: E402


_SLUG = "demo-template"


def _write_meta(tmp: Path, slug: str, asset_policy: dict | None) -> None:
    """Write a minimal templates/<slug>/meta.yml with optional asset_policy."""
    tdir = tmp / "templates" / slug
    tdir.mkdir(parents=True, exist_ok=True)
    body: dict = {
        "id": slug,
        "title": "demo",
        "version": "0.1.0",
    }
    if asset_policy is not None:
        body["asset_policy"] = asset_policy
    (tdir / "meta.yml").write_text(
        yaml.safe_dump(body, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_assets(tmp: Path, slug: str, files: list[str]) -> None:
    """Create shared/assets/<slug>/ with the given basenames as dummy files."""
    adir = tmp / "shared" / "assets" / slug
    adir.mkdir(parents=True, exist_ok=True)
    for name in files:
        (adir / name).write_bytes(b"X")


def _link_schema(tmp: Path) -> None:
    """Make the real repo's schema reachable through tmp/shared/.

    ``load_asset_policy`` reads the schema via a hard-coded
    ``Path(__file__).resolve().parents[3] / shared / asset-policy.schema.yaml``
    chain, which resolves to the real repo regardless of ``root``. We do not
    need to copy or symlink anything — the loader picks up the real schema.
    Kept as a no-op helper so the tests document the dependency explicitly.
    """
    # Intentionally a no-op: load_asset_policy uses Path(__file__)... not root.
    return None


class AssetPolicyAuditTests(unittest.TestCase):
    """Audit cases: happy path, skip, missing, shipped-non-empty, unclassified,
    stale, plus the links_export.yml non-asset case."""

    def _tmp_root(self) -> Path:
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="apa-test-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        _link_schema(tmp)
        return tmp

    # --- 1. Happy path -----------------------------------------------------
    def test_happy_path_returns_ok(self) -> None:
        tmp = self._tmp_root()
        _write_assets(tmp, _SLUG, ["logo.png", "icon.png"])
        _write_meta(
            tmp,
            _SLUG,
            {"embedded": ["logo.png", "icon.png"], "external": [], "shipped": []},
        )
        out_dir = tmp / "out"
        result = apa.run_asset_policy_audit(_SLUG, root=tmp, out_dir=out_dir)
        self.assertTrue(result["ok"], result)
        self.assertFalse(result.get("skipped", False))
        self.assertNotIn("issue", result)
        self.assertEqual(sorted(result["embedded"]), ["icon.png", "logo.png"])
        self.assertEqual(result["shipped"], [])
        report_file = out_dir / "asset_policy_audit.yml"
        self.assertTrue(report_file.exists())

    # --- 2. Silent skip ----------------------------------------------------
    def test_no_asset_dir_silent_skip(self) -> None:
        tmp = self._tmp_root()
        # No shared/assets/<slug>/ created. Meta optional — test the truly
        # asset-free path (8 of 9 templates today).
        _write_meta(tmp, _SLUG, None)
        result = apa.run_asset_policy_audit(_SLUG, root=tmp)
        self.assertTrue(result["ok"])
        self.assertTrue(result["skipped"])
        self.assertIsNone(result["asset_dir"])

    # --- 3. Missing policy when asset dir exists ---------------------------
    def test_missing_policy_when_assets_present(self) -> None:
        tmp = self._tmp_root()
        _write_assets(tmp, _SLUG, ["logo.png"])
        _write_meta(tmp, _SLUG, None)
        result = apa.run_asset_policy_audit(_SLUG, root=tmp)
        self.assertFalse(result["ok"])
        self.assertEqual(result["issue"], "missing")
        self.assertIn("shared/assets", result["message"])

    # --- 4. shipped:-non-empty REJECTED ------------------------------------
    def test_shipped_non_empty_rejected(self) -> None:
        tmp = self._tmp_root()
        _write_assets(tmp, _SLUG, ["logo.png", "photo.jpg"])
        _write_meta(
            tmp,
            _SLUG,
            {"embedded": ["logo.png"], "external": [], "shipped": ["photo.jpg"]},
        )
        result = apa.run_asset_policy_audit(_SLUG, root=tmp)
        self.assertFalse(result["ok"])
        self.assertEqual(result["issue"], "shipped_non_empty")
        # Verbatim message — must match CONTEXT.md lines 56-59.
        self.assertEqual(result["message"], apa._SHIPPED_REJECTED_MSG)

    # --- 5. Unclassified asset on disk -------------------------------------
    def test_unclassified_asset(self) -> None:
        tmp = self._tmp_root()
        _write_assets(tmp, _SLUG, ["logo.png", "extra.png"])
        _write_meta(
            tmp,
            _SLUG,
            {"embedded": ["logo.png"], "external": [], "shipped": []},
        )
        result = apa.run_asset_policy_audit(_SLUG, root=tmp)
        self.assertFalse(result["ok"])
        self.assertEqual(result["issue"], "coverage")
        self.assertEqual(result["unclassified"], ["extra.png"])
        self.assertEqual(result["stale"], [])

    # --- 6. Stale entry in policy ------------------------------------------
    def test_stale_policy_entry(self) -> None:
        tmp = self._tmp_root()
        _write_assets(tmp, _SLUG, ["logo.png"])
        _write_meta(
            tmp,
            _SLUG,
            {"embedded": ["logo.png", "ghost.png"], "external": [], "shipped": []},
        )
        result = apa.run_asset_policy_audit(_SLUG, root=tmp)
        self.assertFalse(result["ok"])
        self.assertEqual(result["issue"], "coverage")
        self.assertEqual(result["unclassified"], [])
        self.assertEqual(result["stale"], ["ghost.png"])

    # --- 7. links_export.yml is metadata, NOT an asset ---------------------
    def test_links_export_yaml_is_metadata(self) -> None:
        tmp = self._tmp_root()
        _write_assets(tmp, _SLUG, ["logo.png"])
        # Drop a links_export.yml + a stray README.md in the same dir.
        adir = tmp / "shared" / "assets" / _SLUG
        (adir / "links_export.yml").write_text(
            "assets: {}\n", encoding="utf-8"
        )
        (adir / "NOTES.md").write_text("notes\n", encoding="utf-8")
        # Policy lists ONLY the actual asset.
        _write_meta(
            tmp,
            _SLUG,
            {"embedded": ["logo.png"], "external": [], "shipped": []},
        )
        result = apa.run_asset_policy_audit(_SLUG, root=tmp)
        self.assertTrue(result["ok"], result)
        self.assertNotIn("links_export.yml", result["on_disk"])
        self.assertNotIn("NOTES.md", result["on_disk"])

    # --- 8. Dual-lookup via meta.yml::idml_source --------------------------
    def test_dual_lookup_via_idml_source(self) -> None:
        """The asset dir may be named after the IDML stem rather than the
        template slug. v2-falzflyer is the canonical case in the repo."""
        tmp = self._tmp_root()
        idml_stem_slug = "some-idml-stem"
        # Assets live under the idml-stem-slug dir, NOT under the template slug.
        (tmp / "shared" / "assets" / idml_stem_slug).mkdir(parents=True)
        (tmp / "shared" / "assets" / idml_stem_slug / "logo.png").write_bytes(b"X")
        # meta.yml carries idml_source pointing at the matching stem.
        tdir = tmp / "templates" / _SLUG
        tdir.mkdir(parents=True)
        (tdir / "meta.yml").write_text(
            yaml.safe_dump(
                {
                    "id": _SLUG,
                    "title": "demo",
                    "idml_source": "Some IDML Stem.idml",
                    "asset_policy": {
                        "embedded": ["logo.png"], "external": [], "shipped": [],
                    },
                },
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        result = apa.run_asset_policy_audit(_SLUG, root=tmp)
        self.assertTrue(result["ok"], result)
        self.assertIn(idml_stem_slug, result["asset_dir"] or "")

    # --- 9. CLI exit codes -------------------------------------------------
    def test_cli_exit_codes(self) -> None:
        tmp = self._tmp_root()
        # Happy path → 0.
        _write_assets(tmp, _SLUG, ["logo.png"])
        _write_meta(
            tmp,
            _SLUG,
            {"embedded": ["logo.png"], "external": [], "shipped": []},
        )
        self.assertEqual(apa.main(["--slug", _SLUG, "--root", str(tmp)]), 0)

        # Coverage (unclassified) → 2.
        (tmp / "shared" / "assets" / _SLUG / "extra.png").write_bytes(b"X")
        self.assertEqual(apa.main(["--slug", _SLUG, "--root", str(tmp)]), 2)

        # Shipped non-empty → 3.
        _write_meta(
            tmp,
            _SLUG,
            {"embedded": ["logo.png", "extra.png"], "external": [], "shipped": ["x.png"]},
        )
        (tmp / "shared" / "assets" / _SLUG / "x.png").write_bytes(b"X")
        self.assertEqual(apa.main(["--slug", _SLUG, "--root", str(tmp)]), 3)


if __name__ == "__main__":
    unittest.main()

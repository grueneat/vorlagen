"""Byte-identity regression for tools/idml_to_dsl.py against v2 falzflyer.

Issue #38 P2 extracts six existing inline patterns from idml_to_dsl.py
into tools/idml_to_dsl_patterns/. This test enforces that the refactor
does not change the converter's output even one byte:

  1. Snapshot the pre-refactor build.py at
     tests/integration/fixtures/v2_falzflyer_build_py_pre_refactor.py.snapshot.
  2. Re-emit the build.py via the post-refactor converter against the
     v2 falzflyer IDML.
  3. Assert byte-identical to the snapshot.

Skips cleanly when originals/ is unavailable (CI without licensed assets).
"""
from __future__ import annotations

import difflib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
SNAPSHOT = ROOT / "tests" / "integration" / "fixtures" / "v2_falzflyer_build_py_pre_refactor.py.snapshot"


def _find_v2_idml() -> Path | None:
    if not (ROOT / "originals").exists():
        return None
    for p in sorted((ROOT / "originals").rglob("*.idml")):
        name_lower = p.name.lower()
        # Require v2-falzflyer-specific tokens. "leporello"/"z-falz" alone
        # match unrelated templates (e.g. the 26-03 Leporello family).
        if "falzflyer" in name_lower or "kandidat" in name_lower:
            return p
    return None


def _have_asset_manifest() -> Path | None:
    manifest = ROOT / "shared" / "assets" / SLUG / "links_export.yml"
    return manifest if manifest.exists() else None


def test_snapshot_exists():
    """The snapshot must be checked in to anchor the byte-identity contract."""
    assert SNAPSHOT.exists(), (
        f"snapshot missing at {SNAPSHOT}; cannot enforce byte-identity"
    )


def test_v2_falzflyer_build_py_byte_identical_after_pattern_extraction():
    idml = _find_v2_idml()
    if idml is None:
        pytest.skip("originals/ missing; v2 falzflyer IDML not available.")
    manifest = _have_asset_manifest()
    if manifest is None:
        pytest.skip(f"asset manifest missing at shared/assets/{SLUG}/links_export.yml")

    # Re-emit the build.py via the post-refactor converter.
    out_path = ROOT / "build" / "byte_identity" / "build.py"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "idml_to_dsl.py"),
        str(idml),
        str(out_path),
        "--template-id", SLUG,
        "--asset-map", str(manifest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, (
        f"converter exited {result.returncode}; stderr:\n{result.stderr}"
    )

    expected = SNAPSHOT.read_bytes()
    actual = out_path.read_bytes()
    if expected != actual:
        # Surface a unified diff to triage.
        expected_text = expected.decode("utf-8", errors="replace").splitlines(keepends=True)
        actual_text = actual.decode("utf-8", errors="replace").splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(
            expected_text, actual_text,
            fromfile="snapshot", tofile="re-emitted", n=3,
        ))
        pytest.fail(
            f"byte-identity broken between snapshot and re-emitted build.py.\n"
            f"diff (first 100 lines):\n{''.join(diff.splitlines(keepends=True)[:100])}"
        )

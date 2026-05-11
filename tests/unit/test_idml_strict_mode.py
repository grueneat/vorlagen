"""Strict-mode unit tests for tools/idml_to_dsl.py — error-path coverage.

Covers the entry-point guards documented in the module docstring:
- ``.indd`` (binary InDesign) is rejected at the ZIP-magic check.
- Missing source IDML produces a clean UnhandledElement.
- Missing --assets-dir produces a clean UnhandledElement.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONVERTER = ROOT / "tools" / "idml_to_dsl.py"


def test_indd_binary_rejected(tmp_path: Path):
    """A file whose first 4 bytes are not the ZIP magic (PK\\x03\\x04) should
    fail with a helpful 'not a valid IDML / re-export from InDesign' message."""
    bogus = tmp_path / "x.indd"
    bogus.write_bytes(b"\x00\x00\x00\x00 not a zip")
    r = subprocess.run(
        [
            sys.executable,
            str(CONVERTER),
            str(bogus),
            str(tmp_path / "out.py"),
            "--template-id",
            "x",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, r.stdout
    assert "not a valid IDML" in r.stderr or "ZIP" in r.stderr


def test_missing_source_idml_raises(tmp_path: Path):
    r = subprocess.run(
        [
            sys.executable,
            str(CONVERTER),
            str(tmp_path / "does_not_exist.idml"),
            str(tmp_path / "out.py"),
            "--template-id",
            "x",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert "Source IDML not found" in r.stderr


def test_missing_assets_dir_raises(tmp_path: Path):
    """A nonexistent --assets-dir must abort with UnhandledElement (the
    converter never falls back to the IDML's original Mac /Users/... path)."""
    # Use any real ZIP as the source so we pass the .indd guard but fail on
    # the missing assets dir. A minimal ZIP is fine — the converter opens
    # IDMLPackage after this check.
    import zipfile

    src = tmp_path / "tiny.idml"
    with zipfile.ZipFile(src, "w") as z:
        z.writestr("placeholder", "")
    r = subprocess.run(
        [
            sys.executable,
            str(CONVERTER),
            str(src),
            str(tmp_path / "out.py"),
            "--template-id",
            "x",
            "--assets-dir",
            str(tmp_path / "nowhere"),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert "assets-dir" in r.stderr and "does not exist" in r.stderr

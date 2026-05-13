"""Integration: v2 falzflyer inject.yml + TOLERANCE_LOG.md migration (Task 17).

Validates:
  1. inject.yml exists and validates against shared/inject.schema.yaml.
  2. hand_patches count matches the inline P5/inject comments migrated
     from build.py at issue-38 time (12 entries).
  3. TOLERANCE_LOG.md documents every brand_overrides entry in meta.yml.
  4. check_overrides_growth.py exits 0 against the current tree (the
     log + inject entries justify the existing tolerance list).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SLUG = "kandidat-falzflyer-din-lang-gruenes-cover-v2"
TDIR = ROOT / "templates" / SLUG
SCHEMA = ROOT / "shared" / "inject.schema.yaml"


def test_inject_yml_exists():
    assert (TDIR / "inject.yml").exists(), f"missing {TDIR / 'inject.yml'}"


def test_inject_yml_validates_against_schema():
    import jsonschema
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    data = yaml.safe_load((TDIR / "inject.yml").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))
    if errors:
        details = "\n".join(
            f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}"
            for e in errors
        )
        pytest.fail(f"inject.yml validation errors:\n{details}")


def test_inject_yml_has_twelve_hand_patches():
    data = yaml.safe_load((TDIR / "inject.yml").read_text(encoding="utf-8"))
    patches = data.get("hand_patches") or []
    assert len(patches) == 12, f"expected 12 hand_patches, got {len(patches)}"


def test_y_coord_bumps_use_delta_field():
    """RESEARCH.md 4.2: y-coord bumps use 'delta' not 'set'."""
    data = yaml.safe_load((TDIR / "inject.yml").read_text(encoding="utf-8"))
    patches = data["hand_patches"]
    y_bumps = [p for p in patches if p.get("field") == "y_mm"]
    assert y_bumps, "expected at least one y-coord bump entry"
    for p in y_bumps:
        assert "delta" in p, f"y_mm patch {p['target']} should use 'delta', not 'set'"
        assert "set" not in p


def test_tolerance_log_exists():
    log = TDIR / "TOLERANCE_LOG.md"
    assert log.exists(), f"missing {log}"


def test_tolerance_log_covers_every_brand_override():
    meta = yaml.safe_load((TDIR / "meta.yml").read_text(encoding="utf-8"))
    brand_overrides = meta.get("brand_overrides") or []
    log_text = (TDIR / "TOLERANCE_LOG.md").read_text(encoding="utf-8")
    for entry in brand_overrides:
        eid = entry.get("id") if isinstance(entry, dict) else entry
        assert eid in log_text, f"TOLERANCE_LOG.md missing entry for {eid!r}"


def test_check_overrides_growth_passes_on_current_tree():
    """The migration must produce a state where the lint exits 0 against HEAD."""
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "check_overrides_growth.py"),
            "--base-ref", "HEAD",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, (
        f"check_overrides_growth failed; stderr:\n{result.stderr}"
    )


def test_inject_classifications_are_valid():
    """Every hand_patch has classification in the documented enum."""
    data = yaml.safe_load((TDIR / "inject.yml").read_text(encoding="utf-8"))
    valid = {"converter-bug", "scribus-engine-bug", "authoring-bug", "human-review"}
    for p in data["hand_patches"]:
        assert p["classification"] in valid


def test_inject_reasons_are_meaningful():
    """Every hand_patch has a non-trivial reason (>=20 chars)."""
    data = yaml.safe_load((TDIR / "inject.yml").read_text(encoding="utf-8"))
    for p in data["hand_patches"]:
        reason = p.get("reason", "")
        assert len(reason) >= 20, (
            f"reason too short for {p['target']}: {reason!r}"
        )

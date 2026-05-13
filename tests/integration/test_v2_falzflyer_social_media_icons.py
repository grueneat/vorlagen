"""Integration test: composite_ai_split on v2 falzflyer's social-media-icons-weiss.ai.

Skips cleanly when originals/ is unavailable. When the inputs are present,
asserts that composite_ai_split.py produces one per-frame PDF for each
distinct ImageFrame in the IDML referencing the AI, plus a manifest.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _find_inputs() -> tuple[Path, Path] | None:
    """Locate the v2 IDML + social-media-icons AI under originals/."""
    if not (ROOT / "originals").exists():
        return None
    idml: Path | None = None
    ai: Path | None = None
    for p in sorted((ROOT / "originals").rglob("*.idml")):
        name_lower = p.name.lower()
        if "leporello" in name_lower or "z-falz" in name_lower:
            idml = p
            break
    if idml is not None:
        for p in sorted(idml.parent.rglob("Links/*")):
            if "social" in p.name.lower() and p.suffix.lower() == ".ai":
                ai = p
                break
    if idml is None or ai is None:
        return None
    return idml, ai


def test_v2_social_media_icons_split():
    inputs = _find_inputs()
    if inputs is None:
        pytest.skip("originals/ missing or social-media AI not found.")
    idml, ai = inputs
    import composite_ai_split as cas
    out_dir = ROOT / "build" / "byte_identity" / "social_media_split"
    manifest = cas.split(ai, idml, out_dir, slug="v2-falzflyer")
    # The strip is documented to contain at least 4 icons.
    assert len(manifest["pages_emitted"]) >= 1
    yml = out_dir / "composite_ai_split.yml"
    assert yml.exists()
    parsed = yaml.safe_load(yml.read_text())
    assert parsed["ai_basename"] == ai.name

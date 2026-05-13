"""Unit tests for tools/asset_extraction_audit.py — Phase E asset audit."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import asset_extraction_audit as aea  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------

_DESIGNMAP = """\
<?xml version="1.0" encoding="UTF-8"?>
<Document>
  <Spread src="Spreads/Spread_u01.xml"/>
</Document>
"""

_SPREAD_ONE_AI_LINK = """\
<?xml version="1.0" encoding="UTF-8"?>
<Spread>
  <Rectangle Self="u10" ItemTransform="1 0 0 1 0 0">
    <Image Self="u11" ItemTransform="1 0 0 1 0 0">
      <Link LinkResourceURI="file:Links/logo.ai"/>
    </Image>
  </Rectangle>
</Spread>
"""

_SPREAD_TWO_AI_FRAMES_DISTINCT_OFFSETS = """\
<?xml version="1.0" encoding="UTF-8"?>
<Spread>
  <Rectangle Self="u20" ItemTransform="1 0 0 1 0 0">
    <Image Self="u21" ItemTransform="1 0 0 1 0 0">
      <Link LinkResourceURI="file:Links/strip.ai"/>
    </Image>
  </Rectangle>
  <Rectangle Self="u30" ItemTransform="1 0 0 1 100 0">
    <Image Self="u31" ItemTransform="1 0 0 1 0 0">
      <Link LinkResourceURI="file:Links/strip.ai"/>
    </Image>
  </Rectangle>
</Spread>
"""


def _make_idml(tmp_path: Path, spread_xml: str, name: str = "test.idml") -> Path:
    """Write a minimal IDML zip with the given Spread XML."""
    p = tmp_path / name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("designmap.xml", _DESIGNMAP)
        z.writestr("Spreads/Spread_u01.xml", spread_xml)
    p.write_bytes(buf.getvalue())
    return p


def _make_solid_pdf(path: Path, width_pt: float, height_pt: float) -> None:
    """Create a single-page PDF of the given point size by saving via Pillow.

    Pillow's PDF writer uses 72 dpi, so 1px = 1pt by default.
    """
    img = Image.new("RGB", (int(width_pt), int(height_pt)), color=(255, 255, 255))
    img.save(str(path), "PDF", resolution=72)


def _write_manifest(path: Path, entries: dict[str, dict]) -> None:
    """Write a minimal links_export.yml at path."""
    body = {"assets": entries}
    path.write_text(
        yaml.safe_dump(body, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Test 1 — happy path: one AI link, present in Links/, in manifest, square.
# ---------------------------------------------------------------------------
def test_audit_ok_one_link(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_ONE_AI_LINK)
    links = tmp_path / "Links"
    links.mkdir()
    # Square 200×200 AI (not composite by aspect ratio).
    _make_solid_pdf(links / "logo.ai", 200.0, 200.0)
    manifest = tmp_path / "links_export.yml"
    _write_manifest(
        manifest,
        {"logo.ai": {"output": "shared/assets/x/logo.png", "kind": "vector_ai", "recipe": "pdftocairo"}},
    )

    out_dir = tmp_path / "out"
    result = aea.audit(
        slug="test",
        idml_path=idml,
        links_export_yml=manifest,
        repo_root=tmp_path,
        out_dir=out_dir,
    )

    assert result["ok"] is True
    assert result["links_total"] == 1
    assert result["links_missing"] == []
    assert result["links_unconverted"] == []
    assert result["composite_ai_detected"] == []
    written = yaml.safe_load((out_dir / "asset_audit.yml").read_text())
    assert written == result


# ---------------------------------------------------------------------------
# Test 2 — AI missing from Links/ => ok=False, links_missing populated.
# ---------------------------------------------------------------------------
def test_audit_link_missing_in_links_dir(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_ONE_AI_LINK)
    (tmp_path / "Links").mkdir()  # no logo.ai
    manifest = tmp_path / "links_export.yml"
    _write_manifest(
        manifest,
        {"logo.ai": {"output": "shared/assets/x/logo.png", "kind": "vector_ai", "recipe": ""}},
    )

    result = aea.audit(
        slug="test",
        idml_path=idml,
        links_export_yml=manifest,
        repo_root=tmp_path,
        out_dir=tmp_path / "out",
    )
    assert result["ok"] is False
    assert "logo.ai" in result["links_missing"]


# ---------------------------------------------------------------------------
# Test 3 — AI present but missing manifest entry.
# ---------------------------------------------------------------------------
def test_audit_link_missing_in_manifest(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_ONE_AI_LINK)
    (tmp_path / "Links").mkdir()
    _make_solid_pdf(tmp_path / "Links" / "logo.ai", 200.0, 200.0)
    manifest = tmp_path / "links_export.yml"
    _write_manifest(manifest, {})

    result = aea.audit(
        slug="test",
        idml_path=idml,
        links_export_yml=manifest,
        repo_root=tmp_path,
        out_dir=tmp_path / "out",
    )
    assert result["ok"] is False
    assert "logo.ai" in result["links_unconverted"]


# ---------------------------------------------------------------------------
# Test 4 — composite-AI by aspect ratio (single page, 600x100 strip).
# ---------------------------------------------------------------------------
def test_audit_composite_ai_by_aspect_ratio(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_ONE_AI_LINK.replace("logo.ai", "strip.ai"))
    (tmp_path / "Links").mkdir()
    _make_solid_pdf(tmp_path / "Links" / "strip.ai", 600.0, 100.0)
    manifest = tmp_path / "links_export.yml"
    _write_manifest(
        manifest,
        {"strip.ai": {"output": "shared/assets/x/strip.png", "kind": "vector_ai", "recipe": ""}},
    )

    result = aea.audit(
        slug="test",
        idml_path=idml,
        links_export_yml=manifest,
        repo_root=tmp_path,
        out_dir=tmp_path / "out",
    )
    assert result["ok"] is False
    assert len(result["composite_ai_detected"]) == 1
    finding = result["composite_ai_detected"][0]
    assert finding["aspect_ratio"] >= 3.0
    assert any("aspect_ratio" in sig for sig in finding["signals"])


# ---------------------------------------------------------------------------
# Test 5 — composite-AI by multiple distinct ImageFrame offsets.
# ---------------------------------------------------------------------------
def test_audit_composite_ai_by_distinct_offsets(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_TWO_AI_FRAMES_DISTINCT_OFFSETS)
    (tmp_path / "Links").mkdir()
    # Square AI so aspect-ratio doesn't trigger; only the distinct-offsets signal.
    _make_solid_pdf(tmp_path / "Links" / "strip.ai", 200.0, 200.0)
    manifest = tmp_path / "links_export.yml"
    _write_manifest(
        manifest,
        {"strip.ai": {"output": "shared/assets/x/strip.png", "kind": "vector_ai", "recipe": ""}},
    )

    result = aea.audit(
        slug="test",
        idml_path=idml,
        links_export_yml=manifest,
        repo_root=tmp_path,
        out_dir=tmp_path / "out",
    )
    assert result["ok"] is False
    finding = result["composite_ai_detected"][0]
    assert finding["distinct_offsets_count"] >= 2
    assert any("distinct_offsets" in sig for sig in finding["signals"])


# ---------------------------------------------------------------------------
# Test 6 — --allow-composite-ai downgrades to warning, ok=True.
# ---------------------------------------------------------------------------
def test_allow_composite_ai_downgrades_to_warning(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_ONE_AI_LINK.replace("logo.ai", "strip.ai"))
    (tmp_path / "Links").mkdir()
    _make_solid_pdf(tmp_path / "Links" / "strip.ai", 600.0, 100.0)
    manifest = tmp_path / "links_export.yml"
    _write_manifest(
        manifest,
        {"strip.ai": {"output": "shared/assets/x/strip.png", "kind": "vector_ai", "recipe": ""}},
    )

    result = aea.audit(
        slug="test",
        idml_path=idml,
        links_export_yml=manifest,
        repo_root=tmp_path,
        allow_composite_ai=True,
        out_dir=tmp_path / "out",
    )
    assert result["ok"] is True
    assert len(result["composite_ai_detected"]) == 1  # still reported
    assert "warnings" in result and result["warnings"]


# ---------------------------------------------------------------------------
# Test 7 — non-AI links are not flagged as composite.
# ---------------------------------------------------------------------------
_SPREAD_PNG_LINK = """\
<?xml version="1.0" encoding="UTF-8"?>
<Spread>
  <Rectangle Self="u10" ItemTransform="1 0 0 1 0 0">
    <Image Self="u11" ItemTransform="1 0 0 1 0 0">
      <Link LinkResourceURI="file:Links/photo.png"/>
    </Image>
  </Rectangle>
</Spread>
"""


def test_png_link_not_flagged_as_composite(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_PNG_LINK)
    (tmp_path / "Links").mkdir()
    # Create a wide PNG; should NOT trigger composite detection (AI-only signal).
    Image.new("RGB", (600, 100), color=(255, 0, 0)).save(
        tmp_path / "Links" / "photo.png"
    )
    manifest = tmp_path / "links_export.yml"
    _write_manifest(
        manifest,
        {"photo.png": {"output": "shared/assets/x/photo.png", "kind": "raster_png", "recipe": ""}},
    )

    result = aea.audit(
        slug="test",
        idml_path=idml,
        links_export_yml=manifest,
        repo_root=tmp_path,
        out_dir=tmp_path / "out",
    )
    assert result["ok"] is True
    assert result["composite_ai_detected"] == []


# ---------------------------------------------------------------------------
# Test 8 — yaml output is byte-stable across runs.
# ---------------------------------------------------------------------------
def test_yaml_output_byte_stable(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_ONE_AI_LINK)
    (tmp_path / "Links").mkdir()
    _make_solid_pdf(tmp_path / "Links" / "logo.ai", 200.0, 200.0)
    manifest = tmp_path / "links_export.yml"
    _write_manifest(
        manifest,
        {"logo.ai": {"output": "shared/assets/x/logo.png", "kind": "vector_ai", "recipe": ""}},
    )

    out_dir_a = tmp_path / "out_a"
    out_dir_b = tmp_path / "out_b"
    aea.audit(slug="test", idml_path=idml, links_export_yml=manifest,
              repo_root=tmp_path, out_dir=out_dir_a)
    aea.audit(slug="test", idml_path=idml, links_export_yml=manifest,
              repo_root=tmp_path, out_dir=out_dir_b)

    a = (out_dir_a / "asset_audit.yml").read_bytes()
    b = (out_dir_b / "asset_audit.yml").read_bytes()
    assert a == b

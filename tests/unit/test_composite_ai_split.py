"""Unit tests for tools/composite_ai_split.py."""
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

import composite_ai_split as cas  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------

_DESIGNMAP = """\
<?xml version="1.0"?>
<Document><Spread src="Spreads/Spread_u01.xml"/></Document>
"""

_SPREAD_FOUR_FRAMES = """\
<?xml version="1.0"?>
<Spread>
  <Rectangle Self="u10" ItemTransform="1 0 0 1 0 0">
    <Image Self="u11" ItemTransform="1 0 0 1 0 0">
      <Link LinkResourceURI="file:Links/strip.ai"/>
    </Image>
  </Rectangle>
  <Rectangle Self="u20" ItemTransform="1 0 0 1 50 0">
    <Image Self="u21" ItemTransform="1 0 0 1 0 0">
      <Link LinkResourceURI="file:Links/strip.ai"/>
    </Image>
  </Rectangle>
  <Rectangle Self="u30" ItemTransform="1 0 0 1 100 0">
    <Image Self="u31" ItemTransform="1 0 0 1 0 0">
      <Link LinkResourceURI="file:Links/strip.ai"/>
    </Image>
  </Rectangle>
  <Rectangle Self="u40" ItemTransform="1 0 0 1 150 0">
    <Image Self="u41" ItemTransform="1 0 0 1 0 0">
      <Link LinkResourceURI="file:Links/strip.ai"/>
    </Image>
  </Rectangle>
</Spread>
"""


def _make_idml(tmp_path: Path, spread_xml: str) -> Path:
    p = tmp_path / "test.idml"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("designmap.xml", _DESIGNMAP)
        z.writestr("Spreads/Spread_u01.xml", spread_xml)
    p.write_bytes(buf.getvalue())
    return p


def _make_ai(tmp_path: Path, w: float = 200.0, h: float = 50.0) -> Path:
    p = tmp_path / "strip.ai"
    Image.new("RGB", (int(w), int(h)), color="white").save(str(p), "PDF", resolution=72)
    return p


# ---------------------------------------------------------------------------
# Test 1 — four distinct frames produce four PDFs.
# ---------------------------------------------------------------------------
def test_four_frames_produce_four_pdfs(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_FOUR_FRAMES)
    ai = _make_ai(tmp_path)
    out_dir = tmp_path / "out"
    manifest = cas.split(ai, idml, out_dir, slug="v2-falzflyer")
    assert len(manifest["pages_emitted"]) == 4
    for row in manifest["pages_emitted"]:
        out_path = Path(row["out"])
        assert out_path.exists()
        assert out_path.suffix == ".pdf"


# ---------------------------------------------------------------------------
# Test 2 — manifest contains bbox / anname for each emitted PDF.
# ---------------------------------------------------------------------------
def test_manifest_has_anname_for_each_emit(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_FOUR_FRAMES)
    ai = _make_ai(tmp_path)
    out_dir = tmp_path / "out"
    manifest = cas.split(ai, idml, out_dir, slug="v2-falzflyer")
    annames = {row["idml_anname"] for row in manifest["pages_emitted"]}
    assert annames == {"u10", "u20", "u30", "u40"}


# ---------------------------------------------------------------------------
# Test 3 — idempotent: rerunning produces identical manifest.
# ---------------------------------------------------------------------------
def test_idempotent_manifest(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_FOUR_FRAMES)
    ai = _make_ai(tmp_path)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    m_a = cas.split(ai, idml, out_a, slug="x")
    m_b = cas.split(ai, idml, out_b, slug="x")
    # Pages-emitted order + transforms should be byte-identical.
    assert [
        (r["index"], r["idml_anname"], r["frame_transform"]) for r in m_a["pages_emitted"]
    ] == [
        (r["index"], r["idml_anname"], r["frame_transform"]) for r in m_b["pages_emitted"]
    ]


# ---------------------------------------------------------------------------
# Test 4 — manifest yml file emitted at <out_dir>/composite_ai_split.yml.
# ---------------------------------------------------------------------------
def test_manifest_yml_written(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_FOUR_FRAMES)
    ai = _make_ai(tmp_path)
    out_dir = tmp_path / "out"
    cas.split(ai, idml, out_dir, slug="x")
    yml = out_dir / "composite_ai_split.yml"
    assert yml.exists()
    parsed = yaml.safe_load(yml.read_text())
    assert parsed["source"] == str(ai)
    assert parsed["ai_basename"] == "strip.ai"
    assert len(parsed["pages_emitted"]) == 4


# ---------------------------------------------------------------------------
# Test 5 — no ImageFrames referencing the AI => warning, no pages.
# ---------------------------------------------------------------------------
def test_no_imageframes_emits_warning(tmp_path):
    spread = '<?xml version="1.0"?><Spread/>'
    idml = _make_idml(tmp_path, spread)
    ai = _make_ai(tmp_path)
    out_dir = tmp_path / "out"
    manifest = cas.split(ai, idml, out_dir, slug="x")
    assert manifest["pages_emitted"] == []
    assert "warning" in manifest


# ---------------------------------------------------------------------------
# Test 6 — output filenames are deterministic given the same input.
# ---------------------------------------------------------------------------
def test_filenames_deterministic(tmp_path):
    idml = _make_idml(tmp_path, _SPREAD_FOUR_FRAMES)
    ai = _make_ai(tmp_path)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    m_a = cas.split(ai, idml, out_a, slug="x")
    m_b = cas.split(ai, idml, out_b, slug="x")
    names_a = sorted(Path(r["out"]).name for r in m_a["pages_emitted"])
    names_b = sorted(Path(r["out"]).name for r in m_b["pages_emitted"])
    assert names_a == names_b

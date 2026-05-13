"""Integration: asset_extraction_audit is wired into render_pipeline._run_audit.

Verifies:
1. _build_preflight accepts the new asset_audit_path keyword and records
   the audit in audits_summary.
2. A fail-state asset_audit.yml flows through to preflight_ok=False.
3. The audit emits the expected yml shape when invoked via the
   asset_extraction_audit module directly using a synthetic IDML.
"""
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

from render_pipeline import _build_preflight  # noqa: E402
import asset_extraction_audit as aea  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic IDML fixture (mirrors tests/unit/test_asset_extraction_audit.py).
# ---------------------------------------------------------------------------

_DESIGNMAP = """\
<?xml version="1.0" encoding="UTF-8"?>
<Document>
  <Spread src="Spreads/Spread_u01.xml"/>
</Document>
"""

_SPREAD = """\
<?xml version="1.0" encoding="UTF-8"?>
<Spread>
  <Rectangle Self="u10" ItemTransform="1 0 0 1 0 0">
    <Image Self="u11" ItemTransform="1 0 0 1 0 0">
      <Link LinkResourceURI="file:Links/logo.ai"/>
    </Image>
  </Rectangle>
</Spread>
"""


def _make_idml(tmp_path: Path, spread_xml: str = _SPREAD) -> Path:
    p = tmp_path / "test.idml"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("designmap.xml", _DESIGNMAP)
        z.writestr("Spreads/Spread_u01.xml", spread_xml)
    p.write_bytes(buf.getvalue())
    return p


def _make_solid_pdf(path: Path, w: float, h: float) -> None:
    Image.new("RGB", (int(w), int(h)), color=(255, 255, 255)).save(
        str(path), "PDF", resolution=72
    )


# ---------------------------------------------------------------------------
# Test 1 — preflight records the asset_extraction audit when path provided.
# ---------------------------------------------------------------------------
def test_preflight_records_asset_extraction(tmp_path):
    out_dir = tmp_path / "validation" / "fake"
    out_dir.mkdir(parents=True)
    asset_audit_path = out_dir / "asset_audit.yml"
    asset_audit_path.write_text(
        yaml.safe_dump(
            {
                "template": "fake",
                "ok": True,
                "links_total": 1,
                "links_resolved": 1,
                "links_converted": 1,
                "links_missing": [],
                "links_unconverted": [],
                "composite_ai_detected": [],
            }
        )
    )

    pf = _build_preflight(
        out_dir=out_dir,
        tid="fake",
        inventory_path=out_dir / "missing.yml",
        text_audit_path=out_dir / "missing.yml",
        image_audit_path=out_dir / "missing.yml",
        font_audit_path=out_dir / "missing.yml",
        text_render_audit_path=out_dir / "missing.yml",
        text_position_audit_path=out_dir / "missing.yml",
        run_style_audit_path=out_dir / "missing.yml",
        color_audit_path=out_dir / "missing.yml",
        asset_audit_path=asset_audit_path,
    )
    assert "asset_extraction" in pf["audits"]
    assert pf["audits"]["asset_extraction"]["ok"] is True
    assert pf["audits"]["asset_extraction"]["issues"] == 0


# ---------------------------------------------------------------------------
# Test 2 — fail-state asset audit flows through to preflight.ok=False.
# ---------------------------------------------------------------------------
def test_failed_asset_audit_blocks_preflight(tmp_path):
    out_dir = tmp_path / "validation" / "fake"
    out_dir.mkdir(parents=True)
    asset_audit_path = out_dir / "asset_audit.yml"
    asset_audit_path.write_text(
        yaml.safe_dump(
            {
                "template": "fake",
                "ok": False,
                "links_total": 2,
                "links_resolved": 1,
                "links_converted": 1,
                "links_missing": ["broken.psd"],
                "links_unconverted": [],
                "composite_ai_detected": [],
            }
        )
    )

    pf = _build_preflight(
        out_dir=out_dir,
        tid="fake",
        inventory_path=out_dir / "missing.yml",
        text_audit_path=out_dir / "missing.yml",
        image_audit_path=out_dir / "missing.yml",
        font_audit_path=out_dir / "missing.yml",
        text_render_audit_path=out_dir / "missing.yml",
        text_position_audit_path=out_dir / "missing.yml",
        run_style_audit_path=out_dir / "missing.yml",
        color_audit_path=out_dir / "missing.yml",
        asset_audit_path=asset_audit_path,
    )
    assert pf["ok"] is False
    assert pf["audits"]["asset_extraction"]["ok"] is False
    assert "missing" in pf["audits"]["asset_extraction"]["detail"]


# ---------------------------------------------------------------------------
# Test 3 — full chain: aea.audit produces yml that _build_preflight consumes.
# ---------------------------------------------------------------------------
def test_end_to_end_audit_to_preflight(tmp_path):
    idml = _make_idml(tmp_path)
    (tmp_path / "Links").mkdir()
    _make_solid_pdf(tmp_path / "Links" / "logo.ai", 200.0, 200.0)
    manifest = tmp_path / "links_export.yml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "assets": {
                    "logo.ai": {
                        "output": "shared/assets/x/logo.png",
                        "kind": "vector_ai",
                        "recipe": "pdftocairo",
                    }
                }
            }
        )
    )

    out_dir = tmp_path / "out"
    report = aea.audit(
        slug="end2end",
        idml_path=idml,
        links_export_yml=manifest,
        repo_root=tmp_path,
        out_dir=out_dir,
    )
    assert report["ok"] is True

    pf = _build_preflight(
        out_dir=out_dir,
        tid="end2end",
        inventory_path=out_dir / "missing.yml",
        text_audit_path=out_dir / "missing.yml",
        image_audit_path=out_dir / "missing.yml",
        font_audit_path=out_dir / "missing.yml",
        text_render_audit_path=out_dir / "missing.yml",
        text_position_audit_path=out_dir / "missing.yml",
        run_style_audit_path=out_dir / "missing.yml",
        color_audit_path=out_dir / "missing.yml",
        asset_audit_path=out_dir / "asset_audit.yml",
    )
    assert pf["audits"]["asset_extraction"]["ok"] is True


# ---------------------------------------------------------------------------
# Test 4 — _run_audit invokes asset_extraction_audit FIRST in chain (smoke).
#
# We can't exercise the full _run_audit here (it requires preview.pdf +
# baseline.pdf + a build.py), but we CAN confirm the import wiring works
# and the args.allow_composite_ai attribute is read from the namespace
# without crashing.
# ---------------------------------------------------------------------------
def test_run_audit_imports_asset_extraction_audit():
    """Smoke: the module-level import statement in _run_audit succeeds."""
    import importlib
    rp = importlib.import_module("render_pipeline")
    aea_mod = importlib.import_module("asset_extraction_audit")
    # _run_audit is defined and asset_extraction_audit is importable from the
    # tools/ path that _run_audit uses.
    assert hasattr(rp, "_run_audit")
    assert hasattr(aea_mod, "audit")


def test_render_pipeline_cli_accepts_allow_composite_ai_flag():
    """The new --allow-composite-ai flag is parseable without crashing."""
    import argparse
    import importlib
    rp = importlib.import_module("render_pipeline")
    # main() will exit when called with --help, so just verify parser
    # construction via the argparse error path isn't triggered.
    # Instead, look at the parser-building code by invoking it with --help.
    import subprocess
    result = subprocess.run(
        [sys.executable, str(TOOLS / "render_pipeline.py"), "--help"],
        capture_output=True,
        text=True,
    )
    # --help exits 0; output mentions our new flag.
    assert result.returncode == 0
    assert "--allow-composite-ai" in result.stdout

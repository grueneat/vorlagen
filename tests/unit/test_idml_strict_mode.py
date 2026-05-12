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


def test_missing_asset_map_raises(tmp_path: Path):
    """--asset-map pointing at a missing file must abort with a clear message."""
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
            "--asset-map",
            str(tmp_path / "nope.yml"),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert "asset-map" in r.stderr and "does not exist" in r.stderr


# ---------------------------------------------------------------------------
# Unit-level coverage for the asset_map flow (does not require the bundled
# IDML — uses the converter's internals directly).
# ---------------------------------------------------------------------------


def _make_pageitem_context() -> "object":
    """Return a minimal ``_Ctx`` populated for ``_emit_image_content``."""
    sys.path.insert(0, str(ROOT / "tools"))
    from idml_to_dsl import _Ctx, PythonRepr  # type: ignore[import-not-found]

    ctx = _Ctx(pkg=None, template_id="t", assets_dir=ROOT)
    ctx.out = PythonRepr()
    return ctx


def test_asset_map_takes_precedence_over_logo_map():
    """When both --asset-map and --logo-map cover a vector logo basename,
    asset_map wins. Backward-compat: legacy logo_map still works on its own."""
    sys.path.insert(0, str(ROOT / "tools"))
    from lxml import etree

    from idml_to_dsl import (  # type: ignore[import-not-found]
        _Ctx,
        PythonRepr,
        _emit_pageitem,
    )

    # Build a synthetic <Rectangle> with a nested <PDF> referencing 'X.ai'.
    spread_xml = b"""<?xml version="1.0"?><Spread Self="s">
      <Rectangle Self="r1" ItemLayer="L1" ItemTransform="1 0 0 1 0 0">
        <Properties>
          <PathGeometry>
            <GeometryPathType PathOpen="false">
              <PathPointArray>
                <PathPointType Anchor="0 0"/>
                <PathPointType Anchor="100 0"/>
                <PathPointType Anchor="100 50"/>
                <PathPointType Anchor="0 50"/>
              </PathPointArray>
            </GeometryPathType>
          </PathGeometry>
        </Properties>
        <PDF Self="pdf1">
          <Link LinkResourceURI="file:///x/X.ai"/>
        </PDF>
      </Rectangle>
    </Spread>"""
    spread = etree.fromstring(spread_xml)
    item = spread.find("Rectangle")
    page_var = "page0"

    ident_str = "1 0 0 1 0 0"
    page_gb = (0.0, 0.0, 595.0, 841.89)  # arbitrary A4 landscape pts
    # asset_map wins.
    ctx_a = _Ctx(pkg=None, template_id="t", assets_dir=ROOT)
    ctx_a.out = PythonRepr()
    ctx_a.layer_id_to_idx = {"L1": 0}
    ctx_a.asset_map = {"X.ai": "shared/assets/x/x-from-asset-map.png"}
    ctx_a.logo_map = {"X.ai": "shared/logos/x-from-logo-map.png"}
    ctx_a._current_page_var = page_var
    _emit_pageitem(ctx_a.out, item, [], ident_str, ident_str, page_gb, page_var, ctx_a, 0)
    rendered_a = ctx_a.out.render()
    assert "x-from-asset-map.png" in rendered_a
    assert "x-from-logo-map.png" not in rendered_a

    # logo_map alone still works (backward-compat).
    ctx_b = _Ctx(pkg=None, template_id="t", assets_dir=ROOT)
    ctx_b.out = PythonRepr()
    ctx_b.layer_id_to_idx = {"L1": 0}
    ctx_b.logo_map = {"X.ai": "shared/logos/x-from-logo-map.png"}
    ctx_b._current_page_var = page_var
    _emit_pageitem(ctx_b.out, item, [], ident_str, ident_str, page_gb, page_var, ctx_b, 0)
    rendered_b = ctx_b.out.render()
    assert "x-from-logo-map.png" in rendered_b


def test_image_with_psd_basename_without_asset_map_raises(tmp_path: Path):
    """The hidden bug from Phase 1: <Image> referencing a .psd basename
    used to silently emit the raw .psd path (Scribus rendered blank). Now
    the converter raises if no --asset-map covers the basename."""
    sys.path.insert(0, str(ROOT / "tools"))
    from lxml import etree

    from idml_to_dsl import (  # type: ignore[import-not-found]
        UnhandledElement as _UnhandledElement,
        _emit_image_content,
        _Ctx,
        PythonRepr,
    )

    # Fake <Rectangle> wrapping a <Image> that points at a .psd.
    rect_xml = b"""<?xml version="1.0"?>
    <Rectangle Self="r1">
      <Image Self="i1">
        <Link LinkResourceURI="file:///x/Plakat.psd"/>
      </Image>
    </Rectangle>"""
    rect = etree.fromstring(rect_xml)
    img = rect.find("Image")

    ctx = _Ctx(pkg=None, template_id="t", assets_dir=tmp_path)
    ctx.out = PythonRepr()
    # No asset_map → legacy fallback active → must raise on .psd extension.

    try:
        _emit_image_content(ctx.out, rect, img, 0, 0, 50, 30, 0, "r1", 0, ctx)
    except _UnhandledElement as e:
        assert "Plakat.psd" in str(e)
        assert "asset-map" in str(e)
        return
    raise AssertionError("expected UnhandledElement for .psd without --asset-map")


def test_image_with_psd_basename_with_asset_map_emits_mapped_png(tmp_path: Path):
    """With --asset-map covering the .psd basename, the converter emits the
    mapped PNG path instead of the raw .psd."""
    sys.path.insert(0, str(ROOT / "tools"))
    from lxml import etree

    from idml_to_dsl import (  # type: ignore[import-not-found]
        _emit_image_content,
        _Ctx,
        PythonRepr,
    )

    rect_xml = b"""<?xml version="1.0"?>
    <Rectangle Self="r1">
      <Image Self="i1">
        <Link LinkResourceURI="file:///x/Plakat.psd"/>
      </Image>
    </Rectangle>"""
    rect = etree.fromstring(rect_xml)
    img = rect.find("Image")

    ctx = _Ctx(pkg=None, template_id="t", assets_dir=tmp_path)
    ctx.out = PythonRepr()
    ctx.asset_map = {"Plakat.psd": "shared/assets/x/plakat.png"}
    ctx._current_page_var = "page0"  # set by the outer emit loop in real runs

    _emit_image_content(ctx.out, rect, img, 0, 0, 50, 30, 0, "r1", 0, ctx)
    rendered = ctx.out.render()
    assert "plakat.png" in rendered
    assert "Plakat.psd" not in rendered

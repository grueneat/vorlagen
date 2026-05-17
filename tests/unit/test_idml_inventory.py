"""Unit tests for tools/idml_inventory.py — IDML spread element inventory.

Tests use synthetic minimal fixtures (tiny IDML zip + build.py text) so
they run fully offline and in <5 seconds.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
import yaml

# Bootstrap tools/ onto sys.path so we can import the module directly.
import sys
TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from idml_inventory import (
    _extract_annames_from_build_py,
    _load_printable_layers,
    _load_spread_order,
    _collect_spread_items,
    _build_hint,
    run_inventory,
    _yaml_dump,
)


# ---------------------------------------------------------------------------
# Fixtures: synthetic IDML + build.py content
# ---------------------------------------------------------------------------

DESIGNMAP_TWO_LAYERS = """\
<?xml version="1.0" encoding="UTF-8"?>
<Document>
  <Layer Self="lba" Name="Gestaltung" Printable="true" Visible="true"/>
  <Layer Self="le6" Name="Info" Printable="false" Visible="true"/>
  <Spread src="Spreads/Spread_ub1.xml"/>
</Document>
"""

SPREAD_XML_SIMPLE = """\
<?xml version="1.0" encoding="UTF-8"?>
<Spread>
  <Rectangle Self="u1" ItemLayer="lba">
    <Image Self="u2" ItemLayer="lba"/>
  </Rectangle>
  <Rectangle Self="u3" ItemLayer="lba">
  </Rectangle>
  <TextFrame Self="u4" ItemLayer="lba" ParentStory="s99">
  </TextFrame>
  <Polygon Self="u5" ItemLayer="lba" FillColor="Color/Green">
  </Polygon>
  <Polygon Self="u6" ItemLayer="le6" FillColor="Color/Info">
  </Polygon>
</Spread>
"""

STORY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<Story Self="s99">
  <ParagraphStyleRange>
    <CharacterStyleRange><Content>Hello</Content></CharacterStyleRange>
  </ParagraphStyleRange>
  <ParagraphStyleRange>
    <CharacterStyleRange><Content>World</Content></CharacterStyleRange>
  </ParagraphStyleRange>
</Story>
"""


def _make_idml_zip(tmp_path: Path, spread_xml: str = SPREAD_XML_SIMPLE) -> Path:
    """Create a minimal IDML zip at tmp_path/test.idml."""
    idml_path = tmp_path / "test.idml"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("designmap.xml", DESIGNMAP_TWO_LAYERS)
        z.writestr("Spreads/Spread_ub1.xml", spread_xml)
        z.writestr("Stories/Story_s99.xml", STORY_XML)
    idml_path.write_bytes(buf.getvalue())
    return idml_path


def _make_build_py(tmp_path: Path, content: str) -> Path:
    bp = tmp_path / "build.py"
    bp.write_text(content, encoding="utf-8")
    return bp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_load_printable_layers_basic(tmp_path):
    idml = _make_idml_zip(tmp_path)
    with zipfile.ZipFile(idml) as z:
        layers = _load_printable_layers(z)
    assert "lba" in layers      # Gestaltung (Printable=true)
    assert "le6" not in layers  # Info (Printable=false)


def test_load_spread_order_from_designmap(tmp_path):
    idml = _make_idml_zip(tmp_path)
    with zipfile.ZipFile(idml) as z:
        order = _load_spread_order(z)
    assert order == ["Spreads/Spread_ub1.xml"]


def test_collect_spread_items_filters_info_layer(tmp_path):
    idml = _make_idml_zip(tmp_path)
    with zipfile.ZipFile(idml) as z:
        printable = _load_printable_layers(z)
        spread_xml = z.read("Spreads/Spread_ub1.xml")
        items = _collect_spread_items(spread_xml, printable, z, "Spread_ub1")
    selfs = [item["self"] for item in items]
    # u1=Rectangle, u3=Rectangle, u4=TextFrame, u5=Polygon (all Gestaltung)
    # u2=Image is a child of u1 → skipped (it's CHILD_CONTENT_TAG)
    # u6=Polygon is Info layer → excluded
    assert "u1" in selfs
    assert "u3" in selfs
    assert "u4" in selfs
    assert "u5" in selfs
    assert "u2" not in selfs   # child Image skipped
    assert "u6" not in selfs   # Info layer excluded


def test_hint_inline_vector_path(tmp_path):
    """A Polygon with FillColor and no Image/PDF child gets 'inline vector path' hint."""
    idml = _make_idml_zip(tmp_path)
    with zipfile.ZipFile(idml) as z:
        printable = _load_printable_layers(z)
        spread_xml = z.read("Spreads/Spread_ub1.xml")
        items = _collect_spread_items(spread_xml, printable, z, "Spread_ub1")
    u5_item = next(i for i in items if i["self"] == "u5")
    assert "inline vector path" in u5_item["hint"]


def test_extract_annames_from_build_py(tmp_path):
    bp_content = """\
page0.add(TextFrame(
    x_mm=10,
    anname='u1ae',
    runs=[Run(text='Hello')],
))
page0.add(ImageFrame(
    x_mm=20,
    anname='u1b0',
    image='foo.png',
))
page0.add(Polygon(
    x_mm=30,
    anname='u1c7',
    fill='Green',
))
"""
    bp = _make_build_py(tmp_path, bp_content)
    annames = _extract_annames_from_build_py(bp)
    assert "u1ae" in annames
    assert annames["u1ae"] == "TextFrame"
    assert "u1b0" in annames
    assert annames["u1b0"] == "ImageFrame"
    assert "u1c7" in annames
    assert annames["u1c7"] == "Polygon"


def test_run_inventory_detects_dropped_element(tmp_path):
    """Elements in IDML but missing from build.py appear in elements_dropped."""
    idml = _make_idml_zip(tmp_path)
    # build.py only emits u1 and u4 — u3 and u5 are dropped
    bp_content = """\
page0.add(TextFrame(anname='u4', runs=[Run(text='Hi')]))
page0.add(ImageFrame(anname='u1', image='x.png'))
"""
    bp = _make_build_py(tmp_path, bp_content)
    report = run_inventory(idml, bp, template="test-tpl")
    assert report["template"] == "test-tpl"
    spread = report["spreads"][0]
    dropped_selfs = {d["self"] for d in spread.get("elements_dropped", [])}
    assert "u3" in dropped_selfs   # Rectangle without emission
    assert "u5" in dropped_selfs   # Polygon without emission
    assert "u1" not in dropped_selfs
    assert "u4" not in dropped_selfs


def test_run_inventory_emitted_count(tmp_path):
    idml = _make_idml_zip(tmp_path)
    # build.py emits all Gestaltung items: u1, u3, u4, u5
    bp_content = """\
page0.add(ImageFrame(anname='u1', image='x.png'))
page0.add(Polygon(anname='u3', fill='Blue'))
page0.add(TextFrame(anname='u4', runs=[Run(text='Hi')]))
page0.add(Polygon(anname='u5', fill='Green'))
"""
    bp = _make_build_py(tmp_path, bp_content)
    report = run_inventory(idml, bp, template="test-tpl")
    spread = report["spreads"][0]
    assert spread["elements_total"] == 4  # u1, u3, u4, u5 (u2 is child, u6 is Info)
    assert spread["elements_emitted"] == 4
    assert "elements_dropped" not in spread


def test_run_inventory_no_extra_for_synthetic_annames(tmp_path):
    """Synthetic annames like u1b0_hl (hand-split frames) are NOT flagged as extra."""
    idml = _make_idml_zip(tmp_path)
    bp_content = """\
page0.add(ImageFrame(anname='u1', image='x.png'))
page0.add(TextFrame(anname='u4', runs=[Run(text='Hi')]))
page0.add(TextFrame(anname='u4_hl', runs=[Run(text='World')]))
page0.add(Polygon(anname='u3', fill='Blue'))
page0.add(Polygon(anname='u5', fill='Green'))
"""
    bp = _make_build_py(tmp_path, bp_content)
    report = run_inventory(idml, bp, template="test-tpl")
    # u4_hl is a synthetic split — should NOT appear in elements_extra_global
    extras = report.get("elements_extra_global", [])
    extra_annames = [e["anname"] for e in extras]
    assert "u4_hl" not in extra_annames


def test_yaml_output_is_deterministic(tmp_path):
    """Running inventory twice on the same input produces identical YAML."""
    idml = _make_idml_zip(tmp_path)
    bp_content = "page0.add(TextFrame(anname='u4', runs=[Run(text='Hi')]))\n"
    bp = _make_build_py(tmp_path, bp_content)
    r1 = run_inventory(idml, bp, template="t")
    r2 = run_inventory(idml, bp, template="t")
    assert _yaml_dump(r1) == _yaml_dump(r2)


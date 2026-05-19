"""Unit tests for the IDML color phase (issue 35, task 4).

Pins the locked-decision-#1 mapping policy:
- Exact CMYK match against shared/ci.yml brand palette → auto-rename.
- ``Color/Paper`` → ``White``.
- ``Color/Registration`` and process-ink builtins → silently skipped.
- Non-brand printable swatch on a used Self → auto-registered as document-local
  CMYK color (preserves authored print-mark colours like Endformat).
- Non-brand printable swatch on an unused Self → silently dropped.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from idml_to_dsl import (  # noqa: E402
    COLOR_CMYK_TO_BRAND,
    UnhandledElement,
    _emit_colors_from_xml,
    _parse_color_value,
)


def _graphic_xml(colors: list[dict[str, str]]) -> bytes:
    """Build a synthetic Resources/Graphic.xml-shaped doc with the given colors."""
    root = etree.Element("Graphic")
    for c in colors:
        etree.SubElement(root, "Color", **c)
    return etree.tostring(root)


def test_parse_color_value_rounds_to_int():
    assert _parse_color_value("85 35 95 10") == (85, 35, 95, 10)
    assert _parse_color_value("84.7 35.0 95.0 10") == (85, 35, 95, 10)


def test_parse_color_value_rejects_bad_token_count():
    with pytest.raises(UnhandledElement):
        _parse_color_value("0 0 0")


def test_parse_color_value_rejects_out_of_range():
    with pytest.raises(UnhandledElement):
        _parse_color_value("0 0 0 150")


def test_brand_rename_dunkelgruen():
    """An exact CMYK match against the brand palette renames to brand name."""
    xml = _graphic_xml([
        {"Self": "Color/C=85 M=35 Y=95 K=10", "Name": "C=85 M=35 Y=95 K=10",
         "Space": "CMYK", "Model": "Process", "ColorValue": "85 35 95 10",
         "ColorOverride": "Normal"},
    ])
    resolved = _emit_colors_from_xml(xml, used_colors={"Color/C=85 M=35 Y=95 K=10"})
    assert resolved == {"Color/C=85 M=35 Y=95 K=10": "Dunkelgrün"}


def test_paper_to_white():
    xml = _graphic_xml([
        {"Self": "Color/Paper", "Name": "Paper", "Space": "CMYK",
         "Model": "Process", "ColorValue": "0 0 0 0",
         "ColorOverride": "Specialpaper"},
    ])
    resolved = _emit_colors_from_xml(xml, used_colors={"Color/Paper"})
    assert resolved == {"Color/Paper": "White"}


def test_registration_skipped():
    xml = _graphic_xml([
        {"Self": "Color/Registration", "Name": "Registration", "Space": "CMYK",
         "Model": "Registration", "ColorValue": "100 100 100 100",
         "ColorOverride": "Specialregistration"},
    ])
    resolved = _emit_colors_from_xml(xml, used_colors={"Color/Registration"})
    assert "Color/Registration" not in resolved


def test_process_ink_cyan_skipped_when_hidden_reserved_and_unused():
    xml = _graphic_xml([
        {"Self": "Color/Cyan", "Name": "Cyan", "Space": "CMYK",
         "Model": "Process", "ColorValue": "100 0 0 0",
         "ColorOverride": "Hiddenreserved"},
    ])
    # An UNUSED Hiddenreserved process ink is dropped.
    resolved = _emit_colors_from_xml(xml, used_colors=set())
    assert "Color/Cyan" not in resolved


def test_referenced_hidden_yellow_resolves_to_brand_gelb():
    """A Hiddenreserved process ink that IS referenced (e.g. the yellow
    squiggle motif fills with the builtin Color/Yellow) must resolve through
    COLOR_CMYK_TO_BRAND instead of being silently skipped — otherwise the
    squiggle's FillColor is unresolvable and the shape renders black."""
    xml = _graphic_xml([
        {"Self": "Color/Yellow", "Name": "Yellow", "Space": "CMYK",
         "Model": "Process", "ColorValue": "0 0 100 0",
         "ColorOverride": "Hiddenreserved"},
    ])
    resolved = _emit_colors_from_xml(xml, used_colors={"Color/Yellow"})
    assert resolved["Color/Yellow"] == "Gelb"


def test_referenced_hidden_black_resolves_to_brand_black():
    xml = _graphic_xml([
        {"Self": "Color/Black", "Name": "Black", "Space": "CMYK",
         "Model": "Process", "ColorValue": "0 0 0 100",
         "ColorOverride": "Hiddenreserved"},
    ])
    resolved = _emit_colors_from_xml(xml, used_colors={"Color/Black"})
    assert resolved["Color/Black"] == "Black"


def test_color_none_skipped_even_when_referenced():
    """Color/None / Swatch/None carry no resolvable CMYK — always dropped."""
    xml = _graphic_xml([
        {"Self": "Color/None", "Name": "None", "Space": "CMYK",
         "Model": "Process", "ColorValue": "0 0 0 0", "ColorOverride": "Normal"},
    ])
    resolved = _emit_colors_from_xml(xml, used_colors={"Color/None"})
    assert "Color/None" not in resolved


def test_non_brand_printable_registers_as_local():
    """A non-brand swatch referenced by a printable fill is auto-registered as
    a document-local color (CMYK preserved). Previously the converter raised
    here; that lost authored print-mark colours like "Endformat" / "Druckformat"
    and dropped the items using them out of the render entirely."""
    xml = _graphic_xml([
        {"Self": "Color/Endformat", "Name": "Endformat", "Space": "CMYK",
         "Model": "Process", "ColorValue": "0 100 100 0",
         "ColorOverride": "Normal"},
    ])
    extra: dict[str, tuple[int, int, int, int]] = {}
    resolved = _emit_colors_from_xml(
        xml, used_colors={"Color/Endformat"}, extra_colors=extra
    )
    # Color is resolved to a sanitized DSL name and exported as an extra CMYK.
    assert "Color/Endformat" in resolved
    dsl_name = resolved["Color/Endformat"]
    assert extra[dsl_name] == (0, 100, 100, 0)


def test_non_brand_unused_silently_dropped():
    """A non-brand swatch that no printable PageItem references is dropped."""
    xml = _graphic_xml([
        {"Self": "Color/Endformat", "Name": "Endformat", "Space": "CMYK",
         "Model": "Process", "ColorValue": "0 100 100 0",
         "ColorOverride": "Normal"},
    ])
    resolved = _emit_colors_from_xml(xml, used_colors=set())
    assert "Color/Endformat" not in resolved


def test_brand_palette_has_six_entries():
    """Smoke: the locked color map covers the six brand-relevant CMYK tuples."""
    assert len(COLOR_CMYK_TO_BRAND) == 6
    assert COLOR_CMYK_TO_BRAND[(85, 35, 95, 10)] == "Dunkelgrün"
    assert COLOR_CMYK_TO_BRAND[(0, 0, 100, 0)] == "Gelb"
    assert COLOR_CMYK_TO_BRAND[(0, 100, 0, 0)] == "Magenta"

"""Unit tests for the IDML style phase (issue 35, task 5).

Pins:
- ``_idml_style_slug`` produces stable, ASCII-folded slugs for the 5 corpus
  paragraph-style names (incl. ``ü`` → ``ue``, ``ß`` → ``ss``, space → ``-``).
- BasedOn chain resolves AppliedFont and PointSize correctly.
- ``JUSTIFICATION_MAP`` covers all 4 corpus values; unknown raises.
- ``_make_font_name`` concatenates family + style.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from idml_to_dsl import (  # noqa: E402
    JUSTIFICATION_MAP,
    UnhandledElement,
    _idml_style_slug,
    _make_font_name,
    _read_paragraph_styles_from_xml,
    _resolve_paragraph_style,
)


def test_slug_normalparagraphstyle():
    assert _idml_style_slug("$ID/NormalParagraphStyle") == "idml/normalparagraphstyle"


def test_slug_absatzformat_1():
    assert _idml_style_slug("Absatzformat 1") == "idml/absatzformat-1"


def test_slug_aufzaehlungen():
    assert (
        _idml_style_slug("Aufzählungen auf grünem Hintergrund")
        == "idml/aufzaehlungen-auf-gruenem-hintergrund"
    )


def test_slug_fliesstext():
    assert (
        _idml_style_slug("Fließtext auf grünem Hintergrund")
        == "idml/fliesstext-auf-gruenem-hintergrund"
    )


def test_slug_headline():
    assert _idml_style_slug("Headline in grünem Kasten") == "idml/headline-in-gruenem-kasten"


def test_justification_map_covers_corpus():
    assert JUSTIFICATION_MAP["LeftAlign"] == 0
    assert JUSTIFICATION_MAP["CenterAlign"] == 1
    assert JUSTIFICATION_MAP["RightAlign"] == 2
    assert JUSTIFICATION_MAP["LeftJustified"] == 3
    assert JUSTIFICATION_MAP["FullyJustified"] == 3


def test_make_font_name_combines_family_and_style():
    assert _make_font_name("Gotham Narrow", "Bold", ctx_self_id="x") == "Gotham Narrow Bold"
    assert _make_font_name("Gotham Narrow", None, ctx_self_id="x") == "Gotham Narrow"
    assert _make_font_name(None, "Bold", ctx_self_id="x") == "Bold"
    assert _make_font_name(None, None, ctx_self_id="x") is None


# --- BasedOn chain resolution -------------------------------------------------

def _styles_xml(*paragraph_styles: dict) -> bytes:
    """Build a minimal Resources/Styles.xml with the given paragraph styles.

    Each input dict may carry: ``Self``, ``Name``, attributes (point_size,
    fill_color, font_style, justification), and optional child props
    (based_on, applied_font, leading).
    """
    root = etree.Element("Styles")
    rpsg = etree.SubElement(root, "RootParagraphStyleGroup")
    rcsg = etree.SubElement(root, "RootCharacterStyleGroup")
    etree.SubElement(rcsg, "CharacterStyle", Self="CharacterStyle/$ID/[No character style]",
                     Name="$ID/[No character style]")
    for ps in paragraph_styles:
        attrs = {"Self": ps["Self"], "Name": ps["Name"]}
        for attr_key, ps_key in (
            ("PointSize", "point_size"),
            ("FillColor", "fill_color"),
            ("FontStyle", "font_style"),
            ("Justification", "justification"),
        ):
            if ps_key in ps and ps[ps_key] is not None:
                attrs[attr_key] = str(ps[ps_key])
        ps_node = etree.SubElement(rpsg, "ParagraphStyle", **attrs)
        props = etree.SubElement(ps_node, "Properties")
        if "based_on" in ps and ps["based_on"]:
            bo = etree.SubElement(props, "BasedOn", type="object")
            bo.text = ps["based_on"]
        if "applied_font" in ps and ps["applied_font"]:
            af = etree.SubElement(props, "AppliedFont", type="string")
            af.text = ps["applied_font"]
        if "leading" in ps and ps["leading"] is not None:
            ld = etree.SubElement(props, "Leading", type="unit")
            ld.text = str(ps["leading"])
    return etree.tostring(root)


def test_based_on_chain_inherits_applied_font():
    xml = _styles_xml(
        {"Self": "ParagraphStyle/$ID/[No paragraph style]",
         "Name": "$ID/[No paragraph style]",
         "point_size": 12, "applied_font": "Times", "font_style": "Roman",
         "fill_color": "Color/Black", "justification": "LeftAlign"},
        {"Self": "ParagraphStyle/Headline in grünem Kasten",
         "Name": "Headline in grünem Kasten",
         "fill_color": "Color/Paper", "font_style": "Bold",
         "justification": "CenterAlign",
         "applied_font": "Gotham Narrow",
         "based_on": "$ID/[No paragraph style]"},
    )
    styles = _read_paragraph_styles_from_xml(xml)
    resolved = _resolve_paragraph_style(
        styles["ParagraphStyle/Headline in grünem Kasten"], styles
    )
    # Own attrs take precedence; inheritance fills point_size from parent.
    assert resolved["applied_font"] == "Gotham Narrow"
    assert resolved["font_style"] == "Bold"
    assert resolved["point_size"] == 12  # inherited from $ID/[No paragraph style]
    assert resolved["justification"] == "CenterAlign"
    assert resolved["fill_color"] == "Color/Paper"


def test_based_on_chain_walks_two_hops():
    """ParagraphStyle/Absatzformat 1 → Fließtext → $ID/[No paragraph style]."""
    xml = _styles_xml(
        {"Self": "ParagraphStyle/$ID/[No paragraph style]",
         "Name": "$ID/[No paragraph style]",
         "point_size": 12, "applied_font": "Times", "fill_color": "Color/Black",
         "justification": "LeftAlign"},
        {"Self": "ParagraphStyle/Fließtext auf grünem Hintergrund",
         "Name": "Fließtext auf grünem Hintergrund",
         "point_size": 11, "applied_font": "Gotham Narrow",
         "fill_color": "Color/Paper", "font_style": "Book",
         "justification": "LeftJustified",
         "based_on": "$ID/[No paragraph style]"},
        {"Self": "ParagraphStyle/Absatzformat 1",
         "Name": "Absatzformat 1",
         "based_on": "ParagraphStyle/Fließtext auf grünem Hintergrund"},
    )
    styles = _read_paragraph_styles_from_xml(xml)
    resolved = _resolve_paragraph_style(styles["ParagraphStyle/Absatzformat 1"], styles)
    assert resolved["point_size"] == 11
    assert resolved["applied_font"] == "Gotham Narrow"
    assert resolved["font_style"] == "Book"
    assert resolved["fill_color"] == "Color/Paper"
    assert resolved["justification"] == "LeftJustified"


def test_unknown_justification_not_in_map():
    """An unrecognised IDML Justification value is not in JUSTIFICATION_MAP."""
    assert "BogusAlign" not in JUSTIFICATION_MAP
    # The converter raises UnhandledElement on unknown justification when it
    # tries to translate; that path is exercised in the end-to-end run.

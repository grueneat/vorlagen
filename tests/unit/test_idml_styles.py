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
            ("SpaceBefore", "space_before"),
            ("SpaceAfter", "space_after"),
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


# ---------------------------------------------------------------------------
# Issue #37 P1 task 5 — always-emit per-paragraph ALIGN (Backport 11 edge case)
# ---------------------------------------------------------------------------

from idml_to_dsl import _walk_story  # noqa: E402

_STYLES_FIXTURE_TEMPLATE = {
    "paragraph_style_map": {
        "ParagraphStyle/$ID/NormalParagraphStyle": "idml/normal",
    },
    "color_map": {"Color/Paper": "White"},
    "paragraph_styles": {
        "ParagraphStyle/$ID/NormalParagraphStyle": {
            "self_id": "ParagraphStyle/$ID/NormalParagraphStyle",
            "applied_font": "Gotham Narrow",
            "font_style": "Book",
            "point_size": 11.0,
            "based_on_self": None,
        },
    },
}


def _story_xml_mixed(justifications: list[str]) -> str:
    psrs = []
    for i, just in enumerate(justifications):
        attr = f' Justification="{just}"' if just else ""
        psrs.append(
            f'<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle"{attr}>'
            f'<CharacterStyleRange><Content>para {i}</Content></CharacterStyleRange>'
            '</ParagraphStyleRange>'
        )
    return (
        '<Story xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging">'
        + "".join(psrs)
        + '</Story>'
    )


def test_mixed_align_emits_explicit_align_per_paragraph():
    """Three PSRs (Center, Left, Right) → every separator emits explicit ALIGN."""
    xml = _story_xml_mixed(["CenterAlign", "LeftAlign", "RightAlign"])
    root = etree.fromstring(xml.encode("utf-8"))
    runs = _walk_story(root, **_STYLES_FIXTURE_TEMPLATE)
    seps = [r for r in runs if r.separator == "para"]
    # Three PSRs → two inter-paragraph separators (first→second, second→third).
    assert len(seps) == 2
    assert seps[0].paragraph_attrs == {"ALIGN": "1"}, seps[0].paragraph_attrs
    assert seps[1].paragraph_attrs == {"ALIGN": "0"}, seps[1].paragraph_attrs


def test_single_psr_leftalign_emits_explicit_trail_align_zero():
    """Single LeftAlign PSR — trail_attrs surfaces ALIGN=0 explicitly.

    For a single-paragraph story, there is no inter-PSR ``Run(separator='para')``
    on which to attach paragraph_attrs. The alignment surfaces via two places
    in ``_emit_pageitem``:
      (1) ``default_style_attrs`` on the TextFrame (the <DefaultStyle/> elt), and
      (2) ``trail_attrs`` from ``_psr_trail_attrs_for_story`` (the <trail/> elt).
    Issue #37 P1 task 5 makes both explicit even when ALIGN=0.
    """
    from idml_to_dsl import _psr_trail_attrs_for_story
    xml = _story_xml_mixed(["LeftAlign"])
    root = etree.fromstring(xml.encode("utf-8"))
    trail = _psr_trail_attrs_for_story(root)
    assert trail is not None
    assert trail.get("ALIGN") == "0", trail


def test_two_psrs_both_center_explicit_align_on_separator():
    """Both PSRs CenterAlign → the inter-PSR separator emits ALIGN=1."""
    xml = _story_xml_mixed(["CenterAlign", "CenterAlign"])
    root = etree.fromstring(xml.encode("utf-8"))
    runs = _walk_story(root, **_STYLES_FIXTURE_TEMPLATE)
    seps = [r for r in runs if r.separator == "para"]
    assert len(seps) == 1  # 2 PSRs → 1 inter-PSR separator
    assert seps[0].paragraph_attrs == {"ALIGN": "1"}


def test_psr_without_justification_inherits_parastyle_align():
    """A PSR without inline Justification picks up its AppliedParagraphStyle's
    resolved justification. With ``justification=FullyJustified`` on the
    ParaStyle, the inherited ALIGN value is 3 on the inter-PSR separator.
    """
    styles_with_just = {
        **_STYLES_FIXTURE_TEMPLATE,
        "paragraph_styles": {
            "ParagraphStyle/$ID/NormalParagraphStyle": {
                **_STYLES_FIXTURE_TEMPLATE["paragraph_styles"][
                    "ParagraphStyle/$ID/NormalParagraphStyle"
                ],
                "justification": "FullyJustified",
            },
        },
    }
    xml = _story_xml_mixed(["", ""])  # 2 PSRs, no inline Justification on either
    root = etree.fromstring(xml.encode("utf-8"))
    runs = _walk_story(root, **styles_with_just)
    seps = [r for r in runs if r.separator == "para"]
    assert len(seps) == 1
    assert seps[0].paragraph_attrs == {"ALIGN": "3"}, seps[0].paragraph_attrs


# ---------------------------------------------------------------------------
# Paragraph spacing — IDML SpaceBefore / SpaceAfter (converter attribute fix).
# ---------------------------------------------------------------------------
def test_space_after_parsed_from_paragraph_style():
    """SpaceAfter on a ParagraphStyle is parsed as a float (points)."""
    xml = _styles_xml(
        {"Self": "ParagraphStyle/Fließtext auf weißem Hintergrund",
         "Name": "Fließtext auf weißem Hintergrund",
         "point_size": 11, "applied_font": "Gotham Narrow",
         "justification": "LeftAlign",
         "space_after": "5.669291338582678"},
    )
    styles = _read_paragraph_styles_from_xml(xml)
    st = styles["ParagraphStyle/Fließtext auf weißem Hintergrund"]
    assert st["space_after"] == 5.669291338582678
    # SpaceBefore absent → None.
    assert st["space_before"] is None


def test_space_before_parsed_from_paragraph_style():
    """SpaceBefore on a ParagraphStyle is parsed as a float (points)."""
    xml = _styles_xml(
        {"Self": "ParagraphStyle/Foo", "Name": "Foo",
         "point_size": 12, "justification": "LeftAlign",
         "space_before": "4"},
    )
    styles = _read_paragraph_styles_from_xml(xml)
    assert styles["ParagraphStyle/Foo"]["space_before"] == 4.0


def test_space_after_inherits_through_based_on_chain():
    """A child style with no SpaceAfter inherits the parent's value."""
    xml = _styles_xml(
        {"Self": "ParagraphStyle/Parent", "Name": "Parent",
         "point_size": 11, "justification": "LeftAlign",
         "space_after": "5.669291338582678"},
        {"Self": "ParagraphStyle/Child", "Name": "Child",
         "based_on": "ParagraphStyle/Parent"},
    )
    styles = _read_paragraph_styles_from_xml(xml)
    resolved = _resolve_paragraph_style(styles["ParagraphStyle/Child"], styles)
    assert resolved["space_after"] == 5.669291338582678


def test_space_after_own_value_overrides_parent():
    """A child's own SpaceAfter takes precedence over the inherited value."""
    xml = _styles_xml(
        {"Self": "ParagraphStyle/Parent", "Name": "Parent",
         "point_size": 11, "justification": "LeftAlign",
         "space_after": "10"},
        {"Self": "ParagraphStyle/Child", "Name": "Child",
         "justification": "LeftAlign", "space_after": "3",
         "based_on": "ParagraphStyle/Parent"},
    )
    styles = _read_paragraph_styles_from_xml(xml)
    resolved = _resolve_paragraph_style(styles["ParagraphStyle/Child"], styles)
    assert resolved["space_after"] == 3.0


def test_ancestor_has_nonzero_detects_explicit_zero_override():
    """A child that sets SpaceAfter=0 over a non-zero parent must be
    detectable as an explicit override — _ancestor_has_nonzero is True so
    the emitter writes space_after_pt=0 (cancels the inherited spacing)
    rather than omitting it (which makes Scribus inherit the parent's air).
    """
    from idml_to_dsl import _ancestor_has_nonzero

    xml = _styles_xml(
        {"Self": "ParagraphStyle/Parent", "Name": "Parent",
         "point_size": 11, "justification": "LeftAlign",
         "space_after": "5.669291338582678"},
        {"Self": "ParagraphStyle/Child", "Name": "Child",
         "justification": "LeftAlign", "space_after": "0",
         "based_on": "ParagraphStyle/Parent"},
    )
    styles = _read_paragraph_styles_from_xml(xml)
    child = styles["ParagraphStyle/Child"]
    # Child's own value is an explicit 0 …
    assert child["space_after"] == 0.0
    # … and an ancestor carries a non-zero value → explicit override.
    assert _ancestor_has_nonzero(child, styles, "space_after") is True
    # A child with no non-zero ancestor is NOT an override.
    parent = styles["ParagraphStyle/Parent"]
    assert _ancestor_has_nonzero(parent, styles, "space_after") is False


# ---------------------------------------------------------------------------
# TextFramePreference + BlendingSetting extraction (converter attribute fix).
# ---------------------------------------------------------------------------
def test_extract_opacity_returns_fraction():
    """BlendingSetting/Opacity=70 → 0.7; Opacity=100 / absent → None."""
    from idml_to_dsl import _extract_opacity

    tf = etree.fromstring(
        b"<TextFrame>"
        b"<TransparencySetting><BlendingSetting Opacity='70'/></TransparencySetting>"
        b"</TextFrame>"
    )
    assert _extract_opacity(tf) == 0.7

    opaque = etree.fromstring(
        b"<TextFrame>"
        b"<TransparencySetting><BlendingSetting Opacity='100'/></TransparencySetting>"
        b"</TextFrame>"
    )
    assert _extract_opacity(opaque) is None

    bare = etree.fromstring(b"<TextFrame/>")
    assert _extract_opacity(bare) is None


def test_extract_textframe_prefs_vertical_justification():
    """VerticalJustification=CenterAlign → vertical_text_align=1; TopAlign → omitted."""
    from idml_to_dsl import _extract_textframe_prefs

    centered = etree.fromstring(
        b"<TextFrame><TextFramePreference VerticalJustification='CenterAlign'/>"
        b"</TextFrame>"
    )
    assert _extract_textframe_prefs(centered)["vertical_text_align"] == 1

    top = etree.fromstring(
        b"<TextFrame><TextFramePreference VerticalJustification='TopAlign'/>"
        b"</TextFrame>"
    )
    assert "vertical_text_align" not in _extract_textframe_prefs(top)


def test_extract_textframe_prefs_multi_column():
    """TextColumnCount=2 → columns=2 + col_gap_pt from TextColumnGutter."""
    from idml_to_dsl import _extract_textframe_prefs

    two_col = etree.fromstring(
        b"<TextFrame><TextFramePreference TextColumnCount='2' "
        b"TextColumnGutter='17.007874015748033'/></TextFrame>"
    )
    prefs = _extract_textframe_prefs(two_col)
    assert prefs["columns"] == 2
    assert abs(prefs["col_gap_pt"] - 17.007874015748033) < 1e-9

    one_col = etree.fromstring(
        b"<TextFrame><TextFramePreference TextColumnCount='1'/></TextFrame>"
    )
    assert "columns" not in _extract_textframe_prefs(one_col)

"""Unit tests for the IDML Story walker (issue 35, task 7).

Pins the rules in PLAN.md task 7:
- Single Content under one ParagraphStyleRange → one Run.
- Br/ → Run(separator="breakline").
- Inter-paragraph → Run(separator="para") with the paragraph_style PARENT.
- Font cascade: CSR with FontStyle and no AppliedFont falls back to its
  paragraph style's resolved font family.
- Unknown <?ACE N?> (N != 7) raises.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from idml_to_dsl import UnhandledElement, _walk_story  # noqa: E402


def _story_xml(inner: str) -> bytes:
    """Build a synthetic Story XML containing the given ParagraphStyleRange XML."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Story Self="ux">'
        f"{inner}"
        "</Story>"
    ).encode("utf-8")


def _styles_dict(slug_overrides=None):
    """Default style/color/slug maps shared by the test cases."""
    return {
        "paragraph_style_map": {
            "ParagraphStyle/Fließtext auf grünem Hintergrund": "idml/fliesstext",
            "ParagraphStyle/Aufzählungen auf grünem Hintergrund": "idml/aufz",
            "ParagraphStyle/$ID/NormalParagraphStyle": "idml/normal",
        },
        "color_map": {
            "Color/Paper": "White",
            "Color/Black": "Black",
            "Color/C=0 M=0 Y=100 K=0": "Gelb",
        },
        "paragraph_styles": {
            "ParagraphStyle/Fließtext auf grünem Hintergrund": {
                "self_id": "ParagraphStyle/Fließtext auf grünem Hintergrund",
                "applied_font": "Gotham Narrow",
                "font_style": "Book",
                "point_size": 11.0,
                "fill_color": "Color/Paper",
                "based_on_self": None,
            },
            "ParagraphStyle/$ID/NormalParagraphStyle": {
                "self_id": "ParagraphStyle/$ID/NormalParagraphStyle",
                "applied_font": "Times",
                "font_style": "Roman",
                "point_size": 12.0,
                "based_on_self": None,
            },
        },
    }


def test_single_content_emits_one_run():
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Fließtext auf grünem Hintergrund">'
        '<CharacterStyleRange><Content>Hello world</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    root = etree.fromstring(xml)
    runs = _walk_story(root, **_styles_dict())
    assert len(runs) == 1
    assert runs[0].text == "Hello world"
    # No separator on a single-paragraph story (Scribus omits trailing <para/>).
    assert runs[0].separator is None


def test_br_emits_breakline_between_content():
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Fließtext auf grünem Hintergrund">'
        '<CharacterStyleRange><Content>A</Content><Br/><Content>B</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    root = etree.fromstring(xml)
    runs = _walk_story(root, **_styles_dict())
    texts = [(r.text, r.separator) for r in runs]
    assert ("A", None) in texts
    assert ("", "breakline") in texts
    assert ("B", None) in texts


def test_multi_paragraph_emits_para_separator():
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Fließtext auf grünem Hintergrund">'
        '<CharacterStyleRange><Content>para1</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle">'
        '<CharacterStyleRange><Content>para2</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    root = etree.fromstring(xml)
    runs = _walk_story(root, **_styles_dict())
    # Expect: para1, separator="para" (with paragraph_style=idml/fliesstext), para2
    assert runs[0].text == "para1"
    sep = next((r for r in runs if r.separator == "para"), None)
    assert sep is not None
    assert sep.paragraph_style == "idml/fliesstext"
    assert any(r.text == "para2" for r in runs)


def test_font_cascade_uses_paragraph_style_applied_font():
    """A CharacterStyleRange with FontStyle but no AppliedFont inherits the
    paragraph style's resolved family."""
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Fließtext auf grünem Hintergrund">'
        '<CharacterStyleRange FontStyle="Black"><Content>bold-ish</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    root = etree.fromstring(xml)
    runs = _walk_story(root, **_styles_dict())
    text_runs = [r for r in runs if r.text == "bold-ish"]
    assert len(text_runs) == 1
    # Paragraph style "Fließtext" cascades AppliedFont="Gotham Narrow"; the
    # CSR's FontStyle="Black" combines into the font name.
    assert text_runs[0].font == "Gotham Narrow Black"


def test_unknown_ace_processing_instruction_raises():
    """ACE 7 is the only allowed processing instruction in v1; ACE N for
    any other N raises."""
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Fließtext auf grünem Hintergrund">'
        '<CharacterStyleRange><Content>x</Content><?ACE 8?><Content>y</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    root = etree.fromstring(xml)
    with pytest.raises(UnhandledElement):
        _walk_story(root, **_styles_dict())


def test_ace_7_preserves_tab_in_content():
    """<?ACE 7?> is the "indent to here" marker; v1 preserves it as a Tab
    character in the next Content run."""
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Fließtext auf grünem Hintergrund">'
        '<CharacterStyleRange><Content>\t•\t</Content><?ACE 7?><Content>bullet item</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    root = etree.fromstring(xml)
    runs = _walk_story(root, **_styles_dict())
    # The ACE 7 indent marker should not eat content; both Contents survive.
    assert any("•" in (r.text or "") for r in runs)
    assert any("bullet item" in (r.text or "") for r in runs)


def test_para_style_font_style_inherited_by_csr_with_no_explicit_font_style():
    """A CSR with NO FontStyle attribute must inherit the paragraph style's
    font_style so that paragraph-level weight overrides are not silently dropped.

    Regression guard for the bug where CSRs without an explicit FontStyle
    attribute emitted font='Gotham Narrow' instead of 'Gotham Narrow Bold'
    when the paragraph style had FontStyle="Bold". This caused GothamNarrow-Bold
    to be absent from preview.pdf even though it is present in baseline.pdf.

    Example: ParagraphStyle/Headline in grünem Kasten has FontStyle="Bold" and
    AppliedFont="Gotham Narrow". Its only CSR carries no FontStyle attribute,
    so the full font name must be "Gotham Narrow Bold"."""
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/HinGK">'
        # CSR has NO FontStyle attribute — must inherit paragraph style's "Bold".
        '<CharacterStyleRange><Content>Headline text</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    root = etree.fromstring(xml)
    d = _styles_dict()
    d["paragraph_style_map"]["ParagraphStyle/HinGK"] = "idml/headline-in-gruenem-kasten"
    d["paragraph_styles"]["ParagraphStyle/HinGK"] = {
        "self_id": "ParagraphStyle/HinGK",
        "applied_font": "Gotham Narrow",
        "font_style": "Bold",
        "point_size": 14.0,
        "fill_color": "Color/Paper",
        "based_on_self": None,
    }
    runs = _walk_story(root, **d)
    text_run = next((r for r in runs if r.text == "Headline text"), None)
    assert text_run is not None
    # The CSR has no explicit FontStyle; the paragraph style's "Bold" must cascade
    # so the font name becomes "Gotham Narrow Bold" (not "Gotham Narrow").
    assert text_run.font == "Gotham Narrow Bold"


def test_csr_explicit_font_style_overrides_para_style_font_style():
    """A CSR with an explicit FontStyle always wins over the paragraph style's
    font_style, even when both differ."""
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Fließtext auf grünem Hintergrund">'
        # Paragraph style says "Book", but CSR explicitly says "Black" — CSR wins.
        '<CharacterStyleRange FontStyle="Black"><Content>lead-word</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    root = etree.fromstring(xml)
    runs = _walk_story(root, **_styles_dict())
    text_run = next((r for r in runs if r.text == "lead-word"), None)
    assert text_run is not None
    # CSR FontStyle="Black" overrides paragraph style's FontStyle="Book".
    assert text_run.font == "Gotham Narrow Black"


def test_font_cascade_via_based_on_chain():
    """CSR FontStyle with no AppliedFont, paragraph style has no AppliedFont
    either but inherits it via the BasedOn chain.  _walk_story must receive
    the *resolved* paragraph_styles dict (BasedOn chain pre-resolved) so that
    ps_family is populated even when it doesn't sit directly on the style.

    Regression guard for the bug where _emit_paragraph_styles stored raw
    (unresolved) styles in ctx.paragraph_styles, causing ps_family=None for
    styles that inherit their font via BasedOn."""
    xml = _story_xml(
        # Aufzählungen has no AppliedFont of its own; it inherits from Fließtext.
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Aufzählungen auf grünem Hintergrund">'
        '<CharacterStyleRange FontStyle="Black"><Content>lead-word </Content></CharacterStyleRange>'
        '<CharacterStyleRange><Content>rest of text</Content></CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    root = etree.fromstring(xml)
    # Simulate ctx.paragraph_styles built with PRE-RESOLVED styles (as fixed):
    # Aufzählungen inherits applied_font from Fließtext via BasedOn.
    resolved_paragraph_styles = {
        "ParagraphStyle/Fließtext auf grünem Hintergrund": {
            "self_id": "ParagraphStyle/Fließtext auf grünem Hintergrund",
            "applied_font": "Gotham Narrow",
            "font_style": "Book",
            "point_size": 11.0,
            "fill_color": "Color/Paper",
            "based_on_self": None,
        },
        "ParagraphStyle/Aufzählungen auf grünem Hintergrund": {
            "self_id": "ParagraphStyle/Aufzählungen auf grünem Hintergrund",
            # No applied_font here — only set on the parent (Fließtext).
            # After BasedOn resolution this becomes "Gotham Narrow".
            "applied_font": "Gotham Narrow",  # resolved
            "font_style": "Book",             # resolved
            "point_size": 11.0,
            "fill_color": "Color/Paper",
            "based_on_self": "ParagraphStyle/Fließtext auf grünem Hintergrund",
        },
    }
    d = _styles_dict()
    d["paragraph_styles"] = resolved_paragraph_styles
    d["paragraph_style_map"]["ParagraphStyle/Aufzählungen auf grünem Hintergrund"] = "idml/aufz"
    runs = _walk_story(root, **d)
    lead = next((r for r in runs if r.text == "lead-word "), None)
    assert lead is not None
    # With resolved styles, the CSR's "Black" style combines with the inherited
    # family "Gotham Narrow" → "Gotham Narrow Black".
    assert lead.font == "Gotham Narrow Black"

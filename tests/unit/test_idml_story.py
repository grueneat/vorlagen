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

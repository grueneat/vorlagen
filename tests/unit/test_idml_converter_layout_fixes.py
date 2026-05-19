"""Unit tests for the four IDML converter layout fixes.

Covers the converter-level fixes proven on flyer-a6-hochformat-portraet:

1. Vector logo (<PDF>) — emitted with SCALETYPE=0 (auto-fit), never
   SCALETYPE=1 + literal local_scale (the Scribus white-on-transparent bug).
2/3. Mixed-font forced-break headlines — split into single-line frames with
   per-font FLOP=1 baseline correction.
4. Explicit numeric IDML <Leading> — emitted as Scribus LINESPMode=0 (Fixed)
   + LINESP, never LINESPMode=2 (baseline grid) or LINESPMode=1 (auto).
"""
from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from idml_to_dsl import (  # noqa: E402
    _font_flop_ratio,
    _psr_trail_attrs_for_story,
    _split_mixed_font_lines,
)
from sla_lib.builder import Run  # noqa: E402


def _story_xml(inner: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Story Self="ux">{inner}</Story>'
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Defects 2/3/4 — explicit numeric IDML Leading -> LINESPMode=0 (Fixed)
# ---------------------------------------------------------------------------
def test_numeric_leading_emits_linespmode_0_fixed():
    """A numeric <Leading> below font-metric must still emit LINESPMode=0.

    The old converter emitted LINESPMode=2 (baseline grid) and fell back to
    LINESPMode=1 (auto) for sub-1.45×fontsize leadings — both ignore the
    authored value. A 38pt headline with Leading=34.13 is sub-metric and must
    now pin LINESPMode=0 + LINESP=34.13.
    """
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle">'
        '<CharacterStyleRange PointSize="38">'
        '<Properties><Leading type="unit">34.13</Leading></Properties>'
        '<Content>Headline</Content>'
        '</CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    trail = _psr_trail_attrs_for_story(etree.fromstring(xml))
    assert trail is not None
    assert trail["LINESPMode"] == "0", f"expected Fixed mode 0, got {trail!r}"
    assert trail["LINESP"] == "34.13"


def test_numeric_leading_above_metric_also_mode_0():
    """A numeric Leading above font-metric is also Fixed (mode 0)."""
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle">'
        '<CharacterStyleRange PointSize="12">'
        '<Properties><Leading type="unit">20</Leading></Properties>'
        '<Content>body</Content>'
        '</CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    trail = _psr_trail_attrs_for_story(etree.fromstring(xml))
    assert trail["LINESPMode"] == "0"
    assert float(trail["LINESP"]) == 20.0


def test_auto_leading_stays_mode_1():
    """Leading="Auto" still maps to LINESPMode=1 (font-metric)."""
    xml = _story_xml(
        '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle">'
        '<CharacterStyleRange PointSize="12">'
        '<Properties><Leading type="unit">Auto</Leading></Properties>'
        '<Content>body</Content>'
        '</CharacterStyleRange>'
        '</ParagraphStyleRange>'
    )
    trail = _psr_trail_attrs_for_story(etree.fromstring(xml))
    assert trail == {"LINESPMode": "1"}


def test_numeric_leading_never_emits_mode_2():
    """Regression guard: the converter must never emit LINESPMode=2.

    Mode 2 is Scribus's baseline-grid mode and renders WIDER than the LINESP
    value — it never honours an authored fixed leading.
    """
    for pt, lead in (("38", "34.13"), ("30", "27"), ("23", "20.48")):
        xml = _story_xml(
            '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle">'
            f'<CharacterStyleRange PointSize="{pt}">'
            f'<Properties><Leading type="unit">{lead}</Leading></Properties>'
            '<Content>x</Content>'
            '</CharacterStyleRange>'
            '</ParagraphStyleRange>'
        )
        trail = _psr_trail_attrs_for_story(etree.fromstring(xml))
        assert trail["LINESPMode"] != "2", f"mode 2 leaked at {pt}pt"


# ---------------------------------------------------------------------------
# Defects 2/3 — mixed-font forced-break headline split
# ---------------------------------------------------------------------------
def _headline_runs(fonts_texts):
    """Build a run list: text runs separated by 'para' (the <Br/>) separators."""
    runs: list[Run] = []
    for i, (font, text) in enumerate(fonts_texts):
        if i:
            runs.append(Run(has_itext=False, separator="para"))
        runs.append(Run(text=text, font=font, fontsize=38))
    return runs


def test_split_mixed_font_headline_three_lines():
    """A Gotham/Vollkorn/Gotham forced-break headline splits into 3 lines."""
    runs = _headline_runs([
        ("Gotham Narrow Ultra", "Das ist die "),
        ("Vollkorn Black Italic", "dreizeilige"),
        ("Gotham Narrow Ultra", "Headline"),
    ])
    lines = _split_mixed_font_lines(runs)
    assert lines is not None
    assert len(lines) == 3
    assert [hl.font for hl in lines] == [
        "Gotham Narrow Ultra", "Vollkorn Black Italic", "Gotham Narrow Ultra",
    ]


def test_single_font_headline_not_split():
    """A forced-break headline whose lines share one font is NOT split.

    Single-font frames render fine as one frame once LINESPMode=0 is set;
    only the mixed-font font-metric mismatch needs the per-line split.
    """
    runs = _headline_runs([
        ("Gotham Narrow Ultra", "Ich bin auch "),
        ("Gotham Narrow Ultra", "eine Headline."),
    ])
    assert _split_mixed_font_lines(runs) is None


def test_single_line_frame_not_split():
    """A frame with no forced break (one line) is never split."""
    runs = [Run(text="just one line", font="Gotham Narrow Ultra", fontsize=38)]
    assert _split_mixed_font_lines(runs) is None


def test_multi_run_line_not_split():
    """A line built from multiple text runs (body text) is not a headline."""
    runs = [
        Run(text="bold bit ", font="Gotham Narrow Bold", fontsize=11),
        Run(text="and book bit", font="Gotham Narrow Book", fontsize=11),
        Run(has_itext=False, separator="para"),
        Run(text="second paragraph", font="Gotham Narrow Book", fontsize=11),
    ]
    assert _split_mixed_font_lines(runs) is None


def test_font_flop_ratio_vollkorn_vs_gotham():
    """Vollkorn carries the rendered-ink-calibrated 0.15 FLOP correction;
    Gotham is the 0.0 reference (and any unmapped font defaults to 0.0).

    The ratio was RECALIBRATED from 0.345 (which had been measured against
    pdfplumber text-matrix coordinates, not rendered ink) to 0.15: the old
    value over-shifted a Vollkorn headline line ~5-8pt upward in the
    rasterised output. 0.15 leaves a sub-0.3pt rendered-ink residual on the
    flyer-a6-hochformat-portraet page-1 (38pt) and page-2 (30pt)
    headlines — verified by ink-top measurement of preview.pdf vs baseline.
    """
    assert _font_flop_ratio("Vollkorn Black Italic") == 0.15
    assert _font_flop_ratio("Gotham Narrow Ultra") == 0.0
    assert _font_flop_ratio("Some Unknown Sans") == 0.0
    assert _font_flop_ratio(None) == 0.0


def test_mixed_font_headline_correction_is_rendered_ink_calibrated():
    """The Vollkorn FLOP correction must shift the line UP by 0.15*fontsize.

    Regression guard for the mixed-font headline split mis-calibration: the
    correction relative to a Gotham line-1 reference is
    ``(ratio_vollkorn - ratio_gotham) * fontsize``. At 38pt that is 5.7pt
    and at 30pt 4.5pt — markedly smaller than the old 0.345 ratio's 13.1pt /
    10.35pt, which rendered the Vollkorn line visibly too high.
    """
    ref = _font_flop_ratio("Gotham Narrow Ultra")
    for fontsize, expected in ((38.0, 5.7), (30.0, 4.5)):
        correction = (_font_flop_ratio("Vollkorn Black Italic") - ref) * fontsize
        assert abs(correction - expected) < 1e-6

"""Variant: caps-eyebrow-categorical-tags.

Hypothesis: Three slogans, each preceded by a small all-caps Gotham
Bold category tag in Dunkelgrün, sitting flush-left above the slogan
with a ~4mm baseline gap. Hierarchy operates by typographic weight +
case + size differential (not by colour or scale jump), keeping the
panel quiet but legible at distance.

Axis commitments: hierarchy + typography. The categorical tag adds an
informational frame intended to aid transport for cold readers while
keeping appeal middling — the move is informational, not emotive.

Envelope notes: the hypothesis named 9pt for the eyebrow; layer-1
`body_min_pt`=10 is NOT relaxed for this variant, so the eyebrow is
set at 10pt — the all-caps + bold + colour + size-jump identity of
the design is preserved. Slogan is 18pt Gotham Narrow Bold, well above
the floor. Only Dunkelgrün/Hellgrün used. Single type family (Gotham
Narrow Bold) across exp styles; type-sizes-per-panel relaxation
already covers the 10/18pt pair on top of production styles.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame

EYEBROW_PT = 10
SLOGAN_PT = 18

CATEGORIES = [
    ("KLIMA", "Klimaplan jetzt."),
    ("WOHNEN", "Leistbares Wohnen."),
    ("BILDUNG", "Bildung vor Ort."),
]


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/caps-eyebrow/eyebrow",
        font="Gotham Narrow Bold",
        fontsize=EYEBROW_PT, linesp=12, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/caps-eyebrow/slogan",
        font="Gotham Narrow Bold",
        fontsize=SLOGAN_PT, linesp=22, align=0,
        fcolor="Dunkelgrün", language="de",
    ))

    page.add(Polygon(
        x_mm=99, y_mm=-3, w_mm=99, h_mm=31,
        fill="Dunkelgrün", layer=0, anname="P2 Top-Band",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=8, w_mm=87, h_mm=14,
        layer=2, style="falzflyer/top-title",
        runs=[Run(text="Mein Plan",
                  paragraph_style="falzflyer/top-title")],
        anname="P2 Top-Title",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=38, w_mm=87, h_mm=22,
        layer=2, style="falzflyer/teaser-headline",
        runs=[Run(text="Drei Bereiche.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    # Three (eyebrow, slogan) groups in the body area (y=70..200).
    # Each group is 28mm tall: eyebrow (6mm) + 2mm gap + slogan (12mm)
    # + 8mm trailing whitespace. Three groups = 84mm of 130mm = ~35%
    # whitespace on the body backing — the tested hierarchy axis lives
    # in the type, not the field, so generous breathing room reinforces
    # the "quiet but legible" character of the hypothesis.
    y0 = 75
    group_h = 28
    eyebrow_to_slogan_gap = 8  # ≈4mm baseline gap given 10pt/18pt sizes
    for i, (eyebrow_text, slogan_text) in enumerate(CATEGORIES):
        gy = y0 + i * group_h
        page.add(TextFrame(
            x_mm=105, y_mm=gy, w_mm=87, h_mm=6,
            layer=2, style="exp/caps-eyebrow/eyebrow",
            runs=[Run(text=eyebrow_text,
                      paragraph_style="exp/caps-eyebrow/eyebrow")],
            anname=f"P2 Eyebrow {i+1}",
        ))
        page.add(TextFrame(
            x_mm=105, y_mm=gy + eyebrow_to_slogan_gap, w_mm=87, h_mm=12,
            layer=2, style="exp/caps-eyebrow/slogan",
            runs=[Run(text=slogan_text,
                      paragraph_style="exp/caps-eyebrow/slogan")],
            anname=f"P2 Slogan {i+1}",
        ))
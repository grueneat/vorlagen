"""Variant: editorial-left-column-rules.

Hypothesis: Asymmetric editorial composition — body content anchored
in a narrow left column with thin Dunkelgrün rules between items, the
right portion of the body backing held as deliberate whitespace. The
asymmetry creates tension and frames the void as a compositional
element rather than residual margin.

Axis commitments: primary=asymmetry (column = 45mm of the 87mm body
width, ~52% column / ~48% sustained right gutter), secondary=whitespace-
strategy (the empty right band is one continuous vertical void, not
distributed slack). Tested axis label per envelope: density+form.

Distinct from dunkelgrun-rules-between-items-v2: that variant used a
55mm column with 3 items and rules confined to that width — closer to
balanced. This one pushes the asymmetry harder: narrower column,
shorter rules, four items so the rule rhythm reads as a structured
list rather than three large statements, and the right gutter spans
the full body height as a sustained negative shape.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame

COLUMN_X_MM = 105
COLUMN_W_MM = 45
COLUMN_Y0_MM = 75
ROW_H_MM = 22


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/leftcol/item",
        font="Gotham Narrow Bold",
        fontsize=17, linesp=21, align=0,
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
        runs=[Run(text="Vier Vorhaben.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    items = [
        "Klimaplan jetzt.",
        "Leistbares Wohnen.",
        "Bildung vor Ort.",
        "Bürgernähe.",
    ]
    for i, text in enumerate(items):
        y = COLUMN_Y0_MM + i * ROW_H_MM
        page.add(TextFrame(
            x_mm=COLUMN_X_MM, y_mm=y, w_mm=COLUMN_W_MM, h_mm=14,
            layer=2, style="exp/leftcol/item",
            runs=[Run(text=text,
                      paragraph_style="exp/leftcol/item")],
            anname=f"P2 Item {i+1}",
        ))
        if i < len(items) - 1:
            page.add(Polygon(
                x_mm=COLUMN_X_MM, y_mm=y + ROW_H_MM - 4,
                w_mm=COLUMN_W_MM, h_mm=0.4,
                fill="Dunkelgrün", layer=0,
                anname=f"P2 Rule {i+1}",
            ))
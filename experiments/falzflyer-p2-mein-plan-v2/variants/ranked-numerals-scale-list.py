"""Variant: ranked-numerals-scale-list.

Hypothesis: Keep all five agenda items but make the reading order
unmistakable through oversized numerals that step down from 1 to 5.
The first numeral alone takes a non-green accent, so hierarchy comes
from both scale and color without reducing the information volume.

Axis commitments: hierarchy, typography, accent-strategy.

Implementation notes:
- Numerals use a descending 60/44/32/24/18pt scale, making the rank
  visually obvious from the first glance.
- Only the #1 numeral uses Magenta; all other text stays Dunkelgrün.
- Five one-line items preserve breadth while staying inside the P2 body
  area and within the brand color set.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame

RANK_SIZES_PT = [60, 44, 32, 24, 18]
ROW_HEIGHTS_MM = [30, 26, 22, 18, 16]
ITEM_BODY_PT = 14


def render_p2(doc, page) -> None:
    for i, size in enumerate(RANK_SIZES_PT, start=1):
        doc.add_para_style(ParaStyle(
            name=f"exp/ranked/numeral-{i}",
            font="Vollkorn Black Italic",
            fontsize=size,
            linesp=int(size * 1.0),
            align=0,
            fcolor="Magenta" if i == 1 else "Dunkelgrün",
            language="de",
        ))
    doc.add_para_style(ParaStyle(
        name="exp/ranked/item",
        font="Gotham Narrow Bold",
        fontsize=ITEM_BODY_PT,
        linesp=int(ITEM_BODY_PT * 1.2),
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))

    page.add(Polygon(
        x_mm=99, y_mm=-3, w_mm=99, h_mm=31,
        fill="Dunkelgrün", layer=0, anname="P2 Top-Band",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=8, w_mm=87, h_mm=14,
        layer=2, style="falzflyer/top-title",
        runs=[Run(text="Mein Plan", paragraph_style="falzflyer/top-title")],
        anname="P2 Top-Title",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=38, w_mm=87, h_mm=22,
        layer=2, style="falzflyer/teaser-headline",
        runs=[Run(
            text="Was zuerst zählt",
            paragraph_style="falzflyer/teaser-headline",
        )],
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
        "Lokale Wirtschaft.",
        "Bürgernähe statt Klüngel.",
    ]

    y = 72
    for i, (text, row_h) in enumerate(zip(items, ROW_HEIGHTS_MM), start=1):
        page.add(TextFrame(
            x_mm=105, y_mm=y, w_mm=22, h_mm=row_h,
            layer=2, style=f"exp/ranked/numeral-{i}",
            runs=[Run(text=str(i), paragraph_style=f"exp/ranked/numeral-{i}")],
            anname=f"P2 Numeral {i}",
        ))
        page.add(TextFrame(
            x_mm=129, y_mm=y + max(0, (row_h - 14) // 2), w_mm=63, h_mm=14,
            layer=2, style="exp/ranked/item",
            runs=[Run(text=text, paragraph_style="exp/ranked/item")],
            anname=f"P2 Item {i}",
        ))
        y += row_h
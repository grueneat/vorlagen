"""Variant: numbered-priority-list-v2 (concept retained from v1).

Hypothesis: Numbered 1..5 priority list, rank-weighted typographic scale.
Axis commitments (per PLAN.md R6): primary=density, secondary=form,
tertiary=hierarchy. The eye lands on #1 first by design — not the v1
constant-28pt failure mode.

v1 broken: all 5 numerals at constant 28pt (no rank scaling). v2 fix:
36/30/24/20/16pt geometric series — smallest still ≥10pt body floor.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame

RANK_SIZES_PT = [36, 30, 24, 20, 16]
ITEM_BODY_PT = 14


def render_p2(doc, page) -> None:
    for size in RANK_SIZES_PT:
        doc.add_para_style(ParaStyle(
            name=f"exp/numbered/numeral-{size}",
            font="Vollkorn Black Italic",
            fontsize=size, linesp=int(size * 1.1), align=0,
            fcolor="Dunkelgrün", language="de",
        ))
    doc.add_para_style(ParaStyle(
        name="exp/numbered/text",
        font="Gotham Narrow Bold",
        fontsize=ITEM_BODY_PT, linesp=int(ITEM_BODY_PT * 1.2), align=0,
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
        runs=[Run(text="In dieser Reihenfolge",
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
        "Lokale Wirtschaft.",
        "Bürgernähe statt Klüngel.",
    ]
    # Row heights track the weighted scale so the largest numeral has
    # the largest row. Sum keeps total content < 130mm available below
    # y=70 to stay within the body backing.
    row_heights_mm = [28, 24, 22, 20, 18]  # sum = 112mm, fits 130mm
    y = 70
    for i, (text, numeral_pt, row_h) in enumerate(zip(items, RANK_SIZES_PT, row_heights_mm)):
        page.add(TextFrame(
            x_mm=105, y_mm=y, w_mm=20, h_mm=row_h - 2,
            layer=2, style=f"exp/numbered/numeral-{numeral_pt}",
            runs=[Run(text=str(i + 1),
                      paragraph_style=f"exp/numbered/numeral-{numeral_pt}")],
            anname=f"P2 Numeral {i+1}",
        ))
        page.add(TextFrame(
            x_mm=126, y_mm=y + (row_h - 8) // 2, w_mm=66, h_mm=14,
            layer=2, style="exp/numbered/text",
            runs=[Run(text=text,
                      paragraph_style="exp/numbered/text")],
            anname=f"P2 Item {i+1}",
        ))
        if i < len(items) - 1:
            page.add(Polygon(
                x_mm=105, y_mm=y + row_h - 2, w_mm=87, h_mm=0.4,
                fill="Dunkelgrün", layer=0,
                anname=f"P2 Rule {i+1}",
            ))
        y += row_h

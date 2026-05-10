"""Variant: numbered-priority-list.

Hypothesis: Numbered 1..5 priority list with rule between
Axes: hierarchy, typography
Rationale: Number each slogan and add thin Dunkelgrün rules between
rows to force a sequence reading. Explicit ordinal hierarchy.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/numbered/numeral",
        font="Vollkorn Black Italic",
        fontsize=28, linesp=30, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/numbered/text",
        font="Gotham Narrow Bold",
        fontsize=16, linesp=20, align=0,
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
    y0 = 70
    row_h = 26
    for i, text in enumerate(items):
        y = y0 + i * row_h
        page.add(TextFrame(
            x_mm=105, y_mm=y, w_mm=14, h_mm=22,
            layer=2, style="exp/numbered/numeral",
            runs=[Run(text=str(i + 1),
                      paragraph_style="exp/numbered/numeral")],
            anname=f"P2 Numeral {i+1}",
        ))
        page.add(TextFrame(
            x_mm=120, y_mm=y + 4, w_mm=72, h_mm=18,
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

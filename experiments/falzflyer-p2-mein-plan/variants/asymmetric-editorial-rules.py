"""Variant: asymmetric-editorial-rules.

Hypothesis: Asymmetric balance, items left-aligned with rules
Axes: asymmetry, whitespace-strategy
Rationale: Replace centered list with left-aligned items separated by
thin Dunkelgrün rules. Editorial composition with intentional right-
column whitespace.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/editorial/item",
        font="Gotham Narrow Bold",
        fontsize=18, linesp=22, align=0,
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
        runs=[Run(text="Was ich für Mödling will",
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
    # Left-aligned items, items occupy left two-thirds (x=105..160 of
    # the 99-198 panel), thin Dunkelgrün rules between them. Right
    # third (x=160..195) is intentional whitespace.
    y0 = 75
    row_h = 22
    for i, text in enumerate(items):
        y = y0 + i * row_h
        page.add(TextFrame(
            x_mm=105, y_mm=y, w_mm=55, h_mm=14,
            layer=2, style="exp/editorial/item",
            runs=[Run(text=text,
                      paragraph_style="exp/editorial/item")],
            anname=f"P2 Item {i+1}",
        ))
        if i < len(items) - 1:
            # 0.4mm thin rule below each row except the last.
            page.add(Polygon(
                x_mm=105, y_mm=y + row_h - 4, w_mm=55, h_mm=0.4,
                fill="Dunkelgrün", layer=0,
                anname=f"P2 Rule {i+1}",
            ))

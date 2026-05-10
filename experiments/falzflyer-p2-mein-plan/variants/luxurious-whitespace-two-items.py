"""Variant: luxurious-whitespace-two-items.

Hypothesis: Reduce to two items with luxurious whitespace
Axes: whitespace-strategy, density
Rationale: Strip to two items — one current Mödling priority, one
future ambition — and let Hellgrün whitespace do the work. Forces a
slow read.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/whitespace/eyebrow",
        font="Gotham Narrow Bold",
        fontsize=10, linesp=12, align=1,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/whitespace/item",
        font="Gotham Narrow Bold",
        fontsize=24, linesp=30, align=1,
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
        runs=[Run(text="Zwei Versprechen",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=88, w_mm=87, h_mm=8,
        layer=2, style="exp/whitespace/eyebrow",
        runs=[Run(text="HEUTE",
                  paragraph_style="exp/whitespace/eyebrow")],
        anname="P2 Eyebrow-1",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=98, w_mm=87, h_mm=20,
        layer=2, style="exp/whitespace/item",
        runs=[Run(text="Klimaplan jetzt.",
                  paragraph_style="exp/whitespace/item")],
        anname="P2 Item-1",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=148, w_mm=87, h_mm=8,
        layer=2, style="exp/whitespace/eyebrow",
        runs=[Run(text="MORGEN",
                  paragraph_style="exp/whitespace/eyebrow")],
        anname="P2 Eyebrow-2",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=158, w_mm=87, h_mm=20,
        layer=2, style="exp/whitespace/item",
        runs=[Run(text="Bürgernähe — immer.",
                  paragraph_style="exp/whitespace/item")],
        anname="P2 Item-2",
    ))

"""Variant: staggered-block-accent.

Hypothesis: Staggered Dunkelgrün accent blocks behind alternating items
Axes: accent-strategy, asymmetry
Rationale: Each odd-indexed slogan sits on a small Dunkelgrün block
that breaks the Hellgrün backing. Visual rhythm + accent without color
swap.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/staggered/dark",
        font="Gotham Narrow Bold",
        fontsize=18, linesp=22, align=1,
        fcolor="White", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/staggered/light",
        font="Gotham Narrow Bold",
        fontsize=18, linesp=22, align=1,
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
    y0 = 75
    row_h = 26
    for i, text in enumerate(items):
        y = y0 + i * row_h
        if i % 2 == 0:
            # Dunkelgrün block, white text. Staggered: even rows on
            # the right half, odd on the left.
            page.add(Polygon(
                x_mm=105, y_mm=y, w_mm=87, h_mm=22,
                fill="Dunkelgrün", layer=0,
                anname=f"P2 Block {i+1}",
            ))
            page.add(TextFrame(
                x_mm=105, y_mm=y + 2, w_mm=87, h_mm=18,
                layer=2, style="exp/staggered/dark",
                runs=[Run(text=text,
                          paragraph_style="exp/staggered/dark")],
                anname=f"P2 Item {i+1}",
            ))
        else:
            # Plain Hellgrün, dark text.
            page.add(TextFrame(
                x_mm=105, y_mm=y + 2, w_mm=87, h_mm=18,
                layer=2, style="exp/staggered/light",
                runs=[Run(text=text,
                          paragraph_style="exp/staggered/light")],
                anname=f"P2 Item {i+1}",
            ))

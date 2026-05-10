"""Variant: vollkorn-italic-cornerstone.

Hypothesis: Vollkorn Italic for emphasized line
Axes: typography, hierarchy
Rationale: Use Vollkorn italic for the cornerstone slogan to introduce
typographic contrast rather than relying on color or accent panels.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/vollkorn/cornerstone",
        font="Vollkorn Black Italic",
        fontsize=24, linesp=28, align=1,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/vollkorn/follower",
        font="Gotham Narrow Book",
        fontsize=14, linesp=18, align=1,
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

    page.add(TextFrame(
        x_mm=105, y_mm=80, w_mm=87, h_mm=44,
        layer=2, style="exp/vollkorn/cornerstone",
        runs=[Run(text="Klimaplan jetzt.",
                  paragraph_style="exp/vollkorn/cornerstone")],
        anname="P2 Cornerstone",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=130, w_mm=87, h_mm=80,
        layer=2, style="exp/vollkorn/follower",
        runs=[
            Run(text="Leistbares Wohnen.", separator="para",
                paragraph_style="exp/vollkorn/follower"),
            Run(text="Bildung vor Ort.", separator="para",
                paragraph_style="exp/vollkorn/follower"),
            Run(text="Lokale Wirtschaft.", separator="para",
                paragraph_style="exp/vollkorn/follower"),
            Run(text="Bürgernähe statt Klüngel.",
                paragraph_style="exp/vollkorn/follower"),
        ],
        anname="P2 Followers",
    ))

"""Variant: vollkorn-italic-cornerstone-jump.

Hypothesis: A single cornerstone phrase in registered Vollkorn Black
Italic at 36pt establishes the panel's voice, while three Gotham 14pt
supporting lines keep the headline/body jump at a real 2.57x.

The panel keeps the production P2 shell verbatim, then commits to one
editorial statement plus three concise priorities beneath it.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/cornerstone/statement",
        font="Vollkorn Black Italic",
        fontsize=36, linesp=38, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/cornerstone/support",
        font="Gotham Narrow Book",
        fontsize=14, linesp=18, align=0,
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
        runs=[Run(text="Wofür ich bleibe.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=72, w_mm=87, h_mm=44,
        layer=2, style="exp/cornerstone/statement",
        runs=[Run(text="Ich bleibe dran.",
                  paragraph_style="exp/cornerstone/statement")],
        anname="P2 Cornerstone",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=136, w_mm=72, h_mm=58,
        layer=2, style="exp/cornerstone/support",
        runs=[
            Run(text="Beim Klimaplan.", separator="para",
                paragraph_style="exp/cornerstone/support"),
            Run(text="Beim leistbaren Wohnen.", separator="para",
                paragraph_style="exp/cornerstone/support"),
            Run(text="Beim Zuhören vor Ort.",
                paragraph_style="exp/cornerstone/support"),
        ],
        anname="P2 Support-Items",
    ))
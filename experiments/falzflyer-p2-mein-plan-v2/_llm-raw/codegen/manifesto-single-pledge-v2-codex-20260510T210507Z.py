"""Variant: manifesto-single-pledge-v2.

Hypothesis: collapse the peer list into one dominant pledge set in
Vollkorn Black Italic, with a short Gotham support line beneath it.
The panel should read as a single political promise rather than a
checklist, while preserving the production P2 band and card geometry.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/manifesto/pledge",
        font="Vollkorn Black Italic",
        fontsize=30, linesp=33, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/manifesto/support",
        font="Gotham Narrow Bold",
        fontsize=13, linesp=16, align=0,
        fcolor="Dunkelgrün", language="de",
    ))

    page.add(Polygon(
        x_mm=99, y_mm=-3, w_mm=99, h_mm=31,
        fill="Dunkelgrün", layer=0, anname="P2 Top-Band",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=8, w_mm=87, h_mm=14,
        layer=2, style="falzflyer/top-title",
        runs=[Run(
            text="Mein Plan",
            paragraph_style="falzflyer/top-title",
        )],
        anname="P2 Top-Title",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=38, w_mm=87, h_mm=22,
        layer=2, style="falzflyer/teaser-headline",
        runs=[Run(
            text="Ein Versprechen.",
            paragraph_style="falzflyer/teaser-headline",
        )],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=74, w_mm=87, h_mm=72,
        layer=2, style="exp/manifesto/pledge",
        runs=[Run(
            text="Ich verspreche: Mödling wird klimafit, leistbar und nah bei den Menschen.",
            paragraph_style="exp/manifesto/pledge",
        )],
        anname="P2 Manifesto-Pledge",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=162, w_mm=72, h_mm=18,
        layer=2, style="exp/manifesto/support",
        runs=[Run(
            text="Konzentriert. Verbindlich. Für die ganze Stadt.",
            paragraph_style="exp/manifesto/support",
        )],
        anname="P2 Support-Line",
    ))

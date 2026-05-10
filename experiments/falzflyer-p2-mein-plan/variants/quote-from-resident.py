"""Variant: quote-from-resident.

Hypothesis: Lead with a constituent quote, candidate's reply below
Axes: voice-formality, density
Rationale: Replace abstract slogans with one verbatim Mödling resident
quote — a problem statement — and a one-line response from Maria.
Editorial reportage register, not campaign manifesto.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/quote/quote",
        font="Vollkorn Black Italic",
        fontsize=20, linesp=24, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/quote/attrib",
        font="Gotham Narrow Bold",
        fontsize=10, linesp=13, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/quote/reply",
        font="Gotham Narrow Book",
        fontsize=13, linesp=17, align=0,
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
        runs=[Run(text="Was Mödling sagt",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=72, w_mm=87, h_mm=70,
        layer=2, style="exp/quote/quote",
        runs=[Run(text=("„Ich habe lange gewartet, dass jemand "
                        "endlich beim Klima konkret wird — "
                        "nicht nur Plakate.\""),
                  paragraph_style="exp/quote/quote")],
        anname="P2 Quote",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=146, w_mm=87, h_mm=8,
        layer=2, style="exp/quote/attrib",
        runs=[Run(text="— Helga K., Vorderbrühl",
                  paragraph_style="exp/quote/attrib")],
        anname="P2 Quote-Attribution",
    ))

    # Reply
    page.add(TextFrame(
        x_mm=105, y_mm=168, w_mm=87, h_mm=40,
        layer=2, style="exp/quote/reply",
        runs=[Run(text=("Ich hab' verstanden, Helga. Klimaplan in "
                        "100 Tagen — keine Plakate. Maßnahmen."),
                  paragraph_style="exp/quote/reply")],
        anname="P2 Reply",
    ))

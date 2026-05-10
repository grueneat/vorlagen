"""Variant: resident-quote-then-pledge.

Hypothesis: open with a short resident-style quote as the problem
statement, then answer it with one concrete pledge and compact support
text. The panel behaves like a brief dialogue rather than a slogan
sheet, testing a more grounded and accountable register.

Axis commitments: voice-formality, hierarchy.
Tested axis: density+form.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/quote/voice",
        font="Vollkorn Black Italic",
        fontsize=24, linesp=28, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/quote/pledge",
        font="Gotham Narrow Bold",
        fontsize=18, linesp=22, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/quote/support",
        font="Gotham Narrow Book",
        fontsize=12, linesp=15, align=0,
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
            text="Erst zuhoren. Dann zusagen.",
            paragraph_style="falzflyer/teaser-headline",
        )],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrun", layer=0, anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=74, w_mm=70, h_mm=34,
        layer=2, style="exp/quote/voice",
        runs=[Run(
            text='"Der Bus passt nie zu meinem Alltag."',
            paragraph_style="exp/quote/voice",
        )],
        anname="P2 Resident-Quote",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=122, w_mm=78, h_mm=34,
        layer=2, style="exp/quote/pledge",
        runs=[Run(
            text="Ich verspreche verlassliche Wege: "
                 "mehr Takt, sichere Schulwege, klare Anschlusse.",
            paragraph_style="exp/quote/pledge",
        )],
        anname="P2 Pledge",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=161, w_mm=74, h_mm=30,
        layer=2, style="exp/quote/support",
        runs=[Run(
            text="Mit der Gemeinde abgestimmt, fur Pendler:innen, "
                 "Familien und alle, die taglich auf den Nahverkehr zahlen.",
            paragraph_style="exp/quote/support",
        )],
        anname="P2 Support",
    ))

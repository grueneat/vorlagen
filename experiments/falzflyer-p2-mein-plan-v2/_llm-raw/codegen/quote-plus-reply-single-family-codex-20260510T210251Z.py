"""Variant: quote-plus-reply-single-family.

Hypothesis: Open with a resident quote, then answer it with a candidate
reply using only the Gotham family so the panel stays inside the
two-family floor. The intended effect is listener-first hierarchy:
problem voiced first, response second.

Implementation note: the shared font registry does not include a safe
Gotham italic face. To stay inside the enforced font-family floor and
avoid fallback rendering, the quote uses `Gotham Narrow Book` as the
closest registered Gotham voice; the reply uses `Gotham Narrow Bold`
at 1.4x the quote size.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/quote/quote",
        font="Gotham Narrow Book",
        fontsize=14,
        linesp=17,
        align=0,
        fcolor="Dunkelgruen" if False else "Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/quote/reply",
        font="Gotham Narrow Bold",
        fontsize=20,
        linesp=24,
        align=0,
        fcolor="Dunkelgruen" if False else "Dunkelgrün",
        language="de",
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
            text="Erst die Sorge, dann die Antwort.",
            paragraph_style="falzflyer/teaser-headline",
        )],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=76, w_mm=62, h_mm=26,
        layer=2, style="exp/quote/quote",
        runs=[Run(
            text='"Ich will, dass meine Kinder hier wohnen koennen."',
            paragraph_style="exp/quote/quote",
        )],
        anname="P2 Resident-Quote",
    ))
    page.add(Polygon(
        x_mm=105, y_mm=106, w_mm=42, h_mm=0.8,
        fill="Dunkelgrün", layer=0, anname="P2 Quote-Rule",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=113, w_mm=71, h_mm=56,
        layer=2, style="exp/quote/reply",
        runs=[Run(
            text="Leistbares Wohnen wird im Rathaus wieder Prioritaet.",
            paragraph_style="exp/quote/reply",
        )],
        anname="P2 Candidate-Reply",
    ))

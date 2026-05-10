"""Variant: manifesto-single-statement.

Hypothesis: Replace the list with one editorial manifesto sentence
Axes: density, typography
Rationale: Trade five even-weight slogans for ONE 48pt manifesto
statement. Polarising by design — the rater either reads the whole
panel or skips it entirely.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/manifesto/statement",
        font="Vollkorn Black",
        fontsize=44, linesp=48, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/manifesto/footer",
        font="Gotham Narrow Book",
        fontsize=10, linesp=13, align=0,
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
        runs=[Run(text="Eine Sache zählt.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=72, w_mm=87, h_mm=120,
        layer=2, style="exp/manifesto/statement",
        runs=[Run(text="Mödling muss vorangehen — beim Klima, beim "
                       "Wohnen, beim Zuhören.",
                  paragraph_style="exp/manifesto/statement")],
        anname="P2 Manifesto",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=198, w_mm=87, h_mm=10,
        layer=2, style="exp/manifesto/footer",
        runs=[Run(text="Maria Beispiel · Die Grünen Mödling",
                  paragraph_style="exp/manifesto/footer")],
        anname="P2 Manifesto-Footer",
    ))

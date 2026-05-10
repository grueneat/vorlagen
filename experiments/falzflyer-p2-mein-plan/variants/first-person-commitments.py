"""Variant: first-person-commitments.

Hypothesis: Personal voice — "Ich werde…" commitments
Axes: voice-formality
Rationale: Convert bullet slogans to first-person commitments. The
message becomes a contract; personal accountability replaces abstract
slogans.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/personal/commitment",
        font="Gotham Narrow Book",
        fontsize=14, linesp=19, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/personal/sig",
        font="Vollkorn Black Italic",
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
        runs=[Run(text="Mein Versprechen",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    commitments = [
        "Ich werde den Klimaplan in den ersten 100 Tagen vorlegen.",
        "Ich werde leistbares Wohnen vor Spekulation stellen.",
        "Ich werde jede Volksschule besuchen — und zuhören.",
        "Ich werde lokale Betriebe vor Konzernen schützen.",
        "Ich werde Bürgersprechstunden monatlich abhalten.",
    ]
    page.add(TextFrame(
        x_mm=105, y_mm=72, w_mm=87, h_mm=110,
        layer=2, style="exp/personal/commitment",
        runs=[
            Run(text=t, separator="para",
                paragraph_style="exp/personal/commitment")
            for t in commitments[:-1]
        ] + [
            Run(text=commitments[-1],
                paragraph_style="exp/personal/commitment"),
        ],
        anname="P2 Commitments",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=190, w_mm=87, h_mm=14,
        layer=2, style="exp/personal/sig",
        runs=[Run(text="— Maria Beispiel",
                  paragraph_style="exp/personal/sig")],
        anname="P2 Signature",
    ))

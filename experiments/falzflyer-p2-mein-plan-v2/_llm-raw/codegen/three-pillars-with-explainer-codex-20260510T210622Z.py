"""Variant: three-pillars-with-explainer.

Hypothesis: Reduce the panel to three ranked priorities and give each one
a short explanatory sentence. The hierarchy is built through a numeric
lead-in, a bold pillar title, and a smaller explainer line that stays
safely above the 10pt body floor.

Axis commitments: density, hierarchy.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/pillars/numeral",
        font="Vollkorn Black Italic",
        fontsize=26,
        linesp=29,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/pillars/title",
        font="Gotham Narrow Bold",
        fontsize=17,
        linesp=20,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/pillars/explainer",
        font="Gotham Narrow Book",
        fontsize=11,
        linesp=14,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))

    page.add(Polygon(
        x_mm=99,
        y_mm=-3,
        w_mm=99,
        h_mm=31,
        fill="Dunkelgrün",
        layer=0,
        anname="P2 Top-Band",
    ))
    page.add(TextFrame(
        x_mm=105,
        y_mm=8,
        w_mm=87,
        h_mm=14,
        layer=2,
        style="falzflyer/top-title",
        runs=[Run(
            text="Mein Plan",
            paragraph_style="falzflyer/top-title",
        )],
        anname="P2 Top-Title",
    ))
    page.add(TextFrame(
        x_mm=105,
        y_mm=38,
        w_mm=87,
        h_mm=22,
        layer=2,
        style="falzflyer/teaser-headline",
        runs=[Run(
            text="Drei Prioritäten.",
            paragraph_style="falzflyer/teaser-headline",
        )],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99,
        y_mm=28,
        w_mm=99,
        h_mm=185,
        fill="Hellgrün",
        layer=0,
        anname="P2 Body-Backing",
    ))

    items = [
        (
            "1",
            "Klimaschutz zuerst.",
            "Mit klarem Fahrplan für saubere Energie und kurze Wege im Alltag.",
        ),
        (
            "2",
            "Wohnen leistbar halten.",
            "Mehr Tempo bei guten Wohnungen, damit Familien im Bezirk bleiben können.",
        ),
        (
            "3",
            "Zuhören und umsetzen.",
            "Regelmäßig vor Ort sein, Probleme aufnehmen und sichtbar erledigen.",
        ),
    ]

    y_positions_mm = [72, 108, 144]
    row_h_mm = 28

    for i, (num, title, explainer) in enumerate(items):
        y = y_positions_mm[i]
        page.add(TextFrame(
            x_mm=105,
            y_mm=y,
            w_mm=14,
            h_mm=20,
            layer=2,
            style="exp/pillars/numeral",
            runs=[Run(
                text=num,
                paragraph_style="exp/pillars/numeral",
            )],
            anname=f"P2 Numeral {i+1}",
        ))
        page.add(TextFrame(
            x_mm=122,
            y_mm=y,
            w_mm=70,
            h_mm=row_h_mm,
            layer=2,
            style="exp/pillars/title",
            runs=[
                Run(
                    text=title,
                    paragraph_style="exp/pillars/title",
                    separator="para",
                ),
                Run(
                    text=explainer,
                    paragraph_style="exp/pillars/explainer",
                ),
            ],
            anname=f"P2 Pillar {i+1}",
        ))
        if i < len(items) - 1:
            page.add(Polygon(
                x_mm=122,
                y_mm=y + row_h_mm + 3,
                w_mm=70,
                h_mm=0.4,
                fill="Dunkelgrün",
                layer=0,
                anname=f"P2 Rule {i+1}",
            ))

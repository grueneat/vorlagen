"""Variant: cut-to-three-with-body.

Hypothesis: Cut to three items, add one-sentence body
Axes: density, hierarchy
Rationale: Five even-weight slogans read as a checklist. Cutting to
three items, each with a one-sentence body, trades breadth for depth
and gives the eye a sequence with an entry point.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/cut-to-three/eyebrow",
        font="Gotham Narrow Bold",
        fontsize=10, linesp=12, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/cut-to-three/body",
        font="Gotham Narrow Book",
        fontsize=10, linesp=13, align=0,
        fcolor="Black", language="de",
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

    blocks = [
        ("KLIMA",   "Klimaplan jetzt.",
         "Solar auf jedes Gemeindedach, Heizung tauschen, ÖV verdoppeln."),
        ("WOHNEN",  "Leistbar bleiben.",
         "Boden zurückkaufen, Genossenschaften stärken, Spekulation stoppen."),
        ("BILDUNG", "Vor Ort stark.",
         "Volksschulen ausbauen, Nachmittagsbetreuung gratis machen."),
    ]
    for i, (eyebrow, headline, body) in enumerate(blocks):
        y = 72 + i * 42
        page.add(TextFrame(
            x_mm=105, y_mm=y, w_mm=87, h_mm=6,
            layer=2, style="exp/cut-to-three/eyebrow",
            runs=[Run(text=eyebrow,
                      paragraph_style="exp/cut-to-three/eyebrow")],
            anname=f"P2 Pillar {i+1} — Eyebrow",
        ))
        page.add(TextFrame(
            x_mm=105, y_mm=y + 6, w_mm=87, h_mm=10,
            layer=2, style="falzflyer/schlagwort",
            runs=[Run(text=headline,
                      paragraph_style="falzflyer/schlagwort")],
            anname=f"P2 Pillar {i+1} — Headline",
        ))
        page.add(TextFrame(
            x_mm=105, y_mm=y + 18, w_mm=87, h_mm=18,
            layer=2, style="exp/cut-to-three/body",
            runs=[Run(text=body,
                      paragraph_style="exp/cut-to-three/body")],
            anname=f"P2 Pillar {i+1} — Body",
        ))

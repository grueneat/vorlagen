"""Variant: yellow-accent-privileged-item.

Hypothesis: Privilege one item via Hellgrün to Gelb swap
Axes: accent-strategy, hierarchy
Rationale: Single most-important item gets a Gelb backing while the
rest stay on Hellgrün; explicit visual hierarchy replaces flatness.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/yellow-accent/hero",
        font="Gotham Narrow Bold",
        fontsize=22, linesp=26, align=1,
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

    # Privileged item: Gelb panel for Klimaplan.
    page.add(Polygon(
        x_mm=99, y_mm=70, w_mm=99, h_mm=42,
        fill="Gelb", layer=0, anname="P2 Hero-Backing",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=80, w_mm=87, h_mm=24,
        layer=2, style="exp/yellow-accent/hero",
        runs=[Run(text="Klimaplan jetzt.",
                  paragraph_style="exp/yellow-accent/hero")],
        anname="P2 Hero-Headline",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=120, w_mm=87, h_mm=85,
        layer=2, style="falzflyer/schlagwort",
        runs=[
            Run(text="Leistbares Wohnen.", separator="para",
                paragraph_style="falzflyer/schlagwort"),
            Run(text="Bildung vor Ort.", separator="para",
                paragraph_style="falzflyer/schlagwort"),
            Run(text="Lokale Wirtschaft.", separator="para",
                paragraph_style="falzflyer/schlagwort"),
            Run(text="Bürgernähe statt Klüngel.",
                paragraph_style="falzflyer/schlagwort"),
        ],
        anname="P2 Teaser-Body",
    ))

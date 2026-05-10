"""Variant: weighted-hero-lead.

Hypothesis: Hero promise leads, four supporters in compact list
Axes: hierarchy, accent-strategy
Rationale: One large hero promise above the fold of the panel; four
short slogans below in 2-up grid. Explicit rank without color tricks.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/hero/lead",
        font="Gotham Narrow Bold",
        fontsize=22, linesp=26, align=1,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/hero/support",
        font="Gotham Narrow Bold",
        fontsize=12, linesp=15, align=1,
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

    page.add(TextFrame(
        x_mm=105, y_mm=70, w_mm=87, h_mm=64,
        layer=2, style="exp/hero/lead",
        runs=[Run(text="Klimaplan in 100 Tagen.",
                  paragraph_style="exp/hero/lead")],
        anname="P2 Hero-Lead",
    ))
    # Thin separator rule.
    page.add(Polygon(
        x_mm=105, y_mm=140, w_mm=87, h_mm=0.4,
        fill="Dunkelgrün", layer=0, anname="P2 Hero-Rule",
    ))

    # 2x2 grid of supporters.
    supporters = [
        ("Wohnen", "Leistbar."),
        ("Bildung", "Vor Ort."),
        ("Wirtschaft", "Lokal."),
        ("Bürgernähe", "Statt Klüngel."),
    ]
    for i, (label, body) in enumerate(supporters):
        col = i % 2
        row = i // 2
        x = 105 + col * 44
        y = 152 + row * 28
        page.add(TextFrame(
            x_mm=x, y_mm=y, w_mm=42, h_mm=22,
            layer=2, style="exp/hero/support",
            runs=[
                Run(text=label, separator="para",
                    paragraph_style="exp/hero/support"),
                Run(text=body,
                    paragraph_style="exp/hero/support"),
            ],
            anname=f"P2 Support {i+1}",
        ))

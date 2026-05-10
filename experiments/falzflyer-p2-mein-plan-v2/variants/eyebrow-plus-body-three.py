"""Variant: eyebrow-plus-body-three.

Hypothesis: Three items, each labelled with a small Gotham Narrow Bold
all-caps eyebrow (KLIMA / WOHNEN / BILDUNG) sitting above a single short
body sentence. Hierarchy operates inside the row, not just between rows.
Axis commitments: primary=density (3 items), secondary=hierarchy
(eyebrow→body two-step within each row).

Body sentences sit at 16pt — well above the 10pt floor — and the eyebrow
sits at 10pt all-caps, on the body floor exactly. Three rows of ~38mm
each fit comfortably inside the 130mm body content area, leaving the
bottom third of the panel as breathing room.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/eyebrow/label",
        font="Gotham Narrow Bold",
        fontsize=10, linesp=12, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/eyebrow/body",
        font="Gotham Narrow Bold",
        fontsize=16, linesp=20, align=0,
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
        runs=[Run(text="Drei Felder. Klar benannt.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    items = [
        ("KLIMA",
         "Klimaschutz vor Ort: konsequent, planvoll, gerecht."),
        ("WOHNEN",
         "Leistbarer Wohnraum für junge Familien und Pensionisten."),
        ("BILDUNG",
         "Beste Bildung beginnt mit Plätzen, Personal und Pausenzeit."),
    ]

    y0 = 75
    row_h = 38
    for i, (label, body) in enumerate(items):
        y = y0 + i * row_h
        page.add(TextFrame(
            x_mm=105, y_mm=y, w_mm=87, h_mm=6,
            layer=2, style="exp/eyebrow/label",
            runs=[Run(text=label,
                      paragraph_style="exp/eyebrow/label")],
            anname=f"P2 Eyebrow {i+1}",
        ))
        page.add(TextFrame(
            x_mm=105, y_mm=y + 7, w_mm=87, h_mm=24,
            layer=2, style="exp/eyebrow/body",
            runs=[Run(text=body,
                      paragraph_style="exp/eyebrow/body")],
            anname=f"P2 Body {i+1}",
        ))
        if i < len(items) - 1:
            page.add(Polygon(
                x_mm=105, y_mm=y + row_h - 4, w_mm=87, h_mm=0.4,
                fill="Dunkelgrün", layer=0,
                anname=f"P2 Rule {i+1}",
            ))
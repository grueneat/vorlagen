"""Variant: dunkelgrun-rules-between-items-v2 (concept retained from v1).

Hypothesis: Left-aligned items separated by thin Dunkelgrün rules,
editorial-magazine register. Right third intentional whitespace.
Axis commitments (per PLAN.md R6): primary=density (3 items),
secondary=form (thin-rule separator vs. block separator).

v1 broken: 5 rows × 22mm = 110mm of content packed into the 130mm
available panel height. Only ~15% whitespace, well below the hcd #3
30% floor. v2 fix: reduce to 3 items, leaving ~49% whitespace in the
body area. Kept the same para style (Gotham Narrow Bold 18pt) and the
0.4mm Dunkelgrün rules, just shorter.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/editorial/item",
        font="Gotham Narrow Bold",
        fontsize=18, linesp=22, align=0,
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
        runs=[Run(text="Drei Schwerpunkte.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    items = [
        "Klimaplan jetzt.",
        "Leistbares Wohnen.",
        "Bildung vor Ort.",
    ]
    y0 = 75
    row_h = 22
    for i, text in enumerate(items):
        y = y0 + i * row_h
        page.add(TextFrame(
            x_mm=105, y_mm=y, w_mm=55, h_mm=14,
            layer=2, style="exp/editorial/item",
            runs=[Run(text=text,
                      paragraph_style="exp/editorial/item")],
            anname=f"P2 Item {i+1}",
        ))
        if i < len(items) - 1:
            page.add(Polygon(
                x_mm=105, y_mm=y + row_h - 4, w_mm=55, h_mm=0.4,
                fill="Dunkelgrün", layer=0,
                anname=f"P2 Rule {i+1}",
            ))

"""Variant: cornerstone-banner-with-minors.

Hypothesis: One priority owns a full-width banner at the top of the
body area; the remaining items sit beneath as smaller supporting lines.
The anatomy creates a clear leader-with-supporters asymmetry without
shrinking the supporters below the body-size floor.

Axis commitments: hierarchy (rank-weighted scale, leader > minors) and
asymmetry (one dominant element + four equal small ones, not a uniform
list). The Gelb banner adds an accent plate beneath the leader so the
leader/minor break is unmistakable; the minor lines remain on the
Hellgrün body backing in the same Gotham Narrow Bold register used by
the editorial-rules reference, keeping the supporting block visually
quiet.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/cornerstone/leader",
        font="Vollkorn Black Italic",
        fontsize=36, linesp=40, align=0,
        fcolor="Dunkelgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/cornerstone/minor",
        font="Gotham Narrow Bold",
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
        runs=[Run(text="Eine Priorität führt.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    # Cornerstone banner — full panel width, Gelb plate behind the
    # leader statement so the rank-1 priority reads as unmistakably
    # dominant against the Hellgrün body field.
    page.add(Polygon(
        x_mm=99, y_mm=70, w_mm=99, h_mm=40,
        fill="Gelb", layer=0, anname="P2 Cornerstone-Banner",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=76, w_mm=87, h_mm=30,
        layer=2, style="exp/cornerstone/leader",
        runs=[Run(text="Klimaplan jetzt.",
                  paragraph_style="exp/cornerstone/leader")],
        anname="P2 Cornerstone-Leader",
    ))

    # Minor supporters — four smaller lines beneath the banner. Same
    # left edge as the leader, single-column, generous bottom whitespace.
    minors = [
        "Leistbares Wohnen.",
        "Bildung vor Ort.",
        "Lokale Wirtschaft.",
        "Bürgernähe statt Klüngel.",
    ]
    y0 = 120
    row_h = 16
    for i, text in enumerate(minors):
        y = y0 + i * row_h
        page.add(TextFrame(
            x_mm=105, y_mm=y, w_mm=87, h_mm=12,
            layer=2, style="exp/cornerstone/minor",
            runs=[Run(text=text,
                      paragraph_style="exp/cornerstone/minor")],
            anname=f"P2 Minor {i+1}",
        ))
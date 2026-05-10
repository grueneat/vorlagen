"""Variant: accent-chip-and-open-field.

Hypothesis: a single Gelb accent chip carries the privileged phrase,
while the rest of the panel stays intentionally sparse. The layout keeps
the production P2 shell, concentrates emphasis into one compact signal,
and leaves a large open field below to test restraint over saturation.

Axis commitments: accent-strategy, whitespace-strategy.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/accent-chip/note",
        font="Gotham Narrow Book",
        fontsize=10,
        linesp=13,
        align=0,
        fcolor="Dunkelgrün",
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
            text="Ein Satz. Dann Raum.",
            paragraph_style="falzflyer/teaser-headline",
        )],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(Polygon(
        x_mm=105, y_mm=82, w_mm=70, h_mm=24,
        fill="Gelb", layer=0, anname="P2 Accent-Chip",
    ))
    page.add(TextFrame(
        x_mm=109, y_mm=87, w_mm=62, h_mm=14,
        layer=2, style="falzflyer/schlagwort",
        runs=[Run(
            text="Klimaplan jetzt.",
            paragraph_style="falzflyer/schlagwort",
        )],
        anname="P2 Accent-Text",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=128, w_mm=56, h_mm=34,
        layer=2, style="exp/accent-chip/note",
        runs=[
            Run(
                text="Leistbares Wohnen.",
                separator="para",
                paragraph_style="exp/accent-chip/note",
            ),
            Run(
                text="Bildung vor Ort.",
                separator="para",
                paragraph_style="exp/accent-chip/note",
            ),
            Run(
                text="Politik, die zuhoert.",
                paragraph_style="exp/accent-chip/note",
            ),
        ],
        anname="P2 Support-Notes",
    ))

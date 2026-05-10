"""Variant: two-column-editorial-split.

Hypothesis: 60/40 editorial column split. The left column carries three
promises in a paced vertical stack; the right column holds authored
identity in a compact Dunkelgrün block at the top, then intentionally
falls to whitespace. This preserves the production P2 frame while
testing asymmetry and hierarchy inside the body zone.

The candidate identity uses the scaffold's production placeholder name
("Maria Beispiel") so the authorship cue is concrete rather than
generic. All PAGEOBJECT annames retain the required ``"P2 "`` prefix.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/split/promise",
        font="Gotham Narrow Bold",
        fontsize=18,
        linesp=22,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/split/name",
        font="Gotham Narrow Bold",
        fontsize=12,
        linesp=14,
        align=0,
        fcolor="Weiß",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/split/role",
        font="Gotham Narrow Book",
        fontsize=10,
        linesp=12,
        align=0,
        fcolor="Gelb",
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
            text="Drei Versprechen. Ein Auftrag.",
            paragraph_style="falzflyer/teaser-headline",
        )],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    promises = [
        ("Klimaplan jetzt.", 78),
        ("Leistbares Wohnen.", 104),
        ("Bildung vor Ort.", 130),
    ]
    for i, (text, y_mm) in enumerate(promises, start=1):
        page.add(TextFrame(
            x_mm=105, y_mm=y_mm, w_mm=49, h_mm=14,
            layer=2, style="exp/split/promise",
            runs=[Run(
                text=text,
                paragraph_style="exp/split/promise",
            )],
            anname=f"P2 Promise {i}",
        ))

    page.add(Polygon(
        x_mm=160, y_mm=72, w_mm=32, h_mm=24,
        fill="Dunkelgrün", layer=0, anname="P2 Identity-Block",
    ))
    page.add(TextFrame(
        x_mm=163, y_mm=76, w_mm=26, h_mm=7,
        layer=2, style="exp/split/name",
        runs=[Run(
            text="Maria Beispiel",
            paragraph_style="exp/split/name",
        )],
        anname="P2 Candidate-Name",
    ))
    page.add(TextFrame(
        x_mm=163, y_mm=84, w_mm=26, h_mm=8,
        layer=2, style="exp/split/role",
        runs=[Run(
            text="Für Mödling.",
            paragraph_style="exp/split/role",
        )],
        anname="P2 Candidate-Role",
    ))

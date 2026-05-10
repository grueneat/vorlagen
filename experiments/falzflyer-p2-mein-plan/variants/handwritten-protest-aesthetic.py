"""Variant: handwritten-protest-aesthetic (WILDCARD).

Hypothesis: Handwritten margin notes alongside the printed slogans
Axes: wildcard
Rationale: Wild-card. Keep the printed list and overlay
'handwritten-style' margin annotations from the candidate
('WICHTIG!', 'unterschätzt'). Voice + authenticity tension. Will
polarise — some find it personal, others find it unprofessional.
Either way: signal.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    # No native handwritten font in the brand set; we approximate with
    # Vollkorn Black Italic at 11pt + slight rotation effect via
    # asymmetric placement. Dunkelgrün ink-on-Hellgrün.
    doc.add_para_style(ParaStyle(
        name="exp/handwritten/note",
        font="Vollkorn Black Italic",
        fontsize=12, linesp=14, align=0,
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

    # Original five slogans — production layout, slightly compressed
    # left so margin annotations have room.
    page.add(TextFrame(
        x_mm=99, y_mm=72, w_mm=70, h_mm=130,
        layer=2, style="falzflyer/schlagwort",
        runs=[
            Run(text="Klimaplan jetzt.", separator="para",
                paragraph_style="falzflyer/schlagwort"),
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

    # Handwritten-style margin notes on the right.
    annotations = [
        ("WICHTIGSTER PUNKT!", 78),
        ("Mödling-spezifisch", 110),
        ("Ja!", 130),
        ("auch klein", 158),
        ("nicht verhandelbar", 182),
    ]
    for i, (text, y) in enumerate(annotations):
        page.add(TextFrame(
            x_mm=170, y_mm=y, w_mm=26, h_mm=18,
            layer=2, style="exp/handwritten/note",
            runs=[Run(text=text,
                      paragraph_style="exp/handwritten/note")],
            anname=f"P2 Margin-Note {i+1}",
        ))

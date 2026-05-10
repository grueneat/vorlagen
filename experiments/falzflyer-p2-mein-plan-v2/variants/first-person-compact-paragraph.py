"""Variant: first-person-compact-paragraph.

Hypothesis: Replace the five-item list with one short first-person
paragraph — a compact personal commitment rather than a fragmented
roster of equal-weight claims. Axis commitments: primary=density
(one prose block, not five rows), secondary=voice-formality (Ich-form
contract register vs. impersonal Schlagworte).

Form intent: voters process a coherent stance instead of hopping
across list items. Single paragraph, single type-size in the body,
generous leading so the sentence breathes inside the Hellgrün field.
Right-side whitespace is deliberate — the column is set narrower than
the body backing to keep the rag short and the eye moving down the
sentence rather than across it.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/firstperson/paragraph",
        font="Gotham Narrow Book",
        fontsize=16, linesp=22, align=0,
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
        runs=[Run(text="Mein Versprechen.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    paragraph = (
        "Ich bringe Mödling beim Klima voran, sorge für leistbares "
        "Wohnen und stärke die Bildung vor Ort. Ich höre zu, "
        "entscheide nachvollziehbar und stehe für jedes Wort, "
        "das ich euch heute gebe, gerade."
    )
    page.add(TextFrame(
        x_mm=105, y_mm=78, w_mm=72, h_mm=110,
        layer=2, style="exp/firstperson/paragraph",
        runs=[Run(text=paragraph,
                  paragraph_style="exp/firstperson/paragraph")],
        anname="P2 Commitment-Paragraph",
    ))
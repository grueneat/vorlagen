"""Variant: two-statement-call-response.

Hypothesis: Two display statements replace the production list and read
as call-and-response. The upper statement poses the civic stakes; a
4mm Dunkelgrün rule creates a deliberate pause; the lower statement
answers with a compact commitment.

Axis commitments: density (two statements instead of five items) and
typography (editorial dialogue between Vollkorn display and Gotham
answer). The composition intentionally leaves the right side and lower
body area open so the pause reads as confidence rather than omission.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame

QUESTION_PT = 30
ANSWER_PT = 12
RULE_H_MM = 4


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/call-response/question",
        font="Vollkorn Black Italic",
        fontsize=QUESTION_PT,
        linesp=33,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/call-response/answer",
        font="Gotham Narrow Bold",
        fontsize=ANSWER_PT,
        linesp=14,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))

    page.add(Polygon(
        x_mm=99,
        y_mm=-3,
        w_mm=99,
        h_mm=31,
        fill="Dunkelgrün",
        layer=0,
        anname="P2 Top-Band",
    ))
    page.add(TextFrame(
        x_mm=105,
        y_mm=8,
        w_mm=87,
        h_mm=14,
        layer=2,
        style="falzflyer/top-title",
        runs=[Run(
            text="Mein Plan",
            paragraph_style="falzflyer/top-title",
        )],
        anname="P2 Top-Title",
    ))
    page.add(TextFrame(
        x_mm=105,
        y_mm=38,
        w_mm=87,
        h_mm=22,
        layer=2,
        style="falzflyer/teaser-headline",
        runs=[Run(
            text="Frage. Antwort. Klar.",
            paragraph_style="falzflyer/teaser-headline",
        )],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99,
        y_mm=28,
        w_mm=99,
        h_mm=185,
        fill="Hellgrün",
        layer=0,
        anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105,
        y_mm=74,
        w_mm=66,
        h_mm=36,
        layer=2,
        style="exp/call-response/question",
        runs=[Run(
            text="Wie weiter im Kreis?",
            paragraph_style="exp/call-response/question",
        )],
        anname="P2 Question",
    ))
    page.add(Polygon(
        x_mm=105,
        y_mm=124,
        w_mm=48,
        h_mm=RULE_H_MM,
        fill="Dunkelgrün",
        layer=0,
        anname="P2 Response-Rule",
    ))
    page.add(TextFrame(
        x_mm=105,
        y_mm=140,
        w_mm=50,
        h_mm=14,
        layer=2,
        style="exp/call-response/answer",
        runs=[Run(
            text="Mit klarem Kurs.",
            paragraph_style="exp/call-response/answer",
        )],
        anname="P2 Answer",
    ))
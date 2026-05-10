"""Variant: paragraph-form-prose-block.

Hypothesis: Replace the list with one cohesive 11pt Gotham prose
paragraph that argues for the candidate's plan as connected reasoning
rather than scannable bullets.

Axis commitments: primary=density (single block vs. multi-item list),
secondary=voice-formality (continuous editorial prose vs. Schlagwort
register). The paragraph trades scannability for narrative pull and a
more adult register — the eye cannot dismiss a plan it has to read.

11pt Gotham Narrow Book sits comfortably above the 10pt body floor and
below the 14pt of bolder reference variants; line spacing 13pt yields a
calm, magazine-feature rhythm at the 87mm body width.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame

PROSE = (
    "Mödling steht an einem Wendepunkt: Klima, Wohnen und Bildung "
    "lassen sich nicht länger getrennt denken. Mein Plan beginnt beim "
    "Klima, weil jede leistbare Wohnung, die wir heute bauen, morgen "
    "auch günstig zu heizen sein muss. Er führt weiter zum Wohnen, weil "
    "junge Familien und ältere Nachbarn dieselbe Stadt brauchen, nicht "
    "zwei getrennte. Und er endet bei der Bildung vor Ort, weil eine "
    "Gemeinde, die ihre Kinder verliert, ihre Zukunft verliert. Das "
    "sind keine Schlagworte — das ist eine Reihenfolge, die zusammen­"
    "hängt, weil sie zusammengehört."
)


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/prose/body",
        font="Gotham Narrow Book",
        fontsize=11, linesp=13, align=0,
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
        runs=[Run(text="Ein Gedanke, zu Ende gedacht.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=72, w_mm=87, h_mm=125,
        layer=2, style="exp/prose/body",
        runs=[Run(text=PROSE,
                  paragraph_style="exp/prose/body")],
        anname="P2 Prose-Paragraph",
    ))
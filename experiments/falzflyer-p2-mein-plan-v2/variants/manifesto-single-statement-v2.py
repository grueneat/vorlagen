"""Variant: manifesto-single-statement-v2 (concept retained from v1).

Hypothesis: ONE long editorial sentence owns the panel.
Axis commitments (per PLAN.md R6): primary=density (1 item),
secondary=form (sentence vs. list).

v1 broken: `Vollkorn Black` (non-italic) was specified but NOT
registered in shared/ci.yml::fonts — Scribus rendered via fallback.
The only registered Vollkorn face is `Vollkorn Black Italic`, so v2
uses that (registered face → brand:font_family passes). Editorial
italic register is congruent with manifesto semantics.

The Gotham Narrow Book footer from v1 is removed: it added a third
type size to the panel and the manifesto's intent is single-statement
ownership of the panel, not statement+attribution.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/manifesto/statement",
        font="Vollkorn Black Italic",
        fontsize=30, linesp=34, align=0,
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
        runs=[Run(text="Eine Sache zählt.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=72, w_mm=87, h_mm=120,
        layer=2, style="exp/manifesto/statement",
        runs=[Run(text="Mödling muss vorangehen — beim Klima, beim "
                       "Wohnen, beim Zuhören.",
                  paragraph_style="exp/manifesto/statement")],
        anname="P2 Manifesto",
    ))

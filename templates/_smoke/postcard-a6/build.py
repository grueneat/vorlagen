#!/usr/bin/env python3
"""Smoke: build a brand-correct A6 postcard skeleton via the DSL.

Not a production template — proves the DSL emits valid Scribus output
with brand colors, an example headline, a Störer badge, and an Impressum.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import (  # noqa: E402
    Document, Color, Style, TextFrame, ImageFrame, Polygon,
)


def build(out_path: Path) -> None:
    doc = Document(title="Postkarte A6 (smoke)", template_id="smoke-postcard-a6")
    page = doc.add_page(size="A6", orientation="portrait", bleed_mm=3,
                        margins_mm=(8, 8, 8, 8))

    # Background — fills the trim area + bleed
    page.add(Polygon(
        x_mm=-3, y_mm=-3, w_mm=111, h_mm=154,
        fill=Color.DUNKELGRUEN, layer=0,
        anname="Hintergrund-Vollfläche",
    ))

    # 4-line brand headline in alternating colors (white / yellow)
    page.add(TextFrame(
        x_mm=8, y_mm=38, w_mm=89, h_mm=66,
        style=Style.HEADLINE_ULTRA, layer=2,
        runs=[
            ("[Zeile 1]",         {"fcolor": Color.WHITE},      "para"),
            ("[Zeile 2 Vollkorn]", {"fcolor": Color.GELB},      "para"),
            ("[Zeile 3]",         {"fcolor": Color.WHITE},      "para"),
            ("[Zeile 4 Vollkorn]", {"fcolor": Color.GELB}),
        ],
        anname="Headline 4-zeilig (Brand-Wechselfarbe)",
    ))

    # Störer (pink badge)
    page.add(Polygon(
        x_mm=72, y_mm=10, w_mm=22, h_mm=22,
        fill=Color.MAGENTA, shape="ellipse", layer=2,
        rotation_deg=8,
        anname="Störer-Kreis",
    ))
    page.add(TextFrame(
        x_mm=73, y_mm=14, w_mm=20, h_mm=14,
        style=Style.STOERER, fcolor=Color.WHITE, layer=2,
        runs=[
            ("[Stör 1]", None, "para"),
            ("[Stör 2]", None, "para"),
            ("[Stör 3]",),
        ],
        rotation_deg=8,
        anname="Störer-Text 3-zeilig",
    ))

    # CTA under headline
    page.add(TextFrame(
        anchor=("center", 90), w_mm=85, h_mm=8,
        text="[Call-to-Action eine Zeile]",
        style=Style.CTA, fcolor=Color.WHITE, layer=2,
        anname="CTA",
    ))

    # Impressum at bottom
    page.add(TextFrame(
        x_mm=8, y_mm=140, w_mm=89, h_mm=6,
        text="Impressum: Medieninhaber und Herausgeber: Die Grünen Niederösterreich, Daniel-Gran-Straße 48, 3100 St. Pölten.",
        style=Style.IMPRESSUM, fcolor=Color.WHITE, layer=2,
        anname="Impressum (Vorderseite)",
    ))

    doc.save(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    build(Path(__file__).parent / "template.sla")

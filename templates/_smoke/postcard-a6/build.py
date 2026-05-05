#!/usr/bin/env python3
"""Smoke: A6 postcard skeleton built with composable blocks."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document, Color, Polygon, blocks  # noqa: E402


def build(out_path: Path) -> None:
    doc = Document(title="Postkarte A6 (smoke)", template_id="smoke-postcard-a6")
    page = doc.add_page(size="A6", orientation="portrait", bleed_mm=3,
                        margins_mm=(8, 8, 8, 8))

    page.add(Polygon(x_mm=-3, y_mm=-3, w_mm=111, h_mm=154,
                     fill=Color.DUNKELGRUEN, layer=0,
                     anname="Hintergrund-Vollfläche"))

    page.add(blocks.Headline4Line(
        lines=("[Zeile 1]", "[Zeile 2 Vollkorn]", "[Zeile 3]", "[Zeile 4 Vollkorn]"),
        x_mm=8, y_mm=38, w_mm=89, h_mm=66,
    ))

    page.add(blocks.StoererBadge(
        text=("[Stör 1]", "[Stör 2]", "[Stör 3]"),
        x_mm=72, y_mm=10, diameter_mm=22, rotation_deg=8,
    ))

    page.add(blocks.ImpressumLine(x_mm=8, y_mm=140, w_mm=89))

    doc.save(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    build(Path(__file__).parent / "template.sla")

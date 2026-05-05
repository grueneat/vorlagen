#!/usr/bin/env python3
"""Build the Event-Plakat family — A0, A1, A2, A3 from one DSL definition.

Output: templates/plakat-event/{a0,a1,a2,a3}.sla — same design at four
sizes, font scales proportionally.

Each plakat has:
  - Logo top-right
  - Big 4-line brand headline
  - Event details (date / time / venue / address) in 2-column layout
  - Anmelde-URL line
  - Impressum line at bottom
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import (  # noqa: E402
    Document, Color, Style, TextFrame, Polygon, blocks,
)


# Page sizes in mm (portrait orientation), keyed by short name
SIZES = {
    "a0": ("A0", (841, 1189)),
    "a1": ("A1", (594, 841)),
    "a2": ("A2", (420, 594)),
    "a3": ("A3", (297, 420)),
}


def build_one(size_iso: str, w_mm: float, h_mm: float, out_path: Path) -> None:
    doc = Document(
        title=f"Event-Plakat {size_iso}",
        template_id=f"plakat-event-{size_iso.lower()}",
    )
    page = doc.add_page(size=size_iso, orientation="portrait", bleed_mm=3,
                         margins_mm=(20, 20, 20, 20))

    # Bottom 40% green block
    block_h = h_mm * 0.42
    page.add(Polygon(
        x_mm=-3, y_mm=h_mm - block_h, w_mm=w_mm + 6, h_mm=block_h + 3,
        fill=Color.DUNKELGRUEN, layer=0,
        anname="Hintergrund unten (Dunkelgrün)",
    ))

    # Logo top-right (size scales with format)
    logo_size = w_mm * 0.18
    page.add(blocks.LogoCorner(corner="top-right", variant="weiss",
                                size_mm=logo_size, margin_mm=w_mm * 0.04))

    # Headline in the green block — DSL Headline4Line, dimensions scaled
    head_w = w_mm * 0.85
    head_h = block_h * 0.65
    page.add(blocks.Headline4Line(
        lines=("[Event Headline 1]", "[Vollkorn-Akzent]",
                "[Headline Zeile 3]", "[Vollkorn-Schluss]"),
        x_mm=w_mm * 0.075, y_mm=h_mm - block_h + block_h * 0.05,
        w_mm=head_w, h_mm=head_h,
    ))

    # Event details (2-column) at bottom of green block
    page.add(blocks.EventDetails(
        x_mm=w_mm * 0.075, y_mm=h_mm - block_h + head_h + block_h * 0.10,
        w_mm=head_w, h_mm=block_h * 0.18, columns=2,
    ))

    # Anmeldung URL near bottom edge
    page.add(TextFrame(
        x_mm=w_mm * 0.075, y_mm=h_mm - block_h * 0.10,
        w_mm=head_w, h_mm=block_h * 0.05,
        text="Anmeldung unter: [gruene.at/event-url]",
        style=Style.CTA, fcolor=Color.WHITE, layer=2,
        anname="Anmelde-URL",
    ))

    # Impressum vertical-rotated on right edge (matches original Plakat A1 design)
    page.add(TextFrame(
        x_mm=w_mm - 5, y_mm=h_mm - block_h + 10, w_mm=block_h - 20, h_mm=4,
        text=("Impressum: Medieninhaber und Herausgeber: Die Grünen "
              "Niederösterreich, Daniel-Gran-Straße 48, 3100 St. Pölten."),
        style=Style.IMPRESSUM, fcolor=Color.WHITE, layer=2,
        rotation_deg=90, anname="Impressum (vertikal)",
    ))

    doc.save(out_path)
    print(f"wrote {out_path} ({size_iso}, {w_mm:.0f}×{h_mm:.0f}mm)")


def build_all(out_dir: Path) -> None:
    for short, (iso, (w, h)) in SIZES.items():
        build_one(iso, w, h, out_dir / f"{short}.sla")


if __name__ == "__main__":
    build_all(Path(__file__).parent)

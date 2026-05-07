"""Wahlaufruf-Postkarte A6 quer — DSL build entry point.

Spec: templates/_specs/wahlaufruf-postkarte-a6-quer.md.
Format: A6 quer 148x105 mm, 2-seitig, 3 mm bleed.

Front: Wahlkreuz-Hero on Dunkelgrün (D12 contract).
Back: 2x2 info-grid + Impressum.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))

from sla_lib.builder import (  # noqa: E402
    Brand,
    Document,
    TextFrame,
    ImageFrame,
    Polygon,
    Run,
    ParaStyle,
    pack_inline_image,
)


# ---------------------------------------------------------------------------
# Constants from spec
# ---------------------------------------------------------------------------
TRIM_W_MM = 148.0
TRIM_H_MM = 105.0
BLEED_MM = 3.0


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(out_path: str | Path = HERE / "template.sla") -> None:
    doc = Document(
        brand=Brand.gruene_noe(),
        title="Wahlaufruf-Postkarte A6 quer",
        template_id="wahlaufruf-postkarte-a6-quer",
        author="Die Grünen Niederösterreich",
        facing_pages=False,
    )

    # Per-template ParaStyles
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/headline",
        font="Gotham Narrow Bold",
        fontsize=24,
        linesp=27,
        linesp_mode=0,
        align=1,  # center
        fcolor="White",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/cell-headline",
        font="Gotham Narrow Bold",
        fontsize=14,
        linesp=16,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/cell-body",
        font="Gotham Narrow Book",
        fontsize=9,
        linesp=11,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/impressum",
        font="Gotham Narrow Book",
        fontsize=6,
        linesp=7,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))

    # Master + 2 pages
    doc.add_master(
        name="Normal",
        size=(TRIM_W_MM, TRIM_H_MM),
        bleed_mm=BLEED_MM,
        margins_mm=(6.0, 6.0, 6.0, 6.0),
    )
    page0 = doc.add_page(size=(TRIM_W_MM, TRIM_H_MM), bleed_mm=BLEED_MM,
                         margins_mm=(6.0, 6.0, 6.0, 6.0), master="Normal")
    page1 = doc.add_page(size=(TRIM_W_MM, TRIM_H_MM), bleed_mm=BLEED_MM,
                         margins_mm=(6.0, 6.0, 6.0, 6.0), master="Normal")

    # ---- PAGE 1: Front (Wahlkreuz hero on Dunkelgrün) ------------------
    page0.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=-BLEED_MM,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=TRIM_H_MM + 2 * BLEED_MM,
        fill="Dunkelgrün",
        layer=0,
        anname="Seitenhintergrund (front)",
    ))

    # Wahlkreuz hero centered (D12: must sit on Dunkelgrün — the page bg
    # already provides Dunkelgrün, so we don't need an extra background polygon
    # here; the wahlkreuz PNG has alpha for the area outside the white circle).
    wahlkreuz_x = (TRIM_W_MM - 55) / 2  # 46.5
    wahlkreuz_y = 16
    wahlkreuz_path = HERE.parents[1] / "shared" / "assets" / "wahlkreuz.png"
    if not wahlkreuz_path.exists():
        raise FileNotFoundError(
            f"Wahlkreuz asset not found at {wahlkreuz_path}; "
            f"this template requires shared/assets/wahlkreuz.png (see D1 revised)."
        )
    wahlkreuz_bytes = wahlkreuz_path.read_bytes()
    wk_data, wk_ext = pack_inline_image(wahlkreuz_bytes, "png")
    page0.add(ImageFrame(
        x_mm=wahlkreuz_x, y_mm=wahlkreuz_y, w_mm=55, h_mm=55,
        inline_image_data=wk_data,
        inline_image_ext=wk_ext,
        scale_type=0,
        ratio=1,
        layer=1,
        anname="Wahlkreuz",
    ))

    # Headline below
    page0.add(TextFrame(
        x_mm=10, y_mm=78, w_mm=128, h_mm=20,
        layer=2,
        style="wahlaufruf/headline",
        runs=[Run(
            text="Wähle Grün am 23. Mai",
            paragraph_style="wahlaufruf/headline",
        )],
        anname="Headline-Wahlaufruf",
    ))

    # ---- PAGE 2: Back (2x2 grid + Impressum) ---------------------------
    # White background (no full-page poly needed; default is white)
    # 2x2 grid: 4 cells, each ~70 mm wide, ~39 mm tall, with 2 mm gutter
    cells = [
        (6, 22, "Was wir tun",
         "Klimaschutz, leistbares Wohnen, Bildung — konkret in deiner Gemeinde."),
        (78, 22, "Warum Grün",
         "Mut zur Veränderung. Faktenbasiert. Generationen­gerecht."),
        (6, 62, "Wann gewählt wird",
         "Sonntag, 23. Mai 2026, 7–17 Uhr."),
        (78, 62, "Wo informieren",
         "gruene-noe.at · Tel. 02742 / 90 230"),
    ]
    cell_idx = 1
    for cx, cy, hd, body in cells:
        cell_w = 68 if cx == 6 else 64
        # Headline
        page1.add(TextFrame(
            x_mm=cx, y_mm=cy, w_mm=cell_w, h_mm=8,
            layer=2,
            style="wahlaufruf/cell-headline",
            runs=[Run(text=hd, paragraph_style="wahlaufruf/cell-headline")],
            anname=f"Cell {cell_idx} — Headline",
        ))
        # Body
        page1.add(TextFrame(
            x_mm=cx, y_mm=cy + 9, w_mm=cell_w, h_mm=30 if cell_idx <= 2 else 20,
            layer=2,
            style="wahlaufruf/cell-body",
            runs=[Run(text=body, paragraph_style="wahlaufruf/cell-body")],
            anname=f"Cell {cell_idx} — Body",
        ))
        cell_idx += 1

    # Impressum bottom strip
    page1.add(TextFrame(
        x_mm=6, y_mm=96, w_mm=136, h_mm=6,
        layer=2,
        style="wahlaufruf/impressum",
        runs=[Run(
            text=("Medieninhaber: Die Grünen NÖ, "
                  "Daniel-Gran-Straße 48, 3100 St. Pölten."),
            paragraph_style="wahlaufruf/impressum",
        )],
        anname="Impressum",
    ))

    out_path = Path(out_path)
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

"""Infostand-Tent-Card A5 quer — DSL build entry point.

Spec: templates/_specs/infostand-tent-card-a5-quer.md.
Format: A4 quer 297×210 mm, gefalzt zu A5-Tent (horizontale Falz bei y=105).

Panel A (oben, y=0..105) liest normal.
Panel B (unten, y=105..210) wird beim Falzen umgedreht — daher rotiert build.py
die Panel-B-TextFrames effektiv um 180° (Pivot Mitte Panel B), so dass nach dem
Falzen beide Seiten korrekt aufrecht lesen.

Implementation note: Frame coordinates in this build correspond to the FINAL
frame positions in the SLA (post-rotation). The visual model: Panel B headline
sits *above* Panel B body in the rotated layout — i.e. when looking at the flat
sheet, the Panel B headline is at y=170 (logically near the bottom of the
sheet but the top of the assembled tent's reverse face).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))

from sla_lib.builder import (  # noqa: E402
    Brand,
    Document,
    DocumentLayer,
    TextFrame,
    ImageFrame,
    Polygon,
    Run,
    ParaStyle,
    pack_inline_image,
)
from sla_lib.builder.blocks import TableTentFold  # noqa: E402


# ---------------------------------------------------------------------------
# Constants from spec
# ---------------------------------------------------------------------------
TRIM_W_MM = 297.0
TRIM_H_MM = 210.0
BLEED_MM = 3.0
FOLD_Y_MM = 105.0       # horizontal fold position

# Layer indexes
LAYER_HINTERGRUND = 0
LAYER_BILDER = 1
LAYER_TEXT = 2
LAYER_FALZ = 3


def build(out_path: str | Path = HERE / "template.sla") -> None:
    doc = Document(
        brand=Brand.gruene_noe(),
        title="Infostand-Tent-Card A5 quer",
        template_id="infostand-tent-card-a5-quer",
        author="Die Grünen Niederösterreich",
        facing_pages=False,
        layers=[
            DocumentLayer(name="Hintergrund", visible=True, printable=True, flow=True),
            DocumentLayer(name="Bilder", visible=True, printable=True, flow=True),
            DocumentLayer(name="Text", visible=True, printable=True, flow=True),
            DocumentLayer(name="Falz", visible=True, printable=False, flow=False),
        ],
    )

    # Document-local Falz spot color
    doc.add_color("Falz", cmyk=(100, 0, 0, 0), spot=True)

    # Per-template ParaStyles
    doc.add_para_style(ParaStyle(
        name="tent/headline",
        font="Vollkorn Black Italic",
        fontsize=36,
        linesp=40,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tent/body",
        font="Gotham Narrow Book",
        fontsize=14,
        linesp=18,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tent/impressum",
        font="Gotham Narrow Book",
        fontsize=5,
        linesp=6,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))

    # Master + 1 page
    doc.add_master(
        name="Normal",
        size=(TRIM_W_MM, TRIM_H_MM),
        bleed_mm=BLEED_MM,
        margins_mm=(12.0, 12.0, 12.0, 12.0),
    )
    page = doc.add_page(
        size=(TRIM_W_MM, TRIM_H_MM),
        bleed_mm=BLEED_MM,
        margins_mm=(12.0, 12.0, 12.0, 12.0),
        master="Normal",
    )

    # ---- PANEL A (y=0..105) — normal orientation ---------------------------
    # Logo (cmyk) top-left of Panel A — 45x14mm = 127.6x39.7pt → scale ≈ 0.309
    logo_cmyk = HERE.parents[1] / "shared" / "logos" / "gruene-cmyk.png"
    if logo_cmyk.exists():
        lc_data, lc_ext = pack_inline_image(logo_cmyk.read_bytes(), "png")
        page.add(ImageFrame(
            x_mm=12, y_mm=10, w_mm=45, h_mm=14,
            inline_image_data=lc_data, inline_image_ext=lc_ext,
            scale_type=0, ratio=1,
            local_scale=(0.309, 0.336),
            layer=LAYER_BILDER,
            anname="Logo Grüne (cmyk, panel A)",
        ))

    # Headline Panel A — placed to the right of the logo
    page.add(TextFrame(
        x_mm=62, y_mm=12, w_mm=223, h_mm=24,
        layer=LAYER_TEXT,
        style="tent/headline",
        runs=[Run(text="Klimaschutz konkret.",
                  paragraph_style="tent/headline")],
        anname="Headline Panel A",
    ))

    # Body Panel A — aligned with headline (under it, slightly indented)
    page.add(TextFrame(
        x_mm=62, y_mm=44, w_mm=223, h_mm=56,
        layer=LAYER_TEXT,
        style="tent/body",
        runs=[Run(
            text=("• Erneuerbare Energie ausbauen\n"
                  "• Öffis verdoppeln\n"
                  "• Wärmepumpe statt Gas"),
            paragraph_style="tent/body",
        )],
        anname="Body Panel A",
    ))

    # Impressum (just above the fold line — y=96..100 = 4 mm tall)
    page.add(TextFrame(
        x_mm=12, y_mm=96, w_mm=280, h_mm=4,
        layer=LAYER_TEXT,
        style="tent/impressum",
        runs=[Run(
            text=("Medieninhaber: Die Grünen NÖ, "
                  "Daniel-Gran-Straße 48, 3100 St. Pölten."),
            paragraph_style="tent/impressum",
        )],
        anname="Impressum (Tent)",
    ))

    # ---- FOLD LINE at y=105 ---------------------------------------------
    page.add(TableTentFold(page_size_mm=(TRIM_W_MM, TRIM_H_MM),
                          layer_idx=LAYER_FALZ))

    # ---- PANEL B (y=105..210) — rotated 180° at emit time ----------------
    # Strategy: place frames with rotation_deg=180. Pivot point in Scribus is
    # the frame's bottom-left corner (or top-left depending on Scribus
    # conventions). For TextFrame ROT=180, the rendered text appears upside-
    # down from the frame's bbox-corner perspective. To flip it correctly we
    # set rotation_deg=180 on each Panel-B frame.
    # Headline Panel B — at y=174..198 (24mm) on flat sheet, rotates around
    # (12+273/2, 174+24/2) = bbox center; for "looks normal when flipped",
    # we set ROT=180 and adjust XPOS to compensate.
    #
    # Simpler: just place the text upright in the post-fold orientation. Since
    # the spec says the YAML coords ARE the final post-rotation coords (D3
    # contract, see infostand-tent-card-a5-quer.md), we use rotation_deg=180
    # to flip the frames into the correct visual orientation when the sheet
    # is folded.

    # Headline Panel B — rotated 180°, positioned with bbox math:
    # original (12, 174, 223, 24) → rotated 180 around bbox center makes
    # the rendered headline read upright when sheet is folded.
    # Frame XPOS/YPOS in Scribus track the rotated bbox top-left (which
    # for ROT=180 lands at original bottom-right): so x = 12+223 = 235,
    # y = 174+24 = 198.
    page.add(TextFrame(
        x_mm=235, y_mm=198, w_mm=223, h_mm=24,
        layer=LAYER_TEXT,
        style="tent/headline",
        runs=[Run(text="Climate. Concrete.",
                  paragraph_style="tent/headline")],
        anname="Headline Panel B",
        rotation_deg=180,
    ))

    # Body Panel B — original (12, 113, 223, 56) → rotated bbox: x=235, y=169
    page.add(TextFrame(
        x_mm=235, y_mm=169, w_mm=223, h_mm=56,
        layer=LAYER_TEXT,
        style="tent/body",
        runs=[Run(
            text=("• Renewables: scale up\n"
                  "• Public transport: double\n"
                  "• Heat pump, not gas"),
            paragraph_style="tent/body",
        )],
        anname="Body Panel B",
        rotation_deg=180,
    ))

    # Logo Panel B (rotated 180°)
    if logo_cmyk.exists():
        lc2_data, lc2_ext = pack_inline_image(logo_cmyk.read_bytes(), "png")
        page.add(ImageFrame(
            x_mm=57, y_mm=210, w_mm=45, h_mm=14,
            inline_image_data=lc2_data, inline_image_ext=lc2_ext,
            scale_type=0, ratio=1,
            local_scale=(0.309, 0.336),
            layer=LAYER_BILDER,
            anname="Logo Grüne (cmyk, panel B)",
            rotation_deg=180,
        ))

    out_path = Path(out_path)
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

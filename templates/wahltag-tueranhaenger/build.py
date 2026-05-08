"""Wahltag-Türanhänger — DSL build entry point.

Spec: templates/_specs/wahltag-tueranhaenger.md.
Format: 105×250 mm vertikal, 2-seitig, 2 mm bleed (knapper als 3 mm wegen Stanze).

Front: Brand-Bar (Dunkelgrün) mit weißem Logo, Loch-Zone (35 mm rund), Wahlkreuz
auf Hellgrün, Headline + Bullet-Liste.
Back: Logo, optional Kandidat-Portrait, Name + Position, Kontakt + Impressum.
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
from sla_lib.builder.blocks import DoorHangerCutout  # noqa: E402


# ---------------------------------------------------------------------------
# Constants from spec
# ---------------------------------------------------------------------------
TRIM_W_MM = 105.0
TRIM_H_MM = 250.0
BLEED_MM = 2.0    # tighter than 3 mm for die-cut

# Layer indexes — match Document(layers=[...]) order below
LAYER_HINTERGRUND = 0
LAYER_BILDER = 1
LAYER_TEXT = 2
LAYER_STANZKONTUR = 3


def build(out_path: str | Path = HERE / "template.sla") -> None:
    doc = Document(
        brand=Brand.gruene_noe(),
        title="Wahltag-Türanhänger",
        template_id="wahltag-tueranhaenger",
        author="Die Grünen Niederösterreich",
        facing_pages=False,
        layers=[
            DocumentLayer(name="Hintergrund", visible=True, printable=True, flow=True),
            DocumentLayer(name="Bilder", visible=True, printable=True, flow=True),
            DocumentLayer(name="Text", visible=True, printable=True, flow=True),
            DocumentLayer(name="Stanzkontur", visible=True, printable=False, flow=False),
        ],
    )

    # Document-local Stanzkontur spot color (D4 revised — NOT in shared/ci.yml)
    doc.add_color("Stanzkontur", cmyk=(0, 100, 0, 0), spot=True)

    # Per-template ParaStyles
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/headline",
        font="Vollkorn Black Italic",
        fontsize=28,
        linesp=30,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/sub",
        font="Gotham Narrow Bold",
        fontsize=18,
        linesp=22,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/body",
        font="Gotham Narrow Book",
        fontsize=11,
        linesp=14,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/cand-name",
        font="Gotham Narrow Bold",
        fontsize=14,
        linesp=16,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/cand-pos",
        font="Gotham Narrow Book Italic",
        fontsize=10,
        linesp=12,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/url",
        font="Gotham Narrow Bold",
        fontsize=11,
        linesp=14,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/impressum",
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
        margins_mm=(8.0, 10.0, 8.0, 10.0),
    )
    page0 = doc.add_page(size=(TRIM_W_MM, TRIM_H_MM), bleed_mm=BLEED_MM,
                         margins_mm=(8.0, 10.0, 8.0, 10.0), master="Normal")
    page1 = doc.add_page(size=(TRIM_W_MM, TRIM_H_MM), bleed_mm=BLEED_MM,
                         margins_mm=(8.0, 10.0, 8.0, 10.0), master="Normal")

    # ---- PAGE 1: Front -------------------------------------------------
    # Brand-Bar Dunkelgrün top zone (over the hole-area's top, lets white logo show)
    page0.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=-BLEED_MM,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=20 + BLEED_MM,
        fill="Dunkelgrün",
        layer=LAYER_HINTERGRUND,
        anname="Brand-Bar (Vorderseite)",
    ))

    # Logo (white) on Brand-Bar — 35x10mm at 413x118px source → scale 0.24
    logo_weiss = HERE.parents[1] / "shared" / "logos" / "gruene-weiss.png"
    if logo_weiss.exists():
        lw_data, lw_ext = pack_inline_image(logo_weiss.read_bytes(), "png")
        page0.add(ImageFrame(
            x_mm=10, y_mm=8, w_mm=35, h_mm=10,
            inline_image_data=lw_data, inline_image_ext=lw_ext,
            scale_type=0, ratio=1,
            local_scale=(0.240, 0.240),
            layer=LAYER_BILDER,
            anname="Logo Grüne (weiss, top)",
        ))

    # Wahlkreuz hero on Hellgrün band (D12: not white, not yellow)
    wahlkreuz_path = HERE.parents[1] / "shared" / "assets" / "wahlkreuz.png"
    if not wahlkreuz_path.exists():
        raise FileNotFoundError(
            f"Wahlkreuz asset not found at {wahlkreuz_path}"
        )
    wahlkreuz_bytes = wahlkreuz_path.read_bytes()
    wk_data, wk_ext = pack_inline_image(wahlkreuz_bytes, "png")

    # Hellgrün band behind the Wahlkreuz (full-width, sits below the hole)
    page0.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=65,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=60,
        fill="Hellgrün",
        layer=LAYER_HINTERGRUND,
        anname="Hellgrün-Band (Wahlkreuz)",
    ))

    page0.add(ImageFrame(
        x_mm=27.5, y_mm=70, w_mm=50, h_mm=50,
        inline_image_data=wk_data,
        inline_image_ext=wk_ext,
        scale_type=0,
        ratio=1,
        layer=LAYER_BILDER,
        anname="Wahlkreuz (Hero)",
    ))

    # Headline — "Heute ist\nWahltag." on 2 lines (28pt Vollkorn Italic, 30pt
    # linesp → ~12 mm between baselines; needs h>=22 mm + ascender room ≈ 26 mm)
    page0.add(TextFrame(
        x_mm=10, y_mm=128, w_mm=85, h_mm=28,
        layer=LAYER_TEXT,
        style="tueranhaenger/headline",
        runs=[
            Run(text="Heute ist", separator="para",
                paragraph_style="tueranhaenger/headline"),
            Run(text="Wahltag.",
                paragraph_style="tueranhaenger/headline"),
        ],
        anname="Headline-Wahltag",
    ))

    # Sub-Headline — Wähle Grün.
    page0.add(TextFrame(
        x_mm=10, y_mm=160, w_mm=85, h_mm=12,
        layer=LAYER_TEXT,
        style="tueranhaenger/sub",
        runs=[Run(text="Wähle Grün.",
                  paragraph_style="tueranhaenger/sub")],
        anname="Sub-Headline",
    ))

    # Bullet list
    page0.add(TextFrame(
        x_mm=10, y_mm=175, w_mm=85, h_mm=60,
        layer=LAYER_TEXT,
        style="tueranhaenger/body",
        runs=[Run(
            text=("• Klima · Soziales · Bildung\n"
                  "• Vor Ort · Ehrlich · Faktenbasiert\n"
                  "• Mehr auf gruene-noe.at"),
            paragraph_style="tueranhaenger/body",
        )],
        anname="Bullet-Liste",
    ))

    # Impressum (Vorderseite)
    page0.add(TextFrame(
        x_mm=10, y_mm=240, w_mm=85, h_mm=6,
        layer=LAYER_TEXT,
        style="tueranhaenger/impressum",
        runs=[Run(
            text=("Medieninhaber: Die Grünen NÖ, "
                  "Daniel-Gran-Straße 48, 3100 St. Pölten."),
            paragraph_style="tueranhaenger/impressum",
        )],
        anname="Impressum",
    ))

    # Stanzkontur (Außen + Loch) — on top
    page0.add(DoorHangerCutout(
        page_size_mm=(TRIM_W_MM, TRIM_H_MM),
        hole_diameter_mm=35,
        hole_top_offset_mm=25,
        layer_idx=LAYER_STANZKONTUR,
    ))

    # ---- PAGE 2: Back --------------------------------------------------
    # Same brand bar at top (so the hole-edge prints clean on both sides)
    page1.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=-BLEED_MM,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=20 + BLEED_MM,
        fill="Dunkelgrün",
        layer=LAYER_HINTERGRUND,
        anname="Brand-Bar (Rückseite)",
    ))

    # Logo (white on Dunkelgrün, back)
    if logo_weiss.exists():
        lw_data2, lw_ext2 = pack_inline_image(logo_weiss.read_bytes(), "png")
        page1.add(ImageFrame(
            x_mm=10, y_mm=8, w_mm=35, h_mm=10,
            inline_image_data=lw_data2, inline_image_ext=lw_ext2,
            scale_type=0, ratio=1,
            local_scale=(0.240, 0.240),
            layer=LAYER_BILDER,
            anname="Logo Grüne (cmyk, back)",
        ))

    # Kandidat-Portrait placeholder (optional — slot stays present, image
    # injected by Codex demo or end user). scale_type=0 so any injected image
    # auto-fits the frame (matches all other photo slots in this issue's
    # templates after the 2026-05-08 scale_type fix).
    page1.add(ImageFrame(
        x_mm=20, y_mm=75, w_mm=65, h_mm=85,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="Kandidat-Portrait",
    ))

    # Kandidat-Name
    page1.add(TextFrame(
        x_mm=10, y_mm=168, w_mm=85, h_mm=10,
        layer=LAYER_TEXT,
        style="tueranhaenger/cand-name",
        runs=[Run(text="Maria Beispiel",
                  paragraph_style="tueranhaenger/cand-name")],
        anname="Kandidat-Name",
    ))

    # Kandidat-Position
    page1.add(TextFrame(
        x_mm=10, y_mm=178, w_mm=85, h_mm=8,
        layer=LAYER_TEXT,
        style="tueranhaenger/cand-pos",
        runs=[Run(text="Bürgermeisterkandidatin Mödling",
                  paragraph_style="tueranhaenger/cand-pos")],
        anname="Kandidat-Position",
    ))

    # Kontakt-URL — narrows to 50 mm so QR fits to its right (Issue #11).
    page1.add(TextFrame(
        x_mm=10, y_mm=200, w_mm=50, h_mm=8,
        layer=LAYER_TEXT,
        style="tueranhaenger/url",
        runs=[Run(text="gruene-moedling.at",
                  paragraph_style="tueranhaenger/url")],
        anname="Kontakt-URL",
    ))

    # Kontakt-Info — same narrowing.
    page1.add(TextFrame(
        x_mm=10, y_mm=210, w_mm=50, h_mm=20,
        layer=LAYER_TEXT,
        style="tueranhaenger/body",
        runs=[Run(text=("maria.beispiel@gruene-moedling.at\n"
                        "+43 660 1234567"),
                  paragraph_style="tueranhaenger/body")],
        anname="Kontakt-Info",
    ))

    # QR-back slot (Issue #11): 30x30 mm on right side of contact area.
    # URL encodes the lokale Listen-URL (~31 chars => version 4 = 33 modules,
    # 30 mm / 33 ≈ 0.91 mm/module — comfortably above D1's 0.5 mm minimum).
    # Conditional inject — only when samples/qr-back.png is committed.
    qr_back_path = HERE / "samples" / "qr-back.png"
    qr_data, qr_ext = (None, None)
    if qr_back_path.exists():
        qr_data, qr_ext = pack_inline_image(qr_back_path.read_bytes(), "png")
    page1.add(ImageFrame(
        x_mm=65, y_mm=200, w_mm=30, h_mm=30,
        inline_image_data=qr_data,
        inline_image_ext=qr_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="QR-Code (back)",
    ))

    # Impressum (back)
    page1.add(TextFrame(
        x_mm=10, y_mm=240, w_mm=85, h_mm=6,
        layer=LAYER_TEXT,
        style="tueranhaenger/impressum",
        runs=[Run(
            text=("Medieninhaber: Die Grünen NÖ, "
                  "Daniel-Gran-Straße 48, 3100 St. Pölten."),
            paragraph_style="tueranhaenger/impressum",
        )],
        anname="Impressum (back)",
    ))

    # Stanzkontur on back too (printer needs it on every page exporting to
    # same layer)
    page1.add(DoorHangerCutout(
        page_size_mm=(TRIM_W_MM, TRIM_H_MM),
        hole_diameter_mm=35,
        hole_top_offset_mm=25,
        layer_idx=LAYER_STANZKONTUR,
    ))

    out_path = Path(out_path)
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

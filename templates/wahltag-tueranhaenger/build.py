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
    library,
    # Issue #12 — composites + constraints
    same_x,
    same_style,
    distance_y,
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


def build_doc() -> Document:
    """Issue #12 D13: return constructed Document; persistence is the
    caller's job (CLI wrapper below or structural_check)."""
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
        linesp=25.2,
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

    # V1 (#18) — *-on-green parallel ParaStyles for Hellgrün/Dunkelgrün backings.
    # Pattern from #17 (postkarte-a6-quer V1). Originals stay unchanged.
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/body-on-green",
        font="Gotham Narrow Book",
        fontsize=11,
        linesp=14,
        linesp_mode=0,
        align=0,
        fcolor="White",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/url-on-green",
        font="Vollkorn Black Italic",
        fontsize=11,
        linesp=14,
        linesp_mode=0,
        align=0,
        fcolor="Gelb",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/cand-name-on-green",
        font="Gotham Narrow Bold",
        fontsize=18,           # bumped from 14 per ISSUE.md V1 spec
        linesp=20,
        linesp_mode=0,
        align=0,
        fcolor="White",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/cand-pos-on-green",
        font="Gotham Narrow Book Italic",
        fontsize=10,
        linesp=12,
        linesp_mode=0,
        align=0,
        fcolor="White",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="tueranhaenger/impressum-on-green",
        font="Gotham Narrow Book",
        fontsize=6,
        linesp=7,
        linesp_mode=0,
        align=0,
        fcolor="White",
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

    # Logo (white) on Dunkelgrün Brand-Bar (back, top) — matches front pattern.
    if logo_weiss.exists():
        lw_data2, lw_ext2 = pack_inline_image(logo_weiss.read_bytes(), "png")
        page1.add(ImageFrame(
            x_mm=10, y_mm=8, w_mm=35, h_mm=10,
            inline_image_data=lw_data2, inline_image_ext=lw_ext2,
            scale_type=0, ratio=1,
            local_scale=(0.240, 0.240),
            layer=LAYER_BILDER,
            anname="Logo Grüne (weiss, back-band)",
        ))

    # iter-3: Brand-Bund logo on the white area below the Brand-Bar.
    # Reinforces brand recognition on the contact side of the door-hanger.
    # On A6-format-equivalent (kurze Kante=105) Quickguide Print target
    # is 3×M = 18.9 mm — 18×16 mm sits at 95 % of target with the new
    # ~1.12:1 aspect. Positioned at x=68..86, y=24..40 (right of band's
    # white-logo, occupying the thin slot above the portrait at y=75).
    logo_brand_path = HERE.parents[1] / "shared" / "logos" / "gruene-logo-bund-dunkel.png"
    if logo_brand_path.exists():
        lb_data, lb_ext = pack_inline_image(logo_brand_path.read_bytes(), "png")
        page1.add(ImageFrame(
            x_mm=68, y_mm=24, w_mm=18, h_mm=16,
            inline_image_data=lb_data, inline_image_ext=lb_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            anname="Logo Grüne (Bund-Dunkel, back)",
        ))

    # Kandidat-Portrait — central library reference (#13). The
    # Bürgermeisterkandidat archetype (male for diversity per CONTEXT D2)
    # lives at portrait_stefan in the central library. Frame 65×85mm portrait
    # ratio (~0.76:1); source 1024×1536 (~0.67:1) — minor center-crop.
    # library.crop_for_frame re-stamps the watermark on the cropped output.
    portrait_data, portrait_ext = (None, None)
    portrait_img = library.load("portrait_stefan", optional=True)
    if portrait_img is not None:
        portrait_bytes = library.crop_for_frame(
            portrait_img, target_w_mm=65, target_h_mm=85
        )
        portrait_data, portrait_ext = pack_inline_image(portrait_bytes, "jpg")
    page1.add(ImageFrame(
        x_mm=20, y_mm=75, w_mm=65, h_mm=85,
        inline_image_data=portrait_data,
        inline_image_ext=portrait_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="Kandidat-Portrait",
    ))

    # Kandidat-Name — iter-3 changed to male persona to match the
    # Bürgermeisterkandidat portrait (CONTEXT.md D2 diversity guidance).
    page1.add(TextFrame(
        x_mm=10, y_mm=168, w_mm=85, h_mm=10,
        layer=LAYER_TEXT,
        style="tueranhaenger/cand-name",
        runs=[Run(text="Stefan Beispiel",
                  paragraph_style="tueranhaenger/cand-name")],
        anname="Kandidat-Name",
    ))

    # Kandidat-Position
    page1.add(TextFrame(
        x_mm=10, y_mm=178, w_mm=85, h_mm=8,
        layer=LAYER_TEXT,
        style="tueranhaenger/cand-pos",
        runs=[Run(text="Bürgermeisterkandidat Mödling",
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
        runs=[Run(text=("stefan.beispiel@gruene-moedling.at\n"
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

    return doc


def build(out_path: str | Path = HERE / "template.sla") -> Path:
    doc = build_doc()
    out_path = Path(out_path)
    doc.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Issue #12 — module-level CONSTRAINTS list (read by structural_check).
#
# The Türanhänger has minor structural symmetry (front + back panels share
# x=10 left margin / x=20 portrait alignment) and a clear hierarchy
# (Headline -> Sub -> Bullet body) on the front panel. CONSTRAINTS below
# capture the alignment + hierarchy invariants in pure metadata form.
# ---------------------------------------------------------------------------
CONSTRAINTS = [
    # Front-panel left edge alignment: Headline / Sub / Bullets / Impressum
    # all start at x=10mm.
    same_x(
        "Headline-Wahltag", "Sub-Headline", "Bullet-Liste", "Impressum",
        name="front_panel_left_edge",
    ),
    # HL -> SL distance (top of HL at y=128, top of SL at y=160 — gap 32mm).
    distance_y(
        "Headline-Wahltag", "Sub-Headline", equals=32.0,
        name="front_hl_to_sl_distance",
    ),
    # Style consistency check: the impressum on both pages uses the same style.
    same_style(
        "Impressum", "Impressum (back)",
        name="impressum_style_consistent",
    ),
    # Back-panel: Kandidat-Name and Kandidat-Position share x for clean
    # left-aligned candidate caption block.
    same_x(
        "Kandidat-Name", "Kandidat-Position",
        name="back_kandidat_caption_left_edge",
    ),
]


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

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
    same_size,
    same_style,
    distance_y,
    aligned_below,
    mirrored_x,
    inside,
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
    # V1 (#18): Brand-Bar shrunk 20→14 mm visible (16 incl. bleed) so the
    # Hellgrün-Akzent strip can sit directly below it.
    page0.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=-BLEED_MM,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=14 + BLEED_MM,
        fill="Dunkelgrün",
        layer=LAYER_HINTERGRUND,
        anname="Brand-Bar (Vorderseite)",
    ))

    # Logo (white) on Brand-Bar — V1 (#18): 18.9×5.7 mm = 3×M Quickguide-konform.
    logo_weiss = HERE.parents[1] / "shared" / "logos" / "gruene-weiss.png"
    if not logo_weiss.exists():
        raise FileNotFoundError(
            f"Required brand asset missing: {logo_weiss}"
        )
    lw_data, lw_ext = pack_inline_image(logo_weiss.read_bytes(), "png")
    page0.add(ImageFrame(
        x_mm=10, y_mm=8, w_mm=18.9, h_mm=5.7,
        inline_image_data=lw_data, inline_image_ext=lw_ext,
        scale_type=0, ratio=1,
        local_scale=(0.130, 0.130),
        layer=LAYER_BILDER,
        anname="Logo Grüne (weiss, top)",
    ))

    # V1 (#18): Hellgrün-Akzent — 4 mm strip directly under Brand-Bar (touches
    # at y=14). Reinforces brand stripe across the hole's top approach.
    page0.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=14,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=4,
        fill="Hellgrün",
        layer=LAYER_HINTERGRUND,
        anname="Hellgrün-Akzent",
    ))

    # Wahlkreuz hero on Hellgrün band (D12: not white, not yellow)
    wahlkreuz_path = HERE.parents[1] / "shared" / "assets" / "wahlkreuz.png"
    if not wahlkreuz_path.exists():
        raise FileNotFoundError(
            f"Wahlkreuz asset not found at {wahlkreuz_path}"
        )
    wahlkreuz_bytes = wahlkreuz_path.read_bytes()
    wk_data, wk_ext = pack_inline_image(wahlkreuz_bytes, "png")

    # Hellgrün band behind the Wahlkreuz — V1 (#18): y 65→63, h 60→64
    # (hosts the now larger 55×55 Wahlkreuz hero).
    page0.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=63,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=64,
        fill="Hellgrün",
        layer=LAYER_HINTERGRUND,
        anname="Hellgrün-Band (Wahlkreuz)",
    ))

    # V1 (#18): Wahlkreuz centered on panel x=52.5 (25..80 × 70..125)
    page0.add(ImageFrame(
        x_mm=25, y_mm=70, w_mm=55, h_mm=55,
        inline_image_data=wk_data,
        inline_image_ext=wk_ext,
        scale_type=0,
        ratio=1,
        layer=LAYER_BILDER,
        anname="Wahlkreuz (Hero)",
    ))

    # Headline — "Heute ist\nWahltag." on 2 lines (28pt Vollkorn Italic,
    # V1 (#18): linesp 30→25.2 (Quickguide-konform 0.9×); y 128→138, h 28→32.
    page0.add(TextFrame(
        x_mm=10, y_mm=138, w_mm=85, h_mm=32,
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

    # Sub-Headline — Wähle Grün. V1 (#18): y 160→176.
    page0.add(TextFrame(
        x_mm=10, y_mm=176, w_mm=85, h_mm=12,
        layer=LAYER_TEXT,
        style="tueranhaenger/sub",
        runs=[Run(text="Wähle Grün.",
                  paragraph_style="tueranhaenger/sub")],
        anname="Sub-Headline",
    ))

    # V1 (#18): Bullets-Card — full-bleed Hellgrün backing (-2..107 × 192..250)
    # behind the bullet list and impressum at the bottom of the front panel.
    page0.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=192,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=58,
        fill="Hellgrün",
        layer=LAYER_HINTERGRUND,
        anname="Bullets-Card",
    ))

    # Bullet list — V1 (#18): y 175→200, h 60→40, white-on-green via
    # tueranhaenger/body-on-green ParaStyle.
    page0.add(TextFrame(
        x_mm=10, y_mm=200, w_mm=85, h_mm=40,
        layer=LAYER_TEXT,
        style="tueranhaenger/body-on-green",
        runs=[Run(
            text=("• Klima · Soziales · Bildung\n"
                  "• Vor Ort · Ehrlich · Faktenbasiert\n"
                  "• Mehr auf gruene-noe.at"),
            paragraph_style="tueranhaenger/body-on-green",
        )],
        anname="Bullet-Liste",
    ))

    # Impressum (Vorderseite) — V1 (#18): white-on-green via
    # tueranhaenger/impressum-on-green. Known WCAG concern (~1.7:1) — surfaced
    # in the spec as future-iteration follow-up; geometry stays for V1.
    page0.add(TextFrame(
        x_mm=10, y_mm=240, w_mm=85, h_mm=6,
        layer=LAYER_TEXT,
        style="tueranhaenger/impressum-on-green",
        runs=[Run(
            text=("Medieninhaber: Die Grünen NÖ, "
                  "Daniel-Gran-Straße 48, 3100 St. Pölten."),
            paragraph_style="tueranhaenger/impressum-on-green",
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
    # V1 (#18): Brand-Bar mirrors front (14 mm visible, 16 incl. bleed).
    page1.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=-BLEED_MM,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=14 + BLEED_MM,
        fill="Dunkelgrün",
        layer=LAYER_HINTERGRUND,
        anname="Brand-Bar (Rückseite)",
    ))

    # Logo (white) on Dunkelgrün Brand-Bar (back, top) — V1 (#18): mirrors front
    # logo geometry (18.9×5.7 mm, local_scale 0.130). logo_weiss verified above.
    lw_data2, lw_ext2 = pack_inline_image(logo_weiss.read_bytes(), "png")
    page1.add(ImageFrame(
        x_mm=10, y_mm=8, w_mm=18.9, h_mm=5.7,
        inline_image_data=lw_data2, inline_image_ext=lw_ext2,
        scale_type=0, ratio=1,
        local_scale=(0.130, 0.130),
        layer=LAYER_BILDER,
        anname="Logo Grüne (weiss, back-band)",
    ))

    # V1 (#18): the iter-3 second back-logo (kurze-Kante 3×M Bund-dark) was
    # removed — see #18 RESEARCH for the double-logo elimination rationale.
    # The shared logo asset stays on disk; four other templates still use it.

    # V1 (#18): Portrait-Card — Hellgrün backing for Kandidat-Portrait
    # (15..90 × 70..170). Portrait sits with 5 mm uniform inset on left/top/right.
    page1.add(Polygon(
        x_mm=15,
        y_mm=70,
        w_mm=75,
        h_mm=100,
        fill="Hellgrün",
        layer=LAYER_HINTERGRUND,
        anname="Portrait-Card",
    ))

    # Kandidat-Portrait — central library reference (#13). The
    # Bürgermeisterkandidat archetype (male for diversity per CONTEXT D2)
    # lives at portrait_stefan in the central library. V1 (#18): h 85→90 so
    # portrait nests into Portrait-Card with 5 mm bottom inset (75..165 vs
    # card 70..170).
    portrait_data, portrait_ext = (None, None)
    portrait_img = library.load("portrait_stefan", optional=True)
    if portrait_img is not None:
        portrait_bytes = library.crop_for_frame(
            portrait_img, target_w_mm=65, target_h_mm=90
        )
        portrait_data, portrait_ext = pack_inline_image(portrait_bytes, "jpg")
    page1.add(ImageFrame(
        x_mm=20, y_mm=75, w_mm=65, h_mm=90,
        inline_image_data=portrait_data,
        inline_image_ext=portrait_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="Kandidat-Portrait",
    ))

    # Kandidat-Name — V1 (#18): y 168→184; switched to
    # tueranhaenger/cand-name-on-green (18 pt White) for Visitenkarten-Footer.
    page1.add(TextFrame(
        x_mm=10, y_mm=184, w_mm=85, h_mm=10,
        layer=LAYER_TEXT,
        style="tueranhaenger/cand-name-on-green",
        runs=[Run(text="Stefan Beispiel",
                  paragraph_style="tueranhaenger/cand-name-on-green")],
        anname="Kandidat-Name",
    ))

    # Kandidat-Position — V1 (#18): y 178→196; tueranhaenger/cand-pos-on-green.
    # NOTE: ISSUE.md prescribed "opacity 85%" — DSL has no TextFrame opacity
    # field, so V1 uses solid white (RESEARCH.md locked decision #6).
    page1.add(TextFrame(
        x_mm=10, y_mm=196, w_mm=85, h_mm=8,
        layer=LAYER_TEXT,
        style="tueranhaenger/cand-pos-on-green",
        runs=[Run(text="Bürgermeisterkandidat Mödling",
                  paragraph_style="tueranhaenger/cand-pos-on-green")],
        anname="Kandidat-Position",
    ))

    # V1 (#18): Visitenkarten-Footer — Dunkelgrün full-bleed bottom 72 mm
    # (-2..107 × 178..250). Encloses Kandidat-Name/Position, Kontakt-URL/Info,
    # Impressum (back) — visually unifies the contact "card".
    page1.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=178,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=72,
        fill="Dunkelgrün",
        layer=LAYER_HINTERGRUND,
        anname="Visitenkarten-Footer",
    ))

    # Kontakt-URL — V1 (#18): y 200→210; Vollkorn Black Italic Gelb on
    # Dunkelgrün via tueranhaenger/url-on-green.
    page1.add(TextFrame(
        x_mm=10, y_mm=210, w_mm=50, h_mm=8,
        layer=LAYER_TEXT,
        style="tueranhaenger/url-on-green",
        runs=[Run(text="gruene-moedling.at",
                  paragraph_style="tueranhaenger/url-on-green")],
        anname="Kontakt-URL",
    ))

    # Kontakt-Info — V1 (#18): y 210→218; white-on-Dunkelgrün via
    # tueranhaenger/body-on-green.
    page1.add(TextFrame(
        x_mm=10, y_mm=218, w_mm=50, h_mm=20,
        layer=LAYER_TEXT,
        style="tueranhaenger/body-on-green",
        runs=[Run(text=("stefan.beispiel@gruene-moedling.at\n"
                        "+43 660 1234567"),
                  paragraph_style="tueranhaenger/body-on-green")],
        anname="Kontakt-Info",
    ))

    # QR-back slot (Issue #11) — V1 (#18): x 65→70, y 200→210, w 30→26, h 30→26.
    # 26 mm / 33 modules ≈ 0.79 mm/module — still above D1's 0.5 mm minimum.
    qr_back_path = HERE / "samples" / "qr-back.png"
    if not qr_back_path.exists():
        raise FileNotFoundError(f"Required QR asset missing: {qr_back_path}")
    qr_data, qr_ext = pack_inline_image(qr_back_path.read_bytes(), "png")
    page1.add(ImageFrame(
        x_mm=70, y_mm=210, w_mm=26, h_mm=26,
        inline_image_data=qr_data,
        inline_image_ext=qr_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="QR-Code (back)",
    ))

    # V1 (#18): QR White-Backing — White polygon (68..98 × 208..238) provides
    # contrast for the QR on Dunkelgrün Visitenkarten-Footer. White is NOT in
    # FILLED_POLYGON_FILLS so this is excluded from brand:image_text_overlap
    # detection. On LAYER_HINTERGRUND so it paints behind the QR (which is
    # on LAYER_BILDER) regardless of code order.
    page1.add(Polygon(
        x_mm=68,
        y_mm=208,
        w_mm=30,
        h_mm=30,
        fill="White",
        layer=LAYER_HINTERGRUND,
        anname="QR White-Backing",
    ))

    # Impressum (back) — V1 (#18): y 240→242; tueranhaenger/impressum-on-green.
    page1.add(TextFrame(
        x_mm=10, y_mm=242, w_mm=85, h_mm=6,
        layer=LAYER_TEXT,
        style="tueranhaenger/impressum-on-green",
        runs=[Run(
            text=("Medieninhaber: Die Grünen NÖ, "
                  "Daniel-Gran-Straße 48, 3100 St. Pölten."),
            paragraph_style="tueranhaenger/impressum-on-green",
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
# Issue #18 — V1 "Composed Hero" CONSTRAINTS list (read by structural_check).
#
# Captures the alignment contracts of the Composed-Hero composition:
# - FRONT: Brand-Bar → Hellgrün-Akzent (touching), Wahlkreuz centered & inside
#   Hellgrün-Band, Headline → Sub stack with format-pragmatic gap, Bullets-Card
#   full-bleed bottom enclosing Bullet-Liste.
# - BACK : Brand-Bar mirror (height pair), Portrait inside Portrait-Card,
#   Kandidat-Name → Kandidat-Position stack, Visitenkarten-Footer enclosing
#   URL/Info, QR White-Backing enclosing QR.
# Annames match build.py exactly (case-sensitive, German + parenthesized).
# ---------------------------------------------------------------------------
CONSTRAINTS = [
    # FRONT — Hellgrün-Akzent below Brand-Bar (touching, gap 0)
    aligned_below("Hellgrün-Akzent", "Brand-Bar (Vorderseite)",
                  gap_mm=0.0, name="akzent_below_brandbar"),
    # FRONT — Hellgrün-Band absolute y-pin via distance_y to Akzent
    # (|14 - 63| = 49 mm; both polygons share full-bleed x, so x-equality is
    # implied by their construction, not by aligned_below).
    distance_y("Hellgrün-Akzent", "Hellgrün-Band (Wahlkreuz)",
               equals=49.0, name="band_below_akzent_49mm"),
    # FRONT — Wahlkreuz centered on panel (panel center x=52.5)
    mirrored_x("Hellgrün-Band (Wahlkreuz)", "Wahlkreuz (Hero)",
               axis_mm=52.5, name="wahlkreuz_panel_center"),
    # FRONT — Wahlkreuz inside Hellgrün-Band
    inside("Wahlkreuz (Hero)", "Hellgrün-Band (Wahlkreuz)",
           name="wahlkreuz_in_band"),
    # FRONT — Headline absolute y-pin via distance_y to Hellgrün-Band
    # (text x=10, band x=-2 — no x-alignment, so use distance_y not aligned_below).
    # |138 - 63| = 75 mm.
    distance_y("Hellgrün-Band (Wahlkreuz)", "Headline-Wahltag",
               equals=75.0, name="headline_below_band_75mm"),
    # FRONT — HL→Sub distance (38mm pragmatic for 250mm format)
    distance_y("Headline-Wahltag", "Sub-Headline",
               equals=38.0, name="hl_to_sub_38mm_format_pragmatic"),
    # FRONT — Bullets-Card and Hellgrün-Akzent share full-bleed x (both x=-2)
    same_x("Bullets-Card", "Hellgrün-Akzent",
           name="bullets_card_full_bleed_x"),
    # FRONT — Bullet-Liste inside Bullets-Card
    inside("Bullet-Liste", "Bullets-Card", name="bullets_in_card"),

    # BACK — Brand-Bar mirror of front (same height)
    same_size("Brand-Bar (Vorderseite)", "Brand-Bar (Rückseite)",
              axis="h", name="brand_bar_h_pair"),
    # BACK — Portrait inside Portrait-Card (5mm uniform inset)
    inside("Kandidat-Portrait", "Portrait-Card",
           name="portrait_in_card"),
    # BACK — Kandidat-Name absolute y-pin via distance_y to Portrait
    # (text x=10, portrait x=20 — no x-alignment, so distance_y not aligned_below).
    # |184 - 75| = 109 mm.
    distance_y("Kandidat-Portrait", "Kandidat-Name",
               equals=109.0, name="name_below_portrait_109mm"),
    # BACK — Kandidat-Position below Name (both at x=10, gap 2mm: 184+10+2=196)
    aligned_below("Kandidat-Position", "Kandidat-Name",
                  gap_mm=2.0, name="position_below_name"),
    # BACK — Kontakt-URL on Visitenkarten-Footer
    inside("Kontakt-URL", "Visitenkarten-Footer", name="url_in_footer"),
    inside("Kontakt-Info", "Visitenkarten-Footer", name="info_in_footer"),
    # BACK — QR backing fully contains QR
    inside("QR-Code (back)", "QR White-Backing", name="qr_in_backing"),
]


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

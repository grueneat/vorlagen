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

from sla_lib.builder import library  # noqa: E402
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
    # Issue #12 / #20 — constraints
    aligned_below,
    inside,
    mirrored_y,
    same_size,
    same_style,
    same_x,
    same_y,
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


# Post-#24 INJECT_MAP idiom (#19 RESEARCH §1, locked decision #1):
# value = bare lib_id (manifest key). build_preview() reads target_w_mm /
# target_h_mm LIVE from each frame, eliminating literal-target drift.
INJECT_MAP: dict[str, str] = {
    "Hintergrund-Mitmachen":         "kontext_infostand_szene",
    "Hintergrund-Mitmachen Panel B": "kontext_infostand_szene",
}


# ---------------------------------------------------------------------------
# V1 "Hero Band" — asset paths used by both panels.
# ---------------------------------------------------------------------------
LOGO_GRUENE_WEISS = HERE.parents[1] / "shared" / "logos" / "gruene-weiss.png"
QR_MITMACHEN = HERE / "samples" / "qr-mitmachen.png"


def _logo_inline() -> tuple[str | None, str | None]:
    """Read shared/logos/gruene-weiss.png as (data, ext) for ImageFrame."""
    if not LOGO_GRUENE_WEISS.exists():
        return (None, None)
    return pack_inline_image(LOGO_GRUENE_WEISS.read_bytes(), "png")


def _qr_inline() -> tuple[str | None, str | None]:
    """Read samples/qr-mitmachen.png as (data, ext) for ImageFrame."""
    if not QR_MITMACHEN.exists():
        return (None, None)
    return pack_inline_image(QR_MITMACHEN.read_bytes(), "png")


def _panel_de() -> list:
    """Panel A (DE, upright) — 12 V1 primitives in flat-sheet absolute coords.

    Layout zones (y axis):
      0..42   Hero-Band Dunkelgrün polygon (full bleed) — apex side
      6..36   Logo (left) + Headline (right) + Pay-off (right) inside hero-band
     39..72   Photo-Backing Dunkelgrün polygon + Photo (full-bleed 297×33)
     78..94   White zone — QR-Code (left) + Bullets + Termine
     95..105  Footer-Strip Hellgrün polygon — CTA-Footer + Impressum (right)
    """
    logo_data, logo_ext = _logo_inline()
    qr_data, qr_ext = _qr_inline()
    return [
        # 1. Hero-Band polygon (full bleed top of Panel A, apex side)
        Polygon(
            x_mm=-3, y_mm=-3, w_mm=303, h_mm=42,
            fill="Dunkelgrün",
            layer=LAYER_HINTERGRUND,
            rotation_deg=0,
            anname="Hero-Band Panel A",
        ),
        # 2. Logo (white wordmark on Dunkelgrün)
        ImageFrame(
            x_mm=12, y_mm=6, w_mm=38, h_mm=30,
            inline_image_data=logo_data,
            inline_image_ext=logo_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            rotation_deg=0,
            anname="Logo Grüne (panel A)",
        ),
        # 3. Headline (white-on-Dunkelgrün, 26pt Vollkorn Italic)
        TextFrame(
            x_mm=55, y_mm=9, w_mm=230, h_mm=18,
            layer=LAYER_TEXT,
            rotation_deg=0,
            style="tent/headline",
            runs=[Run(text="Klimaschutz konkret.",
                      paragraph_style="tent/headline")],
            anname="Headline Panel A",
        ),
        # 4. Pay-off (Gelb 16pt Vollkorn Italic — sub-headline)
        TextFrame(
            x_mm=55, y_mm=27, w_mm=230, h_mm=8,
            layer=LAYER_TEXT,
            rotation_deg=0,
            style="tent/payoff",
            runs=[Run(text="Konkret. Lokal. Jetzt.",
                      paragraph_style="tent/payoff")],
            anname="Pay-off Panel A",
        ),
        # 5. Photo-Backing polygon (Dunkelgrün safety bg under photo)
        Polygon(
            x_mm=-3, y_mm=39, w_mm=303, h_mm=33,
            fill="Dunkelgrün",
            layer=LAYER_HINTERGRUND,
            rotation_deg=0,
            anname="Photo-Backing Panel A",
        ),
        # 6. Hintergrund-Mitmachen photo — populated by build_preview INJECT_MAP
        ImageFrame(
            x_mm=0, y_mm=39, w_mm=297, h_mm=33,
            inline_image_data=None,
            inline_image_ext=None,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            rotation_deg=0,
            anname="Hintergrund-Mitmachen",
        ),
        # 7. QR-Code (D1-conformant 17×17 mm in white zone, NOT in footer)
        ImageFrame(
            x_mm=12, y_mm=78, w_mm=17, h_mm=17,
            inline_image_data=qr_data,
            inline_image_ext=qr_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            rotation_deg=0,
            anname="QR-Code (mitmachen, panel A)",
        ),
        # 8. Body / Bullets (2 short bullets at 12pt — drops V0 third bullet)
        TextFrame(
            x_mm=32, y_mm=78, w_mm=110, h_mm=16,
            layer=LAYER_TEXT,
            rotation_deg=0,
            style="tent/body",
            runs=[Run(
                text=("• Erneuerbare Energie für alle\n"
                      "• Leistbares Wohnen schützen"),
                paragraph_style="tent/body",
            )],
            anname="Body Panel A",
        ),
        # 9. Termine (2 lines at 9pt — drops "Nächste Termine" header)
        TextFrame(
            x_mm=152, y_mm=78, w_mm=133, h_mm=16,
            layer=LAYER_TEXT,
            rotation_deg=0,
            style="tent/termine",
            runs=[Run(
                text=("• 12. Juni — Klimastammtisch\n"
                      "• 26. Juni — Bezirkstreffen"),
                paragraph_style="tent/termine",
            )],
            anname="Termine Panel A",
        ),
        # 10. Footer-Strip polygon (Hellgrün, full bleed, at apex)
        Polygon(
            x_mm=-3, y_mm=95, w_mm=303, h_mm=10,
            fill="Hellgrün",
            layer=LAYER_HINTERGRUND,
            rotation_deg=0,
            anname="Footer-Strip Panel A",
        ),
        # 11. CTA-Footer (white-on-Hellgrün URL — 11pt Gotham Bold)
        TextFrame(
            x_mm=12, y_mm=97, w_mm=200, h_mm=6,
            layer=LAYER_TEXT,
            rotation_deg=0,
            style="tent/cta-footer",
            runs=[Run(text="gruene-noe.at/mitmachen",
                      paragraph_style="tent/cta-footer")],
            anname="CTA-Footer Panel A",
        ),
        # 12. Impressum (right-aligned white 6pt — fills footer-strip right edge)
        TextFrame(
            x_mm=215, y_mm=97, w_mm=80, h_mm=6,
            layer=LAYER_TEXT,
            rotation_deg=0,
            style="tent/impressum",
            runs=[Run(
                text="Medieninhaber: Die Grünen NÖ — gruene-noe.at",
                paragraph_style="tent/impressum",
            )],
            anname="Impressum (Tent)",
        ),
    ]


def _panel_en() -> list:
    """Panel B (EN, rotated 180°) — 12 V1 primitives, mirror+rotate of Panel A.

    SLA math (per-frame):
      Text/Image at Panel-A-LOCAL (x, y, w, h)  → SLA (x+w, 210-y, w, h, ROT=180)
      Polygon    at Panel-A-LOCAL (x, y, w, h)  → SLA (x, 210-y-h, w, h, ROT=0)

    Polygons stay rotation_deg=0 (rectangles need no visual rotation); only
    Text/Image frames carry ROT=180 + bbox-corner SLA coords. The Hellgrün
    Footer-Strip pair (Panel A 95..105 + Panel B 105..115) abuts the apex
    forming a 20 mm Hellgrün band straddling the fold (RESEARCH §3).
    """
    logo_data, logo_ext = _logo_inline()
    qr_data, qr_ext = _qr_inline()
    return [
        # 1. Hero-Band polygon (Panel A (-3, -3, 303, 42) → (-3, 171, 303, 42))
        Polygon(
            x_mm=-3, y_mm=171, w_mm=303, h_mm=42,
            fill="Dunkelgrün",
            layer=LAYER_HINTERGRUND,
            rotation_deg=0,
            anname="Hero-Band Panel B",
        ),
        # 2. Logo (Panel A (12, 6, 38, 30) → (50, 204, 38, 30, ROT=180))
        ImageFrame(
            x_mm=50, y_mm=204, w_mm=38, h_mm=30,
            inline_image_data=logo_data,
            inline_image_ext=logo_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            rotation_deg=180,
            anname="Logo Grüne (panel B)",
        ),
        # 3. Headline (Panel A (55, 9, 230, 18) → (285, 201, 230, 18, ROT=180))
        TextFrame(
            x_mm=285, y_mm=201, w_mm=230, h_mm=18,
            layer=LAYER_TEXT,
            rotation_deg=180,
            style="tent/headline",
            runs=[Run(text="Climate. Concrete.",
                      paragraph_style="tent/headline")],
            anname="Headline Panel B",
        ),
        # 4. Pay-off (Panel A (55, 27, 230, 8) → (285, 183, 230, 8, ROT=180))
        TextFrame(
            x_mm=285, y_mm=183, w_mm=230, h_mm=8,
            layer=LAYER_TEXT,
            rotation_deg=180,
            style="tent/payoff",
            runs=[Run(text="Concrete. Local. Now.",
                      paragraph_style="tent/payoff")],
            anname="Pay-off Panel B",
        ),
        # 5. Photo-Backing polygon (Panel A (-3, 39, 303, 33) → (-3, 138, 303, 33))
        Polygon(
            x_mm=-3, y_mm=138, w_mm=303, h_mm=33,
            fill="Dunkelgrün",
            layer=LAYER_HINTERGRUND,
            rotation_deg=0,
            anname="Photo-Backing Panel B",
        ),
        # 6. Hintergrund-Mitmachen Panel B (Panel A (0, 39, 297, 33) → (297, 171, 297, 33, ROT=180))
        # Populated by build_preview() via INJECT_MAP entry declared in T02.
        ImageFrame(
            x_mm=297, y_mm=171, w_mm=297, h_mm=33,
            inline_image_data=None,
            inline_image_ext=None,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            rotation_deg=180,
            anname="Hintergrund-Mitmachen Panel B",
        ),
        # 7. QR-Code (Panel A (12, 78, 17, 17) → (29, 132, 17, 17, ROT=180))
        ImageFrame(
            x_mm=29, y_mm=132, w_mm=17, h_mm=17,
            inline_image_data=qr_data,
            inline_image_ext=qr_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            rotation_deg=180,
            anname="QR-Code (mitmachen, panel B)",
        ),
        # 8. Body / Bullets (Panel A (32, 78, 110, 16) → (142, 132, 110, 16, ROT=180))
        TextFrame(
            x_mm=142, y_mm=132, w_mm=110, h_mm=16,
            layer=LAYER_TEXT,
            rotation_deg=180,
            style="tent/body",
            runs=[Run(
                text=("• Renewable energy for all\n"
                      "• Affordable housing"),
                paragraph_style="tent/body",
            )],
            anname="Body Panel B",
        ),
        # 9. Termine (Panel A (152, 78, 133, 16) → (285, 132, 133, 16, ROT=180))
        TextFrame(
            x_mm=285, y_mm=132, w_mm=133, h_mm=16,
            layer=LAYER_TEXT,
            rotation_deg=180,
            style="tent/termine",
            runs=[Run(
                text=("• Jun 12 — Climate Stammtisch\n"
                      "• Jun 26 — District meeting"),
                paragraph_style="tent/termine",
            )],
            anname="Termine Panel B",
        ),
        # 10. Footer-Strip polygon (Panel A (-3, 95, 303, 10) → (-3, 105, 303, 10))
        Polygon(
            x_mm=-3, y_mm=105, w_mm=303, h_mm=10,
            fill="Hellgrün",
            layer=LAYER_HINTERGRUND,
            rotation_deg=0,
            anname="Footer-Strip Panel B",
        ),
        # 11. CTA-Footer (Panel A (12, 97, 200, 6) → (212, 113, 200, 6, ROT=180))
        TextFrame(
            x_mm=212, y_mm=113, w_mm=200, h_mm=6,
            layer=LAYER_TEXT,
            rotation_deg=180,
            style="tent/cta-footer",
            runs=[Run(text="noe.gruene.at/joinus",
                      paragraph_style="tent/cta-footer")],
            anname="CTA-Footer Panel B",
        ),
        # 12. Impressum Panel B (Panel A (215, 97, 80, 6) → (295, 113, 80, 6, ROT=180))
        TextFrame(
            x_mm=295, y_mm=113, w_mm=80, h_mm=6,
            layer=LAYER_TEXT,
            rotation_deg=180,
            style="tent/impressum",
            runs=[Run(
                text="Medieninhaber: Die Grünen NÖ — gruene-noe.at",
                paragraph_style="tent/impressum",
            )],
            anname="Impressum (Tent, panel B)",
        ),
    ]


def build_template() -> Document:
    """Issue #12 D13: return constructed Document; persistence is the
    caller's job (CLI wrapper below or structural_check).

    Round-trip stability: produces the SLA without inline image data on
    INJECT_MAP frames (clean for structural_check + spec_check).
    build_preview() wraps this and injects library images for actual
    rendering (page-01.png + preview.pdf)."""
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

    # Per-template ParaStyles — V1 "Hero Band" mutation pattern (#20).
    # Headline: white-on-Dunkelgrün, sized down from 36→26 to match V1 hero-band height.
    doc.add_para_style(ParaStyle(
        name="tent/headline",
        font="Vollkorn Black Italic",
        fontsize=26,
        linesp=23.4,
        linesp_mode=0,
        align=0,
        fcolor="White",
        language="de",
    ))
    # Body: bullets in white zone — fontsize trimmed 14→12 to fit 16 mm h with 2 short bullets.
    doc.add_para_style(ParaStyle(
        name="tent/body",
        font="Gotham Narrow Book",
        fontsize=12,
        linesp=15.6,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))
    # Termine: trimmed 10→9 to fit 2 lines in 16 mm h (drops the V0 "Nächste Termine" header).
    doc.add_para_style(ParaStyle(
        name="tent/termine",
        font="Gotham Narrow Book",
        fontsize=9,
        linesp=11.7,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))
    # Impressum: white-on-Hellgrün, right-aligned (align=2), bumped 5→6 for footer-strip legibility.
    doc.add_para_style(ParaStyle(
        name="tent/impressum",
        font="Gotham Narrow Book",
        fontsize=6,
        linesp=7.8,
        linesp_mode=0,
        align=2,
        fcolor="White",
        language="de",
    ))
    # NEW V1: Pay-off — Vollkorn Italic 16pt Gelb, sits below Headline in hero-band.
    doc.add_para_style(ParaStyle(
        name="tent/payoff",
        font="Vollkorn Black Italic",
        fontsize=16,
        linesp=14.4,
        linesp_mode=0,
        align=0,
        fcolor="Gelb",
        language="de",
    ))
    # NEW V1: CTA-Footer — Gotham Bold 11pt White, lives in Hellgrün footer-strip.
    doc.add_para_style(ParaStyle(
        name="tent/cta-footer",
        font="Gotham Narrow Bold",
        fontsize=11,
        linesp=14,
        linesp_mode=0,
        align=0,
        fcolor="White",
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

    # ---- PANEL A (y=0..105) — V1 "Hero Band", upright DE -------------------
    for prim in _panel_de():
        page.add(prim)

    # ---- FOLD LINE at y=105 ---------------------------------------------
    page.add(TableTentFold(page_size_mm=(TRIM_W_MM, TRIM_H_MM),
                          layer_idx=LAYER_FALZ))

    # ---- PANEL B (y=105..210) — V1 "Hero Band", EN 180° -------------------
    for prim in _panel_en():
        page.add(prim)

    return doc


def build_preview() -> Document:
    """Inject demo library images for gallery PNG render (#24 idiom).

    Pattern: pre-crops the source image to each frame's LIVE dimensions
    via library.inject_into_frame, eliminating the literal-target drift
    that produced regressions in earlier iters.
    """
    doc = build_template()
    if not INJECT_MAP:
        return doc
    for page in doc.pages:
        for item in page.items:
            if not isinstance(item, ImageFrame):
                continue
            lib_id = INJECT_MAP.get(item.anname)
            if not lib_id:
                continue
            img = library.load(lib_id, optional=True)
            if img is None:
                continue
            library.inject_into_frame(
                item, img,
                target_w_mm=item.w_mm,   # LIVE frame dims (post-#24)
                target_h_mm=item.h_mm,
            )
    return doc


# Alias for structural_check / spec_check / smoke — they expect build_doc.
# Keep this alias indefinitely; it points at the clean template (no photos).
build_doc = build_template


def build(out_path: str | Path = HERE / "template.sla") -> Path:
    doc = build_preview()
    out_path = Path(out_path)
    doc.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Issue #20 — V1 "Hero Band" CONSTRAINTS list (read by structural_check).
#
# Cross-panel rules limited to rotation-invariant kinds: mirrored_y on
# Polygons (both rotation_deg=0), same_size on Polygons, same_style on
# text-frame style pairs. inside() is intra-Panel-A only — raw bbox math
# fails on rotated/unrotated mismatch (RESEARCH locked decision #4).
#
# Apex mirror axis y=105.0 mm (Mittelfalz). Panel A polygons live at
# y ∈ [-3..105]; Panel B mirror polygons at y ∈ [105..213].
# ---------------------------------------------------------------------------
CONSTRAINTS = [
    # ── Panel A intra-panel containment (rotation_deg=0 throughout) ──
    inside("Logo Grüne (panel A)",     "Hero-Band Panel A",      name="logo_in_band_a"),
    inside("Headline Panel A",          "Hero-Band Panel A",      name="headline_in_band_a"),
    inside("Pay-off Panel A",           "Hero-Band Panel A",      name="payoff_in_band_a"),
    inside("Hintergrund-Mitmachen",     "Photo-Backing Panel A",  name="photo_in_backing_a"),
    inside("CTA-Footer Panel A",        "Footer-Strip Panel A",   name="cta_footer_in_strip_a"),
    inside("Impressum (Tent)",          "Footer-Strip Panel A",   name="impressum_in_strip_a"),
    # ── Panel A intra-panel adjacency ──
    aligned_below("Photo-Backing Panel A", "Hero-Band Panel A", gap_mm=0.0,
                  name="photo_backing_below_hero_band_a"),
    same_x("Hero-Band Panel A", "Photo-Backing Panel A", "Footer-Strip Panel A",
           name="full_bleed_polygons_share_left_x_a"),
    same_y("Body Panel A", "Termine Panel A",
           name="bullets_termine_baseline_a"),
    same_size("Body Panel A", "Termine Panel A", axis="h",
              name="bullets_termine_height_a"),
    # ── Panel B intra-panel: only same-rotation-state pairs ──
    same_y("Body Panel B", "Termine Panel B",
           name="bullets_termine_baseline_b"),
    same_size("Body Panel B", "Termine Panel B", axis="h",
              name="bullets_termine_height_b"),
    # ── Cross-panel mirror at apex (Polygons only — both rotation_deg=0) ──
    mirrored_y("Hero-Band Panel A",      "Hero-Band Panel B",      axis_mm=105.0,
               name="hero_band_mirror_at_apex"),
    mirrored_y("Photo-Backing Panel A",  "Photo-Backing Panel B",  axis_mm=105.0,
               name="photo_backing_mirror_at_apex"),
    mirrored_y("Footer-Strip Panel A",   "Footer-Strip Panel B",   axis_mm=105.0,
               name="footer_strip_mirror_at_apex"),
    same_size("Hero-Band Panel A",       "Hero-Band Panel B",
              name="hero_bands_same_size"),
    same_size("Photo-Backing Panel A",   "Photo-Backing Panel B",
              name="photo_backings_same_size"),
    same_size("Footer-Strip Panel A",    "Footer-Strip Panel B",
              name="footer_strips_same_size"),
    # ── Cross-panel style consistency (rotation-invariant) ──
    same_style("Headline Panel A",   "Headline Panel B",   name="hero_headline_style"),
    same_style("Pay-off Panel A",    "Pay-off Panel B",    name="payoff_style"),
    same_style("Body Panel A",       "Body Panel B",       name="bullets_style"),
    same_style("Termine Panel A",    "Termine Panel B",    name="termine_style"),
    same_style("CTA-Footer Panel A", "CTA-Footer Panel B", name="cta_footer_style"),
    same_style("Impressum (Tent)",   "Impressum (Tent, panel B)", name="impressum_style"),
]


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

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
    # Issue #12 — constraints
    same_style,
    same_size,
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

    # Body Panel B — iter-3: tightened to h=26 to match Panel A and free
    # space for the CTA + events list. Pre-rot (12, 140, 223, 26) →
    # rotated bbox: x=12+223=235, y=140+26=166.
    page.add(TextFrame(
        x_mm=235, y_mm=166, w_mm=223, h_mm=26,
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

    # iter-3: EN CTA mirroring Panel A's Mitmachen at (62, 68, 60, 6).
    # Pre-rot panel-B equivalent: (62, 210-68-6=136, 60, 6) →
    # rotated (62+60, 136+6) = (122, 142).
    page.add(TextFrame(
        x_mm=122, y_mm=142, w_mm=60, h_mm=6,
        layer=LAYER_TEXT,
        style="tent/cta",
        runs=[Run(text="Get involved — Talk to us!",
                  paragraph_style="tent/cta")],
        anname="CTA Panel B",
        rotation_deg=180,
    ))

    # iter-3: EN events list mirroring Panel A's Termine at
    # (125, 68, 160, 26). Pre-rot (125, 210-68-26=116, 160, 26) →
    # rotated (125+160, 116+26) = (285, 142).
    page.add(TextFrame(
        x_mm=285, y_mm=142, w_mm=160, h_mm=26,
        layer=LAYER_TEXT,
        style="tent/termine",
        runs=[Run(
            text=("Upcoming dates\n"
                  "• 12 June — Climate roundtable, GH zur Post (Mödling)\n"
                  "• 26 June — District meeting, Lower Austria South"),
            paragraph_style="tent/termine",
        )],
        anname="Termine Panel B",
        rotation_deg=180,
    ))

    # Logo Panel B (rotated 180°). T03/T04 transition: still V0 frame
    # geometry; T04 will replace this whole V0 Panel B block via _panel_en().
    lc2_data, lc2_ext = _logo_inline()
    if lc2_data is not None:
        page.add(ImageFrame(
            x_mm=48, y_mm=210, w_mm=36, h_mm=32,
            inline_image_data=lc2_data, inline_image_ext=lc2_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            anname="Logo Grüne (panel B)",
            rotation_deg=180,
        ))

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
# Issue #12 — module-level CONSTRAINTS list (read by structural_check).
#
# Tent-card has a fold at y=105 (A4-quer halved). Panel B (bottom) is
# rotated 180°, so its frame coords are MEASURED in the rotated frame
# (top-down from y=210 down to y=105 — i.e. distances below the fold).
# Asserting geometric mirroring around y=105 directly does not match the
# coordinate system; instead we assert structural sameness: panels share
# size, headlines/bodies share style, panel-cta and panel-termine share
# style consistency.
# ---------------------------------------------------------------------------
CONSTRAINTS = [
    # Style consistency: both panels' headlines / bodies / CTAs / Termine
    # use the same paragraph style.
    same_style(
        "Headline Panel A", "Headline Panel B",
        name="panel_headline_style_consistent",
    ),
    same_style(
        "Body Panel A", "Body Panel B",
        name="panel_body_style_consistent",
    ),
    same_style(
        "CTA Panel A", "CTA Panel B",
        name="panel_cta_style_consistent",
    ),
    same_style(
        "Termine Panel A", "Termine Panel B",
        name="panel_termine_style_consistent",
    ),
    # Panel A and Panel B headlines share width/height.
    same_size(
        "Headline Panel A", "Headline Panel B", axis="both",
        name="panel_headline_size_match",
    ),
]


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

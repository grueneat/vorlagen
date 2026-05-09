"""Themen-Plakat A3 quer — DSL build entry point.

Spec: templates/_specs/themen-plakat-a3-quer.md (D3 — spec is contract).
Format: A3 quer 420×297 mm, 1-seitig, 3 mm bleed.

Layout philosophy: Argumentation These -> Belege -> Quelle.
Three-column evidence grid below a wide thesis headline.
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
    TextFrame,
    ImageFrame,
    Polygon,
    Run,
    ParaStyle,
    pack_inline_image,
    # Issue #12 — composites + free-form constraints (V1 #19 uses subset)
    same_x,
    same_y,
    same_size,
    inside,
    mirrored_x,
    same_style,
    distance_y,
)


# ---------------------------------------------------------------------------
# Constants from spec
# ---------------------------------------------------------------------------
TRIM_W_MM = 420.0
TRIM_H_MM = 297.0
BLEED_MM = 3.0
MARGIN_X_MM = 15.0
MARGIN_Y_MM = 12.0
GUTTER_MM = 8.0
COL_W_MM = (TRIM_W_MM - 2 * MARGIN_X_MM - 2 * GUTTER_MM) / 3  # ≈ 124.67


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_template() -> Document:
    """Construct the Themen-Plakat A3 quer Document — DSL-only, no photo bytes.

    Round-trip stable: T03 removes inline image data so this function is
    safe to feed into structural_check / spec_check / smoke without
    triggering image-fills-frame / preview-SHA drift.

    For preview rendering (PDF + PNG gallery) callers go through
    build_preview() which wraps build_template() and injects library
    images per INJECT_MAP using the post-#24 idiom (#19 RESEARCH §1).

    Returns the Document without saving — callers (CLI / structural_check)
    decide where (or whether) to persist.
    """
    doc = Document(
        brand=Brand.gruene_noe(),
        title="Themen-Plakat A3 quer",
        template_id="themen-plakat-a3-quer",
        author="Die Grünen Niederösterreich",
        facing_pages=False,
    )

    # Per-template paragraph styles (documented in meta.yml.ci_overrides)
    doc.add_para_style(ParaStyle(
        name="themen-plakat/headline",
        font="Vollkorn Black Italic",
        fontsize=60,
        linesp=54,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="themen-plakat/sub",
        font="Gotham Narrow Book",
        fontsize=18,
        linesp=22,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="themen-plakat/beleg-headline",
        font="Gotham Narrow Bold",
        fontsize=24,
        linesp=27,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="themen-plakat/beleg-body",
        font="Gotham Narrow Book",
        fontsize=13,
        linesp=16,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="themen-plakat/source",
        font="Gotham Narrow Book",
        fontsize=10,
        linesp=12,
        linesp_mode=0,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="themen-plakat/impressum",
        font="Gotham Narrow Book",
        fontsize=7,
        linesp=8,
        linesp_mode=0,
        align=2,  # right
        fcolor="Black",
        language="de",
    ))

    # V1 (#19) Evidence Cards — 3 NEW ParaStyles + headline linesp mutation
    # (linesp 64→54 above keeps the headline 0.9-conformant for fontsize 60).
    # stat-hero: large yellow Vollkorn Black Italic for the per-card statistic.
    doc.add_para_style(ParaStyle(
        name="themen-plakat/stat-hero",
        font="Vollkorn Black Italic",
        fontsize=56,
        linesp=50.4,        # 0.9 × 56 = 50.4 — line_spacing_0.9 conformant
        linesp_mode=0,
        align=0,            # left flush — caps Label sits centred below
        fcolor="Gelb",
        language="de",
    ))
    # beleg-body-on-green: white body text laid on Hellgrün card.
    # Per pitfalls §P15 we do NOT mutate the existing themen-plakat/beleg-body
    # align (no consumer post-V1; mutation contradicts ISSUE.md own list).
    doc.add_para_style(ParaStyle(
        name="themen-plakat/beleg-body-on-green",
        font="Gotham Narrow Book",
        fontsize=13,
        linesp=16.9,        # NOT 0.9-conformant (drift 5.2pt) — line_spacing_0.9 override stays per locked #7
        linesp_mode=0,
        align=1,            # centre per improvements.md §"Alignment-Spezifikation"
        fcolor="White",
        language="de",
    ))
    # beleg-headline-yellow: small caps Gelb label below stat-hero.
    # CAPS achieved by uppercasing the run text in T03 (no smcp ParaStyle field).
    # letter-spacing 0.04em @ 18pt → kern = 0.04 × 18 = 0.72 pt.
    doc.add_para_style(ParaStyle(
        name="themen-plakat/beleg-headline-yellow",
        font="Gotham Narrow Bold",
        fontsize=18,
        linesp=16.2,        # 0.9 × 18 = 16.2 — line_spacing_0.9 conformant
        linesp_mode=0,
        align=1,            # centre — caption-style under stat-hero
        fcolor="Gelb",
        kern=0.72,
        language="de",
    ))

    # Master and page
    doc.add_master(
        name="Normal",
        size=(TRIM_W_MM, TRIM_H_MM),
        bleed_mm=BLEED_MM,
        margins_mm=(MARGIN_Y_MM, MARGIN_X_MM, MARGIN_Y_MM, MARGIN_X_MM),
    )
    page = doc.add_page(
        size=(TRIM_W_MM, TRIM_H_MM),
        bleed_mm=BLEED_MM,
        margins_mm=(MARGIN_Y_MM, MARGIN_X_MM, MARGIN_Y_MM, MARGIN_X_MM),
        master="Normal",
    )

    # White full-bleed background
    page.add(Polygon(
        x_mm=-BLEED_MM,
        y_mm=-BLEED_MM,
        w_mm=TRIM_W_MM + 2 * BLEED_MM,
        h_mm=TRIM_H_MM + 2 * BLEED_MM,
        fill="White",
        layer=0,
        anname="Seitenhintergrund",
    ))

    # Logo (top-left, Brand-Bund) — embedded inline so the SLA stays
    # self-contained. V1 (#19) sizes the logo to the Quickguide 3*M
    # target on A3 quer: M = 0.06 * kurze_kante = 0.06 * 297 = 17.82,
    # 3M = 53.46 mm. h=48 keeps the same ~1.12:1 aspect (gruene-logo-bund-dunkel.png).
    # scale_type=0, ratio=1 → Scribus aspect-preserving auto-fit.
    logo_path = HERE.parents[1] / "shared" / "logos" / "gruene-logo-bund-dunkel.png"
    if not logo_path.exists():
        raise FileNotFoundError(
            f"Logo asset missing at {logo_path} — Issue #11 iter-3 brand-logo "
            f"integration requires shared/logos/gruene-logo-bund-dunkel.png."
        )
    logo_bytes = logo_path.read_bytes()
    data, ext = pack_inline_image(logo_bytes, "png")
    page.add(ImageFrame(
        x_mm=15, y_mm=10, w_mm=53.46, h_mm=48,
        inline_image_data=data,
        inline_image_ext=ext,
        scale_type=0,
        ratio=1,
        layer=1,
        anname="Logo Grüne (top-left)",
    ))

    # Issue #12 vorzeige refactor — construct-then-add convention.
    # All frames assigned to named locals BEFORE page.add() so the
    # module-level CONSTRAINTS list can reference them by anname (the
    # locals themselves are out of scope at constraint-eval time, but
    # their annames live on as string labels). This convention is
    # documented in shared/brand/SPEC-WRITING-GUIDE.md "Construct-then-add".

    # Headline — These (60pt Vollkorn Black Italic Dunkelgrün) — V1 (#19)
    # right-half 60/40 column placement at x=235.
    headline = TextFrame(
        x_mm=235, y_mm=70, w_mm=170, h_mm=100,
        layer=2,
        style="themen-plakat/headline",
        runs=[Run(
            text="Klimaschutz ist Wirtschaftspolitik.",
            paragraph_style="themen-plakat/headline",
        )],
        anname="Headline These",
    )
    page.add(headline)

    # Sub-Headline (18pt Gotham Book Dunkelgrün) — V1 (#19) right-half column.
    subheadline = TextFrame(
        x_mm=235, y_mm=172, w_mm=170, h_mm=14,
        layer=2,
        style="themen-plakat/sub",
        runs=[Run(
            text="Drei Belege aus Niederösterreich, Mai 2026.",
            paragraph_style="themen-plakat/sub",
        )],
        anname="Sub-Headline",
    )
    page.add(subheadline)

    # V1 (#19) Hero-Foto-Card — Hellgrün backing for the hero photo.
    # layer=1 (above background layer=0, below text layer=2). Provides
    # visual weight behind the 60/40-split photo + frames `Themen-Hero`
    # for the inside(Hero, Hero-Foto-Card) constraint witness.
    page.add(Polygon(
        x_mm=15, y_mm=70, w_mm=200, h_mm=120,
        fill="Hellgrün",
        layer=1,
        anname="Hero-Foto-Card",
    ))

    # Themen-Hero — central library reference (#13). 194×114mm landscape
    # frame (~1.7:1). Source 1536×1024 (~1.5:1) → centre-crop trims height
    # per crop_focus=[0.65, 0.50] manifest entry. Image bytes injected by
    # build_preview()::INJECT_MAP loop using the post-#24 idiom that reads
    # frame.w_mm / frame.h_mm LIVE — no literal target drift. Sits inside
    # Hero-Foto-Card with 3mm gap top/left/right, 3mm bottom.
    page.add(ImageFrame(
        x_mm=18, y_mm=73, w_mm=194, h_mm=114,
        scale_type=0, ratio=1,
        layer=1,
        anname="Themen-Hero",
    ))

    # V1 (#19) Evidence Cards — three Hellgrün backing cards each carrying
    # stat-hero number + caps Gelb label + white body text on green. Card
    # x = MARGIN_X + i × (COL_W + GUTTER); inner Stat/Label/Body inset by 5mm.
    v1_belege = [
        ("12 700",    "Grüne Jobs in NÖ",
         "In Niederösterreich arbeiten 12 700 Menschen direkt in der "
         "Erneuerbaren-Energie-Branche — mehr als in der konventionellen "
         "Energiewirtschaft.",
         "Beleg 1"),
        ("1.2 Mrd. €", "Umsatz Solar + Wind",
         "Die Solar- und Wind-Branche macht in NÖ 1.2 Mrd. € Jahresumsatz "
         "aus — Tendenz steigend. Jeder Euro fließt in die regionale "
         "Wertschöpfung zurück.",
         "Beleg 2"),
        ("36 %",       "weniger CO₂ seit 2010",
         "Seit 2010 hat NÖ den industriellen CO₂-Ausstoß um 36 % reduziert — "
         "bei gleichzeitig wachsender Industrie-Produktion.",
         "Beleg 3"),
    ]
    for i, (stat, label, body, anname_prefix) in enumerate(v1_belege):
        col_x = MARGIN_X_MM + i * (COL_W_MM + GUTTER_MM)
        inner_x = col_x + 5.0

        # Card backing (Hellgrün polygon, layer=1)
        page.add(Polygon(
            x_mm=col_x, y_mm=210, w_mm=COL_W_MM, h_mm=72,
            fill="Hellgrün",
            layer=1,
            anname=f"{anname_prefix} — Card",
        ))
        # Stat-hero (Vollkorn Black Italic 56pt Gelb, left-flush at inner_x)
        page.add(TextFrame(
            x_mm=inner_x, y_mm=215, w_mm=114.0, h_mm=24,
            layer=2,
            style="themen-plakat/stat-hero",
            runs=[Run(text=stat, paragraph_style="themen-plakat/stat-hero")],
            anname=f"{anname_prefix} — Stat",
        ))
        # Label (CAPS Gotham Narrow Bold 18pt Gelb, centred, kern=0.72)
        # CAPS via literal upper(); ParaStyle has no caps field.
        page.add(TextFrame(
            x_mm=inner_x, y_mm=242, w_mm=114.0, h_mm=8,
            layer=2,
            style="themen-plakat/beleg-headline-yellow",
            runs=[Run(text=label.upper(),
                      paragraph_style="themen-plakat/beleg-headline-yellow")],
            anname=f"{anname_prefix} — Label",
        ))
        # Body (Gotham Narrow Book 13pt White centred on green)
        page.add(TextFrame(
            x_mm=inner_x, y_mm=252, w_mm=114.0, h_mm=26,
            layer=2,
            style="themen-plakat/beleg-body-on-green",
            runs=[Run(text=body,
                      paragraph_style="themen-plakat/beleg-body-on-green")],
            anname=f"{anname_prefix} — Body",
        ))

    # QR-Quelle slot — V1 (#19) enlarged to 35×35 mm to balance the larger
    # 53.46 mm Logo. Placed top-right corner. 35 mm at QR version 4 still
    # well above D1's 0.5 mm/module minimum.
    qr_path = HERE / "samples" / "qr-quelle.png"
    qr_data, qr_ext = (None, None)
    if qr_path.exists():
        qr_data, qr_ext = pack_inline_image(qr_path.read_bytes(), "png")
    page.add(ImageFrame(
        x_mm=370, y_mm=8, w_mm=35, h_mm=35,
        inline_image_data=qr_data,
        inline_image_ext=qr_ext,
        scale_type=0, ratio=1,
        layer=1,
        anname="QR-Code (quelle)",
    ))

    # Quelle (bottom-left). V1 (#19) widened to w=200 to accommodate fuller
    # source citation now that the hero photo no longer dominates the bottom band.
    page.add(TextFrame(
        x_mm=15, y_mm=287, w_mm=200, h_mm=8,
        layer=2,
        style="themen-plakat/source",
        runs=[Run(
            text="Quelle: Statistik Austria, AEA-Energiebilanz NÖ 2024.",
            paragraph_style="themen-plakat/source",
        )],
        anname="Quelle",
    ))

    # Impressum (bottom-right). iter-3: y=287 to align with relocated Quelle.
    page.add(TextFrame(
        x_mm=305, y_mm=287, w_mm=100, h_mm=8,
        layer=2,
        style="themen-plakat/impressum",
        runs=[Run(
            text=(
                "Medieninhaber: Die Grünen NÖ, "
                "Daniel-Gran-Straße 48, 3100 St. Pölten."
            ),
            paragraph_style="themen-plakat/impressum",
        )],
        anname="Impressum",
    ))

    return doc


# Post-#24 INJECT_MAP idiom (#19 RESEARCH §1, locked decision #1):
# value = bare lib_id (manifest key). Loop reads target_w_mm / target_h_mm
# LIVE from each frame, eliminating the literal-target drift that produced
# the half-empty hero in iter-3 (`crop_for_frame(target_w_mm=180, h=60)`
# vs frame at w=194, h=114 → photo rendered at 90×60 inside 194×114 frame).
INJECT_MAP: dict[str, str] = {
    "Themen-Hero": "themen_klimaschutz_windrad",
}


def build_preview() -> Document:
    """Inject demo library images for gallery PNG render (#24 idiom).

    Pattern: pre-crops the source image to the frame's LIVE dimensions
    via library.inject_into_frame, eliminating the literal-target drift
    that produced the half-empty hero frame in iter-3.
    """
    doc = build_template()
    if not INJECT_MAP:
        return doc
    for page in doc.pages:
        for item in page.items:
            if isinstance(item, ImageFrame) and item.anname in INJECT_MAP:
                lib_id = INJECT_MAP[item.anname]
                img = library.load(lib_id, optional=True)
                if img is None:
                    continue
                library.inject_into_frame(
                    item, img,
                    target_w_mm=item.w_mm,
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
# Pure metadata: NOT consumed by build_doc() / build(). Each Constraint
# uses anname-string references, which works regardless of where the
# Frame instances were constructed (build_doc locals are out of scope
# here). See shared/brand/SPEC-WRITING-GUIDE.md "Construct-then-add"
# for the convention.
# ---------------------------------------------------------------------------
CONSTRAINTS = [
    # Headline-stack vertical hierarchy: Sub sits below Headline These in same
    # right-half column. distance_y measures |a.y - b.y| = top-to-top distance.
    # Headline These y=70, Sub-Headline y=172 → 172-70 = 102.
    distance_y("Headline These", "Sub-Headline", equals=102.0,
               name="hl_to_sub"),

    # Three Evidence cards share top y=210 and same width=124.67 (row alignment +
    # uniform card sizing).
    same_y("Beleg 1 — Card", "Beleg 2 — Card", "Beleg 3 — Card",
           name="cards_top_aligned"),
    same_size("Beleg 1 — Card", "Beleg 2 — Card", "Beleg 3 — Card",
              name="cards_same_size"),

    # Cards mirror around page horizontal centre (axis 210mm = page_w/2).
    # Card 1 left=15 ↔ Card 3 right=405.67 → axis (15+405.67)/2 = 210.335 → drift
    # 0.335mm < 0.5mm tolerance ✓.
    mirrored_x("Beleg 1 — Card", "Beleg 3 — Card", axis_mm=210.0,
               name="cards_mirror_around_page_center"),

    # Per-card inner-axis sharing: 3 stat-heros / labels / bodies share x = col_x+5.
    # NOTE: Card itself NOT in this same_x — Card.x = col_x, contents.x = col_x+5;
    # 5mm drift > 0.5mm tol would FAIL. Containment encoded by inside() below.
    # (Pitfalls §3 P3 — ISSUE.md errata.)
    same_x("Beleg 1 — Stat", "Beleg 1 — Label", "Beleg 1 — Body",
           name="card1_v_axis"),
    same_x("Beleg 2 — Stat", "Beleg 2 — Label", "Beleg 2 — Body",
           name="card2_v_axis"),
    same_x("Beleg 3 — Stat", "Beleg 3 — Label", "Beleg 3 — Body",
           name="card3_v_axis"),

    # Per-card containment: each Stat/Label/Body sits inside its Card backing.
    # 9 inside() constraints — declarative witness for "white text on green polygon".
    inside("Beleg 1 — Stat",  "Beleg 1 — Card", name="b1_stat_in_card"),
    inside("Beleg 1 — Label", "Beleg 1 — Card", name="b1_label_in_card"),
    inside("Beleg 1 — Body",  "Beleg 1 — Card", name="b1_body_in_card"),
    inside("Beleg 2 — Stat",  "Beleg 2 — Card", name="b2_stat_in_card"),
    inside("Beleg 2 — Label", "Beleg 2 — Card", name="b2_label_in_card"),
    inside("Beleg 2 — Body",  "Beleg 2 — Card", name="b2_body_in_card"),
    inside("Beleg 3 — Stat",  "Beleg 3 — Card", name="b3_stat_in_card"),
    inside("Beleg 3 — Label", "Beleg 3 — Card", name="b3_label_in_card"),
    inside("Beleg 3 — Body",  "Beleg 3 — Card", name="b3_body_in_card"),

    # Themen-Hero containment in Hero-Foto-Card (NOT aligned_below to Sub-Headline
    # — pitfalls §4 P4: Hero (x=18) and Sub-Headline (x=235) are side-by-side in
    # the 60/40 split, NOT vertically stacked.)
    inside("Themen-Hero", "Hero-Foto-Card", name="hero_in_card"),

    # Style consistency across the 3 Stat / Body frames.
    same_style("Beleg 1 — Stat", "Beleg 2 — Stat", "Beleg 3 — Stat",
               name="stat_style_consistent"),
    same_style("Beleg 1 — Body", "Beleg 2 — Body", "Beleg 3 — Body",
               name="body_style_consistent"),
]


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

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
    # Issue #12 / #14 / #17 — constraints (V1 uses mirrored axes for halo,
    # aligned_below for vertical stacks, same_x for column alignment,
    # distance_x/y to formalize intentional non-aligned offsets that the
    # `brand:undeclared_alignment_drift` heuristic flags as suspicious).
    same_x,
    inside,
    mirrored_x,
    mirrored_y,
    aligned_below,
    distance_x,
    distance_y,
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
def build_doc() -> Document:
    """Issue #12 D13: return constructed Document; persistence is the
    caller's job (CLI wrapper below or structural_check)."""
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
        fontsize=5,
        linesp=4.5,
        linesp_mode=0,
        align=0,
        fcolor="Black",
        language="de",
    ))

    # V1 (Issue #17): 4 new ParaStyles for the Symbol-Tight layout. Existing
    # wahlaufruf/cell-body (Black) is left UNCHANGED — locked decision #5
    # introduces the parallel `*-on-green` migration pattern that #18-#21 reuse
    # rather than mutating the original style in-place.
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/headline-emphasis",
        font="Vollkorn Black Italic",
        fontsize=26,
        linesp=23,
        linesp_mode=0,
        align=1,  # center
        fcolor="Gelb",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/headline-cta",
        font="Gotham Narrow Bold",
        fontsize=14,
        linesp=13,
        linesp_mode=0,
        align=1,  # center
        fcolor="White",
        language="de",
        kern=2.1,  # 0.15em letter-spacing → 14pt × 0.15 = 2.1pt per-glyph expansion
    ))
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/cell-headline-yellow",
        font="Vollkorn Black Italic",
        fontsize=18,
        linesp=16,
        linesp_mode=0,
        align=0,  # left
        fcolor="Gelb",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/cell-body-on-green",
        font="Gotham Narrow Book",
        fontsize=9,
        linesp=11,
        linesp_mode=0,
        align=0,  # left
        fcolor="White",
        language="de",
    ))

    # V1 (Issue #17): QR label + url styles. ISSUE.md prescribes
    # "12pt Gotham Bold Dunkelgrün" and "11pt Gotham Bold Dunkelgrün"
    # respectively; the white impressum strip behind these frames
    # makes Dunkelgrün the readable choice. Plan T03 step 5 option (a).
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/qr-label",
        font="Gotham Narrow Bold",
        fontsize=12,
        linesp=11,
        linesp_mode=0,
        align=1,  # center
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="wahlaufruf/qr-url",
        font="Gotham Narrow Bold",
        fontsize=11,
        linesp=10,
        linesp_mode=0,
        align=1,  # center
        fcolor="Dunkelgrün",
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

    # V1 (Issue #17): Logo (white) at Print-Soll 3*M = 18.9 mm × 5.7 mm
    # (was 35×10 with local_scale=0.240; now matches `brand:logo_size_3M`).
    # local_scale recomputed: 5.7mm/(118px*72/25.4/300dpi) ≈ 0.130.
    logo_weiss_path = HERE.parents[1] / "shared" / "logos" / "gruene-weiss.png"
    if not logo_weiss_path.exists():
        raise FileNotFoundError(
            f"Required brand asset missing: {logo_weiss_path}"
        )
    lw_data, lw_ext = pack_inline_image(logo_weiss_path.read_bytes(), "png")
    page0.add(ImageFrame(
        x_mm=6, y_mm=6, w_mm=18.9, h_mm=5.7,
        inline_image_data=lw_data,
        inline_image_ext=lw_ext,
        scale_type=0, ratio=1,
        local_scale=(0.130, 0.130),
        layer=1,
        anname="Logo Grüne (weiss)",
    ))

    # V1 (Issue #17): Hellgrün halo polygon — must come BEFORE Wahlkreuz on
    # layer=0 so the symbol sits ABOVE it. Locked decision #3: explicit
    # shape="ellipse" (Polygon defaults to rectangle).
    # Halo center = (43+31, 17+31) = (74, 48). Wahlkreuz center = (44+30,
    # 18+30) = (74, 48). Both axes match — see CONSTRAINTS in T04.
    page0.add(Polygon(
        x_mm=43, y_mm=17, w_mm=62, h_mm=62,
        fill="Hellgrün",
        shape="ellipse",
        layer=0,
        anname="wahlkreuz_halo",
    ))

    # Wahlkreuz hero — V1 (Issue #17) repositions to (44, 18) and grows to
    # 60×60 to fit inside the 62 mm halo with 1mm padding on each side.
    # ANNAME stays capitalized — `brand:wahlkreuz_colored_bg` is a
    # case-sensitive substring match (locked decision #4).
    wahlkreuz_path = HERE.parents[1] / "shared" / "assets" / "wahlkreuz.png"
    if not wahlkreuz_path.exists():
        raise FileNotFoundError(
            f"Wahlkreuz asset not found at {wahlkreuz_path}; "
            f"this template requires shared/assets/wahlkreuz.png (see D1 revised)."
        )
    wahlkreuz_bytes = wahlkreuz_path.read_bytes()
    wk_data, wk_ext = pack_inline_image(wahlkreuz_bytes, "png")
    page0.add(ImageFrame(
        x_mm=44, y_mm=18, w_mm=60, h_mm=60,
        inline_image_data=wk_data,
        inline_image_ext=wk_ext,
        scale_type=0,
        ratio=1,
        layer=1,
        anname="Wahlkreuz",
    ))

    # V1 (Issue #17): Headline-Wahlaufruf deleted; replaced with the
    # datum/cta stack below the Wahlkreuz. distance_y(headline_datum,
    # headline_cta, equals=10.0) is enforced via CONSTRAINTS in T04.
    page0.add(TextFrame(
        x_mm=10, y_mm=82, w_mm=128, h_mm=10,
        layer=2,
        style="wahlaufruf/headline-emphasis",
        runs=[Run(
            text="SONNTAG, 26. JÄNNER 2026",
            paragraph_style="wahlaufruf/headline-emphasis",
        )],
        anname="headline_datum",
    ))
    page0.add(TextFrame(
        x_mm=10, y_mm=92, w_mm=128, h_mm=10,
        layer=2,
        style="wahlaufruf/headline-cta",
        runs=[Run(
            text="GIB DEINE STIMME DEN GRÜNEN",
            paragraph_style="wahlaufruf/headline-cta",
        )],
        anname="headline_cta",
    ))

    # ---- PAGE 2: Back (V1 split-half + 3 W-Fragen + QR + Impressum) ----
    # V1 (Issue #17): two background polygons emitted FIRST so they sit
    # below all content. Left half = Dunkelgrün (carries the W-Fragen);
    # bottom strip = white (carries the small Impressum).
    page1.add(Polygon(
        x_mm=-3, y_mm=-3, w_mm=93, h_mm=111,
        fill="Dunkelgrün",
        layer=0,
        anname="seitenhintergrund_back_left",
    ))
    page1.add(Polygon(
        x_mm=0, y_mm=96, w_mm=148, h_mm=9,
        fill="White",
        layer=0,
        anname="impressum_strip_bg",
    ))

    # V1 (Issue #17): back-side logo migrated from gruene-logo-bund-dunkel.png
    # (Bund-Dunkel wordmark) to gruene-weiss.png so it stays legible on the
    # new Dunkelgrün-half background. Anname renamed to lowercase snake_case
    # `logo_back` (locked decision #4: case-INSENSITIVE \bLogo\b brand rule
    # still matches; new annames added by V1 use snake_case). EXPLICIT
    # local_scale=(0.130, 0.130) — default (1.0, 1.0) renders 5.5× scale.
    # logo_weiss_path verified above (front-side load); reuse same path.
    lb_data, lb_ext = pack_inline_image(logo_weiss_path.read_bytes(), "png")
    page1.add(ImageFrame(
        x_mm=96, y_mm=8, w_mm=18.9, h_mm=5.7,
        inline_image_data=lb_data,
        inline_image_ext=lb_ext,
        scale_type=0, ratio=1,
        local_scale=(0.130, 0.130),
        layer=1,
        anname="logo_back",
    ))

    # V1 (Issue #17): 4-Cells loop replaced by 3 W-Frage stacks
    # (Was/Warum/Wann). Each = headline (yellow) + body (white-on-green),
    # gap=1mm, all left-aligned at x=6. Per-stack adjacency declared in
    # CONSTRAINTS (T04) so `brand:undeclared_alignment_drift` reports clean.
    page1.add(TextFrame(
        x_mm=6, y_mm=12, w_mm=84, h_mm=8,
        layer=2,
        style="wahlaufruf/cell-headline-yellow",
        runs=[Run(text="WAS?",
                  paragraph_style="wahlaufruf/cell-headline-yellow")],
        anname="frage_was_headline",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=21, w_mm=84, h_mm=20,
        layer=2,
        style="wahlaufruf/cell-body-on-green",
        runs=[Run(
            text=("Klimaschutz, leistbares Wohnen, Bildung — "
                  "konkret in deiner Gemeinde."),
            paragraph_style="wahlaufruf/cell-body-on-green",
        )],
        anname="frage_was_body",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=40, w_mm=84, h_mm=8,
        layer=2,
        style="wahlaufruf/cell-headline-yellow",
        runs=[Run(text="WARUM?",
                  paragraph_style="wahlaufruf/cell-headline-yellow")],
        anname="frage_warum_headline",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=49, w_mm=84, h_mm=20,
        layer=2,
        style="wahlaufruf/cell-body-on-green",
        runs=[Run(
            text=("Mut zur Veränderung. Faktenbasiert. "
                  "Generationen­gerecht."),
            paragraph_style="wahlaufruf/cell-body-on-green",
        )],
        anname="frage_warum_body",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=68, w_mm=84, h_mm=8,
        layer=2,
        style="wahlaufruf/cell-headline-yellow",
        runs=[Run(text="WANN?",
                  paragraph_style="wahlaufruf/cell-headline-yellow")],
        anname="frage_wann_headline",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=77, w_mm=84, h_mm=20,
        layer=2,
        style="wahlaufruf/cell-body-on-green",
        runs=[Run(text="Sonntag, 26. Jänner 2026, 7–17 Uhr.",
                  paragraph_style="wahlaufruf/cell-body-on-green")],
        anname="frage_wann_body",
    ))

    # V1 (Issue #17): QR stack — label above (y=24), code (y=31, 36×36),
    # url below (y=71). y values 24/31/71 are LOCKED (locked decision #2,
    # ship-blockers B2/B3). aligned_below verifies:
    #   qr_label.bottom = 24+5 = 29 → +2mm gap = qr_code.y=31 ✓
    #   qr_code.bottom = 31+36 = 67 → +4mm gap = qr_url.y=71 ✓
    #   logo_back.bottom = 8+5.7 = 13.7 → +10.3mm gap = qr_label.y=24 ✓
    page1.add(TextFrame(
        x_mm=96, y_mm=24, w_mm=36, h_mm=5,
        layer=2,
        style="wahlaufruf/qr-label",
        runs=[Run(text="WO INFORMIEREN",
                  paragraph_style="wahlaufruf/qr-label")],
        anname="qr_label",
    ))
    qr_back_path = HERE / "samples" / "qr-back.png"
    if not qr_back_path.exists():
        raise FileNotFoundError(f"Required QR asset missing: {qr_back_path}")
    qr_data, qr_ext = pack_inline_image(qr_back_path.read_bytes(), "png")
    page1.add(ImageFrame(
        x_mm=96, y_mm=31, w_mm=36, h_mm=36,
        inline_image_data=qr_data,
        inline_image_ext=qr_ext,
        scale_type=0, ratio=1,
        layer=1,
        anname="qr_code",
    ))
    page1.add(TextFrame(
        x_mm=96, y_mm=71, w_mm=36, h_mm=5,
        layer=2,
        style="wahlaufruf/qr-url",
        runs=[Run(text="gruene-noe.at",
                  paragraph_style="wahlaufruf/qr-url")],
        anname="qr_url",
    ))

    # Impressum bottom strip — V1 (Issue #17): tightened to y=101.5 h=4
    # to fit on the white impressum_strip_bg polygon (which spans y=96..105).
    # Style fontsize 5 / linesp 4.5 set in T01.
    page1.add(TextFrame(
        x_mm=6, y_mm=101.5, w_mm=136, h_mm=4,
        layer=2,
        style="wahlaufruf/impressum",
        runs=[Run(
            text=("Medieninhaber: Die Grünen NÖ, "
                  "Daniel-Gran-Straße 48, 3100 St. Pölten."),
            paragraph_style="wahlaufruf/impressum",
        )],
        anname="Impressum",
    ))

    return doc


def build(out_path: str | Path = HERE / "template.sla") -> Path:
    doc = build_doc()
    out_path = Path(out_path)
    doc.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Issue #12 — module-level CONSTRAINTS list (read by structural_check).
# ---------------------------------------------------------------------------
CONSTRAINTS = [
    # Front: halo + symbol share centers (both axes), and halo contains symbol.
    # mirrored_x/y average centers (NOT same_x/y which compares corners; halo
    # and symbol corners differ by 1mm > 0.5 tolerance — locked decision #1).
    mirrored_x("wahlkreuz_halo", "Wahlkreuz", axis_mm=74.0, name="halo_x_centered"),
    mirrored_y("wahlkreuz_halo", "Wahlkreuz", axis_mm=48.0, name="halo_y_centered"),
    inside("Wahlkreuz", "wahlkreuz_halo", name="halo_contains_symbol"),
    # Front: headline stack vertical hierarchy (datum -> cta gap = 10mm).
    distance_y("headline_datum", "headline_cta", equals=10.0, name="datum_to_cta"),
    # Back: 3 W-Fragen share x-axis (left edge x=6) for headlines and bodies.
    same_x("frage_was_headline", "frage_warum_headline", "frage_wann_headline",
           name="fragen_left_axis"),
    same_x("frage_was_body", "frage_warum_body", "frage_wann_body",
           name="bodies_left_axis"),
    # Back: per-W-Frage stack (body hangs from headline, gap=1mm, same x).
    aligned_below("frage_was_body", "frage_was_headline", gap_mm=1.0,
                  name="was_stack"),
    aligned_below("frage_warum_body", "frage_warum_headline", gap_mm=1.0,
                  name="warum_stack"),
    aligned_below("frage_wann_body", "frage_wann_headline", gap_mm=1.0,
                  name="wann_stack"),
    # Back: QR block right-axis + label-above + url-below (locked decision #2:
    # qr_label.y=24, qr_code.y=31, qr_url.y=71 — NOT ISSUE.md's 24/30/68).
    same_x("qr_label", "qr_code", "qr_url", name="qr_axis"),
    aligned_below("qr_code", "qr_label", gap_mm=2.0, name="qr_label_anchors_code"),
    aligned_below("qr_url", "qr_code", gap_mm=4.0, name="qr_url_below_code"),
    # Back: qr_label hangs from logo_back (right column stacking).
    aligned_below("qr_label", "logo_back", gap_mm=10.3,
                  name="logo_back_anchors_qr"),
    # Intentional cross-column offsets that the audit heuristic flags as
    # near-axis (drift < 5mm). Declaring with distance_x/y formalizes
    # "not aligned, but the gap is by design" — silences
    # `brand:undeclared_alignment_drift` without changing geometry.
    # Front: logo (x=6) sits 4mm left of the headline column (x=10).
    distance_x("Logo Grüne (weiss)", "headline_datum", equals=4.0,
               name="logo_to_headline_column_offset_datum"),
    distance_x("Logo Grüne (weiss)", "headline_cta", equals=4.0,
               name="logo_to_headline_column_offset_cta"),
    # Back: full-bleed left polygon (x=-3) vs impressum strip (x=0).
    distance_x("seitenhintergrund_back_left", "impressum_strip_bg",
               equals=3.0, name="back_bg_strip_x_offset"),
    # Back: cross-column origin offsets between the W-Fragen rows and the
    # QR stack (different columns, unrelated y values that happen to land
    # within 5mm by layout coincidence).
    distance_y("logo_back", "frage_was_headline", equals=4.0,
               name="logo_back_to_first_frage_y_offset"),
    distance_y("frage_was_body", "qr_label", equals=3.0,
               name="frage_was_body_to_qr_label_y_offset"),
    distance_y("frage_wann_headline", "qr_url", equals=3.0,
               name="frage_wann_headline_to_qr_url_y_offset"),
    # Back: Impressum hangs below the last W-Frage body (frage_wann_body
    # bottom y=97; impressum y=101.5 → 4.5mm gap on the impressum_strip_bg).
    aligned_below("Impressum", "frage_wann_body", gap_mm=4.5,
                  name="impressum_below_wann"),
]


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

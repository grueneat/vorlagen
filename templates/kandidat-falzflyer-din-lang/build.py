"""Kandidat-Falzflyer DIN-lang — DSL build entry point.

Spec: templates/_specs/kandidat-falzflyer-din-lang.md.
Format: A4 quer (297×210 mm), 3-fach Zickzackfalz auf 6 Panele à 99×210 mm
(3 front + 3 back). Falz-Linien bei x=99 und x=198 auf Falz-Layer.

Front: Cover (P1) — Teaser (P2) — Closer mit Wahlkreuz auf Dunkelgrün (P3)
Back: Themen 1+2 (P4) — Themen 3+4 (P5) — Kontakt + Impressum (P6)
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
    # Issue #12 + #21 — constraints
    aligned_below,
    same_y,
    inside,
    mirrored_x,
    same_size,
    same_style,
    same_x,
)
from sla_lib.builder.blocks import FoldLine  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRIM_W_MM = 297.0
TRIM_H_MM = 210.0
BLEED_MM = 3.0
PANEL_W_MM = 99.0     # 297/3
FOLD_X1_MM = 99.0
FOLD_X2_MM = 198.0

# Layer indexes
LAYER_HINTERGRUND = 0
LAYER_BILDER = 1
LAYER_TEXT = 2
LAYER_FALZ = 3


# Post-#24 INJECT_MAP idiom (#19 RESEARCH §1, locked decision #1):
# value = bare lib_id (manifest key). build_preview() reads target_w_mm /
# target_h_mm LIVE from each frame, eliminating literal-target drift.
# Em-dash literal U+2014 in Thema annames per RESEARCH locked #4.
INJECT_MAP: dict[str, str] = {
    "P1 Kandidat-Portrait":  "portrait_maria",
    "P4 Thema 1 — Photo":    "themen_klimaschutz_solar",
    "P4 Thema 2 — Photo":    "themen_soziales_kaffeehaus",
    "P5 Thema 3 — Photo":    "themen_bildung_volksschule",
    "P5 Thema 4 — Photo":    "themen_wirtschaft_handwerk",
}


def _top_band(panel_index: int) -> Polygon:
    """V1 universal Top-Band helper — emit 31mm Dunkelgrün Polygon for one
    of the 4 panels that get an explicit Top-Band Polygon (P1, P2, P4, P5).

    Routing per RESEARCH locked #6 + correction #3:
      0 -> P1: outer (x=-3, w=105) — extends into bleed at trim edge
      1 -> P2: inner (x=99, w=99) — flush both Falz-lines
      2 -> P3: ValueError — vollflächig Dunkelgrün; the polygon IS the band
      3 -> P4: outer (x=-3, w=105)
      4 -> P5: inner (x=99, w=99)
      5 -> P6: ValueError — vollflächig Dunkelgrün; the polygon IS the band

    All bands: y=-3, h=31, fill=Dunkelgrün, layer=LAYER_HINTERGRUND.
    """
    if panel_index == 0:
        return Polygon(
            x_mm=-3, y_mm=-3, w_mm=105, h_mm=31,
            fill="Dunkelgrün",
            layer=LAYER_HINTERGRUND,
            anname="P1 Top-Band",
        )
    if panel_index == 1:
        return Polygon(
            x_mm=99, y_mm=-3, w_mm=99, h_mm=31,
            fill="Dunkelgrün",
            layer=LAYER_HINTERGRUND,
            anname="P2 Top-Band",
        )
    if panel_index == 2:
        raise ValueError(
            "P3 is vollflächig — use P3 Hintergrund polygon instead"
        )
    if panel_index == 3:
        return Polygon(
            x_mm=-3, y_mm=-3, w_mm=105, h_mm=31,
            fill="Dunkelgrün",
            layer=LAYER_HINTERGRUND,
            anname="P4 Top-Band",
        )
    if panel_index == 4:
        return Polygon(
            x_mm=99, y_mm=-3, w_mm=99, h_mm=31,
            fill="Dunkelgrün",
            layer=LAYER_HINTERGRUND,
            anname="P5 Top-Band",
        )
    if panel_index == 5:
        raise ValueError(
            "P6 is vollflächig — use P6 Hintergrund polygon instead"
        )
    raise ValueError(f"_top_band: panel_index must be 0..5, got {panel_index}")


def _add_styles(doc):
    """Register the 16 falzflyer-local paragraph styles (V1).

    V1 ParaStyle migration table (per RESEARCH §"V1 ParaStyle table"):
      MUTATIONS (10): cand-name, slogan, closer-headline, closer-url,
        closer-datum, contact-headline, contact-body, thema-body, impressum,
        teaser-body — see per-style notes below.
      KEPT UNCHANGED (2): teaser-headline, thema-headline.
      NEW (4): slogan-on-green, quote-on-green, top-title, themen-eyebrow.
    """
    # V1: align 0->1, fcolor Dunkelgrün->White (P1 Name on Dunkelgrün card).
    doc.add_para_style(ParaStyle(
        name="falzflyer/cand-name",
        font="Vollkorn Black Italic",
        fontsize=24,
        linesp=27,
        align=1,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    # V1: align 0->1 (KEEP fcolor=Black; Slogan-on-green uses parallel style).
    doc.add_para_style(ParaStyle(
        name="falzflyer/slogan",
        font="Gotham Narrow Bold",
        fontsize=14,
        linesp=17,
        align=1,
        fcolor="Black",
        language="de",
        linesp_mode=0,
    ))
    # V1: UNCHANGED (redaktioneller Charakter, align=0 KEEP).
    doc.add_para_style(ParaStyle(
        name="falzflyer/teaser-headline",
        font="Gotham Narrow Bold",
        fontsize=18,
        linesp=22,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
        linesp_mode=0,
    ))
    # V1: align stays 0 (redaktioneller); fcolor Black->White (Hellgrün backing).
    doc.add_para_style(ParaStyle(
        name="falzflyer/teaser-body",
        font="Gotham Narrow Book",
        fontsize=11,
        linesp=14,
        align=0,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    # V1: align 0->1 (already White on Dunkelgrün).
    doc.add_para_style(ParaStyle(
        name="falzflyer/closer-headline",
        font="Gotham Narrow Bold",
        fontsize=22,
        linesp=26,
        align=1,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    # V1: align 0->1.
    doc.add_para_style(ParaStyle(
        name="falzflyer/closer-datum",
        font="Vollkorn Black Italic",
        fontsize=14,
        linesp=18,
        align=1,
        fcolor="Gelb",
        language="de",
        linesp_mode=0,
    ))
    # V1: align 0->1.
    doc.add_para_style(ParaStyle(
        name="falzflyer/closer-url",
        font="Gotham Narrow Bold",
        fontsize=11,
        linesp=14,
        align=1,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    # V1: UNCHANGED (align=0; fcolor stays Dunkelgrün on white themen panels).
    doc.add_para_style(ParaStyle(
        name="falzflyer/thema-headline",
        font="Gotham Narrow Bold",
        fontsize=16,
        linesp=20,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
        linesp_mode=0,
    ))
    # V1: align 0->1, fontsize 9->10, linesp 11->13 (1.3x body convention).
    doc.add_para_style(ParaStyle(
        name="falzflyer/thema-body",
        font="Gotham Narrow Book",
        fontsize=10,
        linesp=13,
        align=1,
        fcolor="Black",
        language="de",
        linesp_mode=0,
    ))
    # V1: align 0->1, fcolor Dunkelgrün->White (P6 vollflächig).
    doc.add_para_style(ParaStyle(
        name="falzflyer/contact-headline",
        font="Gotham Narrow Bold",
        fontsize=16,
        linesp=20,
        align=1,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    # V1: align 0->1, fcolor Black->White (P6 2-Spalten on Dunkelgrün).
    doc.add_para_style(ParaStyle(
        name="falzflyer/contact-body",
        font="Gotham Narrow Book",
        fontsize=10,
        linesp=12,
        align=1,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    # V1: align 0->1, fcolor Black->White (P6 vollflächig).
    doc.add_para_style(ParaStyle(
        name="falzflyer/impressum",
        font="Gotham Narrow Book",
        fontsize=6,
        linesp=8,
        align=1,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    # NEW V1 (A): P1 Name-Card slogan — Gelb on Dunkelgrün.
    doc.add_para_style(ParaStyle(
        name="falzflyer/slogan-on-green",
        font="Gotham Narrow Bold",
        fontsize=14,
        linesp=17,
        align=1,
        fcolor="Gelb",
        language="de",
        linesp_mode=0,
    ))
    # NEW V1 (B): Pull-Quote — registered but no frame in V1 (deferred).
    doc.add_para_style(ParaStyle(
        name="falzflyer/quote-on-green",
        font="Vollkorn Black Italic",
        fontsize=18,
        linesp=20,
        align=1,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    # NEW V1 (C): Top-Title — Caps Bold White 11pt for P2/P3/P4/P5/P6
    # Top-Band tags (left-aligned within band per spec L76-80).
    doc.add_para_style(ParaStyle(
        name="falzflyer/top-title",
        font="Gotham Narrow Bold",
        fontsize=11,
        linesp=14,
        align=0,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    # NEW V1 (D): Themen-Eyebrow — Caps Bold Dunkelgrün 9pt for P4/P5
    # "THEMA 0X" labels; reused on P6 QR-Captions with frame fcolor=White
    # override.
    doc.add_para_style(ParaStyle(
        name="falzflyer/themen-eyebrow",
        font="Gotham Narrow Bold",
        fontsize=9,
        linesp=12,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
        linesp_mode=0,
    ))


def _add_front(doc, page0):
    # P3 vollflächig Dunkelgrün (V0 polygon — used by both P3 Top-Title
    # placement and the gruene-Klammer cross-panel constraint with P6).
    page0.add(Polygon(
        x_mm=FOLD_X2_MM,
        y_mm=-BLEED_MM,
        w_mm=PANEL_W_MM + BLEED_MM,
        h_mm=TRIM_H_MM + 2 * BLEED_MM,
        fill="Dunkelgrün",
        layer=LAYER_HINTERGRUND,
        anname="P3 Hintergrund",
    ))

    # ---- Panel 1 (Cover) — x=0..99 — V1 "grüne Klammer" outer pair -----
    # V1 P1 Top-Band — 31mm Dunkelgrün at the top, +3mm bleed extension
    # left + +3mm overshoot right (RESEARCH correction #3).
    page0.add(_top_band(0))

    # Logo Print-Soll (Trim-konsistent per Quickguide §"Logo-Größen"):
    #   M = 0.06 * min(trim_w, trim_h)
    #   For DIN-lang Zickzackfalz: min(297, 210) = 210 → M = 12.6 → 3M = 37.8 mm
    # The brand rule `brand:logo_size_3M` lives in
    # tools/sla_lib/builder/brand_constraints.py (already trim-konsistent);
    # V1 logo dims are 38×22 (P1 cover) and 38×34 (P6 footer) — both match Soll.
    # See shared/brand/DESIGN-SYSTEM-BRIEF.md §"Logo Print-Soll".
    logo_brand = HERE.parents[1] / "shared" / "logos" / "gruene-logo-bund-dunkel.png"
    logo_weiss = HERE.parents[1] / "shared" / "logos" / "gruene-weiss.png"
    if logo_weiss.exists():
        lc_data, lc_ext = pack_inline_image(logo_weiss.read_bytes(), "png")
        page0.add(ImageFrame(
            x_mm=6, y_mm=4, w_mm=38, h_mm=22,
            inline_image_data=lc_data, inline_image_ext=lc_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            anname="P1 Logo Grüne (weiss)",
        ))

    # Kandidat-Portrait — V1: y=28->34, h=105->100 (more breathing under
    # Top-Band; gives Name-Card more room). Frame dims only — build_preview
    # injects via INJECT_MAP at LIVE frame dims (post-#24 idiom).
    page0.add(ImageFrame(
        x_mm=6, y_mm=34, w_mm=87, h_mm=100,
        inline_image_data=None,
        inline_image_ext=None,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P1 Kandidat-Portrait",
    ))

    # NEW V1: P1 Name-Card — vollbleed bottom Dunkelgrün polygon.
    # Extends to bottom bleed: 134 + 79 = 213 = 210 + 3mm.
    page0.add(Polygon(
        x_mm=-3, y_mm=134, w_mm=105, h_mm=79,
        fill="Dunkelgrün",
        layer=LAYER_HINTERGRUND,
        anname="P1 Name-Card",
    ))

    # Kandidat-Name (V1: cand-name align=1 fcolor=White on Name-Card)
    page0.add(TextFrame(
        x_mm=6, y_mm=142, w_mm=87, h_mm=18,
        layer=LAYER_TEXT,
        style="falzflyer/cand-name",
        runs=[Run(text="Maria Beispiel",
                  paragraph_style="falzflyer/cand-name")],
        anname="P1 Kandidat-Name",
    ))
    # Slogan (V1: NEW slogan-on-green style — Gelb on Dunkelgrün, align=1)
    page0.add(TextFrame(
        x_mm=6, y_mm=164, w_mm=87, h_mm=20,
        layer=LAYER_TEXT,
        style="falzflyer/slogan-on-green",
        runs=[
            Run(text="Mut zur Klima-Wende.", separator="para",
                paragraph_style="falzflyer/slogan-on-green"),
            Run(text="Für Mödling.",
                paragraph_style="falzflyer/slogan-on-green"),
        ],
        anname="P1 Slogan",
    ))

    # ---- Panel 2 (Mein Plan) — x=99..198 — V1 Top-Band + Body-Backing ----
    # NEW V1: P2 Top-Band — 31mm Dunkelgrün, inner panel flush both folds.
    page0.add(_top_band(1))

    # NEW V1: P2 Top-Title "Mein Plan"
    page0.add(TextFrame(
        x_mm=105, y_mm=8, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/top-title",
        runs=[Run(text="Mein Plan",
                  paragraph_style="falzflyer/top-title")],
        anname="P2 Top-Title",
    ))

    # P2 Teaser-Headline — V1: y 20->38, h=22 (UNCHANGED style: redaktioneller)
    page0.add(TextFrame(
        x_mm=105, y_mm=38, w_mm=87, h_mm=22,
        layer=LAYER_TEXT,
        style="falzflyer/teaser-headline",
        runs=[Run(text="Was ich für Mödling will",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))

    # P2 Body-Backing — Hellgrün card backing for the teaser zone.
    # Issue #26: extend top to y=28 (flush against Top-Band end) so
    # the Teaser-Headline sits ON Hellgrün — satisfies brand §7
    # ("Typografie steht IMMER in Kombination mit Grün"). Also extend
    # bottom to y=213 (full bleed) so the bar matches P1 Name-Card
    # and P3 Hintergrund's vertical extent — fixes the user-cited
    # "Hellgrün bar misalignment with everything" bug.
    page0.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün",
        layer=LAYER_HINTERGRUND,
        anname="P2 Body-Backing",
    ))

    # P2 Teaser-Body — V1: x 105->113 (inset +8mm for breathing inside
    # Hellgrün card), y 44->72, w 87->73, h 130 (V1 style: fcolor=White
    # mutation; align=0 KEEP redaktioneller).
    page0.add(TextFrame(
        x_mm=113, y_mm=72, w_mm=73, h_mm=130,
        layer=LAYER_TEXT,
        style="falzflyer/teaser-body",
        runs=[Run(
            text=("Mödling hat einen Klimaplan — er muss umgesetzt werden. "
                  "Ich bringe Erfahrung aus 10 Jahren Energiewende-Beratung mit "
                  "und will sie für unsere Gemeinde einsetzen.\n\n"
                  "Drei Schwerpunkte: leistbares Wohnen, lokale Wirtschaft, "
                  "Bildung vor Ort."),
            paragraph_style="falzflyer/teaser-body",
        )],
        anname="P2 Teaser-Body",
    ))

    # P2 V0 had a small logo at the panel bottom (bund-dunkel 16×14 mm). V1
    # deletes it: the universal Top-Band system on P2 (added in T05+T07)
    # carries the brand identity; a second small logo competes with the
    # Body-Backing card and is redundant.

    # ---- Panel 3 (Wahltag) — x=198..297, on vollflächig Dunkelgrün -----
    # P3 Hintergrund polygon already added above (V0 frame, kept unchanged).

    # NEW V1: P3 Top-Title "Wahltag" — Gelb override (per spec L76-80, sits
    # within Dunkelgrün band but tagged Gelb to distinguish from White
    # top-titles on the other panels).
    page0.add(TextFrame(
        x_mm=204, y_mm=8, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/top-title",
        fcolor="Gelb",
        runs=[Run(text="Wahltag",
                  paragraph_style="falzflyer/top-title")],
        anname="P3 Top-Title",
    ))

    # Wahlkreuz hero — V1: y 30->44 (UNCHANGED size 50x50)
    wahlkreuz_path = HERE.parents[1] / "shared" / "assets" / "wahlkreuz.png"
    if not wahlkreuz_path.exists():
        raise FileNotFoundError(f"Wahlkreuz asset not found at {wahlkreuz_path}")
    wk_data, wk_ext = pack_inline_image(wahlkreuz_path.read_bytes(), "png")
    page0.add(ImageFrame(
        x_mm=222, y_mm=44, w_mm=50, h_mm=50,
        inline_image_data=wk_data,
        inline_image_ext=wk_ext,
        scale_type=0,
        ratio=1,
        layer=LAYER_BILDER,
        anname="P3 Wahlkreuz",
    ))
    # Closer headline — V1: y 90->100, h=32, closer-headline (mutated align=1)
    page0.add(TextFrame(
        x_mm=204, y_mm=100, w_mm=87, h_mm=32,
        layer=LAYER_TEXT,
        style="falzflyer/closer-headline",
        runs=[
            Run(text="Wähle Grün", separator="para",
                paragraph_style="falzflyer/closer-headline"),
            Run(text="am 23. Mai",
                paragraph_style="falzflyer/closer-headline"),
        ],
        anname="P3 Closer-Headline",
    ))
    # Datum-Akzent — V1: y 125->145, h=22, closer-datum (mutated align=1)
    page0.add(TextFrame(
        x_mm=204, y_mm=145, w_mm=87, h_mm=22,
        layer=LAYER_TEXT,
        style="falzflyer/closer-datum",
        runs=[Run(text="Sonntag, 23. Mai 2026",
                  paragraph_style="falzflyer/closer-datum")],
        anname="P3 Datum-Akzent",
    ))
    # URL — V1: y 175->185, h=12, closer-url (mutated align=1)
    page0.add(TextFrame(
        x_mm=204, y_mm=185, w_mm=87, h_mm=12,
        layer=LAYER_TEXT,
        style="falzflyer/closer-url",
        runs=[Run(text="gruene-moedling.at",
                  paragraph_style="falzflyer/closer-url")],
        anname="P3 URL",
    ))

    # ---- Falz-Linien (Front) ------
    page0.add(FoldLine(
        start_mm=(FOLD_X1_MM, 0),
        end_mm=(FOLD_X1_MM, TRIM_H_MM),
        layer_idx=LAYER_FALZ,
        anname="Falz x=99 (Front)",
    ))
    page0.add(FoldLine(
        start_mm=(FOLD_X2_MM, 0),
        end_mm=(FOLD_X2_MM, TRIM_H_MM),
        layer_idx=LAYER_FALZ,
        anname="Falz x=198 (Front)",
    ))


def _add_back(doc, page1):
    # Themen-photo slots (issue #13): photos injected via INJECT_MAP in
    # build_preview() — the frames here carry geometry only. Post-#24
    # idiom: read frame dims LIVE rather than hardcoding target_w/h.
    # Theme 4 (Lokale Wirtschaft) stays text-only in V0; T08 makes it a
    # photo slot for V1.

    # ---- Panel 4 — Themen 1+2 (x=0..99) — V1 -----
    # NEW V1: P4 Top-Band — outer panel, +3mm bleed extension left.
    page1.add(_top_band(3))

    # NEW V1: P4 Top-Title "Themen 1·2" (middle-dot U+00B7 literal)
    page1.add(TextFrame(
        x_mm=6, y_mm=8, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/top-title",
        runs=[Run(text="Themen 1·2",
                  paragraph_style="falzflyer/top-title")],
        anname="P4 Top-Title",
    ))

    # NEW V1: P4 Thema 1 Eyebrow + Headline + Photo (h 24->44 = 1.5:1
    # native aspect; closes today's halb-leer Streifen).
    page1.add(TextFrame(
        x_mm=6, y_mm=38, w_mm=87, h_mm=6,
        layer=LAYER_TEXT, style="falzflyer/themen-eyebrow",
        runs=[Run(text="THEMA 01",
                  paragraph_style="falzflyer/themen-eyebrow")],
        anname="P4 Thema 1 — Eyebrow",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=46, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-headline",
        runs=[Run(text="Klimaplan umsetzen",
                  paragraph_style="falzflyer/thema-headline")],
        anname="P4 Thema 1 — Headline",
    ))
    page1.add(ImageFrame(
        x_mm=6, y_mm=62, w_mm=87, h_mm=44,
        inline_image_data=None,
        inline_image_ext=None,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P4 Thema 1 — Photo",
    ))

    # NEW V1: Thema 1·2 Trenner — 3mm Hellgrün strip dividing the two
    # themen sub-layouts.
    page1.add(Polygon(
        x_mm=-3, y_mm=108, w_mm=105, h_mm=3,
        fill="Hellgrün",
        layer=LAYER_HINTERGRUND,
        anname="P4 Thema 1·2 Trenner",
    ))

    # P4 Thema 1 Body — V1 mutated style (align=1, 10pt, 13 linesp)
    page1.add(TextFrame(
        x_mm=6, y_mm=114, w_mm=87, h_mm=26,
        layer=LAYER_TEXT, style="falzflyer/thema-body",
        runs=[Run(
            text=("Solar auf jedes Gemeindedach. "
                  "Heizungstausch fördern. "
                  "Öffis verdoppeln."),
            paragraph_style="falzflyer/thema-body",
        )],
        anname="P4 Thema 1 — Body",
    ))

    # P4 Thema 2 Eyebrow + Headline + Photo + Body (Issue #26: Body
    # restored — user-cited "Thema 02 has no text at all" fix; the
    # 4-thema panel now has parallel structure across all N).
    # Photo shrunk h=44->24 to make room for the Body below within the
    # 210mm panel height. Asymmetric photo size vs Thema 1 is the
    # trade-off for the symmetric text content.
    page1.add(TextFrame(
        x_mm=6, y_mm=144, w_mm=87, h_mm=6,
        layer=LAYER_TEXT, style="falzflyer/themen-eyebrow",
        runs=[Run(text="THEMA 02",
                  paragraph_style="falzflyer/themen-eyebrow")],
        anname="P4 Thema 2 — Eyebrow",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=152, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-headline",
        runs=[Run(text="Leistbares Wohnen",
                  paragraph_style="falzflyer/thema-headline")],
        anname="P4 Thema 2 — Headline",
    ))
    page1.add(ImageFrame(
        x_mm=6, y_mm=168, w_mm=87, h_mm=24,
        inline_image_data=None,
        inline_image_ext=None,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P4 Thema 2 — Photo",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=196, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-body",
        runs=[Run(
            text=("Gemeindewohnungen ausbauen. "
                  "Mietpreisbremse durchsetzen. "
                  "Sanieren statt versiegeln."),
            paragraph_style="falzflyer/thema-body",
        )],
        anname="P4 Thema 2 — Body",
    ))

    # ---- Panel 5 — Themen 3+4 (x=99..198) — V1 mirrors P4 -----
    # NEW V1: P5 Top-Band — inner panel, flush both folds.
    page1.add(_top_band(4))

    # NEW V1: P5 Top-Title "Themen 3·4" (middle-dot U+00B7 literal)
    page1.add(TextFrame(
        x_mm=105, y_mm=8, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/top-title",
        runs=[Run(text="Themen 3·4",
                  paragraph_style="falzflyer/top-title")],
        anname="P5 Top-Title",
    ))

    # P5 Thema 3 Eyebrow + Headline + Photo (h=44 V1)
    page1.add(TextFrame(
        x_mm=105, y_mm=38, w_mm=87, h_mm=6,
        layer=LAYER_TEXT, style="falzflyer/themen-eyebrow",
        runs=[Run(text="THEMA 03",
                  paragraph_style="falzflyer/themen-eyebrow")],
        anname="P5 Thema 3 — Eyebrow",
    ))
    page1.add(TextFrame(
        x_mm=105, y_mm=46, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-headline",
        runs=[Run(text="Bildung vor Ort",
                  paragraph_style="falzflyer/thema-headline")],
        anname="P5 Thema 3 — Headline",
    ))
    page1.add(ImageFrame(
        x_mm=105, y_mm=62, w_mm=87, h_mm=44,
        inline_image_data=None,
        inline_image_ext=None,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P5 Thema 3 — Photo",
    ))

    # NEW V1: Thema 3·4 Trenner — 3mm Hellgrün strip.
    page1.add(Polygon(
        x_mm=99, y_mm=108, w_mm=99, h_mm=3,
        fill="Hellgrün",
        layer=LAYER_HINTERGRUND,
        anname="P5 Thema 3·4 Trenner",
    ))

    # P5 Thema 3 Body — V1 mutated style
    page1.add(TextFrame(
        x_mm=105, y_mm=114, w_mm=87, h_mm=26,
        layer=LAYER_TEXT, style="falzflyer/thema-body",
        runs=[Run(
            text=("Volksschulen ausbauen. "
                  "Nachmittagsbetreuung gratis. "
                  "Schulwege sicher."),
            paragraph_style="falzflyer/thema-body",
        )],
        anname="P5 Thema 3 — Body",
    ))

    # P5 Thema 4 Eyebrow + Headline + Photo + Body (Issue #26: Body
    # added — user-cited "Thema 04 has no text at all" fix). Photo
    # shrunk h=44->24 to make room for the Body. Mirrors the P4
    # Thema 2 layout for cross-panel consistency.
    page1.add(TextFrame(
        x_mm=105, y_mm=144, w_mm=87, h_mm=6,
        layer=LAYER_TEXT, style="falzflyer/themen-eyebrow",
        runs=[Run(text="THEMA 04",
                  paragraph_style="falzflyer/themen-eyebrow")],
        anname="P5 Thema 4 — Eyebrow",
    ))
    page1.add(TextFrame(
        x_mm=105, y_mm=152, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-headline",
        runs=[Run(text="Lokale Wirtschaft",
                  paragraph_style="falzflyer/thema-headline")],
        anname="P5 Thema 4 — Headline",
    ))
    page1.add(ImageFrame(
        x_mm=105, y_mm=168, w_mm=87, h_mm=24,
        inline_image_data=None,
        inline_image_ext=None,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P5 Thema 4 — Photo",
    ))
    page1.add(TextFrame(
        x_mm=105, y_mm=196, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-body",
        runs=[Run(
            text=("Regionale Betriebe stärken. "
                  "Direktvermarktung fördern. "
                  "Lehrlinge ausbilden."),
            paragraph_style="falzflyer/thema-body",
        )],
        anname="P5 Thema 4 — Body",
    ))

    # ---- Panel 6 — Kontakt + Impressum (x=198..297) — V1 vollflächig -----
    # NEW V1: P6 Hintergrund — vollflächig Dunkelgrün polygon analog to P3
    # (RESEARCH correction #3 / locked #5). Forms the grüne-Klammer pair
    # (P3 Hintergrund <-> P6 Hintergrund — both 102×216 vollbleed).
    page1.add(Polygon(
        x_mm=FOLD_X2_MM,
        y_mm=-BLEED_MM,
        w_mm=PANEL_W_MM + BLEED_MM,
        h_mm=TRIM_H_MM + 2 * BLEED_MM,
        fill="Dunkelgrün",
        layer=LAYER_HINTERGRUND,
        anname="P6 Hintergrund",
    ))

    # NEW V1: P6 Top-Title "Kontakt" — Caps Bold White 11pt
    page1.add(TextFrame(
        x_mm=204, y_mm=8, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/top-title",
        runs=[Run(text="Kontakt", paragraph_style="falzflyer/top-title")],
        anname="P6 Top-Title",
    ))

    # P6 Kontakt-Headline — V1: y 20->38, h=14, contact-headline (mutated:
    # align=1, fcolor=White)
    page1.add(TextFrame(
        x_mm=204, y_mm=38, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/contact-headline",
        runs=[Run(text="Sprich mich an",
                  paragraph_style="falzflyer/contact-headline")],
        anname="P6 Kontakt-Headline",
    ))

    # V1: 4 Kontakt-Cells in 2-column layout symmetric around
    # AXIS_P6_CENTER_X = 247.5. Cells use contact-body (V1 mutated:
    # align=1, fcolor=White). Replaces V0's 2 stacked frames.
    page1.add(TextFrame(
        x_mm=204, y_mm=62, w_mm=41, h_mm=20,
        layer=LAYER_TEXT, style="falzflyer/contact-body",
        runs=[
            Run(text="Hauptstraße 12", separator="para",
                paragraph_style="falzflyer/contact-body"),
            Run(text="2340 Mödling",
                paragraph_style="falzflyer/contact-body"),
        ],
        anname="P6 Adresse",
    ))
    page1.add(TextFrame(
        x_mm=250, y_mm=62, w_mm=41, h_mm=20,
        layer=LAYER_TEXT, style="falzflyer/contact-body",
        runs=[Run(text="+43 660 1234567",
                  paragraph_style="falzflyer/contact-body")],
        anname="P6 Telefon",
    ))
    page1.add(TextFrame(
        x_mm=204, y_mm=90, w_mm=41, h_mm=20,
        layer=LAYER_TEXT, style="falzflyer/contact-body",
        runs=[Run(text="maria.beispiel@gruene-moedling.at",
                  paragraph_style="falzflyer/contact-body")],
        anname="P6 Email",
    ))
    page1.add(TextFrame(
        x_mm=250, y_mm=90, w_mm=41, h_mm=20,
        layer=LAYER_TEXT, style="falzflyer/contact-body",
        runs=[
            Run(text="Sprechtag", separator="para",
                paragraph_style="falzflyer/contact-body"),
            Run(text="Mi 17–19 Uhr",
                paragraph_style="falzflyer/contact-body"),
        ],
        anname="P6 Sprechtag",
    ))

    # QR codes (Issue #11): two slots, qr-mitmachen + qr-termine. Conditional
    # inject — empty slots in fresh checkouts. V1: w 30->24, x repositioned
    # to mirror around AXIS_P6_CENTER_X=247.5.
    qr_mitmachen_path = HERE / "samples" / "qr-mitmachen.png"
    qr_termine_path = HERE / "samples" / "qr-termine.png"
    qr_m_data, qr_m_ext = (None, None)
    qr_t_data, qr_t_ext = (None, None)
    if qr_mitmachen_path.exists():
        qr_m_data, qr_m_ext = pack_inline_image(
            qr_mitmachen_path.read_bytes(), "png"
        )
    if qr_termine_path.exists():
        qr_t_data, qr_t_ext = pack_inline_image(
            qr_termine_path.read_bytes(), "png"
        )
    page1.add(ImageFrame(
        x_mm=218, y_mm=128, w_mm=24, h_mm=24,
        inline_image_data=qr_m_data,
        inline_image_ext=qr_m_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P6 QR-Code (mitmachen)",
    ))
    # NEW V1: QR caption "MITMACHEN" — themen-eyebrow with frame fcolor
    # override (eyebrow style is Dunkelgrün; on P6 vollflächig need White).
    page1.add(TextFrame(
        x_mm=218, y_mm=154, w_mm=24, h_mm=6,
        layer=LAYER_TEXT, style="falzflyer/themen-eyebrow",
        fcolor="White",
        runs=[Run(text="MITMACHEN",
                  paragraph_style="falzflyer/themen-eyebrow")],
        anname="P6 QR-Caption (mitmachen)",
    ))
    page1.add(ImageFrame(
        x_mm=254, y_mm=128, w_mm=24, h_mm=24,
        inline_image_data=qr_t_data,
        inline_image_ext=qr_t_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P6 QR-Code (termine)",
    ))
    # NEW V1: QR caption "TERMINE"
    page1.add(TextFrame(
        x_mm=254, y_mm=154, w_mm=24, h_mm=6,
        layer=LAYER_TEXT, style="falzflyer/themen-eyebrow",
        fcolor="White",
        runs=[Run(text="TERMINE",
                  paragraph_style="falzflyer/themen-eyebrow")],
        anname="P6 QR-Caption (termine)",
    ))

    # P6 Logo Grüne (weiss). V1: 38×34 mm trim-konform 3M = 37.8 mm soll,
    # white wordmark on Dunkelgrün vollflächig P6, centered around
    # AXIS_P6_CENTER_X = 247.5 → x = 247.5 - 38/2 = 228.5 ≈ 228 mm.
    logo_weiss_p6 = HERE.parents[1] / "shared" / "logos" / "gruene-weiss.png"
    if logo_weiss_p6.exists():
        lc6_data, lc6_ext = pack_inline_image(logo_weiss_p6.read_bytes(), "png")
        page1.add(ImageFrame(
            x_mm=228, y_mm=168, w_mm=38, h_mm=34,
            inline_image_data=lc6_data, inline_image_ext=lc6_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            anname="P6 Logo Grüne (weiss)",
        ))

    # Impressum (V1: h 60->8, y=200, impressum mutated align=1 fcolor=White)
    page1.add(TextFrame(
        x_mm=204, y_mm=200, w_mm=87, h_mm=8,
        layer=LAYER_TEXT, style="falzflyer/impressum",
        runs=[Run(
            text=("Medieninhaber: Die Grünen NÖ, "
                  "Daniel-Gran-Straße 48, 3100 St. Pölten."),
            paragraph_style="falzflyer/impressum",
        )],
        anname="P6 Impressum",
    ))

    # ---- Falz-Linien (Back) -----
    page1.add(FoldLine(
        start_mm=(FOLD_X1_MM, 0),
        end_mm=(FOLD_X1_MM, TRIM_H_MM),
        layer_idx=LAYER_FALZ,
        anname="Falz x=99 (Back)",
    ))
    page1.add(FoldLine(
        start_mm=(FOLD_X2_MM, 0),
        end_mm=(FOLD_X2_MM, TRIM_H_MM),
        layer_idx=LAYER_FALZ,
        anname="Falz x=198 (Back)",
    ))


def build_template() -> Document:
    """Return clean Document with frame definitions but NO inline image data
    on INJECT_MAP-managed photos. structural_check + spec_check + smoke
    consume this; build_preview() wraps it for actual rendering."""
    doc = Document(
        brand=Brand.gruene_noe(),
        title="Kandidat-Falzflyer DIN-lang",
        template_id="kandidat-falzflyer-din-lang",
        author="Die Grünen Niederösterreich",
        facing_pages=False,
        layers=[
            DocumentLayer(name="Hintergrund", visible=True, printable=True, flow=True),
            DocumentLayer(name="Bilder", visible=True, printable=True, flow=True),
            DocumentLayer(name="Text", visible=True, printable=True, flow=True),
            DocumentLayer(name="Falz", visible=True, printable=False, flow=False),
        ],
    )
    doc.add_color("Falz", cmyk=(100, 0, 0, 0), spot=True)
    _add_styles(doc)

    doc.add_master(
        name="Normal",
        size=(TRIM_W_MM, TRIM_H_MM),
        bleed_mm=BLEED_MM,
        margins_mm=(0.0, 0.0, 0.0, 0.0),  # per-panel margins handled inside
    )
    page0 = doc.add_page(size=(TRIM_W_MM, TRIM_H_MM), bleed_mm=BLEED_MM,
                         margins_mm=(0.0, 0.0, 0.0, 0.0), master="Normal")
    page1 = doc.add_page(size=(TRIM_W_MM, TRIM_H_MM), bleed_mm=BLEED_MM,
                         margins_mm=(0.0, 0.0, 0.0, 0.0), master="Normal")

    _add_front(doc, page0)
    _add_back(doc, page1)

    return doc


def build_preview() -> Document:
    """Inject demo library images for gallery PNG render (#24 idiom).

    Pre-crops each library image to the LIVE frame dimensions via
    library.inject_into_frame, eliminating the literal-target drift that
    produced regressions in earlier iters.
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
# Issue #21 — V1 "Falz-Rhythm" CONSTRAINTS list (read by structural_check).
#
# 22 entries — replaces V0's 9. Captures the full Falz-Rhythm design language:
#   - Universal Top-Band (4 explicit polygons + 2 vollflächig-anchored)
#   - P3↔P6 grüne-Klammer cross-panel pair
#   - P4 + P5 themen sub-layout mirror (intra-panel)
#   - Cross-panel themen photos uniform size
#   - P6 Kontakt 2-Spalten symmetric around AXIS_P6_CENTER_X = 247.5
#   - Logo Print-Soll consistency on P1 + P6
#   - Style consistency across thema headlines/bodies
#
# All anname strings use REAL names (em-dash U+2014 literal, case-sensitive).
# AXIS_P6_CENTER_X = 247.5 mm (P6 horizontal center: 198 + 99/2).
# ---------------------------------------------------------------------------
AXIS_P6_CENTER_X_MM = 247.5

CONSTRAINTS = [
    # ── Top-Band uniformity (4 explicit polygons; P3+P6 vollflächig handled below) ──
    same_size(
        "P1 Top-Band", "P2 Top-Band", "P4 Top-Band", "P5 Top-Band",
        axis="h", name="top_bands_uniform_h",
    ),
    inside("P3 Top-Title", "P3 Hintergrund", name="p3_top_title_anchored"),
    inside("P6 Top-Title", "P6 Hintergrund", name="p6_top_title_anchored"),

    # ── P3↔P6 grüne-Klammer (vollflächig pair) ──
    same_size("P3 Hintergrund", "P6 Hintergrund", name="gruene_klammer_p3_p6"),

    # ── P4 themen sub-layout mirror (Thema 1 vs 2 within panel) ──
    # Issue #26: Thema 2 Photo shrunk to make room for restored Body;
    # Photos no longer same_size between Thema 1 and Thema 2 — they share
    # x-axis (left/right edges) and width but not height. same_x covers
    # this without over-constraining vertical extent.
    same_x("P4 Thema 1 — Eyebrow", "P4 Thema 2 — Eyebrow",
           name="p4_eyebrow_x"),
    same_x("P4 Thema 1 — Headline", "P4 Thema 2 — Headline",
           name="p4_headline_x"),
    same_x("P4 Thema 1 — Photo", "P4 Thema 2 — Photo",
           name="p4_photo_x"),
    same_x("P4 Thema 1 — Body", "P4 Thema 2 — Body",
           name="p4_body_x"),
    aligned_below("P4 Thema 1 — Photo", "P4 Thema 1 — Headline", gap_mm=2.0,
                  name="p4_t1_photo_anchored"),

    # ── P5 themen sub-layout mirror (Thema 3 vs 4 within panel) ──
    same_x("P5 Thema 3 — Eyebrow", "P5 Thema 4 — Eyebrow",
           name="p5_eyebrow_x"),
    same_x("P5 Thema 3 — Headline", "P5 Thema 4 — Headline",
           name="p5_headline_x"),
    same_x("P5 Thema 3 — Photo", "P5 Thema 4 — Photo",
           name="p5_photo_x"),
    same_x("P5 Thema 3 — Body", "P5 Thema 4 — Body",
           name="p5_body_x"),
    aligned_below("P5 Thema 3 — Photo", "P5 Thema 3 — Headline", gap_mm=2.0,
                  name="p5_t3_photo_anchored"),

    # ── Cross-panel themen Headline-y baseline (P4 ↔ P5) ──
    # All four themen-headlines share their top-y so the eye-flow across
    # the spread reads horizontally. Replaces the prior cross-panel
    # photos_size constraint (Photos now vary in height).
    same_y("P4 Thema 1 — Headline", "P5 Thema 3 — Headline",
           name="cross_panel_t1_t3_headline_y"),
    same_y("P4 Thema 2 — Headline", "P5 Thema 4 — Headline",
           name="cross_panel_t2_t4_headline_y"),

    # ── P6 Kontakt 2-Spalten symmetric around AXIS_P6_CENTER_X = 247.5 ──
    # mirrored_x pairs cover row symmetry; same_y baselines + cells_uniform
    # are deferred to the geometry test (T11 invariant 13/19) to keep this
    # CONSTRAINTS list at exactly 22 (per RESEARCH locked count).
    mirrored_x("P6 Adresse", "P6 Telefon",
               axis_mm=AXIS_P6_CENTER_X_MM, name="p6_col_mirror_row1"),
    mirrored_x("P6 Email", "P6 Sprechtag",
               axis_mm=AXIS_P6_CENTER_X_MM, name="p6_col_mirror_row2"),
    mirrored_x("P6 QR-Code (mitmachen)", "P6 QR-Code (termine)",
               axis_mm=AXIS_P6_CENTER_X_MM, name="p6_qr_mirror"),
    same_size("P6 QR-Code (mitmachen)", "P6 QR-Code (termine)",
              name="p6_qrs_size"),

    # ── Logo Print-Soll consistency on P1 + P6 ──
    same_size("P1 Logo Grüne (weiss)", "P6 Logo Grüne (weiss)",
              axis="w", name="logos_print_soll_w_uniform"),

    # ── Style consistency ──
    same_style(
        "P4 Thema 1 — Headline", "P4 Thema 2 — Headline",
        "P5 Thema 3 — Headline", "P5 Thema 4 — Headline",
        name="thema_headline_style_consistent",
    ),
    same_style(
        "P4 Thema 1 — Body", "P5 Thema 3 — Body",
        name="thema_body_style_consistent",
    ),
]


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

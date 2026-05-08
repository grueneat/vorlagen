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


def _add_styles(doc):
    """Register the 11 falzflyer-local paragraph styles."""
    doc.add_para_style(ParaStyle(
        name="falzflyer/cand-name",
        font="Vollkorn Black Italic",
        fontsize=24,
        linesp=27,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name="falzflyer/slogan",
        font="Gotham Narrow Bold",
        fontsize=14,
        linesp=17,
        align=0,
        fcolor="Black",
        language="de",
        linesp_mode=0,
    ))
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
    doc.add_para_style(ParaStyle(
        name="falzflyer/teaser-body",
        font="Gotham Narrow Book",
        fontsize=11,
        linesp=14,
        align=0,
        fcolor="Black",
        language="de",
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name="falzflyer/closer-headline",
        font="Gotham Narrow Bold",
        fontsize=22,
        linesp=26,
        align=0,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name="falzflyer/closer-datum",
        font="Vollkorn Black Italic",
        fontsize=14,
        linesp=18,
        align=0,
        fcolor="Gelb",
        language="de",
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name="falzflyer/closer-url",
        font="Gotham Narrow Bold",
        fontsize=11,
        linesp=14,
        align=0,
        fcolor="White",
        language="de",
        linesp_mode=0,
    ))
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
    doc.add_para_style(ParaStyle(
        name="falzflyer/thema-body",
        font="Gotham Narrow Book",
        fontsize=9,
        linesp=11,
        align=0,
        fcolor="Black",
        language="de",
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name="falzflyer/contact-headline",
        font="Gotham Narrow Bold",
        fontsize=16,
        linesp=20,
        align=0,
        fcolor="Dunkelgrün",
        language="de",
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name="falzflyer/contact-body",
        font="Gotham Narrow Book",
        fontsize=10,
        linesp=12,
        align=0,
        fcolor="Black",
        language="de",
        linesp_mode=0,
    ))
    doc.add_para_style(ParaStyle(
        name="falzflyer/impressum",
        font="Gotham Narrow Book",
        fontsize=6,
        linesp=8,
        align=0,
        fcolor="Black",
        language="de",
        linesp_mode=0,
    ))


def _add_front(doc, page0):
    # Panel 3 (Closer) Dunkelgrün full-bleed background
    page0.add(Polygon(
        x_mm=FOLD_X2_MM,
        y_mm=-BLEED_MM,
        w_mm=PANEL_W_MM + BLEED_MM,
        h_mm=TRIM_H_MM + 2 * BLEED_MM,
        fill="Dunkelgrün",
        layer=LAYER_HINTERGRUND,
        anname="P3 Hintergrund",
    ))

    # ---- Panel 1 (Cover) — x=0..99 -----
    # Logo (Brand-Bund) top-left corner. iter-3: migrated from
    # gruene-cmyk.png wordmark to gruene-logo-bund-dunkel.png.
    # Frame 20×18 mm honors the new ~1.12:1 aspect within the
    # available y=10..28 zone (portrait starts at y=28). On DIN-lang
    # (kurze Kante=105) Quickguide Print target = 3×M = 18.9 mm —
    # 20 mm sits at 106 %, well within tolerance.
    logo_brand = HERE.parents[1] / "shared" / "logos" / "gruene-logo-bund-dunkel.png"
    logo_weiss = HERE.parents[1] / "shared" / "logos" / "gruene-weiss.png"
    if logo_brand.exists():
        lc_data, lc_ext = pack_inline_image(logo_brand.read_bytes(), "png")
        page0.add(ImageFrame(
            x_mm=6, y_mm=10, w_mm=20, h_mm=18,
            inline_image_data=lc_data, inline_image_ext=lc_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            anname="P1 Logo Grüne",
        ))

    # Kandidat-Portrait — central library reference (#13). When the library
    # has the entry, the demo portrait is cropped to the 87×105mm frame and
    # embedded with watermark re-applied (R-WATERMARK-CROP). On fresh
    # checkouts without the library JPGs, the slot stays empty.
    portrait_data, portrait_ext = (None, None)
    portrait_img = library.load("portrait_maria", optional=True)
    if portrait_img is not None:
        portrait_bytes = library.crop_for_frame(
            portrait_img, target_w_mm=87, target_h_mm=105
        )
        portrait_data, portrait_ext = pack_inline_image(portrait_bytes, "jpg")
    page0.add(ImageFrame(
        x_mm=6, y_mm=28, w_mm=87, h_mm=105,
        inline_image_data=portrait_data,
        inline_image_ext=portrait_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P1 Kandidat-Portrait",
    ))
    # Kandidat-Name
    page0.add(TextFrame(
        x_mm=6, y_mm=138, w_mm=87, h_mm=18,
        layer=LAYER_TEXT,
        style="falzflyer/cand-name",
        runs=[Run(text="Maria Beispiel",
                  paragraph_style="falzflyer/cand-name")],
        anname="P1 Kandidat-Name",
    ))
    # Slogan (2 lines)
    page0.add(TextFrame(
        x_mm=6, y_mm=158, w_mm=87, h_mm=40,
        layer=LAYER_TEXT,
        style="falzflyer/slogan",
        runs=[
            Run(text="Mut zur Klima-Wende.", separator="para",
                paragraph_style="falzflyer/slogan"),
            Run(text="Für Mödling.",
                paragraph_style="falzflyer/slogan"),
        ],
        anname="P1 Slogan",
    ))

    # ---- Panel 2 (Teaser) — x=99..198 -----
    page0.add(TextFrame(
        x_mm=105, y_mm=20, w_mm=87, h_mm=22,
        layer=LAYER_TEXT,
        style="falzflyer/teaser-headline",
        runs=[Run(text="Was ich für Mödling will",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page0.add(TextFrame(
        x_mm=105, y_mm=44, w_mm=87, h_mm=130,
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

    # P2 small logo at bottom of panel. iter-3: bund-dunkel at 16×14 mm
    # honors the new ~1.12:1 aspect; bottom-anchored within y=188..205
    # (panel bottom at y=210, leaving 5 mm clearance).
    if logo_brand.exists():
        lc2_data, lc2_ext = pack_inline_image(logo_brand.read_bytes(), "png")
        page0.add(ImageFrame(
            x_mm=105, y_mm=188, w_mm=16, h_mm=14,
            inline_image_data=lc2_data, inline_image_ext=lc2_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            anname="P2 Logo (klein)",
        ))

    # ---- Panel 3 (Closer) — x=198..297, on Dunkelgrün --------
    # Wahlkreuz hero (Dunkelgrün bg already provides D12 contract)
    wahlkreuz_path = HERE.parents[1] / "shared" / "assets" / "wahlkreuz.png"
    if not wahlkreuz_path.exists():
        raise FileNotFoundError(f"Wahlkreuz asset not found at {wahlkreuz_path}")
    wk_data, wk_ext = pack_inline_image(wahlkreuz_path.read_bytes(), "png")
    page0.add(ImageFrame(
        x_mm=222, y_mm=30, w_mm=50, h_mm=50,
        inline_image_data=wk_data,
        inline_image_ext=wk_ext,
        scale_type=0,
        ratio=1,
        layer=LAYER_BILDER,
        anname="P3 Wahlkreuz",
    ))
    # Closer headline (white on Dunkelgrün)
    page0.add(TextFrame(
        x_mm=204, y_mm=90, w_mm=87, h_mm=32,
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
    # Datum-Akzent (Gelb)
    page0.add(TextFrame(
        x_mm=204, y_mm=125, w_mm=87, h_mm=22,
        layer=LAYER_TEXT,
        style="falzflyer/closer-datum",
        runs=[Run(text="Sonntag, 23. Mai 2026",
                  paragraph_style="falzflyer/closer-datum")],
        anname="P3 Datum-Akzent",
    ))
    # URL
    page0.add(TextFrame(
        x_mm=204, y_mm=175, w_mm=87, h_mm=12,
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
    # Themen-photo slots (issue #13): 3 small landscape images cropped from
    # central library. Frame aspect 87×24mm = 3.6:1 — aggressive horizontal
    # crop from 1.5:1 source (1536×1024). library.crop_for_frame() re-applies
    # the Symbolfoto watermark band on the cropped output (R-WATERMARK-CROP).
    # Theme 4 (Lokale Wirtschaft) stays text-only to keep panel rhythm.
    THEMEN_LIBRARY_IDS = {
        "klimaschutz": "themen_klimaschutz_solar",
        "soziales":    "themen_soziales_kaffeehaus",  # D8 fix: kaffeehaus, not gemeindebau
        "bildung":     "themen_bildung_volksschule",
    }
    THEMEN_FRAME_W_MM = 87.0
    THEMEN_FRAME_H_MM = 24.0

    def _photo_inline(name):
        img = library.load(THEMEN_LIBRARY_IDS[name], optional=True)
        if img is None:
            return (None, None)
        cropped = library.crop_for_frame(
            img, target_w_mm=THEMEN_FRAME_W_MM, target_h_mm=THEMEN_FRAME_H_MM
        )
        return pack_inline_image(cropped, "jpg")

    # ---- Panel 4 — Themen 1+2 (x=0..99) -----
    page1.add(TextFrame(
        x_mm=6, y_mm=20, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-headline",
        runs=[Run(text="Klimaplan umsetzen",
                  paragraph_style="falzflyer/thema-headline")],
        anname="P4 Thema 1 — Headline",
    ))
    p4_t1_data, p4_t1_ext = _photo_inline("klimaschutz")
    page1.add(ImageFrame(
        x_mm=6, y_mm=36, w_mm=87, h_mm=24,
        inline_image_data=p4_t1_data,
        inline_image_ext=p4_t1_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P4 Thema 1 — Photo",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=62, w_mm=87, h_mm=32,
        layer=LAYER_TEXT, style="falzflyer/thema-body",
        runs=[Run(
            text=("Solar auf jedes Gemeindedach. "
                  "Heizungstausch fördern. "
                  "Öffis verdoppeln."),
            paragraph_style="falzflyer/thema-body",
        )],
        anname="P4 Thema 1 — Body",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=105, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-headline",
        runs=[Run(text="Leistbares Wohnen",
                  paragraph_style="falzflyer/thema-headline")],
        anname="P4 Thema 2 — Headline",
    ))
    p4_t2_data, p4_t2_ext = _photo_inline("soziales")
    page1.add(ImageFrame(
        x_mm=6, y_mm=121, w_mm=87, h_mm=24,
        inline_image_data=p4_t2_data,
        inline_image_ext=p4_t2_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P4 Thema 2 — Photo",
    ))
    page1.add(TextFrame(
        x_mm=6, y_mm=147, w_mm=87, h_mm=32,
        layer=LAYER_TEXT, style="falzflyer/thema-body",
        runs=[Run(
            text=("Gemeinde-Wohnbau ankurbeln. "
                  "Mietpreis-Bremse für Neubauten."),
            paragraph_style="falzflyer/thema-body",
        )],
        anname="P4 Thema 2 — Body",
    ))

    # ---- Panel 5 — Themen 3+4 (x=99..198) -----
    page1.add(TextFrame(
        x_mm=105, y_mm=20, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-headline",
        runs=[Run(text="Bildung vor Ort",
                  paragraph_style="falzflyer/thema-headline")],
        anname="P5 Thema 3 — Headline",
    ))
    p5_t3_data, p5_t3_ext = _photo_inline("bildung")
    page1.add(ImageFrame(
        x_mm=105, y_mm=36, w_mm=87, h_mm=24,
        inline_image_data=p5_t3_data,
        inline_image_ext=p5_t3_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P5 Thema 3 — Photo",
    ))
    page1.add(TextFrame(
        x_mm=105, y_mm=62, w_mm=87, h_mm=32,
        layer=LAYER_TEXT, style="falzflyer/thema-body",
        runs=[Run(
            text=("Volksschulen ausbauen. "
                  "Nachmittagsbetreuung gratis. "
                  "Schulwege sicher."),
            paragraph_style="falzflyer/thema-body",
        )],
        anname="P5 Thema 3 — Body",
    ))
    page1.add(TextFrame(
        x_mm=105, y_mm=105, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/thema-headline",
        runs=[Run(text="Lokale Wirtschaft",
                  paragraph_style="falzflyer/thema-headline")],
        anname="P5 Thema 4 — Headline",
    ))
    page1.add(TextFrame(
        x_mm=105, y_mm=121, w_mm=87, h_mm=58,
        layer=LAYER_TEXT, style="falzflyer/thema-body",
        runs=[Run(
            text=("Regionale Lieferketten. "
                  "Handwerks-Förderung. "
                  "Kleinbetriebe statt Konzern-Filialen."),
            paragraph_style="falzflyer/thema-body",
        )],
        anname="P5 Thema 4 — Body",
    ))

    # ---- Panel 6 — Kontakt + Impressum (x=198..297) -----
    page1.add(TextFrame(
        x_mm=204, y_mm=20, w_mm=87, h_mm=14,
        layer=LAYER_TEXT, style="falzflyer/contact-headline",
        runs=[Run(text="Sprich mich an",
                  paragraph_style="falzflyer/contact-headline")],
        anname="P6 Kontakt-Headline",
    ))
    page1.add(TextFrame(
        x_mm=204, y_mm=36, w_mm=87, h_mm=20,
        layer=LAYER_TEXT, style="falzflyer/contact-body",
        runs=[
            Run(text="Hauptstraße 12", separator="para",
                paragraph_style="falzflyer/contact-body"),
            Run(text="2340 Mödling",
                paragraph_style="falzflyer/contact-body"),
        ],
        anname="P6 Kontakt-Adresse",
    ))
    page1.add(TextFrame(
        x_mm=204, y_mm=58, w_mm=87, h_mm=20,
        layer=LAYER_TEXT, style="falzflyer/contact-body",
        runs=[
            Run(text="maria.beispiel@gruene-moedling.at", separator="para",
                paragraph_style="falzflyer/contact-body"),
            Run(text="+43 660 1234567",
                paragraph_style="falzflyer/contact-body"),
        ],
        anname="P6 Kontakt-Email-Tel",
    ))
    # QR codes (Issue #11): two slots, qr-mitmachen + qr-termine. Conditional
    # inject — empty slots in fresh checkouts.
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
        x_mm=210, y_mm=85, w_mm=30, h_mm=30,
        inline_image_data=qr_m_data,
        inline_image_ext=qr_m_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P6 QR-Code (mitmachen)",
    ))
    page1.add(ImageFrame(
        x_mm=246, y_mm=85, w_mm=30, h_mm=30,
        inline_image_data=qr_t_data,
        inline_image_ext=qr_t_ext,
        scale_type=0, ratio=1,
        layer=LAYER_BILDER,
        anname="P6 QR-Code (termine)",
    ))
    # P6 Logo Grüne (Brand-Bund). iter-3: bund-dunkel at 17×15 mm honors
    # the new ~1.13:1 aspect and fits the y=130..145 corner above
    # Impressum (which starts at y=145).
    logo_brand_p6 = HERE.parents[1] / "shared" / "logos" / "gruene-logo-bund-dunkel.png"
    if logo_brand_p6.exists():
        lc6_data, lc6_ext = pack_inline_image(logo_brand_p6.read_bytes(), "png")
        page1.add(ImageFrame(
            x_mm=204, y_mm=130, w_mm=17, h_mm=15,
            inline_image_data=lc6_data, inline_image_ext=lc6_ext,
            scale_type=0, ratio=1,
            layer=LAYER_BILDER,
            anname="P6 Logo Grüne",
        ))
    # Impressum
    page1.add(TextFrame(
        x_mm=204, y_mm=145, w_mm=87, h_mm=60,
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


def build(out_path: str | Path = HERE / "template.sla") -> None:
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

    out_path = Path(out_path)
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

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

from sla_lib.builder import (  # noqa: E402
    Brand,
    Document,
    TextFrame,
    ImageFrame,
    Polygon,
    Run,
    ParaStyle,
    pack_inline_image,
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
def build(out_path: str | Path = HERE / "template.sla") -> None:
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
        linesp=64,
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

    # Logo (top-left) — embedded inline so the SLA stays self-contained
    logo_path = HERE.parents[1] / "shared" / "logos" / "gruene-cmyk.png"
    if logo_path.exists():
        logo_bytes = logo_path.read_bytes()
        data, ext = pack_inline_image(logo_bytes, "png")
        page.add(ImageFrame(
            x_mm=15, y_mm=10, w_mm=60, h_mm=18,
            inline_image_data=data,
            inline_image_ext=ext,
            scale_type=1,  # fit to frame
            ratio=1,
            layer=1,
            anname="Logo Grüne (top-left)",
        ))

    # Headline — These (60 pt Vollkorn Black Italic Dunkelgrün)
    page.add(TextFrame(
        x_mm=15, y_mm=40, w_mm=390, h_mm=50,
        layer=2,
        style="themen-plakat/headline",
        runs=[Run(
            text="Klimaschutz ist Wirtschaftspolitik.",
            paragraph_style="themen-plakat/headline",
        )],
        anname="Headline These",
    ))

    # Sub-Headline (18 pt Gotham Book Dunkelgrün)
    page.add(TextFrame(
        x_mm=15, y_mm=92, w_mm=390, h_mm=16,
        layer=2,
        style="themen-plakat/sub",
        runs=[Run(
            text="Drei Belege aus Niederösterreich, Mai 2026.",
            paragraph_style="themen-plakat/sub",
        )],
        anname="Sub-Headline",
    ))

    # Three evidence columns
    belege = [
        ("12 700 grüne Jobs",
         "In Niederösterreich arbeiten 12 700 Menschen direkt in der "
         "Erneuerbaren-Energie-Branche — mehr als in der konventionellen "
         "Energiewirtschaft.",
         "Beleg 1"),
        ("1.2 Mrd. € Umsatz",
         "Die Solar- und Wind-Branche macht in NÖ 1.2 Mrd. € Jahresumsatz "
         "aus — Tendenz steigend. Jeder Euro fließt in die regionale "
         "Wertschöpfung zurück.",
         "Beleg 2"),
        ("36 % weniger CO₂",
         "Seit 2010 hat NÖ den industriellen CO₂-Ausstoß um 36 % reduziert — "
         "bei gleichzeitig wachsender Industrie-Produktion.",
         "Beleg 3"),
    ]
    for i, (hd, body, label) in enumerate(belege):
        col_x = MARGIN_X_MM + i * (COL_W_MM + GUTTER_MM)
        page.add(TextFrame(
            x_mm=col_x, y_mm=130, w_mm=COL_W_MM, h_mm=20,
            layer=2,
            style="themen-plakat/beleg-headline",
            runs=[Run(text=hd, paragraph_style="themen-plakat/beleg-headline")],
            anname=f"{label} — Headline",
        ))
        page.add(TextFrame(
            x_mm=col_x, y_mm=152, w_mm=COL_W_MM, h_mm=90,
            layer=2,
            style="themen-plakat/beleg-body",
            runs=[Run(text=body, paragraph_style="themen-plakat/beleg-body")],
            anname=f"{label} — Body",
        ))

    # Quelle (bottom-left)
    page.add(TextFrame(
        x_mm=15, y_mm=270, w_mm=280, h_mm=10,
        layer=2,
        style="themen-plakat/source",
        runs=[Run(
            text="Quelle: Statistik Austria, AEA-Energiebilanz NÖ 2024.",
            paragraph_style="themen-plakat/source",
        )],
        anname="Quelle",
    ))

    # Impressum (bottom-right)
    page.add(TextFrame(
        x_mm=305, y_mm=270, w_mm=100, h_mm=10,
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

    out_path = Path(out_path)
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

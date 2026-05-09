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
    # Issue #12 — composites + constraints
    AlignedRow,
    same_y,
    same_x,
    same_style,
    inside,
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

    # Logo (white) top-left on Dunkelgrün front
    # 413x118 px source → 35x10 mm frame (99.2 x 28.3 pt) → scale ≈ 0.24
    logo_weiss_path = HERE.parents[1] / "shared" / "logos" / "gruene-weiss.png"
    if logo_weiss_path.exists():
        lw_data, lw_ext = pack_inline_image(logo_weiss_path.read_bytes(), "png")
        page0.add(ImageFrame(
            x_mm=6, y_mm=6, w_mm=35, h_mm=10,
            inline_image_data=lw_data,
            inline_image_ext=lw_ext,
            scale_type=0, ratio=1,
            local_scale=(0.240, 0.240),
            layer=1,
            anname="Logo Grüne (weiss)",
        ))

    # Wahlkreuz hero centered (D12: must sit on Dunkelgrün — the page bg
    # already provides Dunkelgrün, so we don't need an extra background polygon
    # here; the wahlkreuz PNG has alpha for the area outside the white circle).
    wahlkreuz_x = (TRIM_W_MM - 55) / 2  # 46.5
    wahlkreuz_y = 16
    wahlkreuz_path = HERE.parents[1] / "shared" / "assets" / "wahlkreuz.png"
    if not wahlkreuz_path.exists():
        raise FileNotFoundError(
            f"Wahlkreuz asset not found at {wahlkreuz_path}; "
            f"this template requires shared/assets/wahlkreuz.png (see D1 revised)."
        )
    wahlkreuz_bytes = wahlkreuz_path.read_bytes()
    wk_data, wk_ext = pack_inline_image(wahlkreuz_bytes, "png")
    page0.add(ImageFrame(
        x_mm=wahlkreuz_x, y_mm=wahlkreuz_y, w_mm=55, h_mm=55,
        inline_image_data=wk_data,
        inline_image_ext=wk_ext,
        scale_type=0,
        ratio=1,
        layer=1,
        anname="Wahlkreuz",
    ))

    # Headline below
    page0.add(TextFrame(
        x_mm=10, y_mm=78, w_mm=128, h_mm=20,
        layer=2,
        style="wahlaufruf/headline",
        runs=[Run(
            text="Wähle Grün am 23. Mai",
            paragraph_style="wahlaufruf/headline",
        )],
        anname="Headline-Wahlaufruf",
    ))

    # ---- PAGE 2: Back (2x2 grid + Impressum) ---------------------------
    # White background (no full-page poly needed; default is white)
    # Logo (Brand-Bund) top-left. iter-3: migrated from gruene-cmyk.png
    # wordmark to gruene-logo-bund-dunkel.png. Frame re-sized to 18×16 mm
    # to honor the new ~1.12:1 aspect within the cramped y=6..22 corner
    # (cells start at y=22). On A6 (kurze Kante=105) the Quickguide
    # Print target is 3×M = 18.9 mm — 18 mm sits at 95%. ✓
    logo_brand_path = HERE.parents[1] / "shared" / "logos" / "gruene-logo-bund-dunkel.png"
    if logo_brand_path.exists():
        lc_data, lc_ext = pack_inline_image(logo_brand_path.read_bytes(), "png")
        page1.add(ImageFrame(
            x_mm=6, y_mm=6, w_mm=18, h_mm=16,
            inline_image_data=lc_data,
            inline_image_ext=lc_ext,
            scale_type=0, ratio=1,
            layer=1,
            anname="Logo Grüne (Bund-Dunkel)",
        ))

    # 2x2 grid: 4 cells, each ~70 mm wide, ~39 mm tall, with 2 mm gutter.
    # Cell 4 ("Wo informieren") is narrowed to 35 mm so a QR slot fits to its
    # right (Issue #11 — demo back-side QR encoding the Bezirks-URL).
    cells = [
        (6, 22, "Was wir tun",
         "Klimaschutz, leistbares Wohnen, Bildung — konkret in deiner Gemeinde."),
        (78, 22, "Warum Grün",
         "Mut zur Veränderung. Faktenbasiert. Generationen­gerecht."),
        (6, 62, "Wann gewählt wird",
         "Sonntag, 23. Mai 2026, 7–17 Uhr."),
        (78, 62, "Wo informieren",
         "gruene-noe.at"),
    ]
    # Issue #12 — construct-then-add convention: each cell's hd/bd frame
    # assigned to a named local before page.add. AlignedRow with single
    # child preserves byte-stable interleave order while documenting the
    # row-alignment intent (cells in same row share y).
    cell_idx = 1
    for cx, cy, hd, body in cells:
        if cx == 6:
            cell_w = 68
        elif cell_idx == 4:
            # Cell 4 narrows to 35 mm to make room for QR slot at x=115.
            cell_w = 35
        else:
            cell_w = 64
        cell_hd = TextFrame(
            x_mm=cx, y_mm=cy, w_mm=cell_w, h_mm=8,
            layer=2,
            style="wahlaufruf/cell-headline",
            runs=[Run(text=hd, paragraph_style="wahlaufruf/cell-headline")],
            anname=f"Cell {cell_idx} — Headline",
        )
        cell_bd = TextFrame(
            x_mm=cx, y_mm=cy + 9, w_mm=cell_w, h_mm=30 if cell_idx <= 2 else 20,
            layer=2,
            style="wahlaufruf/cell-body",
            runs=[Run(text=body, paragraph_style="wahlaufruf/cell-body")],
            anname=f"Cell {cell_idx} — Body",
        )
        page1.add(AlignedRow(y_mm=cy, children=[cell_hd],
                              name=f"cell{cell_idx}_hd_row"))
        page1.add(AlignedRow(y_mm=cy + 9, children=[cell_bd],
                              name=f"cell{cell_idx}_bd_row"))
        cell_idx += 1

    # QR-back slot (Issue #11): 25x25 mm, bottom-right of back, conditional
    # inject — only embedded when samples/qr-back.png is committed. Fresh
    # checkouts (no demo content) leave the slot empty.
    qr_back_path = HERE / "samples" / "qr-back.png"
    qr_data, qr_ext = (None, None)
    if qr_back_path.exists():
        qr_data, qr_ext = pack_inline_image(qr_back_path.read_bytes(), "png")
    page1.add(ImageFrame(
        x_mm=115, y_mm=62, w_mm=27, h_mm=27,
        inline_image_data=qr_data,
        inline_image_ext=qr_ext,
        scale_type=0, ratio=1,
        layer=1,
        anname="QR-Code (back)",
    ))

    # Impressum bottom strip
    page1.add(TextFrame(
        x_mm=6, y_mm=96, w_mm=136, h_mm=6,
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
    # Top row of 2x2 grid: cells 1+2 share y=22 (headline) and y=31 (body).
    same_y("Cell 1 — Headline", "Cell 2 — Headline", name="back_row1_hd"),
    same_y("Cell 1 — Body", "Cell 2 — Body", name="back_row1_bd"),
    # Bottom row of 2x2 grid: cells 3+4 share y=62 (headline) and y=71 (body).
    same_y("Cell 3 — Headline", "Cell 4 — Headline", name="back_row2_hd"),
    same_y("Cell 3 — Body", "Cell 4 — Body", name="back_row2_bd"),
    # Left column shared x: cells 1 & 3 left-aligned.
    same_x("Cell 1 — Headline", "Cell 3 — Headline", name="back_col1_x"),
    # Right column shared x: cells 2 & 4 left-aligned at x=78.
    same_x("Cell 2 — Headline", "Cell 4 — Headline", name="back_col2_x"),
    # Style consistency across all 4 cell-headlines and all 4 cell-bodies.
    same_style(
        "Cell 1 — Headline", "Cell 2 — Headline",
        "Cell 3 — Headline", "Cell 4 — Headline",
        name="cell_hd_style_consistent",
    ),
    same_style(
        "Cell 1 — Body", "Cell 2 — Body",
        "Cell 3 — Body", "Cell 4 — Body",
        name="cell_bd_style_consistent",
    ),
]


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")

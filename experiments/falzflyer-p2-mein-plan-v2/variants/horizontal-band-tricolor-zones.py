"""Variant: horizontal-band-tricolor-zones.

Hypothesis: Three full-width horizontal bands structure the P2 body:
Hellgrün top, Dunkelgrün centre, Hellgrün bottom. The centre band is
the optical anchor by two means only: reverse contrast (Weiß on
Dunkelgrün, brand-compliant) and extra height at roughly 1.6x the
neighbour bands. No Gelb accent is used.

Axis commitments: asymmetry, accent-strategy. Transport is expected to
concentrate on the central cornerstone while the flanking bands act as
supporting rhythm rather than equal-priority list items.

Implementation notes:
- Re-emits the scaffold-required production P2 shell.
- Uses only registered brand-safe fonts.
- Keeps all emitted PAGEOBJECTs inside the P2 bounds and prefixes every
  anname with "P2 ".
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


TOP_BOTTOM_PT = 14
CENTER_PT = 36


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/hbands/support",
        font="Gotham Narrow Bold",
        fontsize=TOP_BOTTOM_PT,
        linesp=int(TOP_BOTTOM_PT * 1.2),
        align=1,
        fcolor="Dunkelgrün",
        language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/hbands/cornerstone",
        font="Gotham Narrow Bold",
        fontsize=CENTER_PT,
        linesp=int(CENTER_PT * 1.1),
        align=1,
        fcolor="Weiß",
        language="de",
    ))

    page.add(Polygon(
        x_mm=99, y_mm=-3, w_mm=99, h_mm=31,
        fill="Dunkelgrün", layer=0, anname="P2 Top-Band",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=8, w_mm=87, h_mm=14,
        layer=2, style="falzflyer/top-title",
        runs=[Run(
            text="Mein Plan",
            paragraph_style="falzflyer/top-title",
        )],
        anname="P2 Top-Title",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=38, w_mm=87, h_mm=22,
        layer=2, style="falzflyer/teaser-headline",
        runs=[Run(
            text="Drei klare Zusagen.",
            paragraph_style="falzflyer/teaser-headline",
        )],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    page.add(Polygon(
        x_mm=99, y_mm=72, w_mm=99, h_mm=35,
        fill="Hellgrün", layer=0, anname="P2 Band Top",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=107, w_mm=99, h_mm=56,
        fill="Dunkelgrün", layer=0, anname="P2 Band Center",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=163, w_mm=99, h_mm=35,
        fill="Hellgrün", layer=0, anname="P2 Band Bottom",
    ))

    page.add(TextFrame(
        x_mm=105, y_mm=82, w_mm=87, h_mm=14,
        layer=2, style="exp/hbands/support",
        runs=[Run(
            text="Leistbares Wohnen.",
            paragraph_style="exp/hbands/support",
        )],
        anname="P2 Slogan Top",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=123, w_mm=87, h_mm=24,
        layer=2, style="exp/hbands/cornerstone",
        runs=[Run(
            text="Klimaplan jetzt.",
            paragraph_style="exp/hbands/cornerstone",
        )],
        anname="P2 Slogan Center",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=173, w_mm=87, h_mm=14,
        layer=2, style="exp/hbands/support",
        runs=[Run(
            text="Bildung vor Ort.",
            paragraph_style="exp/hbands/support",
        )],
        anname="P2 Slogan Bottom",
    ))
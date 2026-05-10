"""Variant: ballot-cross-text-container (wildcard).

Hypothesis: Use the Wahlkreuz not as a small brand sign-off but as the
structural text container itself — the pledge occupies the vertical
arm, support lines occupy the horizontal arm. A radically literal,
campaign-object composition that tests whether voters respond to a
symbolic memory structure the team would not normally permit.

Axis commitments: wildcard. The cross-as-container form is the move.
The DSL is axis-aligned, so the Wahlkreuz is realised as a thick "+"
of Dunkelgrün arms on the Hellgrün body. Hellgrün text on Dunkelgrün
arms mirrors the production top-band/top-title pairing (text-on-green
preserved; display contrast threshold applies at 18pt+). The pledge
is split across the upper and lower halves of the vertical arm so the
crossing point reads as the act of voting that confirms the promise.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/cross/pledge",
        font="Vollkorn Black Italic",
        fontsize=24, linesp=28, align=1,
        fcolor="Hellgrün", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/cross/support",
        font="Gotham Narrow Bold",
        fontsize=18, linesp=22, align=1,
        fcolor="Hellgrün", language="de",
    ))

    page.add(Polygon(
        x_mm=99, y_mm=-3, w_mm=99, h_mm=31,
        fill="Dunkelgrün", layer=0, anname="P2 Top-Band",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=8, w_mm=87, h_mm=14,
        layer=2, style="falzflyer/top-title",
        runs=[Run(text="Mein Plan",
                  paragraph_style="falzflyer/top-title")],
        anname="P2 Top-Title",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=38, w_mm=87, h_mm=22,
        layer=2, style="falzflyer/teaser-headline",
        runs=[Run(text="Mein Wahlkreuz.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    # Wahlkreuz arms — Dunkelgrün "+" on the Hellgrün ground.
    # Vertical arm: 36mm wide, 126mm tall, horizontally centred on the panel.
    # Horizontal arm: 87mm wide, 24mm tall, vertically centred in the body.
    page.add(Polygon(
        x_mm=130, y_mm=72, w_mm=36, h_mm=126,
        fill="Dunkelgrün", layer=0, anname="P2 Cross-Arm-Vertical",
    ))
    page.add(Polygon(
        x_mm=105, y_mm=124, w_mm=87, h_mm=24,
        fill="Dunkelgrün", layer=0, anname="P2 Cross-Arm-Horizontal",
    ))

    # Pledge — Hellgrün italic centred in the upper half of the vertical arm.
    page.add(TextFrame(
        x_mm=130, y_mm=82, w_mm=36, h_mm=36,
        layer=2, style="exp/cross/pledge",
        runs=[
            Run(text="Ich",
                paragraph_style="exp/cross/pledge", separator="para"),
            Run(text="stehe.",
                paragraph_style="exp/cross/pledge"),
        ],
        anname="P2 Pledge-Top",
    ))
    # Pledge continues in the lower half of the vertical arm.
    page.add(TextFrame(
        x_mm=130, y_mm=154, w_mm=36, h_mm=36,
        layer=2, style="exp/cross/pledge",
        runs=[
            Run(text="Für",
                paragraph_style="exp/cross/pledge", separator="para"),
            Run(text="Mödling.",
                paragraph_style="exp/cross/pledge"),
        ],
        anname="P2 Pledge-Bottom",
    ))

    # Support lines — Hellgrün bold centred on the horizontal arm.
    page.add(TextFrame(
        x_mm=105, y_mm=130, w_mm=87, h_mm=14,
        layer=2, style="exp/cross/support",
        runs=[Run(text="Klima · Wohnen · Bildung.",
                  paragraph_style="exp/cross/support")],
        anname="P2 Support",
    ))
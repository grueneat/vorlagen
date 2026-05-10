"""Variant: candidate-portrait-overlay-pact.

Hypothesis (wildcard × photographic-vs-typographic): drop the Schlagwort
list entirely. A face_crop ≥60% portrait fills the panel; a single short
commitment phrase sits in a Dunkelgrün rectangular plate anchored to the
lower third. The piece stops being a list of promises and becomes a face
attached to one sentence — directions the team historically resists for
being too personality-driven.

Implementation notes
--------------------
The DSL exposes no image primitive, so the face_crop is represented by a
Magenta polygon stand-in. Magenta is one of the brand_colors_only set
and counts as 1 of the 2 permitted non-green accent colours per piece
(brand Magenta is distinct from the forbidden Linke-magenta).

The face polygon fills x=105..192 (87mm) × y=70..192 (122mm) inside the
body content area (87×130 = 11 310 sq mm) → ≈93.8% fill, well above the
face_crop_fill_pct floor of 60.

The Dunkelgrün commitment plate sits entirely inside the face frame
(x=110..187, y=160..188) — it is fully contained, not partially
overlapping the face-frame edges. The commitment text renders Hellgrün
on Dunkelgrün for text_on_green compliance; type_on_white_plate_forbidden
is honoured (no Weiß plates anywhere).
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/portrait/commitment",
        font="Gotham Narrow Bold",
        fontsize=22, linesp=26, align=0,
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
        runs=[Run(text="Ich stehe für eines.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    # Face crop: photographic stand-in fills the body content area.
    page.add(Polygon(
        x_mm=105, y_mm=70, w_mm=87, h_mm=122,
        fill="Magenta", layer=0, anname="P2 Face-Crop",
    ))

    # Commitment plate fully contained within the face frame, anchored
    # to the lower third (face y-range 70..192; plate y-range 160..188).
    page.add(Polygon(
        x_mm=110, y_mm=160, w_mm=77, h_mm=28,
        fill="Dunkelgrün", layer=0, anname="P2 Commitment-Plate",
    ))
    page.add(TextFrame(
        x_mm=114, y_mm=166, w_mm=69, h_mm=18,
        layer=2, style="exp/portrait/commitment",
        runs=[Run(text="Klimaplan jetzt.",
                  paragraph_style="exp/portrait/commitment")],
        anname="P2 Commitment-Text",
    ))
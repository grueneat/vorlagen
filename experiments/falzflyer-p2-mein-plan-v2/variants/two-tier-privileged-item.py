"""Variant: two-tier-privileged-item.

Hypothesis: Two-tier hierarchy with one privileged cornerstone slogan
on a full-width Dunkelgrün block in Weiß reverse contrast at display
size; three peer slogans below in Dunkelgrün-on-Hellgrün at body
weight. The accent is the brand's text-on-green reverse pairing — not
Gelb — so the move stays inside the envelope.

Axis commitments (per hypothesis): primary=hierarchy,
secondary=accent-strategy. The v1 failure mode this addresses is the
five-even-weight slogans flat layout where the eye lands nowhere:
privileging one cornerstone gives transport at the cost of polarising
appeal (some readers resent the implied ranking — expected).

Size jump: privileged 36pt / peer 14pt = 2.57x, matching the
numbered-priority-list-v2 reference and clearing the 2.5x floor.
"""
from __future__ import annotations

from sla_lib.builder import ParaStyle, Polygon, Run, TextFrame

PRIVILEGED_PT = 36
PEER_PT = 14


def render_p2(doc, page) -> None:
    doc.add_para_style(ParaStyle(
        name="exp/two-tier/privileged",
        font="Gotham Narrow Bold",
        fontsize=PRIVILEGED_PT, linesp=int(PRIVILEGED_PT * 1.1), align=0,
        fcolor="Weiß", language="de",
    ))
    doc.add_para_style(ParaStyle(
        name="exp/two-tier/peer",
        font="Gotham Narrow Book",
        fontsize=PEER_PT, linesp=int(PEER_PT * 1.3), align=0,
        fcolor="Dunkelgrün", language="de",
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
        runs=[Run(text="Eines zuerst.",
                  paragraph_style="falzflyer/teaser-headline")],
        anname="P2 Teaser-Headline",
    ))
    page.add(Polygon(
        x_mm=99, y_mm=28, w_mm=99, h_mm=185,
        fill="Hellgrün", layer=0, anname="P2 Body-Backing",
    ))

    # Privileged cornerstone: full-width Dunkelgrün block, reverse text.
    # Block bleeds to panel edges (x=99, w=99) — full-width is the
    # whole point of the accent strategy.
    page.add(Polygon(
        x_mm=99, y_mm=74, w_mm=99, h_mm=44,
        fill="Dunkelgrün", layer=0, anname="P2 Privileged-Block",
    ))
    page.add(TextFrame(
        x_mm=105, y_mm=84, w_mm=87, h_mm=24,
        layer=2, style="exp/two-tier/privileged",
        runs=[Run(text="Klimaplan jetzt.",
                  paragraph_style="exp/two-tier/privileged")],
        anname="P2 Privileged-Item",
    ))

    # Three peer slogans on Hellgrün at body weight — no rules, the
    # privileged block is the only separator the layout needs.
    peers = [
        "Leistbares Wohnen.",
        "Bildung vor Ort.",
        "Lokale Wirtschaft.",
    ]
    y0 = 134
    row_h = 18
    for i, text in enumerate(peers):
        page.add(TextFrame(
            x_mm=105, y_mm=y0 + i * row_h, w_mm=87, h_mm=14,
            layer=2, style="exp/two-tier/peer",
            runs=[Run(text=text,
                      paragraph_style="exp/two-tier/peer")],
            anname=f"P2 Peer {i+1}",
        ))
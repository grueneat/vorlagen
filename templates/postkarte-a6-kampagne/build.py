#!/usr/bin/env python3
"""Build the canonical Kampagnen-Postkarte A6 (front + back) via the DSL.

Output: templates/postkarte-a6-kampagne/template.sla — opens cleanly in
Scribus, ready for designers to edit.

Two-page document:
  Page 1 (Vorderseite): full-bleed Dunkelgrün bg, Brand-Headline 4-zeilig,
                        Störer-Badge, CTA, Impressum, central logo
  Page 2 (Rückseite):   full-bleed Dunkelgrün bg, sub-headline, body text,
                        QR-Bereich + URL, Social-Handles, Impressum
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document, Color, Polygon, ImageFrame, blocks  # noqa: E402


PAGE_W_MM = 105
PAGE_H_MM = 148
BLEED_MM = 3


def _full_bleed_bg(page, color: str = Color.DUNKELGRUEN) -> None:
    page.add(Polygon(
        x_mm=-BLEED_MM, y_mm=-BLEED_MM,
        w_mm=PAGE_W_MM + 2 * BLEED_MM, h_mm=PAGE_H_MM + 2 * BLEED_MM,
        fill=color, layer=0,
        anname="Hintergrund-Vollfläche (Dunkelgrün, mit Bleed)",
    ))


def build_front(page) -> None:
    _full_bleed_bg(page)

    # Brand 4-line headline, alternating white / yellow Vollkorn
    page.add(blocks.Headline4Line(
        lines=("[Zeile 1 Headline]", "[Zeile 2 Vollkorn]",
               "[Zeile 3 Headline]", "[Zeile 4 Vollkorn]"),
        x_mm=8, y_mm=42, w_mm=89, h_mm=66,
    ))

    # Störer top-right
    page.add(blocks.StoererBadge(
        text=("[Stör 1]", "[Stör 2]", "[Stör 3]"),
        x_mm=72, y_mm=10, diameter_mm=22, rotation_deg=8,
    ))

    # CTA centered under headline
    page.add(blocks.Headline4Line.__bases__[0]) if False else None  # noqa
    # Use a TextFrame via the CTA-style block — implement inline to keep it
    # simple. Could be a future Block.
    from sla_lib.builder import TextFrame, Style
    page.add(TextFrame(
        x_mm=8, y_mm=110, w_mm=89, h_mm=8,
        text="[Call-to-Action eine Zeile]",
        style=Style.CTA, fcolor=Color.WHITE, layer=2,
        anname="CTA",
    ))

    # Logo placeholder (centered, bottom 40mm above edge)
    page.add(ImageFrame(
        x_mm=42, y_mm=120, w_mm=21, h_mm=21,
        src="../../shared/logos/gruene-weiss.png", layer=1,
        anname="Logo Grüne (weiss, zentriert)",
    ))

    # Impressum (1-zeilig, ganz unten in der Bleed-Zone)
    page.add(blocks.ImpressumLine(x_mm=8, y_mm=144, w_mm=89))


def build_back(page) -> None:
    _full_bleed_bg(page)

    # Sub-headline ("Unterüberschrift" Position)
    from sla_lib.builder import TextFrame, Style
    page.add(TextFrame(
        x_mm=10, y_mm=10, w_mm=85, h_mm=8,
        text="[UNTERÜBERSCHRIFT]",
        style=Style.BODY_12, fcolor=Color.WHITE, layer=2,
        anname="Unterüberschrift Rückseite",
    ))

    # Main message (2-line headline)
    page.add(blocks.Headline4Line(
        lines=("[Zeile 1 wichtige]", "[Zeile 2 Aussage]",
               "[Zeile 3 evtl.]", "[Zeile 4 evtl.]"),
        x_mm=8, y_mm=20, w_mm=89, h_mm=46,
    ))

    # Body text
    page.add(TextFrame(
        x_mm=10, y_mm=70, w_mm=85, h_mm=30,
        text=("[Erklärtext zur Kampagne — 5-7 Zeilen Text der die "
              "Hauptbotschaft erklärt und Lesende in Detail aufklärt. "
              "Ersetzt durch eigenen Inhalt im Scribus.]"),
        style=Style.BODY_11, fcolor=Color.WHITE, layer=2,
        anname="Erklärtext Rückseite",
    ))

    # QR placeholder
    page.add(ImageFrame(
        x_mm=38, y_mm=104, w_mm=29, h_mm=29,
        src="qr-placeholder.png", layer=1,
        anname="QR-Code (wird aus URL generiert)",
    ))

    # URL line
    page.add(TextFrame(
        x_mm=10, y_mm=135, w_mm=85, h_mm=4,
        text="https://gruene.at/[kampagne]",
        style=Style.IMPRESSUM, fcolor=Color.GELB, layer=2,
        anname="Kampagnen-URL",
    ))

    # Social handles
    page.add(blocks.SocialHandlesVertical(x_mm=10, y_mm=140, w_mm=45, h_mm=8))

    # Impressum
    page.add(blocks.ImpressumLine(x_mm=55, y_mm=140, w_mm=42))


def build(out_path: Path) -> None:
    doc = Document(
        title="Kampagnen-Postkarte A6",
        template_id="postkarte-a6-kampagne",
    )
    front = doc.add_page(size=(PAGE_W_MM, PAGE_H_MM), orientation="portrait",
                         bleed_mm=BLEED_MM, margins_mm=(8, 8, 8, 8),
                         label="Vorderseite")
    build_front(front)
    back = doc.add_page(size=(PAGE_W_MM, PAGE_H_MM), orientation="portrait",
                        bleed_mm=BLEED_MM, margins_mm=(8, 8, 8, 8),
                        label="Rückseite")
    build_back(back)
    doc.save(out_path)
    print(f"wrote {out_path} ({len(doc.pages)} pages, {len(doc.masters)} masters)")


if __name__ == "__main__":
    build(Path(__file__).parent / "template.sla")

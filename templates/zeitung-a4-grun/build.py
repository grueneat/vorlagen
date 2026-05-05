#!/usr/bin/env python3
"""Build the Grüne Zeitung A4 — multi-page Skelett with master pages and
labeled example pages.

Output: templates/zeitung-a4-grun/template.sla — single SLA file with
N example pages users can duplicate, edit, reorder, and delete.

Master pages (defined in this DSL):
  Normal             — implicit baseline
  rechts-3col        — interior right-hand page, 3-column grid
  links-3col         — interior left-hand page, 3-column grid
  titelseite         — front cover
  foto-spread        — full-bleed photo page
  impressum-master   — back-cover impressum layout

Example pages (each labeled in the Page Panel):
  1. Titelseite (Cover)
  2. Beispiel: Hauptartikel 3-spaltig
  3. Beispiel: Drei kleine Artikel
  4. Beispiel: Foto-Doppelseite (links)
  5. Beispiel: Foto-Doppelseite (rechts)
  6. Beispiel: Veranstaltungskalender
  7. Beispiel: Interview
  8. Beispiel: Kommentar mit Pull-Quote
  9. Impressum + Postvermerk
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import (  # noqa: E402
    Document, Color, Style, TextFrame, ImageFrame, Polygon, blocks,
)


PAGE_W_MM = 210
PAGE_H_MM = 297
BLEED_MM = 3


def define_masters(doc: Document) -> None:
    # Right-hand 3-col master with footer accent
    m_rechts = doc.add_master(name="rechts-3col", size="A4", facing="right")
    m_rechts.add(Polygon(x_mm=185, y_mm=290, w_mm=15, h_mm=4,
                          fill=Color.GELB, layer=0,
                          anname="Footer-Akzent (rechts)"))

    # Left-hand 3-col master
    m_links = doc.add_master(name="links-3col", size="A4", facing="left")
    m_links.add(Polygon(x_mm=10, y_mm=290, w_mm=15, h_mm=4,
                        fill=Color.GELB, layer=0,
                        anname="Footer-Akzent (links)"))

    # Titelseite master (no footer accent)
    doc.add_master(name="titelseite", size="A4")

    # Foto-spread master — empty, items added per-page
    doc.add_master(name="foto-spread", size="A4")

    # Impressum master
    doc.add_master(name="impressum-master", size="A4")


def page_titelseite(doc: Document) -> None:
    p = doc.add_page(size="A4", master="titelseite", label="Titelseite (Cover)")
    # Full bleed dunkelgrün hero area at top
    p.add(Polygon(x_mm=-BLEED_MM, y_mm=-BLEED_MM,
                   w_mm=PAGE_W_MM + 2 * BLEED_MM, h_mm=140,
                   fill=Color.DUNKELGRUEN, layer=0,
                   anname="Hero-Hintergrund (Dunkelgrün)"))
    # Masthead at top
    p.add(blocks.Masthead(zeitungsname="[Zeitungsname]",
                           ausgabe="[Monat / Ausgabe]",
                           x_mm=10, y_mm=15))
    # Big 4-line headline
    p.add(blocks.Headline4Line(
        lines=("[Titel-Headline 1]", "[Vollkorn-Akzent]",
                "[Headline 3]", "[Vollkorn-Schluss]"),
        x_mm=10, y_mm=60, w_mm=190, h_mm=70,
    ))
    # Störer
    p.add(blocks.StoererBadge(
        text=("[Stör 1]", "[Stör 2]", "[Stör 3]"),
        x_mm=160, y_mm=20, diameter_mm=35, rotation_deg=-8,
    ))
    # Content teasers below the hero
    p.add(blocks.ContentTeasers(x_mm=10, y_mm=160, w_mm=190, h_mm=80))
    # Postvermerk at bottom
    p.add(TextFrame(x_mm=10, y_mm=275, w_mm=80, h_mm=4,
                     text="zugestellt durch: ÖSTERREICHISCHE POST AG",
                     style=Style.IMPRESSUM, fcolor=Color.BLACK, layer=2,
                     anname="Postvermerk"))


def page_hauptartikel(doc: Document) -> None:
    p = doc.add_page(size="A4", master="rechts-3col",
                      label="Beispiel: Hauptartikel 3-spaltig")
    p.add(blocks.ArticleHeadline(text="[Hauptartikel-Headline — markant und konkret]",
                                  x_mm=10, y_mm=20, w_mm=190))
    p.add(ImageFrame(x_mm=10, y_mm=45, w_mm=190, h_mm=80,
                      src="", layer=1,
                      anname="Hauptbild des Artikels (optional)"))
    p.add(blocks.ArticleBody(columns=3, x_mm=10, y_mm=130, w_mm=190, h_mm=150))


def page_drei_artikel(doc: Document) -> None:
    p = doc.add_page(size="A4", master="rechts-3col",
                      label="Beispiel: Drei Artikel nebeneinander")
    p.add(TextFrame(x_mm=10, y_mm=15, w_mm=190, h_mm=10,
                     text="[Themenseite — Übersicht]",
                     style=Style.HEADLINE_ULTRA, fcolor=Color.BLACK, layer=2,
                     anname="Seitentitel"))
    p.add(blocks.ContentTeasers(x_mm=10, y_mm=35, w_mm=190, h_mm=240))


def page_foto_spread_links(doc: Document) -> None:
    p = doc.add_page(size="A4", master="foto-spread",
                      label="Beispiel: Foto-Doppelseite (linke Seite)")
    # Full-bleed image area
    p.add(ImageFrame(x_mm=-BLEED_MM, y_mm=-BLEED_MM,
                      w_mm=PAGE_W_MM + 2 * BLEED_MM, h_mm=PAGE_H_MM + 2 * BLEED_MM,
                      src="", layer=1,
                      anname="Foto Vollbild (Bleed-Bereich)"))
    # Caption overlay
    p.add(Polygon(x_mm=10, y_mm=240, w_mm=140, h_mm=40,
                   fill=Color.DUNKELGRUEN, layer=0,
                   anname="Bildunterschrift-Hintergrund"))
    p.add(TextFrame(x_mm=15, y_mm=245, w_mm=130, h_mm=30,
                     text="[Bildunterschrift / Story-Text — Foto-Doppelseiten "
                          "können ein Bild über zwei Seiten erzählen.]",
                     style=Style.BODY_11, fcolor=Color.WHITE, layer=2,
                     anname="Bildunterschrift Foto-Doppelseite"))


def page_foto_spread_rechts(doc: Document) -> None:
    p = doc.add_page(size="A4", master="foto-spread",
                      label="Beispiel: Foto-Doppelseite (rechte Seite)")
    # Continuation of the left-side image — typically same image extends
    p.add(ImageFrame(x_mm=-BLEED_MM, y_mm=-BLEED_MM,
                      w_mm=PAGE_W_MM + 2 * BLEED_MM, h_mm=PAGE_H_MM + 2 * BLEED_MM,
                      src="", layer=1,
                      anname="Foto Vollbild Fortsetzung"))
    p.add(blocks.QuoteSidebar(text="[Großes Zitat — Pull-Quote auf der "
                                    "rechten Seite einer Foto-Doppelseite]",
                                x_mm=20, y_mm=120, w_mm=170, h_mm=60))


def page_veranstaltungen(doc: Document) -> None:
    p = doc.add_page(size="A4", master="rechts-3col",
                      label="Beispiel: Veranstaltungskalender")
    p.add(blocks.ArticleHeadline(text="[Veranstaltungen]", x_mm=10, y_mm=20, w_mm=190))
    # Stub list — 5 veranstaltungs-rows
    for i in range(5):
        y = 50 + i * 35
        p.add(TextFrame(x_mm=10, y_mm=y, w_mm=60, h_mm=8,
                         text=f"[Datum {i+1}] · [Uhrzeit]",
                         style=Style.CTA, fcolor=Color.BLACK, layer=2,
                         anname=f"Veranstaltung {i+1} — Datum"))
        p.add(TextFrame(x_mm=10, y_mm=y + 8, w_mm=120, h_mm=18,
                         text=f"[Veranstaltung {i+1} Titel]\n[Ort, kurze Beschreibung]",
                         style=Style.BODY_11, fcolor=Color.BLACK, layer=2,
                         anname=f"Veranstaltung {i+1} — Details"))


def page_interview(doc: Document) -> None:
    p = doc.add_page(size="A4", master="links-3col",
                      label="Beispiel: Interview-Layout")
    p.add(ImageFrame(x_mm=10, y_mm=20, w_mm=80, h_mm=100,
                      src="", layer=1,
                      anname="Interview — Portrait des/der Interviewten"))
    p.add(TextFrame(x_mm=10, y_mm=125, w_mm=80, h_mm=15,
                     text="[Vorname Nachname]\n[Funktion / Rolle]",
                     style=Style.BODY_11, fcolor=Color.BLACK, layer=2,
                     anname="Interview — Person"))
    # Q&A on the right
    p.add(blocks.ArticleHeadline(
        text="[Interview-Headline — markante Aussage als Frage oder Zitat]",
        x_mm=100, y_mm=20, w_mm=100, h_mm=30))
    p.add(TextFrame(
        x_mm=100, y_mm=55, w_mm=100, h_mm=220,
        text=("[Frage 1?]\n\n[Antwort 1 ausführlich. Lorem ipsum dolor sit "
               "amet, consectetur adipiscing elit.]\n\n[Frage 2?]\n\n"
               "[Antwort 2 ausführlich.]\n\n[Frage 3?]\n\n[Antwort 3.]"),
        style=Style.BODY_11, fcolor=Color.BLACK, layer=2,
        anname="Interview — Q&A Block"))


def page_kommentar(doc: Document) -> None:
    p = doc.add_page(size="A4", master="rechts-3col",
                      label="Beispiel: Kommentar mit Pull-Quote")
    p.add(TextFrame(x_mm=10, y_mm=20, w_mm=80, h_mm=8,
                     text="KOMMENTAR", style=Style.CTA,
                     fcolor=Color.MAGENTA, layer=2,
                     anname="Kommentar-Genremarker"))
    p.add(blocks.ArticleHeadline(text="[Kommentar-Headline — pointiert]",
                                   x_mm=10, y_mm=30, w_mm=190))
    p.add(blocks.QuoteSidebar(text="[Pull-Quote — der zentrale Gedanke "
                                     "in einem Satz, in Vollkorn-Italic]",
                                 x_mm=125, y_mm=70, w_mm=75, h_mm=80))
    p.add(blocks.ArticleBody(columns=2, x_mm=10, y_mm=70, w_mm=110, h_mm=200))
    p.add(TextFrame(x_mm=10, y_mm=275, w_mm=80, h_mm=5,
                     text="von [Autor:in]", style=Style.IMPRESSUM,
                     fcolor=Color.BLACK, layer=2,
                     anname="Autor:innen-Vermerk"))


def page_impressum(doc: Document) -> None:
    p = doc.add_page(size="A4", master="impressum-master",
                      label="Impressum + Postvermerk")
    # Background block for visual anchor
    p.add(Polygon(x_mm=-BLEED_MM, y_mm=180, w_mm=PAGE_W_MM + 2 * BLEED_MM,
                   h_mm=120, fill=Color.DUNKELGRUEN, layer=0,
                   anname="Impressum-Hintergrund (Dunkelgrün)"))
    p.add(blocks.Masthead(zeitungsname="[Zeitungsname — Schluss]",
                            ausgabe="[Ausgabe / Jahrgang]",
                            x_mm=10, y_mm=20))
    p.add(blocks.ImpressumBlock(
        x_mm=10, y_mm=200, w_mm=120, h_mm=70,
        fcolor=Color.WHITE,
    ))
    p.add(blocks.SocialHandlesVertical(
        x_mm=140, y_mm=200, w_mm=60, h_mm=40,
        fcolor=Color.WHITE,
    ))
    p.add(TextFrame(x_mm=140, y_mm=275, w_mm=60, h_mm=10,
                     text="zugestellt durch:\nÖSTERREICHISCHE POST AG",
                     style=Style.IMPRESSUM, fcolor=Color.WHITE, layer=2,
                     anname="Postvermerk"))


def build(out_path: Path) -> None:
    doc = Document(
        title="Grüne Zeitung A4",
        template_id="zeitung-a4-grun",
    )
    define_masters(doc)
    page_titelseite(doc)
    page_hauptartikel(doc)
    page_drei_artikel(doc)
    page_foto_spread_links(doc)
    page_foto_spread_rechts(doc)
    page_veranstaltungen(doc)
    page_interview(doc)
    page_kommentar(doc)
    page_impressum(doc)
    doc.save(out_path)
    print(f"wrote {out_path} ({len(doc.pages)} pages, {len(doc.masters)} masters)")


if __name__ == "__main__":
    build(Path(__file__).parent / "template.sla")

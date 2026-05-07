#!/usr/bin/env python3
"""Smoke: 4-page A4 with 2 masters and per-page labels.
Demonstrates multi-page DSL for the Zeitung use case."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))

from sla_lib.builder import Document, Color, Polygon, blocks  # noqa: E402


def build(out_path: Path) -> None:
    doc = Document(title="Zeitung Mini Smoke", template_id="smoke-zeitung-mini")

    # Master pages with shared elements
    m_artikel = doc.add_master(name="artikel-3col", size="A4")
    m_artikel.add(Polygon(x_mm=185, y_mm=290, w_mm=15, h_mm=4,
                          fill=Color.GELB, layer=0,
                          anname="Master: Footer-Akzent"))

    m_titel = doc.add_master(name="titelseite", size="A4")

    # Page 1 — Titelseite
    p1 = doc.add_page(size="A4", master="titelseite", label="Titelseite")
    p1.add(blocks.legacy.Masthead(zeitungsname="[Zeitungsname]",
                            ausgabe="[Monat / Ausgabe]",
                            x_mm=10, y_mm=15))
    p1.add(blocks.legacy.Headline4Line(
        lines=("[Titel-Headline 1]", "[Vollkorn-Akzent]",
               "[Headline 3]", "[Vollkorn-Schluss]"),
        x_mm=10, y_mm=80, w_mm=190, h_mm=80,
    ))
    p1.add(blocks.legacy.ContentTeasers(x_mm=10, y_mm=180, w_mm=190, h_mm=80))

    # Page 2 — Hauptartikel
    p2 = doc.add_page(size="A4", master="artikel-3col",
                      label="Beispiel: Hauptartikel 3-spaltig")
    p2.add(blocks.legacy.ArticleHeadline(text="[Hauptartikel-Headline]",
                                    x_mm=10, y_mm=20, w_mm=190))
    p2.add(blocks.legacy.ArticleBody(columns=3, x_mm=10, y_mm=50, w_mm=190, h_mm=220))

    # Page 3 — Drei kleinere Artikel
    p3 = doc.add_page(size="A4", master="artikel-3col",
                      label="Beispiel: Drei Artikel nebeneinander")
    p3.add(blocks.legacy.ContentTeasers(x_mm=10, y_mm=20, w_mm=190, h_mm=130))

    # Page 4 — Impressum
    p4 = doc.add_page(size="A4", master="artikel-3col",
                      label="Impressum + Postvermerk")
    p4.add(blocks.legacy.ImpressumBlock(x_mm=10, y_mm=240, w_mm=80, h_mm=40,
                                  fcolor=Color.WHITE))

    doc.save(out_path)
    print(f"wrote {out_path} ({len(doc.pages)} pages, {len(doc.masters)} masters)")


if __name__ == "__main__":
    build(Path(__file__).parent / "template.sla")

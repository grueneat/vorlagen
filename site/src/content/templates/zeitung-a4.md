---
id: zeitung-a4
version: 0.1.0
build_py_sha256: 5bfe1f8316ba2d05782eb3937d5475c2841f3e339de7ceeb333ca95c9736ac08
title: Grüne Zeitung A4
format: A4
orientation: portrait
pages: 9
audience:
- bezirksgruppe
- landesgruppe
description: Mehrseitige Zeitung im A4-Format für lokale Berichterstattung und Themenvielfalt.
build:
  script: build.py
  output: template.sla
original_sla: ../../gruene-zeitung-vorlage-original.sla
previews_for_sla: e12438734f8234d8220f6caf37c2c03a10d29a478477ebe6a9029e33f8fcbc00
sla_diff_strict: false
text_render_strict: false
brand_overrides:
- id: brand:line_spacing_0.9
  reason: Production template auto-generated from gruene-zeitung-vorlage-original
    .sla; multiple per-template para-styles drift from Quickguide 0.9 factor (e.g.
    Titelseite Header 46/55=0.84, Bildunterschrift weiß 12/10=1.2x). The Zeitung uses
    journalism conventions (tighter headline leading, looser caption leading) that
    differ from the unified-Quickguide rule. Round- trip diff is the byte-stable contract.
- id: brand:image_text_overlap
  reason: 'Caption-on-photo intentional design pattern: several text frames (page-1
    cover headline u2989 over u2950 band, page-3/page-7 caption text inside u6ad/Kopie-von-u6ad
    polygons, page-14 captions on P13 Hero) extend slightly beyond their containing
    colored polygons. The page-10 Polygon `Kopie von u1529` overlap with text columns
    `Kopie von u2d5c (13)`/`(16)` was the documented bug — FIXED in Issue #23 T07
    by shrinking the columns'' h_mm to end above the green card. Remaining 9 cases
    are caption-on-photo design intent; tightening text frames to match polygon edges
    exactly would change the visual layout. Out of scope for #23; revisit per follow-up
    audit.'
- id: brand:inside_page
  reason: 'Zeitung geometry was reset to the original InDesign SLA — the #40/#42/#45/#48/#51
    alignment "fixes" had wrongly pulled full-bleed and cross-page spread images page-local.
    The original layout (confirmed correct) places hero/spread images (P9 Spread,
    P1/P13 Hero, the page-13 full-page tile, the u2950 cover polygon) so they extend
    across the spread and into the adjacent page''s bleed. The inside_page rule models
    single-page frames and cannot represent an intentional cross-page newspaper spread.'
- id: brand:bleed_coverage
  reason: Same reset as brand:inside_page. The bleed_coverage rule expects each frame's
    outer edge to land on its own page's bleed line; the zeitung cover/hero/spread
    frames span both pages of a spread, so a single frame's outer edge legitimately
    sits at the far page edge rather than at -3mm. The original InDesign SLA layout
    is the convergence target.
- id: brand:band_consistency
  reason: Same reset as brand:inside_page. The original newspaper layout runs full-bleed
    hero/spread photos (Cover Hero, P1/P13 Hero, P4 Foto-Spread, P9 Spread) that cross
    the header/free/footer band boundaries by design, plus editorial photo/caption
    frames that sit a few mm outside the body-margin spec. band_consistency models
    a single-column body pool and cannot represent a 14-page newspaper's editorial
    grid.
body_block_margins:
  bands:
    header:
      y_top_mm: 20.0
      y_bottom_mm: 49.0
    footer:
      y_top_mm: 283.0
      y_bottom_mm: 297.0
  margins:
    left:
      outer_mm: 20.0
      inner_mm: 20.0
    right:
      outer_mm: 20.0
      inner_mm: 20.0
  background_decoration:
    fills:
    - Dunkelgrün
    - Hellgrün
    - Magenta
    - Gelb
    - White
ci_overrides:
  non_ci_styles:
  - Default Paragraph Style
  - '[No paragraph style]'
  - Titelseite Header
  - Monat/Ausgabe
  - Zustellerhinweis (Post)
  - Impressum
  - Copyright
  - Seitenzahl
  - Fließtext
  - Schrift Störer
  - Inhaltsheadline Titelseite
  - Überschrift weiß
  - Überschrift Dunkelgrün
  - Bildunterschrift weiß
  - Fließtext weiß
  - Fließtext in grünem Kasten
  - Headline in grünem Kasten
  - Zwischenüberschrift
  - Einleitungstext
  - Zwischenüberschrift weiß
  - Zitat weißer Text
  - Zitat grüner Text
  - NormalParagraphStyle
  non_ci_colors:
  - Green
masters:
- name: Normal
  description: implicit baseline
- name: rechts-3col
  description: rechte Innenseite mit 3-Spalten-Raster und Footer-Akzent
- name: links-3col
  description: linke Innenseite mit 3-Spalten-Raster und Footer-Akzent
- name: titelseite
  description: Cover-Layout mit Hero-Bereich
- name: foto-spread
  description: Vollbild-Fotoseite
- name: impressum-master
  description: Rückseite mit Impressum-Block
example_pages:
- num: 1
  label: Titelseite (Cover)
- num: 2
  label: 'Beispiel: Hauptartikel 3-spaltig'
- num: 3
  label: 'Beispiel: Drei Artikel nebeneinander'
- num: 4
  label: 'Beispiel: Foto-Doppelseite (links)'
- num: 5
  label: 'Beispiel: Foto-Doppelseite (rechts)'
- num: 6
  label: 'Beispiel: Veranstaltungskalender'
- num: 7
  label: 'Beispiel: Interview-Layout'
- num: 8
  label: 'Beispiel: Kommentar mit Pull-Quote'
- num: 9
  label: Impressum + Postvermerk
preflight:
  bleed_mm: 3
  cmyk_only: true
  min_image_dpi: 300
category: zeitung
category_label: Zeitung
variant_label: A4 mehrseitig
_downloads:
- label: Burgenland
  bundesland: bgld
  sla: /templates/zeitung-a4/impressum/bgld.sla
- label: Kärnten
  bundesland: ktn
  sla: /templates/zeitung-a4/impressum/ktn.sla
- label: Niederösterreich
  bundesland: noe
  sla: /templates/zeitung-a4/impressum/noe.sla
- label: Oberösterreich
  bundesland: ooe
  sla: /templates/zeitung-a4/impressum/ooe.sla
- label: Salzburg
  bundesland: sbg
  sla: /templates/zeitung-a4/impressum/sbg.sla
- label: Steiermark
  bundesland: stmk
  sla: /templates/zeitung-a4/impressum/stmk.sla
- label: Tirol
  bundesland: tirol
  sla: /templates/zeitung-a4/impressum/tirol.sla
- label: Vorarlberg
  bundesland: vbg
  sla: /templates/zeitung-a4/impressum/vbg.sla
- label: Wien
  bundesland: wien
  sla: /templates/zeitung-a4/impressum/wien.sla
_preview_pdf: /templates/zeitung-a4/preview.pdf
_previews:
- label: Seite 1
  src: /templates/zeitung-a4/page-01.png
- label: Seite 2
  src: /templates/zeitung-a4/page-02.png
- label: Seite 3
  src: /templates/zeitung-a4/page-03.png
- label: Seite 4
  src: /templates/zeitung-a4/page-04.png
- label: Seite 5
  src: /templates/zeitung-a4/page-05.png
- label: Seite 6
  src: /templates/zeitung-a4/page-06.png
- label: Seite 7
  src: /templates/zeitung-a4/page-07.png
- label: Seite 8
  src: /templates/zeitung-a4/page-08.png
- label: Seite 9
  src: /templates/zeitung-a4/page-09.png
- label: Seite 10
  src: /templates/zeitung-a4/page-10.png
- label: Seite 11
  src: /templates/zeitung-a4/page-11.png
- label: Seite 12
  src: /templates/zeitung-a4/page-12.png
- label: Seite 13
  src: /templates/zeitung-a4/page-13.png
- label: Seite 14
  src: /templates/zeitung-a4/page-14.png
---

# So nutzt du die Zeitungs-Vorlage

Die Vorlage ist eine mehrseitige A4-Zeitung mit fertigen Beispielseiten für
alle typischen Layouts — Titelseite, Artikel, Foto-Doppelseite, Interview,
Veranstaltungskalender, Impressum. Du baust deine Ausgabe, indem du die
passenden Beispielseiten übernimmst und die Inhalte ersetzt.

## Schritt für Schritt

1. **Vorlage öffnen** — `template.sla` mit [Scribus](https://www.scribus.net)
   öffnen (kostenlos für Windows, macOS und Linux). Die oben verlinkten
   Schriften vorher installieren.
2. **Beispielseiten ansehen** — im Seitenbedienpanel (*Fenster →
   Seitenbedienpanel*) trägt jede Beispielseite oben eine pinke Beschriftung,
   z. B. „Beispiel: Hauptartikel 3-spaltig". So erkennst du, welche Seite welches
   Layout zeigt.
3. **Seiten übernehmen** — die Beispielseiten, die du brauchst, im
   Seitenbedienpanel duplizieren (Rechtsklick → *Seite kopieren*) und an die
   gewünschte Position einfügen. Nicht benötigte Seiten löschen.
4. **Inhalte ersetzen** — Texte überschreiben, Fotos austauschen. Klick auf
   einen Rahmen zeigt unten rechts seinen Namen (z. B. „Headline 4-zeilig" oder
   „Bildunterschrift") — so findest du, was wofür gedacht ist.
5. **Reihenfolge anpassen** — Seiten per Drag-and-Drop im Seitenbedienpanel
   sortieren.
6. **Pinke Hinweise entfernen** — die Beispielseiten-Beschriftungen liegen auf
   dem Layer „Hilfslinien" und werden im PDF ohnehin nicht gedruckt; wer mag,
   blendet den Layer aus oder löscht die Hinweise.
7. **Impressum prüfen** — der Impressums-Block ist gesetzlich vorgeschrieben.
   Angaben ergänzen, nicht löschen.
8. **Als PDF exportieren** — *Datei → Exportieren → Als PDF speichern*. Fertig
   für die Druckerei.

## Verfügbare Beispielseiten

1. **Titelseite** — Hero-Headline, Masthead, Störer, Inhalts-Teaser
2. **Hauptartikel 3-spaltig** — großer Artikel mit Bild und 3-Spalten-Text
3. **Drei kleine Artikel** — Themenseite mit drei Teasern nebeneinander
4. **Foto-Doppelseite (links)** — Vollbild-Foto mit Bildunterschrift
5. **Foto-Doppelseite (rechts)** — Fortsetzung mit Pull-Quote
6. **Veranstaltungskalender** — Liste von Events mit Datum und Ort
7. **Interview-Layout** — Porträt plus Frage-Antwort-Block
8. **Kommentar mit Pull-Quote** — zweispaltig mit hervorgehobenem Zitat
9. **Impressum + Postvermerk** — Rückseite

## Eigene Seiten anlegen

Brauchst du eine leere Seite in einem bestimmten Raster, kannst du beim Anlegen
einer Seite eine Musterseite (*Bearbeiten → Musterseiten*) wählen:

| Musterseite | Verwendung |
|---|---|
| `titelseite` | Cover-Layout mit Hero-Bereich oben |
| `rechts-3col` | rechte Innenseite, 3-Spalten-Raster |
| `links-3col` | linke Innenseite, 3-Spalten-Raster |
| `foto-spread` | Vollbild-Fotoseite |
| `impressum-master` | Rückseite mit Impressum-Bereich |

Musterseite zuweisen: im Seitenbedienpanel Rechtsklick auf die Seite →
*Musterseite anwenden*.

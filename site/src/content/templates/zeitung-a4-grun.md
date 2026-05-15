---
id: zeitung-a4-grun
version: 0.1.0
title: Grüne Zeitung A4
format: A4
orientation: portrait
pages: 9
audience:
- bezirksgruppe
- landesgruppe
description: 'Mehrseitige A4-Zeitungsvorlage mit Master-Pages und Beispielseiten.
  Eine Datei mit allen typischen Layout-Optionen — Bezirks- und Landesgruppen duplizieren
  die gewünschten Beispielseiten, passen Inhalte an und löschen ungenutzte Beispiele.

  '
build:
  script: build.py
  output: template.sla
original_sla: ../../gruene-zeitung-vorlage-original.sla
previews_for_sla: b008d0d0bd6eb51d513f59496311c17068c9a1490cd69188d3f947a5d8f57096
sla_diff_strict: false
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
variant_label: A4 grün
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/zeitung-a4-grun/template.sla
  pdf: /templates/zeitung-a4-grun/preview.pdf
_previews:
- label: Seite 1
  src: /templates/zeitung-a4-grun/page-01.png
- label: Seite 2
  src: /templates/zeitung-a4-grun/page-02.png
- label: Seite 3
  src: /templates/zeitung-a4-grun/page-03.png
- label: Seite 4
  src: /templates/zeitung-a4-grun/page-04.png
- label: Seite 5
  src: /templates/zeitung-a4-grun/page-05.png
- label: Seite 6
  src: /templates/zeitung-a4-grun/page-06.png
- label: Seite 7
  src: /templates/zeitung-a4-grun/page-07.png
- label: Seite 8
  src: /templates/zeitung-a4-grun/page-08.png
- label: Seite 9
  src: /templates/zeitung-a4-grun/page-09.png
- label: Seite 10
  src: /templates/zeitung-a4-grun/page-10.png
- label: Seite 11
  src: /templates/zeitung-a4-grun/page-11.png
- label: Seite 12
  src: /templates/zeitung-a4-grun/page-12.png
- label: Seite 13
  src: /templates/zeitung-a4-grun/page-13.png
- label: Seite 14
  src: /templates/zeitung-a4-grun/page-14.png
---

# Grüne Zeitung A4 — Skelett-Vorlage

Mehrseitige Zeitungsvorlage mit allen typischen Layout-Varianten in **einer einzigen SLA-Datei**.

## So nutzt du die Vorlage

1. `template.sla` in Scribus öffnen.
2. Im **Page-Panel** (Fenster → Seitenbedienpanel) siehst du eine pinke Beschriftung pro Beispielseite — z.B. "BEISPIELSEITE — Beispiel: Hauptartikel 3-spaltig" am oberen Seitenrand.
3. **Beispielseite duplizieren** (Rechtsklick im Page-Panel → "Seite kopieren" → an gewünschter Position einfügen).
4. **Inhalte ersetzen** — die Frames sind beschriftet (Object Properties → ANNAME), z.B. "Headline 4-zeilig (Brand-Wechselfarbe)" oder "Bildunterschrift Foto-Doppelseite". Klick auf einen Frame zeigt seinen Namen rechts unten.
5. **Beispielseite-Beschriftungen löschen** — die pinken Hinweise oben (Layer "Hilfslinien") werden im PDF-Export sowieso nicht gedruckt; wer mag, blendet den Layer aus oder löscht die Frames.
6. **Nicht benötigte Beispielseiten löschen** — wenn du nur 4 Seiten brauchst, wirf die anderen weg.
7. Reihenfolge per Drag-and-Drop im Page-Panel anpassen.

## Master-Pages

Über **Bearbeiten → Musterseiten** sind diese verfügbar:

| Name | Verwendung |
|---|---|
| `Normal` | Default — leere Seite |
| `rechts-3col` | Rechte Innenseite mit 3-Spalten-Raster |
| `links-3col` | Linke Innenseite mit 3-Spalten-Raster |
| `titelseite` | Cover-Layout (Hero-Bereich oben) |
| `foto-spread` | Vollbild-Fotoseite ohne Hilfsraster |
| `impressum-master` | Rückseite mit großzügigem Impressum-Bereich |

Master per Page-Panel auf Seiten anwenden: Rechtsklick auf Seite → "Musterseite anwenden".

## Beispielseiten in dieser Vorlage

1. **Titelseite (Cover)** — Hero-Headline, Masthead, Störer, Inhalts-Teaser
2. **Hauptartikel 3-spaltig** — Großer Artikel mit Bild und 3-Spalten-Body
3. **Drei kleine Artikel** — Themenseite mit drei nebeneinanderstehenden Teasern
4. **Foto-Doppelseite (links)** — Vollbild-Foto mit Bildunterschrift-Block
5. **Foto-Doppelseite (rechts)** — Fortsetzung mit Pull-Quote
6. **Veranstaltungskalender** — Liste von 5 Events mit Datum/Ort
7. **Interview-Layout** — Portrait + Q&A-Block
8. **Kommentar mit Pull-Quote** — Genre-Markup, Pull-Quote, 2-Spalten-Body
9. **Impressum + Postvermerk** — Rückseite

## Vorlagen-Generierung (für Maintainer:innen)

`template.sla` wird aus `build.py` über die DSL erzeugt:

```bash
python3 templates/zeitung-a4-grun/build.py
```

Wer das Layout strukturell ändern will (z.B. neue Beispielseite, Master-Page-Anpassung) editiert `build.py` und re-generiert. Wer nur Inhalte ändert oder eine konkrete Ausgabe baut, arbeitet direkt in Scribus an der `template.sla`.

## Bekannte Abweichungen vom Original-SLA

`gruene-zeitung-vorlage-original.sla` enthält zwei Bildrahmen, die der
Scribus-Autor versehentlich um 210 mm nach rechts (auf den Off-Page-
Scratch-Canvas) plaziert hat — sie rendern im Original-PDF nichts
Sichtbares (verifiziert via `pdfimages -list`):

- `P9 Spread` (build.py:1802, war `x_mm=210` auf `page9`) → korrigiert
  auf `x_mm=0` auf derselben Seite. `anname` bleibt erhalten, damit
  `INJECT_MAP` und `CONSTRAINTS` weiter aufgelöst werden. Issue #16.
- Unbenannter Vollseiten-Dunkelgrün-Rahmen (build.py:2061, war
  `page11.add(...)` mit `x_mm=210`) → verschoben zu `page12.add(...)`
  mit `x_mm=0` (gedruckte Seite 13, dem ursprünglich gemeinten Ziel).
  Issue #16.

Daher weicht `template.sla` an diesen zwei Stellen bewusst vom
Original-SLA ab. Der Round-Trip-Check `tools/sla_diff.py --strict`
ist für diese Vorlage entsprechend deaktiviert
(`meta.yml::sla_diff_strict: false`); `tools/render_pipeline.py`
überspringt den Strict-Diff für Templates mit diesem Flag.

Eine dritte, davon unabhängige Überfüllung — der gedrehte
Cover-Polygon `u2950` (build.py:246-256, ~4.17 mm Bottom-Overshoot) —
bleibt vorerst durch den `brand_overrides[brand:inside_page]`-Eintrag
abgedeckt und wird in GH #39 separat behoben.

## Brand

Alle Farben und Schriften referenzieren `shared/ci.yml`. Direkt-Edits an Stilen in der SLA werden vom CI-Validator (`tools/check_ci.py`) als Drift gemeldet.

## LANGUAGE-Vererbung auf STYLE-Ebene

Die ursprüngliche Zeitungsvorlage setzt `LANGUAGE="de"` nur auf 13 von 23 Paragraphenstilen. Die anderen 10 Stile (z.B. `Fließtext`, `Fließtext weiß`, `Fließtext in grünem Kasten`) erben über `PARENT` oder verlassen sich auf den Dokument-Default (DEFLANG="de"). Der DSL-Konverter (`tools/sla_to_dsl.py`) übernimmt dieses Muster verbatim — `ParaStyle.language` ist `None` für die 10 Stile, die das Original nicht setzt.

Die Hyphenation in den `Fließtext*`-Spalten (vgl. Seite 3/4 der gerenderten PDF) ist im DSL-Output identisch mit der Originalvorlage; das Auslassen von `LANGUAGE` führt nicht zu Drift, weil der Default greift. Sollte sich das in einem zukünftigen Scribus-Upgrade ändern, muss der Konverter auf "alle 23 Stile auf `language='de'` setzen" umgestellt werden.

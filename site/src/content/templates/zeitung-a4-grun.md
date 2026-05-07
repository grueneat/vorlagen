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
previews_for_sla: f8d1744d980925e9034469d59ec4e9f1a7ed4c5e788d451e071356f9f364e8a4
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

## Brand

Alle Farben und Schriften referenzieren `shared/ci.yml`. Direkt-Edits an Stilen in der SLA werden vom CI-Validator (`tools/check_ci.py`) als Drift gemeldet.

## LANGUAGE-Vererbung auf STYLE-Ebene

Die ursprüngliche Zeitungsvorlage setzt `LANGUAGE="de"` nur auf 13 von 23 Paragraphenstilen. Die anderen 10 Stile (z.B. `Fließtext`, `Fließtext weiß`, `Fließtext in grünem Kasten`) erben über `PARENT` oder verlassen sich auf den Dokument-Default (DEFLANG="de"). Der DSL-Konverter (`tools/sla_to_dsl.py`) übernimmt dieses Muster verbatim — `ParaStyle.language` ist `None` für die 10 Stile, die das Original nicht setzt.

Die Hyphenation in den `Fließtext*`-Spalten (vgl. Seite 3/4 der gerenderten PDF) ist im DSL-Output identisch mit der Originalvorlage; das Auslassen von `LANGUAGE` führt nicht zu Drift, weil der Default greift. Sollte sich das in einem zukünftigen Scribus-Upgrade ändern, muss der Konverter auf "alle 23 Stile auf `language='de'` setzen" umgestellt werden.

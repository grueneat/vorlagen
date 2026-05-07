---
id: themen-plakat-a3-quer
version: 0.1.0
title: Themen-Plakat A3 quer
format: A3
orientation: landscape
pages: 1
preview_dpi: 100
audience:
- bezirksgruppe
- landesgruppe
- ortsgruppe
description: 'Argumentations-Plakat A3 quer (420×297 mm) für sachthemen-orientierte
  Aufhänge in Gemeindeämtern, Lokalen und auf Infotafeln. Layout: Hauptthese span
  volle Breite, 3-Spalten-Belege darunter, Quelle + Impressum unten.

  '
build:
  script: build.py
  output: template.sla
previews_for_sla: cf1eeefd7dbf7b2dacfbd85720f3c02f90fa11daf696c9ba4627258a7a9ddeba
ci_overrides:
  non_ci_styles:
  - themen-plakat/headline
  - themen-plakat/sub
  - themen-plakat/beleg-headline
  - themen-plakat/beleg-body
  - themen-plakat/source
  - themen-plakat/impressum
  non_ci_colors: []
slots:
  headline_thesis:
    type: text
    description: 1-zeilige Hauptthese (Argumentations-Anker)
    anname: Headline These
  subheadline:
    type: text
    description: Sub-Headline mit Kontext (Region, Datum)
    anname: Sub-Headline
  evidence_1_headline:
    type: text
    description: Beleg 1 — kurzer Kennzahl-Anker
    anname: Beleg 1 — Headline
  evidence_1_body:
    type: text
    description: Beleg 1 — 3-5 Sätze Kontext
    anname: Beleg 1 — Body
  evidence_2_headline:
    type: text
    anname: Beleg 2 — Headline
  evidence_2_body:
    type: text
    anname: Beleg 2 — Body
  evidence_3_headline:
    type: text
    anname: Beleg 3 — Headline
  evidence_3_body:
    type: text
    anname: Beleg 3 — Body
  quelle:
    type: text
    description: Quelle/Source-Citation (klein, unten links)
    anname: Quelle
  impressum:
    type: text
    description: Mediengesetz §24 Impressum (unten rechts)
    anname: Impressum
  logo_grueneAT:
    type: image
    description: Grünen-Logo (top-left)
    source: shared/logos/gruene-cmyk.png
    optional: true
    anname: Logo Grüne (top-left)
example_pages:
- num: 1
  label: Themen-Plakat A3 quer (Vorderseite)
preflight:
  bleed_mm: 3
  cmyk_only: true
  min_image_dpi: 300
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/themen-plakat-a3-quer/template.sla
  pdf: /templates/themen-plakat-a3-quer/preview.pdf
_previews:
- label: Seite 1
  src: /templates/themen-plakat-a3-quer/page-01.png
---

# Themen-Plakat A3 quer

Argumentations-Plakat A3 quer (420 × 297 mm) für Sachthemen-Aufhänge in
Gemeindeämtern, Lokalen und auf Infotafeln.

## Wann verwenden?

- Sachthema außerhalb des Wahlkampfs (z.B. „Klimaschutz ist Wirtschaftspolitik",
  „Was unsere Heizungsförderung leistet").
- Lese-Distanz ~50 cm – 1.5 m.
- Soll überzeugen, nicht aufrufen — daher kein Wahlkreuz, kein Stoerer.

## Was anpassen?

In Scribus öffnen → die folgenden Frame-Annames anklicken und Text/Bild
ersetzen:

| Anname | Inhalt |
|---|---|
| `Headline These` | Hauptthese, 1 Zeile |
| `Sub-Headline` | Kontext: Region + Datum |
| `Beleg 1 / 2 / 3 — Headline` | Kennzahl-Anker je Spalte |
| `Beleg 1 / 2 / 3 — Body` | 3–5 Sätze Begründung |
| `Quelle` | Wissenschaftliche / behördliche Quelle |
| `Impressum` | Mediengesetz-§24-Block |
| `Logo Grüne (top-left)` | (optional) Logo, sonst leer |

Spec: [`templates/_specs/themen-plakat-a3-quer.md`](../_specs/themen-plakat-a3-quer.md).

## Build

```bash
python3 templates/themen-plakat-a3-quer/build.py
# → templates/themen-plakat-a3-quer/template.sla
```

## Druck-Empfehlung

- **Bleed:** 3 mm allseitig
- **Papier:** Bilderdruck matt 170 g/m² oder Plakatpapier blueback 135 g/m²
- **Druck:** Offset (≥ 100 Stück) oder Großformat-Digital (< 100)
- **DPI:** 300 für eingebettete Bilder
- **CMYK only**, ICC-Profil PSO Uncoated ISO12647 (ECI)

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.
Inhalte (Texte, Belege, Quellen) sind Verantwortung der Endnutzer:innen.

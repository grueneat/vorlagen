---
id: plakat-a1-hochformat
version: 0.1.0
title: Event-Plakat (Familie)
type: family
audience:
- bezirksgruppe
- landesgruppe
- ortsgruppe
description: 'Veranstaltungs-Plakat für Events, Mahnwachen, Stammtische, Kundgebungen.
  Verfügbar als A0, A1, A2, A3 — gleiche Gestaltung, skaliert für die jeweilige Größe.
  Eine build.py-Definition erzeugt alle vier SLAs.

  '
build:
  script: build.py
  output: template.sla
  outputs:
  - a0.sla
  - a1.sla
  - a2.sla
  - a3.sla
original_sla: ../../plakat-a1-hochformat-original.sla
ci_overrides:
  non_ci_styles:
  - Default Paragraph Style
  - Headlineweiß
  - Überschrift gelb
  - Fließtext
  - Impressum
  non_ci_colors: []
sizes:
- code: a0
  format: A0
  mm:
  - 841
  - 1189
- code: a1
  format: A1
  mm:
  - 594
  - 841
- code: a2
  format: A2
  mm:
  - 420
  - 594
- code: a3
  format: A3
  mm:
  - 297
  - 420
slots:
  headline:
    type: text
    description: 4-zeilige Event-Headline (alternierend Weiß/Gelb)
    lines: 4
    anname: Headline 4-zeilig (Brand-Wechselfarbe)
  date:
    type: text
    description: Datum (z.B. "Samstag, 15. Mai")
    anname: Veranstaltung — Datum/Zeit
  venue:
    type: text
    description: Veranstaltungsort + Adresse
    anname: Veranstaltung — Ort/Adresse
  url:
    type: text
    description: Anmelde- oder Info-URL
    pattern: ^(https?://)?[a-z0-9.-]+
    anname: Anmelde-URL
  logo:
    type: image
    description: Grünen-Logo (rechts oben)
    source: shared/logos/gruene-weiss.png
    anname: Logo (top-right, weiss)
  impressum:
    type: text
    description: Impressum (vertikal am rechten Rand)
    anname: Impressum (vertikal)
preflight:
  bleed_mm: 3
  cmyk_only: true
_downloads:
- label: A0 (841×1189mm)
  sla: /templates/plakat-a1-hochformat/a0.sla
  pdf: /templates/plakat-a1-hochformat/a0.pdf
- label: A1 (594×841mm)
  sla: /templates/plakat-a1-hochformat/a1.sla
  pdf: /templates/plakat-a1-hochformat/a1.pdf
- label: A2 (420×594mm)
  sla: /templates/plakat-a1-hochformat/a2.sla
  pdf: /templates/plakat-a1-hochformat/a2.pdf
- label: A3 (297×420mm)
  sla: /templates/plakat-a1-hochformat/a3.sla
  pdf: /templates/plakat-a1-hochformat/a3.pdf
_previews:
- label: A0
  src: /templates/plakat-a1-hochformat/a0-page-1.png
- label: A1
  src: /templates/plakat-a1-hochformat/a1-page-1.png
- label: A2
  src: /templates/plakat-a1-hochformat/a2-page-1.png
- label: A3
  src: /templates/plakat-a1-hochformat/a3-page-1.png
---

# Event-Plakat (A0/A1/A2/A3 Familie)

Vier SLA-Dateien aus einer DSL-Definition — gleicher Entwurf, vier Größen.

## So nutzt du die Vorlage

1. Größe wählen: a0.sla / a1.sla / a2.sla / a3.sla.
2. In Scribus öffnen.
3. Inhalte ersetzen — Headline, Datum, Ort, URL.
4. Logo platzieren (Bilder-Frame oben rechts, ANNAME "Logo (top-right, weiss)").
5. PDF exportieren.

## Wann welche Größe?

| Größe | Verwendung |
|---|---|
| A0 (84 × 119 cm) | City-Lights, Großflächen, Litfaßsäulen |
| A1 (59 × 84 cm)  | Schaufenster, Anschlagsäulen |
| A2 (42 × 59 cm)  | Veranstaltungsorte innen, Eingänge |
| A3 (30 × 42 cm)  | Aushangtafeln, Lokale, Café |

## Anpassung der Vorlage

`build.py` definiert Layout für alle vier Größen. Editieren + `python3 build.py` regeneriert alle.

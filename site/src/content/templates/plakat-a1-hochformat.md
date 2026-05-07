---
id: plakat-a1-hochformat
version: 0.1.0
title: Event-Plakat A1
type: single
audience:
- bezirksgruppe
- landesgruppe
- ortsgruppe
description: 'Veranstaltungs-Plakat für Events, Mahnwachen, Stammtische, Kundgebungen.
  A1 Hochformat (594×841 mm). Für andere Druckgrößen direkt im Druckdialog skalieren
  — die Vektor-Inhalte bleiben dabei verlustfrei.

  '
build:
  script: build.py
  output: template.sla
original_sla: ../../plakat-a1-hochformat-original.sla
previews_for_sla: 5c9a04ed876a8bdfad9ed7bb1851fbe4e39fd6119db1469f18b06f1c07bad48c
ci_overrides:
  non_ci_styles:
  - Default Paragraph Style
  - Headlineweiß
  - Überschrift gelb
  - Fließtext
  - Impressum
  non_ci_colors: []
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
- label: Vollständig (SLA + PDF)
  sla: /templates/plakat-a1-hochformat/template.sla
  pdf: /templates/plakat-a1-hochformat/preview.pdf
_previews:
- label: Seite 1
  src: /templates/plakat-a1-hochformat/page-01.png
---

# Event-Plakat A1

A1 Hochformat (594 × 841 mm) — DSL-built reproduction of `plakat-a1-hochformat-original.sla`.

## So nutzt du die Vorlage

1. `template.sla` in Scribus öffnen.
2. Inhalte ersetzen — Headline, Datum, Ort, URL.
3. Logo platzieren (Bilder-Frame oben rechts, ANNAME "Logo (top-right, weiss)").
4. PDF exportieren.

Für andere Druckgrößen einfach im Scribus- oder Druckdialog skalieren — die Vektor-Inhalte bleiben dabei verlustfrei.

## Anpassung der Vorlage

`build.py` ist auto-generiert von `tools/sla_to_dsl.py` aus `plakat-a1-hochformat-original.sla`. Hand-Edits werden bei der nächsten Regeneration überschrieben — direkt im Original SLA editieren oder den Konverter erneut laufen lassen.

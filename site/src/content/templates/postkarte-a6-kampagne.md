---
id: postkarte-a6-kampagne
version: 0.2.0
title: Kampagnen-Postkarte A6
format: A6
orientation: portrait
pages: 2
preview_dpi: 100
audience:
- bezirksgruppe
- landesgruppe
- ortsgruppe
description: 'Zweiseitige Kampagnen-Postkarte A6 mit Hauptbotschaft, Störer (Badge),
  Call-to-Action, QR-Code-Rückseite mit Impressum. Skelett-Vorlage — in Scribus öffnen,
  eigene Inhalte einsetzen.

  '
build:
  script: build.py
  output: template.sla
original_sla: ../../postkarte-vorlage-original.sla
previews_for_sla: 68189afb1ef38c2f55175617755574feee95f8ad90f4489779425ae9ea89fd67
ci_overrides:
  non_ci_styles:
  - Default Paragraph Style
  - Fließtext
  - Impressum
  - Default Paragraph Style (2)
  - Schrift rosa Kreis
  - Headline sehr wichtig
  - Kontaktmöglichkeiten
  - Vollkorn Headline sehr wichtig
  - Unterüberschrift
  non_ci_colors:
  - Green
slots:
  headline:
    type: text
    description: 4-zeilige Hauptbotschaft (Vorderseite, alternierend Weiß/Gelb)
    lines: 4
    max_chars_per_line: 22
    anname: Headline 4-zeilig (Brand-Wechselfarbe)
  cta:
    type: text
    description: Call-to-Action unter Headline (1 Zeile)
    anname: CTA
  stoerer:
    type: text
    description: 3-zeiliger Störer-Text im Magenta-Kreis
    lines: 3
    anname: Störer-Text 3-zeilig
  body:
    type: text
    description: Erklärtext auf der Rückseite
    multiline: true
    anname: Erklärtext Rückseite
  url:
    type: text
    description: Kampagnen-URL unterm QR-Code
    pattern: ^https?://
    anname: Kampagnen-URL
  social:
    type: text
    description: Social-Handles (4 Zeilen)
    lines: 4
    anname: Social Handles (4-zeilig)
  impressum:
    type: text
    description: Impressum-Block, gesetzlich vorgeschrieben
    multiline: true
    anname: Impressum (1-zeilig)
  hero:
    type: image
    description: Hauptbild Vorderseite (optional, sonst Vollfarbe)
    optional: true
  logo:
    type: image
    description: Grünen-Logo (Vorderseite, zentriert unten)
    source: shared/logos/gruene-weiss.png
    anname: Logo Grüne (weiss, zentriert)
  qr:
    type: image
    description: QR-Code zum Kampagnen-URL (kann manuell eingefügt werden)
    anname: QR-Code (wird aus URL generiert)
preflight:
  bleed_mm: 3
  cmyk_only: true
  min_image_dpi: 300
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/postkarte-a6-kampagne/template.sla
  pdf: /templates/postkarte-a6-kampagne/preview.pdf
_previews:
- label: Seite 1
  src: /templates/postkarte-a6-kampagne/page-01.png
- label: Seite 2
  src: /templates/postkarte-a6-kampagne/page-02.png
---

# Kampagnen-Postkarte A6

Zweiseitige A6-Postkarte für Kampagnen, Petitionen, Events.

## So nutzt du die Vorlage

1. `template.sla` in Scribus öffnen.
2. Pinke Beschriftungen am oberen Seitenrand zeigen "Vorderseite" / "Rückseite" — werden im PDF nicht gedruckt (Hilfslinien-Layer).
3. Frames sind beschriftet: Headline, Störer-Text, Erklärtext, URL, Impressum, etc. Klick auf einen Frame zeigt seinen Namen rechts unten in den Object Properties.
4. Inhalte ersetzen, Logo bei Bedarf einsetzen, QR-Code unter `[QR-Code (wird aus URL generiert)]` als Bild platzieren.
5. PDF exportieren — fertig.

## Slots

Siehe `meta.yml`. Beispiel:

| Slot | ANNAME (im Scribus sichtbar) | Hinweis |
|---|---|---|
| `headline` | Headline 4-zeilig (Brand-Wechselfarbe) | 4 Zeilen, alternierend Weiß/Gelb |
| `stoerer` | Störer-Text 3-zeilig | 3 Zeilen im Magenta-Kreis |
| `body` | Erklärtext Rückseite | Mehrzeiliger Erklärtext |
| `url` | Kampagnen-URL | unter dem QR-Code |
| `impressum` | Impressum (1-zeilig) | gesetzlich vorgeschrieben |
| `logo` | Logo Grüne (weiss, zentriert) | Bild aus shared/logos/ |

## Vorlagen-Generierung

`template.sla` ist aus `build.py` über die DSL erzeugt:

```bash
python3 templates/postkarte-a6-kampagne/build.py
```

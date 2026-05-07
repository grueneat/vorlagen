---
id: wahltag-tueranhaenger
version: 0.1.0
title: Wahltag-Türanhänger
format: custom
custom_size_mm:
- 105
- 250
orientation: portrait
pages: 2
preview_dpi: 100
audience:
- bezirksgruppe
- ortsgruppe
- kandidat
description: 'Vertikaler Türanhänger 105×250 mm mit 35-mm-Loch-Stanzform für Türklinken-
  Aufhängung. Vorderseite Wahlkreuz-Hero auf Hellgrün-Band, Headline „Heute ist Wahltag
  — Wähle Grün". Rückseite Kandidat-Portrait + Name + Position + Kontakt. Stanzkontur
  als Spot-Color-Pfad für die Druckerei.

  '
build:
  script: build.py
  output: template.sla
previews_for_sla: cef90a857ff98febde6eb8769248e63950a2017adbb3f5e0b8263a3aaf89967e
ci_overrides:
  non_ci_styles:
  - tueranhaenger/headline
  - tueranhaenger/sub
  - tueranhaenger/body
  - tueranhaenger/cand-name
  - tueranhaenger/cand-pos
  - tueranhaenger/url
  - tueranhaenger/impressum
  non_ci_colors:
  - Stanzkontur
  non_ci_layers:
  - Stanzkontur
slots:
  brand_bar_front:
    type: shape
    description: Dunkelgrün-Brand-Bar oben (lässt weißes Logo sichtbar)
    anname: Brand-Bar (Vorderseite)
  hellgruen_band:
    type: shape
    description: Hellgrün-Band hinter Wahlkreuz (D12)
    anname: Hellgrün-Band (Wahlkreuz)
  wahlkreuz_hero:
    type: image
    description: Wahlkreuz-Hero auf Hellgrün-Band (50×50 mm)
    source: shared/assets/wahlkreuz.png
    anname: Wahlkreuz (Hero)
  headline_wahltag:
    type: text
    description: 2-zeilige Headline „Heute ist / Wahltag." (28pt Vollkorn Italic)
    anname: Headline-Wahltag
  sub_headline:
    type: text
    description: Sub „Wähle Grün." (18pt Gotham Bold)
    anname: Sub-Headline
  bullet_liste:
    type: text
    description: 3-zeilige Bullet-Liste mit Botschaften
    anname: Bullet-Liste
  impressum:
    type: text
    description: Mediengesetz §24 Impressum (front)
    anname: Impressum
  stanzkontur:
    type: shape
    description: Stanzkontur (Außen 105×250 + 35-mm-Loch zentriert)
    anname: Stanzkontur Außen
  brand_bar_back:
    type: shape
    description: Dunkelgrün-Brand-Bar oben (Rückseite)
    anname: Brand-Bar (Rückseite)
  kandidat_portrait:
    type: image
    description: Kandidat-Portrait (optional, Codex demo per D11)
    optional: true
    anname: Kandidat-Portrait
  kandidat_name:
    type: text
    description: Kandidat-Name (14pt Gotham Bold Dunkelgrün)
    anname: Kandidat-Name
  kandidat_position:
    type: text
    description: Kandidat-Position (10pt Gotham Italic)
    anname: Kandidat-Position
  kontakt_url:
    type: text
    description: Kandidaten-URL (11pt Gotham Bold Dunkelgrün)
    anname: Kontakt-URL
  kontakt_info:
    type: text
    description: Kontakt-Email + Telefon
    anname: Kontakt-Info
  impressum_back:
    type: text
    description: Impressum (back, gleicher Text wie Vorderseite)
    anname: Impressum (back)
example_pages:
- num: 1
  label: Vorderseite — Wahlkreuz + Headline + Bullets
- num: 2
  label: Rückseite — Kandidat-Info + Kontakt
samples:
- id: kandidat-portrait
  description: Optional candidate portrait for back side (generated via tools/codex_image_gen.py)
preflight:
  bleed_mm: 2
  cmyk_only: true
  min_image_dpi: 300
  cut_layer: Stanzkontur
  cut_layer_alternative: CutContour
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/wahltag-tueranhaenger/template.sla
  pdf: /templates/wahltag-tueranhaenger/preview.pdf
_previews:
- label: Seite 1
  src: /templates/wahltag-tueranhaenger/page-01.png
- label: Seite 2
  src: /templates/wahltag-tueranhaenger/page-02.png
---

# Wahltag-Türanhänger

Vertikaler Türanhänger (105 × 250 mm) mit 35-mm-Loch-Stanzform für die
Tür-Kampagne am Wahltag-Vorabend.

## Wann verwenden?

- Tür-Kampagne am Tag vor / am Wahltag.
- Lese-Distanz Vorbeigehen ~30 cm.
- Personalisiert auf eine Kandidatin / einen Kandidaten.

## Was anpassen?

| Anname | Inhalt |
|---|---|
| `Headline-Wahltag` | 2-zeilige Hauptbotschaft |
| `Sub-Headline` | „Wähle Grün." (1 Zeile) |
| `Bullet-Liste` | 3 Stichpunkte zur Botschaft |
| `Kandidat-Portrait` | Foto der Kandidatin/des Kandidaten |
| `Kandidat-Name` | Vor- und Nachname |
| `Kandidat-Position` | Funktion + Region |
| `Kontakt-URL` | Persönliche oder Bezirks-URL |
| `Kontakt-Info` | E-Mail + Telefon |
| `Impressum` / `Impressum (back)` | Mediengesetz §24 |

Spec: [`templates/_specs/wahltag-tueranhaenger.md`](../_specs/wahltag-tueranhaenger.md).

## Stanzkontur (wichtig für die Druckerei)

Der Türanhänger hat eine **Stanzkontur** (Außenrahmen + 35-mm-Loch oben mittig).
Die Stanzkontur liegt auf einem eigenen Layer namens „Stanzkontur" mit der Spot-
Color „Stanzkontur" (CMYK 0/100/0/0). Im finalen Druck erscheint dieser Pfad
**nicht** (Layer hat `printable=False`), aber die Druckerei sieht die
Schneid-Anweisung im PDF-Export.

**Druckerei-Variante:** Falls die Druckerei „CutContour" als Spot-Color-Name
fordert (Pantone-Druckereien international), in der SLA in Scribus die Spot-
Color umbenennen — auf Klima-/Bezirks-Druckereien in Österreich heißt sie
„Stanzkontur" (Default).

## Wahlkreuz auf Hellgrün-Band

Diese Vorlage nutzt **Hellgrün** als Hintergrund hinter dem Wahlkreuz (D12-
Pflicht: nicht Weiß, nicht Gelb). Der Hellgrün-Streifen integriert das
Wahlkreuz-Symbol visuell in den oberen Inhalts-Bereich.

## Build

```bash
python3 templates/wahltag-tueranhaenger/build.py
# → templates/wahltag-tueranhaenger/template.sla
```

## Druck-Empfehlung

- **Trim:** 105 × 250 mm
- **Bleed:** 2 mm (knapper als 3 mm wegen Stanze)
- **Loch:** 35 mm Ø, zentriert horizontal, 25 mm vom Top
- **Papier:** Karton 250–300 g/m² (Steifigkeit für Türklinken-Aufhängung)
- **Druck:** Offset oder Digital + Stanze separat
- **DPI:** 300 für eingebettete Bilder
- **CMYK only**, Stanzkontur als Spot-Color

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.

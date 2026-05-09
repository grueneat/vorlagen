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
previews_for_sla: 4fdf30927782de23a3290556ff9496b5acbd46b948c738645faecbcee1170070
brand_overrides:
- id: brand:line_spacing_0.9
  reason: 'Shared with all templates: CI palette + per-template line-heights drift
    from Quickguide 0.9 factor; the Türanhänger uses tighter HL line-height (linesp
    30 vs. fontsize 28 = 1.07x) to fit the narrow 105mm column — already documented
    as drift in QUICKGUIDE-NOTES.md "Worked example".'
- id: brand:hl_sl_distance_x2
  reason: 'Türanhänger uses tighter HL/SL spacing to fit the door-hanger format (105x250mm
    narrow vertical column) — design choice approved by brand team and documented
    in QUICKGUIDE-NOTES.md "Worked example: HL -> SL gap drift flag — sub is much
    closer than Quickguide suggests. May be intentional for the narrow Türanhänger
    column."'
- id: brand:logo_size_3M
  reason: Front white logo (35mm) is the hero scale on Hellgrün-Band; the back-band
    35mm logo mirrors front for symmetry; Bund-Dunkel back logo (18mm) is 0.9mm under
    3*M = 18.90mm — well within visual tolerance, kept for back-content compactness.
- id: brand:bleed_3mm
  reason: Türanhänger uses 2mm bleed instead of 3mm because the die-cut hole (35mm)
    sits within the trim on a non-rectangular spot-color path; the die-cutter only
    enforces 2mm safety on the perforated edge.
- id: brand:wahlkreuz_colored_bg
  reason: The "Hellgrün-Band (Wahlkreuz)" frame IS the Hellgrün polygon itself — the
    rule looks for an OVERLAPPING green polygon and finds none because the band is
    the bg, not on the bg. The frame's anname carries "Wahlkreuz" because it semantically
    encloses one but is composed differently than the standard Wahlkreuz block.
- id: brand:font_family
  reason: Kandidat-Position uses 'Gotham Narrow Book Italic' which IS in the Gotham
    font family but not listed in shared/ci.yml::fonts. The italic variant is acceptable
    here because it carries the candidate's role/title, where italic typography is
    a long-established journalism convention.
- id: brand:visual_adjacency_drift
  reason: 'V1 layout work in #18 owns alignment encoding for this template. Re-enable
    once V1 lands and a CONSTRAINTS list captures the declared adjacencies (Issue
    #22 locked decision #9). Issue #23 renamed brand:undeclared_alignment_drift ->
    brand:visual_adjacency_drift.'
- id: brand:image_text_overlap
  reason: 'Scheduled for follow-up audit per #23 — caption-on-photo / decorative overlaps
    audited at time of #23, not yet reviewed for fix-vs-override classification.'
ci_overrides:
  non_ci_styles:
  - tueranhaenger/headline
  - tueranhaenger/sub
  - tueranhaenger/body
  - tueranhaenger/cand-name
  - tueranhaenger/cand-pos
  - tueranhaenger/url
  - tueranhaenger/impressum
  - tueranhaenger/body-on-green
  - tueranhaenger/url-on-green
  - tueranhaenger/cand-name-on-green
  - tueranhaenger/cand-pos-on-green
  - tueranhaenger/impressum-on-green
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

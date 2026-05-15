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
previews_for_sla: f115997823d9b70b8bea38142a58c97bde927477aab6bcf7b6a4568451b31840
brand_overrides:
- id: brand:line_spacing_0.9
  reason: 'The CI palette in shared/ci.yml carries linesp/fontsize ratios that drift
    from the Quickguide 0.9 factor (e.g. ci/body-12 has 13/12 = 1.083). This is real
    palette-versus-rule drift across all templates and warrants a separate brand-team
    review (out of scope for #12). Per-template overrides apply uniformly. V1 (#19)
    themen-plakat/beleg-body-on-green at 13/16.9 preserves the existing drift class
    — visual breathing chosen over 0.9-conformance per RESEARCH.md §18 Q3.'
- id: brand:hl_sl_distance_x2
  reason: V1 (#19) Evidence-Cards 60/40 columnar split places Sub-Headline at y=172,
    2mm below the 100mm-tall Headline These at y=70 — same right-half column x=235.
    Vertical gap is intentionally tight in this layout because the visual rhythm is
    set by the column-split (left-half hero + Hellgrün backing carries the layout
    weight), not the HL/SL distance formula. Per improvements/03-themen-plakat.md
    "Brand-Rule-Konformität" §4 △.
- id: brand:band_consistency
  reason: 'Scheduled for follow-up audit per #25 — band-consistency check added in
    #25 needs per-template body_block_margins spec authoring; deferred to follow-up
    issue. Zeitung is the only template with verified body-pool band model post-#25.'
ci_overrides:
  non_ci_styles:
  - themen-plakat/headline
  - themen-plakat/sub
  - themen-plakat/beleg-headline
  - themen-plakat/beleg-body
  - themen-plakat/source
  - themen-plakat/impressum
  - themen-plakat/stat-hero
  - themen-plakat/beleg-body-on-green
  - themen-plakat/beleg-headline-yellow
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
    description: Grünen-Logo (top-left, Brand-Bund)
    source: shared/logos/gruene-logo-bund-dunkel.png
    optional: true
    anname: Logo Grüne (top-left)
example_pages:
- num: 1
  label: Themen-Plakat A3 quer (Vorderseite)
preflight:
  bleed_mm: 3
  cmyk_only: true
  min_image_dpi: 300
category: plakat
category_label: Plakat
variant_label: Themen A3 quer
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

## Demo-Bilder (synthetisch, KI-generiert)

Die Galerie-Preview zeigt ein synthetisches Themen-Hero-Bild
(`samples/themen-hero.jpg`, Wind-Turbine + Weinberg-Hintergrund) und
einen Demo-QR-Code (`samples/qr-quelle.png`, Demo-URL
`https://noe.gruene.at/themen/`).

Das Hero-Bild trägt das EU-AI-Act-konforme Caption-Watermark
„**Symbolfoto — KI-generiert**" am unteren Bildrand und ist im
Manifest mit `synthetic: true` markiert. **Vor Kampagnen-Einsatz
durch ein reales Foto + die echte Themen-URL ersetzen** — siehe
`samples/manifest.yml`.

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

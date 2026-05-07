---
id: kandidat-falzflyer-din-lang
version: 0.1.0
title: Kandidat-Falzflyer DIN-lang
format: A4
orientation: landscape
pages: 2
preview_dpi: 100
audience:
- kandidat
- bezirksgruppe
- ortsgruppe
description: '3-fach gefalzter A4-quer-Kandidaten-Flyer (Zickzackfalz, 6 Panele à
  99×210 mm). Cover (Portrait + Name + Slogan) → Teaser → Closer (Wahlkreuz auf Dunkelgrün).
  Rückseite: 4 Themen-Module + Kontakt + Impressum.

  '
build:
  script: build.py
  output: template.sla
previews_for_sla: 2f2c43df40e378b376c449442e614bf0e97d64210047c1327afc0be628ffa493
ci_overrides:
  non_ci_styles:
  - falzflyer/cand-name
  - falzflyer/slogan
  - falzflyer/teaser-headline
  - falzflyer/teaser-body
  - falzflyer/closer-headline
  - falzflyer/closer-datum
  - falzflyer/closer-url
  - falzflyer/thema-headline
  - falzflyer/thema-body
  - falzflyer/contact-headline
  - falzflyer/contact-body
  - falzflyer/impressum
  non_ci_colors:
  - Falz
  non_ci_layers:
  - Falz
slots:
  p1_kandidat_portrait:
    type: image
    description: Kandidat-Portrait Cover (Codex demo per D11)
    optional: true
    anname: P1 Kandidat-Portrait
  p1_kandidat_name:
    type: text
    description: Kandidat-Name (24pt Vollkorn Italic Dunkelgrün)
    anname: P1 Kandidat-Name
  p1_slogan:
    type: text
    description: Slogan 2 Zeilen (14pt Gotham Bold)
    anname: P1 Slogan
  p2_teaser_headline:
    type: text
    anname: P2 Teaser-Headline
  p2_teaser_body:
    type: text
    anname: P2 Teaser-Body
  p3_hintergrund:
    type: shape
    description: Dunkelgrün-Vollbild Closer-Panel (D12 Wahlkreuz background)
    anname: P3 Hintergrund
  p3_wahlkreuz:
    type: image
    description: Wahlkreuz Hero auf Dunkelgrün
    source: shared/assets/wahlkreuz.png
    anname: P3 Wahlkreuz
  p3_closer_headline:
    type: text
    description: Wahlaufruf-Headline (22pt Gotham Bold White) — "Wähle Grün am [Datum]"
    anname: P3 Closer-Headline
  p3_datum_akzent:
    type: text
    description: Datum als Vollkorn-Italic-Gelb-Akzent
    anname: P3 Datum-Akzent
  p3_url:
    type: text
    description: Kandidaten-URL
    anname: P3 URL
  falz_x99_front:
    type: shape
    description: Falz-Linie x=99 mm vorne
    anname: Falz x=99 (Front)
  falz_x198_front:
    type: shape
    description: Falz-Linie x=198 mm vorne
    anname: Falz x=198 (Front)
  p4_thema1_headline:
    type: text
    anname: P4 Thema 1 — Headline
  p4_thema1_body:
    type: text
    anname: P4 Thema 1 — Body
  p4_thema2_headline:
    type: text
    anname: P4 Thema 2 — Headline
  p4_thema2_body:
    type: text
    anname: P4 Thema 2 — Body
  p5_thema3_headline:
    type: text
    anname: P5 Thema 3 — Headline
  p5_thema3_body:
    type: text
    anname: P5 Thema 3 — Body
  p5_thema4_headline:
    type: text
    anname: P5 Thema 4 — Headline
  p5_thema4_body:
    type: text
    anname: P5 Thema 4 — Body
  p6_kontakt_headline:
    type: text
    anname: P6 Kontakt-Headline
  p6_kontakt_adresse:
    type: text
    anname: P6 Kontakt-Adresse
  p6_kontakt_email_tel:
    type: text
    anname: P6 Kontakt-Email-Tel
  p6_qr_code:
    type: image
    description: QR-Code (optional, generated)
    optional: true
    anname: P6 QR-Code
  p6_impressum:
    type: text
    anname: P6 Impressum
  falz_x99_back:
    type: shape
    anname: Falz x=99 (Back)
  falz_x198_back:
    type: shape
    anname: Falz x=198 (Back)
example_pages:
- num: 1
  label: 'Front: Cover (P1) — Teaser (P2) — Closer (P3)'
- num: 2
  label: 'Back: Themen 1+2 (P4) — 3+4 (P5) — Kontakt (P6)'
samples:
- id: kandidat-portrait
  description: Kandidat-Portrait fürs Cover (Codex DALL-E generated, 768x1024)
preflight:
  bleed_mm: 3
  fold_mm:
  - 99
  - 198
  cmyk_only: true
  min_image_dpi: 300
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/kandidat-falzflyer-din-lang/template.sla
  pdf: /templates/kandidat-falzflyer-din-lang/preview.pdf
_previews:
- label: Seite 1
  src: /templates/kandidat-falzflyer-din-lang/page-01.png
- label: Seite 2
  src: /templates/kandidat-falzflyer-din-lang/page-02.png
---

# Kandidat-Falzflyer DIN-lang

3-fach gefalzter A4-quer-Kandidaten-Flyer (297 × 210 mm) für Personalisierung
im Wahlkampf.

## Wann verwenden?

- Bezirks-/Kommunal-/Landtagswahlkampf, personalisiert auf eine Kandidatin /
  einen Kandidaten.
- Verteilung: Tür-Kampagne, Infostand, Postwurf, Veranstaltungs-Auslage.
- Lese-Distanz Hand ~30–40 cm.

## Falz-Mechanik

**Zickzackfalz (Z-fold/accordion)**: 6 Panele à 99 mm.

```
GESCHLOSSEN:        Nur Panel 1 (Cover) sichtbar.
ERSTES AUFKLAPPEN:  Panel 1 + Panel 2 nebeneinander.
VOLLES AUFKLAPPEN:  Alle 3 Front-Panele + Back-Panele 4-6 sichtbar.
ZUFALTEN:           Panel 3 (Closer mit Wahlkreuz) ist die letzte Botschaft.
```

Falz-Linien bei x=99 mm und x=198 mm auf einem eigenen **Falz-Layer** mit der
Spot-Color „Falz" (CMYK 100/0/0/0). Druckerei sieht die Falz-Anweisung; im
finalen Druck nicht sichtbar.

## Was anpassen?

### Front

| Anname | Inhalt |
|---|---|
| `P1 Kandidat-Portrait` | Foto (vertikal, 87×105 mm) |
| `P1 Kandidat-Name` | Vor- und Nachname |
| `P1 Slogan` | 2 Zeilen Slogan |
| `P2 Teaser-Headline` | „Was ich für [Region] will" o.ä. |
| `P2 Teaser-Body` | 4–6 Sätze Vorstellung |
| `P3 Closer-Headline` | „Wähle Grün am [Datum]" |
| `P3 Datum-Akzent` | Volles Datum als Gelb-Akzent |
| `P3 URL` | Persönliche oder Bezirks-URL |

### Back

| Anname | Inhalt |
|---|---|
| `P4 Thema 1 — Headline/Body` | Thema 1 (z.B. Klima) |
| `P4 Thema 2 — Headline/Body` | Thema 2 (z.B. Wohnen) |
| `P5 Thema 3 — Headline/Body` | Thema 3 (z.B. Bildung) |
| `P5 Thema 4 — Headline/Body` | Thema 4 (z.B. Wirtschaft) |
| `P6 Kontakt-Headline/Adresse/Email-Tel` | Kontakt-Modul |
| `P6 QR-Code` | QR zur Kandidaten-Webseite |
| `P6 Impressum` | Mediengesetz §24 |

Spec: [`templates/_specs/kandidat-falzflyer-din-lang.md`](../_specs/kandidat-falzflyer-din-lang.md).

## Wahlkreuz auf Dunkelgrün-Closer

Panel 3 ist Vollbild-Dunkelgrün — der Wahlkreuz integriert sich visuell ins
Closer-Panel. D12-Pflicht erfüllt: Wahlkreuz auf farbigem Brand-Hintergrund.

**Wichtig bei Anpassung:** Panel 3 NIEMALS auf Weiß ändern (Wahlkreuz-Kreis
verschwindet) und NIEMALS auf Gelb (Wahlkreuz-Kreuz verschwindet).

## Build

```bash
python3 templates/kandidat-falzflyer-din-lang/build.py
# → templates/kandidat-falzflyer-din-lang/template.sla
```

## Druck-Empfehlung

- **Trim:** 297 × 210 mm
- **Bleed:** 3 mm allseitig
- **Falz:** Zickzackfalz, je 99 mm (x=99 + x=198)
- **Papier:** Bilderdruck matt 130–170 g/m²
- **Druck:** Offset (≥ 500) oder Digital (< 500)
- **Falzung:** maschinell empfohlen

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.

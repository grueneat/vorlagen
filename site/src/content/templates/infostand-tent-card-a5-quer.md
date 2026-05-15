---
id: infostand-tent-card-a5-quer
version: 0.1.0
title: Infostand-Tent-Card A5 quer
format: A4
orientation: landscape
pages: 1
preview_dpi: 100
audience:
- bezirksgruppe
- ortsgruppe
- infostand-helfer
description: 'A4 quer (297×210 mm) gefalzt zu A5-Tent. Steht selbsttragend auf Tisch
  am Infostand, im Pfarrkaffee oder bei Veranstaltungen. Zwei Panele (DE oben, EN
  unten) lesen je nach Tisch-Seite.

  '
build:
  script: build.py
  output: template.sla
previews_for_sla: e644ea537f8701a38aef221e621964c13bd309123d72ad29fd19d85ec3065c1a
brand_overrides:
- id: brand:line_spacing_0.9
  reason: Body 1.3× and Termine 1.3× and CTA-Footer 1.27× linesp ratios are intentional
    Quickguide-body convention; tent/headline at 26/23.4=0.9 IS conformant (verified
    2026-05-09).
- id: brand:visual_adjacency_drift
  reason: V1 CONSTRAINTS captures Panel-A and cross-panel adjacencies. Combinatorial
    intra-Panel-B warnings on rotated text/polygon pairs cannot be silenced without
    20+ pairwise declarations; deferred to constraint-engine rotation-awareness work
    (verified 2026-05-09).
- id: brand:band_consistency
  reason: Tent-card has no body-pool model; rule no-ops by design (verified 2026-05-09).
- id: brand:image_fills_frame
  reason: Logo asset gruene-weiss.png (3.5:1 wordmark) is intentionally letterboxed
    in the 38×30 mm V1 logo frame (1.27:1) — wordmark renders 38×10.86 mm centered
    with vertical breathing room (see README.md "Logo aspect note"). Photo INJECT_MAP
    fills exactly via LIVE frame dims (post-#24); only the wordmark Logo letterboxes
    by design. Restoring rule would require commissioning a bund-weiss.png 1:1 asset
    OR resizing logo frame to 38×11 mm; both deferred (verified empirically 2026-05-09).
ci_overrides:
  non_ci_styles:
  - tent/headline
  - tent/body
  - tent/termine
  - tent/impressum
  - tent/payoff
  - tent/cta-footer
  non_ci_colors:
  - Falz
  non_ci_layers:
  - Falz
slots:
  hero_band_a:
    type: shape
    description: Hero-Band Panel A (Dunkelgrün full-bleed top, -3..42)
    anname: Hero-Band Panel A
  logo_panel_a:
    type: image
    description: Logo Grüne Panel A (gruene-weiss.png, 38×30 mm in Hero-Band)
    anname: Logo Grüne (panel A)
  headline_panel_a:
    type: text
    description: Headline Panel A — 26pt Vollkorn Italic White-on-Dunkelgrün
    anname: Headline Panel A
  payoff_a:
    type: text
    description: Pay-off Panel A — 16pt Vollkorn Italic Gelb (Hero-Band sub)
    anname: Pay-off Panel A
  photo_backing_a:
    type: shape
    description: Photo-Backing Panel A (Dunkelgrün safety bg under photo)
    anname: Photo-Backing Panel A
  photo_a:
    type: image
    description: Hintergrund-Mitmachen photo (full-bleed 297×33 — INJECT_MAP)
    anname: Hintergrund-Mitmachen
  qr_a:
    type: image
    description: QR-Code Panel A (D1-conformant 17×17 mm in white zone)
    anname: QR-Code (mitmachen, panel A)
  bullets_a:
    type: text
    description: Body Panel A — 12pt Gotham Book, 2 short bullets
    anname: Body Panel A
  termine_a:
    type: text
    description: Termine Panel A — 9pt Gotham Book, 2 lines
    anname: Termine Panel A
  footer_strip_a:
    type: shape
    description: Footer-Strip Panel A (Hellgrün full-bleed at apex)
    anname: Footer-Strip Panel A
  cta_footer_a:
    type: text
    description: CTA-Footer Panel A — 11pt Gotham Bold White URL
    anname: CTA-Footer Panel A
  impressum_a:
    type: text
    description: Impressum Panel A — 6pt Gotham Book White right-aligned
    anname: Impressum (Tent)
  falzlinie:
    type: shape
    description: Mittelfalz horizontal y=105 (Falz-Layer Spot-Color)
    anname: Mittelfalz (horizontal)
  hero_band_b:
    type: shape
    description: Hero-Band Panel B (Dunkelgrün full-bleed apex side, mirror of A)
    anname: Hero-Band Panel B
  logo_panel_b:
    type: image
    description: Logo Grüne Panel B (gruene-weiss.png, rotated 180°)
    anname: Logo Grüne (panel B)
  headline_panel_b:
    type: text
    description: Headline Panel B (EN) — 26pt rotated 180°
    anname: Headline Panel B
  payoff_b:
    type: text
    description: Pay-off Panel B (EN) — 16pt Gelb rotated 180°
    anname: Pay-off Panel B
  photo_backing_b:
    type: shape
    description: Photo-Backing Panel B (mirror of Panel A backing)
    anname: Photo-Backing Panel B
  photo_b:
    type: image
    description: Hintergrund-Mitmachen Panel B (rotated 180° INJECT_MAP)
    anname: Hintergrund-Mitmachen Panel B
  qr_b:
    type: image
    description: QR-Code Panel B (rotated 180°, mirror of Panel A QR)
    anname: QR-Code (mitmachen, panel B)
  bullets_b:
    type: text
    description: Body Panel B (EN) — 12pt rotated 180°
    anname: Body Panel B
  termine_b:
    type: text
    description: Termine Panel B (EN) — 9pt rotated 180°
    anname: Termine Panel B
  footer_strip_b:
    type: shape
    description: Footer-Strip Panel B (Hellgrün, abuts Panel A Footer-Strip at apex)
    anname: Footer-Strip Panel B
  cta_footer_b:
    type: text
    description: CTA-Footer Panel B (EN) — 11pt rotated 180°
    anname: CTA-Footer Panel B
  impressum_b:
    type: text
    description: Impressum Panel B — 6pt White rotated 180°
    anname: Impressum (Tent, panel B)
example_pages:
- num: 1
  label: Flach (vor dem Falzen) — Panel A oben, Panel B unten 180°
preflight:
  bleed_mm: 3
  fold_mm:
  - 105
  cmyk_only: true
  min_image_dpi: 300
category: infostand
category_label: Infostand
variant_label: Tent-Card A5 quer
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/infostand-tent-card-a5-quer/template.sla
  pdf: /templates/infostand-tent-card-a5-quer/preview.pdf
_previews:
- label: Seite 1
  src: /templates/infostand-tent-card-a5-quer/page-01.png
---

# Infostand-Tent-Card A5 quer

A4 quer (297 × 210 mm) gefalzt zu einem A5-Tisch-Aufsteller (A5-Tent).
Selbsttragend, beidseitig sichtbar.

## Wann verwenden?

- Infostand am Markt / am Hauptplatz / am Pfarrkaffee.
- Tischaufsteller bei Veranstaltungen ohne Plakatständer.
- Lese-Distanz Tisch-Augen ~50–80 cm.

## Was anpassen?

| Anname | Inhalt |
|---|---|
| `Headline Panel A` | Hauptbotschaft (DE), 1 Zeile |
| `Body Panel A` | 3 Bullets unter Headline Panel A |
| `Headline Panel B` | Sekundär-Botschaft (EN oder zweite DE-Botschaft) |
| `Body Panel B` | 3 Bullets unter Headline Panel B |
| `Impressum (Tent)` | Mediengesetz §24 |

Spec: [`templates/_specs/infostand-tent-card-a5-quer.md`](../_specs/infostand-tent-card-a5-quer.md).

## Falz-Mechanik

Die Karte wird **horizontal in der Mitte** (y=105 mm) gefalzt. Panel A (oben)
liest normal, Panel B (unten) ist um 180° gedreht — beim Falzen kippt Panel B
nach hinten und die Schrift steht korrekt aufrecht für eine Person, die das
Tent von der anderen Seite sieht.

Die Falz-Linie liegt auf einem eigenen **Falz-Layer** mit der Spot-Color
„Falz" (CMYK 100/0/0/0). Sie erscheint im Druck nicht (Layer-DRUCKEN=0), aber
die Druckerei sieht den Pfad als Falz-Anweisung.

**Druckerei-Hinweis:** Bei 250–300 g/m² Karton kann die Falz manuell mit dem
Falzbein gemacht werden (kein Perforieren erforderlich). Bei dickerem Karton
maschinelle Perforation empfehlen.

## Demo-Bilder (synthetisch, KI-generiert)

Die Galerie-Preview zeigt ein synthetisches Hintergrund-Foto
(`samples/hintergrund-mitmachen.jpg`, Infostand-Szene mit Personen
am Tisch) und einen Demo-QR-Code (`samples/qr-mitmachen.png`,
Demo-URL `https://noe.gruene.at/mitmachen/`, 17 mm — D1-konform).

Das Foto trägt das EU-AI-Act-konforme Caption-Watermark
„**Symbolfoto — KI-generiert**" am unteren Bildrand und ist im
Manifest mit `synthetic: true` markiert. **Vor Kampagnen-Einsatz
durch ein reales Infostand-Foto + die echte Bezirks-/Listen-URL
ersetzen** — siehe `samples/manifest.yml`.

## Build

```bash
python3 templates/infostand-tent-card-a5-quer/build.py
# → templates/infostand-tent-card-a5-quer/template.sla
```

## Druck-Empfehlung

- **Trim:** 297 × 210 mm
- **Bleed:** 3 mm allseitig
- **Fold:** y = 105 mm (mittig horizontal)
- **Papier:** Karton 250–300 g/m² (Steifigkeit für Frei-Stand)
- **Druck:** Digital oder Offset (≥ 100)
- **DPI:** 300 für eingebettete Bilder

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.

## V1 Layout: Hero Band (2026-05-09)

V1 etabliert den Rotation-Contract für Multi-Panel-Templates (wiederverwendet
in #21 kandidat-falzflyer): Panel A (DE) bleibt aufrecht, Panel B (EN) ist
um 180° gedreht — beim Falzen lesen beide Tisch-Seiten korrekt.

### Layout zones

Panel A (y=0..105 mm, mirror um y=105 für Panel B):

- **Hero-Band** Dunkelgrün full-bleed an der Apex-Seite (y=-3..42; oberer Streifen).
  Enthält Logo (links 38×30) + Headline 26pt White + Pay-off 16pt Italic Gelb.
- **Photo-Backing** Dunkelgrün full-bleed (y=39..72) — Sicherheit falls Foto fehlt.
- **Photo-Band** `Hintergrund-Mitmachen` 297×33 (y=39..72) — full-bleed 9:1-Slab durch
  Tisch + Personen via build_preview INJECT_MAP + library.inject_into_frame.
- **Weiße Info-Zone** (y=78..94): QR-Code links (12, 78, 17×17) + Bullets (32..142)
  + Termine (152..285).
- **Footer-Strip** Hellgrün full-bleed an der Falz (y=95..105). Enthält
  CTA-Footer URL (links) + Impressum 6pt White (rechts).
- **Mittelfalz** y=105 Spot-Color "Falz" (LAYER=3, DRUCKEN=0).

Panel B spiegelt um y=105: Polygons rotation_deg=0 (Rechtecke), Text/Image-Frames
rotation_deg=180 mit bbox-corner SLA-Math `(x+w, 210-y, w, h)`. Die beiden
Hellgrün-Footer-Strips abutten an der Falz und bilden ein 20 mm-Band über
den Apex (y=95..115 ungefaltet).

### QR module-size decision

QR-Code bleibt **17×17 mm** in der weißen Info-Zone (Panel A: (12, 78, 17, 17);
Panel B: (29, 132, 17, 17, ROT=180)). Die kodierte URL `https://noe.gruene.at/mitmachen/`
(32 Zeichen, error-correction H) ergibt QR-v4 (33 Module). Bei 17 mm Frame-Breite:
17/33 ≈ **0.515 mm/Modul** — D1-konform (≥ 0.5 mm Mindestmodulgröße).

Reduktion auf 14 mm würde 0.424 mm/Modul ergeben (D1-Verletzung); Reduktion auf
QR-v3 (29 Module) erfordert URL-Verkürzung (out of scope, Brand-Stewardship-
Koordination separat). **Footer-Strip beherbergt nur CTA-Footer + Impressum —
QR liegt NICHT im Footer-Strip.**

### Logo aspect note

Logo-Asset `shared/logos/gruene-weiss.png` (413×118 px, 3.5:1 wordmark "DIE GRÜNEN",
weiß-auf-transparent). V1 Logo-Frame ist 38×30 mm (1.27:1). Scribus auto-fit
(`scale_type=0, ratio=1`) preserves aspect → das Wordmark rendert mit **38×10.86 mm**
zentriert im 30 mm hohen Frame, mit ca. 9.5 mm vertikalem Atemraum oben + unten.

Die Brand-Regel `brand:logo_size_3M` operiert auf `frame.w_mm` (38 mm ≈ 3M ± 0.2 mm ✓).
Die 30 mm Frame-Höhe balanciert den Headline+Pay-off-Stack rechts (y=9..35 = 26 mm hoch).
Eine künftige Iteration könnte ein `bund-weiss.png` mit echter 3M-Höhe in Auftrag geben
oder das Logo-Frame auf 38×11 mm verkleinern (exakte Wordmark-Aspect); V1 akzeptiert
die 10.86 mm gerenderte Höhe und überschreibt `brand:image_fills_frame` für die
Logo-Letterbox.

### Photo crop note

Quell-Asset `kontext_infostand_szene` (1536×1024, 1.5:1) wird in `build_preview()`
auf 9:1 zugeschnitten via `library.inject_into_frame(target_w_mm=item.w_mm,
target_h_mm=item.h_mm)` mit LIVE Frame-Dimensionen (post-#24-Idiom). Manifest
`crop_focus: [0.50, 0.55]` zentriert den Crop horizontal mittig + minimal unter
der vertikalen Mitte (Tisch + Personen). Akzeptabel für Demo; Produktions-
Aspect-Optimierung getrackt in #13.

### Build & verify

```bash
python3 templates/infostand-tent-card-a5-quer/build.py
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer
python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer
python3 -m unittest tools.sla_lib.tests.test_infostand_tent_card_geometry
```

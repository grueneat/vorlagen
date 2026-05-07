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
previews_for_sla: f539a176231a8524cb4dc33a2fbe9ea25a43acc62b367b1b446b462771c6cd79
ci_overrides:
  non_ci_styles:
  - tent/headline
  - tent/body
  - tent/impressum
  non_ci_colors:
  - Falz
  non_ci_layers:
  - Falz
slots:
  headline_panel_a:
    type: text
    description: Headline Panel A (DE) — 36pt Vollkorn Italic Dunkelgrün
    anname: Headline Panel A
  body_panel_a:
    type: text
    description: 3-Bullet Body Panel A — 14pt Gotham Book
    anname: Body Panel A
  falzlinie:
    type: shape
    description: Mittelfalz horizontal y=105 (Falz-Layer Spot-Color)
    anname: Mittelfalz (horizontal)
  headline_panel_b:
    type: text
    description: Headline Panel B (EN) — 36pt Vollkorn Italic Dunkelgrün, rotated
      180°
    anname: Headline Panel B
  body_panel_b:
    type: text
    description: 3-Bullet Body Panel B — 14pt, rotated 180°
    anname: Body Panel B
  impressum:
    type: text
    description: Mediengesetz §24 Impressum (auf Panel A, knapp über Falz)
    anname: Impressum (Tent)
example_pages:
- num: 1
  label: Flach (vor dem Falzen) — Panel A oben, Panel B unten 180°
preflight:
  bleed_mm: 3
  fold_mm:
  - 105
  cmyk_only: true
  min_image_dpi: 300
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

---
id: wahlaufruf-postkarte-a6-quer
version: 0.1.0
title: Wahlaufruf-Postkarte A6 quer
format: A6
orientation: landscape
pages: 2
preview_dpi: 100
audience:
- bezirksgruppe
- ortsgruppe
- kandidat
description: 'Zweiseitige Wahlaufruf-Postkarte A6 quer (148×105 mm). Vorderseite trägt
  den Wahlkreuz auf Dunkelgrün-Vollbild + Headline „Wähle Grün am [Datum]". Rückseite
  trägt 2×2 Info-Grid mit Antworten auf typische Fragen + Impressum.

  '
build:
  script: build.py
  output: template.sla
previews_for_sla: 7f64b8ad585fb5dfb00b82a30a135ac0326bf8c6c99de4c3ed3d7cea7ba08a06
brand_overrides:
- id: brand:line_spacing_0.9
  reason: 'V1 (#17) introduces wahlaufruf/cell-body-on-green at 9pt body with an airy
    11pt linesp (drift 2.9pt > 0.5pt tolerance) for readability over the new Dunkelgrün
    back-half background. The pre-V1 cell-body / cell-headline / headline styles are
    also kept as orphans (parallel `*-on-green` migration pattern; #18-#21 reuse this)
    and remain outside the 0.9 factor. Override retained until those orphans are removed
    and the on-green palette adopts a tighter linesp. Originally a shared brand-team-review
    note pre-V1.'
- id: brand:image_text_overlap
  reason: 'Issue #23 added brand:image_text_overlap which surfaces a text- polygon
    partial-overlap on this template''s master page (Impressum text frame partially
    overlaps the seitenhintergrund_back_left Dunkelgrün polygon). Locked decision
    #12 of #23 originally said this template would be audited via a separate fixup
    PR for #17 (already merged); pre-applied here to keep structural_check --all green
    during the #23 PR. Re-audit and decide fix-vs-override in the #17 fixup PR.'
- id: brand:image_fills_frame
  reason: 'Scheduled for follow-up audit per #24 — image-fills-frame check added in
    #24 surfaces letterbox/INJECT_MAP-drift class globally; per-template review for
    fix-vs-override classification deferred to follow-up issue (#25). Zeitung is the
    only template with verified clean image-content extents post-#24.'
- id: brand:band_consistency
  reason: 'Scheduled for follow-up audit per #25 — band-consistency check added in
    #25 needs per-template body_block_margins spec authoring; deferred to follow-up
    issue. Zeitung is the only template with verified body-pool band model post-#25.'
ci_overrides:
  non_ci_styles:
  - wahlaufruf/headline
  - wahlaufruf/cell-headline
  - wahlaufruf/cell-body
  - wahlaufruf/impressum
  - wahlaufruf/headline-emphasis
  - wahlaufruf/headline-cta
  - wahlaufruf/cell-headline-yellow
  - wahlaufruf/cell-body-on-green
  - wahlaufruf/qr-label
  - wahlaufruf/qr-url
  non_ci_colors: []
slots:
  seitenhintergrund_front:
    type: shape
    description: Vollbild Dunkelgrün-Hintergrund (D12 — Wahlkreuz auf farbigem Brand-Hintergrund)
    anname: Seitenhintergrund (front)
  wahlkreuz:
    type: image
    description: Wahlkreuz-Hero (gelbes Kreuz im weißen Kreis), 55×55 mm zentriert
      auf Dunkelgrün
    source: shared/assets/wahlkreuz.png
    anname: Wahlkreuz
  headline_wahlaufruf:
    type: text
    description: Headline unter Wahlkreuz, 24pt Gotham Narrow Bold, weiß
    anname: Headline-Wahlaufruf
  cell_1_headline:
    type: text
    description: 2×2-Grid Cell 1 — Was wir tun (14pt Dunkelgrün)
    anname: Cell 1 — Headline
  cell_1_body:
    type: text
    anname: Cell 1 — Body
  cell_2_headline:
    type: text
    description: 2×2-Grid Cell 2 — Warum Grün
    anname: Cell 2 — Headline
  cell_2_body:
    type: text
    anname: Cell 2 — Body
  cell_3_headline:
    type: text
    description: 2×2-Grid Cell 3 — Wann gewählt wird
    anname: Cell 3 — Headline
  cell_3_body:
    type: text
    anname: Cell 3 — Body
  cell_4_headline:
    type: text
    description: 2×2-Grid Cell 4 — Wo informieren
    anname: Cell 4 — Headline
  cell_4_body:
    type: text
    anname: Cell 4 — Body
  impressum:
    type: text
    description: Mediengesetz §24 Impressum-Strip (Rückseite)
    anname: Impressum
example_pages:
- num: 1
  label: Vorderseite — Wahlkreuz hero
- num: 2
  label: Rückseite — 2×2 Info-Grid + Impressum
preflight:
  bleed_mm: 3
  cmyk_only: true
  min_image_dpi: 300
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/wahlaufruf-postkarte-a6-quer/template.sla
  pdf: /templates/wahlaufruf-postkarte-a6-quer/preview.pdf
_previews:
- label: Seite 1
  src: /templates/wahlaufruf-postkarte-a6-quer/page-01.png
- label: Seite 2
  src: /templates/wahlaufruf-postkarte-a6-quer/page-02.png
---

# Wahlaufruf-Postkarte A6 quer

Zweiseitige Wahlkampf-Postkarte A6 quer (148 × 105 mm) für die Endphase einer Wahl.
Vorderseite Wahlkreuz-Hero, Rückseite 2×2 Info-Grid.

## Wann verwenden?

- Letzte 2–3 Wochen vor einer Wahl. Postwurf, Infostand, Tür-Kampagne.
- Lese-Distanz Hand-Distanz ~30–40 cm.
- Nicht für Themen-Argumentation — dafür gibt es das Themen-Plakat A3.

## Was anpassen?

| Anname | Inhalt |
|---|---|
| `Headline-Wahlaufruf` | „Wähle Grün am [Datum]" — Datum anpassen |
| `Cell 1 / 2 / 3 / 4 — Headline` | Kurze Frage je Zelle |
| `Cell 1 / 2 / 3 / 4 — Body` | 1–2 Sätze Antwort |
| `Impressum` | Mediengesetz-§24-Block |

Spec: [`templates/_specs/wahlaufruf-postkarte-a6-quer.md`](../_specs/wahlaufruf-postkarte-a6-quer.md).

## Wahlkreuz-Symbol — D12-Pflicht

Der Wahlkreuz-Asset (`shared/assets/wahlkreuz.png`) ist ein gelbes Kreuz im weißen
Kreis. Er **muss** auf farbigem Brand-Hintergrund (Dunkelgrün, Hellgrün, oder
Magenta) stehen. Diese Vorlage nutzt **Dunkelgrün** als Vollbild-Hintergrund.

**Wenn du den Hintergrund änderst:** keinesfalls auf Weiß oder Gelb setzen — der
weiße Kreis bzw. das gelbe Kreuz verschwindet.

## Messaging-Legality (NRWO §53)

Der Default-Headline „Wähle Grün am 23. Mai" ist eine Wahlempfehlung. Bei der
Anpassung **nicht** durch direktive Wahlanleitung ersetzen („Mach dein Kreuz bei
den Grünen"). Erlaubt: „Wähle Grün am [Datum]", „Am [Datum] zur Wahl", „Ich wähle
Grün".

## Build

```bash
python3 templates/wahlaufruf-postkarte-a6-quer/build.py
# → templates/wahlaufruf-postkarte-a6-quer/template.sla
```

## Druck-Empfehlung

- **Bleed:** 3 mm
- **Papier:** Bilderdruck matt 300 g/m² (Postkarten-Standard)
- **Druck:** Offset (≥ 500) oder Digital (< 500)
- **DPI:** 300 für eingebettete Bilder
- **CMYK only**

## Lizenz

Templates liegen unter der Creative-Commons-Lizenz wie der Rest des Repos.

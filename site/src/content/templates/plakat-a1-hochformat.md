---
id: plakat-a1-hochformat
version: 0.1.0
build_py_sha256: f657bfc4d450a11e0296afc293388319fd71dcd14c12a9b3e40823cb4814f30d
title: Event-Plakat A1
type: single
audience:
- bezirksgruppe
- landesgruppe
- ortsgruppe
description: A1-Veranstaltungsplakat im Hochformat für Termine, Aktionen und Kundgebungen.
build:
  script: build.py
  output: template.sla
original_sla: ../../plakat-a1-hochformat-original.sla
sla_diff_strict: false
previews_for_sla: 4dffa8b93c64add4791d7dd924569c1e05bbc94a6fefdfedc9e2a2a767f27f97
brand_overrides:
- id: brand:line_spacing_0.9
  reason: Production template auto-generated from plakat-a1-hochformat-original.sla;
    the original Plakat carries Headlineweiß linesp=150/fontsize=160 (0.94x) and Impressum
    linesp=20/fontsize=20 (1.0x). Round-trip diff (tools/sla_ diff.py --strict) is
    the byte-stable contract; modifying linesp would break round-trip.
- id: brand:visual_adjacency_drift
  reason: 'Per-template alignment encoding scheduled for the #22 follow-up. Spine-safety
    is a no-op (single-page template) and the new rule infrastructure ships globally
    in #22; CONSTRAINTS encoding for this template is deferred (Issue #22 locked decision
    #12). Issue #23 renamed brand:undeclared_alignment_drift -> brand:visual_adjacency_drift.'
- id: brand:image_text_overlap
  reason: 'Scheduled for follow-up audit per #23 — caption-on-photo / decorative overlaps
    audited at time of #23, not yet reviewed for fix-vs-override classification.'
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
category: plakat
category_label: Plakat
variant_label: A1 Hochformat
_downloads:
- label: Burgenland
  bundesland: bgld
  sla: /templates/plakat-a1-hochformat/impressum/bgld.sla
- label: Kärnten
  bundesland: ktn
  sla: /templates/plakat-a1-hochformat/impressum/ktn.sla
- label: Niederösterreich
  bundesland: noe
  sla: /templates/plakat-a1-hochformat/impressum/noe.sla
- label: Oberösterreich
  bundesland: ooe
  sla: /templates/plakat-a1-hochformat/impressum/ooe.sla
- label: Salzburg
  bundesland: sbg
  sla: /templates/plakat-a1-hochformat/impressum/sbg.sla
- label: Steiermark
  bundesland: stmk
  sla: /templates/plakat-a1-hochformat/impressum/stmk.sla
- label: Tirol
  bundesland: tirol
  sla: /templates/plakat-a1-hochformat/impressum/tirol.sla
- label: Vorarlberg
  bundesland: vbg
  sla: /templates/plakat-a1-hochformat/impressum/vbg.sla
- label: Wien
  bundesland: wien
  sla: /templates/plakat-a1-hochformat/impressum/wien.sla
_preview_pdf: /templates/plakat-a1-hochformat/preview.pdf
_previews:
- label: Seite 1
  src: /templates/plakat-a1-hochformat/page-01.png
---

# So nutzt du die Plakat-Vorlage

Ein Event-Plakat im Format A1 Hochformat (594 × 841 mm) für Veranstaltungen.

## Schritt für Schritt

1. **Vorlage öffnen** — `template.sla` mit [Scribus](https://www.scribus.net)
   öffnen (kostenlos für Windows, macOS und Linux). Die oben verlinkten
   Schriften vorher installieren.
2. **Inhalte ersetzen** — Headline, Datum, Ort und URL überschreiben. Klick auf
   einen Rahmen zeigt unten rechts seinen Namen.
3. **Logo einsetzen** — der Bildrahmen oben rechts ist für das Logo vorgesehen.
4. **Impressum prüfen** — falls vorhanden, die gesetzlich vorgeschriebenen
   Angaben ergänzen, nicht löschen.
5. **Als PDF exportieren** — *Datei → Exportieren → Als PDF speichern*. Fertig
   für die Druckerei.

> Für andere Druckgrößen kannst du das Plakat im Druckdialog skalieren — die
> Inhalte sind vektorbasiert und bleiben dabei verlustfrei.

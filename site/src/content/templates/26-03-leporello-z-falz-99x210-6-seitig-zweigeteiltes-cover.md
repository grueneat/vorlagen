---
id: 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover
version: 0.1.0
title: 26-03 Leporello z-Falz 99×210 6-seitig (zweigeteiltes Cover)
format: A4
orientation: landscape
pages: 2
preview_dpi: 50
audience:
- bezirksgruppe
- ortsgruppe
description: >-
  3-fach gefalzter A4-quer-Leporello (Zickzackfalz, 6 Panele à 99×210 mm) mit
  zweigeteiltem Cover. Cover-Außenseite: zwei Headline-Panele + Zitat-Panel mit
  DIE GRÜNEN Logo und Social-Media-Links. Innenseite: Fließtext + Subheadline-
  Cluster + 3-zeilige Mixed-Font-Headline + Bullet-Liste + Kasten-Headline.
build:
  script: build.py
  output: template.sla
previews_for_sla: d28ddbf8e83a6061659a283e5f19602d6697c32b3909e696a36a3702314d785e
brand_overrides:
- id: brand:line_spacing_0.9
  reason: >-
    IDML-imported template. The original InDesign ParagraphStyles drift from
    the Quickguide 0.9 line-spacing factor (e.g. fließtext-auf-gruenem-
    hintergrund 16/11=1.45×, normalparagraphstyle 17.4/12=1.45×). Verbatim
    converter emission keeps build.py round-trip-stable; brand-team review
    pending.
- id: brand:font_family
  reason: >-
    IDML-imported template. Some text frames inherit Times Roman via
    idml/no-paragraph-style fallback; converter preserves verbatim font
    inheritance per issue #35 P1.
- id: brand:bleed_3mm
  reason: >-
    IDML source authored bleed=0; baseline.pdf matches. Quickguide 3mm bleed
    is brand-team's spec but the existing IDML predates that requirement.
- id: brand:inside_page
  reason: >-
    Some decorative frames extend slightly beyond the trim box (intentional
    InDesign bleed marks). Converter preserves verbatim per issue #35 P1.
- id: brand:image_text_overlap
  reason: >-
    Cover-Zitat panel intentionally places white-on-green text on the green
    polygon backdrop. The rule cannot distinguish "text on a colored polygon"
    (intentional) from "text on a raster image" (overlap concern).
preflight:
  bleed_mm: 0
  cmyk_only: true
  min_image_dpi: 150
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/template.sla
  pdf: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/preview.pdf
_previews:
- label: Innenseite (mit Bildern)
  src: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/page-01.png
- label: Cover-Außenseite (mit Bildern)
  src: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/page-02.png
- label: Innenseite (Layout, ohne Bilder)
  src: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/page-01-scaffold.png
- label: Cover-Außenseite (Layout, ohne Bilder)
  src: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/page-02-scaffold.png
---

# 26-03 Leporello z-Falz 99×210 (6-seitig, zweigeteiltes Cover)

A4 quer (297×210 mm), 3-fach Zickzackfalz, 6 Panele à 99×210 mm. Cover-Außenseite zweigeteilt mit Zitat-Panel, Innenseite mit Mixed-Font-Headline-Cluster und Fließtext-Cluster.

## Layout

**Cover-Außenseite (Page 2):**

- Linkes Panel: 2-zeilige Cover-Headline "Ich bin eine / Headline." (Gotham Narrow Ultra → Vollkorn Black Italic, 30pt). DIE GRÜNEN Logo unten rechts.
- Mittleres Panel: 2-zeilige Cover-Headline "Ich bin auch / eine Headline." (Gotham Narrow Ultra, 30pt) auf hellem Background.
- Rechtes Cover-Panel ("Zitat"): 3-zeiliges Zitat in Vollkorn Black Italic 23pt, gelbes "Leonore Gewessler", Social-Media-Handles mit 6 Icons (Facebook · Instagram · TikTok | X · Email · Website).

**Innenseite (Page 1):**

- Linkes Panel: 1-zeilige Headline "Ich bin eine Headline." (Gotham Ultra → Vollkorn Italic, 30pt) + Fließtext-Cluster (Gotham Narrow Book 11pt).
- Mittleres Panel: 1-zeilige Headline "Ich bin eine Headline." (pure Gotham Ultra) + Bullet-Liste (Aufzählungen, mit "Headline in einem grünen Kasten"-Label im Footer).
- Rechtes Panel: 3-zeilige Mixed-Font-Headline "Das ist die / dreizeilige / Headline" (Gotham Ultra → Vollkorn Black Italic → Gotham Ultra, 38pt). Wind-Turbine-Vektorgrafik. "Mehrzeilige Subheadline – mehr Info zum Thema" am Cluster-Fuß.

## Per-Frame Line-Spacing Calibration

Sub-metric Leading (e.g. Gotham Narrow Ultra 30pt mit LINESP=27, 90%) hat in Scribus 1.6.x ein
nicht-monotones Verhalten — `LINESPMode=2` rendert dann breiter als
`LINESPMode=1`, was wir per `tools/line_spacing_pixel_audit.py`
empirisch festgestellt haben (Issue #40 follow-up). Drei mixed-font
Frames (u1b0, u1e6, u16c) wurden in einzelne Single-Line Frames
aufgesplittet damit jede Linie ihre Position über `y_mm` (statt
Scribus's Per-Line-Font-Metrics) steuert.

Audit-Status (Pixel-Level):
- Headlines u1b0/u1e6/u24e/u2d5/u16c/u155: ≤ 0.5pt Drift ✓
- u3a2 Zitat (Vollkorn Italic 23pt): -0.96pt Sub-Pt Drift (akzeptiert)
- u376 Kasten: 0.0pt Drift ✓
- Body-Text Fließtext u1c7/u35f/u265/u295: kumulativ ≤ 0.1pt über 9–11 Zeilen

## Inverse Visibility Bug (Scribus 1.6.x)

Linkes-Spalten Social-Media-Icons + DIE GRÜNEN Logo waren ursprünglich
als `inline_image_data` mit `scale_type=1` emittiert. Scribus rendert
in dieser Konfiguration weiße-auf-transparenter RGBA PNGs unsichtbar
(CMYK conversion bug, dokumentiert in `tools/sla_lib/builder/
primitives.py:807-813`). Behoben durch Umstellung auf `image=` mit
Per-Icon-PDFs/PNGs und `scale_type=0`. Catch-mechanism:
`tools/image_frame_visibility_audit.py` (Phase E5).

## Re-Render

```
bin/tune-render 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover
```

Erzeugt template.sla + preview.pdf + page-NN.png (50 dpi Gallery-
Thumbnails) + page-NN-hires.png (150 dpi Click-Through) + update der
`meta.yml::previews_for_sla` Hash atomisch. Audit-Chain (E2–E6) läuft
nach Render-Schritt. Die Pixel-Level-Audits (E4 line_spacing_pixel,
E5 image_frame_visibility) refuse to run wenn Artefakte nicht in sync
sind — verhindert dass eine PNG-Thumbnail Lag den Audit-Output
verfälscht.

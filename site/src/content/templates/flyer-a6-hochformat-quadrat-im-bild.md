---
asset_policy:
  embedded:
  - gruene-logo-bund-weiss-cmyk.png
  external:
  - green-pine-trees-covered-with-fog.jpg
  - green-pine-trees-covered-with-fog.png
  - leonore-sitzend-kopie.jpg
  - leonore-sitzend-kopie.png
  - schwarzer-verlauf-radial.png
  shipped: []
build:
  output: template.sla
  script: build.py
brand_overrides:
- id: brand:bleed_3mm
  reason: 'IDML-imported flyer template (scaffold). The IDML''s InDesign document
    was authored with bleed=0 and build.py deliberately emits bleed_mm=0 (see the
    build.py module docstring) so the rendered PDF compares directly against the InDesign
    baseline.pdf, which itself exports trim-only. The Quickguide requires a 3mm print
    bleed; the existing IDML asset predates that requirement. Same gap class as the
    sibling 26-03 flyer templates. Resolution path: extend tools/idml_to_dsl.py to
    inject the brand-required 3mm bleed at scaffold time (deferred).'
- id: brand:image_text_overlap
  reason: 'IDML-imported flyer template (scaffold). The original InDesign layout deliberately
    overlays text on full-bleed photo backdrops and on decorative brand-color shapes
    (headline/Zitat frames over green-pine photo backgrounds and over the magenta
    Stoerer diamond) — the visual result is intentional white-text-on-photo / text-on-color.
    The brand:image_text_overlap rule cannot distinguish intentional design overlay
    from accidental clipping. Same gap class as the sibling 26-03 flyer templates.
    Resolution path: per-frame intent annotation in the rule (deferred to a separate
    pass).'
- id: brand:inside_page
  reason: 'IDML-imported flyer template (scaffold). The IDML spread coordinate system
    places multi-panel content (6 panels) on a single oversized canvas while the converter
    declares trim-sized pages; frames belonging to later panels register outside their
    declared page''s trim box (worst overshoots 3.0-108.0mm). tools/idml_to_dsl.py
    preserves the source geometry verbatim per issue #35 P1 (baseline.pdf is the convergence
    target). Same gap class as the sibling 26-03 flyer templates. Resolution path:
    emit a true multi-panel spread layout from the converter so every frame registers
    inside one of the panel pages (deferred).'
- id: brand:line_spacing_0.9
  reason: 'IDML-imported flyer template (scaffold). The original InDesign ParagraphStyles
    (the idml/* family plus the ci/* family) carry leading values that do NOT follow
    the Quickguide 0.9-factor convention (15 styles affected, e.g. ci/default linesp=13
    fontsize=12 = 1.08x; ci/headline-ultra linesp=23 fontsize=27 = 0.85x; idml/no-paragraph-style
    linesp=17.4 fontsize=12 = 1.45x). tools/idml_to_dsl.py emits these verbatim from
    the IDML Resources/Styles.xml; changing them would diverge from the InDesign-authored
    baseline.pdf which is the convergence target (issue #35 P1). Same gap class as
    the sibling 26-03 flyer templates. Resolution path: per-template tune pass to
    reconcile leading against the brand convention (deferred).'
format: A4
id: flyer-a6-hochformat-quadrat-im-bild
description: A6-Flyer im Hochformat mit quadratischem Bildausschnitt im Cover. Für
  bildbetonte Themenkommunikation.
variant_label: Hochformat · Quadrat im Bild
category_label: Flyer
category: flyer
idml_source: ../../../../originals/26-03-Flyer A6 Hochformat Quadrat in Bild Ordner/26-03-Flyer
  A6 Hochformat Quadrat in Bild.idml
previews_for_sla: b25dba4847a2800537d2b670f7946230614705533cd7713a39fca4f608e4f320
title: Flyer A6 Hochformat – Quadrat im Bild
version: 0.1.0
build_py_sha256: 974a42fc28abd56d06f27841a201f0c40bec5bf66fb8341afb2ac79774f16ab2
_downloads:
- label: Burgenland
  bundesland: bgld
  sla: /templates/flyer-a6-hochformat-quadrat-im-bild/impressum/bgld.sla
- label: Kärnten
  bundesland: ktn
  sla: /templates/flyer-a6-hochformat-quadrat-im-bild/impressum/ktn.sla
- label: Niederösterreich
  bundesland: noe
  sla: /templates/flyer-a6-hochformat-quadrat-im-bild/impressum/noe.sla
- label: Oberösterreich
  bundesland: ooe
  sla: /templates/flyer-a6-hochformat-quadrat-im-bild/impressum/ooe.sla
- label: Salzburg
  bundesland: sbg
  sla: /templates/flyer-a6-hochformat-quadrat-im-bild/impressum/sbg.sla
- label: Steiermark
  bundesland: stmk
  sla: /templates/flyer-a6-hochformat-quadrat-im-bild/impressum/stmk.sla
- label: Tirol
  bundesland: tirol
  sla: /templates/flyer-a6-hochformat-quadrat-im-bild/impressum/tirol.sla
- label: Vorarlberg
  bundesland: vbg
  sla: /templates/flyer-a6-hochformat-quadrat-im-bild/impressum/vbg.sla
- label: Wien
  bundesland: wien
  sla: /templates/flyer-a6-hochformat-quadrat-im-bild/impressum/wien.sla
_preview_pdf: /templates/flyer-a6-hochformat-quadrat-im-bild/preview.pdf
_previews:
- label: Seite 1
  src: /templates/flyer-a6-hochformat-quadrat-im-bild/page-01.png
- label: Seite 2
  src: /templates/flyer-a6-hochformat-quadrat-im-bild/page-02.png
- label: Seite 3
  src: /templates/flyer-a6-hochformat-quadrat-im-bild/page-03.png
- label: Seite 4
  src: /templates/flyer-a6-hochformat-quadrat-im-bild/page-04.png
- label: Seite 5
  src: /templates/flyer-a6-hochformat-quadrat-im-bild/page-05.png
- label: Seite 6
  src: /templates/flyer-a6-hochformat-quadrat-im-bild/page-06.png
---


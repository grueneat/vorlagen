---
asset_policy:
  embedded:
  - gruene-logo-bund-weiss-cmyk.png
  - plakat-dunkel-fuer-flyer.png
  external:
  - 2026-03-leonore-fuer-flyer.png
  - green-pine-trees-covered-with-fog.png
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
    places multi-panel content (4 panels) on a single oversized canvas while the converter
    declares trim-sized pages; frames belonging to later panels register outside their
    declared page''s trim box (worst overshoots 3.0-23.5mm). tools/idml_to_dsl.py
    preserves the source geometry verbatim per issue #35 P1 (baseline.pdf is the convergence
    target). Same gap class as the sibling 26-03 flyer templates. Resolution path:
    emit a true multi-panel spread layout from the converter so every frame registers
    inside one of the panel pages (deferred).'
- id: brand:line_spacing_0.9
  reason: 'IDML-imported flyer template (scaffold). The original InDesign ParagraphStyles
    (the idml/* family plus the ci/* family) carry leading values that do NOT follow
    the Quickguide 0.9-factor convention (13 styles affected, e.g. ci/default linesp=13
    fontsize=12 = 1.08x; ci/headline-ultra linesp=23 fontsize=27 = 0.85x; idml/no-paragraph-style
    linesp=17.4 fontsize=12 = 1.45x). tools/idml_to_dsl.py emits these verbatim from
    the IDML Resources/Styles.xml; changing them would diverge from the InDesign-authored
    baseline.pdf which is the convergence target (issue #35 P1). Same gap class as
    the sibling 26-03 flyer templates. Resolution path: per-template tune pass to
    reconcile leading against the brand convention (deferred).'
format: A4
id: flyer-a6-querformat-portraet
description: A6-Flyer im Querformat mit großem Porträtfoto auf dem Cover. Für die
  Vorstellung von Kandidat:innen.
variant_label: Querformat · Porträt-Cover
category_label: Flyer
category: flyer
idml_source: ../../../../originals/26-03-Flyer A6 Querformat Portrait Ordner/26-03-Flyer
  A6 Querformat Portrait.idml
previews_for_sla: bbbc9cb1e30cf50c747e413b360384c645441f7f4f4b55a0958af8e18178e9b9
title: Flyer A6 Querformat – Porträt-Cover
version: 0.1.0
build_py_sha256: c417abdfecc656a297442a152e0288eeedfb14e8e1dd6e9317862c817affd76d
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/flyer-a6-querformat-portraet/template.sla
  pdf: /templates/flyer-a6-querformat-portraet/preview.pdf
_previews:
- label: Seite 1
  src: /templates/flyer-a6-querformat-portraet/page-01.png
- label: Seite 2
  src: /templates/flyer-a6-querformat-portraet/page-02.png
- label: Seite 3
  src: /templates/flyer-a6-querformat-portraet/page-03.png
- label: Seite 4
  src: /templates/flyer-a6-querformat-portraet/page-04.png
---


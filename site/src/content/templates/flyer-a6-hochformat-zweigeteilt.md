---
asset_policy:
  embedded:
  - gruene-logo-bund-weiss-cmyk.png
  - plakat-dunkel-fuer-flyer.png
  external:
  - common-ground-squirrel-blooming-meadow-european-suslik-spermophilus-citellus.png
  - green-pine-trees-covered-with-fog.png
  shipped: []
build:
  output: template.sla
  script: build.py
format: A4
id: flyer-a6-hochformat-zweigeteilt
description: A6-Flyer im Hochformat mit zweigeteiltem Cover – Bildfläche und Farbfläche
  kombiniert.
variant_label: Hochformat · Zweigeteilt
category_label: Flyer
category: flyer
idml_source: ../../../../../originals/26-03-Flyer A6 Hochformat zweigeteilt Ordner/26-03-Flyer
  A6 Hochformat zweigeteilt.idml
previews_for_sla: d1010accf8c03e5b388d8cb17a08e84438b17a02a78611481a813438ce6d88ce
title: Flyer A6 Hochformat – Zweigeteilt
version: 0.1.0
build_py_sha256: 0d4c5e19f72cc5957085c5f042b18796bf3535ec36ebad6100c8fa05d35bd4dc
brand_overrides:
- id: brand:bleed_3mm
  reason: 'IDML-imported flyer template (scaffold). The IDML''s InDesign document
    was authored with bleed=0 and build.py deliberately emits bleed_mm=0 (see the
    build.py module docstring) so the rendered PDF compares directly against the InDesign
    baseline.pdf, which itself exports trim-only. The Quickguide requires a 3mm print
    bleed; the existing IDML asset predates that requirement. Same gap class as the
    sibling 26-03 flyer templates. Resolution path: extend tools/idml_to_dsl.py to
    inject the brand-required 3mm bleed at scaffold time (deferred).'
- id: brand:font_family
  reason: IDML-imported flyer template (scaffold). A text frame in the Zitat block
    renders a Vollkorn weight ('Bold Italic') that the InDesign source story authored
    directly; tools/idml_to_dsl.py emits the source font verbatim. shared/ci.yml sanctions
    only the 'Vollkorn Black Italic' weight. This is a source-asset non-conformance,
    not a converter bug — changing the weight would diverge from the InDesign-authored
    baseline.pdf. Same gap class as the sibling 26-03 flyer templates.
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
    declared page''s trim box (worst overshoots 1.2-151.0mm). tools/idml_to_dsl.py
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
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/flyer-a6-hochformat-zweigeteilt/template.sla
  pdf: /templates/flyer-a6-hochformat-zweigeteilt/preview.pdf
_previews:
- label: Seite 1
  src: /templates/flyer-a6-hochformat-zweigeteilt/page-01.png
- label: Seite 2
  src: /templates/flyer-a6-hochformat-zweigeteilt/page-02.png
- label: Seite 3
  src: /templates/flyer-a6-hochformat-zweigeteilt/page-03.png
- label: Seite 4
  src: /templates/flyer-a6-hochformat-zweigeteilt/page-04.png
- label: Seite 5
  src: /templates/flyer-a6-hochformat-zweigeteilt/page-05.png
- label: Seite 6
  src: /templates/flyer-a6-hochformat-zweigeteilt/page-06.png
---


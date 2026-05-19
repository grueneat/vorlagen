---
asset_policy:
  embedded:
  - bluesky-weiss.png
  - gruene-logo-bund-weiss-cmyk.png
  - mail-weiss.png
  - plakat-dunkel-fuer-flyer.png
  - social-media-icons-weiss.png
  - website-weiss.png
  external:
  - green-pine-trees-covered-with-fog.jpg
  - green-pine-trees-covered-with-fog.png
  - leonore-stehend-lang-retuschiert-crop.jpg
  - leonore-stehend-lang-retuschiert.jpg
  - leonore-stehend-lang-retuschiert.png
  - schwarzer-verlauf-radial.png
  shipped: []
build:
  output: template.sla
  script: build.py
brand_overrides:
- id: brand:bleed_3mm
  reason: 'IDML-imported leporello template (scaffold). The IDML''s InDesign document
    was authored with bleed=0 and build.py deliberately emits bleed_mm=0 (see the
    build.py module docstring) so the rendered PDF compares directly against the InDesign
    baseline.pdf, which itself exports trim-only. The Quickguide requires a 3mm print
    bleed; the existing IDML asset predates that requirement. Same gap class as the
    shipped sibling 26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover which carries
    the identical brand_overrides block. Resolution path: extend tools/idml_to_dsl.py
    to inject the brand-required 3mm bleed at scaffold time (deferred).'
- id: brand:image_text_overlap
  reason: 'IDML-imported leporello template (scaffold). The original InDesign layout
    deliberately overlays text on full-bleed photo backdrops and on decorative brand-color
    shapes (headline/Zitat frames over green-pine photo backgrounds and over the magenta
    Stoerer diamond) — the visual result is intentional white-text-on-photo / text-on-color.
    The brand:image_text_overlap rule cannot distinguish intentional design overlay
    from accidental clipping. Same gap class as the shipped sibling 26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover
    which carries the identical brand_overrides block. Resolution path: per-frame
    intent annotation in the rule (deferred to a separate pass).'
- id: brand:inside_page
  reason: 'IDML-imported leporello template (scaffold). The IDML spread coordinate
    system places multi-panel content (6 panels) on a single oversized canvas while
    the converter declares trim-sized pages; frames belonging to later panels register
    outside their declared page''s trim box. tools/idml_to_dsl.py preserves the source
    geometry verbatim per issue #35 P1 (baseline.pdf is the convergence target). Same
    gap class as the shipped sibling 26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover
    which carries the identical brand_overrides block. Resolution path: emit a true
    multi-panel spread layout from the converter so every frame registers inside one
    of the panel pages (deferred).'
- id: brand:line_spacing_0.9
  reason: 'IDML-imported leporello template (scaffold). The original InDesign ParagraphStyles
    (the idml/* family plus the ci/* family) carry leading values that do NOT follow
    the Quickguide 0.9-factor convention (14 styles affected, e.g. ci/default linesp=13
    fontsize=12 = 1.08x; ci/headline-ultra linesp=23 fontsize=27 = 0.85x; idml/no-paragraph-style
    linesp=17.4 fontsize=12 = 1.45x). tools/idml_to_dsl.py emits these verbatim from
    the IDML Resources/Styles.xml; changing them would diverge from the InDesign-authored
    baseline.pdf which is the convergence target (issue #35 P1). Same gap class as
    the shipped sibling 26-03-leporello-z-falz-99x210-6-seitig-gruenes-cover which
    carries the identical brand_overrides block. Resolution path: per-template tune
    pass to reconcile leading against the brand convention (deferred).'
format: A4
id: falzflyer-z-falz-6-seitig-portraet
description: Sechsseitiger Z-Falz-Faltflyer mit Porträtfoto-Cover. Für die Vorstellung
  von Kandidat:innen.
variant_label: Z-Falz 6-seitig · Porträt-Cover
category_label: Falzflyer
category: falzflyer
idml_source: ../../../../../originals/26-03-Leporello z-Falz 99x210 6-seitig Portrait
  Ordner/26-03-Leporello z-Falz 99x210 6-seitig Portrait.idml
previews_for_sla: d2404e48f483060feedf48a699232c0b1bb5da598905b7cc2a559a62e7cde137
title: Falzflyer Z-Falz 6-seitig – Porträt-Cover
version: 0.1.0
build_py_sha256: 42e086d5d1a710c789b875b961301ac470595e43c5001d12b2fbe5c11a7d1ecb
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/falzflyer-z-falz-6-seitig-portraet/template.sla
  pdf: /templates/falzflyer-z-falz-6-seitig-portraet/preview.pdf
_previews:
- label: Seite 1
  src: /templates/falzflyer-z-falz-6-seitig-portraet/page-01.png
- label: Seite 2
  src: /templates/falzflyer-z-falz-6-seitig-portraet/page-02.png
---


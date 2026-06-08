---
asset_policy:
  embedded:
  - gruene-logo-bund-weiss-cmyk.png
  external:
  - 2026-03-leonore-fuer-flyer.png
  - green-pine-trees-covered-with-fog.jpg
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
    places multi-panel content (6 panels) on a single oversized canvas while the converter
    declares trim-sized pages; frames belonging to later panels register outside their
    declared page''s trim box (worst overshoots 3.0-151.0mm). tools/idml_to_dsl.py
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
id: flyer-a6-querformat-gruenes-cover
description: A6-Flyer im Querformat mit durchgehend grünem Marken-Cover. Für textbetonte
  Botschaften.
variant_label: Querformat · Grünes Cover
category_label: Flyer
category: flyer
idml_source: ../../../../originals/26-03-Flyer A6 Querformat gruenes Cover Ordner/26-03-Flyer
  A6 gruenes Cover.idml
previews_for_sla: d74bf4b7259c34ab0e222a641c2ddc51cfe6a5cc69bbc94b934ac74ab03a1ec4
title: Flyer A6 Querformat – Grünes Cover
version: 0.1.0
build_py_sha256: d05a1ef6e0ff9c08c04a05600c87222b35eb5772192a0012903597b43467fcb5
_downloads:
- label: Burgenland
  bundesland: bgld
  sla: /templates/flyer-a6-querformat-gruenes-cover/impressum/bgld.sla
- label: Kärnten
  bundesland: ktn
  sla: /templates/flyer-a6-querformat-gruenes-cover/impressum/ktn.sla
- label: Niederösterreich
  bundesland: noe
  sla: /templates/flyer-a6-querformat-gruenes-cover/impressum/noe.sla
- label: Oberösterreich
  bundesland: ooe
  sla: /templates/flyer-a6-querformat-gruenes-cover/impressum/ooe.sla
- label: Salzburg
  bundesland: sbg
  sla: /templates/flyer-a6-querformat-gruenes-cover/impressum/sbg.sla
- label: Steiermark
  bundesland: stmk
  sla: /templates/flyer-a6-querformat-gruenes-cover/impressum/stmk.sla
- label: Tirol
  bundesland: tirol
  sla: /templates/flyer-a6-querformat-gruenes-cover/impressum/tirol.sla
- label: Vorarlberg
  bundesland: vbg
  sla: /templates/flyer-a6-querformat-gruenes-cover/impressum/vbg.sla
- label: Wien
  bundesland: wien
  sla: /templates/flyer-a6-querformat-gruenes-cover/impressum/wien.sla
_preview_pdf: /templates/flyer-a6-querformat-gruenes-cover/preview.pdf
_previews:
- label: Seite 1
  src: /templates/flyer-a6-querformat-gruenes-cover/page-01.png
- label: Seite 2
  src: /templates/flyer-a6-querformat-gruenes-cover/page-02.png
- label: Seite 3
  src: /templates/flyer-a6-querformat-gruenes-cover/page-03.png
- label: Seite 4
  src: /templates/flyer-a6-querformat-gruenes-cover/page-04.png
- label: Seite 5
  src: /templates/flyer-a6-querformat-gruenes-cover/page-05.png
- label: Seite 6
  src: /templates/flyer-a6-querformat-gruenes-cover/page-06.png
---

# So nutzt du die Flyer-Vorlage

Ein A6-Flyer zum Verteilen — Cover plus Innenseiten.

## Schritt für Schritt

1. **Vorlage öffnen** — `template.sla` mit [Scribus](https://www.scribus.net)
   öffnen (kostenlos für Windows, macOS und Linux). Die oben verlinkten
   Schriften vorher installieren.
2. **Inhalte ersetzen** — Headline, Fließtext, Fotos und Logo austauschen. Klick
   auf einen Rahmen zeigt unten rechts seinen Namen, so erkennst du, was wofür
   gedacht ist. Die Vorschaubilder oben zeigen alle Seiten der Vorlage.
3. **Impressum prüfen** — der Impressums-Block ist gesetzlich vorgeschrieben.
   Angaben ergänzen, nicht löschen.
4. **Als PDF exportieren** — *Datei → Exportieren → Als PDF speichern*. Fertig
   für die Druckerei.

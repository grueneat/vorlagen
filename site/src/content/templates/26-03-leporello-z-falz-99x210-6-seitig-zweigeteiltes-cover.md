---
asset_policy:
  embedded:
  - bluesky-weiss.png
  - gruene-logo-bund-weiss-cmyk.png
  - mail-weiss.png
  - social-media-icons-weiss.png
  - website-weiss.png
  external:
  - 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover--ai-Social Media Icons
    weiss--0.pdf
  - 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover--ai-Social Media Icons
    weiss--1.pdf
  - 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover--ai-Social Media Icons
    weiss--2.pdf
  - green-pine-trees-covered-with-fog.jpg
  - plakat-dunkel-fuer-flyer.png
  - ziesel.jpg
  shipped: []
build:
  output: template.sla
  script: build.py
format: A4
id: 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover
idml_source: ../../originals/26-03-Leporello z-Falz 99x210 6-seitig zweigeteiltes
  Cover Ordner/26-03-Leporello z-Falz 99x210 6-seitig zweigeteiltes Cover.idml
previews_for_sla: e7dbeb9101f801f24f203c0540eb493519694c837806a4d3d419ab257da59cc2
title: 26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover
version: 0.1.0
brand_overrides:
- id: brand:line_spacing_0.9
  reason: IDML-imported template. The original InDesign ParagraphStyles (idml/headline-in-gruenem-kasten,
    idml/absatzformat-1, idml/fliesstext-auf-gruenem-hintergrund, idml/aufzaehlungen-auf-gruenem-hintergrund,
    idml/normalparagraphstyle, idml/no-paragraph-style, plus the ci/* family) carry
    leading values that do NOT follow the Quickguide 0.9-factor convention (e.g. headline-in-gruenem-kasten
    linesp=12 fontsize=12 = 1.0x; fliesstext-auf-gruenem-hintergrund linesp=16 fontsize=11
    = 1.45x; absatzformat-1 linesp=14.3 fontsize=11 = 1.3x). The converter emits these
    verbatim from the IDML Resources/Styles.xml; changing them would diverge from
    the InDesign-authored baseline.pdf which is the convergence target (issue 35 P1).
    Same gap class as the sibling v2 falzflyer.
- id: brand:font_family
  reason: 'IDML-imported template. 11 text frames inherit FONT="Times Roman" via the
    idml/no-paragraph-style and idml/normalparagraphstyle defaults that the IDML preserves
    untouched (the InDesign source never overrides them for these minor labels). The
    converter cannot remap these to brand fonts without changing the baseline.pdf
    convergence target. Resolution path: extend tools/idml_to_dsl.py font resolution;
    tracked alongside issue 37 as a converter completeness gap. Same gap class as
    the sibling v2 falzflyer.'
- id: brand:bleed_3mm
  reason: IDML-imported template. The IDML's InDesign document was authored with bleed=0;
    converter respects the source page geometry. The baseline.pdf (convergence target)
    also has bleed=0. Adjusting bleed would force a deviation from the InDesign-authored
    output. Brand-team review pending — the canonical Quickguide requires 3mm but
    the existing IDML asset predates that requirement. Same gap class as the sibling
    v2 falzflyer.
- id: brand:inside_page
  reason: IDML-imported template. Multiple frames in the original IDML extend slightly
    outside the trim box (u1ae background polygon with 1.82mm overshoot; u514, u3a2,
    and several decorative shapes with similar overshoot). These were intentional
    InDesign- side bleed/extension marks in the source asset. The converter preserves
    the source geometry verbatim per issue 35 P1 (baseline.pdf is the convergence
    target). Same gap class as the sibling v2 falzflyer.
- id: brand:image_text_overlap
  reason: IDML-imported template. The IDML places impressum text and other white-on-green
    text overlapping the green page-background polygon by design — the visual result
    is white-text-on-green, visually correct against baseline.pdf. The brand:image_text_overlap
    rule cannot distinguish "text on a colored polygon backdrop" (intentional) from
    "text on a raster image" (overlap concern). Same gap class as the sibling v2 falzflyer.
ci_overrides:
  non_ci_styles:
  - idml/absatzformat-1
  - idml/aufzaehlungen-auf-gruenem-hintergrund
  - idml/fliesstext-auf-gruenem-hintergrund
  - idml/headline-in-gruenem-kasten
  - idml/no-paragraph-style
  - idml/normalparagraphstyle
  non_ci_colors: []
  non_ci_layers: []
category: falzflyer
category_label: Falzflyer
variant_label: Z-Falz 6-seitig (zweigeteiltes Cover)
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/template.sla
  pdf: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/preview.pdf
_previews:
- label: Seite 1
  src: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/page-01.png
- label: Seite 2
  src: /templates/26-03-leporello-z-falz-99x210-6-seitig-zweigeteiltes-cover/page-02.png
---


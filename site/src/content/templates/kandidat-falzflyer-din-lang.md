---
id: kandidat-falzflyer-din-lang
version: 0.1.0
title: Kandidat-Falzflyer DIN-lang
format: A4
orientation: landscape
pages: 2
preview_dpi: 100
audience:
- kandidat
- bezirksgruppe
- ortsgruppe
description: '3-fach gefalzter A4-quer-Kandidaten-Flyer (Zickzackfalz, 6 Panele à
  99×210 mm). Cover (Portrait + Name + Slogan) → Teaser → Closer (Wahlkreuz auf Dunkelgrün).
  Rückseite: 4 Themen-Module + Kontakt + Impressum.

  '
build:
  script: build.py
  output: template.sla
previews_for_sla: af443213101618b58a2fbeb3054b9931db918e8a4a69e412aabde13da49ab30e
brand_overrides:
- id: brand:line_spacing_0.9
  reason: 'Shared with all templates: CI palette ratios drift; per-template panel
    styles use slightly looser line-heights (e.g. teaser-body 14/11=1.27x) to keep
    narrow 99mm panels readable. Brand-team review pending.'
- id: brand:image_text_overlap
  reason: P6 vollflächig Dunkelgrün design intentionally places Impressum (h=8) directly
    below the P6 Logo at the panel footer; rule reports a 38×2mm partial overlap (Impressum
    top edge crosses Logo bottom edge) which is intentional band-edge bleed for tight
    footer composition. Cannot be fixed by frame separation without breaking the V1
    footer rhythm.
- id: brand:band_consistency
  reason: V1 still has minor ParaStyle band drift on the eyebrow Caps; needs per-template
    body_block_margins spec authoring. Deferred to follow-up issue per RESEARCH.
ci_overrides:
  non_ci_styles:
  - falzflyer/cand-name
  - falzflyer/slogan
  - falzflyer/slogan-on-green
  - falzflyer/teaser-headline
  - falzflyer/teaser-body
  - falzflyer/thema-headline
  - falzflyer/thema-body
  - falzflyer/themen-eyebrow
  - falzflyer/top-title
  - falzflyer/quote-on-green
  - falzflyer/closer-headline
  - falzflyer/closer-datum
  - falzflyer/closer-url
  - falzflyer/contact-headline
  - falzflyer/contact-body
  - falzflyer/impressum
  non_ci_colors:
  - Falz
  non_ci_layers:
  - Falz
slots:
  p1_top_band:
    type: shape
    description: Universal Top-Band Dunkelgrün (105×31, +3mm bleed)
    anname: P1 Top-Band
  p1_logo:
    type: image
    description: Grüne wordmark white (3M = 38mm Trim-konform)
    source: shared/logos/gruene-weiss.png
    anname: P1 Logo Grüne (weiss)
  p1_kandidat_portrait:
    type: image
    description: Kandidat-Portrait (87×100, INJECT_MAP -> portrait_maria)
    optional: true
    anname: P1 Kandidat-Portrait
  p1_name_card:
    type: shape
    description: Name-Card vollbleed bottom Dunkelgrün polygon
    anname: P1 Name-Card
  p1_kandidat_name:
    type: text
    description: Kandidat-Name (24pt Vollkorn Italic White on Name-Card)
    anname: P1 Kandidat-Name
  p1_slogan:
    type: text
    description: Slogan (14pt Gotham Bold Gelb on Dunkelgrün)
    anname: P1 Slogan
  p2_top_band:
    type: shape
    description: Top-Band Dunkelgrün (99×31 inner)
    anname: P2 Top-Band
  p2_top_title:
    type: text
    description: Top-Title "Mein Plan" (Caps Bold White 11pt)
    anname: P2 Top-Title
  p2_teaser_headline:
    type: text
    anname: P2 Teaser-Headline
  p2_body_backing:
    type: shape
    description: Hellgrün card backing for teaser body
    anname: P2 Body-Backing
  p2_teaser_body:
    type: text
    anname: P2 Teaser-Body
  p3_hintergrund:
    type: shape
    description: Dunkelgrün vollflächig polygon (P3 grüne-Klammer pair)
    anname: P3 Hintergrund
  p3_top_title:
    type: text
    description: Top-Title "Wahltag" (Caps Bold Gelb 11pt — fcolor override)
    anname: P3 Top-Title
  p3_wahlkreuz:
    type: image
    description: Wahlkreuz Hero auf Dunkelgrün
    source: shared/assets/wahlkreuz.png
    anname: P3 Wahlkreuz
  p3_closer_headline:
    type: text
    description: Wahlaufruf-Headline (22pt Gotham Bold White)
    anname: P3 Closer-Headline
  p3_datum_akzent:
    type: text
    description: Datum als Vollkorn-Italic-Gelb-Akzent
    anname: P3 Datum-Akzent
  p3_url:
    type: text
    description: Kandidaten-URL
    anname: P3 URL
  falz_x99_front:
    type: shape
    anname: Falz x=99 (Front)
  falz_x198_front:
    type: shape
    anname: Falz x=198 (Front)
  p4_top_band:
    type: shape
    description: Top-Band Dunkelgrün (105×31 outer)
    anname: P4 Top-Band
  p4_top_title:
    type: text
    description: Top-Title "Themen 1·2"
    anname: P4 Top-Title
  p4_thema1_eyebrow:
    type: text
    anname: P4 Thema 1 — Eyebrow
  p4_thema1_headline:
    type: text
    anname: P4 Thema 1 — Headline
  p4_thema1_photo:
    type: image
    description: Thema 1 photo (87×44, INJECT_MAP -> themen_klimaschutz_solar)
    optional: true
    anname: P4 Thema 1 — Photo
  p4_thema_trenner:
    type: shape
    description: 3mm Hellgrün strip dividing Thema 1 / 2
    anname: P4 Thema 1·2 Trenner
  p4_thema1_body:
    type: text
    anname: P4 Thema 1 — Body
  p4_thema2_eyebrow:
    type: text
    anname: P4 Thema 2 — Eyebrow
  p4_thema2_headline:
    type: text
    anname: P4 Thema 2 — Headline
  p4_thema2_photo:
    type: image
    description: Thema 2 photo (87×44, INJECT_MAP -> themen_soziales_kaffeehaus)
    optional: true
    anname: P4 Thema 2 — Photo
  p5_top_band:
    type: shape
    description: Top-Band Dunkelgrün (99×31 inner)
    anname: P5 Top-Band
  p5_top_title:
    type: text
    description: Top-Title "Themen 3·4"
    anname: P5 Top-Title
  p5_thema3_eyebrow:
    type: text
    anname: P5 Thema 3 — Eyebrow
  p5_thema3_headline:
    type: text
    anname: P5 Thema 3 — Headline
  p5_thema3_photo:
    type: image
    optional: true
    anname: P5 Thema 3 — Photo
  p5_thema_trenner:
    type: shape
    description: 3mm Hellgrün strip dividing Thema 3 / 4
    anname: P5 Thema 3·4 Trenner
  p5_thema3_body:
    type: text
    anname: P5 Thema 3 — Body
  p5_thema4_eyebrow:
    type: text
    anname: P5 Thema 4 — Eyebrow
  p5_thema4_headline:
    type: text
    anname: P5 Thema 4 — Headline
  p5_thema4_photo:
    type: image
    description: Thema 4 photo NEW V1 (87×44, INJECT_MAP -> themen_wirtschaft_handwerk)
    optional: true
    anname: P5 Thema 4 — Photo
  p6_hintergrund:
    type: shape
    description: Dunkelgrün vollflächig polygon (P6 grüne-Klammer pair)
    anname: P6 Hintergrund
  p6_top_title:
    type: text
    description: Top-Title "Kontakt"
    anname: P6 Top-Title
  p6_kontakt_headline:
    type: text
    anname: P6 Kontakt-Headline
  p6_adresse:
    type: text
    description: 2-col cell row 1 left (mirrored around 247.5)
    anname: P6 Adresse
  p6_telefon:
    type: text
    description: 2-col cell row 1 right
    anname: P6 Telefon
  p6_email:
    type: text
    description: 2-col cell row 2 left
    anname: P6 Email
  p6_sprechtag:
    type: text
    description: 2-col cell row 2 right
    anname: P6 Sprechtag
  p6_qr_mitmachen:
    type: image
    description: QR-Code mitmachen (24×24 mirror axis 247.5)
    optional: true
    anname: P6 QR-Code (mitmachen)
  p6_qr_caption_mitmachen:
    type: text
    description: QR-Caption "MITMACHEN" (themen-eyebrow fcolor=White)
    anname: P6 QR-Caption (mitmachen)
  p6_qr_termine:
    type: image
    optional: true
    anname: P6 QR-Code (termine)
  p6_qr_caption_termine:
    type: text
    anname: P6 QR-Caption (termine)
  p6_logo:
    type: image
    description: Grüne wordmark white footer (38×34 = 3M Trim-konform)
    source: shared/logos/gruene-weiss.png
    anname: P6 Logo Grüne (weiss)
  p6_impressum:
    type: text
    anname: P6 Impressum
  falz_x99_back:
    type: shape
    anname: Falz x=99 (Back)
  falz_x198_back:
    type: shape
    anname: Falz x=198 (Back)
example_pages:
- num: 1
  label: 'Front: Cover (P1) — Teaser (P2) — Closer (P3)'
- num: 2
  label: 'Back: Themen 1+2 (P4) — 3+4 (P5) — Kontakt (P6)'
samples:
- id: kandidat-portrait
  description: Kandidat-Portrait fürs Cover (Codex DALL-E generated, 768x1024)
preflight:
  bleed_mm: 3
  fold_mm:
  - 99
  - 198
  cmyk_only: true
  min_image_dpi: 300
_downloads:
- label: Vollständig (SLA + PDF)
  sla: /templates/kandidat-falzflyer-din-lang/template.sla
  pdf: /templates/kandidat-falzflyer-din-lang/preview.pdf
_previews:
- label: Seite 1
  src: /templates/kandidat-falzflyer-din-lang/page-01.png
- label: Seite 2
  src: /templates/kandidat-falzflyer-din-lang/page-02.png
---

# Kandidat-Falzflyer DIN-lang (V1 "Falz-Rhythm")

A4 quer (297×210 mm), 3-fach Zickzackfalz, 6 Panele à 99×210 mm.
Front: Cover (P1) — Mein Plan (P2) — Wahltag (P3).
Back: Themen 1·2 (P4) — Themen 3·4 (P5) — Kontakt (P6).

Spec: `templates/_specs/kandidat-falzflyer-din-lang.md`.

## V1 deltas vs V0 (Issue #21)

V1 "Falz-Rhythm" is the **fifth and final** template in the V1 rollout
sequence (#15: #17→#18→#19→#20→#21). It absorbs every pattern from the
preceding four V1s and adds the universal Top-Band system + grüne-Klammer
mirror + P4/P5 themen sub-layout symmetry + P6 2-Spalten Kontakt.

### Layout deltas

- **3 logo resizes** (T01–T02): P1 Logo 20×18 → 38×22, P6 Logo 17×15 →
  38×34, P2 Logo (klein) deleted entirely. White wordmark
  (`shared/logos/gruene-weiss.png`) replaces V0's `gruene-logo-bund-dunkel.png`.
- **4 universal Top-Band polygons** (P1, P2, P4, P5): 31mm Dunkelgrün
  band at top of each panel; outer panels (P1, P4) extend +3mm into bleed
  left and +3mm overshoot right. Inner panels (P2, P5) flush both folds.
  P3 + P6 are vollflächig Dunkelgrün (the polygon IS the band).
- **P1 Name-Card** (NEW): vollbleed bottom Dunkelgrün polygon (134..213,
  +3mm bleed) holding Kandidat-Name (White) + Slogan (Gelb).
- **P2 Body-Backing** (NEW): Hellgrün card (99×144) under Teaser-Body;
  body fcolor mutated Black→White for legibility on Hellgrün.
- **P3 vollflächig** (V0 had this; V1 adds Top-Title "Wahltag" with
  fcolor='Gelb' override + repositions Closer-Headline/Datum/URL for
  rhythm consistency).
- **P4/P5 themen restructure**: 4 Eyebrow Caps (`THEMA 0X`) + 4 Headlines
  + 4 Photos (87×44 native 1.5:1 — fixes V0's 87×24 halb-leer Streifen)
  + 2 Bodies (Thema 1, Thema 3 only — Thema 2/4 deleted, photo carries
  the message). 3mm Hellgrün Trenner divides each panel.
- **P5 Thema 4 photo** is NEW V1 (asset `themen_wirtschaft_handwerk` in
  central library).
- **P6 vollflächig Dunkelgrün**: Top-Title "Kontakt" + Headline + 4
  Kontakt-Cells (Adresse / Telefon / Email / Sprechtag) in 2-Spalten
  layout symmetric around `AXIS_P6_CENTER_X = 247.5` (= 198 + 99/2).
  QRs resized 30→24mm and repositioned to mirror around the same axis.
  Footer logo 38×34 + Impressum h 60→8 fcolor=White.

### ParaStyle migration

- **10 in-place mutations**: 9 align flips + 1 fcolor-only on `teaser-body`.
- **4 NEW parallel styles**: `slogan-on-green`, `quote-on-green`,
  `top-title`, `themen-eyebrow`.
- **2 KEPT unchanged**: `teaser-headline`, `thema-headline` (both
  align=0 for redaktionellen Charakter).

Total: 12 V0 → 16 V1 falzflyer/* styles registered.

### CONSTRAINTS

22-entry V1 list (was 9 in V0): Top-Band uniformity (3), grüne-Klammer
P3↔P6 (1), P4 themen mirror (5), P5 themen mirror (5), cross-panel
photo size (1), P6 2-Spalten symmetry (4), logo Print-Soll (1), style
consistency (2).

### INJECT_MAP (post-#24 idiom)

5 photo frames defined in `build_template()` without inline-image-data;
`build_preview()` injects via `library.inject_into_frame(frame, img,
target_w_mm=frame.w_mm, target_h_mm=frame.h_mm)` reading LIVE frame
dimensions (no hardcoded targets).

```python
INJECT_MAP = {
    "P1 Kandidat-Portrait":  "portrait_maria",
    "P4 Thema 1 — Photo":    "themen_klimaschutz_solar",
    "P4 Thema 2 — Photo":    "themen_soziales_kaffeehaus",
    "P5 Thema 3 — Photo":    "themen_bildung_volksschule",
    "P5 Thema 4 — Photo":    "themen_wirtschaft_handwerk",
}
```

## M-Basis decision rationale

Per Quickguide §"Logo-Größen": `M = 0.06 * min(trim_w, trim_h)`. For
DIN-lang Zickzackfalz: `min(297, 210) = 210 → M = 12.6 → 3M = 37.8 mm`.

The brand rule `brand:logo_size_3M` lives in
`tools/sla_lib/builder/brand_constraints.py:262` and is **already**
trim-konsistent — V0 had a misleading code-comment in `build.py:195-199`
suggesting "kurze Kante=105 → 18.9 mm" (panel-based, NOT trim-based).
V0 logos were 20mm / 16mm / 17mm (panel-based "tolerance"); all three
violate the actual trim-based 3M rule.

**No tool/library code change in #21:**
- `tools/check_ci.py` was untouched (RESEARCH correction #1: it has
  zero logo-/alignment-logic; ISSUE.md framing was wrong).
- `tools/sla_lib/builder/brand_constraints.py` was untouched (RESEARCH
  locked decision #1: rule already correct).

What changed: the misleading `build.py` header comment was rewritten
(T01); `meta.yml.brand_overrides` entry `brand:logo_size_3M` was
removed (T01); 3 logo frames were resized to soll (T02).

Cross-validated: parametric M-Basis-rule regression test
(`test_m_basis_rule_all_v1_templates`) runs the rule against all 5 V1
templates — 0 violations on each.

See: `shared/brand/DESIGN-SYSTEM-BRIEF.md` §"Logo Print-Soll".

## Visual rendering of P1 + P6 logos

The 3.5:1 white wordmark (`shared/logos/gruene-weiss.png`, 413×118 RGB)
fits inside frames of differing aspect:
- **P1**: 38×22 mm frame → wordmark auto-fits to width (10.86mm h), 5.6mm
  padding above + below within the Top-Band y range.
- **P6**: 38×34 mm frame → wordmark auto-fits to width (10.86mm h),
  11.6mm padding above + below within the footer zone.

Same treatment as #20 infostand-tent-card (`brand:image_fills_frame`
fires WARNING for these letterbox padding scenarios — accepted as a
brand-decision; it would require either tighter frames or a square-aspect
wordmark variant to silence).

## Asset library bindings

5 INJECT_MAP photo IDs (manifest at `shared/sample-images/manifest.yml`):

- `portrait_maria` (Codex AI-generated, watermark "Symbolfoto — KI-generiert")
- `themen_klimaschutz_solar`
- `themen_soziales_kaffeehaus`
- `themen_bildung_volksschule`
- `themen_wirtschaft_handwerk` (already in central library — no copy needed)

All assets carry the `Symbolfoto — KI-generiert` watermark band; cropped
variants get the band re-applied via `library.crop_for_frame()`
(R-WATERMARK-CROP).

Local QR samples (template-specific per RESEARCH locked #9):
- `samples/qr-mitmachen.png` (P6 QR-Code mitmachen)
- `samples/qr-termine.png` (P6 QR-Code termine)

## Build

```bash
# Build template.sla (clean — no photos, structural_check / smoke fodder)
python3 templates/kandidat-falzflyer-din-lang/build.py

# Regen template.sla + preview.pdf + page-NN.png + meta.yml SHA + site mirror
bin/render-gallery kandidat-falzflyer-din-lang --skip-visual-diff
```

## Verification

```bash
# Structural check (22 CONSTRAINTS + 11 brand rules; 3 overrides)
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang

# Cross-template regression
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all

# Smoke test (15 V1 assertions)
PYTHONPATH=tools python3 -m unittest templates._smoke.test_kandidat_falzflyer_din_lang

# Geometry invariants (21 V1 invariants)
PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_kandidat_falzflyer_geometry

# All sla_lib tests (754 total)
python3 -m unittest discover tools/sla_lib/tests

# Verify SHA freshness
bin/check-stale-previews
```

All exit 0 in V1 final state.

## Open questions / deferred

- **Pull-Quote frame**: `falzflyer/quote-on-green` style is registered
  but no frame is emitted in V1 (RESEARCH pitfall 15 — deferred).
- **`falzflyer/contact-label` Caps-row variants**: deferred per RESEARCH
  pitfall 16; current V1 does not need a separate label style (4 cells
  use `contact-body` directly).
- **P6 Impressum on Dunkelgrün at 6pt**: readability check pending; if
  print proof shows poor legibility, consider 7pt + linesp 9.
- **brand_overrides cleanup remainders**: `image_text_overlap` was
  RESTORED empirically (V1 P6 vollflächig design intentionally places
  Impressum directly below P6 Logo footer; 38×2mm partial overlap is
  intentional band-edge bleed). `line_spacing_0.9` and `band_consistency`
  remain shared-template overrides per RESEARCH.

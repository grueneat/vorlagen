# Review Notes — 26-03-flyer-a6-hochformat-portrait

## What this template is

A **6-page A6 portrait flyer** (105 x 148 mm trim) for Die Grünen. Source:
`26-03-Flyer A6 Hochformat Portrait.idml` — a 4-spread document: spreads 1
and 4 are single-page (cover, back), spreads 2 and 3 are facing-pages spreads
with 2 pages each (6 pages total). Page 1 cover (three-line headline + Störer
badge + Gewessler portrait photo), pages 2-5 inner content, page 6 a quote
page on a dark crumpled-paper background.

## Latest pass — combined image + squiggle re-render (2026-05-18)

This template was re-imported again to pick up the shared squiggle fixes that
landed after the first image re-render: yellow-filled squiggle polygons
(`fill='Gelb'`, CMYK Y=100) and squiggle word re-anchoring. The converter now
writes `templates/<slug>/squiggle_anchors.yml` binding each squiggle Polygon
to the word it underlines; the `squiggle_realign` playbook + the
`squiggle_alignment_audit` keep each squiggle tracking its word across
Scribus's different line-wrap.

### Squiggle audit — before vs after

| Audit | Fresh re-import (before) | After tune loop (after) |
|-------|--------------------------|-------------------------|
| `squiggle_alignment_audit` | `ok: false` — 7 of 8 squiggles off their word: u11e3 2.06mm, u11e4 1.94mm, u11e2 1.94mm, u126c 1.94mm, u126e 1.94mm, u1286 13.08mm, u1269 4.99mm | `ok: true`, **0 issues** — every squiggle drift ≤0.68mm |

The `squiggle_realign` playbook re-anchored all 8 squiggles in build.py
(8 `# playbook squiggle_realign.py:` markers). Verified VISUALLY against
baseline.pdf, page by page:

- **Page 1** — yellow brush band behind "dreizeilige" (yellow Vollkorn-italic
  headline line). Matches baseline.
- **Page 2** — yellow loop around "in et", yellow underline under
  "Lia vellam". Match baseline.
- **Page 3** — yellow underline under "auch" (headline) and under "vellaccum"
  (first bullet). Match baseline.
- **Page 4** — yellow underline under "volor re doleceat laciisci nectur" and
  yellow loop around "Nam". The "Nam" squiggle moved ~13mm down because the
  word "Nam" itself drifted down under Scribus's wider body-text wrap; the
  squiggle correctly follows the word (post-fix drift 0.0mm).

All 8 squiggles render YELLOW. No squiggle is black; no squiggle is off its
word.

## First re-render pass — image-fidelity

This template was re-imported to pick up the shared CMYK->sRGB and
geometry-derived aspect-fill crop fixes (commit `de96b7c`). The earlier
overnight scaffold's `build.py` was regenerated from the fixed converter, as
intended. The Stage-2 tune nudges from the overnight run were dropped by the
re-import and the `bin/tune-render` -> `bin/tune-fix` loop was re-run.

## Re-import outcome — GREEN (Stage-1 gate passes)

`bin/idml-import --reimport --scaffold-only` completed; the Stage-1 inventory
gate passes; `build.py` runs clean and renders all 6 pages. Reaching GREEN
required four converter / tooling fixes — all in Stage 1, where converter and
gate edits are permitted. They are catalogued in `TOLERANCE_LOG.md` (R1-R4);
in brief:

1. **`inventory_extract.py` crop on-disk check (R1).** The de96b7c crop fix
   emits geometry-derived crops into a `crops/` subdir and build.py references
   `crops/<name>-<uXXX>.png`. The Stage-1 gate's "every Link basename on disk"
   rule mis-flagged the crop as missing because `_join_assets` stamped every
   build.py-only asset `on_disk=False`. Now it resolves the `image=` path and
   checks the file. STAGE-1 GATE FAILURE cleared.
2. **Group-aware page routing (R2).** `_extract_anchors` on a Group returns
   only the first child's PathGeometry. Group `u12e3` (the green "Kasten"
   headline + body) routed to PDF page 5 by first-child anchors; its true leaf
   union is on PDF page 4. In the new page-by-page render model the mis-routed
   group landed at x=-85mm (off the page-5 canvas) and all 30 green-box words
   were silently dropped. New `_item_page_local_bbox_pt` routes a Group by the
   union of its leaf descendants' page-local bboxes.
3. **Spread-spanning background on every page (R3).** The full-spread green
   background `u11e1` (216mm wide) belongs to both pages of facing-pages
   spread u11d. The page-by-page model emitted it on PDF page 2 only, leaving
   PDF page 3 white (white text on no background = invisible, 21 words lost).
   `_pages_overlapped_by_item` now emits a >=60%-coverage spanning fill on
   every page it covers, with a `_p<idx>` anname suffix on non-owner pages.
4. **`visual_diff` 1px raster-rounding tolerance (R4).** A <=2px
   baseline/preview size delta now crops to the common extent instead of hard
   -erroring the `visual_diff_regions` audit phase.

Effect of R2 + R3: `text_render_audit` went from **30 missing words -> 2**,
preview word count 312 -> 341 (baseline 343). Pages 3 and 4 now render their
full content (green background + green Kasten + text).

## Tune outcome — RESIDUAL (preflight not green)

`bin/tune-render` -> `bin/tune-fix` ran. The `y_mm_shift` playbook entered the
same documented 2-cycle limit cycle on several body frames (drift 253<->255)
and could not converge; no new per-template numeric override was applied. The
residual is accepted per the re-render gate policy. No `brand_overrides`,
`non_ci_*`, or `TOLERANCES.yml` numeric growth was required.

## IMAGE AUDIT — before (overnight) vs after (this re-render)

This re-render exists to verify the de96b7c image fixes landed. They did.

| Audit | Overnight run | This re-render |
|-------|---------------|----------------|
| `image_content_audit` | **3 broken** — u1164 (radial), u1260 (pine), ubc2 (plakat) | **1 broken** — only ubc2 |
| `image_frame_visibility_audit` | **2 invisible** — u116b, u1260 | **0 invisible**, 1 faint (u116b) |
| `visual_diff_regions` worst regions | image-driven (pine / radial blank or discoloured) | text-driven (line-wrap) + residual ICC colour; no pine / Gewessler / radial region |

Frame-by-frame after the fix:

- **u115d (Gewessler portrait, CMYK JPEG)** — was a CMYK JPEG that Scribus
  cannot render (blank). Now converted ICC-aware to PNG and aspect-fill
  cropped: mean_delta 4.1 RGB, classification **ok**. Page 1 renders the
  portrait correctly.
- **u1164 (radial gradient, PSD)** — mean_delta 6.0, **ok** (was broken).
- **u1260 (pine forest, JPEG)** — mean_delta 7.1, visibility_ratio 1.09,
  **ok** (was broken / invisible). Page 5 renders the pine photo correctly.
- **ubc2 (dark "Plakat dunkel" PSD, page 6)** — renders the correct
  crumpled-paper texture and is NOT blank (visibility_ratio 1.02). Still
  flagged `broken` by `image_content_audit` via `hist_divergence` 0.227 — a
  residual CMYK->sRGB green-tone shift (mean_delta 12.6 RGB). This is an
  intrinsic ICC colour delta, NOT a CMYK-blank regression: the de96b7c fix
  cleared the blank/discoloured state, the green texture is present.
  Accepted as `scribus-engine` ICC residual, not a missing-fix regression.
- **u116b (inline DIE GRUENEN logo)** — faint (white-on-transparent RGBA
  SCALETYPE). Pre-existing documented Scribus 1.6.x bug; not a regression.

Verdict: the CMYK + crop fixes landed cleanly on 3 of the 4 raster frames;
the 4th (ubc2) renders correct content with a residual ICC tone shift. No
CMYK or photo frame is blank or broken-content anymore.

## Residual drift (final preflight)

| Audit | Issues | Status |
|-------|--------|--------|
| `text_position_audit_structural` | 232 large drifts (>5pt) | accepted — cross-renderer line-wrap divergence (cap 260; `severity: structural` keeps preflight red by design) |
| `text_position_audit_jitter` | 23 sub-perceptible drifts (≤5pt) | tolerated this pass — cosmetic, cap 30, same wrap class (TOLERANCES T1) |
| `text_render_audit` | 0 | green — all baseline text renders |
| `systematic_text_audit` | 9 frames | tolerated — y_mm_shift oscillation (cap 12) |
| `squiggle_alignment_audit` | 0 | **green** — all 8 squiggles on their word, yellow |
| `image_content_audit` | 1 broken (ubc2) | tolerated — ICC tone shift, content present (cap 2) |
| `image_frame_visibility_audit` | 1 faint (u116b) | accepted — pre-existing logo SCALETYPE bug |
| `visual_diff_regions` | 60 hot regions | tolerated — text-wrap + ICC derivative (cap 70); worst regions all text-row driven |
| `image_audit` | 39 vector-path delta | tolerated — ICC derivative (cap 45) |
| `inventory` | 1 dropped (u1152) | tolerated — off-page registration mark (cap 1) |
| `per_region_regression` | 0 | green — no frame regressed from the squiggle re-anchoring |
| green | asset_extraction, asset_policy, external_asset_substitution, font_audit, run_style_audit, region_color | — |

**Final preflight: `ok: false`** — the single un-tolerated failing audit is
`text_position_audit_structural` (232 issues). Its tolerance is deliberately
`severity: structural`: it documents the residual but does NOT flip preflight
green, because >5pt drift is visible. This is the documented accepted residual
for the batch — cross-renderer line-wrap divergence, not a converter bug.

### Impressum 2-line wrap (text_render_audit residual)

The three rotated -90deg 6pt "Impressum: xxxxxx" edge frames (u11fd, u126f,
u12fb) wrap to two lines — "Impressu" + "m: xxxxxx". **No text is lost** —
every character renders, the string is split across two lines. Root cause:
the converter now emits the geometrically-correct un-rotated frame extent
(53.4 x 10 mm) and the rotated non-empty-TextFrame W/H swap in
`tools/sla_lib/builder/primitives.py` (de96b7c) then yields a 10mm text-flow
width, forcing the wrap. `primitives.py` is a forbidden path for Stage 2.
Logged as a follow-up for the converter/primitives swap reconciliation.

## Known issues — NOT regressions

- **Cross-renderer line-wrap text drift** (232 `text_position_audit_
  structural` + 23 `text_position_audit_jitter` drifts) — Scribus vs InDesign
  font-metric / hyphenation engine difference. Documented batch-wide.
- **DIE GRUENEN inline logo (u116b)** — white-on-transparent RGBA SCALETYPE,
  pre-existing Scribus 1.6.x bug.
- **`ubc2` ICC tone shift** — the dark "Plakat dunkel" PSD renders the correct
  green crumpled-paper texture; the `image_content_audit` `broken` flag is a
  residual CMYK->sRGB tone delta (`hist_divergence` 0.227), not a blank frame.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page 1 (cover)** — the Gewessler portrait photo renders in colour (the
   CMYK JPEG fix). The three-line headline fits inside the page.
2. **Page 3** — full green background + headline "Ich bin auch eine Headline"
   + 5-item bullet list. The green background is the spread-spanning fill
   re-emitted onto this page (R3); confirm it is not white.
3. **Page 4** — white page with the green "Kasten" box at the bottom carrying
   "Headline in einem grünen Kasten" + the "Nequia volupti..." body. This is
   the Group-routing fix (R2); confirm the green box has its text.
4. **Page 5** — the pine-forest photo renders in colour (CMYK fix); confirm
   it is not blank.
5. **Page 6** — dark crumpled-paper green background renders (slightly
   different green tone vs baseline — the accepted ubc2 ICC residual).
6. **Impressum edge text** (pages 2, 4) — the tiny rotated 6pt "Impressum:
   xxxxxx" wraps to 2 lines; all characters present, cosmetic only.
7. **Body / bullet paragraphs** — line breaks fall at slightly different
   words than the baseline; accepted cross-renderer wrap divergence — check
   the text is complete, not the exact wrap column.
8. **Yellow squiggles** — page 1 ("dreizeilige"), page 2 ("in et",
   "Lia vellam"), page 3 ("auch", "vellaccum"), page 4 ("volor re doleceat
   laciisci nectur", "Nam"). Confirm each squiggle is YELLOW and sits on its
   word. On page 4 the "Nam" squiggle sits lower than the baseline because
   the word "Nam" itself drifted down under Scribus's body-text wrap — the
   squiggle correctly tracks the word.

# Review Notes — 26-03-flyer-a6-gruenes-cover

Prose summary for human review of the Stage-1 + Stage-2 IDML import of
this template. Companion to `TOLERANCE_LOG.md` (per-tolerance detail)
and `TOLERANCES.yml` (machine-readable caps).

## What this template is

A6-Querformat flyer, "gruenes Cover" variant — a 6-page campaign flyer.
It is the Querformat sibling of the already-landed
`26-03-flyer-a6-hochformat-gruenes-cover`; same content family
(headline / subheadline cover, bullet-list body pages, candidate
portrait, impressum), rotated to landscape. Source IDML:
`originals/26-03-Flyer A6 Querformat gruenes Cover Ordner/26-03-Flyer
A6 gruenes Cover.idml` (the IDML filename omits "Querformat", which is
why the derived slug is `26-03-flyer-a6-gruenes-cover` with no
`-querformat` segment — there is no collision with the Hochformat
template).

Structure: 6 IDML pages, page-based export, 4 spreads, 16 stories,
56 text runs across 4 paragraph styles, 3 linked assets.

## Scaffold outcome — GREEN (structurally complete)

`bin/idml-import --scaffold-only` produced a structurally complete
scaffold with NO converter changes required:

- All 56 IDML text runs present in `build.py`
  (`every_idml_run_present_in_build_py: true`).
- `asset_audit.yml::ok == true` — 3/3 links resolved, none missing.
- `build.py` and the render both run clean.
- `inventory_compare` against the committed `SCAFFOLD_INVENTORY.yml`
  shows `count_deltas: []`, `delta_count: 0` — no structural
  regression.
- Four 6.3x6.3mm off-page registration-mark rectangles
  (u6f0, u6f2, u77f, u964) were deliberately skipped by the converter
  ("entirely outside page bounds — InDesign design artifact"), exactly
  as the prior batch templates handled the same artifact class.

## Tune outcome — RESIDUAL (documented, preflight stays red)

This is the expected terminal state for the flyer family — identical
to the sibling `26-03-flyer-a6-hochformat-gruenes-cover`, which also
finishes RESIDUAL with the same documented `severity: structural`
tolerances. Preflight is red because of cross-renderer line-wrap
divergence (intrinsic Scribus-vs-InDesign behaviour) and two CMYK
asset-pipeline limitations — none is a converter or build.py bug.

Build.py changes during tune (no numeric tolerance growth — all
playbook-class image-frame fixes):

- **uad7 (DIE GRÜNEN logo, page 1 cover)**: switched from
  `inline_image_data` + `scale_type=1` to a direct `image=` reference
  + `scale_type=0`. The inline PNG rendered fully transparent under
  the Scribus 1.6.x SCALETYPE=1 white-on-transparent-PNG bug; the swap
  is the documented `frame_visibility` playbook fix. The logo now
  renders — `image_frame_visibility_audit` dropped from 2 invisible
  frames to 1.
- **u906 (pine-forest photo, page 5)**: switched from `scale_type=1`
  + `local_scale`/`local_offset_mm` to `scale_type=0`. Still invisible
  (see CMYK-JPEG residual below) but now in the correct fit-to-frame
  form.
- **2x `# noinject:` markers** added above the u906 and ube9
  ImageFrame calls — both are real IDML content images, not demo
  placeholders. This cleared `external_asset_substitution_audit`.

## Tolerances granted (9 entries — see TOLERANCE_LOG.md for full detail)

All caps are current-count + small buffer; no tolerance was grown to
mask a real bug.

1. `tol:inventory-offpage-registration-marks` — `inventory`, cosmetic,
   cap 4. The four deliberately-skipped off-page artifact rectangles.
   human-review (correct converter behaviour).
2. `tol:image-audit-vector-path-delta` — `image_audit`, cosmetic,
   cap 45 (current 41). Scribus raster/ICC differences on full-bleed
   backgrounds + inline decorative vector paths. scribus-engine.
3. `tol:text-position-jitter-freetype-kerning` —
   `text_position_audit_jitter`, cosmetic, cap 26 (current 22).
   Sub-perceptible FreeType-vs-InDesign kerning jitter. scribus-engine.
4. `tol:text-position-structural-cross-renderer-wrap` —
   `text_position_audit_structural`, structural, cap 265 (current 257).
   Cross-renderer line-wrap cascade. Keeps preflight red by design.
   scribus-engine.
5. `tol:systematic-text-line-count-divergence` —
   `systematic_text_audit`, structural, cap 11 (current 10). Per-frame
   view of the same wrap divergence; sim returned no rows.
   scribus-engine.
6. `tol:text-render-cross-renderer-wrap-wordsplit` —
   `text_render_audit`, structural, cap 12 (current 12). 12 "missing"
   words all verified present in build.py — they are line-wrap
   word-splits (e.g. `impressum` -> `impressu` + `m`), not text loss.
   scribus-engine.
7. `tol:image-content-cmyk-render` — `image_content_audit`,
   structural, cap 2. u906 (CMYK JPEG, blank) + ube9 (CMYK PSD,
   discoloured). authoring-bug.
8. `tol:image-frame-visibility-cmyk-jpeg-blank` —
   `image_frame_visibility_audit`, structural, cap 1. u906 invisible
   (CMYK JPEG, Scribus cannot decode). authoring-bug.
9. `tol:visual-diff-image-size-mismatch` — `visual_diff_regions`,
   documentation-only (phase error, hard red regardless). 1px raster
   size mismatch from the printer's-marks baseline crop.
   authoring-bug / scribus-engine adjacent.

## Residual drift numbers (final render)

- `text_position_audit_structural`: 257 large (>5pt) word drifts —
  cross-renderer line-wrap. Querformat brief band is ~279; 257 sits
  just under it.
- `text_position_audit_jitter`: 22 sub-perceptible (<=5pt) drifts.
- `systematic_text_audit`: 10 frames with line-count/SPLIT divergence.
- `text_render_audit`: 12 word-split false positives.
- `image_audit`: 41 vector-path deltas.
- `image_content_audit`: 2 broken (u906, ube9).
- `image_frame_visibility_audit`: 1 invisible (u906).
- `inventory`: 4 deliberately-skipped off-page artifacts.
- `visual_diff_regions`: phase error, baseline 874x620 vs preview
  875x621 (1px each axis).

## human-review / authoring-bug items

- **human-review**: the 4 off-page registration-mark rectangles
  (`tol:inventory-offpage-registration-marks`) — correct converter
  behaviour; the audit is conservative.
- **authoring-bug**: the two CMYK assets. `u906`
  (`green-pine-trees-covered-with-fog.jpg`) is a CMYK JPEG that
  Scribus 1.6.x cannot decode — renders fully blank. `ube9`
  (`2026-03-leonore-fuer-flyer.png`) is converted from a CMYK PSD by
  the `convert -flatten` recipe, which yields non-ICC CMYK->RGB output
  that posterizes/discolours the portrait. Both are on the overnight
  brief's "known shared issues — do not re-litigate" list. The
  `visual_diff_regions` 1px mismatch is also authoring-adjacent (the
  baseline.pdf had printer's marks; the auto-crop pixel rounding does
  not match the trim-only SLA page).

## What to eyeball in preview.pdf vs baseline.pdf

- **Page 1 (cover)**: confirm the DIE GRÜNEN logo (top-right, uad7)
  now renders white-on-green. This was invisible before the tune;
  verify the swap to `image=` ref worked.
- **Page 5**: the pine-forest photo strip (u906) renders BLANK/white
  in the preview — this is the accepted CMYK-JPEG authoring-bug. The
  baseline shows the green pine photo. Expected residual, not a
  regression.
- **Page 6**: the candidate portrait (ube9) renders with distorted
  colours (posterized) vs the natural portrait in the baseline — the
  accepted CMYK-PSD conversion authoring-bug.
- **Body pages 2-4**: text content is all present and correct, but
  bullet-list and justified paragraphs wrap at slightly different
  words than the baseline, shifting downstream lines. This is the
  intrinsic cross-renderer line-wrap difference — confirm no text is
  actually missing (it is not; all 56 runs are present), only
  re-flowed.

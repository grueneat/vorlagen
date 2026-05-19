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

Re-imported on the carried converter + audit-chain fix set, then
tuned. Preflight finishes RED on the documented cross-renderer
line-wrap residual (`severity: structural` tolerances) — the expected
terminal state for the flyer family. The re-import + tune RESOLVED
several issues the prior tune had to tolerate (CMYK assets, word-split
FPs) and cut the body-text drift sharply.

Three per-frame `build.py` fixes (the closeable wins):

- **Body ParaStyle leading 16.0 -> 15.0pt** (`fliesstext-auf-gruenem-`,
  `fliesstext-auf-weissem-`, `aufzaehlungen-auf-gruenem-hintergrund`).
  The IDML flow stories carry no explicit `<Leading>` — AutoLeading
  120% — and the converter emitted ~16.0pt. The baseline.pdf body line
  gap measures a uniform 15.0pt (pixel-scan of every body column, all
  6 pages). 16->15 closes the per-line leading drift:
  `line_spacing_pixel_audit` (E4) now reports OK (was 2 frames major
  >3pt).
- **IDML `<Br>` -> `<breakline/>`** on `u6d8` / `u92e`. Stories `u6db`
  and `u931` are each ONE `ParagraphStyleRange` with 3 `<Br>` forced
  line breaks; the converter emitted them as `separator='para'` empty
  paragraphs, injecting a blank line + `space_after` at each break and
  overflowing the 2-column flow. Changed to `separator='breakline'`.
  Body text now flows continuously at 15pt like the baseline; this
  also cleared `text_render_audit` (the word-split FPs are gone).
- **`u9df` bullet LINESP 8.0 -> 15.0pt.** The IDML carries `Leading=8`
  on a trailing empty CharacterStyleRange; the converter applied it
  frame-wide, so the page-5 bullet list rendered with overlapping
  lines. Baseline renders the bullets at a 15.0pt gap.

A `min_glyph_shrink` reduction (0.98->0.94) was trialled — it closes
`line_match_audit` 24->12 but regresses `u6d8` per-region
(`line_spacing_max_drift` 6.24->16.8pt, past the committed baseline's
14.4pt). The per-region regression guard (P7) outranks the global
count, so `min_glyph_shrink` is left at the IDML-calibrated 0.98.

Image-frame fixes (carried from the prior tune, re-verified):
the DIE GRÜNEN logo (uad7) and the CMYK assets all render — the
re-import's converter fix set resolved the prior CMYK-blank /
CMYK-discolour issues. `image_content_audit`,
`image_frame_visibility_audit` and `external_asset_substitution_audit`
are all GREEN at 0 issues.

## Tolerances (see TOLERANCE_LOG.md for full detail)

Caps tightened where the re-import improved the count; one
auto-accept-conservative bump; one stale entry replaced.

- `tol:inventory-offpage-registration-marks` — `inventory`, cap 4
  (current 4). Four deliberately-skipped off-page artifact rectangles.
- `tol:image-audit-vector-path-delta` — `image_audit`, cap 45
  (current 40). Scribus raster/ICC differences on full-bleed
  backgrounds + inline decorative vector paths.
- `tol:text-position-jitter-freetype-kerning` —
  `text_position_audit_jitter`, cap 26 -> **33** (current 32).
  Sub-perceptible FreeType-vs-InDesign kerning jitter; the leading +
  breakline fixes shifted a few >5pt drifts down into this bucket.
- `tol:text-position-structural-cross-renderer-wrap` —
  `text_position_audit_structural`, cap 265 -> **180** (TIGHTENED,
  current 173). Body-frame column-overflow reflow. `severity:
  structural` keeps preflight red by design.
- `tol:systematic-text-line-count-divergence` —
  `systematic_text_audit`, cap 11 -> **5** (TIGHTENED, current 4).
- `tol:text-render-cross-renderer-wrap-wordsplit` — `text_render_audit`,
  cap 12, now UNUSED (audit passes at 0 — the breakline fix removed
  the word-split FPs).
- `tol:image-content-cmyk-render` — `image_content_audit`, cap 2, now
  UNUSED (audit passes at 0 — the CMYK assets render).
- `tol:image-frame-visibility-cmyk-jpeg-blank` —
  `image_frame_visibility_audit`, cap 1, now UNUSED (audit passes at
  0).
- `tol:visual-diff-cross-renderer-wrap-and-cmyk-tone` —
  `visual_diff_regions`, cap **55** (current 54). Replaces the stale
  `tol:visual-diff-image-size-mismatch` — the crop-rounding ERROR no
  longer occurs on this re-import; the 54 hot cells are the body-frame
  column overflow + the brief's known-acceptable glyph-width + CMYK
  tone residual.

## Residual drift numbers (final render)

- `line_match_audit`: 24 line(s) mismatched (38/62 match) — driven
  down from 45 by the leading + breakline + LINESP fixes. The 24:
  17 in the two body frames (u6d8/u92e column-overflow), 2 rotated
  Impressum sidebar (u693/u85a — Scribus rotated-frame engine limit),
  2 bullet wrap (cross-renderer), 3 sub-perceptible (1-2pt).
- `text_position_audit_structural`: 173 large (>5pt) word drifts —
  body-frame column-overflow reflow (down from 257).
- `text_position_audit_jitter`: 32 sub-perceptible (<=5pt) drifts.
- `systematic_text_audit`: 4 frames with line-count divergence (the
  two body frames + ub92 + u872 — all "wrapped differently").
- `visual_diff_regions`: 54 hot grid cells.
- `image_audit`: 40 vector-path deltas.
- `inventory`: 4 deliberately-skipped off-page artifacts.
- `line_spacing_pixel_audit`, `text_render_audit`,
  `image_content_audit`, `image_frame_visibility_audit`,
  `squiggle_alignment_audit`, `split_headline_spacing`,
  `idml_attribute_coverage`, `per_region_regression`: all OK.

## Root cause of the structural residual — authoring-bug

The two 2-column body frames (`u6d8` page 2, `u92e` page 4) have an
IDML `TextFrame` that is **undersized for its content**. The
baseline.pdf itself CLIPS ~6 lines — it renders 9 + 9 of ~24 total
lines. The converter widened the frame 53.76 -> 63.5mm to avoid
silent text loss, so the Scribus preview holds ~2 more lines per
column and the column break lands at a different word than the
clipped baseline. One wrap-point difference cascades into dozens of
downstream word-position drifts. Closing the residual fully would
require re-introducing the baseline's text loss — a worse regression.
Classification: authoring-bug (undersized IDML frame).

## What to eyeball in preview.pdf vs baseline.pdf

- **Page 1 (cover)**: DIE GRÜNEN logo (top-right) renders
  white-on-green; the headline split ("Ich bin eine" white /
  "Headline." yellow italic) and the yellow squiggle are correct.
- **Page 5**: the pine-forest photo renders; the bullet list has
  proper 15pt spacing (no overlap) after the LINESP fix.
- **Body pages 2 & 4**: all text is present (56 runs, inventory gate
  exit 0). The body wraps at slightly different words than the
  baseline and the column break diverges — the documented undersized-
  frame residual. No text is missing, only re-flowed.

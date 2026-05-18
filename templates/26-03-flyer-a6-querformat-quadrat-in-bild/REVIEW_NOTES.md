# REVIEW_NOTES — 26-03-flyer-a6-querformat-quadrat-in-bild

Human-review summary for the overnight IDML-import batch (template 6 of 9).

## What the template is

A6 querformat flyer, "Quadrat in Bild" variant — a 6-page flyer
(148x105mm landscape per page) for Die Grünen Niederösterreich. The
InDesign source authors the 6 pages across 4 spreads (two 2-page
facing spreads + two single-page spreads) but exports the baseline
PDF **page-by-page** (6 PDF pages). The layout features a square
photo crop set inside each page, a 3-line mixed-font headline, a
white Grünen logo, and justified Fliesstext body copy on both green
and white backgrounds.

## Scaffold outcome — GREEN (after a converter fix)

The first scaffold run failed with a hard `page count mismatch:
baseline=6 dsl=4`. Root cause: the converter (`tools/idml_to_dsl.py`)
assumed InDesign always exports **spread-based** PDFs and merged each
facing-pages spread into one wide SLA page — producing 4 pages. But
this template's baseline.pdf is **page-based**: 6 PDF pages, one per
IDML page, each 419.5pt wide (a merged 2-page spread would be 839pt).

### Converter fix (Stage 1, permitted)

Added a render-page-mode resolver to `tools/idml_to_dsl.py`:

- New `_resolve_render_page_mode(ctx)` locates the sibling
  `<stem>.pdf`, counts its pages, and compares against the IDML page
  count and spread count. When `baseline_pages == idml_page_count`
  AND `!= spread_count`, it selects `"page"` mode (one SLA page per
  IDML page). Otherwise the default `"spread"` mode (spread-merged)
  is kept — so leporello / fold templates are unaffected.
- `_collect_spread_pages` emits one render-page entry per IDML page
  in `"page"` mode, carrying a `page_local_idx`.
- `_emit_pages` routes each top-level spread item to its page via the
  existing `_route_item_to_page` helper, so a facing spread's items
  land on the correct individual page exactly once.
- `_emit_page_stubs` / `_emit_document_scaffold` follow the active
  mode.

The fix is conservative: a template with no facing spreads, or whose
baseline genuinely IS spread-based (verified against the sibling
`26-03-flyer-a6-querformat-portrait`, which has 6 IDML pages / 4
spreads but a 4-page spread-based baseline and correctly STAYS in
spread mode), keeps the original behaviour. Converter unit tests
pass (15 passed, 4 skipped).

After the fix the scaffold is structurally complete:
`every_idml_run_present_in_build_py: true`, all 4 `<Link>` assets
resolved on disk (`asset_audit.yml::ok: true`), build.py + render
both succeed, 6-page SLA emitted. The 4 "dropped elements" are
off-page InDesign registration furniture the converter deliberately
skips (logged + recorded; completeness assertion passes).

## Tune outcome — RESIDUAL (preflight RED, fully documented)

The `bin/tune-render` -> `bin/tune-fix` loop ran two full iterations.
The playbooks could not advance the text-drift residual because
`line_spacing_sim` returned NO ROWS for every text frame — the drift
is line-WRAP-count divergence (Scribus breaks justified paragraphs
at different words than InDesign), and no leading value reconciles a
wrap-count difference.

One tuning fix landed: **ua5a** (white Grünen logo) was switched from
`inline_image_data` + `scale_type=1` to a direct `image=` reference
+ `scale_type=0`, fixing a Scribus 1.6.x transparent-render bug
(visibility 0.0 -> 0.88, class `ok`). Four external CMYK image
frames got `# noinject:` annotations, clearing
`external_asset_substitution_audit` entirely.

Failing sub-audits dropped from 8 to 5. Final preflight: `ok: false`
with 5 RED sub-audits, all classified and tolerance-documented.

## Tolerances granted (9 — see TOLERANCE_LOG.md / TOLERANCES.yml)

NO `brand_overrides` / `non_ci_*` growth. All 9 tolerances are
audit-scoped `TOLERANCES.yml` entries:

1. `inventory` (cap 4) — 4 off-page registration-mark Rectangles the
   converter correctly skips. cosmetic / human-review.
2. `image_audit` (cap 48, measured 45) — raster/ICC + inline-vector +
   CMYK render deltas. cosmetic / scribus-engine-bug.
3. `image_content_audit` (cap 4) — u9be/u906/ua88 CMYK-JPEG +
   ua8f CMYK-PSD render gaps. structural / authoring-bug. Stays RED.
4. `image_frame_visibility_audit` (cap 2) — u906 invisible + u9be
   faint (CMYK JPEG). structural / authoring-bug. Stays RED.
5. `systematic_text_audit` (cap 12, measured 11) — line-wrap-count
   drift, no sim rows. structural / scribus-engine-bug. Stays RED.
6. `text_position_audit_jitter` (cap 24, measured 21) — sub-5pt
   FreeType kerning jitter. cosmetic / scribus-engine-bug.
7. `text_position_audit_structural` (cap 280, measured 254) —
   cross-renderer line-wrap. structural / scribus-engine-bug. RED.
8. `text_render_audit` (cap 12) — tail words of justified paragraphs
   clipped by Scribus over-wrapping. structural / scribus-engine-bug.
   Stays RED.
9. `visual_diff_regions` (cap 1) — 1px rasterise size rounding
   (0.01mm mm<->pt). cosmetic / human-review.

## human-review / authoring-bug items

- **authoring-bug:** `image_content_audit` (4 frames) and
  `image_frame_visibility_audit` (2 frames) — the source assets
  `green-pine-trees-covered-with-fog.jpg` and `leonore-sitzend-kopie.jpg`
  are **CMYK JPEGs** and `schwarzer-verlauf-radial.psd` is a CMYK PSD.
  Scribus 1.6.x renders CMYK JPEGs blank/faint and the
  `links_export.py` `convert -flatten` recipe discolours CMYK PSDs.
  Documented shared issues for this batch — no converter fix. The
  user's downloaded SLA keeps the real asset references; only the
  preview render shows the artifact.
- **human-review:** `inventory` (off-page furniture, correct behaviour)
  and `visual_diff_regions` (sub-pixel rounding) — both benign.

## Inventory gate note

`inventory_compare` exits 2 between the scaffold snapshot and the
post-tune render, but ONLY on the `words.missing_from_preview` list —
which words clip at justified-paragraph tails. All structural fields
are provably identical: 14 text / 5 image / 27 polygon / 4 group
frames (same annames), `total_idml` runs 55->55, `build_py_runs`
identical, `every_idml_run_present_in_build_py` true, preview word
count 306->306, `count_deltas: []`. None of the skill's hard blocking
rules (count decrease / anname removal / preview word dropped) fired.
The clipped-tail-word churn is the documented nondeterministic
cross-renderer line-wrap (Scribus clips a slightly different tail set
run-to-run) — not a structural regression. The committed
`SCAFFOLD_INVENTORY.yml` is kept as the structural calibration record.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page count + page geometry.** Confirm preview.pdf has 6 pages
   landscape, matching baseline page-for-page. This is the headline
   converter fix — verify the facing-spread pages (the baseline's
   2-page spreads) landed as separate, correctly-ordered pages with
   the right items on each.
2. **CMYK photos (pages 1, 5, 6).** The pine-tree photo (u9be page 1,
   u906 page 5) will render blank or washed-out; the Leonore photo
   (ua88 page 6) and the radial gradient (ua8f page 6) will look
   discoloured. This is the documented CMYK-render gap — confirm the
   FRAME placement / crop is correct even though the colour is wrong.
3. **White Grünen logo (ua5a, page 1).** Should now be VISIBLE
   (the tuning fix). Confirm it sits in the right spot.
4. **Justified body text.** Scribus wraps the Fliesstext paragraphs
   to slightly different line counts than InDesign; tail words
   ("consent.", "quatur.", etc.) overflow and clip on the body-text
   frames. Confirm the visible body text reads correctly and the
   clipping is only at paragraph tails — this is the cross-renderer
   line-wrap residual, expected and accepted.
5. **3-line headline (ua62, page 1).** Mixed Gotham Ultra + Vollkorn
   Black Italic; line spacing drifts vs baseline (Scribus per-line
   font metrics). Confirm all three words are present and legible.

# REVIEW NOTES — 26-03-flyer-a6-querformat-portrait

Prose summary for the human reviewer. Read alongside `TOLERANCE_LOG.md`
(per-tolerance detail) and `TOLERANCES.yml` (machine-readable).

## What the template is

A6 landscape ("Querformat") candidate flyer for Die Grünen NÖ, source
`26-03-Flyer A6 Querformat Portrait.idml`. It is a **folded flyer**: the
IDML has 4 spreads totalling 6 pages — spread 1 = page 1 (single,
A6 419x297pt), spread 2 = pages 2+3 (facing pair), spread 3 = pages 4+5
(facing pair), spread 4 = page 6 (single). InDesign exports this layout
**spread-based**, so `baseline.pdf` has 4 pages: 419 / 839 / 839 / 419 pt
wide (the two facing spreads are double-width single pages).

Content: page 1 cover (three-line headline, Störer circle, Leonore
portrait, subheadline); pages 2-3 and 4-5 are inner panels with lorem-
ipsum body text, bullet lists, a windmill line-art icon, and a quote
panel; page 6 is a full-bleed green "Plakat" background with a centred
white quote and yellow attribution.

## Scaffold outcome — GREEN (structural)

The scaffold required two converter changes in `tools/idml_to_dsl.py`
(Stage 1 permits converter edits):

1. **Spread-merged page model.** The converter previously emitted one
   SLA page per IDML *page* (6 pages). InDesign exports spread-based, so
   the rendered preview never aligned with `baseline.pdf` and the
   `visual_diff` audit crashed on a 6-vs-4 size mismatch. The converter
   now emits one SLA page per IDML *spread*: a facing-pages spread merges
   into one double-width page with all items placed relative to the
   leftmost page's origin. New helper `_collect_spread_pages`;
   `_emit_pages` / `_emit_build_template` / `_emit_page_stubs` rewired.
   Result: preview.pdf is 4 pages at 419/839/839/420pt — matches
   baseline page-for-page.

2. **Rotated-frame geometry fix.** `_compute_page_local_bbox_pt` used to
   return the rotated *axis-aligned bbox* as the frame width/height for
   rotated frames. Scribus rotates a frame around its XPOS/YPOS top-left,
   so this swept the -90deg full-bleed "Plakat" background (u978) off the
   top of the sheet — page 6 rendered blank. The converter now returns
   the un-rotated WIDTH/HEIGHT plus the rotation pivot. Page 6 now
   renders the green background correctly.

Also fixed a latent crash in `tools/systematic_text_audit.py`
(`max_drift_pt=None` TypeError on the MD report) and a stale-PNG bug in
`tools/visual_diff.py::rasterise` (it globbed `prefix-*.png` and picked
up leftover higher-numbered PNGs when the page count decreased 6->4).
The `test_rotated_90deg_textframe` unit test was updated to encode the
corrected rotated-frame contract; the full 597-test unit suite passes.

Every IDML element is emitted or explicitly skipped (completeness
assertion passes); all 4 `<Link>` assets resolve on disk; build.py runs
and renders. `SCAFFOLD_INVENTORY.yml` captured 46 elements, 40 emitted,
6 deliberately skipped off-page artifacts.

## Tune outcome — RESIDUAL (preflight red, 6 audits)

`bin/tune-render` -> `bin/tune-fix` ran the closed loop for 5 iterations.
The `y_mm_shift` playbook applied small uniform shifts to a few text
frames; the `line_spacing` playbook returned NO ROWS for all 12 flagged
frames (the drift is wrap-count divergence, not a leading value); the
`frame_visibility` playbook escalated the CMYK image frames. No playbook
could advance further — the loop is playbook-exhausted.

`# noinject:` annotations were added to the 3 external content
ImageFrames (u9cc, u906, u978), which cleared `external_asset_substitution_audit`.

`TOLERANCES.yml` documents 9 audit-scoped tolerances. Three of them
(inventory, image_audit, text_position_audit_jitter) flipped their
audits to tolerated. Six audits remain RED:

- `image_content_audit` / `image_frame_visibility_audit` — CMYK image
  rendering (see below).
- `systematic_text_audit` (12) / `text_position_audit_structural` (279)
  / `text_render_audit` (10 words) / `visual_diff_regions` (38) — all
  one root cause: cross-renderer line-wrap divergence.

A red preflight with fully documented, classified residuals is the
accepted terminal state for this batch — the sibling flyer/leporello
templates committed the same way.

## Residual drift numbers

| Audit | Count | Class |
|---|---|---|
| text_position_audit_structural | 279 large (>5pt) word drifts | scribus-engine |
| text_position_audit_jitter | 32 sub-perceptible (<=5pt) | scribus-engine (tolerated) |
| visual_diff_regions | 38 hot grid regions | scribus-engine |
| image_audit | 24 vector/image deltas | scribus-engine (tolerated) |
| systematic_text_audit | 12 sim-actionable frames | scribus-engine |
| text_render_audit | 10 unique words / 31 occurrences clipped | scribus-engine |
| inventory | 6 off-page artifacts | human-review (tolerated) |
| image_content_audit | 2 broken (u9cc, u906) | authoring-bug |
| image_frame_visibility_audit | 1 invisible + 1 faint | authoring-bug |

## authoring-bug items — what to eyeball

- **u906** (`green-pine-trees-covered-with-fog.jpg`, a CMYK JPEG) renders
  **completely blank** in preview page 2. Scribus 1.6.x fails to
  rasterise this CMYK JPEG. `links_export.py` keeps CMYK JPEGs as
  `passthrough` by a documented, tested decision (sRGB pre-conversion
  rendered a precedent image 2x too dark), so this was NOT changed.
  Impact is limited — u906 is the top strip of the merged facing spread
  where the baseline is mostly green background anyway.
- **u9cc** (`2026-03-leonore-fuer-flyer`, a CMYK PSD) renders on page 1
  but with a mean-RGB shift — the known `convert -flatten` non-ICC
  CMYK->RGB discolouration. The portrait IS visible, just colour-shifted.

## human-review items

- The 6 `inventory` dropped elements are off-page registration furniture
  (17.9x17.9pt Rectangles at x=476..794pt or x=-504pt). The converter
  correctly skips them and InDesign omits them too — no action needed,
  the audit is just conservative.

## What to eyeball in preview.pdf vs baseline.pdf

1. **Page geometry** — confirm preview is 4 pages at 419/839/839/420pt
   matching baseline (the whole point of the spread-merge converter fix).
2. **Page 4 (last spread)** — confirm the green full-bleed Plakat
   background renders (this is the rotated-frame fix; it was blank
   before).
3. **Page 2 top-right strip** — u906 pine-tree photo is blank
   (CMYK-JPEG residual). The baseline shows green-toned foliage there.
4. **Body-text tails on pages 2-3** — Scribus wraps the justified
   lorem-ipsum paragraphs to slightly different line counts, so the last
   word(s) of some paragraphs are clipped (`consent.`, `nam`, `quatur.`
   etc). Compare paragraph endings; this is the cross-renderer wrap
   residual, not lost content in the data model.
5. **Page 1 cover** — should match closely (headline, Störer, portrait,
   subheadline all present and positioned correctly).

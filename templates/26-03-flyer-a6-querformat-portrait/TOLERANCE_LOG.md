# TOLERANCE_LOG — 26-03-flyer-a6-querformat-portrait

Every tolerance / override granted on this template, with the measured
drift it resolves and why it is conservative. Reviewed by a human; the
matching machine-readable entries live in `TOLERANCES.yml`.

This template carried NO `meta.yml::brand_overrides`, `non_ci_*`, or
brand-rule growth — all 49 brand-rule errors are left un-suppressed
(they are the inherited `brand:font_family` Minion-Pro-on-abstract-
ParaStyle false positive plus `brand:line_spacing_0.9` /
`brand:inside_page` informational rows, identical to the sibling flyer
templates). Only `TOLERANCES.yml` audit-scoped entries were added.

| # | TOLERANCES.yml id | Audit | max_issues | Measured | Classification | Why conservative |
|---|---|---|---|---|---|---|
| 1 | tol:inventory-offpage-registration-marks | inventory | 6 | 6 dropped | human-review | Cap == exact dropped count. All 6 are 17.9x17.9pt Rectangles placed 100s of pt off-page (registration furniture); converter explicitly records each as skipped, completeness assertion still passes. InDesign also omits them. |
| 2 | tol:image-audit-vector-path-delta | image_audit | 28 | 24 deltas | scribus-engine-bug | Cap 28 vs 24 measured (small headroom). Raster/ICC + inline-vector-path extraction differences; same class as sibling flyer templates. |
| 3 | tol:image-content-cmyk-render | image_content_audit | 2 | 2 broken (u9cc, u906) | authoring-bug | Cap == exact broken count. u9cc CMYK-PSD colour shift (known links_export convert-flatten issue); u906 CMYK-JPEG blank (Scribus 1.6.x). Stage-1 asset-pipeline limits, not converter/build.py bugs. |
| 4 | tol:image-frame-visibility-cmyk-and-faint-icon | image_frame_visibility_audit | 2 | 1 invisible + 1 faint | authoring-bug | Cap == exact count. u906 invisible (same CMYK-JPEG failure); u46c faint (small inline-PNG Scribus weakness). |
| 5 | tol:systematic-text-line-wrap-no-sim-rows | systematic_text_audit | 12 | 12 actionable | scribus-engine-bug | Cap == exact count. line_spacing_sim returned NO ROWS for all 12 frames across 5 tune-fix iterations — drift is line-WRAP-count divergence, not a leading value. No (LINESPMode, LINESP) reconciles a wrap-count change. |
| 6 | tol:text-position-jitter-freetype-kerning | text_position_audit_jitter | 36 | 32 drifts | scribus-engine-bug | Cap 36 vs 32 measured. Sub-perceptible (<=5pt) FreeType-vs-InDesign kerning jitter. |
| 7 | tol:text-position-structural-cross-renderer-wrap | text_position_audit_structural | 290 | 279 drifts | scribus-engine-bug | Cap 290 vs 279 measured. Cross-renderer line-wrap divergence; amplified on the 839pt merged facing spreads where word-matching pairs a left-page word with its right-page lorem-ipsum twin. NOT tolerated-as-passing — preflight stays red. |
| 8 | tol:text-render-cross-renderer-wrap-overflow | text_render_audit | 12 | 10 words / 31 occ. | scribus-engine-bug | Cap 12 vs 10 measured. Tail words of justified paragraphs clipped because Scribus wraps to more lines than the frame holds. Converter already widened several frames; residual is wrap-count driven. |
| 9 | tol:visual-diff-regions-cross-renderer | visual_diff_regions | 44 | 38 hot regions | scribus-engine-bug | Cap 44 vs 38 measured. Page-grid view of the text-wrap + CMYK image residuals above; not an independent defect. |

## Notes

- Entries 1, 2, 6 flipped their audits to `ok: true (tolerated)` and
  removed them from the failing-audit set (9 -> 6 red audits).
- Entries 3, 4, 5, 7, 8, 9 remain RED in preflight: those audits are
  not tolerance-aware in `_build_preflight`, so `preflight.yml::ok`
  stays false. This matches how the sibling flyer/leporello templates
  in this batch were committed — a red preflight with fully documented,
  classified residuals is the accepted terminal state for cross-renderer
  line-wrap and CMYK-image gaps.
- No `--accept-residual` flag exists on `bin/tune-render` / `bin/tune-fix`;
  the documented residual-acceptance path is this `TOLERANCE_LOG.md` +
  `TOLERANCES.yml` + `REVIEW_NOTES.md` trio.

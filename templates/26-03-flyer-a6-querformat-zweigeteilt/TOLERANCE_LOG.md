# TOLERANCE_LOG — 26-03-flyer-a6-querformat-zweigeteilt

Every tolerance / override granted on this template, with the measured
drift it resolves and why it is conservative. Reviewed by a human; the
matching machine-readable entries live in `TOLERANCES.yml`.

This template carried NO `meta.yml::brand_overrides`, `non_ci_*`, or
brand-rule growth — all 46 brand-rule errors are left un-suppressed
(they are the inherited `brand:font_family` Minion-Pro-on-abstract-
ParaStyle false positive plus `brand:line_spacing` / `brand:inside_page`
informational rows, identical to the sibling flyer templates). Only
`TOLERANCES.yml` audit-scoped entries were added.

| # | TOLERANCES.yml id | Audit | max_issues | Measured | Classification | Why conservative |
|---|---|---|---|---|---|---|
| 1 | tol:inventory-offpage-registration-marks | inventory | 4 | 4 dropped (u6f0, u6f2, u77f, u964) | human-review | Cap == exact dropped count. All 4 are 17.9x17.9pt Rectangles placed off-page (x=-29.8mm / x=179..180mm); converter explicitly records each as skipped, completeness assertion still passes. InDesign also omits them from the trimmed export. |
| 2 | tol:image-audit-vector-path-delta | image_audit | 48 | 44 deltas | scribus-engine-bug | Cap 48 vs 44 measured (small headroom for raster-count jitter). Raster/ICC + inline-vector-path extraction differences; same class as the sibling flyer templates. |
| 3 | tol:image-content-cmyk-jpeg-blank | image_content_audit | 1 | 1 broken (u906) | authoring-bug | Cap == exact broken count. u906 (green-pine-trees CMYK JPEG) renders blank — preview mean-RGB [248,248,244] vs baseline [103,106,84], histogram divergence 0.47. Known Scribus 1.6.x CMYK-JPEG failure; no converter fix per batch policy. |
| 4 | tol:image-frame-visibility-cmyk-jpeg-blank | image_frame_visibility_audit | 2 | 2 invisible (u906, uace) | authoring-bug | Cap == exact count. u906 ink density 0.0; uace (ziesel.jpg CMYK JPEG) ink density 0.06 vs baseline 0.33. Both confirmed CMYK JPEGs via identify. Logo frame uad7 was repaired this pass and is no longer flagged. |
| 5 | tol:systematic-text-line-wrap-no-sim-rows | systematic_text_audit | 11 | 11 actionable | scribus-engine-bug | Cap == exact count. line_spacing_sim returned 0 changes for all frames across every tune-fix iteration — drift is line-WRAP-count divergence (uaf8 4->5, u9df 8->6, ub3b 4->6, u6d8 10->11), not a leading value. No (LINESPMode, LINESP) reconciles a wrap-count change. |
| 6 | tol:text-position-jitter-freetype-kerning | text_position_audit_jitter | 34 | 21 drifts | scribus-engine-bug | Cap 34 vs 21 measured. Sub-perceptible (<=5pt) FreeType-vs-InDesign kerning jitter; the count fluctuated 21-31 across iterations, hence the headroom. |
| 7 | tol:text-position-structural-cross-renderer-wrap | text_position_audit_structural | 269 | 269 drifts | scribus-engine-bug | Cap == exact count. Cross-renderer line-wrap divergence; 269 sits in the documented Querformat-flyer range (~257-279) and close to the sibling portrait flyer (279). NOT tolerated-as-passing — preflight stays red. |
| 8 | tol:text-render-cross-renderer-wrap-overflow | text_render_audit | 12 | 12 words / 28 occ. / 132 chars | scribus-engine-bug | Cap == exact count. Tail words of justified lorem-ipsum paragraphs clipped because Scribus wraps to more lines than the frame holds. Converter already widened several frames; residual is wrap-count driven. |
| 9 | tol:visual-diff-regions-raster-size-mismatch | visual_diff_regions | 1 | 1px raster-size mismatch (phase error) | human-review | Cap 1. baseline (874,620) vs preview (875,621) — sub-mm rounding at 150 dpi. Tooling artifact in the heatmap-overlay phase; no template edit changes it. Surfaces as a phase ERROR so it cannot be tolerance-cleared. Same error on sibling batch templates. |

## build.py edits made during tune (no tolerance — direct fixes)

- **uad7 (DIE GRUENEN logo)** — switched from `inline_image_data` (64KB
  base64 PNG blob) + `scale_type=1` to a direct `image=` reference to
  `shared/assets/.../gruene-logo-bund-weiss-cmyk.png` + `scale_type=0`.
  Scribus 1.6.x renders SCALETYPE=1 + small frame + RGBA white-on-
  transparent PNG fully transparent. After the fix the logo renders
  (image_frame_visibility_audit dropped 3 invisible -> 2). Mirrors the
  worked example in the idml-tune SKILL (26-03 Leporello u141).
- **uace / u906 / ub34** — added `# noinject:` justification comments
  above each external-image ImageFrame so external_asset_substitution_
  audit passes (it went from 3 missing -> OK). uace and u906 are CMYK
  JPEGs accepted as authoring-bug residual; ub34 is the design's
  intended back-cover poster artwork with no library substitute.
- **ub52 ("Leonore Gewessler")** — y_mm reverted to the scaffold value
  69.4096. The y_mm_shift playbook oscillated this single-line frame
  (alternating +-2.4 / +-4.8pt) across many iterations without
  converging and triggered a per-region regression; the audit's
  "uniform offset" reading is a line-count-mismatch artifact, not a
  real anchor offset. Reverting stopped the churn — per_region_
  regression returned to OK.

## Notes

- Entries 1, 2, 6 carry `severity: cosmetic` and flipped their audits to
  `ok: true (tolerated)`, removing them from the failing-audit set.
- Entries 3, 4, 5, 7, 8, 9 carry `severity: structural` and remain RED
  in preflight: those audits are documented but not flipped green. This
  matches how the sibling flyer/leporello templates in this batch were
  committed — a red preflight with fully documented, classified
  residuals is the accepted terminal state for cross-renderer line-wrap
  and CMYK-image gaps.
- No `--accept-residual` flag exists on `bin/tune-render` / `bin/tune-fix`;
  the documented residual-acceptance path is this `TOLERANCE_LOG.md` +
  `TOLERANCES.yml` + `REVIEW_NOTES.md` trio.

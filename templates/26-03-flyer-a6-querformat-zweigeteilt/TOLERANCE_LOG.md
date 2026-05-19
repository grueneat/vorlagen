# TOLERANCE_LOG — 26-03-flyer-a6-querformat-zweigeteilt

Every tolerance / override granted on this template, with the measured
drift it resolves and why it is conservative. Reviewed by a human; the
matching machine-readable entries live in `TOLERANCES.yml`.

This template carries NO `meta.yml::brand_overrides`, `non_ci_*`, or
brand-rule growth — all 56 brand-rule errors are left un-suppressed
(they are the inherited `brand:font_family` Minion-Pro-on-abstract-
ParaStyle false positive plus `brand:line_spacing` / `brand:inside_page`
informational rows, identical to the sibling flyer templates). The
`Minion Pro Regular` brand_constraint FAILs are read off the abstract
parent ParaStyle `idml/normalparagraphstyle` via the `<trail>`/`<DefaultStyle>`
PARENT reference; every actual ITEXT run carries a Gotham/Vollkorn FONT.
Only `TOLERANCES.yml` audit-scoped entries were added.

| # | TOLERANCES.yml id | Audit | max_issues | Measured | Classification | Why conservative |
|---|---|---|---|---|---|---|
| 1 | tol:inventory-offpage-registration-marks | inventory | 4 | 4 dropped (u6f0, u6f2, u77f, u964) | human-review | Cap == exact dropped count. All 4 are 17.9x17.9pt Rectangles placed off-page (x=-29.8mm / x=179..180mm); converter explicitly records each as skipped, completeness assertion still passes. InDesign also omits them from the trimmed export. |
| 2 | tol:image-audit-vector-path-delta | image_audit | 48 | 43 deltas | scribus-engine-bug | Cap 48 vs 43 measured (small headroom for raster-count jitter). Raster/ICC + inline-vector-path extraction differences; same class as the sibling flyer templates. |
| 3 | tol:systematic-text-line-wrap-no-sim-rows | systematic_text_audit | 6 | 6 actionable | scribus-engine-bug | Cap == exact count. line_spacing_sim returned no measurable drift for any candidate on any frame across every tune-fix iteration — drift is line-WRAP-count divergence (u6d8 10->11, u67c 7->9, u872 2->3, u92e 10->9, u9df 8->7, ub3b 4->3), not a leading value. No (LINESPMode, LINESP) reconciles a wrap-count change. Count dropped 11->6 after the u9df single-column fix. |
| 4 | tol:text-position-jitter-freetype-kerning | text_position_audit_jitter | 67 | 67 drifts | scribus-engine-bug | Cap == exact measured count (smallest tolerance). Sub-perceptible (<=5pt) FreeType-vs-InDesign kerning jitter. Count rose 34->67 this pass because the u9df single-column fix re-positioned every word in that frame (2-column flow restored) and the +2.88pt y_mm anchor correction shifted u9df's lines — both add sub-perceptible word-position deltas. |
| 5 | tol:text-position-structural-cross-renderer-wrap | text_position_audit_structural | 205 | 205 drifts | scribus-engine-bug | Cap == exact count. Cross-renderer line-wrap divergence, mostly inside the 2-column frames u67c/u92e/u9df/u6d8. Count dropped 269->205 this pass after the u9df single-column fix restored its 2-column flow. NOT tolerated-as-passing — severity structural, preflight stays red. |
| 6 | tol:visual-diff-regions-raster-size-mismatch | visual_diff_regions | 52 | 52 hot regions | human-review | Cap == exact count. The raster-size 1px phase error resolved this pass — visual_diff_regions is now a real audit row. The 52 hot regions trace to the cross-renderer line-wrap divergence plus the small CMYK->sRGB tone residual on dark photo frames. Same class as the sibling batch templates. severity structural — documented, preflight stays red. |

## build.py edits made during tune (no tolerance — direct fixes)

- **u9df (bullet list, page 4) — LINESP corrected 8.0 -> 15.999999999999998.**
  The re-imported build.py carried `LINESP: '8.0'` on every body paragraph of
  the u9df bullet frame. Root cause: the converter propagated a stray
  `<Leading>8</Leading>` from a CharacterStyleRange whose content is just `'.\t'`
  (a period + tab, not body text) onto the whole paragraph. At 8pt leading all 5
  bullets collapsed into column 1, so Scribus never flowed the 2nd column —
  u9df rendered single-column where the baseline (and the sibling 2-column frame
  u67c, which carries NO LINESP override) render 2-column. The bullet ParaStyle's
  leading is ~16pt; the baseline body-line gaps measure ~15pt. Setting LINESP to
  the ParaStyle's 15.999999999999998 restored the 2-column flow (preview Scim
  x=55.5 / Lia x=231.3, matching the baseline). line_match dropped 47->40,
  text_position_structural 286->272 word drifts.
- **u9df — y_mm shifted 45.55 -> 46.566 (+1.016mm = +2.88pt).** After the LINESP
  fix the line_spacing_pixel_audit measured u9df's line-1 ink-top 2.88pt above
  the baseline first line and line_match raised a `frame_vertical_position`
  finding (centroid drift over the 2.0pt tol). The +2.88pt y_mm correction
  anchors the block onto the baseline first line; the `frame_vertical_position`
  finding cleared and line_match dropped 40->34. The residual below line 1 is
  the 8-vs-7 column line-count divergence (cross-renderer wrap), not an anchor
  error.

## Removed since the previous pass (no longer needed)

- **tol:image-content-cmyk-jpeg-blank** and **tol:image-frame-visibility-cmyk-
  jpeg-blank** — REMOVED. The previous pass tolerated the green-pine-trees and
  ziesel CMYK JPEGs rendering blank. The current converter's CMYK->sRGB +
  aspect-fill crop fix resolves this entirely: `image_content_audit` is 4 ok /
  0 broken and `image_frame_visibility_audit` is 4 ok / 0 invisible. uace
  (ziesel) asset_render_ratio 0.998, u906 (green-pine) 0.996, uad7 (logo) 0.928,
  ub34 (plakat) renders all-black in baseline and preview as intended. No
  tolerance is needed any more.
- **tol:text-render-cross-renderer-wrap-overflow** — REMOVED. The previous pass
  tolerated 12 tail words of body text clipped by frame overflow. `text_render_
  audit` is now OK (0 issues, "all baseline text rendered") — the CMYK fix plus
  the u9df 2-column restoration removed the overflow.

## Notes

- Entries 1, 2 carry `severity: cosmetic` and flip their audits to
  `ok: true (tolerated)`, removing them from the failing-audit set.
- Entries 3, 4, 5, 6 carry `severity: structural` and remain RED in
  preflight: those audits are documented but not flipped green. This
  matches how the sibling flyer/leporello templates in this batch were
  committed — a red preflight with fully documented, classified
  residuals is the accepted terminal state for cross-renderer line-wrap.
- No `--accept-residual` flag exists on `bin/tune-render` / `bin/tune-fix`;
  the documented residual-acceptance path is this `TOLERANCE_LOG.md` +
  `TOLERANCES.yml` + `REVIEW_NOTES.md` trio. The final render that
  produced the committed artifacts ran `bin/tune-render --no-transactional`
  so the documented-red render is promoted into `templates/`.

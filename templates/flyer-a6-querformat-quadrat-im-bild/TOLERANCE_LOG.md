# TOLERANCE_LOG — flyer-a6-querformat-quadrat-im-bild

Every tolerance / override granted on this template, with the measured
drift it resolves and why it is conservative. Reviewed by a human; the
matching machine-readable entries live in `TOLERANCES.yml`.

This template carried NO `meta.yml::brand_overrides`, `non_ci_*`, or
brand-rule growth — all 42 brand-rule errors are left un-suppressed
(they are the inherited `brand:font_family` Minion-Pro-on-abstract-
ParaStyle false positive plus `brand:line_spacing` / `brand:inside_page`
informational rows, identical to the sibling flyer templates). Only
`TOLERANCES.yml` audit-scoped entries were added.

| # | TOLERANCES.yml id | Audit | severity | max_issues | Measured | Classification | Why conservative |
|---|---|---|---|---|---|---|---|
| 1 | tol:inventory-offpage-registration-marks | inventory | cosmetic | 4 | 4 dropped | human-review | Cap == exact dropped count. All 4 are 6.3x6.3mm Rectangles placed 500+pt off-page (u6f0, u6f2, u77f, u964 — registration furniture); converter explicitly records each as skipped, completeness assertion still passes. InDesign also omits them. |
| 2 | tol:image-audit-vector-path-delta | image_audit | cosmetic | 48 | 45 deltas | scribus-engine-bug | Cap 48 vs 45 measured (small headroom). Raster/ICC + inline-vector-path extraction differences + CMYK image render gaps; same class as sibling flyer templates. |
| 3 | tol:image-content-cmyk-render | image_content_audit | structural | 4 | 4 broken (u9be, u906, ua88, ua8f) | authoring-bug | Cap == exact broken count. u9be/u906/ua88 CMYK-JPEG blank/faint/discoloured (Scribus 1.6.x); ua8f CMYK-PSD colour shift (known links_export convert-flatten issue). Stage-1 asset-pipeline limits, not converter/build.py bugs. Each frame carries a # noinject: annotation. Stays RED (structural). |
| 4 | tol:image-frame-visibility-cmyk-jpeg | image_frame_visibility_audit | structural | 2 | 1 invisible + 1 faint | authoring-bug | Cap == exact count. u906 invisible + u9be faint (CMYK-JPEG render failure). The third originally-flagged frame ua5a (white logo) was FIXED — see Tuning fixes below. Stays RED (structural). |
| 5 | tol:systematic-text-line-wrap-no-sim-rows | systematic_text_audit | structural | 12 | 11 actionable | scribus-engine-bug | Cap 12 vs 11 measured. line_spacing_sim returned NO ROWS for all 11 frames across 2 tune-fix iterations — drift is line-WRAP-count divergence, not a leading value. No (LINESPMode, LINESP) reconciles a wrap-count change. Stays RED (structural). |
| 6 | tol:text-position-jitter-freetype-kerning | text_position_audit_jitter | cosmetic | 24 | 21 drifts | scribus-engine-bug | Cap 24 vs 21 measured. Sub-perceptible (<=5pt) FreeType-vs-InDesign kerning jitter. |
| 7 | tol:text-position-structural-cross-renderer-wrap | text_position_audit_structural | structural | 280 | 254 drifts | scribus-engine-bug | Cap 280 vs 254 measured. Cross-renderer line-wrap divergence; known shared band for Querformat flyers is ~279. NOT tolerated-as-passing — preflight stays RED. |
| 8 | tol:text-render-cross-renderer-wrap-overflow | text_render_audit | structural | 12 | 12 issues (12 words / 24 occ.) | scribus-engine-bug | Cap == exact count. Tail words of justified Fliesstext paragraphs clipped because Scribus wraps to more lines than the frame holds. Same root cause as text_position_audit_structural. Stays RED (structural). |
| 9 | tol:visual-diff-regions-rasterise-size-rounding | visual_diff_regions | cosmetic | 1 | 1 phase error | human-review | Cap == 1. 1px rasterise size mismatch (874x620 vs 875x621) from 0.01mm mm<->pt rounding on the page MediaBox. Sub-pixel, harmless. |

## Tuning fixes applied (not tolerances)

- **ua5a (white Gruenen logo, page 0):** switched from `inline_image_data`
  + `scale_type=1` to a direct `image=` reference to
  `gruene-logo-bund-weiss-cmyk.png` + `scale_type=0`. The Scribus 1.6.x
  SCALETYPE=1 + small-frame + RGBA white-PNG bug rendered it fully
  transparent (visibility ratio 0.0). After the fix it renders at
  visibility ratio 0.88 — class `ok`. Same fix pattern as the leporello
  u141 logo.
- **4 external CMYK image frames (u9be, u906, ua88, ua8f):** added
  `# noinject:` annotations with authoring-bug reasons, which cleared
  `external_asset_substitution_audit` (4 missing -> 0, audit now OK).

## Notes

- Entries 1, 2, 6, 9 are `severity: cosmetic` and flipped their audits
  to `ok: true (tolerated)`, removing them from the failing-audit set
  (8 -> 5 red sub-audits).
- Entries 3, 4, 5, 7, 8 are `severity: structural`: documented and
  classified but they do NOT flip preflight; `preflight.yml::ok` stays
  false. This matches how the sibling flyer / leporello templates in
  this batch were committed — a red preflight with fully documented,
  classified residuals is the accepted terminal state for cross-renderer
  line-wrap and CMYK-image gaps.
- No `--accept-residual` flag exists on `bin/tune-render` / `bin/tune-fix`;
  the documented residual-acceptance path is this `TOLERANCE_LOG.md` +
  `TOLERANCES.yml` + `REVIEW_NOTES.md` trio.

---

## brand_overrides — 2026-05-19 — IDML-import structural-check exceptions

`meta.yml::brand_overrides` entries granted for this scaffold-imported
26-03 template. Each silences one `structural_check` brand rule whose
violation traces to the IDML import, not to a build.py defect. Identical
gap class to the sibling 26-03 leporello templates (gruenes-cover-2,
portrait, zweigeteiltes-cover) that already carry the same block.

- **`brand:bleed_3mm`** — The IDML document was authored with bleed=0 and build.py deliberately emits bleed_mm=0 so the rendered PDF compares directly against the trim-only InDesign baseline.pdf. The Quickguide's 3mm print bleed postdates this asset. Resolution path: inject the brand 3mm bleed in tools/idml_to_dsl.py at scaffold time — deferred.
- **`brand:image_text_overlap`** — The original InDesign layout deliberately overlays headline / Zitat text on full-bleed photo backdrops and on the magenta Stoerer decoration. The brand rule cannot distinguish intentional design overlay from accidental clipping. Resolution path: per-frame intent annotation in the rule — deferred.
- **`brand:inside_page`** — The IDML spread coordinate system places multi-panel content on a single oversized canvas; frames belonging to later panels register outside the converter's declared trim-sized page. The converter preserves source geometry verbatim per issue #35 P1. Resolution path: emit a true multi-panel spread layout — deferred.
- **`brand:line_spacing_0.9`** — The IDML-imported InDesign ParagraphStyles (idml/* and ci/* families) carry leading values that do not follow the Quickguide 0.9-factor convention. tools/idml_to_dsl.py emits the source leading verbatim; the InDesign-authored baseline.pdf is the convergence target (issue #35 P1). Identical handling to the sibling 26-03 leporello templates that already carry this override. Resolution path: a per-template tune pass — deferred.

# Tolerance Log — 26-03-flyer-a6-hochformat-quadrat-in-bild

Every tolerance, override, frame edit, and accepted residual for this
template, with measured drift and classification. Newest first.

| # | What | Values (before → after) | Drift it resolves | Why conservative | Classification |
|---|------|--------------------------|-------------------|------------------|----------------|
| 1 | `# noinject:` on 4 ImageFrames `u132c`, `u1260`, `u137f`, `u1386` (build.py) | external_asset_substitution_audit: 4 missing → 0 | Cleared `external_asset_substitution_audit` (4 frames flagged "missing INJECT_MAP/noinject"). | These are the genuine IDML-placed content images (pine-forest cover photo, pine-forest banner, Gewessler portrait, radial-gradient overlay) — present on disk, embedded in the SLA, real template content. They are NOT demo placeholders, so library substitution is wrong; `# noinject:` with a content reason is the audit's own documented correct disposition. | not-a-tolerance (correct disposition); logged for transparency |
| 2 | Frame `u1336` (DIE GRÜNEN logo): `inline_image_data` → `image=` ref + `scale_type=0` (build.py) | `inline_image_data`+`scale_type=1`+`local_scale=(0.284972,…)` → `image='…/gruene-logo-bund-weiss-cmyk.png'`+`scale_type=0` | image_frame_visibility_audit: u1336 `invisible_in_preview` (visibility_ratio 0.0) → no longer flagged. The white-on-transparent logo did not render at all under the inline+scale_type=1 path (known Scribus 1.6.x bug). | This is the SKILL's documented `frame_visibility` playbook fix ("swap inline_image_data → image= ref with scale_type=0"). The asset is on disk and identifiable. `scale_type=0` (fit-to-frame) is correct for a logo. No geometry or content guesswork. | scribus-engine (Scribus 1.6.x SCALETYPE=1 + small RGBA white-on-transparent PNG renders transparent) — resolved |
| 3 | Frames `u1260`, `u132c`, `u1386`: `scale_type=1` → `scale_type=0` (build.py) | `scale_type=1` → `scale_type=0` (local_scale/local_offset_mm kept as-is) | image_frame_visibility_audit: `u1260` invisible (ratio 0.0), `u132c` faint (ratio 0.399) → both `ok`. image_content_audit: u1260 + u132c `broken` → `ok`. The pine-forest photos rendered washed-out/missing under `scale_type=1` because Scribus re-fits on top of the converter's `local_scale`/`local_offset_mm` crop, conflicting with it. `scale_type=0` (free transform) honours the converter's crop directly. | Same SKILL `frame_visibility` playbook disposition extended to the pine-photo frames. Only the SCALETYPE flag changed; the converter's `local_scale`/`local_offset_mm` crop values are preserved untouched. Verified visually (pages 1 + 5 now match baseline). u1386 (radial gradient) also switched for consistency — its residual is the asset itself (row in Accepted residuals). | scribus-engine — resolved for u1260, u132c |

## Accepted residuals (preflight not green)

The Stage-2 `bin/tune-render` → `bin/tune-fix` loop could not drive
preflight green; the residuals below are accepted per the overnight
gate policy (scribus-engine / human-review classes). No `converter-bug`
is left silently unfixed — the line-spacing items the convergence-review
classifier labelled `converter-bug` were verified by measurement to be
cross-renderer line-wrap (scribus-engine), see Notes.

| Audit | Residual | Classification | Reason accepted |
|-------|----------|----------------|-----------------|
| `text_position_audit_structural` | 254 large drifts (>5pt) | scribus-engine | Cross-renderer line-wrap differences. Scribus and InDesign break the justified body / bullet-list paragraphs at slightly different words (font-metric / hyphenation differences). One wrap-point difference flips a word from end-of-line to start-of-line, producing dx≈-160…-187pt and cascading downstream. Page content and frame geometry verified correct by page-by-page visual diff (pages 1, 2, 5, 6). Not a converter or routing bug. |
| `text_position_audit_jitter` | 29 sub-perceptible drifts (≤5pt) | scribus-engine | Sub-perceptible (≤5pt) cross-renderer position jitter, below the visible threshold. The `y_mm_shift` playbook reported "no reliable calibration frame" and emitted only tentative recommendations — no deterministic shift could be derived. |
| `systematic_text_audit` | 8 frames sim-actionable | scribus-engine | The `line_spacing` playbook's simulator (`tools/line_spacing_sim.py`) returned **no rows** for every one of these frames — the drift is line-WRAP-count divergence, not a leading value. line_spacing_pixel_audit confirms line-count mismatches (u1242 16→17, u129e 10→9, u12b5 11→12). No single (LINESPMode, LINESP) reconciles a wrap-count difference. |
| `image_content_audit` | 1 broken frame: `u1386` (`Schwarzer Verlauf radial`) | converter-bug (asset pipeline) — accepted as residual for this run; flagged human-review | The source `Schwarzer Verlauf radial.psd` is CMYK; the asset pipeline converted it to `schwarzer-verlauf-radial.png` (RGB) with a broken CMYK→RGB step — the PSD corner CMYK `(40,255,255,255)` (near-black) became RGB `(0,173,233)` (cyan) in the PNG. The radial vignette renders as a pale-blue blob over the page-6 portrait (mean_delta_rgb 102.8). The IDENTICAL broken asset is shipped in the sibling template `26-03-flyer-a6-hochformat-portrait` (template 1 of this batch). This is a shared asset-conversion bug, not a per-template error — fixing it belongs in the Stage-1 asset/PSD-conversion pipeline (`tools/`), out of scope for a Stage-2 tune. Surfaced as human-review (see REVIEW_NOTES.md). |
| `image_audit` | 40 vector-path delta | scribus-engine | Derivative of the above image-rendering differences plus brand-colour ICC shifts (region_color_audit is green / informational `concentrated_fill_bugs`). |
| `phase-error: visual_diff_regions` | `ValueError: image size mismatch baseline=(620,874) preview=(621,875)` | tooling-bug | A 1-pixel raster-size mismatch in the audit harness's region differ — a pre-existing tool bug, not a template issue. The sibling template `26-03-flyer-a6-hochformat-portrait` carries the identical phase-error. Not addressable from a template. |

## Notes
- No `meta.yml::brand_overrides`, `non_ci_*`, or `TOLERANCES.yml` numeric
  growth was required — `region_color_audit` and `run_style_audit` are
  green; the residual is cross-renderer fidelity, not a brand/CI
  violation. `TOLERANCES.yml` is present only as a placeholder
  documenting that no numeric tolerance was grown.
- The convergence-review classifier (`bin/convergence-review`) labelled
  several `line_spacing_pixel_audit` items `converter-bug` (u11e6,
  u1214, u1242, u129e, u12b5, u133f). This was verified by measurement
  to be a heuristic false-positive: `classification.md` line 30 maps
  `line_spacing_audit delta>0.5` → `converter-bug`, but
  `line_spacing_audit` (E2) is deprecated. The authoritative pixel
  audit (E4) plus `line_spacing_full_audit` (cross-source IDML→build.py
  →SLA) show the per-line GAP is `match` (e.g. u1242 baseline gap
  14.3pt == preview gap 14.3pt — leading correct). The cumulative
  drift comes purely from preview wrapping into a different line
  COUNT. The converter emits correct leading; there is no converter
  bug to fix.
- An attempt to override the 2-line headlines (u122b, u1287, u12cc)
  with `LINESPMode=0, LINESP=28.44` was made and REVERTED — the pixel
  audit showed those frames were already within 1.92pt and the
  override regressed them to 4.32–6.24pt (per_region_regression
  flagged it). The pdfplumber-based full-audit "gap 28→42pt" signal
  that motivated the attempt is exactly the unreliable text-matrix-Y
  measurement the SKILL warns against; the authoritative pixel audit
  governed the revert.

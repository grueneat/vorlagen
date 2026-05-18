# Tolerance Log — 26-03-flyer-a6-hochformat-quadrat-in-bild

Every tolerance, override, frame edit, and accepted residual for this
template, with measured drift and classification. Newest first.

This is the **image-fidelity re-render pass** (template 2 of 8). The
template was re-imported to pick up the shared CMYK->sRGB and
geometry-derived crop fixes (commit `de96b7c`) plus the four
converter/tooling follow-ups from template 1's re-render (commit
`dcc52c7`). The earlier scaffold's `build.py` was intentionally
overwritten; the earlier tune's hand-edits were re-applied below.

| # | What | Values (before → after) | Drift it resolves | Why conservative | Classification |
|---|------|--------------------------|-------------------|------------------|----------------|
| 1 | Converter fix — rotated-TextFrame W/H convention (`tools/idml_to_dsl.py`, TextFrame emission) | `_compute_page_local_bbox_pt` un-rotated extent passed straight through → for ±90° non-empty TextFrames, converted to the axis-aligned-bbox-of-rotated-rect form before emission | `text_render_audit`: 2 words missing (`impressum`, `xxxxxx` → clipped to `impressu`), `per_region_regression`: 2 regressions (`u137f`, `u1386`). The `de96b7c`/`5e48f81` rotated-frame branch in `_compute_page_local_bbox_pt` emits the *un-rotated* frame extent + pivot — correct for ImageFrames and empty background frames. But the TextFrame primitive (`sla_lib/builder/primitives.py`) applies a text-flow W/H swap to any ±90° frame carrying text. Feeding it the un-rotated model AND letting it swap is a double-correction: the visible Impressum frames (`u11fd`, `u126f`) collapsed from a 53.4mm-wide text strip to a 10mm-wide one and clipped after 8 characters. | The fix is in the converter (Stage-1-permitted; structural gate failure). It is scoped to ±90° **non-empty** TextFrames only — the un-rotated model is left untouched for ImageFrames and empty background frames, which the primitive places verbatim. The conversion is closed-form geometry (axis-aligned bbox of the rotated rectangle), not a guess; verified the result reproduces the pre-`dcc52c7` working `u11fd` geometry exactly (`x=95, y=82.6, w=10, h=53.4`). | converter-bug — fixed in Stage 1 |
| 2 | Frame `u1336` (DIE GRÜNEN logo): `inline_image_data` + `scale_type=1` → `image=` ref + `scale_type=0` (build.py) | `inline_image_data`+`inline_image_ext='png'`+`local_scale=(0.284972,…)`+`scale_type=1` → `image='…/gruene-logo-bund-weiss-cmyk.png'`+`scale_type=0` | `image_frame_visibility_audit`: `u1336` `invisible_in_preview` (visibility_ratio 0.0) → `ok` (0 invisible frames). The white-on-transparent RGBA logo did not render at all under the inline+`scale_type=1` path. | This is the SKILL's documented `frame_visibility` playbook fix (swap `inline_image_data` → `image=` ref with `scale_type=0`). The asset is on disk and identifiable. `scale_type=0` (fit-to-frame) is correct for a logo. No geometry guesswork. The `bin/tune-fix` `frame_visibility` playbook escalated ("not inline_image_data form, or asset name unknown" — it could not auto-resolve the asset basename), so the documented swap was applied by hand and re-rendered. Re-applies the prior tune's TOLERANCE_LOG row 2 that the re-import dropped. | scribus-engine (Scribus 1.6.x SCALETYPE=1 + small RGBA white-on-transparent PNG renders transparent) — resolved |
| 3 | `# noinject:` comment on ImageFrame `u1386` (build.py) | external_asset_substitution_audit: 1 missing → 0 (`noinject_justified: 1`) | Cleared `external_asset_substitution_audit` (`u1386` flagged "missing INJECT_MAP/noinject"). | `u1386` is the genuine IDML-placed radial-gradient vignette overlay (`Schwarzer Verlauf radial.psd`), real template content — not a demo placeholder. `# noinject:` with a content reason is the audit's own documented correct disposition. Only one frame is flagged this pass (vs four in the prior run) — the `de96b7c` crop fix routes the three photo frames through `crops/` so the audit no longer flags them. | not-a-tolerance (correct disposition); logged for transparency |

## Accepted residuals (preflight not green)

The Stage-2 `bin/tune-render` → `bin/tune-fix` loop drove the image
audits fully green but could not drive the text-position audits green;
the residuals below are accepted per the overnight gate policy
(scribus-engine class). `bin/tune-fix` exhausted every playbook — the
`line_spacing` simulator returned **no rows** for all 10 frames,
confirming the drift is line-wrap-count divergence, not a leading
value no playbook can address.

| Audit | Residual | Classification | Reason accepted |
|-------|----------|----------------|-----------------|
| `text_position_audit_structural` | 253 large drifts (>5pt) | scribus-engine | Cross-renderer line-wrap differences. Scribus and InDesign break the justified body / bullet-list paragraphs at slightly different words (font-metric / hyphenation models differ). One wrap-point difference flips a word from end-of-line to start-of-line (dx ≈ -160…-187pt) and cascades downstream. Page content and frame geometry verified correct by page-by-page visual diff (pages 1, 5, 6). Not a converter or routing bug. One fewer than the prior run's 254 (line-wrap is sensitive to the re-imported geometry). |
| `text_position_audit_jitter` | 30 sub-perceptible drifts (≤5pt) | scribus-engine | Sub-perceptible (≤5pt) cross-renderer position jitter, below the visible threshold. The `y_mm_shift` playbook emitted only tentative recommendations ("no reliable calibration frame — no line-count match"); no deterministic shift could be derived. This audit is green under the tolerance cap. |
| `systematic_text_audit` | 10 frames sim-actionable | scribus-engine | The `line_spacing` playbook's simulator (`tools/line_spacing_sim.py`) returned **no rows** for every one of these 10 frames. `line_spacing_pixel_audit` confirms the root cause is line-COUNT divergence (u1242 16→17, u129e 10→9, u12b5 11→12) — and the per-line GAP is correct in both renderers (baseline gaps 13.9-14.9pt == preview gaps 13.9-14.9pt). No single (LINESPMode, LINESP) reconciles a wrap-count difference. |
| `visual_diff_regions` | 59 hot regions | scribus-engine | Derivative of the cross-renderer line-wrap. The worst region on every page is a body-TEXT band (page 0 row1 18.3%, page 2 row1 22.6%, page 4 row2 25.6%) — NOT a photo band. This is the goal outcome of the image-fidelity pass: the worst regions are now text-driven, not image-driven. `visual_diff_regions` no longer phase-errors (the `dcc52c7` raster-rounding tolerance fix resolved the pre-existing 1-pixel-mismatch ValueError the prior run carried). |
| `image_audit` | 39 vector-path deltas (tolerated, cap 45) | scribus-engine | Derivative of intrinsic Scribus image-rendering differences plus brand-colour ICC shifts. Within the existing `TOLERANCES.yml` cap (45) — green, no growth. |
| `image_frame_visibility_audit` | 1 faint frame: `u1386` (radial gradient) | accepted tolerance (CMYK→sRGB tone) | `u1386` visibility_ratio 0.681 — the radial vignette renders, just lighter than baseline. This is the small residual CMYK→sRGB tone shift on the dark PSD that the re-render brief explicitly classifies as acceptable. The audit's overall verdict is `ok` (0 invisible). |

## Image audit — before vs after (the goal of this pass)

| Audit | Prior overnight run | This re-render | Outcome |
|-------|--------------------|----------------|---------|
| `image_content_audit` | 1 broken (`u1386` radial PSD — cyan blob, mean_delta_rgb 102.8) | **0 broken, 5 ok** (`u1386` mean_delta_rgb 4.2) | FIXED — the CMYK→sRGB conversion bug is resolved |
| `image_frame_visibility_audit` | 1 invisible (`u1336` logo) | **0 invisible**, 1 faint (`u1386`) | FIXED — the logo renders; `u1386` faint is the accepted CMYK tone residual |
| `external_asset_substitution_audit` | 4 missing | **0 missing** (`u1386` noinject; 3 photos routed via `crops/`) | FIXED |
| `visual_diff_regions` | phase-error (ValueError 1px size mismatch) | runs clean, 59 hot regions, all text-driven | FIXED (tooling) — worst regions are now text, not image |

Per-frame `image_content_audit` mean_delta_rgb this pass: `u132c` pine
cover 5.2, `u1260` pine banner 7.1, `u137f` Leonore portrait 2.1,
`u1386` radial PSD 4.2. All five frames classified `ok`. The pine
backgrounds (pages 1 + 5) and the Leonore portrait (page 6) were
washed-out / invisible / discoloured in the prior run and now render
correctly — verified visually against `baseline.pdf`.

## Notes

- No `meta.yml::brand_overrides`, `non_ci_*`, or `TOLERANCES.yml`
  NUMERIC growth was required. `region_color_audit` (9 fill_likely,
  informational `concentrated_fill_bugs`) and `run_style_audit` are
  green — no brand or CI-rule violation. The `image_audit` count (39)
  is within the existing cap (45). `TOLERANCES.yml` records the
  accepted-residual entries; none grows a numeric brand/CI tolerance.
- `meta.yml::asset_policy` was NOT changed. `links_export.yml` shows
  the pine and Leonore CMYK JPEGs are now converted to `.png` by the
  `de96b7c` ICC-aware pipeline, but `asset_policy_audit` reports
  `ok: true` — both `.jpg` (original source) and `.png` (render
  asset) are on disk and classified, matching the convention the
  sibling template `26-03-flyer-a6-hochformat-portrait` set at its
  `dcc52c7` re-import. No `.jpg`→`.png` edit was needed.
- The convergence-review classifier (`bin/convergence-review`)
  labelled 7 `line_spacing_pixel_audit` items `converter-bug` (u11e6,
  u1214, u1242, u129e, u12b5, u12e4, u133f), each with
  `est_drift_drop: 0.0pp`. This is the known heuristic false-positive
  (`classification.md` maps the deprecated E2 `line_spacing_audit` to
  `converter-bug`; the authoritative E4 pixel audit + cross-source
  full audit show the per-line GAP is `match` — the converter's
  leading is correct). The drift is line-wrap COUNT divergence.
  Treated as `scribus-engine`, not escalated — the same verified
  finding as the prior overnight run.
- The Stage-2 hand-edits (rows 2-3) are inline in `build.py`. They
  will be lost on a clean re-import (no `inject.yml` reconciler path
  for image-ref swaps); preserved here per the protocol.

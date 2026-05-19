# Tolerance Log — 26-03-flyer-a6-hochformat-quadrat-in-bild

Every tolerance, override, frame edit, and accepted residual for this
template, with measured drift and classification. Newest first.

This is the **combined-fidelity re-render pass** (template 2 of 8). The
template was re-imported to pick up the full converter/tooling fix set:
CMYK->sRGB conversion, deterministic aspect-fill crop, squiggle colour +
re-anchoring, the five newly-consumed Tier-A attributes (`SpaceAfter`,
`BlendingSetting/Opacity`, `VerticalJustification`, `TextColumnCount`,
`TextColumnGutter`), the ground-truth squiggle alignment audit, the
attribute-coverage gate (Phase E5f), and the R5 converter fix from
template 1's re-render (trailing-`<Br/>` no longer doubles the paragraph
break). The re-import regenerated `build.py` from the fully-fixed
converter, overwriting the prior pass's `build.py`; the prior tune's
hand-edits were re-applied below (rows 2-4).

---

## FINAL re-render — verification pass (newest)

Re-import + tune against the current committed converter/audit fix set
(HEAD `870a9a3`). The re-import regenerated `build.py`, overwriting the
prior pass's tune edits. The current converter's mixed-font headline
splitter now emits the recalibrated geometry directly: each split line
frame is widened by a `+12mm` clip-safety margin (`w_mm=70.4538`) and
the per-line FLOP correction is applied in-converter — so the prior
pass's manual `u133f_l2` `y_mm +6.24pt` shift and `w_mm 70.4538→58.4538`
narrowing are NO LONGER the right edits (they fought an older converter).
This pass re-applies only what the converter genuinely drops, and fixes
one shared audit-tool bug.

### Edits applied (build.py)

| # | What | Values (before → after) | Drift it resolves | Why conservative |
|---|------|--------------------------|-------------------|------------------|
| G1 | `space_after_pt` on green body ParaStyle `idml/fliesstext-auf-gruenem-hintergrund` (build.py `_add_styles`) | (absent) → `space_after_pt=5.6693` | `text_position_audit_structural` 152 → **46**; `systematic_text_audit` 6 → 4. The IDML carries the green body's inter-paragraph spacing as `<SameParaStyleSpacing>` (its `BasedOn` is `[No paragraph style]`, `SpaceAfter=0`); the converter does not consume `SameParaStyleSpacing`, so a re-import drops it. The white sibling `fliesstext-auf-weissem-hintergrund` carries `5.669…` explicitly via `SpaceAfter`. `baseline.pdf` shows ~5.67pt inter-paragraph spacing on the green body + bullet lists. | Restores the IDML-rendered spacing exactly (5.6693pt, the white-sibling value). Same fix templates 1-3 needed on re-import. |
| G2 | `u133f` 3-line headline split frames: centred + frame x shifted to keep frame-centre on the IDML frame-centre (build.py) | all three `x_mm` 23.2731 → 17.2731; lines 2-3 `paragraph_attrs` gained `ALIGN: '1'`; all three `trail_attrs` gained `ALIGN: '1'` | `line_match_audit` headline findings — preview headline rendered LEFT-hugging the green box instead of centred. | The IDML story `Story_u1342.xml` is `Justification="CenterAlign"`. The current converter widens each split frame by `+12mm` (`line_w = w_mm + 12`) but emits left-alignment; a single-Run frame's only paragraph is closed by `<trail>`, so `ALIGN` must live in `trail_attrs` AND in lines 2-3 `paragraph_attrs`. The `x_mm` shift of `-6.0mm` (half the `+12` widening) keeps the widened frame's centre exactly on the IDML text frame's centre (IDML `x=23.2731`, `w=58.4538` → centre `52.50mm`; new `x=17.2731`, `w=70.4538` → centre `52.50mm`), so the centred lines land on the InDesign text-column centre. The converter-emitted `y_mm` values are kept untouched — the pixel-clean scan (below) confirms all three lines render at 0.0pt drift at the converter's `y`. |
| G3 | `# noinject:` comment on ImageFrame `u1386` (build.py) | `external_asset_substitution_audit`: 1 missing → 0 | Cleared `external_asset_substitution_audit` (`u1386` flagged "missing INJECT_MAP/noinject"). | `u1386` is the genuine IDML-placed radial-gradient vignette overlay (`Schwarzer Verlauf radial.psd`) — a fixed dark vignette over the page-6 portrait so the white citation stays legible. Not a substitutable demo photo. `# noinject:` with a content reason is the audit's documented disposition. |

### Shared audit-tool bugfix (`tools/line_spacing_pixel_audit.py`)

`measure_split_headline` reported a phantom `split_headline_spacing`
failure (`u133f` "worst 2.88pt") that did not respond to any frame
`y_mm` move. Root cause: the current converter widens each split-
headline frame by `+12mm` past its IDML text width, so the union bbox
of the three `u133f` lines (`x` 17.27→87.73mm) overhangs the green box
(`x` 21→84mm) onto the foggy pine-forest photo. The audit's white-
colour ink scan (`_scan_color_lines`, `min_ink_columns=6`) latched onto
the diffuse atmospheric fog (12–35 matched columns) instead of the
headline glyph cap-row (82–119 columns). A direct pixel scan restricted
to the green box (x 25–90mm) measured ALL THREE headline lines at
**0.0pt drift** — the headline geometry is correct; only the audit was
contaminated. Fix: a new density-aware scanner `_scan_color_headline_top`
groups matched rows into bands, selects the band with the highest peak
column count (the real glyphs — diffuse contamination forms low-peak
bands), and returns the first row reaching half the band peak (the
glyph cap-top, skipping any faint contamination skirt that merged into
the band). `measure_split_headline` now calls it for both PDFs. The 10
`tests/unit/test_line_spacing_pixel_audit.py` cases still pass; the
change only affects split-headline rows and is drift-neutral for clean
headlines (both renders measured identically). `split_headline_spacing`
went RED → GREEN.

### Accepted residuals — preflight RED (documented, genuinely unclosable in Stage 2)

| Audit | Residual | Classification | Reason accepted |
|-------|----------|----------------|-----------------|
| `line_match_audit` | 16 of 70 lines mismatched | scribus-engine | Same documented breakdown as the prior pass: 6 body line-wrap + 1 unmatched (`u1242`, `u129e` — Scribus breaks justified paragraphs at different words); 3 rotated-frame (`u11fd`/`u126f` Δ28.34pt rotated `-90°` Impressum sidebar, `u1358` Δ-1.47pt rotated `-9°` Störer — Scribus rotated-frame engine limit); 6 sub-2pt centred/justified `first_word_x` (`u133f`×3 Δ~1.2pt, `u12fb` Δ-1.92pt, `u1390`×2 Δ~1.8pt — the ~0.75% Vollkorn/Gotham glyph-width difference shifts a centred line's start by ~half the width delta). `bin/tune-fix` exhausted every playbook; `line_spacing_sim` returned no rows. All 16 fall in the brief's known-acceptable residual classes (cross-renderer line-wrap, rotated-frame centring, ~0.75% glyph-width). `line_match_audit` is not tolerance-able — preflight stays red; no fix is durable (any frame nudge fits renderer noise and is dropped on re-import). |
| `text_position_audit_structural` | 46 large drifts (>5pt) | scribus-engine | Cross-renderer line-wrap. Down from 152 (the G1 `SpaceAfter` fix). The remaining 46 are the 2 wrap events (`u1242`, `u129e`) cascading downstream words on their pages. All 6 pages verified visually — content + frame geometry correct. Within cap 260. `severity: structural` — preflight red by design. |
| `systematic_text_audit` | 4 frames sim-actionable | scribus-engine | `line_spacing_sim` returned no rows for every frame (`u1287`, `u129e`, `u12b5`, `u13a7`) — line-WRAP-count divergence, not a leading value. `line_spacing_pixel_audit` confirms per-line GAP is correct in both renderers. Within cap 11 (improved from 6 last pass). |
| `image_frame_visibility_audit` | 1 faint frame: `u1386` | accepted (CMYK→sRGB tone) | `u1386` visibility_ratio 0.686, `asset_render_ratio` 0.987 — the radial vignette renders, just lighter than baseline (small CMYK→sRGB tone shift on the dark PSD). 0 invisible frames; overall audit verdict `ok`. |

### Audits driven / held GREEN this pass

`split_headline_spacing` (RED → GREEN — see audit-tool bugfix above;
the headline geometry was correct throughout), `squiggle_alignment_audit`
(8 yellow squiggles, all on their words), `idml_attribute_coverage`
(0 unconsumed), `image_content_audit` (5 ok / 0 broken),
`image_frame_visibility_audit` (0 invisible; logo `u1336`
`asset_render_ratio` 0.849), `external_asset_substitution_audit`
(0 missing), `text_render_audit`, `per_region_regression`, `inventory`
(exit 0 — no structural regression vs `SCAFFOLD_INVENTORY.yml`).

No tolerance cap grew this pass.

---

## FINAL re-render (template 2 of 8, FINAL pass) — prior

This re-import + tune cycle was driven against the full committed
converter/audit fix set including the 6 audit-coordinate fixes from
template 1. The re-import regenerated `build.py`; the converter this
time emitted a structurally clean scaffold (the prior pass's `u1336`
logo swap and `u12b5` widening were NOT needed — the inline logo
renders and `text_render_audit` is OK without the widening). The
tune-stage edits this pass:

### Edits applied (build.py)

| # | What | Values (before → after) | Drift it resolves | Why conservative |
|---|------|--------------------------|-------------------|------------------|
| F1 | `space_after_pt` on green body ParaStyle `idml/fliesstext-auf-gruenem-hintergrund` (build.py `_add_styles`) | (absent) → `space_after_pt=5.6693` | `text_position_audit_structural` 253 → **46**; `systematic_text_audit` 9 → 6. The IDML drops `SpaceAfter` on the green body variant — its `BasedOn` is `[No paragraph style]` (`SpaceAfter=0`) while the white sibling `fliesstext-auf-weissem-hintergrund` carries `5.669…` explicitly. `baseline.pdf` measured: ~14pt within-paragraph line gaps vs ~20pt at paragraph boundaries on the green body AND green bullet lists — i.e. ~5.67pt `SpaceAfter` is present in the InDesign render. | Restores the IDML-rendered spacing exactly (5.6693pt, the white-sibling value). The bullet style `aufzaehlungen-auf-gruenem-hintergrund` inherits it (parent = the green body style) — matches the measured ~20pt bullet-item gaps. Same fix template 1's run needed. |
| F2 | `u133f` 3-line headline split frames: `ALIGN` restored + frame width set to text-column width (build.py) | lines 2-3 `paragraph_attrs` gained `ALIGN: '1'`; all three `trail_attrs` gained `ALIGN: '1'`; `w_mm` 70.4538 → 58.4538 | `line_match_audit` `u133f_l3` Δ-21.72pt → Δ-1.04pt (`u133f` Δ-4.92→-1.24, `u133f_l2` Δ-3.82→-1.24). The converter split the mixed-font headline into 3 single-line frames but lost the `Justification="CenterAlign"` on lines 2-3 and on the `<trail>` of all three — they rendered left-aligned. | The IDML story is `Justification="CenterAlign"` for the whole headline (verified in `Story_u1342.xml`). A single-Run frame's only paragraph is closed by `<trail>`, so `ALIGN` must live in `trail_attrs` (the sibling `u1358` carries it there and renders centred). The width 58.4538mm is the IDML `TextColumnFixedWidth` (165.696pt) — the text centres in the column, not the wider frame; using the column width lands the centred lines on the baseline's text-column centre. |
| F3 | `u133f_l2` (Vollkorn "dreizeilige" line) `y_mm` (build.py) | `y_mm=57.7804` → `59.9813` (+6.24pt) | `line_spacing_pixel_audit` 2 major drifts (>3pt) → 0 major. The pixel audit (authoritative) measured the Vollkorn line ink-top 6.24pt too high vs baseline — Vollkorn Black Italic's cap-top sits higher than the IDML expects under FLOP top-align. | The shift is exactly the measured pixel drift (6.24pt = 2.2009mm). Only the one Vollkorn split frame moved; the two Gotham lines (`u133f`, `u133f_l3`) measured 0.0 / 0.48pt and were left untouched. `per_region_regression` clean after the edit. |
| F4 | `# noinject:` comment on ImageFrame `u1386` (build.py) | `external_asset_substitution_audit`: 1 missing → 0 | Cleared `external_asset_substitution_audit` (`u1386` flagged "missing INJECT_MAP/noinject"). | `u1386` is the genuine IDML-placed radial-gradient vignette overlay (`Schwarzer Verlauf radial.psd`) — real template content, a fixed dark vignette over the page-6 portrait so the white citation stays legible. Not a substitutable demo photo. `# noinject:` with a content reason is the audit's documented correct disposition. |

### Tolerance cap growth

| Audit | Cap before → after | Reason |
|-------|--------------------|--------|
| `text_position_audit_jitter` | 35 → **38** | The jitter count rose 19 → 37 because the F1 `SpaceAfter` fix moved ~207 words off the structural (>5pt) cascade — the tail of that correction lands sub-5pt in the jitter bucket. Same cross-renderer line-wrap root cause, `severity: cosmetic`, sub-perceptible (≤5pt). The bump is the smallest that covers the post-fix count (37 + 1 headroom). No other cap grew; structural/systematic/visual_diff/image_audit all hold within prior caps with room to spare. |

### Accepted residuals — preflight RED (documented, genuinely unclosable in Stage 2)

| Audit | Residual | Classification | Reason accepted |
|-------|----------|----------------|-----------------|
| `line_match_audit` | 16 of 70 lines mismatched | scribus-engine | 2 rotated Impressum frames (`u11fd`/`u126f`, Δ28.34pt = the 10mm frame width — Scribus centres `-90°`-rotated `VerticalJustification=CenterAlign` text on the opposite cross-axis edge; documented rotated-frame engine limit). 6 body line-wrap differences (`u1242`, `u129e` — Scribus breaks justified paragraphs at different words). 8 sub-2pt centred-line residuals (`u133f`×3 Δ~1.2pt, `u12fb` Δ-1.9pt, `u1390`×2 Δ~1.8pt — the ~0.75% Vollkorn/Gotham glyph-width difference shifts a centred line's start by ~half the width delta; `u1358` Δ-1.47pt rotated). `bin/tune-fix` exhausted every playbook; `line_spacing_sim` returned no rows. No single fix closes these. |
| `text_position_audit_structural` | 46 large drifts (>5pt) | scribus-engine | Cross-renderer line-wrap. Down from 253 (the F1 `SpaceAfter` fix). The remaining 46 are 2 wrap events (`u1242`, `u129e`) cascading downstream words on their pages. Page content + frame geometry verified correct. Within cap 260. `severity: structural` — preflight stays red by design. |
| `systematic_text_audit` | 6 frames sim-actionable | scribus-engine | `line_spacing_sim` returned no rows for every frame — line-WRAP-count divergence, not a leading value. `line_spacing_pixel_audit` confirms per-line GAP is correct in both renderers. Within cap 11. |
| `image_frame_visibility_audit` | 1 faint frame: `u1386` | accepted (CMYK→sRGB tone) | `u1386` visibility_ratio 0.686, `asset_render_ratio` 0.987 — the radial vignette renders, just lighter than baseline (small CMYK→sRGB tone shift on the dark PSD; the brief classifies this acceptable). 0 invisible frames. |

### Audits driven GREEN this pass

`squiggle_alignment_audit` (8 yellow squiggles, all on their words),
`idml_attribute_coverage` (0 unconsumed), `image_content_audit`
(5 ok / 0 broken), `text_render_audit` (all text rendered),
`per_region_regression` (no regression), `frame_vertical_position`
(no finding — the prior `u1358` finding cleared), `inventory` (exit 0).
The DIE GRÜNEN logo `u1336` `asset_render_ratio` 0.849 — well above
the 0.35 floor.

---

## Prior pass (history)

| # | What | Values (before → after) | Drift it resolves | Why conservative | Classification |
|---|------|--------------------------|-------------------|------------------|----------------|
| 1 | Converter fix — rotated-TextFrame W/H convention (`tools/idml_to_dsl.py`, TextFrame emission) | `_compute_page_local_bbox_pt` un-rotated extent passed straight through → for ±90° non-empty TextFrames, converted to the axis-aligned-bbox-of-rotated-rect form before emission | `text_render_audit`: 2 words missing (`impressum`, `xxxxxx` → clipped to `impressu`), `per_region_regression`: 2 regressions (`u137f`, `u1386`). The `de96b7c`/`5e48f81` rotated-frame branch in `_compute_page_local_bbox_pt` emits the *un-rotated* frame extent + pivot — correct for ImageFrames and empty background frames. But the TextFrame primitive (`sla_lib/builder/primitives.py`) applies a text-flow W/H swap to any ±90° frame carrying text. Feeding it the un-rotated model AND letting it swap is a double-correction: the visible Impressum frames (`u11fd`, `u126f`) collapsed from a 53.4mm-wide text strip to a 10mm-wide one and clipped after 8 characters. | The fix is in the converter (Stage-1-permitted; structural gate failure). It is scoped to ±90° **non-empty** TextFrames only — the un-rotated model is left untouched for ImageFrames and empty background frames, which the primitive places verbatim. The conversion is closed-form geometry (axis-aligned bbox of the rotated rectangle), not a guess; verified the result reproduces the pre-`dcc52c7` working `u11fd` geometry exactly (`x=95, y=82.6, w=10, h=53.4`). | converter-bug — fixed in Stage 1 |
| 2 | Frame `u1336` (DIE GRÜNEN logo): `inline_image_data` + `scale_type=1` → `image=` ref + `scale_type=0` (build.py) | `inline_image_data`+`inline_image_ext='png'`+`local_scale=(0.284972,…)`+`scale_type=1` → `image='…/gruene-logo-bund-weiss-cmyk.png'`+`scale_type=0` | `image_frame_visibility_audit`: `u1336` `invisible_in_preview` (visibility_ratio 0.0) → `ok` (0 invisible frames). The white-on-transparent RGBA logo did not render at all under the inline+`scale_type=1` path. | This is the SKILL's documented `frame_visibility` playbook fix (swap `inline_image_data` → `image=` ref with `scale_type=0`). The asset is on disk and identifiable. `scale_type=0` (fit-to-frame) is correct for a logo. No geometry guesswork. The `bin/tune-fix` `frame_visibility` playbook escalated ("not inline_image_data form, or asset name unknown" — it could not auto-resolve the asset basename), so the documented swap was applied by hand and re-rendered. Re-applies the prior tune's TOLERANCE_LOG row 2 that the re-import dropped. | scribus-engine (Scribus 1.6.x SCALETYPE=1 + small RGBA white-on-transparent PNG renders transparent) — resolved |
| 3 | `# noinject:` comment on ImageFrame `u1386` (build.py) | external_asset_substitution_audit: 1 missing → 0 (`noinject_justified: 1`) | Cleared `external_asset_substitution_audit` (`u1386` flagged "missing INJECT_MAP/noinject"). | `u1386` is the genuine IDML-placed radial-gradient vignette overlay (`Schwarzer Verlauf radial.psd`), real template content — not a demo placeholder. `# noinject:` with a content reason is the audit's own documented correct disposition. Only one frame is flagged this pass (vs four in the prior run) — the `de96b7c` crop fix routes the three photo frames through `crops/` so the audit no longer flags them. Re-applies the prior tune's comment that the combined-fidelity re-import dropped. | not-a-tolerance (correct disposition); logged for transparency |
| 4 | Frame `u12b5` (page 4 body text): `h_mm` widened 63.5mm → 71.0mm (build.py) | `h_mm=63.5` (IDML PathPointArray geometry) → `h_mm=71.0` | `text_render_audit`: 2 words missing in render (`maioriat`, `fuga.`), `inventory` regression (preview_pdf_count 337→335, `maioriat` in `missing_from_preview`). At the IDML `h_mm` Scribus wraps the justified body to 12 lines vs InDesign's 11 (cross-renderer wrap drift); per-line drift accumulates ~0.5pt/line (`line_spacing_pixel_audit` cumulative 11.52pt) until the last line `"…sed maioriat fuga."` falls below the frame and clips. InDesign overflows silently. | `+7.5mm` is the smallest widening that clears the overflow with ~1.5-line headroom. The frame is top-aligned and the page below `u12b5` is empty (next-lowest item bottom is at y=65.3mm vs the widened bottom y=136.3mm; A6 page height ~140mm) — no overlap introduced. This re-applies the prior tune's `u12b5` widening (prior value 74.79mm) that the combined-fidelity re-import dropped; this pass needs less (`+7.5` vs the prior `+11.3`) because the R5 trailing-`<Br/>` converter fix removed the doubled empty paragraphs that previously inflated the frame's line count. `inventory` gate exit 0 and `text_render_audit` OK after the edit. | scribus-engine (cross-renderer line-wrap count divergence; Scribus clips, InDesign overflows) — resolved |

## Accepted residuals (preflight not green)

The Stage-2 `bin/tune-render` → `bin/tune-fix` loop drove the image,
squiggle, attribute-coverage and text-render audits fully green but
could not drive the text-position audits green; the residuals below
are accepted per the overnight gate policy (scribus-engine class).
`bin/tune-fix` exhausted every playbook — the `line_spacing` simulator
returned **no rows** for all 9 frames, confirming the drift is
line-wrap-count divergence, not a leading value no playbook can
address. The two red audits below carry `severity: structural` in
`TOLERANCES.yml`, so they are DOCUMENTED but deliberately do not flip
preflight to green; the render was promoted via `bin/tune-render
--no-transactional` because the structural cross-renderer line-wrap
floor cannot be closed in Stage 2 (same terminal state as the prior
committed run, which also shipped with a red preflight).

| Audit | Residual | Classification | Reason accepted |
|-------|----------|----------------|-----------------|
| `text_position_audit_structural` | 253 large drifts (>5pt) | scribus-engine | Cross-renderer line-wrap differences. Scribus and InDesign break the justified body / bullet-list paragraphs at slightly different words (font-metric / hyphenation models differ). One wrap-point difference flips a word from end-of-line to start-of-line (dx ≈ -160…-187pt) and cascades downstream. Page content and frame geometry verified correct by page-by-page visual diff (pages 1, 5, 6). Not a converter or routing bug. Within the `TOLERANCES.yml` cap (260); 253 this re-render vs 254 the prior overnight run. `severity: structural` — preflight stays red by design. |
| `text_position_audit_jitter` | 19 sub-perceptible drifts (≤5pt) | scribus-engine | Sub-perceptible (≤5pt) cross-renderer position jitter, below the visible threshold. The `y_mm_shift` playbook emitted only tentative recommendations ("no reliable calibration frame — no line-count match"); no deterministic shift could be derived. This audit is green under the tolerance cap (35). 19 this pass vs 30 the prior run. |
| `systematic_text_audit` | 9 frames sim-actionable | scribus-engine | The `line_spacing` playbook's simulator (`tools/line_spacing_sim.py`) returned **no rows** for every one of these 9 frames. `line_spacing_pixel_audit` confirms the root cause is line-COUNT divergence (u1242 16→17, u129e 10→9, u12b5 11→12) — and the per-line GAP is correct in both renderers (baseline gaps 13.9-14.9pt == preview gaps 13.9-14.9pt). No single (LINESPMode, LINESP) reconciles a wrap-count difference. Within cap (11); `severity: structural` — preflight stays red by design. 9 this pass vs 10 the prior run. |
| `visual_diff_regions` | 59 hot regions | scribus-engine | Derivative of the cross-renderer line-wrap. The worst region on every page is a body-TEXT band — NOT a photo band. This is the goal outcome of the fidelity pass: the worst regions are text-driven, not image-driven. `visual_diff_regions` no longer phase-errors. Within cap (65). |
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
- The Stage-2 hand-edits (rows 2-4) are inline in `build.py`. They
  will be lost on a clean re-import (no `inject.yml` reconciler path
  for image-ref swaps or `h_mm` overrides); preserved here per the
  protocol. The combined-fidelity re-import this pass dropped all
  three; they were re-applied identically (row 4's `h_mm` value is
  smaller than the prior pass's because of the R5 trailing-`<Br/>`
  converter fix — see row 4).
- `squiggle_alignment_audit` (ground-truth): `ok: true`, 0 issues. All
  8 squiggle PolyLines carry `fill='Gelb'` (yellow) and the audit
  reports every one `status: ok` with `vgap_mm` ≈ 0 — the squiggles
  sit on their words.
- `idml_attribute_coverage` (Phase E5f): `ok: true`, 0 issues — "all
  significant unconsumed attributes accounted for (920-entry
  baseline)". No new significant unconsumed attribute.
- The five newly-consumed Tier-A attributes, as they land in this
  template: `BlendingSetting/Opacity` → `fill_opacity` 0.7/0.7/0.9 on
  3 frames (`u1386` the radial vignette at 0.9); `VerticalJustification`
  ("CenterAlign") → `vertical_text_align=1` → SLA PAGEOBJECT `ALIGN="1"`
  on the two rotated Impressum frames `u11fd`/`u126f` (text vertically
  centred); `SpaceAfter` → `space_after_pt=5.6693` on the
  `fliesstext-auf-weissem-hintergrund` body style → SLA STYLE
  `NACH="5.6693"` (paragraph spacing below white-background body
  paragraphs). `TextColumnCount`/`TextColumnGutter`: every frame in
  this template is single-column (`TextColumnCount="1"`), so the
  converter correctly omits `columns`/`col_gap_pt` — no multi-column
  text exists here to apply them to.

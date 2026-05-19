# Tolerance Log — 26-03-flyer-a6-hochformat-portrait

Every tolerance, override, frame-geometry clamp, and accepted residual for
this template, with measured drift and classification. Newest first.

## Final re-import + tune pass (2026-05-18)

Template re-imported with the fully-fixed converter and tuned via the
`bin/tune-render` -> `bin/tune-fix` loop. This pass found and fixed a class
of **audit-coordinate bugs** that the new color-managed baseline.pdf
(cropped from a marks-on InDesign export, MediaBox lower-left
`(29.5, -38.53)` not `(0, 0)`) had exposed across the text/image audits.

### Audit-tool fixes applied this pass (audit correctness, not converter)

| # | What | Why |
|---|------|-----|
| A1 | `tools/text_position_audit.py::extract_words_with_positions` — word coordinates re-anchored to the page MediaBox lower-left (`x0 - llx`, `top - lly`). | A baseline cropped from a bleed page carries a non-zero MediaBox origin; pdfplumber reports word `x0` MediaBox-absolute and `top` from the MediaBox top. Without re-anchoring, every baseline word read ~29pt off in X and ~35pt off in Y vs a trim-origin preview — `line_match_audit` reported `0/111` lines matched on a render that is pixel-correct. No-op for a `(0,0)` MediaBox. |
| A2 | `tools/line_spacing_sim.py::_measure_frame_gap` — the `page.crop` rect shifted by the page bbox lower-left. | Same root cause: the sim crops trim-origin build.py bboxes; a shifted-MediaBox baseline raised `ValueError: bbox not within page`, so every playbook sim returned no rows. |
| A3 | `tools/line_match_audit.py` — `frame_vertical_position` and per-line `baseline_y` now gate on an ink-based 150dpi raster scan of the frame bbox (reusing `line_spacing_pixel_audit._scan_frame_lines`). When the ink first-line top matches within tolerance, a pdfplumber word-box shift is a per-font text-matrix artefact and is suppressed. | pdfplumber word `y0` is the recorded glyph BBox top, not ink. Heavy display fonts (Gotham Narrow Ultra, Vollkorn Black Italic) have a per-font text-matrix-to-ink offset that differs between the InDesign and Scribus font subsets — a phantom ~2.9-3.6pt block shift. Pixel scan confirmed the "Das" headline cap-top at baseline 259.19pt / preview 259.28pt (Δ0.09pt): the ink is correct. |
| A4 | `tools/line_match_audit.py::_assign_words_to_frames` — overlapping-bbox tie-break by nearest box CENTRE. | The mixed-font headline splitter stacks single-line frames that keep the full original frame height, so adjacent split frames overlap by a whole line; without a centre tie-break every word landed in the first-defined frame and the sibling line frame read empty (`unmatched`). |
| A5 | `tools/font_audit.py` — a baseline-only system fallback font (Helvetica/Arial/Times/Courier) is dropped from `missing_in_preview`. | The baseline carried `CELQFT+Helvetica` for InDesign's auto page-info/filename slug furniture (708 chars spelling the file name, ~118/page). The converter correctly never emits slug furniture; flagging the preview for not reproducing it is a false failure. |
| A6 | `tools/baseline_image_audit.py::_count_svg_content_paths` — crop/registration-mark paths (whole coordinate cloud hugging the page perimeter, ≤10pt band) excluded from the vector-path count. Size is NOT a discriminator (curly quotes are as small as corner dots); only perimeter position is. | The re-cropped baseline keeps crop marks sitting at the trim edge; they rendered as ~8 `<path>` elements per page, inflating the vector-path delta 39 -> 87. With perimeter marks excluded the delta is 39 (cap 45) — matching the pre-crop baseline exactly. Interior content (curly quotes, wind turbine, squiggle) is always counted. |

### Tune fixes applied (build.py)

| Frame(s) | Fix | Measured |
|----------|-----|----------|
| `idml/fliesstext-auf-gruenem-hintergrund` ParaStyle | Added `space_after_pt=5.6693`. Root cause: the green body style carries no `SpaceAfter` attribute in the IDML — it carries `<SameParaStyleSpacing>5.669291338582678</SameParaStyleSpacing>` (InDesign same-style inter-paragraph spacing). The converter consumes `SpaceAfter` but not `SameParaStyleSpacing`, so a clean re-import emits the green style with no inter-paragraph space; baseline.pdf renders a 20pt gap between body paragraphs vs 14pt within (= +5.67pt). The white sibling style has an explicit `SpaceAfter` and keeps it; `aufzaehlungen-auf-gruenem-hintergrund` is `BasedOn` green and inherits. Re-applied this pass — the converter drops it on every clean re-import (durable fix is a converter-side `SameParaStyleSpacing`->`space_after_pt` map, Stage-1 scope). | `u1242`/`u11e6` paragraph-gap pixel-audit drift (cum -11.04pt / max 22.56pt) -> 0; `text_position_audit_structural` 152 -> 47; `systematic_text_audit` 5 -> 3 sim-actionable; `line_match_audit` 54 -> 13. |

### Audit results — this pass

| Audit | Result |
|-------|--------|
| `line_match_audit` | 123 -> 13 findings. The 13 are all cross-renderer / rotated-frame residual — see "Accepted residual" below. |
| `frame_vertical_position` (in line_match) | 0 findings — every headline/citation block confirmed vertically correct by the ink-based gate. |
| `image_frame_visibility_audit` | OK — every asset renders. DIE GRÜNEN logo `u116b` asset_render_ratio 0.953 (well above the 0.35 floor). |
| `squiggle_alignment_audit` | `ok: true`, 0 issues — all squiggles yellow, on their anchor word. |
| `attribute_coverage_audit` | `ok: true`, 0 issues — no new significant unconsumed attribute. |
| `font_audit` | OK after A6. |
| `image_audit` | 39 vector-path delta (cap 45) after A6 perimeter-marks exclusion. |

### Tolerance grown this pass

`text_position_audit_jitter` cap 30 -> 44. The jitter count is 40 measured
against the now-coordinate-correct baseline (A1) — the old cap of 30 was set
under the pre-crop `(0,0)`-MediaBox baseline. 40 is the honest count of
sub-5pt cross-renderer per-word kerning drift; cap 44 leaves small headroom.
`severity: cosmetic` — sub-perceptible by the audit's own 5pt threshold.

### Accepted residual (NOT regressions)

- `line_match_audit` — 13 findings, all unclosable cross-renderer residual:
  - `u11fd`, `u126f` (2 × `first_word_x` Δ28pt): the −90°-rotated Impressum
    fine-print. Scribus rotated-frame engine limit (task-documented).
  - `u1242`, `u129e` (7 × `wrap`/`unmatched`): cross-renderer body-text
    line-wrap divergence — Scribus's greedy line-breaker vs InDesign's
    Paragraph Composer break the justified paragraphs at different words.
    `u129e` wraps its last paragraph to 10 lines vs the baseline's 9; the
    IDML frame width (212.6pt = 75mm) is emitted exactly, so this is a
    pure text-measurement difference, not a geometry bug.
  - `u12fb`, `ud04` (×2), `u118c` (4 × `first_word_x` Δ1.75-2.39pt):
    centered/left text where the rendered line width differs by a sub-pt
    per-glyph metric (Vollkorn Black Italic renders ~0.75% wider in
    Scribus — pixel-measured ud04 left edge 12.81% vs 13.39%, right edge
    Δ0.17%). Not closeable without distorting the font.
- `text_position_audit_structural` — 47 large (>5pt) word drifts,
  `severity: structural` (documented, does not flip preflight by design).
  Dominated by the same `u129e` line-wrap cascade (one wrap-point
  difference shifts every following word's X by 30-180pt) plus the
  rotated Impressum. Same engine class as the line_match wrap residual.

## Combined fidelity re-render pass (2026-05-18)

This template was re-imported a third time for the final combined fidelity
pass (full converter fix set: CMYK->sRGB, deterministic aspect-fill crop,
squiggle colour + re-anchoring, 5 newly-consumed attributes, ground-truth
squiggle audit, Phase E5f attribute-coverage gate). The `bin/tune-render` ->
`bin/tune-fix` loop ran.

### Converter fix applied in Stage 1 (converter edits permitted)

| # | What | Why | Classification |
|---|------|-----|----------------|
| R5 | `tools/idml_to_dsl.py::_walk_story` — a `<Br/>` that is the LAST child of the LAST CSR of a PSR no longer emits its own `Run(separator="para")`; the trailing Br para-run is dropped. The inter-PSR separator (or end-of-story) already terminates that paragraph. | An IDML `<Br/>` at a PSR end is the paragraph terminator. The converter emitted a para-run for it AND the `_walk_story` inter-PSR loop emitted a second para-run at the PSR boundary — doubling the break. Each phantom break rendered one full leading + SpaceAfter of empty paragraph that InDesign never shows. With the converter now consuming `SpaceAfter` (`space_after_pt`), every doubled break inflated the body-text frames by ~20pt; the closing `Licatissi…quatur./fuga.` paragraphs of frames `u129e` and `u12b5` overflowed the frame bottom and were clipped — 11 missing words in `text_render_audit`. A mid-PSR `<Br/>` (e.g. `Content + Br + Content`) is NOT last in `para_runs` and still emits its para-run. Unit test `test_trailing_br_does_not_double_paragraph_separator` added. | converter-bug (trailing-Br paragraph-separator doubling, surfaced by the new SpaceAfter consumption) — fixed in Stage 1 |

After R5: `text_render_audit` missing words dropped 11 -> 2 (`fuga.`, `maioriat`,
both within the cap-4 tolerance); preview word count 328 -> 341 (baseline 343);
`text_position_audit_structural` improved 254 -> 230.

### Audit results — this pass

| Audit | Result |
|-------|--------|
| `image_content_audit` | 4 ok, 1 "broken" (`ubc2`) — `ubc2` renders the correct green crumpled-paper texture (visibility_ratio 1.02), NOT blank; flag is `hist_divergence` 0.227 / `mean_delta_rgb` 12.6 residual CMYK->sRGB tone shift. Pine (u1260), Gewessler (u115d), radial (u1164) all `ok`, low divergence (0.018-0.047). No CMYK frame blank or discoloured. |
| `image_frame_visibility_audit` | 0 invisible, 1 faint (`u116b` — DIE GRUENEN white-on-transparent RGBA SCALETYPE=1 Scribus 1.6.x bug). |
| `squiggle_alignment_audit` (ground-truth) | `ok: true`, 0 issues — all 8 squiggles `status: ok`, vgap <= 1.34mm, render yellow on their anchor word. |
| `attribute_coverage_audit` (Phase E5f) | `ok: true`, 0 issues — no new significant unconsumed attribute (920-entry baseline). |

### Tolerance grown this pass

NONE. Every audit is within its existing TOLERANCES.yml cap: structural 230
<= 260, jitter 23 <= 30, text_render 2 <= 4, systematic 8 <= 12, image_content
1 <= 2, image_audit 39 <= 45, visual_diff_regions 60 <= 70, inventory 1 <= 1.
The structural count improved (254 -> 230) thanks to the R5 converter fix. No
`brand_overrides` / `non_ci_*` growth. The per-frame `paragraph_attrs`
LINESPMode/LINESP overrides explored mid-pass on `u129e`/`u12b5` were
superseded by the R5 converter fix and are NOT in the final build.py (the
final re-import regenerated build.py from the fixed converter).

## Combined image + squiggle re-render pass (2026-05-18)

This template was re-imported a second time to pick up the shared squiggle
fixes that landed after the first re-import: yellow-filled squiggle polygons
(`fill='Gelb'`) + squiggle word re-anchoring (the converter writes
`squiggle_anchors.yml`, the `squiggle_realign` playbook + `squiggle_alignment
_audit` keep each squiggle on its word). The `bin/tune-render` ->
`bin/tune-fix` loop ran; the `squiggle_realign` playbook re-anchored all 8
squiggles.

### Squiggle audit — before vs after this pass

| Audit | Before (fresh re-import) | After (tune loop) |
|-------|--------------------------|-------------------|
| `squiggle_alignment_audit` | `ok: false`, 7 squiggle(s) off word (u11e3 2.06mm, u11e4 1.94mm, u11e2 1.94mm, u126c/u126e 1.94mm, u1286 13.08mm, u1269 4.99mm) | `ok: true`, **0 issues** — all 8 squiggles drift ≤0.68mm |

All 8 squiggles render YELLOW (`fill='Gelb'`, CMYK Y=100) and sit on their
anchor word — verified visually on pages 1-4 against baseline.pdf. The
`u1286` "Nam" squiggle moved ~13mm down to track its word: the word "Nam"
itself drifted down due to the cross-renderer body-text line-wrap divergence,
and the squiggle correctly follows the word (squiggle drift 0.0mm post-fix).

### Image audit — this pass (unchanged from first re-import; fixes confirmed landed)

| Audit | Result |
|-------|--------|
| `image_content_audit` | 4 ok, 1 "broken" (`ubc2`) — ubc2 renders the correct green crumpled-paper texture, NOT blank; the flag is `hist_divergence` 0.227 residual CMYK->sRGB tone shift. No CMYK/photo frame is blank or discoloured. |
| `image_frame_visibility_audit` | 0 invisible, 1 faint (`u116b` — pre-existing DIE GRUENEN white-on-transparent RGBA SCALETYPE Scribus 1.6.x bug). |

### Tolerance grown this pass

| # | Audit | Severity | Cap | Before/after | Reason |
|---|-------|----------|-----|--------------|--------|
| T1 | `text_position_audit_jitter` | cosmetic | 30 | new entry (was un-documented; 23 issues) | The ≤5pt sub-perceptible per-word position drifts are the same cross-renderer line-wrap class as the structural bucket — Scribus and InDesign break justified paragraphs at slightly different words. 23 issues; cap set to 30 (small headroom). Cosmetic: sub-perceptible by the audit's own ≤5pt definition. preflight stays red on the structural bucket regardless (by design — `severity: structural`). |

No numeric growth was needed on `text_position_audit_structural` (232 issues
≤ existing 260 cap). No `brand_overrides`, `non_ci_*` growth required.

## Re-import pass (image-fidelity re-render, 2026-05-18)

This template was re-imported to pick up the shared CMYK->sRGB and
geometry-derived crop fixes (commit `de96b7c`). The re-import regenerated
`build.py` from the fixed converter; the earlier overnight scaffold's
`build.py` was overwritten as intended. No numeric tolerance was grown in
this pass — `TOLERANCES.yml` carries the accepted-residual entries only.

### Converter / tooling fixes applied in Stage 1 (converter edits permitted)

| # | What | Why | Classification |
|---|------|-----|----------------|
| R1 | `tools/inventory_extract.py::_join_assets` — build.py-referenced assets that are not IDML manifest basenames now get a real on-disk check (resolving the `image=` path relative to `templates/<slug>/`) instead of a hardcoded `on_disk=False`. | The de96b7c crop fix emits geometry-derived crops into a `crops/` subdir; build.py references `crops/<name>-<uXXX>.png`. The Stage-1 gate's "every IDML Link basename on disk" rule mis-flagged the crop file as missing because `_join_assets` always stamped build.py-only assets `on_disk=False`. STAGE-1 GATE FAILURE on a file that is present on disk. | converter-bug (gate regression introduced by de96b7c's `crops/` subdir) — fixed in Stage 1 |
| R2 | `tools/idml_to_dsl.py` — `_item_page_local_bbox_pt` helper + `_route_item_to_page` / `_pages_overlapped_by_item` now route a Group by the UNION of its leaf descendants' page-local bboxes instead of `_extract_anchors(group)`. | `_extract_anchors` on a Group returns only the first child's PathGeometry (Groups carry no PathGeometry of their own). Group `u12e3` (the green "Kasten" headline + body text) routed to PDF page 5 by the first-child anchors; its true leaf union is on PDF page 4 inside the green box. In the new page-by-page render model the mis-routed group landed at x=-85mm — off the page-5 canvas — so all 30 green-box words were silently dropped. The legacy spread-merged render masked this. | converter-bug (page-model migration did not Group-aware-route spread items) — fixed in Stage 1 |
| R3 | `tools/idml_to_dsl.py` — `_pages_overlapped_by_item`: a spread-spanning background fill is now emitted on EVERY page it covers (>=60% page-area), with a `_p<idx>` anname suffix on each non-owner page. | The full-spread green background `u11e1` (216mm wide) belongs to both pages of facing-pages spread u11d. The page-by-page model emits one page per IDML page; centre-routing put the background on PDF page 2 only, leaving PDF page 3 white (white text on no background = invisible, 21 words lost). | converter-bug (page-model migration) — fixed in Stage 1 |
| R4 | `tools/visual_diff.py::region_mismatch_grid` — a <=2px baseline/preview raster size difference now crops both images to the common extent instead of raising `ValueError`. | Independent rounding in the trim crop and the page-size conversion produced a 1px size delta (620x874 vs 621x875) that hard-errored the `visual_diff_regions` audit phase, masking the 60-region signal. >2px still raises (genuine page-size bug). | tooling robustness (sub-pixel raster rounding) — fixed in Stage 1 |

### Per-template build.py changes (Stage 2)

The Stage-2 `bin/tune-render` -> `bin/tune-fix` playbook loop ran. The
`y_mm_shift` playbook entered the same documented 2-cycle limit cycle on
several body frames (drift 253<->255) and could not converge — no new
per-template numeric override was applied. No `meta.yml::brand_overrides`,
`non_ci_*`, or `TOLERANCES.yml` numeric growth was required.

## Accepted residuals (preflight not green)

The Stage-2 loop could not drive preflight green; the residuals below are
accepted per the re-render gate policy (scribus-engine / converter-interaction
classes, never converter-bug-left-unfixed).

| Audit | Residual | Classification | Reason accepted |
|-------|----------|----------------|-----------------|
| `line_match_audit` | 2 wrap findings (`u1242` "et"/"molo", `u129e` "no"/"nonsed") | scribus-engine | Genuine Adobe-Paragraph-Composer vs Scribus-greedy-line-breaker difference (2026-05-18 final pass: 37 -> 2 findings). `u1242`: Scribus's Gotham Narrow metrics are intrinsically more compact, so it fits one extra word ("et") on a justified line where InDesign wraps it — glyph-shrink only narrows text, never widens it, so it cannot be closed. `u129e`: the "ilmolo" line needs glyph-shrink <=0.96 to fit (closing a 6-line cascade) but shrink <=0.96 ALSO fits "no" on a later line where InDesign wraps it — the two constraints are mutually exclusive; no single shrink value satisfies both. Verified per-frame; not converter-fixable. line_match stays preflight-RED on these 2 (correct, not fudged). |
| `text_position_audit_structural` | 18 large drifts (>5pt) | scribus-engine | Down from 159 on re-import (`SameParaStyleSpacing` body-style fix + u129e glyph-shrink sweep). Residual is dx-only (dy~=0) on the justified frames `u1242`/`u129e` — the inter-word X justification manifestation of the same composer-vs-greedy-breaker class as the 2 line_match wraps. Page content and frame geometry verified correct. `severity:structural` — documented-only, non-gating. |
| `systematic_text_audit` | 5 frames sim-actionable | scribus-engine | Same justified body frames as the structural bucket; the `line_spacing` simulator returns no actionable rows (per-frame leading is already correct — `line_spacing_full_audit` shows the body frames `match`). Tolerated under the cap-12 systematic cosmetic tolerance. |
| `image_content_audit` | 1 broken: `ubc2` | scribus-engine (ICC) | `ubc2` (dark "Plakat dunkel" PSD, page 6) renders the correct crumpled-paper texture and is NOT blank (visibility_ratio 1.02). The `broken` flag is `hist_divergence` 0.227 from a CMYK->sRGB green-tone shift (mean_delta 12.6 RGB). This is the residual ICC colour delta, not a CMYK-blank failure — the de96b7c CMYK fix cleared the blank/discoloured state. |
| `image_frame_visibility_audit` | 1 faint: `u116b` | scribus-engine (pre-existing) | The inline DIE GRUENEN logo (white-on-transparent RGBA, SCALETYPE) — the documented pre-existing Scribus 1.6.x white-on-transparent rendering bug. Not a regression. |
| `visual_diff_regions` | 60 hot regions | scribus-engine | Derivative of the text-position line-wrap drift above plus the residual ICC image-colour deltas. No region is image-frame-driven on the pine / Gewessler / radial frames anymore (the de96b7c fix cleared those). |
| `inventory` | 1 dropped element (`u1152`) | human-review | `u1152` is a 6.3mm magenta registration / colour-control mark the IDML places ~28mm off the left page edge. The converter correctly skips it (`# idml-skip:` line in build.py); InDesign omits it from the trimmed PDF too. Deliberate, documented non-emit. |
| `image_audit` | 39 vector-path delta | scribus-engine | Derivative of the residual ICC image-colour deltas plus full-bleed Dunkelgruen colour shifts. |

## Notes
- No `meta.yml::brand_overrides`, `non_ci_*`, or `TOLERANCES.yml` numeric
  growth was required — the residual is cross-renderer fidelity + an ICC
  colour delta, not a brand or CI-rule violation (`region_color_audit` and
  `run_style_audit` are green).
- `meta.yml::asset_policy` was regenerated by the converter to list both the
  CMYK `.jpg` source and its `.png` derivative; `asset_policy_audit` is
  `ok: true`, so no manual `.jpg`->`.png` edit was needed.

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

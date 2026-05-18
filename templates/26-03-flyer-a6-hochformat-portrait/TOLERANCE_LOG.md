# Tolerance Log — 26-03-flyer-a6-hochformat-portrait

Every tolerance, override, frame-geometry clamp, and accepted residual for
this template, with measured drift and classification. Newest first.

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
| `text_position_audit_structural` | ~230-254 large drifts (>5pt) | scribus-engine | Cross-renderer line-wrap divergence: Scribus and InDesign break the justified body / bullet paragraphs at slightly different words (font-metric / hyphenation model differences). One wrap-point difference cascades into dozens of downstream "drifted" words. Page content and frame geometry verified correct page-by-page. Documented known issue for this batch. |
| `text_render_audit` | 2 words (`impressum`, `xxxxxx` -> `impressu` + `m: xxxxxx`) | scribus-engine / converter-interaction | The three rotated -90deg 6pt "Impressum: xxxxxx" edge frames (`u11fd`, `u126f`, `u12fb`) wrap to 2 lines. NO text is lost — every character renders, the string is split across 2 lines. Root cause: the converter now emits the geometrically-correct un-rotated frame extent (53.4x10mm), and `tools/sla_lib/builder/primitives.py`'s rotated non-empty-TextFrame W/H swap (de96b7c) then yields a 10mm text-flow width, forcing the wrap. `primitives.py` is forbidden to Stage 2. Cosmetic 2-line wrap of tiny edge furniture; flagged as a follow-up for the converter/primitives swap reconciliation. |
| `systematic_text_audit` | 9 frames sim-actionable | scribus-engine | Same frames as the structural / jitter bucket; the `y_mm_shift` playbook 2-cycle-oscillates and the `line_spacing` simulator returns no actionable rows. Needs the documented playbook oscillation guard (follow-up). |
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

---
id: '24'
title: 'Zeitung remaining alignment: image content doesn''t fill frame (scale_type
  letterboxing) + page-by-page Codex audit'
status: done
priority: high
labels:
- bug
- templates
- dsl
source: github
source_id: 47
source_url: https://github.com/GrueneAT/vorlagen/issues/47
---

# Zeitung remaining alignment: image content doesn't fill frame (scale_type letterboxing) + page-by-page Codex audit

## Why

#23 fixed bbox-based geometry but the user reports Zeitung is still visibly misaligned on multiple pages — examples cited: page-1 right edge of Cover Hero image not aligned, page-14 image and green box not aligned. Direct probe of the post-#23 state confirms:

- **All bbox extents are correct** (Cover Hero `(-3, 0, 213, 155.6)` matches u2950 `(-3, 155.6, 213, 300)` outer extents; P13 Hero `(-3, 149.6, 207, 297)` matches Dunkelgrün polygon `(-3, -0.2, 207, 152.4)` outer extents).
- **But the rendered image content doesn't fill the frame.** 13 ImageFrames in Zeitung use `scale_type=1, ratio=1` (Scribus aspect-fit). When the asset's native aspect ratio doesn't match the frame's aspect, Scribus letterboxes — leaving white margins inside the frame, so the visible image content doesn't reach the frame's outer edges.

13 affected frames (sweep verified):
`Cover Hero` (pg 1), `P1 Hero` (2), `P2 Mid` (3), `P3 Hero` (4), `P4 Foto-Spread` (5), `P5 Hero` (6), `P7 Portrait` (8), `P10 Portrait` (11), unnamed (12), `P11 Bottom` (12), unnamed (13), `P13 Hero` (14), unnamed (14).

The bbox-based detector built in #22/#23 cannot catch this — it inspects frame extents, not rendered-content extents. **A new detection class is needed**, plus the user requested a comprehensive **Codex visual audit of all 14 pages** (not just the user-cited ones) to surface every alignment class the bbox detector misses.

## Scope

### Phase 1 — Codex visual audit of all 14 Zeitung pages (TDD-for-rules continuation)

Run `issue-cli review-exec --tool codex` with a prompt asking Codex to enumerate alignment issues per page in `templates/zeitung-a4-grun/page-{01..14}.png`. Output: structured Markdown list per page (frames involved, type of misalignment, drift if measurable). Save to `reviews/codex-zeitung-all-pages.md`.

Cross-check against `bin/audit-alignment zeitung-a4-grun --json` output. For every issue Codex sees that the audit misses, classify the misalignment class:
- **Letterboxing** (image content < frame extent due to aspect mismatch): expected primary class.
- **Other** (any unanticipated class — possibly z-order issues, color contrast, off-center placement of content within frame, etc.).

### Phase 2 — New rule(s) for the missed classes

For LETTERBOXING (the primary expected class):

**`brand:image_fills_frame`** (severity=ERROR for full-bleed frames, WARNING otherwise):
- For each ImageFrame with `scale_type=1, ratio=1`:
  - Compute the asset's native aspect ratio (via `Pillow.Image.open(asset_path).size`).
  - Compute the frame's aspect ratio (`w_mm / h_mm`).
  - If they differ by more than `tolerance_ratio_pct` (default 1%), Scribus will letterbox.
  - Severity = ERROR if the frame is "full-bleed" (any edge within `bleed` of page boundary or part of cover/spread). WARNING otherwise.
  - Suggestion in violation message: switch to `scale_type=0` with `local_scale=(s, s)` chosen for aspect-fill, OR re-crop the asset to match the frame's aspect.

For any other class Codex surfaces: extend `brand:visual_adjacency_drift` or add per-class rule. Iterate per #23's TDD-for-rules pattern.

### Phase 3 — Audit tool extension

`tools/audit_alignment.py` runs `brand:image_fills_frame` and surfaces letterboxing risks per template + per page. Suggested fixes inline.

### Phase 4 — Fix Zeitung's 13 letterboxed frames

For each of the 13 frames:
- Read the asset's native dimensions.
- Compute the required `scale_type=0` + `local_scale` to fill the frame on its short axis (aspect-fill).
- For very wide frames where aspect-fill would crop unacceptably, consider `local_offset_mm` to choose the crop window.
- Update `build.py`.
- Re-run audit; verify `brand:image_fills_frame` clean.

### Phase 5 — Geometric outcome tests

Extend `tools/sla_lib/tests/test_zeitung_geometry.py` with:
- For each fixed frame: assert the rendered-content bbox (computed from frame + scale_type + local_scale + asset native dims) matches the frame's outer extent (within 0.5 mm).
- These tests fail before Phase 4 lands; pass after.

### Phase 6 — Re-run Codex visual review post-fix

Re-run Codex visual review on regenerated PNGs. Cross-check: zero remaining alignment issues from the new rule perspective. If Codex still flags anything, return to Phase 2 and add another rule class.

### Phase 7 — Apply across other facing-pages templates

`brand:image_fills_frame` runs globally. Verify no regressions on other templates; pre-apply `brand_overrides` skip with reason "scheduled for follow-up audit" where appropriate.

### Phase 8 — Regen + SHA bump

`bin/render-gallery zeitung-a4-grun --skip-visual-diff`. Verify `bin/check-stale-previews` exit 0.

## Acceptance Criteria

- [ ] Codex visual review completed for ALL 14 Zeitung pages (output saved in `reviews/codex-zeitung-all-pages.md`).
- [ ] Every visual issue Codex identifies is captured by at least one BrandRule (existing or new). New rules are GENERIC (work on any template, no Zeitung-specific code).
- [ ] `brand:image_fills_frame` (or equivalent) added with full test coverage; severity ERROR for full-bleed frames.
- [ ] All 13 Zeitung letterboxed frames fixed (`scale_type=0` with computed `local_scale`, OR asset re-crop, OR `meta.yml::brand_overrides` if the letterboxing is intentional).
- [ ] `bin/audit-alignment zeitung-a4-grun --strict` exit 0.
- [ ] `python3 -m sla_lib.builder.structural_check --all` exit 0.
- [ ] `python3 -m unittest discover tools/sla_lib/tests` exit 0.
- [ ] `bin/check-stale-previews` exit 0.
- [ ] Re-run Codex visual review post-fix: zero remaining alignment issues from the new rule perspective.
- [ ] Geometric tests in `test_zeitung_geometry.py` pin rendered-content extent invariants for the 13 fixed frames.

## Out of scope

- Re-authoring Zeitung's design — only image-extent fixes.
- Other templates' alignment encoding (#19, #20, #21) — paused until Zeitung is verifiably clean per user directive.
- Promoting `bin/audit-alignment` to fatal CI step — defer.

## Dependencies

Depends on: #14, #22, #23 (constraint DSL + alignment rules + audit tool + Phase 4 geometry fix). Closes: nothing additional.

## Labels

bug, templates, dsl, zeitung

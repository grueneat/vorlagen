# Execution: V1 layout for `infostand-tent-card-a5-quer` (Hero Band)

**Started:** 2026-05-09
**Completed:** 2026-05-09
**Status:** complete
**Branch:** issue/20-v1-layout-for-infostand-tent-card-a5-quer-hero-band

## Pre-flight probe

- [x] **Logo asset probe (T01 prerequisite):** `shared/logos/gruene-weiss.png` exists (7411 bytes, 413×118 px wordmark per RESEARCH addendum). No fallback needed.
- [x] Baseline build: `python3 templates/infostand-tent-card-a5-quer/build.py` exits 0.
- [x] Baseline smoke: 9/9 PASS.
- [x] Baseline structural_check: 0 errors, 0 warnings, 6 skipped, 15 passes.

## Execution Log

- [x] T01: ParaStyles MUTATE+ADD+DROP + meta.yml ci_overrides extension — commit 25cb534
- [x] T02: build_template + build_preview split + INJECT_MAP scaffold + build_doc alias — commit fc356e9
- [x] T03: V1 Panel A layout via _panel_de helper — commit 576f400
- [x] T04: V1 Panel B layout via _panel_en helper — commit 8aa10c9
- [x] T05: V1 CONSTRAINTS list (22 entries, replaces 5) — commit 66f0e7b
- [x] T06: Regen template.sla + brand_overrides cleanup + slots rewrite — commit 09a2397
- [x] T07: README.md V1 deltas + QR D1 rationale + logo aspect note — commit 06d9dc9
- [x] T08: Smoke additions + spec rewrite + NEW geometry tests — commit 3a6df28
- [x] T09: Brief §10 row + EXECUTION.md final + ISSUE status=done — final commit pending

## Final Verification Gate

Run from worktree root after T09 commit:

```
python3 -m unittest discover tools/sla_lib/tests          # 733 tests, OK (skipped=2)
python3 -m unittest templates._smoke.test_infostand_tent_card_a5_quer  # 15 tests, OK
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check infostand-tent-card-a5-quer  # 0 errors, 4 warnings (cover_extent_match full-bleed pairs), 4 skipped, 35 passes
PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all  # 0 errors
bin/check-stale-previews                                   # exit 0
PYTHONPATH=tools python3 templates/_smoke/test_infostand_tent_card_a5_quer.py  # 15/15 OK
```

ALL exit 0.

## Summary

**Tasks completed:** 9/9 (T01..T09).
**Commits on branch beyond research/plan:** 9 (T01..T09).
**Files touched:**
- `templates/infostand-tent-card-a5-quer/build.py` (T01-T05; full V1 rewrite)
- `templates/infostand-tent-card-a5-quer/meta.yml` (T01 ci_overrides; T06 brand_overrides + slots)
- `templates/infostand-tent-card-a5-quer/template.sla` (T06 regen)
- `templates/infostand-tent-card-a5-quer/page-01.png` (T06 regen)
- `templates/infostand-tent-card-a5-quer/preview.pdf` (T06 regen)
- `templates/infostand-tent-card-a5-quer/README.md` (T07)
- `site/public/templates/infostand-tent-card-a5-quer/{template.sla,page-01.png,preview.pdf}` (T06 mirror)
- `templates/_smoke/test_infostand_tent_card_a5_quer.py` (T08; 9→15 tests)
- `templates/_specs/infostand-tent-card-a5-quer.md` (T08 full V1 rewrite)
- `tools/sla_lib/tests/test_infostand_tent_card_geometry.py` (T08 NEW; 21 invariants)
- `shared/brand/DESIGN-SYSTEM-BRIEF.md` (T09 §10 row)
- `.issues/20-.../{ISSUE.md, EXECUTION.md}` (T09 status flip + close)

**Tightenings beyond RESEARCH:**
- Empirical brand_overrides verification in T06 promoted MEDIUM-confidence prediction
  to evidence: 2 of 3 candidates removed cleanly; brand:image_fills_frame RESTORED
  (gruene-weiss.png 3.5:1 wordmark letterboxes 38×10.86 mm in 38×30 mm V1 logo frame
  by design; documented in README.md "Logo aspect note" + meta.yml override reason).
  Final brand_overrides count: 4 (vs plan's predicted 3).
- T08 geometry tests: 21 invariants (vs minimum 12 required) — covers cross-panel
  mirror, intra-panel containment, ParaStyle existence + V0 absence, Logo asset
  identity, Falz layer integrity, full rotation contract.

**No deferrals, no asset fallbacks needed.** Logo asset `gruene-weiss.png` confirmed
present (T01 probe).

## Deviations from Plan

### T06 — brand_overrides empirical verification (RESEARCH locked decision #10)

**Plan prediction (MEDIUM-confidence):** REMOVE 3 (`logo_size_3M`, `image_text_overlap`, `image_fills_frame`).

**Empirical result (after T06 render-gallery):**
- `brand:logo_size_3M` — REMOVED ✓ — runs PASS (38mm × 12.6 ≈ 3.02M conformant)
- `brand:image_text_overlap` — REMOVED ✓ — runs PASS (V1 text fully inside polygons)
- `brand:image_fills_frame` — **RESTORED with updated reason**: rule WARNs on Logo Grüne (panel A) and Logo Grüne (panel B) — gruene-weiss.png wordmark (3.5:1) renders letterboxed (38×10.86 mm) inside the 38×30 mm V1 logo frame. Photo INJECT_MAP frame fills exactly (LIVE frame dims used per T02 step 4 — verified). The Logo letterbox is deliberate per RESEARCH addendum (logo aspect note); restoring the override (rather than commissioning a `bund-weiss.png` 1:1 asset OR resizing logo frame to 38×11) is the V1 lock.

**Final brand_overrides count:** 4 (instead of plan's predicted 3).

**Kept with updated 2026-05-09 reasons:**
- `brand:line_spacing_0.9`
- `brand:visual_adjacency_drift`
- `brand:band_consistency`
- `brand:image_fills_frame` (restored)

## Discovered Issues

None yet.

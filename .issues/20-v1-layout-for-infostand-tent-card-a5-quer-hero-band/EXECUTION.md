# Execution: V1 layout for `infostand-tent-card-a5-quer` (Hero Band)

**Started:** 2026-05-09
**Status:** in_progress
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
- [ ] T06: Regen template.sla + brand_overrides cleanup + slots rewrite
- [ ] T07: README.md V1 deltas + QR D1 rationale + logo aspect note
- [ ] T08: Smoke additions + spec rewrite + NEW geometry tests
- [ ] T09: Brief §10 row + EXECUTION.md final + ISSUE status=done

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

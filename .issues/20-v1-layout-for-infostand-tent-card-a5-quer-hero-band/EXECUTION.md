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

- [ ] T01: ParaStyles MUTATE+ADD+DROP + meta.yml ci_overrides extension
- [ ] T02: build_template + build_preview split + INJECT_MAP scaffold + build_doc alias
- [ ] T03: V1 Panel A layout via _panel_de helper
- [ ] T04: V1 Panel B layout via _panel_en helper
- [ ] T05: V1 CONSTRAINTS list (22 entries, replaces 5)
- [ ] T06: Regen template.sla + brand_overrides cleanup + slots rewrite
- [ ] T07: README.md V1 deltas + QR D1 rationale + logo aspect note
- [ ] T08: Smoke additions + spec rewrite + NEW geometry tests
- [ ] T09: Brief §10 row + EXECUTION.md final + ISSUE status=done

## Deviations from Plan

None yet.

## Discovered Issues

None yet.

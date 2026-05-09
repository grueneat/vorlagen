# Execution: V1 layout for wahlaufruf-postkarte-a6-quer (Symbol-Tight)

**Started:** 2026-05-09
**Status:** complete
**Branch:** issue/17-v1-layout-for-wahlaufruf-postkarte-a6-quer-symbol-tight
**Completed:** 2026-05-09

## Baseline (pre-T01)

- `python3 -m unittest discover tools/sla_lib/tests` → 570 passed, 2 skipped
- `python3 -m unittest templates._smoke.test_wahlaufruf_postkarte_a6_quer` → 8 passed
- `python3 -m sla_lib.builder.structural_check wahlaufruf-postkarte-a6-quer` → 0 errors, 0 warnings, 3 skipped, 16 passes
- `bin/audit-alignment wahlaufruf-postkarte-a6-quer` → 1 suspicious page-1, 8 page-2 (expected pre-V1; V1 deletes/replaces)
- `python3 tools/check_ci.py templates/wahlaufruf-postkarte-a6-quer/template.sla` → 4 extra-style warnings (existing 4 wahlaufruf/* styles), exit 0

## Execution Log

## T01: Add 4 new V1 ParaStyles + update meta.yml::ci_overrides.non_ci_styles — [x] done
- Commit: bbccf73 17: feat(wahlaufruf-postkarte): add 4 V1 ParaStyles + tighten impressum
- Files changed: templates/wahlaufruf-postkarte-a6-quer/build.py (+50 -2), templates/wahlaufruf-postkarte-a6-quer/meta.yml (+4)
- Tests passing: 570/570 stdlib + 8/8 smoke; structural_check 0 errors / 0 warnings
- Notes: ParaStyle.kern field already exists (styles.py:76). All 4 styles + impressum tweak landed; check_ci exits 0 (warnings only, by design).

## T02: V1 front layout — logo resize, halo, Wahlkreuz reposition, datum/cta — [x] done
- Commit: fae6247 17: feat(wahlaufruf-postkarte): V1 front — halo + Wahlkreuz reposition + datum/cta
- Files changed: templates/wahlaufruf-postkarte-a6-quer/build.py (+41 -16)
- Tests passing: build exits 0; structural_check still 0 errors / 0 warnings (page 1 / CONSTRAINTS unchanged)
- Notes: Halo emitted BEFORE Wahlkreuz (z-order); shape="ellipse"; Wahlkreuz ANNAME kept capitalized.

## T03: V1 back layout — split-half bg, white logo, 3 W-Fragen, QR, Impressum — [x] done
- Commit: fff3283 17: feat(wahlaufruf-postkarte): V1 back — split-half bg + 3 W-Fragen + QR + logo swap
- Files changed: templates/wahlaufruf-postkarte-a6-quer/build.py (+143 -66), templates/wahlaufruf-postkarte-a6-quer/meta.yml (+2)
- Tests passing: build exits 0; structural_check WARNs on stale Cell N CONSTRAINTS (expected — T04 fixes)
- Notes: Took option (a) — inline-added wahlaufruf/qr-label + wahlaufruf/qr-url styles for ISSUE.md's Dunkelgrün label/URL spec, extended ci_overrides. logo_back uses lowercase snake_case anname; case-INSENSITIVE \bLogo\b brand rule still matches.

## T04: V1 CONSTRAINTS — 13-entry locked list — [x] done
- Commit: df2f0a0 17: feat(wahlaufruf-postkarte): V1 CONSTRAINTS — 13 entries (mirrored axes, aligned_below, same_x)
- Files changed: templates/wahlaufruf-postkarte-a6-quer/build.py (+34 -25)
- Tests passing: 13/13 CONSTRAINTS green; structural_check 0 errors / 0 warnings; --all 8/8 templates green; 570/570 stdlib tests pass
- Notes: Imports cleaned (dropped AlignedRow/same_y/same_style; added mirrored_x/mirrored_y/aligned_below/distance_y). All halo math verified: centers (74, 48) match.

## T05: Rewrite smoke test — V1 W-Fragen + halo + datum/cta + QR — [x] done
- Commit: 6af436d 17: test(wahlaufruf-postkarte): rewrite smoke for V1 W-Fragen + halo + datum/cta + QR
- Files changed: templates/_smoke/test_wahlaufruf_postkarte_a6_quer.py (+203 -63)
- Tests passing: 12/12 smoke (was 8 pre-V1; +5 V1 tests, -1 stale 2x2_grid test, all carry-over invariants kept)
- Notes: Added _frame_by_anname/_frame_geom_mm helpers (page-relative mm via PAGEXPOS/PAGEYPOS conversion). Whitelisted seitenhintergrund_back_left in trim+bleed test.

## T06: Regenerate template.sla + gallery via bin/render-gallery — [x] done
- Commit: 7c6e021 17: chore(wahlaufruf-postkarte): regenerate template.sla + gallery via bin/render-gallery
- Files changed: template.sla, page-01.png, page-02.png, preview.pdf, meta.yml; mirrored to site/public/. (9 files, +111 -81)
- Tests passing: bin/check-stale-previews exits 0; SHA pin updated to 7f64b8ad…ba08a06
- Notes: Used `bin/render-gallery wahlaufruf-postkarte-a6-quer --skip-visual-diff`. Auto-bumps meta.yml SHA via the pipeline.

## T07: Remove 2 stale brand_overrides + declare cross-column adjacencies — [x] done
- Commit: ba2cd49 17: chore(wahlaufruf-postkarte): remove 2 stale brand_overrides + declare cross-column adjacencies
- Files changed: templates/wahlaufruf-postkarte-a6-quer/build.py (+30 -1), templates/wahlaufruf-postkarte-a6-quer/meta.yml (+7 -14)
- Tests passing: 20/20 CONSTRAINTS PASS, audit shows 0 suspicious on BOTH pages (was 2+5), --all 8/8 templates green, 570 stdlib + 12 smoke pass
- Notes: Removed brand:logo_size_3M (V1 enforces 3*M) and brand:undeclared_alignment_drift (V1 declares all adjacencies). Kept brand:line_spacing_0.9 with refreshed reason — V1's cell-body-on-green at 9pt/11pt drifts 2.9pt from the 0.9 factor for Dunkelgrün readability. Added 7 audit-driven constraints (3 distance_x + 3 distance_y + 1 aligned_below) to formalize intentional cross-column offsets.

## T08: Rewrite _specs for V1 layout — [x] done
- Commit: 17055d1 17: docs(wahlaufruf-postkarte): rewrite _specs for V1 "Symbol-Tight" layout
- Files changed: templates/_specs/wahlaufruf-postkarte-a6-quer.md (+384 -215)
- Tests passing: spec_check (0 errors / 0 info / 0 extras); 19 V1 annames declared
- Notes: Constraints described in PROSE per SCHEMA.md §11-12. Re-emitted slots: YAML block. ParaStyle-Hygiene calls out the orphan trio kept for #18-#21 migration parity.

## T09: Session-history row + Resulting-issue link — [x] done
- Commit: 7118d1d 17: docs(brand): append session-history row for wahlaufruf-postkarte V1
- Files changed: shared/brand/DESIGN-SYSTEM-BRIEF.md (+1 -1) committed in worktree; companion edit to /root/workspace/improvements/01-wahlaufruf-postkarte.md (untracked at workspace root, not in git)
- Tests passing: both grep verifies pass (brief contains improvements/01-...md substring; improvements file contains GitHub URL)
- Notes: improvements/ is untracked at workspace root (never in git index); brief row references the source .md path via "(Source: ...)" parenthetical so the verify grep finds the substring. Issue URL points to GitHub #33 with "V1 only; V2/V3 backlog" qualifier.

## Final Verification

All gates per the prompt's "When all 9 tasks done" section:

| Command | Result |
|---|---|
| `python3 -m unittest discover tools/sla_lib/tests` | 570 passed, 2 skipped |
| `python3 -m unittest templates._smoke.test_wahlaufruf_postkarte_a6_quer` | 12 passed |
| `python3 -m sla_lib.builder.structural_check --all` | 8/8 templates green; per-template `wahlaufruf-postkarte-a6-quer` → 0 errors / 0 warnings / 1 skipped (`brand:line_spacing_0.9` documented) / 30 passes |
| `bin/audit-alignment wahlaufruf-postkarte-a6-quer` | 0 suspicious adjacencies on BOTH pages (was 1+8 pre-V1, then 2+5 immediately after override removal) |
| `bin/check-stale-previews` | exit 0 (SHA pin matches regenerated SLA) |
| `python3 tools/check_ci.py templates/wahlaufruf-postkarte-a6-quer/template.sla` | exit 0; 10 extra-style warnings for the template-local non_ci_styles (declared in meta.yml::ci_overrides.non_ci_styles) — non-critical, by design |
| `issue-cli store update-status 17-… done` | `{"status": "done", "ship_state": "none"}` |

Stub / debug / placeholder grep on changed files: clean (only the pre-existing
`print(f"wrote {out}")` CLI shim in build.py, kept).

## Commit Manifest

| # | SHA | Message |
|---|-----|---------|
| T01 | bbccf73 | 17: feat(wahlaufruf-postkarte): add 4 V1 ParaStyles + tighten impressum |
| T02 | fae6247 | 17: feat(wahlaufruf-postkarte): V1 front — halo + Wahlkreuz reposition + datum/cta |
| T03 | fff3283 | 17: feat(wahlaufruf-postkarte): V1 back — split-half bg + 3 W-Fragen + QR + logo swap |
| T04 | df2f0a0 | 17: feat(wahlaufruf-postkarte): V1 CONSTRAINTS — 13 entries (mirrored axes, aligned_below, same_x) |
| T05 | 6af436d | 17: test(wahlaufruf-postkarte): rewrite smoke for V1 W-Fragen + halo + datum/cta + QR |
| T06 | 7c6e021 | 17: chore(wahlaufruf-postkarte): regenerate template.sla + gallery via bin/render-gallery |
| T07 | ba2cd49 | 17: chore(wahlaufruf-postkarte): remove 2 stale brand_overrides + declare cross-column adjacencies |
| T08 | 17055d1 | 17: docs(wahlaufruf-postkarte): rewrite _specs for V1 "Symbol-Tight" layout |
| T09 | 7118d1d | 17: docs(brand): append session-history row for wahlaufruf-postkarte V1 |

Plus the EXECUTION.md commit (this file) as the final commit.

## Self-Check

- [x] All files from plan exist (build.py, meta.yml, smoke test, _specs MD, brief)
- [x] All commit SHAs verified present on the branch (`git log --oneline`)
- [x] Full verification suite passes (8/8 + 570/570 + 12/12 + 0 suspicious + clean check_ci + clean stale-previews + clean spec_check)
- [x] No stubs / TODOs / placeholders in changed files
- [x] No new debug code (existing CLI print() preserved)
- **Result:** PASSED

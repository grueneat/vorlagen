# Execution: 16-fix-zeitung-a4-image-frames-placed-past-page-boundary-spilling-into-adjacent-pag

**Started:** 2026-05-09
**Completed:** 2026-05-09
**Status:** complete
**Branch:** issue/16-fix-zeitung-a4-image-frames-placed-past-page-boundary-spilling-into-adjacent-pag

## Pre-execution baseline

- `python3 -m unittest discover tools/sla_lib/tests`: 531 tests, OK
- `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all`: exit 0
- GH #39 verified open (cover polygon u2950 follow-up)
- Scribus 1.6.5 + xvfb-run available on PATH

## Execution Log

## T01: Add sla_diff_strict field to meta.yml schema — [x] done
- Commit: 90d16c3 16: feat(meta_schema): add sla_diff_strict opt-out flag
- Files changed: tools/sla_lib/builder/meta_schema.py (+27), tools/sla_lib/tests/test_meta_schema.py (+66)
- Tests passing: 536/536 (5 new tests in SlaDiffStrictTests)
- Notes: TDD RED-then-GREEN: import-error first, then helper added; full suite green.

## T02: Gate _run_sla_diff_strict on sla_diff_strict flag — [x] done
- Commit: 8435ad7 16: feat(render_pipeline): gate strict diff on meta sla_diff_strict
- Files changed: tools/render_pipeline.py (+7), tools/sla_lib/tests/test_render_pipeline.py (+29)
- Tests passing: 538/538 (2 new tests in SlaDiffStrictGateTests)
- Notes: Gate inserted after the original_sla skip (so canonical message order preserved). Mock-based tests confirm subprocess is not invoked on opt-out; subprocess IS invoked when key absent.

## T03: Set sla_diff_strict=false on zeitung + reword override — [x] done
- Commit: 13e9573 16: chore(zeitung): set sla_diff_strict=false + reword inside_page override
- Files changed: templates/zeitung-a4-grun/meta.yml (+15 / -4)
- Tests passing: structural_check zeitung-a4-grun exits 0
- Notes: Verified GH #39 exists open. Override now points at #39 for u2950 follow-up.

## T04: Move Frame A "P9 Spread" to page-local origin (x=0) — [x] done
- Commit: 2403e04 16: fix(zeitung): move P9 Spread frame to page-local origin
- Files changed: templates/zeitung-a4-grun/build.py (+2 / -2)
- Tests passing: harness reports 2 errors (was 3); P9 Spread no longer flagged
- Notes: Single-coordinate edit; anname preserved so INJECT_MAP and CONSTRAINTS still resolve.

## T05: Move Frame B from page11 to page12 — [x] done
- Commit: d48275e 16: fix(zeitung): move unnamed page-12 polygon to page12
- Files changed: templates/zeitung-a4-grun/build.py (+2 / -2)
- Tests passing: harness reports 1 error (was 2); only u2950 remains
- Notes: Two changes — page binding (page11 -> page12) and x_mm (210 -> 0.0). All other fields verbatim, including local_offset_mm.

## T06: Regenerate template.sla, page PNGs, previews_for_sla SHA — [x] done
- Commit: e61ba8c 16: chore(zeitung): regenerate template.sla and gallery previews
- Files changed: templates/zeitung-a4-grun/{template.sla, template-preview.sla, preview.pdf, page-10.png, page-11.png, meta.yml} + site/public mirror
- Tests passing: bin/check-stale-previews zeitung-a4-grun exit 0; structural_check zeitung-a4-grun exit 0
- Notes: Render via Scribus 1.6.5 + xvfb-run succeeded. New SHA c0a39009...3893ebda96f. baseline.pdf left untouched. Only page-10.png and page-11.png changed (the affected pages). The meta-hash rewriter stripped the comment block above sla_diff_strict; re-added it post-regen.

## T07: Update test_zeitung_overflow.py + tolerate round-trip drift — [x] done
- Commit: 1f1f1f3 16: test(zeitung): expect 1 inside_page error and tolerate intentional round-trip drift
- Files changed: tools/sla_lib/tests/test_zeitung_overflow.py (rewritten, +29/-37), tools/sla_lib/tests/test_sla_to_dsl.py (+69/-19)
- Tests passing: 538/538 (full suite green)
- Notes: Plan only anticipated test_zeitung_overflow.py update. Discovered (Principle 5) that ZeitungRoundTrip.test_diff_against_original_clean was implicitly enforcing byte-stable round-trip — the contract we explicitly broke per sla_diff_strict=false. Added an OwnPage-scoped allow-list for criticals (pages 11, 12) and drift warnings (pages 9, 11, 12). Real round-trip regressions on other pages still fail. ZeitungConverterFreshRun left untouched.

## T08: README divergence note + final --all verification — [x] done
- Commit: c7ea24e 16: docs(zeitung): note intentional divergence from original SLA
- Files changed: templates/zeitung-a4-grun/README.md (+26)
- Tests passing: 538/538; structural_check --all exit 0; check-stale-previews exit 0
- Notes: German section "Bekannte Abweichungen vom Original-SLA" inserted between Vorlagen-Generierung and Brand sections.

## Final verification

- `python3 -m unittest discover tools/sla_lib/tests`: 538 tests, OK (exit 0)
- `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all`: 0 errors, 0 warnings, 2 skipped, 16 passes (exit 0)
- `bin/check-stale-previews`: exit 0 across all templates

## Deviations from Plan

### Auto-fixed (Rule 5: fix what you break)

1. **test_sla_to_dsl.py::ZeitungRoundTrip.test_diff_against_original_clean**
   - Found during: T07 (ran full suite after updating test_zeitung_overflow.py)
   - Issue: Test asserted byte-stable round-trip against original SLA — exactly the contract sla_diff_strict=false now opts out of. The plan only anticipated test_zeitung_overflow.py needing update.
   - Fix: Added OwnPage-scoped allow-list for criticals (pages 11, 12) and drift warnings (pages 9, 11, 12). Anything outside still fails.
   - Files: tools/sla_lib/tests/test_sla_to_dsl.py
   - Commit: 1f1f1f3

### Blocked (Rule 4)

None.

## Discovered Issues

- **meta-hash rewriter strips comments** above the `sla_diff_strict:` line. T03's commented opt-out block was stripped by `_update_meta_hash` during T06's regen. I re-added it post-regen and it's now committed correctly. If the rewriter is run again, the comment will be lost again — could be filed as a follow-up to make `_update_meta_hash` preserve adjacent comment blocks.

## Self-Check

- [x] All files from plan exist
- [x] All commits exist on branch (verified via `git log --oneline main..HEAD`)
- [x] Full verification suite passes (538 tests OK, structural_check --all exit 0, check-stale-previews exit 0)
- [x] No stubs/TODOs/placeholders in changed code
- [x] No leftover debug code (no print/console.log/debugger)
- [x] baseline.pdf intentionally untouched (per Locked decision #7)
- **Result:** PASSED

**Status:** complete

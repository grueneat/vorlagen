# Execution — Rewrite Postkarte A6 onto Brand + blocks

**Issue:** rewrite-postkarte-onto-brand-blocks (id 6)
**Status:** complete
**Executed:** 2026-05-07
**Branch:** issue/rewrite-postkarte-onto-brand-blocks

## Tasks

- [x] Task 1: Add --allow-brand-extras flag to sla_diff and wire through bin/validate — commit `eff5ba7`
- [x] Task 2: Forward line_color / line_width_pt through PageBackground.for_page() — commit `2e5541c`
- [x] Task 3: Hoist missing PDF attribute key into shared/ci-defaults.yml — commit `f1bc6d7`
  - Hoisted key: `CompressMethod = '0'` (DSL builder always emits this; converter was capturing it as a per-template residual)
  - Also updated test_brand.py count from 34 → 35 (expected breakage)
- [x] Task 4: Regenerate templates/postkarte-a6-kampagne/build.py via converter — commit `7974d6f`
- [x] Task 5: Substitute the 2 PageBackground polygons with block calls — commit `7166b50`
- [x] Task 6: Rebuild gallery, run full validation, regenerate previews_for_sla SHA — commit `1ebe8ef`
  - Deviation: [Rule 3 - Blocker] render_pipeline.py also needed --allow-brand-extras (same issue as bin/validate)
  - Deviation: [Rule 1 - Bug fix] PostkarteRoundTrip.test_diff_against_original_clean needed brand-extras allowlist update (expected breakage from Brand migration)
- [x] Task 7: Acceptance check + write EXECUTION.md

## Acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | visual_diff clean against baseline.pdf | PASS | `tools/visual_diff.py ... --dpi 96 ...` → exit 0; pixel-clean |
| 2 | pytest tools/sla_lib/tests -x | PASS | 249 passed, 3 warnings |
| 3 | bin/validate --ci green for ALL three templates | PASS | plakat/postkarte/zeitung all PASS (sla_diff + visual_diff) |
| 4 | tools/check_ci.py templates/postkarte-a6-kampagne | PASS | exit 0 (template-local style warnings are expected/non-blocking) |
| 5 | extra_doc_attrs <= 23 keys | PASS | 23 keys |
| 6 | extra_pdf_attrs <= 11 keys | PASS | 11 keys |

## Metrics

- LOC: 437 → 369 (informational; not an AC)
  - Starting: 437 (committed pre-migration)
  - After converter regen + DocumentLayer add: 386
  - After PageBackground x2 substitution: 369
  - RESEARCH.md projected ~366; actual 369 (3 LOC over estimate)
- extra_doc_attrs: 113 → 23 keys
- extra_pdf_attrs: 34 → 11 keys
- Block substitutions: 2 (PageBackground page0 + page1)
- Brand uptake: brand=Brand.gruene_noe(), palette_replaces_ci removed
- Note: LOC target of <=280 (original issue triage estimate) is NOT achievable;
  see RESEARCH.md §"Why the LOC target is hard to hit" for explanation.
  Realistic LOC with current block surface: ~365-370. No AC gate on LOC.

## Deviations from Plan

### Auto-fixed (Rules 1 and 3)

1. **[Rule 3 - Blocker] render_pipeline.py also needed --allow-brand-extras**
   - Found during: Task 6 (bin/render-gallery call)
   - Issue: `bin/render-gallery` calls `tools/render_pipeline.py` which has its own
     `sla_diff --strict` invocation without `--allow-brand-extras`, causing
     render-gallery to fail on postkarte's brand-injected ci/* styles
   - Fix: Added `--allow-brand-extras` to `_run_sla_diff_strict()` in render_pipeline.py
   - Files: tools/render_pipeline.py
   - Commit: 1ebe8ef

2. **[Rule 1 - Bug fix] PostkarteRoundTrip test needed brand-extras allowlist update**
   - Found during: Task 6 (full test suite run)
   - Issue: `PostkarteRoundTrip.test_diff_against_original_clean` asserted 0 warnings
     against the original SLA. After migration the committed build.py uses
     Brand.gruene_noe() which injects ci/* styles → 8 extra-style warnings. The same
     warning type was already tolerated in `PostkarteConverterFreshRun` with a code-level
     allowlist filter — applying the same pattern to the RoundTrip test is the correct fix.
   - Fix: Updated test to filter extra-style/extra-layer warnings using the same allowlist
     pattern as PostkarteConverterFreshRun (lines 99-106 in test_sla_to_dsl.py)
   - Files: tools/sla_lib/tests/test_sla_to_dsl.py
   - Commit: 1ebe8ef

3. **[Rule 1 - Expected breakage] test_brand.py count updated 34 → 35**
   - Found during: Task 3 (after hoisting CompressMethod to ci-defaults)
   - Issue: test_brand_default_pdf_attrs_count hardcoded 34; after hoisting CompressMethod
     it's 35
   - Fix: Updated assertion to 35 with explanatory comment referencing issue #6
   - Files: tools/sla_lib/tests/test_brand.py
   - Commit: f1bc6d7

### Blocked (Rule 4)

None.

## Discovered Issues

- **Zeitung preview.pdf non-determinism**: bin/render-gallery always rebuilds all templates,
  causing the zeitung preview.pdf to regenerate with a slightly different PDF trailer
  (timestamp scrubbing doesn't fully canonicalize all PDF metadata). Committed as part
  of Task 6 — this is expected and matches the existing scrub_pdf behavior.

## P2 follow-ups (file as future issues, do NOT implement here)

1. **Widen `Impressum` block to support prefix-bold-Run idiom.** Current API emits a
   single Run; all three production templates (Plakat, Postkarte, Zeitung) carry an
   "Impressum:" Bold prefix Run that the block cannot represent. Proposal: add
   `prefix_text=`, `prefix_font=` kwargs OR a `runs=` override to `Impressum.emit()`.

2. **Widen `ContactBlock` block to support `separator='breakline'`, `default_style_attrs=`,
   `vertical_text_align=`, and per-Run `fshade=`.** Postkarte's contact frame uses all
   four; the current block API only fits the defaulted shape. File a new issue for
   ContactBlock widening before Plakat/Zeitung migration (issue #7/#8).

3. **Audit `extra_pdf_attrs` for further hoist candidates** once Plakat and Zeitung migrate
   (issues #7, #8). The 11-key residual may shrink further once we see what's actually
   constant across all three regenerations.

4. **Optional: widen `_SizedPageBackground` to accept `anname=` override.** Current default
   'Seitenhintergrund' — fine for Postkarte but might collide with multi-frame layered
   backgrounds in Zeitung. Defer until issue #8 surfaces it.

5. **DSL builder emits CompressMethod='0' unconditionally but ci-defaults.yml previously
   listed CMethod (not CompressMethod).** They are different keys. Confirmed CompressMethod
   is a builder-hardcoded addition; audit whether the original SLA's CMethod vs builder's
   CompressMethod coexistence is intentional or whether one should supersede the other.
   (Currently both appear in the built SLA — no rendering impact, but worth cleaning up.)

## Notes

- `--allow-brand-extras` is now the canonical mechanism for tolerating Brand-injected
  `extra-style` / `extra-layer` warnings in both `bin/validate` and `bin/render-gallery`.
  Future template migrations (Plakat #7, Zeitung #8) will rely on this flag without
  further changes.
- The Postkarte rewrite is mostly mechanical: 95% of the work is the converter-regen;
  hand edits were surgical (2 block substitutions + 1 layer kwarg + 1 import addition).
- LOC ≤280 target from original issue triage was not achievable; see RESEARCH.md for
  full analysis. Actual achieved: 369 LOC (down 68 from 437). The converter does the
  heavy lifting; block substitution adds ~20 LOC of savings. The 9 template-local
  ParaStyles and 5 contact-icon ImageFrames dominate the remaining count.

## Self-Check

- [x] All files from plan exist
- [x] All 6 commits exist on branch (eff5ba7, 2e5541c, f1bc6d7, 7974d6f, 7166b50, 1ebe8ef)
- [x] Full verification suite passes (249 tests, bin/validate --ci green for all 3 templates)
- [x] No stubs/TODOs/placeholders in changed files
- [x] No leftover debug code
- **Result:** PASSED

**Completed:** 2026-05-07
**Duration:** ~2 hours
**Commits:** 6 (Tasks 1-6; Task 7 commits EXECUTION.md)

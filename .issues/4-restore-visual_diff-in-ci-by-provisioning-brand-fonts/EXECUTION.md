# Execution: Local render pipeline that commits gallery artifacts; CI becomes pure shipper

**Started:** 2026-05-06T11:20:21Z
**Status:** in_progress
**Branch:** issue/4-restore-visual_diff-in-ci-by-provisioning-brand-fonts

## Execution Log

- [ ] Phase 0: Pipeline skeleton + PDF metadata scrub helper
  - [ ] Task 0.1: Create tools/render_pipeline.py with helper functions
  - [ ] Task 0.2: Create bin/render-gallery shim
  - [ ] Task 0.3: Add tools/sla_lib/tests/test_render_pipeline.py
- [ ] Phase 1: Per-template orchestrator + 50-dpi PNG + plakat per-size
  - [ ] Task 1.1: Implement non-family branch of _orchestrate_template
  - [ ] Task 1.2: Implement family branch (plakat per-size)
  - [ ] Task 1.3: Wire --dry-run, --skip-visual-diff, summary into main()
- [ ] Phase 2: Hash field handling in meta.yml + postcard preview_dpi
  - [ ] Task 2.1: Verify meta.yml hash-field round-trip on all 3 real templates
  - [ ] Task 2.2: Add postkarte-a6-kampagne meta.yml::preview_dpi: 100
- [ ] Phase 3: bin/check-stale-previews + bin/validate preflight wiring
  - [ ] Task 3.1: Create tools/check_stale_previews.py + bin/check-stale-previews shim
  - [ ] Task 3.2: Wire bin/check-stale-previews into bin/validate as a preflight
  - [ ] Task 3.3: Add tools/sla_lib/tests/test_check_stale_previews.py
- [ ] Phase 4: tools/gallery_build.py copy-only refactor
  - [ ] Task 4.1: Delete render_pdf and pdf_to_pngs functions
  - [ ] Task 4.2: Refactor process_template to copy-only with _fail_missing helper
  - [ ] Task 4.3: Add tools/sla_lib/tests/test_gallery_build_copy_only.py
- [ ] Phase 5: .github/workflows/pages.yml simplification
  - [ ] Task 5.1: Add bin/check-stale-previews invocation; drop TODO comment block
- [ ] Phase 6: Regenerate all gallery artifacts via new pipeline + regression check
  - [ ] Task 6.1: Clean tree + bin/render-gallery from scratch
  - [ ] Task 6.2: Idempotency regression: second run = no diff
  - [ ] Task 6.3: Reference-PDF regression check (PR #7's 0-px standard)
  - [ ] Task 6.4: Final bin/validate exits 0
- [ ] Phase 7: Documentation
  - [ ] Task 7.1: Add 'Local-only rendering' + 'Maintainer workflow' to docs/render-fidelity.md
  - [ ] Task 7.2: Update shared/fonts/README.md to clarify local-only path
- [ ] Phase 8: End-to-end demo (synthetic edit → render → validate → revert)
  - [ ] Task 8.1: Synthetic template edit + render + validate + revert
  - [ ] Task 8.2: Document demo + push procedure in EXECUTION.md
- [ ] Phase 9: Final verification
  - [ ] Task 9.1: Acceptance criteria checklist
  - [ ] Task 9.2: Final summary + tree state confirmation

## Phase Gates

| Phase | Gate |
|-------|------|
| 0 | Pending |
| 1 | Pending |
| 2 | Pending |
| 3 | Pending |
| 4 | Pending |
| 5 | Pending |
| 6 | Pending |
| 7 | Pending |
| 8 | Pending |
| 9 | Pending |

## Verification Results

**Baseline:** 136 tests, OK

## Deviations from Plan

None yet.

## Discovered Issues

None yet.

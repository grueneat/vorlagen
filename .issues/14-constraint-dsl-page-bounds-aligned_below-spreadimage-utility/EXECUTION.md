# Execution: Constraint DSL — page-bounds, aligned_below, SpreadImage utility (#14)

**Started:** 2026-05-09
**Completed:** 2026-05-09
**Status:** complete
**Branch:** issue/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility
**Baseline:** `python3 -m unittest discover tools/sla_lib/tests` → 490 tests OK
**Final:** 531 tests OK; `structural_check --all` exit 0 under `set -euo pipefail`

## Execution Log

## T01: rotation-aware bbox helpers — [x] done
- Commit: 03faee6 14: feat(constraints): add rotation-aware bbox helpers (Issue #14)
- Files changed: tools/sla_lib/builder/brand_constraints.py (+57 lines, +math/PT_TO_MM/resolve_anchor imports), tools/sla_lib/tests/test_constraints_inside_page.py (NEW, 134 lines)
- Tests passing: 11/11 in test_constraints_inside_page.py; full suite 501 OK (+11 from baseline 490)
- Notes: Anchor-obliterates-(x,y) handled via resolve_anchor mirroring _Frame._xy_pt. CCW-positive top-left-pivot rotation matches Scribus ROT convention (verification gated to a human render-check pre-merge per RESEARCH).
## T02: brand:inside_page rule + threshold confirmation — [x] done
- Commit: 076e3bf 14: feat(brand): add brand:inside_page rule with rotation-aware bbox
- Files changed: tools/sla_lib/builder/brand_constraints.py (+~85 lines: docstring 8→9, _InsidePageRule class, registry entry), tools/sla_lib/tests/test_constraints_inside_page.py (+13 new tests)
- Tests passing: 24/24 in test_constraints_inside_page.py; full suite 514 tests with 2 expected failures in test_brand_constraints.RegistryTests (fixed in T03 atomically per plan).
- Notes: 1.0 mm error / 0.5 mm warning split chosen vs. ISSUE.md's 0.5 mm cutoff — documented in commit + class docstring. Master-page items skipped per plan. Per-Violation severity emit (vs. BrandRule.severity field) is novel but supported by the orchestrator.
## T03: 9-rule registry test update — [x] done
- Commit: 29c8f48 14: test(brand): update registry tests for 9-rule count
- Files changed: tools/sla_lib/tests/test_brand_constraints.py (+4/-2: rename test, add brand:inside_page id, import _InsidePageRule)
- Tests passing: full suite 514 OK
- Notes: Method renamed (not just count-bumped) so the change is discoverable in git blame/log.
## T04: aligned_below constraint factory — [x] done
- Commit: 64828ac 14: feat(constraints): add aligned_below factory
- Files changed: tools/sla_lib/builder/constraints.py (+~55 lines: _AlignedBelowConstraint + aligned_below factory), tools/sla_lib/builder/__init__.py (+2 lines: import + __all__), tools/sla_lib/tests/test_constraints.py (+~75 lines: 8 tests)
- Tests passing: 8/8 AlignedBelowTests; full suite 522 OK (+8 new)
- Notes: Test helper `_pair` initially had duplicate-kwarg bug from inline literals + below_kwargs; refactored to merge dicts before construction. Targets order `(below, above)` preserved per plan to match editor's reading.
## T05: SpreadImage block — [x] done
- Commit: 874fa2c 14: feat(blocks): add SpreadImage builder block
- Files changed: tools/sla_lib/builder/blocks.py (+~65 lines: SpreadImage dataclass with emit() + place()), tools/sla_lib/tests/test_spread_image.py (NEW, 81 lines)
- Tests passing: 7/7 SpreadImageEmitTests; full suite 529 OK (+7 new)
- Notes: Right half local_offset_mm=(-page_w_mm, 0) verified by test. scale_type=0 hard-pinned by default. Re-export not needed at __init__ level — blocks module already exported, callers use blocks.SpreadImage (matches WahlkreuzSymbol/FoldedPanel pattern).
## T06: zeitung brand_override skip for inside_page — [x] done
- Commit: 6d57e25 14: chore(zeitung): brand_overrides skip for inside_page (see #16)
- Files changed: templates/zeitung-a4-grun/meta.yml (+6 lines: appended brand:inside_page override entry with reason)
- Verify: `cd tools && python3 -m sla_lib.builder.structural_check zeitung-a4-grun` → exit 0; output shows `SKIP brand:inside_page (overridden in meta.yml: ...)`. Existing brand:line_spacing_0.9 entry left byte-identical.
- Notes: Used Edit (not Write) per plan — `original_sla` / `previews_for_sla` / `ci_overrides` blocks unchanged.
## T07: --all green-bar verification + tolerance investigation gate — [x] done (verification-only, no commit)
- Verification: `cd tools && set -euo pipefail; python3 -m sla_lib.builder.structural_check --all` → exit 0
- Decision-tree branch applied: **None for non-zeitung templates** — all 7 show `PASS brand:inside_page`. Zeitung shows `SKIP brand:inside_page` per the override (the rule-level skip silences the entire template at structural_check time). For zeitung itself, T10 (which constructs the rule directly and bypasses the override) DID surface branch 1 — see "Discovered Issues" below. No NEW non-zeitung template surfaced an inside_page issue, so no extra override / tolerance bump was required for the `--all` sweep.
- Per-template summary (8 templates total):
  - infostand-tent-card-a5-quer: 0 errors, 0 warnings, 2 skipped, 12 passes (inside_page PASS)
  - kandidat-falzflyer-din-lang: 0 errors, 0 warnings, 2 skipped, 16 passes (inside_page PASS)
  - plakat-a1-hochformat: 0 errors, 0 warnings, 1 skipped, 9 passes (inside_page PASS — confirms rotation-270 Impressum frame fits)
  - postkarte-a6-kampagne: 0 errors, 0 warnings, 1 skipped, 9 passes (inside_page PASS)
  - themen-plakat-a3-quer: 0 errors, 0 warnings, 3 skipped, 12 passes (inside_page PASS)
  - wahlaufruf-postkarte-a6-quer: 0 errors, 0 warnings, 2 skipped, 15 passes (inside_page PASS)
  - wahltag-tueranhaenger: 0 errors, 0 warnings, 6 skipped, 7 passes (inside_page PASS — confirms 2 mm bleed handled correctly via `page.bleed_mm`)
  - zeitung-a4-grun: 0 errors, 0 warnings, 2 skipped, 16 passes (inside_page SKIP per #16 override)
- Aggregate: **0 errors, 0 warnings across all 8 templates.** No commit needed for T07 — gate is verification-only and no code/data changed.
## T08: SCHEMA.md catalogue entries — [x] done
- Commit: e99de15 14: docs(schema): add inside_page, aligned_below, SpreadImage to SCHEMA §12
- Files changed: templates/_specs/SCHEMA.md (+23/-5: factory list +aligned_below; new "Neue Factories (Issue #14)" subsection with aligned_below + SpreadImage; "8 Regeln"→"9 Regeln" + brand:inside_page entry)
- Verify: `grep -nE "brand:inside_page|aligned_below|SpreadImage|9 Regeln" templates/_specs/SCHEMA.md` → 5 hits in §12. `grep -nE "8 Regeln|eight rules|acht Regeln"` → empty.
## T09: SPEC-WRITING-GUIDE.md catalogue + SpreadImage migration recipe — [x] done
- Commit: 2669aa5 14: docs(brand): add SpreadImage migration recipe to SPEC-WRITING-GUIDE
- Files changed: shared/brand/SPEC-WRITING-GUIDE.md (+50 lines: §5 aligned_below entry; §7 brand:inside_page entry; new "SpreadImage-Migration" subsection before §8 with ❌/✅ recipe)
- Verify: 5 grep hits for aligned_below/SpreadImage/brand:inside_page; no residual "8 Regeln/eight rules/acht Regeln".
- Notes: Inserted as subsections within existing sections (§5 / §7) rather than into new factory/brand-rule "catalogue" tables — this guide doesn't carry tabular catalogues; SCHEMA.md §12 plays that role (T08).
## T10: regression test for the known zeitung overflows — [x] done
- Commit: 2054bbd 14: test(zeitung): regression for the known overflow frames
- Files changed: tools/sla_lib/tests/test_zeitung_overflow.py (NEW, 113 lines)
- Tests passing: 2/2 ZeitungInsidePageRegressionTests; full suite 531 OK (+2 new)
- Notes: ISSUE.md predicted "exactly two" inside_page errors today; the rotation-aware bbox helper surfaced a THIRD: rotated cover-page Dunkelgrün polygon `u2950` (build.py:246-256). Conservative path applied per prompt — captured as a real bug in test docstring + module docstring + commit message; silenced today by zeitung's rule-level `brand:inside_page` override; tracked as a follow-up under "Discovered Issues" below for the human to file separately.

## Discovered Issues

- **Zeitung cover-page rotated polygon `u2950` overflows bottom edge by ~4.17 mm.** Frame at `templates/zeitung-a4-grun/build.py:246-256` is a rotated (90° CCW) Dunkelgrün polygon (148.60×220.49 mm pivoted at (216.41, 155.57)) whose rotation-aware bbox spans (-4.08, 155.57)→(216.41, 304.17), exceeding the A4 trim+bleed bottom (300 mm) by ~4.17 mm. Surfaced by the new `brand:inside_page` rule. Already silenced by zeitung's existing rule-level override (`structural_check --all` exits 0). Should be filed as a follow-up issue against zeitung — likely needs the polygon shrunk OR repositioned in the upstream Scribus original. NOT in scope for issue #14 or #16 (#16 specifically targets the two right-edge spread frames).

## Verification Results

- `python3 -m unittest discover tools/sla_lib/tests` → **531 tests OK** (baseline 490; +41 new across the four new test files).
- `cd tools && set -euo pipefail; python3 -m sla_lib.builder.structural_check --all` → **exit 0** across all 8 templates. Per-template breakdown in T07.
- `grep -nE "8 Regeln|eight rules|acht Regeln" templates/_specs/SCHEMA.md shared/brand/SPEC-WRITING-GUIDE.md` → empty.
- `grep -rn "PageBackground" templates/` → 3 hits, all using `.for_page(...)` (pitfall P-20 sanity check passed).

## Self-Check

- [x] All files from plan exist (`brand_constraints.py` rule + helpers; `constraints.py` aligned_below; `blocks.py` SpreadImage; meta.yml override; SCHEMA.md + SPEC-WRITING-GUIDE.md docs; 4 test files).
- [x] All commits exist on branch (verified via `git log --oneline issue/... ^main`).
- [x] Full verification suite passes (`unittest discover` 531 OK; `structural_check --all` exit 0).
- [x] No stubs/TODOs/placeholders introduced (greps clean for the new code paths).
- [x] No leftover debug code (no `print`/`breakpoint` in the new modules).
- **Result:** PASSED.

## Summary

- Tasks completed: 10/10 (T01-T10)
- Tests added: 41 across 4 files (test_constraints_inside_page.py 24 tests, test_constraints.py +8 AlignedBelowTests, test_spread_image.py 7 tests, test_zeitung_overflow.py 2 tests).
- structural_check --all: exit 0; 0 errors, 0 warnings across all 8 templates; brand:inside_page PASS for 7 templates, SKIP for zeitung (per #16 override).
- Branch: issue/14-constraint-dsl-page-bounds-aligned_below-spreadimage-utility
- Issue status: `done` (transitioned via `issue-cli store update-status`).
- Ready for: /issue:verify, then /issue:ship.

**Pre-merge human verification gate (per RESEARCH §"Render-verify"):** open the emitted `templates/plakat-a1-hochformat` SLA in Scribus once and visually confirm the rotated Impressum frame lands where `_rotated_bbox` predicts (CCW positive, top-left pivot). The structural check passing for plakat is strong evidence the convention is correct, but a one-shot visual confirmation closes the medium-confidence gap noted in research.

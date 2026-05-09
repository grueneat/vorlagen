# Execution: V1 layout for `themen-plakat-a3-quer` — Evidence Cards (#19)

**Started:** 2026-05-09T18:08:38Z
**Status:** complete
**Branch:** issue/19-v1-layout-for-themen-plakat-a3-quer-evidence-cards

## Summary

V1 "Evidence Cards" layout landed in 11 atomic commits per the locked-decision PR ordering.
The post-#24 INJECT_MAP idiom (build_template + build_preview split, live frame.w_mm /
frame.h_mm targets) replaces the iter-3 literal-targets-vs-frame-dims drift that produced
the "halb-leerer" hero photo. Three Hellgrün backing cards lift the body off white and give
the Belege real visual weight. CONSTRAINTS list rewritten to 19 entries (corrected per
RESEARCH.md errata: Card dropped from per-row same_x quad; aligned_below(Hero, Sub-Headline)
replaced with inside(Hero, Hero-Foto-Card)). Brand_overrides cleaned 6 → 2 entries (3 lifted
by V1 design intent + 1 lifted by exact 3M logo width).

## Tasks completed

- [x] T01 — feat(themen-plakat): add 3 V1 ParaStyles + headline linesp mutation + meta.yml ci_overrides extension — commit c3e90be
- [x] T02 — refactor(themen-plakat): split build_doc into build_template + build_preview with build_doc alias — commit 56f2051
- [x] T03 — feat(themen-plakat): V1 layout deltas — frames added, deleted, repositioned — commit c6425f3
  - Interim state: old CONSTRAINTS still references deleted Beleg N — Headline annames; T05 rewrites the list.
- [x] T04 — feat(themen-plakat): INJECT_MAP for Themen-Hero (post-#24 pattern, live frame dims) — commit aaa3668
- [x] T05 — feat(themen-plakat): replace CONSTRAINTS list with V1 19-entry corrected list — commit 268b1a6
- [x] T06 — chore(themen-plakat): regenerate template.sla + preview.pdf + page-01.png + meta.yml SHA bump — commit eb1abe7
  - SHA bumped: b89e2074… → f1159978…
- [x] T07 — chore(themen-plakat): brand_overrides cleanup in meta.yml — commit 1cc7c9e
  - 6 entries → 2 (REMOVED 4: visual_adjacency_drift, image_text_overlap, image_fills_frame, logo_size_3M)
- [x] T08 — test(smoke): rewrite test_themen_plakat_a3_quer.py for V1 anname set — commit a496ad5
- [x] T09 — docs(spec): rewrite _specs/themen-plakat-a3-quer.md for V1 layout — commit 669bcd5
  - spec_check 0 errors (was 24)
- [x] T10 — test(geometry): NEW invariant-pinning tests in test_themen_plakat_geometry.py — commit a2b2c8c
- [x] T11 — docs(brief): append session-history row + complete EXECUTION.md — pending

## ISSUE.md errata corrected during planning

- `scale_type=aspect_fill` (Open Question 1) → replaced with post-#24 INJECT_MAP idiom (locked decision #1). DSL has no aspect_fill enum; the canonical fix is `library.inject_into_frame(target_w_mm=item.w_mm, target_h_mm=item.h_mm)` which pre-crops the source to frame aspect.
- `same_x("Beleg N — Card", "Beleg N — Stat", "Beleg N — Label", "Beleg N — Body")` → would FAIL by 5 mm (Card.x=col_x but contents.x=col_x+5; 5 mm > 0.5 mm tol). Dropped Card from the per-row same_x; rely on 9 inside() containment witnesses (locked decision #2).
- `aligned_below("Themen-Hero", "Sub-Headline", gap_mm=8.0)` → geometrically invalid (Hero x=18, Sub x=235 — different columns; Hero y=73 ABOVE Sub y=172). Replaced with inside(Hero, Hero-Foto-Card) (locked decision #2).
- Logo `w=54` → corrected to `w=53.46` for exact 3M conformance (M=0.06×297=17.82, 3M=53.46) per locked decision #5; allowed removal of `brand:logo_size_3M` override.

## Brand-overrides cleanup (T07)

Before T07: 6 entries. After T07: 2 entries.

| id                              | Status            | Rationale |
|---------------------------------|-------------------|-----------|
| brand:line_spacing_0.9          | KEEP (extended)   | 5 existing + new beleg-body-on-green styles violate 0.9. Reason text extended with V1 13/16.9 rationale. |
| brand:hl_sl_distance_x2         | KEEP (rewritten)  | V1 60/40 split intentionally tight HL/Sub gap (2 mm); reason text rewritten for V1 columnar split. |
| brand:logo_size_3M              | REMOVED           | V1 logo `w=53.46` = exact 3M conformant. |
| brand:visual_adjacency_drift    | REMOVED           | V1 CONSTRAINTS list captures the central adjacencies (cards-row, mirror, per-card axis + containment). |
| brand:image_text_overlap        | REMOVED           | V1 text fully inside Hellgrün cards (rule docstring carve at brand_constraints.py:725-727). |
| brand:image_fills_frame         | REMOVED           | V1 INJECT_MAP pre-crop fills Hero exactly. |

## Verification gates (final state)

- `structural_check themen-plakat-a3-quer` → **0 errors**, 109 warnings, 2 skipped, 30 passes
- `structural_check --all` → **0 errors**, 122 warnings, 2 skipped, 34 passes (baseline maintained)
- `spec_check themen-plakat-a3-quer` → **0 errors**, 0 info, 0 extras
- `unittest templates._smoke.test_themen_plakat_a3_quer` → **8/8 pass**
- `unittest tools.sla_lib.tests.test_themen_plakat_geometry` → **13/13 pass**
- `unittest discover tools/sla_lib/tests` → **687 tests pass** (skipped=2)
- `bin/check-stale-previews` (themen-plakat) → exit 0 (GREEN)
- `bin/audit-alignment themen-plakat-a3-quer` → exit 0, **0 ERROR-severity** violations
- `check_ci.py templates/themen-plakat-a3-quer/template.sla` → exit 0 (warnings only)

The 109 structural_check warnings are real-and-expected from removing
`brand:visual_adjacency_drift`. They surface non-load-bearing adjacencies (e.g.
Beleg 3 — Stat to QR-Code right-edge) that the V1 CONSTRAINTS list does NOT need
to cover (CONSTRAINTS captures the load-bearing structural invariants —
cards-row, mirror, per-card axis, containment). All warnings are non-blocking.

## Acceptance criteria mapping (ISSUE.md)

- [x] V1 deltas applied in build.py in atomic tasks → T01 + T02 + T03 + T04 + T05 (5 commits)
- [x] build.py regenerates template.sla cleanly → T06 (bin/render-gallery exits 0, ~7s)
- [x] structural_check zero errors, all CONSTRAINTS green → T05 + T06 (19 CONSTRAINTS PASS)
- [x] --all stays green → T05, T06, T07 verified 0 errors maintained
- [x] check_ci.py passes → exit 0; baseline extra-style warnings only (now 9 vs 6 — 3 NEW V1 styles added to non_ci_styles list in T01)
- [x] Hero photo fills the frame → T04 INJECT_MAP idiom sets scale_type=0 + pre-crops to frame aspect; brand:image_fills_frame rule passes by-construction (override removed at T07)
- [x] HL/Sub-Gap exception documented → T07 brand:hl_sl_distance_x2 reason updated to V1 60/40 split rationale
- [x] Brief §10 gets the Session-History row → T11

Additional success criteria added by RESEARCH.md:

- [x] Smoke test reflects V1 anname set → T08
- [x] Spec rewritten + zero spec_check errors → T09
- [x] Invariant-pinning geometry tests added → T10
- [x] EXECUTION.md complete and committed → T11
- [x] BRAND_CONSTRAINTS registry stays at 15 (no new BrandRule added) → satisfied by NOT touching tools/sla_lib/builder/brand_constraints.py

## Out of scope (deferred)

- V2 "Hero Photo Plakat" (full-bleed photo half) — backlog
- V3 "Argument Stack" (foto-loses Backup) — backlog
- Codex visual review (locked decision #6 — SKIP for single-page A3)
- New BrandRule additions (locked decision #13 — registry stays at 15)
- Refactor of pre-existing non-conformant ParaStyles (themen-plakat/sub, beleg-headline,
  beleg-body, source, impressum) to satisfy brand:line_spacing_0.9 — template-wide drift
  outside #19 scope (locked #7 keeps the override)

## Open follow-ups

- README.md content discipline note (Open Question 2 from ISSUE.md): add a note to
  templates/themen-plakat-a3-quer/README.md about the new Stat-Hero requiring
  Bezirksgruppen content discipline (big number + caps label format). Tracked as
  future polish; not a #19 blocker.

## Deviations from plan

- T03 commits a transitional state where the old CONSTRAINTS list (still referencing
  `Beleg N — Headline` annames) reports 1 error / 3 warnings on `structural_check`. This
  is intentional per locked decision #10 atomic-PR ordering: T03 lands geometry, T05
  rewrites CONSTRAINTS to match. The plan's T03 verify block accepts this by only
  checking Python attribute introspection, not structural_check. T05 + T06 then deliver
  the green steady state.
- T05 lands 19 CONSTRAINTS (RESEARCH.md predicted 17 — the 2 additional same_style
  emerge from the parallel pattern). All geometrically valid by construction.
- T06 regen also updated `site/public/templates/themen-plakat-a3-quer/` mirror files
  (template.sla + preview.pdf + page-01.png) — staged together per the convention in
  e03c5bd.

## Self-Check

- [x] All files from plan exist
- [x] All commits exist on branch
- [x] Full verification suite passes (structural_check / spec_check / smoke /
      geometry / check_stale_previews / audit-alignment / check_ci all green)
- [x] No stubs / TODOs / placeholders introduced (verified by grep on touched files)
- [x] No leftover debug code

**Result:** PASSED

**Completed:** 2026-05-09T18:30:00Z
**Duration:** ~22 min
**Commits:** 11 (T01-T11) + EXECUTION

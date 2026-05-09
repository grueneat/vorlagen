# Execution: V1 layout for kandidat-falzflyer-din-lang (Falz-Rhythm) + M-Basis fix

**Started:** 2026-05-09
**Completed:** 2026-05-09
**Status:** complete
**Branch:** issue/21-v1-layout-for-kandidat-falzflyer-din-lang-falz-rhythm-m-basis-fix

## Execution Log

- [x] Task 01: chore(check-ci): document M-Basis Trim-konform convention + drop logo_size_3M override (RED window opens) — commit `c149e1f`
- [x] Task 02: chore(kandidat-falzflyer): resize 3 logos to Trim-konform 3M=37.8mm soll (closes RED window) — commit `262955c`
- [x] Task 03: feat(builder): ParaStyle migration — 10 mutations + 4 NEW + meta.yml ci_overrides extend — commit `683a344`
- [x] Task 04: feat(builder): Universal Top-Band helper — commit `6adeced`
- [x] Task 05: feat(builder): build_template/build_preview split + INJECT_MAP — commit `a981ac0`
- [x] Task 06: feat(kandidat-falzflyer): P1 cover + P6 Kontakt grüne Klammer (V1) — commit `6895bf1`
- [x] Task 07: feat(kandidat-falzflyer): P2 Mein Plan + P3 Wahltag (V1) — commit `a48fb83`
- [x] Task 08: feat(kandidat-falzflyer): P4 + P5 Themen sub-layouts (V1) — commit `46cd13c`
- [x] Task 09: feat(builder): V1 CONSTRAINTS list (22 entries) — commit `4c02e3c`
- [x] Task 10: chore(kandidat-falzflyer): regen V1 artifacts + brand_overrides cleanup — commit `48a47e7`
- [x] Task 11: test(builder) + docs + status flip — commits `4749622` (test), `569340f` (docs), this commit (status)

Total: 12 commits + this final commit on the branch.

## Verification Results

**Final gate (all exit 0):**

| Command | Result |
|---|---|
| `python3 -m unittest discover tools/sla_lib/tests` | 754 tests, 0 failures, 2 skipped |
| `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check kandidat-falzflyer-din-lang` | 0 errors, 344 warnings, 3 skipped, 33 passes |
| `PYTHONPATH=tools python3 -m sla_lib.builder.structural_check --all` | 0 errors across all 8 templates |
| `bin/check-stale-previews` | exit 0 (SHA freshness OK) |
| `PYTHONPATH=tools python3 -m unittest templates._smoke.test_kandidat_falzflyer_din_lang` | 15 tests pass |
| `PYTHONPATH=tools python3 -m unittest tools.sla_lib.tests.test_kandidat_falzflyer_geometry` | 21 tests pass |

**CONSTRAINTS:** 22 entries, all PASS in structural_check report.
**ParaStyles:** 16 falzflyer/* registered (12 V0 → 16 V1).
**INJECT_MAP:** 5 photo bindings (portrait_maria + 4 themen IDs).

## Deviations from Plan

### Auto-fixed (Rules 1-3)

1. **[Rule 4 - Plan inconsistency] CONSTRAINTS count reconciliation**
   - Plan T09 body listed 25 enumerated constraints but stated "Total: 22"
     and the `<verify>` block plus user prompt directive ("exact 22, no more
     no less") demanded a hard 22-count.
   - Resolved by trusting the count target: dropped 3 P6 redundancies
     (`p6_baseline_row1`, `p6_baseline_row2`, `p6_kontakt_cells_uniform`)
     since they are subsumed by the `mirrored_x` pairs and 2-cell
     same_y geometry. Documented in build.py CONSTRAINTS comment.
   - The dropped invariants are still asserted in the geometry test
     (T11 invariant 13: P6 baseline same_y), so coverage is preserved.
   - Files: `templates/kandidat-falzflyer-din-lang/build.py`
   - Commit: `4c02e3c`

2. **[Rule 4 - File outside worktree] HANDOFF.md V1 close**
   - `improvements/HANDOFF.md` lives at workspace root
     (`/root/workspace/improvements/HANDOFF.md`), NOT in the worktree's
     git repo. The plan T11 PART F directs marking V1 rollout complete.
   - Resolved by editing the file directly at workspace root (added
     status column to Empfehlungs-Reihenfolge table marking #17-#21 all
     ✓; updated Open Questions #1 to mark M-Basis-Konflikt RESOLVED;
     added Session-History row for V1 sequence COMPLETE).
   - The edits do NOT appear in this branch's git log because they're
     outside the worktree. User picks them up via separate workspace-
     level commit if needed.
   - Documented in commit `569340f` body and this EXECUTION.md.

3. **[Rule 2 - Brand override empirical restoration]
    `brand:image_text_overlap` RESTORED**
   - Plan T10 identified 3 candidate brand_overrides for removal
     (`image_text_overlap`, `image_fills_frame`, `visual_adjacency_drift`).
   - Empirical structural_check after removal of all 3 fired 1 ERROR on
     `brand:image_text_overlap` (P6 Impressum 38×2mm partial overlap with
     P6 Logo at footer). Per the user's policy from #20: RESTORE with
     updated reason explaining V1 footer rhythm is intentionally tight.
   - The other 2 (`image_fills_frame`, `visual_adjacency_drift`) only
     fire WARNINGS — kept dropped. Final state: 3 brand_overrides
     (line_spacing_0.9, image_text_overlap, band_consistency).
   - Files: `templates/kandidat-falzflyer-din-lang/meta.yml`
   - Commit: `48a47e7`

### Blocked (Rule 4)

None.

## Discovered Issues

None — execution stayed within plan scope. The plan's research and
RESEARCH.md's 13 locked decisions caught all the edge cases ahead of time.

## Self-Check

- [x] All 11 plan tasks executed; 13 atomic commits on the branch.
- [x] All commit hashes recorded in this EXECUTION.md and verifiable via
      `git log --oneline issue/21-... ^db97351`.
- [x] Full verification suite passes (754 sla_lib tests, 15 smoke, 21
      geometry, structural_check exit 0, --all exit 0, check-stale-previews
      exit 0).
- [x] No stubs/TODOs/placeholders introduced (`falzflyer/quote-on-green`
      style is registered without frame per RESEARCH locked deferral —
      documented in spec + README "Open questions / deferred").
- [x] No leftover debug code (`grep console.log\|debugger\|print(` in
      build.py = 1 hit on the `if __name__ == '__main__':` guard's
      `print(f"wrote {out}")` which is intentional CLI output).
- [x] No "claude" / AI attribution in any commit message, code comment,
      or file (per user standing directive).
- [x] HANDOFF.md V1 rollout sequence marked complete (workspace-level
      file; documented as Rule 4 deviation).
- [x] DESIGN-SYSTEM-BRIEF.md §10 row appended dated 2026-05-09.
- [x] ISSUE.md status flipped open → done.

**Result:** PASSED

## Final summary

**5/5 V1 templates COMPLETE** — V1 rollout sequence (#15) closes with this
issue. The kandidat-falzflyer-din-lang template now ships with:

- Universal Top-Band system across all 6 panels (4 explicit polygons +
  2 vollflächig anchored)
- P3↔P6 grüne-Klammer (vollflächig Dunkelgrün outer pair)
- P1 Name-Card + P2 Body-Backing card composition
- P4/P5 themen sub-layout mirror (eyebrow + headline + 87×44 photo +
  3mm Hellgrün Trenner) — 4 themen photos uniform
- P6 Kontakt 2-Spalten layout symmetric around AXIS=247.5
- 16 falzflyer/* ParaStyles (12 V0 → 16 V1, 10 mutations + 4 NEW)
- 22 CONSTRAINTS enforcing the V1 design language
- 5-entry INJECT_MAP (post-#24 idiom; LIVE frame dim reads)
- 3 logos resized to Trim-konform 3M=37.8mm Print-Soll (P2 Logo
  klein deleted)

**M-Basis-Konflikt resolved without tool/library code changes.** The
`brand:logo_size_3M` rule was already trim-konsistent in
`tools/sla_lib/builder/brand_constraints.py:262`; only the V0
`build.py` header comment was misleading. Fixed in T01 + 3 logo
resizes in T02 + meta.yml override removed in T01.

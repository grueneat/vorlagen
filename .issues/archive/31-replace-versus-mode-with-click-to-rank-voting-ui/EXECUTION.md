# Execution Log — Click-to-Rank Voting UI

**Status:** complete (T11 partial — manual mobile pass pending Flo; T-final = manual Flo voting + dual-section corpus update)
**Branch:** issue/31-replace-versus-mode-with-click-to-rank-voting-ui
**Worktree:** .worktrees/31-replace-versus-mode-with-click-to-rank-voting-ui/
**Scope this run:** T01–T13 (T-final = manual Flo voting session, deferred)
**Started:** 2026-05-11
**Completed:** 2026-05-11

## Tasks

- [x] T01 — Install SortableJS — edc6004 — pinned exact `1.15.7` (no caret) in `site/package.json`; `node -e "require('sortablejs')"` smoke-test passes
- [x] T02 — Delete versus mode — 30dd041 — removed versus HTML, pair generator, two-axis voting, keyboard map, wins-ratio/disagreement/Spearman JS, Fisher-Yates shuffle, versus localStorage; direct-pick path survives unchanged; build green
- [x] T03 — Rewrite results schema — 63b73c5 — new `oneOf` over `{mode:"rank"} | {mode:"direct-pick"}` with `not:{required:[<opposite>]}`; 11 schema tests pass (valid rank, valid direct-pick, ambiguous reject, missing/unknown mode, missing payload field, cross-branch field leak, duplicate-slug)
- [x] T04 — Rewrite aggregator — 8c32deb — deleted versus fns (compute_wins_ratio, ranking, disagreement_index, spearman_correlation); added compute_position_scores (linear Borda `(N-1-i)/(N-1)`, None for unranked, div-by-zero guard for N=1) + compute_position_scores_for_direct_pick (1.0/None); aggregate() validates per file + means non-None values per slug; render_summary() outputs top-3/bottom-3 + dropped + dual-section corpus stub
- [x] T05 — Rewrite aggregator tests — 709073a — RankAggregationTest (6 cases) + DirectPickFallbackTest (2 cases) + MixedModeAggregationTest (3 cases); DroppedAndCorpusStubTest preserved verbatim; 25 tests across both modules; full `tools/sla_lib/tests` discover passes (864 tests, 0 failures, 11 skipped)
- [x] T06 — Add rank-mode HTML — 854eb44 — `<section id="exp-rank">` + JS-rendered grid with sibling `<button class="checkmark">` (aria-label, aria-pressed=false, inner checkmark-visual + position-badge spans); `<ol id="ranked-list">` + #rank-empty + #export-rank; `<div aria-live="polite" aria-atomic="true">` live region; bundled `<script>` block with `import Sortable from 'sortablejs'` coexists with is:inline blocks; mode switcher defaults to rank when variants >= 3 (CONTEXT decision 2)
- [x] T07 — Add rank-mode CSS — e4e7867 — brand tokens (`var(--gruen-hell)` fill, `var(--gruen-dunkel)` border + badge text); .checkmark 44x44 hit zone with 28px visual; selected-state white tick via CSS borders; .position-badge top-left circular pill; .ranked-row grid layout with min-height:56px (CLS prevention); .drag-handle is the ONLY selector with `touch-action: none` (pitfall #5); .sr-only utility; mobile @media (max-width: 640px) drops grid to 150px minmax, keeps 44x44 inner buttons
- [x] T08 + T09 + T10 — Rank-mode JS (selection + reorder + export) — d119b0d — one cohesive bundled-script change covering all three: checkmark toggle with defensive ev.stopPropagation; localStorage key `experiment:<id>:session:v2:rank`; v1 cleanup scans `experiment:*:session:v1:*` keys, console.log + removeItem (silent migration); arrow ▲/▼ swap + aria-live announce "Moved '<slug>' from position N to M of T"; SortableJS init with handle/filter (pitfall #2 hard-required), delay:150, delayOnTouchOnly, touchStartThreshold:5; X remove with announce; sortableInstance.destroy() + re-init per refreshRankUI (rebuilt OL = fresh DOM); doExportRank builds `{mode:"rank", ranking}` payload, filename `<rater>-<exp>-rank-<YYYY-MM-DD>.json`, prompt() fallback when rater empty; rater sanitization `[a-z0-9_-]`
- [PARTIAL] T11 — Mobile verification — d119b0d (CSS + JS source) / 197df50 (final scrub) — automated CSS/build/touch-target audit PASS, manual 9-item checklist pending Flo (no headless mobile tooling)
- [x] T12 — Update experiments SKILL.md — 2e44f64 — removed all versus / pairwise / disagreement / spearman references; documented rank as primary mode + direct-pick as <3-variant fallback; updated capture section with new JSON shape, schema validation, linear Borda math; word count 1687 (well under 5000 floor)
- [x] T13 — Verify template byte-stability — 197df50 (covers T13 audit + final docstring scrub) — all 8 production `templates/*/page-01.png` SHA256s match `main` byte-for-byte
- [ ] T-final — Pending: manual Flo voting + dual-section corpus update (closes #29 T15 + #30 T17 + #31)

## Verification status

- Python unit tests: PASS — `python3 -m unittest discover tools/sla_lib/tests` Ran 864 tests in ~19 s, 0 failures, 11 skipped
- `npm --prefix site run build`: PASS — 12 pages built, no errors
- New schema validates rank + direct-pick + rejects ambiguous: PASS (11 schema-test cases)
- Aggregator handles rank shape (linear Borda) + direct-pick fallback (1.0): PASS (14 aggregator-test cases)
- Bundle size for rank-page chunk: 14.8 kB gzipped (`dist/_astro/_id_.astro_astro_type_script_index_0_lang.*.js`); within 20 kB gate
- Skill file <= 5000 words: PASS — 1687 words
- Production templates `page-01.png` byte-stable: PASS — all 8 templates match main
- Versus/pairwise/compute_wins/disagreement/spearman grep across touched files: returns empty (final acceptance gate)

## Commit chain (atomic, in order)

| Task | Commit | Description |
|------|--------|-------------|
| T01 | edc6004 | `chore(deps): add sortablejs@1.15.7 to site` |
| T02 | 30dd041 | `refactor(experiments): delete versus mode from voting page` |
| T03 | 63b73c5 | `refactor(schema): rewrite results schema for rank + direct-pick` |
| T04 | 8c32deb | `refactor(tools): rewrite experiment_results aggregator for rank shape` |
| T05 | 709073a | `test(tools): rewrite aggregator tests for rank + direct-pick` |
| T06 | 854eb44 | `feat(experiments): add rank-mode HTML scaffolding` |
| T07 | e4e7867 | `feat(experiments): add rank-mode CSS (brand tokens, touch targets)` |
| T08/T09/T10 | d119b0d | `feat(experiments): wire rank-mode JS (selection + reorder + export)` |
| T12 | 2e44f64 | `docs(skill): rewrite experiments SKILL.md for rank as primary mode` |
| T11/T13 + cleanup | 197df50 | `chore: scrub legacy mode-name references from prose + docstrings` |

## Choices documented per plan

- **SortableJS `delay`**: 150 ms, `delayOnTouchOnly: true`, `touchStartThreshold: 5` per resolved uncertainty #2. To be adjusted after Flo's mobile pass if accidental drags or sluggish drag-initiate appear.
- **Sortable re-init strategy**: destroy + re-attach on every `refreshRankUI()` (the rebuilt `<ol>` is a fresh DOM). Simpler than mutating rows in place and the row count is small (typically <= ~12) so destroy/init cost is negligible.
- **Position badge layout**: child of `<button class="checkmark">` (resolved uncertainty #3), absolutely positioned top-left within the button so it moves with the checkmark.
- **Rank-mode default**: enabled when `variants.length >= 3`. CONTEXT decision 2 fallback to direct-pick for <3.
- **Direct-pick export shape**: emits the new schema (`{mode:"direct-pick", selections}`) — the only consumer is `tools/experiment_results.py`, which now requires the v2 shape.

## T11 — Mobile verification: automated audit (executor) + manual checklist (Flo)

### Automated audit (executor, headless)

- `npm --prefix site run build` — PASS, no warnings
- `@media (max-width: 640px)` block present in generated CSS (verified in `dist/experiments/falzflyer-p2-mein-plan-v2/index.html`)
- Touch-target sizes in generated CSS for `.checkmark`, `.drag-handle`, `.ranked-row .arrow-up`, `.ranked-row .arrow-down`, `.ranked-row .remove-btn`: each declares `min-width: 44px` and `min-height: 44px` (or fixed `width: 44px; height: 44px` for `.drag-handle`)
- `touch-action: none` present on `.drag-handle` ONLY (verified via grep on both source `.astro` and generated `index.html`); never on row or container per pitfall #5
- Bundle size for rank-page chunk: 14.8 kB gzipped, under 20 kB gate
- Defensive `ev.stopPropagation` on checkmark + arrow + remove handlers

### Manual checklist (deferred to Flo — requires real phone or devtools mobile emulation)

- [ ] Variant grid collapses to 1-2 columns at 360px width without overflow.
- [ ] Checkmark hit zone is comfortable to tap (>=44x44 — confirm via devtools accessibility inspector or by tapping without missing).
- [ ] Tapping the image opens the lightbox; tapping the checkmark toggles selection without opening the lightbox (pitfall #1 verified live).
- [ ] Drag works on touch: long-press the `⋮⋮` handle, drag to reorder, drop. Items DO reorder; scrolling the page works when finger starts on a row body (not the handle).
- [ ] ▲/▼ arrows work on touch — single tap moves the row; no accidental drag (pitfall #2 verified live).
- [ ] X remove works on touch — single tap removes the row.
- [ ] Ranked list scrolls naturally below the grid; export button is reachable.
- [ ] aria-live announcements fire in a screen reader (VoiceOver iOS or TalkBack Android) on arrow-press and drop-end.
- [ ] Reload mid-session restores ranking from localStorage v2.

If any item fails: tune SortableJS `delay` (try 200 ms first, then 120 ms per resolved uncertainty #2); current value `delay: 150`.

## Discovered issues (out-of-scope, not fixed)

- `tools/sla_lib/tests/test_experiment_results_schema.py` previously referenced a JSON example carrying the old `votes` / `winner` shape; updated to a rank-mode example as part of T03 (in-scope side-effect, noted for traceability).
- Direct-pick mode export now emits the new schema shape (`mode:"direct-pick", selections`). The previous mixed payload that bundled wins-ratio etc. is gone; this is consistent with CONTEXT decision 9 (no backward compat) and the rewritten aggregator. In-scope per T02.

## Handoff to user (T-final)

<runbook>
1. Open https://grueneat.github.io/vorlagen/experiments/falzflyer-p2-mein-plan-v2/ on phone
2. Verify the 9-item mobile checklist above
3. Set rater field to `flo`, vote in rank mode
4. Click Export, save to experiments/falzflyer-p2-mein-plan-v2/results/flo-<DATE>.json
5. Run `bin/experiment-results falzflyer-p2-mein-plan-v2`
6. Amend `design-guide/gruene-corpus.md` with DUAL-SECTION update:
   - Section A: "From v1 (issue #29) — what we learned about envelope necessity"
   - Section B: "From v2 (issue #30 + #31) — density+form findings"
7. Commit results JSON + corpus update together — closes #29 T15 + #30 T17 + #31 in one commit
</runbook>

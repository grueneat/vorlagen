# CONTEXT — Design Decisions

Captured before research/planning. Research and planner MUST follow the locked decisions; the discretion section is open for the planner to refine; deferred items are explicitly out of scope.

## Decisions (locked — research/planner must follow)

### Voting modes

1. **Remove versus mode entirely.** The voting page exposes two modes only: `direct-pick` (existing, unordered favorites with star) and the new `rank` mode (ordered list). Versus mode + all its code paths in `site/src/pages/experiments/[id].astro` are deleted. `.claude/skills/experiments/SKILL.md` is updated to document rank as the primary mode.

2. **Rank becomes the default mode** on page load when an experiment has ≥3 variants. Direct-pick stays available for "I just want to mark favorites without ordering."

### Click semantics — IMPORTANT

3. **Clicking the variant image keeps its existing click-to-zoom lightbox behavior** (shipped in #28, reused in #29 on the experiments page). It does NOT toggle selection. This is non-negotiable — the image is the viewport for inspection.

4. **A dedicated checkmark control on each variant card toggles selection.** Recommended placement: top-right corner of the card, overlaid on the image. Default state: outlined empty checkmark. Selected state: filled green checkmark + position number badge ("1", "2", …) reflecting rank position in the list. Click the checkmark toggles selection on/off; the underlying image click is unaffected.

5. **The checkmark control must satisfy WCAG touch-target minimum** — ≥44×44px hit area on mobile, with adequate spacing from the image-click area (no accidental zoom while reaching for checkmark). Visual size can be smaller than the hit area (e.g., 32×32px visible, 44×44px tap zone).

6. **Ranked list below the variant grid** shows position number + variant title + small thumbnail + ▲/▼ reorder buttons + drag-handle (for SortableJS) + X remove button per row. Selecting an image adds it to the bottom of the list; subsequent selections append; deselecting removes from anywhere in the list.

### Reorder mechanism

7. **Both up/down arrow buttons AND drag-drop via SortableJS.** Arrows are the primary accessible path (keyboard + screen reader + clear semantics). Drag-drop is the secondary, tactile path. SortableJS handles mobile touch events correctly where native HTML5 DnD doesn't.

8. **SortableJS is the one new npm dependency** for the entire feature. Add to `site/package.json`. Latest stable, pinned. Mobile touch-and-drag must work; verified during T-implement.

### Schema and aggregator

9. **New ranking-format JSON only; old pairwise format is deprecated.** `experiments/_schema/results.schema.yaml` is rewritten to accept only the new shape. Old v1 pairwise results (none committed; locally generated only) are not processable. The schema bump is a breaking change documented in `.claude/skills/experiments/SKILL.md`.

10. **New results JSON shape:**
    ```json
    {
      "experiment_id": "falzflyer-p2-mein-plan-v2",
      "rater": "flo",
      "started_at": "2026-05-11T12:00:00Z",
      "exported_at": "2026-05-11T12:18:00Z",
      "mode": "rank",
      "ranking": ["slug-1", "slug-2", "slug-3", "..."]
    }
    ```
    `ranking` is an ordered list of variant slugs. `mode` is `"rank"` or `"direct-pick"`. For `direct-pick` exports, the field is `"selections"` (unordered set) instead of `ranking` — schema uses `oneOf` to enforce shape per mode.

11. **`tools/experiment_results.py` aggregator changes:**
    - Reads new ranking JSON, computes per-variant `position_score` = `(N - rank) / (N - 1)` for variant at rank `rank` out of `N` total ranked. Variants not in the ranked list get `position_score = null` (excluded from ranking, not zero).
    - SUMMARY.md still produces top-3 / bottom-3 + dual-section corpus stub (v1 envelope-necessity + v2 density+form findings).
    - No more disagreement index / Spearman / dual-axis surfacing — single-axis ranking only. Those calculations belong in the deprecated pairwise aggregator (deleted in this issue).
    - Backward-compat fallback for `direct-pick` JSON: `position_score = 1.0` for every selected variant, `null` for unselected. Top-3 by selection count.

### Mobile UX

12. **Page must work on a phone screen** (verified during T-implement against a real mobile viewport, ≥360px wide). The variant grid collapses to 1-2 columns on narrow screens. Ranked list takes full width below.

13. **Touch targets** for checkmark, arrows, X, and drag-handle ALL meet WCAG AA ≥44×44px tap zone.

### LocalStorage + export

14. **LocalStorage key updated** to include mode: `experiment:<exp-id>:session:v2:<mode>` (was `v1`). Schema version bumped to `v2`. Old `v1` keys are NOT migrated — first load of the new page clears them (with a one-line console.log noting the migration).

15. **Export filename**: `<rater>-<exp-id>-<mode>-<YYYY-MM-DD>.json` (mode now included to avoid collisions if a rater does both modes).

## Claude's Discretion (research/planner explores)

- Exact visual treatment of selected/unselected checkmark (filled green vs filled brand green; position number badge font and color).
- Whether the position badge overlays the checkmark or is a separate element next to it.
- Drag-handle vs whole-row drag in the ranked list (SortableJS supports both).
- Animation/transition on add/remove/reorder (subtle, no library beyond CSS).
- Whether to surface "X selected / Y not yet ranked" counter near the export button.
- Where the export button lives on mobile (sticky bottom vs in-flow at bottom of ranked list).
- Whether the ranked list collapses/expands on mobile to free viewport space when reviewing variants.
- Whether to dedupe the per-variant title (the hypothesis name) at the rank-list-row level vs in the per-card overlay (could be only in the list to keep cards clean).

## Deferred (out of scope for this issue — phase 2 / separate issue)

- Re-introducing dual-axis (appeal + transport) within rank mode — single combined ranking only for this issue
- Multi-rater real-time merging
- Adaptive sampling
- Auto-corpus-update from results
- Versus mode revival (deleted entirely; if pairwise data becomes valuable, a new issue revives it cleanly without touching the old code path)
- Migrating any v1 pairwise JSON results to the new format (none committed, so no migration needed)
- Mobile-specific gestures beyond drag (no swipe-to-remove, no long-press menus)

---
id: '31'
title: Replace versus mode with click-to-rank voting UI
status: open
priority: high
labels:
- enhancement
- templates
- visual-qa
source: github
source_id: 62
source_url: https://github.com/GrueneAT/vorlagen/issues/62
---

## Context

Issues #29 + #30 shipped a working experiment system with two voting modes: direct-pick (favorites) and versus (pairwise tournament). User reviewed v2 on phone (https://grueneat.github.io/vorlagen/experiments/falzflyer-p2-mein-plan-v2/) and reports: **versus mode is too complicated and work-intensive**. Wants a simpler ranking mechanism.

## Solution

Add a new "rank" mode (or replace versus mode entirely) with a click-to-add-then-reorder UX:

1. All variants render in a grid (similar to direct-pick layout).
2. Click an image → adds it to a "ranked choices" list below the grid.
3. Below the variants: ordered list of selections showing position number + variant title + small thumbnail + remove button per item.
4. Reorder via drag-drop on desktop, up/down arrow buttons on mobile (or both).
5. Click an image a second time OR click the list-item remove button → removes it.
6. Single combined ranking (no axes split) — user explicitly chose this for simplicity over dual-axis purity.
7. Export JSON has new shape: `{ rater, started_at, exported_at, experiment_id, ranking: [slug, slug, ...] }`.

## Tooling changes

- `site/src/pages/experiments/[id].astro` — implement the new mode. Keep existing direct-pick mode; replace versus mode with rank mode (or add rank as third mode and demote versus to "advanced" — planner decides).
- `experiments/_schema/results.schema.yaml` — extend schema to accept the new ranking shape alongside the existing pairwise shape (backward compatibility).
- `tools/experiment_results.py` — read the new format. Computed wins-ratio per variant becomes "position score" (e.g., 1.0 for #1, decreasing); same SUMMARY.md output shape.
- `.claude/skills/experiments/SKILL.md` — document the new mechanism, deprecate or de-emphasize versus mode.

## Acceptance Criteria

- [ ] Rank mode implemented in `site/src/pages/experiments/[id].astro`
- [ ] Click-image-to-add works on desktop and mobile
- [ ] Ranked list below variants shows position, title, thumbnail, remove button per item
- [ ] Reorder works (drag-drop or up/down arrows; both ideally)
- [ ] localStorage persists ranking across reload
- [ ] Export JSON has the new shape; validates against extended results schema
- [ ] `tools/experiment_results.py` aggregates the new ranking format; SUMMARY.md still produces top-3 / bottom-3 + dual-section corpus stub
- [ ] `.claude/skills/experiments/SKILL.md` updated to describe rank mode as the primary voting UX
- [ ] Mobile-responsive — verified on actual phone screen
- [ ] Flo votes a v2 session using rank mode → results JSON committed → `design-guide/gruene-corpus.md` amended with dual-section update (v1 envelope-necessity + v2 density+form findings). This closes #29 T15, #30 T17, AND #31's deliverable in one move.

## Out of scope (phase 2)

- Reintroducing dual-axis (appeal + transport) within rank mode — single combined ranking only for this issue
- Multi-rater merging
- Adaptive sampling

## Dependencies

#29 + #30 (both merged). Voting page at `site/src/pages/experiments/[id].astro` is the touchpoint.

## Priority

High — gating the corpus contribution from v2 (and v1's deferred T15). Without a usable voting UX, the merge gate on both prior issues can't actually close.

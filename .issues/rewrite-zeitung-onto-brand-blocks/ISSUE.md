---
id: '8'
title: Rewrite Zeitung A4 onto Brand + blocks
status: done
priority: high
labels:
- dsl
- refactor
- migration
depends_on:
- 5
source: github
source_id: 13
source_url: https://github.com/GrueneAT/vorlagen/issues/13
---

## Goal

Rewrite `templates/zeitung-a4-grun/build.py` onto `Brand.gruene_noe()` + the 5
evidence-driven blocks landed in issue #5. Target: ≤2400 LOC (down from 3244).

## Why now

Gating from issue #5 — no new templates land before P1 hardening merges. Zeitung is
last in the size-order migration sequence (Postkarte → Plakat → Zeitung) because it is
the most complex template (84 `ColumnTextStory` frames, 12 `PageNumber` frames, 23
master-page items, and 3244 LOC). The migration patterns from issues #6 and #7 should
be established first.

## Inputs

- `templates/zeitung-a4-grun/template.sla` (committed)
- `templates/zeitung-a4-grun/baseline.pdf` (committed visual baseline)
- `tools/sla_lib/builder/brand.py` — `Brand.gruene_noe()` from issue #5
- `tools/sla_lib/builder/blocks.py` — 5 evidence-driven blocks from issue #5
- Issues #6 and #7 (Postkarte and Plakat migrations) for established migration pattern

## Approach

1. Re-run `tools/sla_to_dsl.py` against the existing `template.sla` after issue #5 lands.
   The emitter now produces a slim `build.py` using `brand=Brand.gruene_noe()`, dropped
   pt-geometry overrides, and `clip_edit=True` without explicit rect-paths (~86 frames lose
   2 lines each, net ~170 LOC reduction from clip-rect noise alone).
2. Where idioms map to blocks, hand-edit:
   - 12 `var='pgno'` frames → `PageNumber` block
   - 84 `ColumnTextStory` pattern frames → `ColumnTextStory` block
   - `PageBackground` on Titelseite → `PageBackground` block
   - `Impressum` frames → `Impressum` block
3. Run `bin/validate --ci` to confirm visual diff vs baseline is clean.
4. Measure LOC and confirm ≤2400.

## Acceptance criteria

- `tools/visual_diff.py` clean against `templates/zeitung-a4-grun/baseline.pdf`
  (within `docs/diff-tolerance.md` thresholds).
- `pytest tools/sla_lib/tests -x` green.
- `bin/validate --ci` green for ALL three templates (no regression on plakat/postkarte).
- `build.py` LOC ≤ 2400 — verify and document the actual number in EXECUTION.md.
- `tools/check_ci.py templates/zeitung-a4-grun` clean.
- `extra_doc_attrs` in the new `build.py` contains ≤ 23 keys.
- `extra_pdf_attrs` in the new `build.py` contains ≤ 11 keys.

## Non-goals

- No visual changes to the rendered output.
- No `template.sla` hand-edits (templates regenerate from `build.py` only).
- No further DSL changes (those go back to issue #5 successors).
- No migration of Postkarte or Plakat (separate issues #6 and #7).

## Depends on

Issue #5 (DSL hardening + Brand + blocks) must be merged before this issue starts.
Issues #6 and #7 (Postkarte and Plakat migrations) should be merged first to establish
the pattern, but are not hard dependencies.

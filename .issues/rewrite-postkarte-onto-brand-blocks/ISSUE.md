---
id: '6'
title: Rewrite Postkarte A6 onto Brand + blocks
status: open
priority: high
labels:
- dsl
- refactor
- migration
depends_on:
- 5
source: github
source_id: 11
source_url: https://github.com/GrueneAT/vorlagen/issues/11
---

## Goal

Rewrite `templates/postkarte-a6-kampagne/build.py` onto `Brand.gruene_noe()` + the 5
evidence-driven blocks landed in issue #5. Target: ≤280 LOC (down from 437).

## Why now

Gating from issue #5 — no new templates land before P1 hardening merges. Postkarte is
first in the size-order migration sequence (Postkarte → Plakat → Zeitung) because it is
the smallest non-trivial template, offering the highest signal-to-noise ratio for the
migration pattern.

## Inputs

- `templates/postkarte-a6-kampagne/template.sla` (committed)
- `templates/postkarte-a6-kampagne/baseline.pdf` (committed visual baseline)
- `tools/sla_lib/builder/brand.py` — `Brand.gruene_noe()` from issue #5
- `tools/sla_lib/builder/blocks.py` — 5 evidence-driven blocks from issue #5

## Approach

1. Re-run `tools/sla_to_dsl.py` against the existing `template.sla` after issue #5 lands.
   The emitter now produces a slim `build.py` using `brand=Brand.gruene_noe()`, dropped
   pt-geometry overrides, and `clip_edit=True` without explicit rect-paths.
2. Where idioms map to blocks (`Impressum`, `ContactBlock`, `PageBackground`,
   `PageNumber`), hand-edit the generated `build.py` to use the block.
3. Run `bin/validate --ci` to confirm visual diff vs baseline is clean.
4. Measure LOC and confirm ≤280.

## Acceptance criteria

- `tools/visual_diff.py` clean against `templates/postkarte-a6-kampagne/baseline.pdf`
  (within `docs/diff-tolerance.md` thresholds).
- `pytest tools/sla_lib/tests -x` green.
- `bin/validate --ci` green for ALL three templates (no regression on plakat/zeitung).
- `build.py` LOC ≤ 280 — verify and document the actual number in EXECUTION.md.
- `tools/check_ci.py templates/postkarte-a6-kampagne` clean.
- `extra_doc_attrs` in the new `build.py` contains ≤ 23 keys.
- `extra_pdf_attrs` in the new `build.py` contains ≤ 11 keys.

## Non-goals

- No visual changes to the rendered output.
- No `template.sla` hand-edits (templates regenerate from `build.py` only).
- No further DSL changes (those go back to issue #5 successors).
- No migration of Plakat or Zeitung (separate issues #7 and #8).

## Depends on

Issue #5 (DSL hardening + Brand + blocks) must be merged before this issue starts.

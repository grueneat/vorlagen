---
id: '7'
title: Rewrite Plakat A1 onto Brand + blocks
status: done
ship_state: merged
priority: high
labels:
- dsl
- refactor
- migration
depends_on:
- 5
source: github
source_id: 12
source_url: https://github.com/GrueneAT/vorlagen/issues/12
---

## Goal

Rewrite `templates/plakat-a1-hochformat/build.py` onto `Brand.gruene_noe()` + the 5
evidence-driven blocks landed in issue #5. Target: ≤180 LOC (down from 235).

## Why now

Gating from issue #5 — no new templates land before P1 hardening merges. Plakat is
second in the size-order migration sequence (Postkarte → Plakat → Zeitung). Postkarte's
migration (issue #6) establishes the migration pattern; Plakat applies it to a simpler
single-page poster layout.

## Inputs

- `templates/plakat-a1-hochformat/template.sla` (committed)
- `templates/plakat-a1-hochformat/baseline.pdf` (committed visual baseline)
- `tools/sla_lib/builder/brand.py` — `Brand.gruene_noe()` from issue #5
- `tools/sla_lib/builder/blocks.py` — 5 evidence-driven blocks from issue #5
- Issue #6 (Postkarte migration) for established migration pattern

## Approach

1. Re-run `tools/sla_to_dsl.py` against the existing `template.sla` after issue #5 lands.
   The emitter now produces a slim `build.py` using `brand=Brand.gruene_noe()`, dropped
   pt-geometry overrides, and `clip_edit=True` without explicit rect-paths.
2. Where idioms map to blocks (`PageBackground`, `Impressum`), hand-edit the generated
   `build.py` to use the block.
3. Run `bin/validate --ci` to confirm visual diff vs baseline is clean.
4. Measure LOC and confirm ≤180.

## Acceptance criteria

- `tools/visual_diff.py` clean against `templates/plakat-a1-hochformat/baseline.pdf`
  (within `docs/diff-tolerance.md` thresholds).
- `pytest tools/sla_lib/tests -x` green.
- `bin/validate --ci` green for ALL three templates (no regression on postkarte/zeitung).
- `build.py` LOC ≤ 180 — verify and document the actual number in EXECUTION.md.
- `tools/check_ci.py templates/plakat-a1-hochformat` clean.
- `extra_doc_attrs` in the new `build.py` contains ≤ 23 keys.
- `extra_pdf_attrs` in the new `build.py` contains ≤ 11 keys.

## Non-goals

- No visual changes to the rendered output.
- No `template.sla` hand-edits (templates regenerate from `build.py` only).
- No further DSL changes (those go back to issue #5 successors).
- No migration of Postkarte or Zeitung (separate issues #6 and #8).

## Depends on

Issue #5 (DSL hardening + Brand + blocks) must be merged before this issue starts.
Issue #6 (Postkarte migration) should be merged first to establish the pattern, but is
not a hard dependency.

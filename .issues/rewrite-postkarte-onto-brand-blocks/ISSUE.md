---
id: '6'
title: Rewrite Postkarte A6 onto Brand + blocks
status: done
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
evidence-driven blocks landed in issue #5. The rewrite is judged by visual-diff
fidelity and Brand-profile uptake, not by an absolute LOC target.

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
3. Where the current block API has a gap that prevents a clean substitution, leave the
   frames as primitives and file the gap as a P2 follow-up (block widening). Do NOT
   widen blocks inside this issue beyond the smallest local fixes (e.g. forwarding
   already-supported kwargs through factory methods).
4. Run `bin/validate --ci` to confirm visual diff vs baseline is clean.
5. Measure and document the achieved LOC in EXECUTION.md (informational; not an AC).

## Acceptance criteria

- `tools/visual_diff.py` clean against `templates/postkarte-a6-kampagne/baseline.pdf`
  (within `docs/diff-tolerance.md` thresholds).
- `pytest tools/sla_lib/tests -x` green.
- `bin/validate --ci` green for ALL three templates (no regression on plakat/zeitung).
  Implementing this is allowed to require fixing `tools/sla_diff.py` to allow
  brand-injected `extra-layer`/`extra-style` warnings (the existing `test_sla_to_dsl.py`
  has a code-level allowlist; `bin/validate` lacks the equivalent flag). The
  `--allow-brand-extras` (or equivalent) sla_diff change is in scope.
- `tools/check_ci.py templates/postkarte-a6-kampagne` clean.
- `extra_doc_attrs` in the new `build.py` contains ≤ 23 keys.
- `extra_pdf_attrs` in the new `build.py` contains ≤ 11 keys (may require a 1-line
  addition of the missing key to `shared/ci-defaults.yml`).

## Non-goals

- No visual changes to the rendered output.
- No `template.sla` hand-edits (templates regenerate from `build.py` only).
- No further DSL changes (those go back to issue #5 successors).
- No migration of Plakat or Zeitung (separate issues #7 and #8).

## Depends on

Issue #5 (DSL hardening + Brand + blocks) must be merged before this issue starts.

---
id: '9'
title: 'Post-migration DSL hygiene: Impressum widening, fresh-run test, extras audit'
status: done
ship_state: pr_open
priority: medium
labels:
- dsl
- refactor
- test
source: github
source_id: 17
source_url: https://github.com/GrueneAT/vorlagen/issues/17
---

## Goal

Three small DSL hygiene items surfaced as P2 follow-ups across the size-order migration sequence (#6 Postkarte, #7 Plakat, #8 Zeitung). Combine them into one short hardening pass so the DSL doesn't carry a backlog of post-migration paper cuts.

## Why now

All three are mechanical, individually small, and share the same files (`tools/sla_lib/builder/blocks.py`, `tools/sla_lib/tests/test_sla_to_dsl.py`, `tools/sla_diff.py`, `shared/ci-defaults.yml`). Folding them into a single issue avoids three near-trivial PRs.

## Scope

### A. Impressum block widening — three accumulated gaps

Across the migration sequence, the `Impressum` block surfaced three API gaps that each blocked a clean substitution. All three migrations kept `Impressum` as a primitive `TextFrame` and deferred. Land them together:

1. **Bold-prefix Run** (surfaced by Postkarte #6) — Impressum text often opens with a bold "Impressum:" run before the body. Add `prefix_text: str | None = None`, `prefix_font: str = "Gotham Narrow Bold"` (or similar) so the block emits two Runs when `prefix_text` is set.
2. **Rotation** (surfaced by Plakat #7) — Plakat's Impressum is rotated 270°. Add `rotation_deg: float = 0` kwarg passthrough to the inner `TextFrame`.
3. **3-run heading + spacer + body schema** (surfaced by Zeitung #8) — Zeitung's Impressum follows a heading-Run + paragraph-break-Run + body-Run pattern. Generalize the block to accept an optional `heading_text` + `heading_font` + `heading_paragraph_style` triple and emit the spacer-Run between heading and body when set.

Verify by either re-running the converter against each template in a `/tmp/` regen and confirming the original-but-now-block-substitutable Impressum sites would diff clean — OR by adding a unit test per gap in `tools/sla_lib/tests/test_blocks.py`.

### B. `ZeitungConverterFreshRun` test class

`tools/sla_lib/tests/test_sla_to_dsl.py` has `PostkarteRoundTrip` and `PlakatRoundTrip` test classes that exercise SLA→build.py→SLA round-tripping with the brand-additive allowlist. Zeitung doesn't have an equivalent class, despite being the largest and most feature-exercising template. Add `ZeitungConverterFreshRun` mirroring the existing two patterns. Hygiene only — no behavioural changes.

### C. `extra_*_attrs` / `_LEGACY_LAYER_NAMES` audit

After the three migrations, audit:

1. `extra_doc_attrs` and `extra_pdf_attrs` blobs in the rebuilt `templates/*/build.py`. Compare which keys still appear identically across all three. Any key now identical across all three is a candidate to hoist into `shared/ci-defaults.yml`. Rebuild + visual-diff after each hoist.
2. `_LEGACY_LAYER_NAMES` in `tools/sla_diff.py` (the brand-stack allowlist for `--allow-brand-extras`'s `missing-layer` filter). The current set was sized for Zeitung's `Ebene 1`. Confirm Postkarte and Plakat don't have additional legacy-layer names that should be filtered.

This audit is investigation + small config tweaks. Don't widen any allowlist beyond what's actually needed.

## Acceptance criteria

- [ ] `Impressum` block accepts `prefix_text`/`prefix_font`, `rotation_deg`, and the heading/spacer/body schema. Each gap has at least one unit test in `tools/sla_lib/tests/test_blocks.py`.
- [ ] `ZeitungConverterFreshRun` class exists in `tools/sla_lib/tests/test_sla_to_dsl.py` mirroring the `PostkarteRoundTrip` / `PlakatRoundTrip` shape.
- [ ] `extra_doc_attrs` / `extra_pdf_attrs` audit completed; any cross-template-identical keys hoisted to `shared/ci-defaults.yml` and the rebuilt templates' attr counts updated.
- [ ] `_LEGACY_LAYER_NAMES` audit completed; the set is documented as either complete-as-is or expanded with justification.
- [ ] `pytest tools/sla_lib/tests` green and `python3 -m unittest discover tools/sla_lib/tests` green (CI uses unittest, not pytest — see #16's CI fix).
- [ ] `bin/validate --ci` green for ALL three templates.
- [ ] No visual_diff drift against committed gallery PDFs.

## Non-goals

- No new template migrations.
- No DSL surface changes beyond the listed three areas.
- No converter (`tools/sla_to_dsl.py`) behavioural changes.
- No further block additions beyond extending `Impressum`.

## Pointers

- `tools/sla_lib/builder/blocks.py` — `Impressum` class (~lines 89–124 pre-edit; check current line range)
- `tools/sla_lib/tests/test_blocks.py` — block unit tests (add coverage for the 3 Impressum gaps)
- `tools/sla_lib/tests/test_sla_to_dsl.py` — `PostkarteRoundTrip` / `PlakatRoundTrip` shape; add `ZeitungConverterFreshRun` mirror
- `tools/sla_diff.py` — `_LEGACY_LAYER_NAMES` constant; `--allow-brand-extras` filter predicate
- `shared/ci-defaults.yml` — hoisted brand defaults
- `templates/*/build.py` — rebuilt files; the source for any further attr-hoist analysis
- Background context: archived issues #6, #7, #8.

## Test runner note

When verifying tests, run BOTH:
- `pytest tools/sla_lib/tests -q` (matches local development)
- `python3 -m unittest discover tools/sla_lib/tests` (matches CI exactly — caught a stray `import pytest` in #8 only after CI failed)

# Execution: Post-migration DSL hygiene — Impressum widening, Zeitung fresh-run, extras audit

**Started:** 2026-05-07T14:20:00Z
**Status:** complete
**Branch:** issue/post-migration-dsl-hygiene

---

## Tasks

- [x] Task 1: Widen the Impressum dataclass and emit() — commit 580295c
- [x] Task 2: Add 4 unittest-style coverage tests for the widened Impressum — commit b5ea830
- [x] Task 3: Add ZeitungConverterFreshRun mirror class — commit e9567bb
- [x] Task 4: Document the C1 + C2 audit outcomes — commit 1bfaeaf
- [x] Task 5: Final gate — all four gates green

---

## Audit C1: extra_doc_attrs / extra_pdf_attrs cross-template

- Method: programmatically computed `set ∩ set ∩ set` over the three
  template `Document(...)` calls (Postkarte build.py:29-30,
  Plakat build.py:28-29, Zeitung build.py:29-30).
- Hard counts:
  - `extra_doc_attrs`: 23 keys per template, 23 keys in the 3-way set
    intersection, **0 keys with identical VALUES across all three**
    templates.
  - `extra_pdf_attrs`: 11 keys per template, 11 keys in the 3-way set
    intersection, **0 keys with identical VALUES across all three**
    templates.
- Outcome: **No hoist candidates remain.** `shared/ci-defaults.yml`
  already absorbs every truly-shared key during issues #6/#7/#8. The
  residual 23+11 keys diverge in value because they encode per-template
  state (color profile names, paper size, image DPI, Scribus
  user-preference state, or Zeitung's higher-precision float
  serialization).
- Action taken: **none.** No edit to `shared/ci-defaults.yml`. No edit
  to any `templates/*/build.py`.

## Audit C2: _LEGACY_LAYER_NAMES (tools/sla_diff.py)

- Method: grepped `<LAYERS NAME=...>` in the three workspace-root SLA
  originals.
- Findings:
  - `postkarte-vorlage-original.sla`: only `Hintergrund` (already in
    `Brand.gruene_noe()` 4-layer stack — produces no warning).
  - `plakat-a1-hochformat-original.sla`: only `Hintergrund` (same as
    Postkarte).
  - `gruene-zeitung-vorlage-original.sla`: `Ebene 1` (already in
    `_LEGACY_LAYER_NAMES`).
- Outcome: `_LEGACY_LAYER_NAMES = ("Ebene 1",)` is **complete-as-is**
  for the three current templates.
- Action taken: **none.** No edit to `tools/sla_diff.py`.

---

## Acceptance criteria

- [x] `Impressum` block accepts `prefix_text`/`prefix_font`, `rotation_deg`, and
  the heading/spacer/body schema; each gap has at least one unit test in
  `tools/sla_lib/tests/test_blocks.py` — Tasks 1 + 2.
- [x] `ZeitungConverterFreshRun` class exists in `test_sla_to_dsl.py` mirroring
  `PostkarteConverterFreshRun` shape — Task 3.
- [x] `extra_doc_attrs` / `extra_pdf_attrs` audit completed; 0 hoist candidates
  documented in Audit C1 above — Task 4.
- [x] `_LEGACY_LAYER_NAMES` audit completed; complete-as-is documented in Audit C2
  above — Task 4.
- [x] `pytest tools/sla_lib/tests` green AND `python3 -m unittest discover
  tools/sla_lib/tests` green — Task 5 (261 tests, 0 failures).
- [x] `bin/validate --ci` green for all three templates — Task 5.
- [x] No visual_diff drift against committed gallery PDFs — Task 5 (covered by
  `bin/validate --ci`).

---

## Verification Results

### Gate 1: pytest tools/sla_lib/tests -q

```
261 passed, 3 warnings, 18 subtests passed in 1.26s
```

### Gate 2: python3 -m unittest discover tools/sla_lib/tests

```
Ran 261 tests in 1.165s
OK
```

### Gate 3: bin/validate --ci

```
=== preflight: bin/check-fontsizes ===
preflight: PASS

=== preflight: bin/check-stale-previews ===
preflight: PASS

=== plakat-a1-hochformat ===
  original: plakat-a1-hochformat-original.sla
  template: templates/plakat-a1-hochformat/template.sla
  sla_diff: PASS
  visual_diff (96dpi): PASS
=== postkarte-a6-kampagne ===
  original: postkarte-vorlage-original.sla
  template: templates/postkarte-a6-kampagne/template.sla
  sla_diff: PASS
  visual_diff (96dpi): PASS
=== zeitung-a4-grun ===
  original: gruene-zeitung-vorlage-original.sla
  template: templates/zeitung-a4-grun/template.sla
  sla_diff: PASS
  visual_diff (96dpi): PASS
```

### Gate 4: python3 tools/check_ci.py (non-strict mode)

```
Exit code: 0
(template-local extra-style warnings are expected; no critical issues)
```

---

## P3 follow-ups (out of scope here)

- Substituting the three primitive `TextFrame(trail_style='Impressum', ...)` corpus
  sites in `templates/*/build.py` for `Impressum(...)` block calls (RESEARCH.md §E2).
  Saves ~36 LOC across the three templates but adds visual_diff churn risk; defer until
  next hygiene pass or until the user explicitly asks.
- Optional `gruene_noe_kleinformat` 2-way preset for Postkarte+Plakat shared values
  (RESEARCH.md §E6). Re-evaluate when a 4th small-format template lands.
- Optional `PlakatConverterFreshRun` for symmetry with Postkarte and Zeitung. Trivially
  mirror-able if the user wants full converter coverage.

---

## Self-Check

- [x] All files from plan exist: `tools/sla_lib/builder/blocks.py`, `tools/sla_lib/tests/test_blocks.py`, `tools/sla_lib/tests/test_sla_to_dsl.py`, `EXECUTION.md`
- [x] All commits exist on branch: 580295c, b5ea830, e9567bb, 1bfaeaf
- [x] Full verification suite passes (261 tests, 0 failures, bin/validate --ci PASS)
- [x] No stubs/TODOs/placeholders
- [x] No leftover debug code
- [x] No `import pytest` in any file under `tools/sla_lib/tests/`
- **Result:** PASSED

**Completed:** 2026-05-07T14:45:00Z
**Duration:** ~25 minutes
**Commits:** 5 (including this EXECUTION.md finalization)

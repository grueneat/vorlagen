# Execution: Post-migration DSL hygiene — Impressum widening, Zeitung fresh-run, extras audit

**Started:** 2026-05-07T14:20:00Z
**Status:** in_progress
**Branch:** issue/post-migration-dsl-hygiene

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

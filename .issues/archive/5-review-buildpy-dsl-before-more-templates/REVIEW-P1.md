# P1 Reconciled — issue 5

Source: REVIEW.md (authoritative) + RESEARCH.md (planner input).

---

## Final P1 list (executor implements in this order)

1. **Brand profile** — new `tools/sla_lib/builder/brand.py` (~120 LOC); `shared/ci-defaults.yml`
   holding the 113 identical `extra_doc_attrs` keys + 34 identical `extra_pdf_attrs` keys;
   `Document(brand=...)` kwarg; `palette_replaces_ci=False` default on brand path.
   Maps to **Task 3**. Source: REVIEW.md §Higher-level construct proposals + §Prioritized P1 backlog P1-1.
   Notes: All three reviewers converged on Option A (frozen dataclass). No deviations from RESEARCH.md.

2. **Evidence-driven blocks** — replace `blocks.py` 8 aspirational blocks with 5 corpus-backed blocks
   (`PageNumber`, `Impressum`, `PageBackground`, `ContactBlock`, `ColumnTextStory`); rewrite
   `test_blocks.py`. Old 8 blocks move to `blocks.legacy`.
   Maps to **Task 4**. Source: REVIEW.md §Higher-level construct proposals + §Prioritized P1 backlog P1-2.
   Notes: Reordered ahead of converter changes (blocks need Brand context to be clear first).

3. **Converter leanness** (three sub-steps in order):
   - **3a**: Emit `brand=Brand.gruene_noe()` and only the 23 differing `extra_doc_attrs` keys
     + 11 differing `extra_pdf_attrs` keys. Flip `palette_replaces_ci` to `False` on brand path.
   - **3b**: Drop redundant `xpos_pt/ypos_pt/width_pt/height_pt`; gate behind `--strict-bytes`
     flag if `sla_diff` byte-equivalence is gated in CI (verify first by running the sla_diff
     tests). Per REVIEW.md Codex B-6: this is not yet safe without the `sla_diff` check.
   - **3c**: Auto-emit `clip_edit=True` rectangle path in DSL so `custom_path=` can be omitted
     for the 86 Zeitung frames with verbatim rect paths.
   Maps to **Task 5**. Source: REVIEW.md §Prioritized P1 backlog P1-3.

4. **DSL ergonomics** (critical fix first, then rest):
   - **Critical (A-1)**: Remove `Line` from public surface (`__init__.py`, `docs/dsl-reference.md`,
     tests); document that lines are emitted as `Polygon(custom_path=..., line_color=..., fill='None')`.
     This is the first sub-step before any other ergonomics change.
   - **Additive paragraph-style emission (Codex A-1)**: Fix `_emit_styles()` at `document.py:678-685`
     which returns early when any custom paragraph style exists, disabling CI style stack emission.
     Make custom styles additive over the CI stack.
   - **Anchor API**: Introduce `Anchor(h=, v=, margin_mm=)` canonical named-args form; keep legacy
     string/tuple parsers with `DeprecationWarning`.
   - **Run legacy tuple form**: Emit `DeprecationWarning` for non-internal callers.
   - **Validation messages**: Pass offending attr name + closed set name to error messages.
   - **Rename `text_align` to `vertical_text_align`**.
   Maps to **Task 6**. Source: REVIEW.md §Area A P1 findings + §Prioritized P1 backlog P1-4.
   Notes: REVIEW.md adds Codex A-1 (additive paragraph-style emission) as an additional P1
   sub-item not listed in RESEARCH.md's ergonomics section.

5. **Multi-input ADR** — write `tools/sla_lib/docs/adr-001-multi-input-readiness.md`.
   Maps to **Task 7**. Source: REVIEW.md §Area C + §Prioritized P1 backlog P1-5.

6. **Spec schema** — write `shared/template-spec.schema.yaml` + `docs/spec-input-schema.md`.
   Maps to **Task 8**. Source: REVIEW.md §Prioritized P1 backlog P1-6.

---

## Items demoted from RESEARCH.md

- **`clip_edit` auto-emit as unconditional** (RESEARCH.md item 5) — Demoted from "unconditional
  P1" to "guarded optimization". Per REVIEW.md instruction (coordinator note): apply only on
  rectangular frames where the path is safely derivable from `width/height`. Skip frames where
  derivation isn't trivial. Still P1 but with the guard condition. Covered in Task 5c.

- **Strip pt overrides unconditionally** (RESEARCH.md item 3) — Demoted to conditional on
  `sla_diff` byte-equivalence check result. Per REVIEW.md Codex B-6 and coordinator note:
  gate behind `--strict-bytes` flag if sla_diff requires byte equivalence (verify first).
  Covered in Task 5b with this guard.

---

## Items added by REVIEW.md not in RESEARCH.md

- **Additive paragraph-style emission fix** (Codex A-1) — `_emit_styles()` at `document.py:678-685`
  returns early when any custom paragraph style exists. This disables CI style stack emission.
  Added as a P1 sub-item in Task 6 (DSL ergonomics). Merged into existing Task 6 scope.

- **`palette_replaces_ci=True` → `False` on brand path** — REVIEW.md confirmed explicitly that
  the flip is part of Task 5a (converter consumes Brand) AND Task 6 (Brand profile default).
  This was mentioned in RESEARCH.md but not as an explicit separate P1 item. Merged into Task 5a.

- **`Line.to_pageobject` AttributeError** (Claude A-1 critical) — Explicitly elevated to
  "first sub-step" of Task 6. Lowest-risk fix: remove `Line` from public surface; document
  that lines are `Polygon(custom_path=..., line_color=..., fill='None')`. RESEARCH.md mentioned
  this as "either remove Line or document it" without the critical severity. REVIEW.md makes it
  critical and requires it be addressed first in Task 6.

---

## Items kept verbatim from RESEARCH.md

- Brand profile Option A (frozen dataclass) — Task 3
- Evidence-driven 5 blocks (PageNumber, Impressum, PageBackground, ContactBlock,
  ColumnTextStory) — Task 4
- Converter leanness: emit brand= + differing extras only — Task 5a
- Multi-input ADR — Task 7
- Spec schema — Task 8

---

## Mapping to PLAN.md tasks

| P1 # | Task in PLAN | Notes |
|---|---|---|
| 1 | Task 3 (Brand profile) | Verbatim from RESEARCH.md. No deviations. |
| 2 | Task 4 (evidence-driven blocks) | Verbatim. TDD required. |
| 3 | Task 5 (converter leanness, 3 sub-commits) | 5b guarded by --strict-bytes; 5c rectangle-only guard. |
| 4 | Task 6 (DSL ergonomics) | Add Codex A-1 additive-styles fix as first sub-step after Line removal. |
| 5 | Task 7 (multi-input ADR) | Documentation only. |
| 6 | Task 8 (spec schema) | Documentation only. |

No new tasks required beyond PLAN.md Tasks 2-10. All REVIEW.md P1 additions fit within existing
task boundaries. No halt-and-ask escalation needed.

---

## Gating confirmation

Per REVIEW.md §Gating decision (confirmed by all three reviewers):

- No `templates/<id>/build.py` for new templates may land before Tasks 3-6 (P1 hardening) merge.
- Existing-template rewrites (Postkarte, Plakat, Zeitung) are the migration follow-ups, filed
  in Task 9, with `depends_on: [5]`.

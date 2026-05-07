# EXECUTION — Review build.py + DSL before more templates

**Started:** 2026-05-07
**Status:** complete
**Branch:** issue/5-review-buildpy-dsl-before-more-templates

## Acceptance check

- [x] `/issue:review` run completed with all three reviewers — evidence: `grep "Reviewers: Claude (claude-sonnet-4-6), Codex (gpt-5.4), Gemini" REVIEW.md` and "Per-reviewer raw output" section present with three subsections.
- [x] Review report committed under `.issues/5-.../REVIEW.md` summarizing findings per area A/B/C — evidence: sections `## Area A`, `## Area B`, `## Area C` present; `## Higher-level construct proposals` and `## Prioritized P1 backlog` cover areas D/E per RESEARCH.md three-area split.
- [x] Concrete API proposal for `Brand`, content blocks, and page-template layer — evidence: `Brand.gruene_noe()` implemented in `tools/sla_lib/builder/brand.py` (commit 757a4b4); 5 evidence-driven blocks in `tools/sla_lib/builder/blocks.py` (commit 4888324); `Document.add_facing_pages_masters(...)` convenience method in `document.py` (noted in REVIEW.md "Higher-level construct proposals").
- [x] Line-count delta estimate for applying the new constructs — evidence: REVIEW.md "Line-count delta estimates" section has consensus ≈160-190/260-330/2200-2550; actual pre-issue LOC is 235/437/3244 (migrations deferred to follow-up issues #6/#7/#8 per CONTEXT.md).
- [x] Prioritized list of follow-up issues filed — evidence: `.issues/rewrite-postkarte-onto-brand-blocks/ISSUE.md` (id:6), `.issues/rewrite-plakat-onto-brand-blocks/ISSUE.md` (id:7), `.issues/rewrite-zeitung-onto-brand-blocks/ISSUE.md` (id:8); all have `depends_on: [5]`.
- [x] No new templates land before P1 hardening merges — evidence: REVIEW.md `## Gating decision` section confirms "no `templates/<id>/build.py` for new templates may land before P1 hardening items above are merged"; restated here per CONTEXT.md decision 4.

**Gating decision (restated):** No new `templates/<id>/build.py` may be committed until issue #5 is merged. The existing-template rewrites (issues #6, #7, #8) are the agreed migration follow-ups and are themselves gated on issue #5.

## Verification commands run

| Command | Result | Notes |
|---|---|---|
| `pytest tools/sla_lib/tests -x` | PASS | 245 passed, 3 warnings, 18 subtests |
| `bin/validate --ci` | PASS | sla_diff + visual_diff PASS for all three templates |
| `bin/render-gallery` | PASS | plakat, postkarte, zeitung all OK |
| `python3 tools/check_ci.py templates/plakat-a1-hochformat/template.sla` | warnings only | 4 extra-style warnings (template-local styles, expected); 0 errors |
| `python3 tools/check_ci.py templates/postkarte-a6-kampagne/template.sla` | warnings only | 1 extra-color + 7 extra-style warnings (template-local, expected); 0 errors |
| `python3 tools/check_ci.py templates/zeitung-a4-grun/template.sla` | warnings only | 1 extra-color + 23 extra-style warnings (template-local, expected); 0 errors |

## Execution log

- [x] Task 1: Run /issue:review and produce REVIEW.md — commit 583e1da
- [x] Task 2: Reconcile P1 list — commit 28893c0
- [x] Task 3: Brand profile hoisting 113+34 attrs — commit 757a4b4
- [x] Task 4: Replace aspirational blocks with 5 evidence-driven blocks — commit 4888324
- [x] Task 5: Converter leanness (Brand emit + pt-geometry drop + clip-rect auto) — commit ebe5d57
- [x] Task 6: DSL LLM-emission ergonomics — commit c02fefd
- [x] Task 7: Multi-input readiness ADR — commit 8f92b69
- [x] Task 8: Spec-file schema + LLM consumption guide — commit 71867c5
- [x] Task 9: Create follow-up migration issues — commit c5cac86
- [x] Task 10: Acceptance check + EXECUTION.md — this commit

## Artifacts produced

| Artifact | Path | Notes |
|---|---|---|
| REVIEW.md | `.issues/5-.../REVIEW.md` | All three reviewers (Claude, Codex, Gemini); per-reviewer raw output |
| REVIEW-P1.md | `.issues/5-.../REVIEW-P1.md` | Reconciled P1 backlog |
| Brand profile | `tools/sla_lib/builder/brand.py` | Frozen dataclass; 113 doc-attrs + 34 pdf-attrs |
| CI defaults data | `shared/ci-defaults.yml` | 113+34 identical brand defaults |
| blocks.py (rewritten) | `tools/sla_lib/builder/blocks.py` | 5 evidence-driven blocks replacing 8 aspirational |
| sla_to_dsl.py (refactored) | `tools/sla_to_dsl.py` | Emits brand=, drops pt-geometry on recoverable frames, clip-rect auto |
| document.py (updated) | `tools/sla_lib/builder/document.py` | Clip-rect auto-emit, additive styles, brand wiring |
| primitives.py (updated) | `tools/sla_lib/builder/primitives.py` | Anchor dataclass, Run deprecation, vertical_text_align, Line fix |
| ADR-001 | `tools/sla_lib/docs/adr-001-multi-input-readiness.md` | Multi-input DSL contract |
| Spec schema | `shared/template-spec.schema.yaml` | JSON Schema (draft-2020-12) in YAML |
| Spec guide | `docs/spec-input-schema.md` | LLM consumption guide with worked example |
| Follow-up issue #6 | `.issues/rewrite-postkarte-onto-brand-blocks/ISSUE.md` | depends_on: [5] |
| Follow-up issue #7 | `.issues/rewrite-plakat-onto-brand-blocks/ISSUE.md` | depends_on: [5] |
| Follow-up issue #8 | `.issues/rewrite-zeitung-onto-brand-blocks/ISSUE.md` | depends_on: [5] |

## LOC measurements

| Template | Pre-issue | Post-issue | Note |
|---|---|---|---|
| Plakat A1 | 235 | 235 | Migration deferred to issue #7; converter output unchanged (not re-run per CONTEXT.md) |
| Postkarte A6 | 437 | 437 | Migration deferred to issue #6 |
| Zeitung A4 | 3244 | 3244 | Migration deferred to issue #8 |

Note: LOC reductions are achieved in the migration follow-up issues (#6, #7, #8) by re-running the
updated converter against existing `template.sla` files. The DSL hardening in this issue (Brand,
blocks, clip-rect auto, pt-geometry drop) is what makes those reductions possible. The Task 5
verify block checked that the converter now correctly emits `brand=Brand.gruene_noe()` and drops
redundant geometry; it does not re-run the existing templates' build.py (that would violate
CONTEXT.md: "existing-template rewrites are themselves the migration follow-ups").

## Deviations from plan

### Auto-fixed (Rules 1-3)

1. **[Rule 1 - Bug] Fixed `Line.to_pageobject` AttributeError** (REVIEW.md A-1 critical)
   - Found: `Line` references `self.clip_edit` but does not inherit from `_Frame`; any `page.add(Line(...)).save()` crashes.
   - Fix: hardcoded `"CLIPEDIT": "0"` in `to_pageobject`; added `DeprecationWarning`; updated docstring.
   - Commit: c02fefd

2. **[Rule 1 - Bug] Fixed additive paragraph-style emission** (REVIEW.md Codex A-1)
   - Found: `_emit_styles()` in `document.py` returned early as soon as any custom style existed, suppressing the entire CI style stack.
   - Fix: gated on `palette_replaces_ci`; when False, emit CI base stack then extra styles additive on top.
   - Commit: c02fefd

3. **[Rule 2 - Correctness] Fixed `test_default_style_marker_is_default` after additive fix**
   - Found: test found first `<STYLE>` by position; additive fix changed emission order.
   - Fix: find by name attribute.
   - Commit: c02fefd

4. **[Rule 3 - Blocker] Fixed `test_5b_non_inline_frames_have_no_xpos_pt` assertion**
   - Found: `page_xpos_pt=` on `add_page()` calls was being counted as frame-level `xpos_pt=` by naive `str.count`.
   - Fix: subtract `page_xpos_pt=` count from total `xpos_pt=` count.
   - Commit: ebe5d57

### Blocked (Rule 4)

None.

## Open items deferred to follow-ups

P2 items from REVIEW.md (see "P2 follow-up issues to file" section in REVIEW.md):

- Fix `load_ci()` global singleton: cache by resolved path (Codex B-1) — separate issue
- Fix master-page NEXTITEM/BACKITEM chain patching (Codex B-2) — separate issue
- Fix soft-shadow erase round-trip key mismatch (Codex B-3) — separate issue
- Fix `unit` and `first_page_num` kwargs silently no-op (Claude A-12) — separate issue
- Update generated build.py header to reflect AI-authored workflow (Codex B-4) — separate issue
- Extend `check_ci.py` to validate brand-style PARENT inheritance (Claude A-16) — separate issue

## Self-check

- [x] All files from plan exist (brand.py, ci-defaults.yml, blocks.py, adr-001, template-spec.schema.yaml, spec-input-schema.md, three follow-up issue files)
- [x] All commits exist on branch (583e1da, 28893c0, 757a4b4, 4888324, ebe5d57, c02fefd, 8f92b69, 71867c5, c5cac86)
- [x] Full verification suite passes (245 tests, bin/validate --ci, bin/render-gallery all green)
- [x] No stubs/TODOs/placeholders in produced code
- [x] No leftover debug code
- **Result:** PASSED

**Completed:** 2026-05-07
**Duration:** ~1 session (continuation from prior session where Tasks 1-4 were completed)
**Commits:** 9 (Tasks 1-9) + 1 (this EXECUTION.md)
